

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

### [> Build ECPIX5 Design:

    ./ecpix.py --build --load
