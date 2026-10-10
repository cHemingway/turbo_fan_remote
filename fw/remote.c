/*
Turbo fan IR remote - CH32L103F8P6

Three buttons (up, power, down). The chip lives in standby (~0.4uA) and is
woken by a falling edge on any button via an EXTI *event*. Waking from standby
is a full power reset, so every button press starts again at main(): read
which button is held, send the NEC frame, send NEC repeat codes while it stays
held (up to NEC_REPEAT_MAX_MS), go back to standby. The PVD guards against a
flat battery: no transmission if VDD is already low, and a frame is cut short
if VDD sags toward 1.8 V (see pvd_set_level()). A button still held at
that point (stuck, or sat on) is armed to wake on its release instead, so a
jammed button can't keep the chip awake and drain the coin cell.

IR generation uses TIM1 alone:
  - CH1 runs PWM at 38 kHz, 1/3 duty. That's the carrier.
  - The repetition counter (RPTCR) makes the update event fire only once every
    REP+1 carrier periods, so one update = one mark or space.
  - On each update, DMA burst writes the next {RPTCR, CH1CVR} pair from a
    table via TIM1_DMAADR. CH1CVR = duty for a mark, 0 for a space. Both
    registers are preloaded, so changes land exactly on carrier period
    boundaries and no partial pulses come out.

Pins:
  PA1  TIM1_CH1 (AFIO remap 010) -> IR LED driver (NPN / N-FET, active high).
       Put a pull-down on the driver input: all GPIOs float in standby.
  PA4  UP button    -> GND, active low
  PA5  POWER button -> GND, active low
  PA6  DOWN button  -> GND, active low
       Fit external pull-ups (100k-1M) to VDD. The internal pull-ups are
       enabled while running, but GPIO config isn't guaranteed to hold in
       standby.

SWD stays on PA13/PA14 (shorted internally to PB6/PB7 on the F8P6; don't use
those as outputs).
*/

#include "ch32fun.h"
#include <stdint.h>
#include <stdbool.h>

#define PIN_IR        PA1
#define PIN_UP        PA4
#define PIN_POWER     PA5
#define PIN_DOWN      PA6
#define BUTTON_MASK   ((1 << 4) | (1 << 5) | (1 << 6)) // EXTI lines / GPIOA bits

// NEC codes. Placeholders: match these to whatever the fan controller decodes.
#define NEC_ADDRESS   0x00
#define NEC_CMD_UP    0x01
#define NEC_CMD_POWER 0x02
#define NEC_CMD_DOWN  0x03

#define NEC_REPEAT_PERIOD_MS 108
#define NEC_REPEAT_MAX_MS    10000 // stop repeating a button held longer than this

// Carrier: 8 MHz / 210 = 38.095 kHz, duty 70/210 = 1/3
#define IR_CARRIER_HZ  38000
#define CARRIER_ARR    ((FUNCONF_SYSTEM_CORE_CLOCK + IR_CARRIER_HZ / 2) / IR_CARRIER_HZ - 1)
#define CARRIER_DUTY   ((CARRIER_ARR + 1) / 3)

// The ch32fun TIM_TypeDef for the L103 has CHxCVR_TIM4 padding fields that put
// CH1CVR, BDTR, DMACFGR and DMAADR at the wrong offsets. Use the RM addresses
// for TIM1 (RM table 14-x: RPTCR 0x30, CH1CVR 0x34, BDTR 0x44, DMACFGR 0x48,
// DMAADR 0x4C).
#define TIM1_CH1CVR   (*(volatile uint32_t *)(TIM1_BASE + 0x34))
#define TIM1_BDTR     (*(volatile uint16_t *)(TIM1_BASE + 0x44))
#define TIM1_DMACFGR  (*(volatile uint16_t *)(TIM1_BASE + 0x48))
#define TIM1_DMAADR   (*(volatile uint32_t *)(TIM1_BASE + 0x4C))

