# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "matplotlib",
#     "numpy",
# ]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, np, plt


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Turbo fan remote: CR2032 battery life

    How much of a CR2032's capacity the remote can actually use, and how long
    that lasts, for two settings of the in-frame brown-out abort level
    (`PVD_LEVEL_ABORT` in `fw/remote.c`).

    **Why the cut-off matters.** The firmware stops transmitting when either:

    1. VDD *at rest* (MCU awake, LED off) is below the "OK to transmit" PVD
       level, or
    2. VDD *during a frame* dips below the abort PVD level.

    A coin cell's internal resistance climbs steeply near end of life, so the
    remote stops working before the cell is actually empty. Raising the abort
    level by about 0.2 V gives more margin above the MCU's 1.8 V minimum but
    gives up some capacity.

    The PVD only has discrete levels, so "1.87 V + 0.2 V" becomes the nearest
    level, **2.08 V** (PLS = 010, falling edge).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Sources

    | What | Source | Used for |
    |---|---|---|
    | CR2032 cell | [Energizer CR2032 datasheet](https://data.energizer.com/pdfs/cr2032.pdf) (form 2032NA0618) | Rated capacity, 235 mAh to 2.0 V at 15 kΩ |
    | CR2032 behaviour | [Energizer Lithium Coin Handbook](https://data.energizer.com/pdfs/lithiumcoin_appman.pdf) (2018) | p5: OCV and internal resistance vs capacity, 75 Ω pulses (~30 mA, 0.1 s on / 4.9 s off). p4: 0 °C vs 21 °C at 1 mA. p7: ~1 %/year self-discharge, 10-year shelf life |
    | MCU | [WCH CH32L103 datasheet](https://www.wch-ic.com/downloads/CH32L103DS0_PDF.html) (local copy: `datasheets/CH32L103DS0.PDF`) | Run/standby current (Tables 3-6, 3-8-1), PVD levels and PDR (Table 3-4), reset duration |
    | IR LED | [Vishay TSAL6200 datasheet](https://www.vishay.com/docs/81010/tsal6200.pdf) (doc 81010) | I–V curve (Fig. 4, 100 µs pulses), radiant intensity vs current (Fig. 5), −1.8 mV/K |
    | LED reservoir caps | [Samsung CL31A107MQHNNN characteristics](https://datasheet.octopart.com/CL31A107MQHNNNE-Samsung-datasheet-12514918.pdf), [reference spec sheet](https://datasheet.octopart.com/CL31A107MQHNNNE-Samsung-datasheet-42315309.pdf), [Samsung product page](https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL31A107MQHNNN), [LCSC C15008](https://www.lcsc.com/product-detail/Multilayer-Ceramic-Capacitors-MLCC-SMD-SMT_SAMSUNG_CL31A107MQHNNNE_100uF-107-20-6-3V_C15008.html) | DC bias −40 % at 3 V; insulation resistance ≥ 50 MΩ·µF |

    The handbook's p5 curves suit this design better than the datasheet's
    pulse chart: they come from ~30 mA, 100 ms pulses, close to the remote's
    9 ms leader plus 60 ms of data at tens of mA.
    """)
    return


@app.cell
def _(np):
    # --- Energizer CR2032 ---
    CELL_NOMINAL_MAH = 235.0  # datasheet, to 2.0 V at 15 kOhm
    # Handbook p5, 21 °C, 75 Ohm pulse 0.1 s on / 4.9 s off (read by eye)
    OCV_CAP_MAH = np.array([0, 10, 25, 50, 100, 150, 175, 185, 195, 203, 208, 212])
    OCV_V = np.array([2.88, 2.86, 2.88, 2.88, 2.88, 2.87, 2.85, 2.82, 2.77, 2.70, 2.62, 2.55])
    IR_CAP_MAH = np.array([0, 10, 25, 50, 75, 100, 125, 150, 170, 185, 195, 202, 207, 212])
    IR_OHM = np.array([9, 10, 13, 14, 16, 15, 15, 16, 18, 22, 30, 40, 55, 75])
    SELF_DISCHARGE_PER_YEAR = 0.01  # handbook p7

    # --- 0 °C, from handbook p4 (1 mA continuous, 0 °C vs 21 °C) ---
    COLD_CAP_SCALE = 150 / 228  # 2.0 V reached at ~150 mAh instead of ~228 mAh
    COLD_OCV_OFFSET = -0.20  # plateau ~2.65 V instead of ~2.85 V at 1 mA
    COLD_IR_SCALE = 2.0  # ASSUMPTION: no published CR2032 pulse-IR vs temperature found
    COLD_VF_SHIFT = 0.04  # TSAL6200 -1.8 mV/K x 21 K

    # --- Circuit ---
    R7 = 15.0  # LED series resistor
    Q1_RDS = 0.05  # AO3400A, ~48 mOhm at VGS 2.5 V
    # TSAL6200 I-V, datasheet Fig. 4 (25 °C, 100 us pulses, read by eye);
    # anchored to the table: 1.35 V typ at 100 mA, 2.2 V typ at 1 A
    LED_IV_V = np.array([1.15, 1.20, 1.27, 1.35, 1.50, 1.70, 2.00, 2.20])
    LED_IV_MA = np.array([1, 10, 30, 100, 200, 400, 700, 1000])
    R8 = 47.0  # LED reservoir feed resistor
    C4_C6_DC_BIAS_FACTOR = 0.60  # Samsung DC-bias curve: -40 % at 3 V
    C_LED = 3 * 100e-6 * C4_C6_DC_BIAS_FACTOR
    C_VDD = 10e-6 * 0.8 + 2 * 100e-9  # C1 10 uF 25 V part, light derating at 3 V; C2, C3
    CARRIER_DUTY = 1 / 3

    # --- Ceramic leakage: Samsung spec IR >= 50 MOhm.uF (or 10 GOhm, whichever smaller) ---
    IR_SPEC_MOHM_UF = 50.0
    LEAKY_CAPS_UF = [100, 100, 100, 10]  # C4-C6, C1 (C1 assumed same spec class)
    V_CELL_TYP = 2.9

    # --- MCU (CH32L103 datasheet) ---
    I_RUN = 2.14e-3  # run, 8 MHz HSI, PLL off, peripherals on (Table 3-6)
    I_STANDBY = 0.37e-6  # standby, no RAM retention, LSI off (Table 3-8-1)
    T_BOOT_S = 6.5e-3  # reset duration after standby wake (tRSTTEMPO typ)
    T_FIRMWARE_OVERHEAD_S = 10e-3 + 20e-3 + 2 * 100e-6  # debounce + release settle + PVD settles

    # --- Brown-out thresholds (PVD levels, CH32L103 datasheet Table 3-4) ---
    PVD_TX_OK = 2.35  # PLS=011 rising edge; conservative for the check-before-send
    PVD_ABORT_OPTIONS = {"1.87 V (PLS=001)": 1.87, "2.08 V (PLS=010)": 2.08}
    PVD_ABORT_FIRMWARE = "2.08 V (PLS=010)"  # what fw/remote.c uses (PVD_LEVEL_ABORT)
    VDD_MCU_MIN = 1.8

    # --- Usage assumptions ---
    PRESSES_PER_DAY = 20
    REPEATS_PER_PRESS = 3  # ~0.4 s average hold
    NEC_REPEAT_PERIOD_S = 0.108
    return (
        C4_C6_DC_BIAS_FACTOR,
        CARRIER_DUTY,
        CELL_NOMINAL_MAH,
        COLD_CAP_SCALE,
        COLD_IR_SCALE,
        COLD_OCV_OFFSET,
        COLD_VF_SHIFT,
        C_LED,
        C_VDD,
        IR_CAP_MAH,
        IR_OHM,
        IR_SPEC_MOHM_UF,
        I_RUN,
        I_STANDBY,
        LEAKY_CAPS_UF,
        NEC_REPEAT_PERIOD_S,
        OCV_CAP_MAH,
        OCV_V,
        PRESSES_PER_DAY,
        PVD_ABORT_FIRMWARE,
        PVD_ABORT_OPTIONS,
        PVD_TX_OK,
        LED_IV_MA,
        LED_IV_V,
        Q1_RDS,
        R7,
        R8,
        REPEATS_PER_PRESS,
        SELF_DISCHARGE_PER_YEAR,
        T_BOOT_S,
        T_FIRMWARE_OVERHEAD_S,
        VDD_MCU_MIN,
        V_CELL_TYP,
    )


@app.cell(hide_code=True)
def _(
    C4_C6_DC_BIAS_FACTOR,
    COLD_CAP_SCALE,
    COLD_IR_SCALE,
    COLD_OCV_OFFSET,
    COLD_VF_SHIFT,
    mo,
):
    mo.md(rf"""
    ## Inputs

    **21 °C.** OCV and internal resistance against capacity used come from the
    handbook's p5 chart, read by eye.

    **0 °C.** The handbook (p4) shows a CR2032 at 1 mA running about 0.2 V lower
    at 0 °C (≈2.65 V instead of ≈2.85 V) and reaching 2.0 V at about 150 mAh
    instead of about 228 mAh. The cold case therefore:

    - compresses the capacity axis by {COLD_CAP_SCALE:.2f}
    - shifts the voltage down by {abs(COLD_OCV_OFFSET):.2f} V
    - multiplies the internal resistance by {COLD_IR_SCALE:g} (**assumption**:
      I found no published CR2032 pulse-resistance-vs-temperature data)
    - shifts the LED I–V curve up by {COLD_VF_SHIFT:.2f} V (TSAL6200 tempco)

    **Circuit** (schematic as of this notebook): the MCU runs straight off the
    cell, and the LED runs from its own reservoir C4–C6 refilled through R8.
    C4–C6 keep {C4_C6_DC_BIAS_FACTOR:.0%} of their 100 µF at 3 V (Samsung
    DC-bias curve). The LED current is averaged over the 38 kHz carrier (1/3
    duty). That's fine for the supply nodes because the reservoir and R8 smooth
    the carrier ripple.
    """)
    return


@app.cell
def _(
    COLD_CAP_SCALE,
    COLD_IR_SCALE,
    COLD_OCV_OFFSET,
    COLD_VF_SHIFT,
    IR_CAP_MAH,
    IR_OHM,
    OCV_CAP_MAH,
    OCV_V,
    np,
):
    CASES = {
        "21 °C": dict(cap_scale=1.0, ocv_offset=0.0, ir_scale=1.0, vf_shift=0.0),
        "0 °C": dict(
            cap_scale=COLD_CAP_SCALE,
            ocv_offset=COLD_OCV_OFFSET,
            ir_scale=COLD_IR_SCALE,
            vf_shift=COLD_VF_SHIFT,
        ),
    }

    def cell_model(life_mah, cap_scale, ocv_offset, ir_scale):
        """OCV and internal resistance at each capacity-used point."""
        voc = np.interp(life_mah, OCV_CAP_MAH * cap_scale, OCV_V) + ocv_offset
        rint = np.interp(life_mah, IR_CAP_MAH * cap_scale, IR_OHM) * ir_scale
        return voc, rint

    return CASES, cell_model


@app.cell(hide_code=True)
def _(CASES, OCV_CAP_MAH, cell_model, np, plt):
    _fig, _ax = plt.subplots(figsize=(7, 3.5))
    _ax2 = _ax.twinx()
    for (_name, _p), _ls in zip(CASES.items(), ["-", "--"]):
        _m = np.linspace(0, OCV_CAP_MAH[-1] * _p["cap_scale"], 200)
        _voc, _rint = cell_model(_m, _p["cap_scale"], _p["ocv_offset"], _p["ir_scale"])
        _ax.plot(_m, _voc, _ls, color="tab:blue", label=f"OCV {_name}")
        _ax2.plot(_m, _rint, _ls, color="tab:green", label=f"Internal resistance {_name}")
    _ax.set_xlabel("Capacity used (mAh)")
    _ax.set_ylabel("Voltage (V)")
    _ax2.set_ylabel("Internal resistance (Ω)")
    _ax.set_title("CR2032 model (Energizer handbook p4/p5)")
    _ax.grid(alpha=0.3)
    _fig.legend(fontsize=8, loc="center left", bbox_to_anchor=(0.12, 0.45))
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## LED drive

    During a carrier pulse the LED, R7 and Q1 sit across the LED reservoir
    VLED, so the pulse current is where the LED's I–V curve meets the load
    line VLED − I·(R7 + R<sub>DS(on)</sub>). Using the datasheet curve rather than
    a fixed V<sub>F</sub> matters at low VLED, where the knee (≈1.2 V) makes the current
    fall off faster than a straight line. Radiant intensity is roughly
    proportional to current (TSAL6200 Fig. 5) and range goes as its square
    root, so relative range ≈ √(I / 100 mA).

    **No saturation in this design.** In the
    [TSAL6200 datasheet](https://www.vishay.com/docs/81010/tsal6200.pdf),
    Fig. 5 (radiant intensity vs current) and Fig. 6 (radiant power vs
    current) are close to linear from 1 mA to 1 A. The table gives
    72 mW/sr typ at 100 mA and 600 mW/sr at 1 A, so 10× the current gives
    ~8.3× the light: ~15–20 % droop, and only near 1 A. The LED here runs at
    40–170 mA, well inside the linear part. Self-heating is negligible at
    this duty cycle; Fig. 7 gives −0.6 %/K, so it's ~15 % *brighter* at
    0 °C than at 25 °C, which isn't modelled here. Because light tracks LED
    current, and the battery supplies that same current, light per unit of
    battery charge is roughly independent of R7.
    """)
    return


@app.cell
def _(LED_IV_MA, LED_IV_V, Q1_RDS, R7, np):
    _I_GRID = np.logspace(-4, 0, 600)  # 0.1 mA .. 1 A

    def led_vf(i_amps, vf_shift=0.0):
        """TSAL6200 forward voltage, interpolated in log(I)."""
        return np.interp(np.log10(i_amps * 1e3), np.log10(LED_IV_MA), LED_IV_V) + vf_shift

    def led_current(vled, vf_shift=0.0, r7=R7):
        """LED pulse current (A) for a given VLED: I-V curve meets the R7 + Q1 load line."""
        v_needed = led_vf(_I_GRID, vf_shift) + _I_GRID * (r7 + Q1_RDS)
        return np.interp(vled, v_needed, _I_GRID, left=0.0)

    return led_current, led_vf


@app.cell(hide_code=True)
def _(CASES, LED_IV_MA, LED_IV_V, Q1_RDS, R7, led_current, led_vf, np, plt):
    _fig, _ax = plt.subplots(figsize=(7, 4))
    _i = np.logspace(-3, 0, 300)
    for (_name, _p), _ls in zip(CASES.items(), ["-", "--"]):
        _ax.plot(led_vf(_i, _p["vf_shift"]), _i * 1e3, _ls, color="k", label=f"TSAL6200 I–V, {_name}")
    _ax.plot(LED_IV_V, LED_IV_MA, "o", color="k", ms=4, label="Datasheet points (Fig. 4)")
    for _vled, _col in zip([3.0, 2.6, 2.2, 1.9], ["tab:blue", "tab:green", "tab:orange", "tab:red"]):
        _v = np.linspace(1.0, _vled, 50)
        _ax.plot(_v, (_vled - _v) / (R7 + Q1_RDS) * 1e3, color=_col, lw=1, label=f"Load line, VLED = {_vled} V")
        _ipk = led_current(np.array([_vled]))[0]
        _ax.plot(led_vf(_ipk), _ipk * 1e3, "o", color=_col)
        _ax.annotate(f"{_ipk * 1e3:.0f} mA", (led_vf(_ipk), _ipk * 1e3), textcoords="offset points", xytext=(6, 4), fontsize=8, color=_col)
    _ax.set_xlim(1.0, 2.2)
    _ax.set_ylim(0, 200)
    _ax.set_xlabel("Forward voltage (V)")
    _ax.set_ylabel("Forward current (mA)")
    _ax.set_title(f"LED operating point, R7 = {R7:g} Ω")
    _ax.grid(alpha=0.3)
    _ax.legend(fontsize=7, loc="upper left")
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Supply simulation

    Two nodes: **VDD** (MCU, C1–C3) is fed from the cell's open-circuit voltage
    through its internal resistance; **VLED** (C4–C6) is fed from VDD through
    R8 and drains into the LED during marks. The sequence is what one held
    press sends: an NEC frame, then two repeat codes on the 108 ms grid. It's
    simulated at every point of the cell's life at once, starting from a
    rested cell.
    """)
    return


@app.cell
def _(NEC_REPEAT_PERIOD_S):
    def nec_frame(command, address=0x00):
        """(duration_s, is_mark) segments for one NEC frame."""
        data = address | ((~address & 0xFF) << 8) | (command << 16) | ((~command & 0xFF) << 24)
        segs = [(9e-3, True), (4.5e-3, False)]
        for i in range(32):
            segs += [(563e-6, True), (1688e-6 if (data >> i) & 1 else 563e-6, False)]
        segs.append((563e-6, True))
        return segs

    def nec_repeat():
        return [(9e-3, True), (2.25e-3, False), (563e-6, True)]

    def pad_to_period(segs, period=NEC_REPEAT_PERIOD_S):
        """Append the idle gap up to the next 108 ms slot."""
        used = sum(d for d, _ in segs)
        return segs + [(period - used, False)]

    # One held press: frame + 2 repeats, each window padded to 108 ms
    PRESS_WINDOWS = [
        pad_to_period(nec_frame(0x02)),
        pad_to_period(nec_repeat()),
        pad_to_period(nec_repeat()),
    ]
    FRAME_S = sum(d for d, _ in nec_frame(0x02))
    return FRAME_S, PRESS_WINDOWS, nec_frame, nec_repeat, pad_to_period


@app.cell
def _(CARRIER_DUTY, C_LED, C_VDD, I_RUN, R8, led_current, np):
    def simulate(voc, rint, vf_shift, windows, dt=10e-6, r8=R8, c_led=C_LED, r7=None):
        """Simulate supply nodes for every (voc, rint) pair at once.

        r8 and c_led may be scalars or arrays matching voc (for sweeps); r7
        overrides the schematic's LED resistor (scalar).

        Returns per-life-point minimum VDD and minimum VLED, plus the LED
        charge drawn in each window (coulombs, per life point).
        """
        vdd = voc.astype(float).copy()
        vled = vdd.copy()
        vdd_min = vdd.copy()
        vled_min = vled.copy()
        q_windows = []
        for window in windows:
            q = np.zeros_like(vdd)
            for duration, mark in window:
                for _ in range(int(round(duration / dt))):
                    i_led = (
                        CARRIER_DUTY * led_current(vled, vf_shift, *(() if r7 is None else (r7,)))
                        if mark
                        else 0.0
                    )
                    i_cell = (voc - vdd) / rint
                    i_r8 = (vdd - vled) / r8
                    vdd = vdd + (i_cell - i_r8 - I_RUN) * dt / C_VDD
                    vled = vled + (i_r8 - i_led) * dt / c_led
                    np.minimum(vdd_min, vdd, out=vdd_min)
                    np.minimum(vled_min, vled, out=vled_min)
                    q = q + i_led * dt
            q_windows.append(q)
        return vdd_min, vled_min, q_windows

    return (simulate,)


@app.cell
def _(CASES, I_RUN, OCV_CAP_MAH, PRESS_WINDOWS, cell_model, np, simulate):
    sims = {}
    for _name, _p in CASES.items():
        _life = np.arange(0.0, OCV_CAP_MAH[-1] * _p["cap_scale"], 0.5)
        _voc, _rint = cell_model(_life, _p["cap_scale"], _p["ocv_offset"], _p["ir_scale"])
        _vdd_min, _vled_min, _q = simulate(_voc, _rint, _p["vf_shift"], PRESS_WINDOWS)
        sims[_name] = {
            "life_mah": _life,
            "vdd_rest": _voc - I_RUN * _rint,  # awake, LED off: what the TX-OK check sees
            "vdd_min": _vdd_min,
            "vled_min": _vled_min,
            "q_frame": _q[0],
            "q_repeat": np.mean(_q[1:], axis=0),
        }
    return (sims,)


@app.cell
def _(
    CELL_NOMINAL_MAH,
    FRAME_S,
    IR_SPEC_MOHM_UF,
    I_RUN,
    I_STANDBY,
    LEAKY_CAPS_UF,
    NEC_REPEAT_PERIOD_S,
    PRESSES_PER_DAY,
    REPEATS_PER_PRESS,
    SELF_DISCHARGE_PER_YEAR,
    T_BOOT_S,
    T_FIRMWARE_OVERHEAD_S,
    V_CELL_TYP,
    sims,
):
    MAH = 3.6  # coulombs per mAh

    # Ceramic leakage at the spec's guaranteed-minimum insulation resistance
    i_leak_spec = sum(V_CELL_TYP / (min(IR_SPEC_MOHM_UF / c, 10_000) * 1e6) for c in LEAKY_CAPS_UF)
    LEAKAGE = {"typical": 0.0, "spec max": i_leak_spec}

    standby_mah_per_year = I_STANDBY * 8760 * 1000
    self_discharge_mah_per_year = SELF_DISCHARGE_PER_YEAR * CELL_NOMINAL_MAH
    t_awake = T_BOOT_S + T_FIRMWARE_OVERHEAD_S + FRAME_S + REPEATS_PER_PRESS * NEC_REPEAT_PERIOD_S

    consumption = {}
    for _name, _s in sims.items():
        _q_led = _s["q_frame"][0] + REPEATS_PER_PRESS * _s["q_repeat"][0]
        _q_press = _q_led + I_RUN * t_awake
        _press_mah_per_year = PRESSES_PER_DAY * 365 * _q_press / MAH
        for _leak_name, _i_leak in LEAKAGE.items():
            _per_year = (
                _press_mah_per_year
                + standby_mah_per_year
                + self_discharge_mah_per_year
                + _i_leak * 8760 * 1000
            )
            consumption[(_name, _leak_name)] = {
                "q_led": _q_led,
                "q_press": _q_press,
                "mah_per_year": _per_year,
                "mah_per_day": _per_year / 365,
            }
    return (
        LEAKAGE,
        MAH,
        consumption,
        i_leak_spec,
        self_discharge_mah_per_year,
        standby_mah_per_year,
        t_awake,
    )


@app.cell(hide_code=True)
def _(
    PRESSES_PER_DAY,
    PVD_ABORT_OPTIONS,
    PVD_TX_OK,
    VDD_MCU_MIN,
    consumption,
    plt,
    sims,
):
    _fig, _axes = plt.subplots(len(sims), 1, figsize=(9, 4.2 * len(sims)))
    _x_max = max(_s["life_mah"][-1] for _s in sims.values())
    for _ax, (_name, _s) in zip(_axes, sims.items()):
        _m = _s["life_mah"]
        _ax.plot(_m, _s["vdd_rest"], label="VDD at rest (TX-OK check)")
        _ax.plot(_m, _s["vdd_min"], label="VDD min during press")
        _ax.plot(_m, _s["vled_min"], ":", label="VLED min (LED reservoir)")
        _ax.axhline(PVD_TX_OK, color="tab:purple", ls="--", lw=1, label=f"TX-OK {PVD_TX_OK} V")
        for (_label, _v), _col in zip(PVD_ABORT_OPTIONS.items(), ["tab:red", "tab:orange"]):
            _ax.axhline(_v, color=_col, ls="--", lw=1, label=f"Abort {_label}")
        _ax.axhline(VDD_MCU_MIN, color="k", lw=0.8, label="MCU min 1.8 V")
        _ax.set_title(_name)
        _ax.set_xlabel("Capacity used (mAh)")
        _ax.set_ylabel("Voltage (V)")
        _ax.set_xlim(0, _x_max)  # same range on both, so the cold cell's shorter life shows
        _ax.set_ylim(1.4, 3.0)
        _ax.grid(alpha=0.3)

        # Second x axis: years of use at this temperature, typical leakage
        _mpy = consumption[(_name, "typical")]["mah_per_year"]
        _years = _ax.secondary_xaxis(-0.24, functions=(lambda m, k=_mpy: m / k, lambda y, k=_mpy: y * k))
        _years.set_xlabel(f"Years ({PRESSES_PER_DAY} presses/day, typical leakage)")
    _axes[0].legend(fontsize=7, loc="lower left")
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(CASES, led_current, np, plt, sims):
    _fig, _axes = plt.subplots(len(sims), 1, figsize=(9, 3.4 * len(sims)))
    _x_max = max(_s["life_mah"][-1] for _s in sims.values())
    for _ax, (_name, _s) in zip(_axes, sims.items()):
        _shift = CASES[_name]["vf_shift"]
        _m = _s["life_mah"]
        _i_start = led_current(_s["vdd_rest"], _shift) * 1e3  # VLED = VDD at rest: first pulse
        _i_min = led_current(_s["vled_min"], _shift) * 1e3  # weakest pulse, late in the frame
        _ax.plot(_m, _i_start, label="Pulse current, first pulse")
        _ax.plot(_m, _i_min, label="Pulse current, weakest pulse")
        _ax.fill_between(_m, _i_min, _i_start, alpha=0.15)
        _ax.axhline(200, color="k", lw=0.8, ls=":", label="TSAL6200 I_FM 200 mA")
        _ax.set_title(_name)
        _ax.set_xlabel("Capacity used (mAh)")
        _ax.set_ylabel("LED pulse current (mA)")
        _ax.set_xlim(0, _x_max)
        _ax.set_ylim(0, 220)
        _ax.grid(alpha=0.3)
        # Right axis: range relative to a 100 mA pulse (range ~ sqrt(intensity) ~ sqrt(I))
        _r = _ax.secondary_yaxis(
            "right", functions=(lambda i: np.sqrt(np.maximum(i, 0) / 100), lambda r: 100 * r**2)
        )
        _r.set_yticks([0.4, 0.6, 0.8, 1.0, 1.2, 1.4])
        _r.set_ylabel("Range vs 100 mA pulse")
    _axes[0].legend(fontsize=7, loc="lower left")
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## End of life and battery life

    End of life is the first point where a press would be refused (VDD at rest
    below the TX-OK level) or cut short (VDD during the press below the abort
    level). The capacity used up to there is what's usable.

    Charge per press = LED charge (frame + repeats, from the simulation of a
    fresh cell) + MCU run current × time awake (boot, debounce, the frames
    themselves, release settle). Each year also loses standby current, the
    cell's self-discharge and capacitor leakage.

    **Capacitor leakage** is shown two ways. *Typical*: modern X5R parts
    usually leak far less than their guarantee, so it's taken as negligible.
    *Spec max*: Samsung only guarantees insulation resistance ≥ 50 MΩ·µF, i.e.
    0.5 MΩ for each 100 µF part, so leakage could legally be several µA.
    That's 10× the MCU's standby current, so measure a real board.
    """)
    return


@app.cell
def _(LEAKAGE, MAH, PVD_ABORT_OPTIONS, PVD_TX_OK, CELL_NOMINAL_MAH, consumption, np, sims):
    def usable_mah(s, abort_v):
        """Capacity used at end of life, and which check ends it."""
        refused = s["vdd_rest"] < PVD_TX_OK
        aborted = s["vdd_min"] < abort_v
        dead = refused | aborted
        if not dead.any():
            return s["life_mah"][-1], "cell exhausted (end of handbook data)"
        i = np.argmax(dead)
        return s["life_mah"][i], "abort in frame" if aborted[i] else "TX-OK at rest"

    results = []
    for _name, _s in sims.items():
        for _label, _v in PVD_ABORT_OPTIONS.items():
            _usable, _limit = usable_mah(_s, _v)
            for _leak in LEAKAGE:
                _c = consumption[(_name, _leak)]
                results.append(
                    {
                        "case": _name,
                        "abort": _label,
                        "leakage": _leak,
                        "usable_mah": _usable,
                        "usable_pct": 100 * _usable / CELL_NOMINAL_MAH,
                        "limited_by": _limit,
                        "q_press_mc": 1e3 * _c["q_press"],
                        "q_led_mc": 1e3 * _c["q_led"],
                        "presses": _usable * MAH / _c["q_press"],
                        "mah_per_year": _c["mah_per_year"],
                        "years": _usable / _c["mah_per_year"],
                    }
                )
    return (results,)


@app.cell(hide_code=True)
def _(
    CELL_NOMINAL_MAH,
    PRESSES_PER_DAY,
    PVD_ABORT_FIRMWARE,
    REPEATS_PER_PRESS,
    i_leak_spec,
    mo,
    results,
    self_discharge_mah_per_year,
    standby_mah_per_year,
):
    _cols = ["Temp", "Abort level", "Cap leakage", f"Usable (of {CELL_NOMINAL_MAH:.0f} mAh)",
             "Limited by", "Charge per press", "Presses", "mAh/year", "Years"]
    _head = "".join(f"<th>{c}</th>" for c in _cols)
    _body = []
    for r in results:
        # Highlight the expected case: firmware's abort level, typical leakage
        _chosen = r["abort"] == PVD_ABORT_FIRMWARE and r["leakage"] == "typical"
        _style = ' style="background:#fff3b0;font-weight:bold"' if _chosen else ""
        _cells = [
            r["case"], r["abort"] + (" ◀ firmware" if r["abort"] == PVD_ABORT_FIRMWARE else ""),
            r["leakage"], f"{r['usable_mah']:.0f} mAh ({r['usable_pct']:.0f} %)", r["limited_by"],
            f"{r['q_press_mc']:.2f} mC ({r['q_led_mc']:.2f} LED)", f"{r['presses']:,.0f}",
            f"{r['mah_per_year']:.1f}", f"{r['years']:.1f}",
        ]
        _body.append(f"<tr{_style}>" + "".join(f"<td>{c}</td>" for c in _cells) + "</tr>")
    mo.vstack([
        mo.Html(f"<table><thead><tr>{_head}</tr></thead><tbody>{''.join(_body)}</tbody></table>"),
        mo.md(
            f"""
    **Highlighted:** the expected battery life, with the firmware's abort level
    ({PVD_ABORT_FIRMWARE}) and typical capacitor leakage.

    Assumes {PRESSES_PER_DAY} presses/day, each a frame plus {REPEATS_PER_PRESS}
    repeats, all at the stated temperature. Fixed drains: standby
    {standby_mah_per_year:.1f} mAh/year, self-discharge
    {self_discharge_mah_per_year:.1f} mAh/year, capacitor leakage at spec max
    {i_leak_spec * 1e6:.1f} µA ({i_leak_spec * 8760 * 1e3:.0f} mAh/year).
    """
        ),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Sweep: R8 and LED reservoir size

    The LED reservoir sags through each frame, so late pulses are weaker than
    the first. More capacitance (more 100 µF parts in parallel) or a smaller R8
    flattens it. But a smaller R8 lets the LED pull harder on the cell, which
    drags VDD down and ends the cell's useful life sooner, especially when
    cold.

    For each combination, the sweep simulates one NEC frame across the cell's
    life and reports:

    - **weakest-pulse range**: range of the weakest pulse in a frame from a
      fresh cell at 21 °C, relative to a 100 mA pulse (√I scaling)
    - **usable capacity** at 21 °C and 0 °C, with the 2.08 V abort level

    The current design (R8 = 47 Ω, 3 caps) is outlined.
    """)
    return


@app.cell
def _(
    C4_C6_DC_BIAS_FACTOR,
    CASES,
    I_RUN,
    OCV_CAP_MAH,
    PRESS_WINDOWS,
    PVD_TX_OK,
    cell_model,
    led_current,
    np,
    simulate,
):
    R8_SWEEP = np.array([10, 15, 22, 33, 47, 68, 100])
    N_CAPS_SWEEP = np.arange(1, 7)  # 100 uF 1206 parts in parallel
    SWEEP_ABORT_V = 2.08

    sweep = {}
    for _name, _p in CASES.items():
        _life = np.arange(0.0, OCV_CAP_MAH[-1] * _p["cap_scale"], 1.0)
        _voc, _rint = cell_model(_life, _p["cap_scale"], _p["ocv_offset"], _p["ir_scale"])
        _shape = (len(R8_SWEEP), len(N_CAPS_SWEEP), len(_life))
        _r8 = np.broadcast_to(R8_SWEEP[:, None, None], _shape).ravel()
        _c = np.broadcast_to(N_CAPS_SWEEP[None, :, None] * 100e-6 * C4_C6_DC_BIAS_FACTOR, _shape).ravel()
        _v = np.broadcast_to(_voc, _shape).ravel()
        _r = np.broadcast_to(_rint, _shape).ravel()
        # One frame is the worst case; repeats are shorter
        _vdd_min, _vled_min, _ = simulate(_v, _r, _p["vf_shift"], PRESS_WINDOWS[:1], r8=_r8, c_led=_c)
        _vdd_min = _vdd_min.reshape(_shape)
        _vled_min = _vled_min.reshape(_shape)
        _vdd_rest = np.broadcast_to(_voc - I_RUN * _rint, _shape)

        _dead = (_vdd_rest < PVD_TX_OK) | (_vdd_min < SWEEP_ABORT_V)
        _usable = np.where(_dead.any(axis=2), _life[np.argmax(_dead, axis=2)], _life[-1])
        _i_weak = led_current(_vled_min[:, :, 0], _p["vf_shift"])
        sweep[_name] = {
            "usable_mah": _usable,
            "weak_range": np.sqrt(_i_weak / 0.1),
            "weak_ma": _i_weak * 1e3,
        }
    return N_CAPS_SWEEP, R8_SWEEP, SWEEP_ABORT_V, sweep


@app.cell(hide_code=True)
def _(N_CAPS_SWEEP, R8, R8_SWEEP, SWEEP_ABORT_V, plt, sweep):
    _panels = [
        ("Weakest-pulse range, fresh cell, 21 °C\n(vs 100 mA pulse)", sweep["21 °C"]["weak_range"], "{:.2f}", "viridis"),
        (f"Usable capacity, 21 °C (mAh)\nabort {SWEEP_ABORT_V} V", sweep["21 °C"]["usable_mah"], "{:.0f}", "magma"),
        (f"Usable capacity, 0 °C (mAh)\nabort {SWEEP_ABORT_V} V", sweep["0 °C"]["usable_mah"], "{:.0f}", "magma"),
    ]
    _fig, _axes = plt.subplots(1, 3, figsize=(13, 4.4))
    _r8_i = list(R8_SWEEP).index(int(R8))
    for _ax, (_title, _data, _fmt, _cmap) in zip(_axes, _panels):
        _ax.imshow(_data.T, origin="lower", cmap=_cmap, aspect="auto")
        for _i in range(len(R8_SWEEP)):
            for _j in range(len(N_CAPS_SWEEP)):
                _ax.text(_i, _j, _fmt.format(_data[_i, _j]), ha="center", va="center", fontsize=8,
                         color="w" if _data[_i, _j] < (_data.min() + _data.max()) / 2 else "k")
        _ax.add_patch(plt.Rectangle((_r8_i - 0.5, 3 - 1 - 0.5), 1, 1, fill=False, ec="red", lw=2))
        _ax.set_xticks(range(len(R8_SWEEP)), [f"{r:g}" for r in R8_SWEEP])
        _ax.set_yticks(range(len(N_CAPS_SWEEP)), [str(n) for n in N_CAPS_SWEEP])
        _ax.set_xlabel("R8 (Ω)")
        _ax.set_ylabel("100 µF caps in reservoir")
        _ax.set_title(_title, fontsize=10)
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(N_CAPS_SWEEP, R8_SWEEP, mo, sweep):
    _candidates = [
        (47, 3, "current design"),
        (22, 3, "smaller R8, no extra parts"),
        (22, 4, "one more cap, smaller R8"),
        (47, 5, "two more caps, same R8"),
        (10, 1, "almost straight off the cell"),
    ]
    _rows = []
    for _r8, _n, _note in _candidates:
        _i, _j = list(R8_SWEEP).index(_r8), list(N_CAPS_SWEEP).index(_n)
        _rows.append(
            f"| {_r8} Ω | {_n} | {_note} | {sweep['21 °C']['weak_ma'][_i, _j]:.0f} mA "
            f"({sweep['21 °C']['weak_range'][_i, _j]:.2f}) | {sweep['21 °C']['usable_mah'][_i, _j]:.0f} "
            f"| {sweep['0 °C']['usable_mah'][_i, _j]:.0f} |"
        )
    _table = "\n".join(_rows)
    mo.md(
        f"""
    | R8 | Caps | | Weakest pulse, fresh 21 °C (range) | Usable 21 °C (mAh) | Usable 0 °C (mAh) |
    |---|---|---|---|---|---|
    {_table}

    The first pulse of every frame is the same (~100 mA fresh) in all cases.
    Only the tail of the frame changes.
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Caveats

    - **Chart data is read by eye.** The end-of-life point sits on the steep
      part of the internal-resistance curve, so ±5 mAh of reading error moves
      it by about the same.
    - **The cold model is part measured, part assumed.** The capacity and
      voltage shifts come from Energizer's 1 mA curves. The ×2 on internal
      resistance is an assumption; below 0 °C it will be worse.
    - **No margin on the PVD levels.** The datasheet gives typical thresholds
      only.
    - **Capacitor leakage is the big unknown.** At the guaranteed minimum it
      would dominate everything else and cut life to a year or two. Real parts
      are usually far better, but the spec doesn't promise it. If a prototype
      shows µA-level leakage, a P-FET to disconnect C4–C6 in standby fixes it.
    - **Shelf life caps it anyway.** Energizer quotes a 10-year shelf life, so
      treat anything past ~10 years as "the battery lasts as long as a CR2032
      can".
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Appendix: one button press in time

    **NEC timing.** A full frame is a 9 ms leader burst, a 4.5 ms space,
    32 bits and a 562.5 µs stop burst: 68.1 ms, the same for every code
    because each byte is sent with its inverse. Each bit is a 562.5 µs burst
    followed by a 562.5 µs space (0) or a 1687.5 µs space (1). While the
    button stays held, repeat codes (9 ms burst, 2.25 ms space, 562.5 µs
    burst = 11.8 ms) follow. Every transmission starts on a **108 ms** grid,
    start to start. That leaves ~39.9 ms of silence after the full frame
    and ~96.2 ms between repeats.

    | Element | Burst | Space | Total |
    |---|---|---|---|
    | Leader | 9 ms | 4.5 ms | 13.5 ms |
    | Bit 0 / bit 1 | 562.5 µs | 562.5 µs / 1687.5 µs | 1.125 / 2.25 ms |
    | Full frame (incl. stop burst) | | | 68.1 ms |
    | Repeat code | 9 ms + 562.5 µs | 2.25 ms | 11.8 ms |
    | Frame / repeat period | | | 108 ms |

    Below is a typical press (the full frame plus the repeats assumed in the
    usage model) from a cell at **0 °C, halfway through its usable life**.
    The 38 kHz carrier isn't drawn. LED current is the height of each carrier
    pulse; the average during a burst is a third of that.
    """)
    return


@app.cell
def _(
    CARRIER_DUTY,
    CASES,
    C_LED,
    C_VDD,
    I_RUN,
    NEC_REPEAT_PERIOD_S,
    PVD_ABORT_FIRMWARE,
    R8,
    REPEATS_PER_PRESS,
    cell_model,
    led_current,
    nec_frame,
    nec_repeat,
    np,
    pad_to_period,
    results,
):
    TRACE_CASE = "0 °C"
    _p = CASES[TRACE_CASE]
    _usable = next(
        r["usable_mah"]
        for r in results
        if r["case"] == TRACE_CASE and r["abort"] == PVD_ABORT_FIRMWARE and r["leakage"] == "typical"
    )
    trace_life_mah = 0.5 * _usable
    _voc, _rint = cell_model(np.array([trace_life_mah]), _p["cap_scale"], _p["ocv_offset"], _p["ir_scale"])
    _voc, _rint = float(_voc[0]), float(_rint[0])

    # Same supply model as simulate(), but for one life point, recording every step
    _segs = pad_to_period(nec_frame(0x02))
    for _ in range(REPEATS_PER_PRESS):
        _segs += pad_to_period(nec_repeat(), NEC_REPEAT_PERIOD_S)
    _dt = 10e-6
    _vdd = _vled = _voc
    _t, _mark, _vdd_t, _vled_t, _ipk_t = [], [], [], [], []
    _now = 0.0
    for _duration, _is_mark in _segs:
        for _ in range(int(round(_duration / _dt))):
            _ipk = float(led_current(np.array([_vled]), _p["vf_shift"])[0]) if _is_mark else 0.0
            _i_cell = (_voc - _vdd) / _rint
            _i_r8 = (_vdd - _vled) / R8
            _vdd += (_i_cell - _i_r8 - I_RUN) * _dt / C_VDD
            _vled += (_i_r8 - CARRIER_DUTY * _ipk) * _dt / C_LED
            _t.append(_now)
            _mark.append(_is_mark)
            _vdd_t.append(_vdd)
            _vled_t.append(_vled)
            _ipk_t.append(_ipk)
            _now += _dt
    trace = {
        "t_ms": np.array(_t) * 1e3,
        "mark": np.array(_mark, dtype=float),
        "vdd": np.array(_vdd_t),
        "vled": np.array(_vled_t),
        "i_pk_ma": np.array(_ipk_t) * 1e3,
        "voc": _voc,
        "rint": _rint,
    }
    return TRACE_CASE, trace, trace_life_mah


@app.cell(hide_code=True)
def _(PVD_ABORT_OPTIONS, PVD_ABORT_FIRMWARE, TRACE_CASE, plt, trace, trace_life_mah):
    _fig, (_a1, _a2, _a3) = plt.subplots(
        3, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1, 2, 2]}
    )
    _t = trace["t_ms"]
    _a1.fill_between(_t, 0, trace["mark"], step="post", color="tab:purple", lw=0)
    _a1.set_yticks([0, 1], ["off", "38 kHz"])
    _a1.set_ylim(-0.1, 1.3)
    _a1.set_title(
        f"One press, {TRACE_CASE}, {trace_life_mah:.0f} mAh used "
        f"(OCV {trace['voc']:.2f} V, internal resistance {trace['rint']:.0f} Ω)"
    )
    _a1.annotate("full frame", (2, 1.05), fontsize=8)
    for _k, _x in enumerate([108, 216, 324]):
        _a1.annotate(f"repeat {_k + 1}", (_x + 1, 1.05), fontsize=8)

    _a2.plot(_t, trace["vdd"], label="VDD (MCU)")
    _a2.plot(_t, trace["vled"], label="VLED (C4–C6 reservoir)")
    _a2.axhline(PVD_ABORT_OPTIONS[PVD_ABORT_FIRMWARE], color="tab:orange", ls="--", lw=1,
                label=f"Abort level {PVD_ABORT_FIRMWARE} (checked on VDD)")
    _a2.set_ylabel("Voltage (V)")
    _a2.legend(fontsize=8, loc="lower right")
    _a2.grid(alpha=0.3)

    _a3.plot(_t, trace["i_pk_ma"], color="tab:red", lw=0.8)
    _a3.set_ylabel("LED pulse current (mA)")
    _a3.set_xlabel("Time from start of first frame (ms); boot + debounce (~17 ms) come before this")
    _a3.set_ylim(0, max(110, trace["i_pk_ma"].max() * 1.1))
    _a3.grid(alpha=0.3)
    for _ax in (_a1, _a2, _a3):
        for _x in (108, 216, 324):
            _ax.axvline(_x, color="0.6", lw=0.6, ls=":")
    _fig.tight_layout()
    _fig
    return

@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Appendix B: choosing R7

    The single-press trace shows the LED current falling from ~86 mA to
    ~42 mA during the 9 ms leader, as the reservoir drains. Would a bigger R7
    help? It lowers the first pulse, but it also drains the reservoir more
    slowly. The question is which R7 gives the strongest *weakest* pulse,
    since that pulse limits range. In a press it's the end of the leader.

    ### Model

    During one burst of length $T$, take:

    - **Source.** The cell and R8 form a Thévenin source:
      $U_0 = V_{oc} - R_{int} I_{run}$ behind $R_s = R_{int} + R_8$. VDD's own
      10 µF is ignored (its time constant is ~0.2 ms, much less than $T$).
    - **LED.** Linearised as $V_F + r_d I$ around the operating point. The
      pulse path is $R = R_7 + R_{DS(on)} + r_d$.
    - **Carrier.** With duty $d$, the reservoir $C$ supplies an average of
      $d\,i$, where $i$ is the pulse current.

    With $x = v_{LED} - V_F$ and $U = U_0 - V_F$:

    $$C\,\dot x = \frac{U - x}{R_s} - \frac{d\,x}{R}, \qquad x(0) = U \;\text{(rested)}$$

    which is first order, so

    $$x(t) = x_\infty + (U - x_\infty)\,e^{-t/\tau},\qquad
    x_\infty = U\frac{R}{R + a},\qquad \tau = C\,\frac{R_s R}{R + a},\qquad a = d\,R_s$$

    and the pulse current $i = x/R$ is

    $$\boxed{\,i(t) = \frac{U}{R + a}\left[\,1 + \frac{a}{R}\,e^{-t/\tau}\right]}$$

    ### Limits: a smaller R7 wins

    - First pulse: $i(0) = U/R$.
    - A very long burst: $i(\infty) = U/(R + a)$.

    Both strictly decrease with $R$. So for very short or very long bursts,
    a smaller R7 is always better, and making R7 *bigger* can't help.

    ### Finite burst: an optimum exists, but has no closed form

    Substitute $s = 1/R$. Then $T/\tau = k + \beta s$ with
    $k = T/(C R_s)$ and $\beta = d\,T/C$, giving

    $$\frac{i(T)}{U} = \frac{s}{1 + a s}\left[\,1 + a\,e^{-k}\, s\, e^{-\beta s}\right]$$

    $$\frac{\partial}{\partial s}\frac{i(T)}{U} =
    \frac{1 + a\,e^{-k}\, s\, e^{-\beta s}\big[(2 - \beta s)(1 + a s) - a s\big]}{(1 + a s)^2}$$

    The optimum is where the numerator is zero. That equation mixes a
    polynomial with $e^{-\beta s}$, and the quadratic factor stops it reducing
    to the Lambert W function. **There's no elementary closed form for the
    optimal R7**, but it's a trivial one-dimensional numerical solve.

    ### Closed-form bounds

    1. **Optimum is below $R_{crit}$.** A root needs the bracket to be
       negative, i.e. $2 + (a - \beta)s - a\beta s^2 < 0$. In terms of $R$:

       $$R_{opt} < R_{crit} = \frac{\beta - a + \sqrt{(a - \beta)^2 + 8 a \beta}}{4}$$

       Above $R_{crit}$, a smaller R7 always gives a stronger weakest pulse.
       $\beta = dT/C$ is the resistance at which the reservoir would drain in
       about one burst.

    2. **Pulse-current limit.** A fresh cell (up to ~3.2 V open-circuit,
       handbook p3/p5) must not push the first pulse past the TSAL6200's
       200 mA peak rating:

       $$R_7 \ge R_{FM} = \frac{V_{max} - V_F(I_{FM})}{I_{FM}} - R_{DS(on)}$$

    So the best R7 is $\max\!\big(R_{FM},\; R_{opt}\big)$ with
    $R_{opt} < R_{crit}$. It also costs battery: a smaller R7 draws more
    charge per press and sags VDD further. That's checked against the full
    nonlinear simulation below.

    **Decision:** R7 stays at 15 Ω for now. 10 Ω would give ~12 % stronger
    weakest pulses (~6 % more range) for ~1–1.5 years less calculated life,
    still above the cell's 10-year shelf life.
    """)
    return


@app.cell
def _(C_LED, CARRIER_DUTY, I_RUN, Q1_RDS, R8, led_vf, np):
    T_LEADER_S = 9e-3
    LED_I_FM = 0.200  # TSAL6200 peak forward current (tp/T = 0.5, tp = 100 us)
    V_FRESH_MAX = 3.2  # fresh CR2032 OCV before first load (handbook p3/p5)

    # LED linearised through the 30 mA and 100 mA datasheet points
    _i1, _i2 = 0.030, 0.100
    R_D = (led_vf(_i2) - led_vf(_i1)) / (_i2 - _i1)
    V_F0 = led_vf(_i1) - R_D * _i1

    def i_burst(t, r7, voc, rint, vf_shift=0.0):
        """Closed-form pulse current after t seconds of a burst (A)."""
        u = voc - rint * I_RUN - (V_F0 + vf_shift)
        rs = rint + R8
        r = r7 + Q1_RDS + R_D
        a = CARRIER_DUTY * rs
        tau = C_LED * rs * r / (r + a)
        return u / (r + a) * (1 + a / r * np.exp(-t / tau))

    def r_crit(rint):
        """Upper bound on the optimal total pulse-path resistance R (Ohm)."""
        a = CARRIER_DUTY * (rint + R8)
        beta = CARRIER_DUTY * T_LEADER_S / C_LED
        return (beta - a + np.sqrt((a - beta) ** 2 + 8 * a * beta)) / 4

    def r7_opt_numeric(voc, rint, vf_shift=0.0):
        """Numerical maximiser of the end-of-leader current over R7."""
        r7 = np.linspace(0.5, 60, 4000)
        return r7[np.argmax(i_burst(T_LEADER_S, r7, voc, rint, vf_shift))]

    R7_FM = (V_FRESH_MAX - led_vf(LED_I_FM)) / LED_I_FM - Q1_RDS
    return (
        LED_I_FM,
        R7_FM,
        R_D,
        T_LEADER_S,
        V_F0,
        V_FRESH_MAX,
        i_burst,
        r7_opt_numeric,
        r_crit,
    )


@app.cell
def _(
    CASES,
    I_RUN,
    MAH,
    OCV_CAP_MAH,
    PRESSES_PER_DAY,
    PRESS_WINDOWS,
    PVD_ABORT_FIRMWARE,
    PVD_ABORT_OPTIONS,
    PVD_TX_OK,
    REPEATS_PER_PRESS,
    cell_model,
    led_current,
    np,
    self_discharge_mah_per_year,
    simulate,
    standby_mah_per_year,
    t_awake,
):
    R7_SWEEP = np.array([4.7, 6.8, 8.2, 10, 12, 15, 18, 22, 27, 33])
    _abort_v = PVD_ABORT_OPTIONS[PVD_ABORT_FIRMWARE]

    r7_sweep = {}
    for _name, _p in CASES.items():
        _life = np.arange(0.0, OCV_CAP_MAH[-1] * _p["cap_scale"], 2.0)
        _voc, _rint = cell_model(_life, _p["cap_scale"], _p["ocv_offset"], _p["ir_scale"])
        _vdd_rest = _voc - I_RUN * _rint
        _rows = []
        for _r7 in R7_SWEEP:
            _vdd_min, _vled_min, _q = simulate(_voc, _rint, _p["vf_shift"], PRESS_WINDOWS, r7=_r7)
            _dead = (_vdd_rest < PVD_TX_OK) | (_vdd_min < _abort_v)
            _usable = _life[np.argmax(_dead)] if _dead.any() else _life[-1]
            _half = np.argmin(np.abs(_life - _usable / 2))
            _q_press = _q[0][0] + REPEATS_PER_PRESS * np.mean([_w[0] for _w in _q[1:]]) + I_RUN * t_awake
            _per_year = PRESSES_PER_DAY * 365 * _q_press / MAH + standby_mah_per_year + self_discharge_mah_per_year
            _rows.append(
                {
                    "r7": _r7,
                    "usable_mah": _usable,
                    "years": _usable / _per_year,
                    "first_ma_fresh": 1e3 * led_current(_vdd_rest[:1], _p["vf_shift"], _r7)[0],
                    "weak_ma_half": 1e3 * led_current(_vled_min[_half : _half + 1], _p["vf_shift"], _r7)[0],
                    "voc_half": _voc[_half],
                    "rint_half": _rint[_half],
                }
            )
        r7_sweep[_name] = _rows
    return R7_SWEEP, r7_sweep


@app.cell(hide_code=True)
def _(
    CASES,
    LED_I_FM,
    R7,
    R7_FM,
    R_D,
    Q1_RDS,
    T_LEADER_S,
    V_FRESH_MAX,
    i_burst,
    np,
    plt,
    r7_opt_numeric,
    r7_sweep,
    r_crit,
):
    _fig, (_ax1, _ax2) = plt.subplots(1, 2, figsize=(12, 4.4))
    _r7 = np.linspace(2, 40, 300)
    for (_name, _rows), _col in zip(r7_sweep.items(), ["tab:blue", "tab:green"]):
        _voc, _rint = _rows[0]["voc_half"], _rows[0]["rint_half"]
        _shift = CASES[_name]["vf_shift"]
        _ax1.plot(_r7, 1e3 * i_burst(T_LEADER_S, _r7, _voc, _rint, _shift), color=_col,
                  label=f"{_name}, half life: closed form")
        _ax1.plot([r["r7"] for r in _rows], [r["weak_ma_half"] for r in _rows], "o", color=_col,
                  label=f"{_name}, half life: full simulation (weakest pulse)")
        _ropt = r7_opt_numeric(_voc, _rint, _shift)
        _ax1.axvline(_ropt, color=_col, ls=":", lw=1)
        _ax1.axvline(r_crit(_rint) - Q1_RDS - R_D, color=_col, ls="-.", lw=1)
    _ax1.axvspan(0, R7_FM, color="tab:red", alpha=0.12, label=f"R7 < R_FM: first pulse > {LED_I_FM * 1e3:.0f} mA at {V_FRESH_MAX} V")
    _ax1.axvline(R7, color="k", lw=1, label=f"Current R7 = {R7:g} Ω")
    _ax1.set_xlabel("R7 (Ω)")
    _ax1.set_ylabel("End-of-leader pulse current (mA)")
    _ax1.set_title("Weakest pulse vs R7 (dotted: optimum, dash-dot: R_crit)", fontsize=10)
    _ax1.set_xlim(2, 40)
    _ax1.grid(alpha=0.3)
    _ax1.legend(fontsize=7)

    for (_name, _rows), _col in zip(r7_sweep.items(), ["tab:blue", "tab:green"]):
        _ax2.plot([r["r7"] for r in _rows], [r["years"] for r in _rows], "o-", color=_col, label=f"Years, {_name}")
    _ax2.axvspan(0, R7_FM, color="tab:red", alpha=0.12)
    _ax2.axvline(R7, color="k", lw=1)
    _ax2.set_xlabel("R7 (Ω)")
    _ax2.set_ylabel("Battery life (years, typical leakage)")
    _ax2.set_title("Battery life vs R7", fontsize=10)
    _ax2.set_xlim(2, 40)
    _ax2.grid(alpha=0.3)
    _ax2.legend(fontsize=8)
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(LED_I_FM, R7, R7_FM, R_D, V_F0, mo, r7_sweep):
    _hdr = "| R7 | First pulse, fresh 21 °C | Weakest pulse, half life 21 °C | Weakest pulse, half life 0 °C | Years 21 °C | Years 0 °C |"
    _rows = []
    for _a, _b in zip(r7_sweep["21 °C"], r7_sweep["0 °C"]):
        _mark = " ◀ current" if _a["r7"] == R7 else ""
        _warn = " ⚠" if _a["first_ma_fresh"] > LED_I_FM * 1e3 * 0.9 else ""
        _rows.append(
            f"| {_a['r7']:g} Ω{_mark} | {_a['first_ma_fresh']:.0f} mA{_warn} | {_a['weak_ma_half']:.0f} mA "
            f"| {_b['weak_ma_half']:.0f} mA | {_a['years']:.1f} | {_b['years']:.1f} |"
        )
    _body = "\n".join(_rows)
    mo.md(
        f"""
    {_hdr}
    |---|---|---|---|---|---|
    {_body}

    The first pulse here is at the fresh cell's loaded OCV. A brand-new cell
    can briefly sit at ~3.2 V, which is what $R_{{FM}}$ = {R7_FM:.1f} Ω
    guards against. ⚠ = within 10 % of the 200 mA rating. LED linearisation:
    $V_F$ = {V_F0:.2f} V + {R_D:.2f} Ω × I.
    """
    )
    return

if __name__ == "__main__":
    app.run()
