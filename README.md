

      _____________  __  ________   _  __    _______      __  __   _ __      _  __
     / ___/_  __/ / / / / ___/ _ | / |/ /___/ __/ _ \   _/_/ / /  (_) /____ | |/_/
    / /__  / / / /_/ / / /__/ __ |/    /___/ _// // / _/_/  / /__/ / __/ -_)>  <
    \___/ /_/  \____/  \___/_/ |_/_/|_/   /_/ /____/ /_/   /____/_/\__/\__/_/|_|
           Integration test of the CTU CAN-FD Core with LiteX for MoTeC.


[> Intro
--------

This project aims to test the CTU CAN-FD integrated with LiteX.

[> Getting started
------------------
### [> Installing LiteX:

LiteX can be installed by following the installation instructions from the LiteX Wiki: https://github.com/enjoy-digital/litex/wiki/Installation

[> Build and Test the design(s)
---------------------------------

### [> Run Simulation:

    ./sim.py
    vcd2fst -v build/sim/gateware/sim.vcd -f build/sim/gateware/sim.fst
    gtkwave build/sim/gateware/sim.fst

### [> Build included bench test example designs:

    % path/to/ecpix5.py --build --load
    % path/to/bench/xyloni.py --build --flash --with-can
    % litex_term /dev/ttyUSB3

```
       / /  (_) /____ | |/_/
      / /__/ / __/ -_)>  <
     /____/_/\__/\__/_/|_|
   Build your hardware, easily!

 (c) Copyright 2012-2022 Enjoy-Digital
 (c) Copyright 2007-2015 M-Labs

 BIOS built on Mar 21 2022 16:28:39
 BIOS CRC passed (5fa3bd4b)

 Migen git sha1: ac70301
 LiteX git sha1: f565bec7

--=============== SoC ==================--
CPU:		VexRiscv_Min @ 33MHz
BUS:		WISHBONE 32-bit @ 4GiB
CSR:		32-bit data
ROM:		32KiB
SRAM:		2KiB
FLASH:		16384KiB

--========== Initialization ============--

Initializing W25Q128JV SPI Flash @0x00000000...
SPI Flash clk configured to 16 MHz
Memspeed at 0 (Sequential, 4.0KiB)...
   Read speed: 350.0KiB/s
Memspeed at 0 (Random, 4.0KiB)...
   Read speed: 3.2KiB/s

--============== Boot ==================--
Booting from serial...
Press Q or ESC to abort boot completely.
sL5DdSMmkekro
Timeout
No boot medium found

--============= Console ================--

litex> mem_list

Available memory regions:
SRAM      0x10000000 0x800
SPIFLASH  0x00000000 0x1000000
ROM       0x00040000 0x8000
CTU_CAN_FD0  0x80000000 0x1000
CSR       0xf0000000 0x10000

litex> mem_read 0x80000000 0x100

Memory dump:
0x80000000  fd ca 04 02 10 02 00 02 84 00 02 00 00 00 00 00  ................
0x80000010  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x80000020  00 00 00 00 85 a1 50 10 83 61 20 10 60 80 04 00  ......P..a .`...
0x80000030  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x80000040  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x80000050  00 00 00 00 00 00 00 00 00 00 00 00 0f 00 00 00  ................
0x80000060  20 00 20 00 00 00 00 00 01 00 00 00 00 00 00 00   . .............
0x80000070  88 00 00 00 00 00 02 00 01 00 00 00 1f 00 00 00  ................
0x80000080  00 00 0a 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x80000090  ef be ad de 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x800000a0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x800000b0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x800000c0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x800000d0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x800000e0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0x800000f0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
```

### [> Build for linux:
    ./make.py --board=ecpix5 --build --load
