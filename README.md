## Turbo Fan Remote

Simple coin cell powered IR remote control, designed to mount on some bike handlebars and control a fan.

Based on a CH32L103F8P6 as its cheap, supported by ch32v003fun, and much lower power in standby (0.4uA) than the CH32V003.

An experiment in using Claude for component choice, design calcs and analysis, see [calcs/battery_life.pdf](calcs/battery_life.pdf) for an example of the analysis to size the capacitor bank and estimate battery life.


### Status
[Code](fw/remote.c) done, [schematic](turbo_fan_remote.pdf) done, PCB layout, enclosure (handlebar mount 3D print), bringup and test TODO

### Requires
- Kicad 10
- uv (we use PEP 723 to install more dependencies as needed)
- RISC-V GCC toolchain. On macos I used the [official brew packages](https://github.com/riscv-software-src/homebrew-riscv)
- GNU make
- clang if you want IDE assistance through `make clangd`

### Building
```
git submodule update --init
cd fw
make flash # Builds and flashes code
make pdf # Makes PDFs of the schematic and calculations
```

### Credits
- Claude Opus 5.5: Code, component choices (apart from CH32L103), design calculations, schematics
- [mixelpixx/Konnect](https://github.com/mixelpixx/Konnect) for Claude to Kicad integration
- [cnhlohr/ch32fun](https://github.com/cnlohr/ch32fun) for the MCU libraries/build tools