// DMA burst: start at RPTCR (0x30 / 4 = 12), 2 registers (RPTCR, CH1CVR)
#define TIM1_DBA_RPTCR 12
#define TIM1_DBL_2     (1 << 8)

// One mark or space. Layout must match the burst order: RPTCR then CH1CVR.
typedef struct
{
	uint32_t rep; // carrier periods - 1 (0..255)
	uint32_t ccr; // CARRIER_DUTY for a mark, 0 for a space
} ir_seg_t;

// NEC frame: leader (2 + 1) + 32 bits * 2 + stop mark + terminator = 69
#define IR_MAX_SEGS 80
static ir_seg_t ir_segs[IR_MAX_SEGS];
static int ir_nsegs;

static void ir_add(uint32_t us, bool mark)
{
	uint32_t periods = (us * IR_CARRIER_HZ + 500000) / 1000000;
	uint32_t ccr = mark ? CARRIER_DUTY : 0;

	// RPTCR is 8 bits, so anything over 256 periods (6.7 ms) is split
	while (periods && ir_nsegs < IR_MAX_SEGS)
	{
		uint32_t n = periods > 256 ? 256 : periods;
		ir_segs[ir_nsegs++] = (ir_seg_t){ n - 1, ccr };
		periods -= n;
	}
}

static void ir_init(void)
{
	RCC->APB2PCENR |= RCC_AFIOEN | RCC_TIM1EN;
	RCC->AHBPCENR |= RCC_DMA1EN;

	// TIM1 remap {TIM1_RM_H, TIM1_RM} = 010 -> CH1 on PA1
	AFIO->PCFR2 &= ~AFIO_PCFR2_TIM1_RM_H;
	AFIO->PCFR1 = (AFIO->PCFR1 & ~AFIO_PCFR1_TIM1_RM) | AFIO_PCFR1_TIM1_RM_1;
	funPinMode(PIN_IR, GPIO_CFGLR_OUT_10Mhz_AF_PP);

	TIM1->CTLR1 = TIM_ARPE | TIM_URS; // URS: UG doesn't fire the DMA request
	TIM1->PSC = 0;
	TIM1->ATRLR = CARRIER_ARR;
	TIM1->CHCTLR1 = TIM_OC1M_2 | TIM_OC1M_1 | TIM_OC1PE; // PWM mode 1, preloaded
	TIM1_CH1CVR = 0;
	TIM1->CCER = TIM_CC1E;
	TIM1_DMACFGR = TIM1_DBL_2 | TIM1_DBA_RPTCR;
	TIM1_BDTR = TIM_MOE;
	TIM1->SWEVGR = TIM_UG; // latch CCR = 0 so the output idles low
}

// Brown-out protection. The hardware PDR only resets the chip at ~1.55 V
// (1.45-1.65 V), but it's only specified down to 1.8 V, so a flat coin cell
// sagging under the LED load could leave it running out of spec. The PVD
// watches VDD instead: before transmitting we check the resting voltage, and
// during a frame we abort the moment VDD dips toward 1.8 V.
#define PVD_LEVEL_TX_OK    PWR_CTLR_PLS_MODE3 // 2.28 V falling / 2.35 V rising
#define PVD_LEVEL_ABORT    PWR_CTLR_PLS_MODE1 // 1.87 V falling / 1.93 V rising

static void pvd_set_level(uint32_t level)
{
	RCC->APB1PCENR |= RCC_PWREN;
	PWR->CTLR = (PWR->CTLR & ~PWR_CTLR_PLS) | level | PWR_CTLR_PVDE;
	Delay_Us(100); // let the comparator settle
}

static bool vdd_low(void)
{
	return PWR->CSR & PWR_CSR_PVDO; // 1 = VDD below the PVD threshold
}

