#ifndef _FUNCONFIG_H
#define _FUNCONFIG_H

// Run straight from the 8 MHz HSI, no PLL. Plenty for generating the carrier
// and keeps the awake current down.
#define FUNCONF_USE_HSI 1
#define FUNCONF_USE_PLL 0
#define FUNCONF_SYSTEM_CORE_CLOCK 8000000
// Unused with the PLL off, but ch32l103hw.h errors on the default of 1
#define FUNCONF_PLL_MULTIPLIER 2

#endif