// Stop the carrier immediately, mid-frame if need be, and leave TIM1 ready
// for the next ir_send()
static void ir_stop(void)
{
	TIM1->CTLR1 &= ~TIM_CEN;
	TIM1->DMAINTENR = 0;
	DMA1_Channel5->CFGR = 0;
	TIM1->CHCTLR1 = TIM_OC1M_2 | TIM_OC1PE; // force OC1 inactive (LED off) now
	TIM1->RPTCR = 0;
	TIM1_CH1CVR = 0;
	TIM1->SWEVGR = TIM_UG; // latch CCR = 0
	TIM1->CHCTLR1 = TIM_OC1M_2 | TIM_OC1M_1 | TIM_OC1PE; // back to PWM mode 1
	ir_nsegs = 0;
}

// Transmit ir_segs[0..ir_nsegs). Blocks until the last mark has finished.
// Returns false if VDD browned out and the frame was cut short.
static bool ir_send(void)
{
	// Terminator: once this is active the output is off and we can stop
	ir_segs[ir_nsegs++] = (ir_seg_t){ 0, 0 };

	// Segment 0 goes straight into the shadow registers via UG, segment 1
	// into the preload registers. From then on, the update that ends
	// segment k loads k+1 into the shadows and DMA writes k+2 into preload.
	TIM1->RPTCR = ir_segs[0].rep;
	TIM1_CH1CVR = ir_segs[0].ccr;
	TIM1->SWEVGR = TIM_UG;
	TIM1->RPTCR = ir_segs[1].rep;
	TIM1_CH1CVR = ir_segs[1].ccr;

	DMA1_Channel5->CFGR = 0; // TIM1_UP is DMA1 channel 5
	DMA1_Channel5->PADDR = (uint32_t)&TIM1_DMAADR;
	DMA1_Channel5->MADDR = (uint32_t)&ir_segs[2];
	DMA1_Channel5->CNTR = (ir_nsegs - 2) * 2;
	DMA1->INTFCR = DMA_CGIF5;
	DMA1_Channel5->CFGR = DMA_CFGR1_DIR | DMA_CFGR1_MINC |
		DMA_CFGR1_PSIZE_1 | DMA_CFGR1_MSIZE_1 | DMA_CFGR1_EN;

	TIM1->INTFR = 0;
	TIM1->DMAINTENR = TIM_UDE;
	TIM1->CTLR1 |= TIM_CEN;

	// DMA done = terminator is in preload and the final mark is running
	while (!(DMA1->INTFR & DMA_TCIF5))
		if (vdd_low()) goto brownout;
	TIM1->INTFR = (uint16_t)~TIM_UIF;
	// Next update = final mark done, terminator (CCR = 0) active
	while (!(TIM1->INTFR & TIM_UIF))
		if (vdd_low()) goto brownout;

	TIM1->CTLR1 &= ~TIM_CEN;
	TIM1->DMAINTENR = 0;
	DMA1_Channel5->CFGR = 0;
	ir_nsegs = 0;
	return true;

brownout:
	ir_stop();
	return false;
}

static bool nec_send_frame(uint8_t address, uint8_t command)
{
	uint32_t data = address | ((uint32_t)(uint8_t)~address << 8) |
		((uint32_t)command << 16) | ((uint32_t)(uint8_t)~command << 24);

	ir_add(9000, true);
	ir_add(4500, false);
	for (int i = 0; i < 32; i++)
	{
		ir_add(563, true);
		ir_add((data & (1UL << i)) ? 1688 : 563, false);
	}
	ir_add(563, true);
	return ir_send();
}

static bool nec_send_repeat(void)
{
	ir_add(9000, true);
	ir_add(2250, false);
	ir_add(563, true);
	return ir_send();
}

static void buttons_init(void)
{
	funPinMode(PIN_UP, GPIO_CFGLR_IN_PUPD);
	funPinMode(PIN_POWER, GPIO_CFGLR_IN_PUPD);
	funPinMode(PIN_DOWN, GPIO_CFGLR_IN_PUPD);
	GPIOA->BSHR = BUTTON_MASK; // pull-ups
}

// Bitmask (GPIOA / EXTI line numbering) of buttons currently held down
static uint32_t buttons_held(void)
{
	return ~GPIOA->INDR & BUTTON_MASK;
}

// Returns the NEC command for the held button, or -1 if none
static int buttons_read_command(void)
{
	if (!funDigitalRead(PIN_POWER)) return NEC_CMD_POWER;
	if (!funDigitalRead(PIN_UP)) return NEC_CMD_UP;
	if (!funDigitalRead(PIN_DOWN)) return NEC_CMD_DOWN;
	return -1;
}

// Returns only if standby was not entered
static void enter_standby(void)
{
	// Button lines as EXTI events (events, not interrupts, wake the chip from
	// standby). PA4..PA6 -> EXTI4..6, port A = 0 in EXTICR2. Released buttons
	// wake on press (falling edge); any still held wake on release (rising).
	uint32_t held = buttons_held();
	AFIO->EXTICR[1] &= ~0x0FFF;
	EXTI->INTENR = 0;
	EXTI->RTENR = held;
	EXTI->FTENR = BUTTON_MASK & ~held;
	EXTI->EVENR = BUTTON_MASK;
	EXTI->INTFR = BUTTON_MASK;

	RCC->APB1PCENR |= RCC_PWREN;
	PWR->CTLR |= PWR_CTLR_CWUF | PWR_CTLR_CSBF;

	// No RAM retention, no LDO tricks, no PVD; flash low-power mode 1
	PWR->CTLR &= ~(PWR_RAMLV | PWR_CTLR_R18KVBAT | PWR_CTLR_R2KVBAT | PWR_CTLR_R18KSTY |
		PWR_CTLR_R2KSTY | PWR_CTLR_LDO_EC | PWR_CTLR_AUTO_LDO_EC | PWR_CTLR_FLASH_LP |
		PWR_CTLR_PVDE);
	PWR->CTLR |= PWR_CTLR_FLASH_LP_REG | PWR_CTLR_FLASH_LP_1 | PWR_CTLR_PDDS;
	NVIC->SCTLR |= (1 << 2); // SLEEPDEEP

	// A button that changed state after we sampled it may have already had its
	// edge, so bail out and let main() look again. If we do get to standby,
	// the next edge resets the chip and we never return.
	if (buttons_held() != held)
		return;
	__WFE();
}

int main(void)
{
	SystemInit();
	funGpioInitAll();

	RCC->APB1PCENR |= RCC_PWREN;
	bool from_standby = PWR->CSR & PWR_CSR_SBF;

	buttons_init();
	ir_init();

	if (!from_standby)
	{
		// Debug access dies in standby. Give a window after power-up / NRST
		// to reflash before going to sleep for the first time.
		Delay_Ms(5000);
	}

	while (1)
	{
		Delay_Ms(10); // debounce
		int command = buttons_read_command();

		// A cell that's already low at rest will sag below 1.8 V under the
		// LED load, so don't even start
		pvd_set_level(PVD_LEVEL_TX_OK);
		if (command >= 0 && !vdd_low())
		{
			pvd_set_level(PVD_LEVEL_ABORT);
			uint32_t frame_start = funSysTick32();
			bool ok = nec_send_frame(NEC_ADDRESS, command);

			for (int repeats = 0; ok && buttons_read_command() == command &&
				repeats < NEC_REPEAT_MAX_MS / NEC_REPEAT_PERIOD_MS; repeats++)
			{
				while ((uint32_t)(funSysTick32() - frame_start) < DELAY_MSEC_COUNT(NEC_REPEAT_PERIOD_MS));
				frame_start = funSysTick32();
				ok = nec_send_repeat();
			}
		}

		Delay_Ms(20); // let release bounce settle before arming the wake edges

		enter_standby();
	}
}
