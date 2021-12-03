#!/usr/bin/env python3

import sys
import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.common import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import *

from litecan.ctucanfd import CTUCANFD

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk/Rst.
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),

    # CAN-FD.
    ("can", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _io)

# Simulation SoC -----------------------------------------------------------------------------------

class SimSoC(SoCMini):
    def __init__(self):
        platform     = Platform()
        sys_clk_freq = int(1e6)
        self.comb += platform.trace.eq(1)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # CAN-FD -----------------------------------------------------------------------------------
        self.submodules.can = CTUCANFD(self.platform, pads=platform.request("can"))
        self.bus.add_slave("can", self.can.bus, SoCRegion(origin=0x90000000, size=65536))

        # Finish -----------------------------------------------------------------------------------
        cycles = Signal(32)
        self.sync += cycles.eq(cycles + 1)
        self.sync += If(cycles == 1000,
            Display("-"*80),
            Display("Cycles: %d", cycles),
            Finish(),
        )

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX / CTU CAN-FD Minimal Simulation")
    args = parser.parse_args()

    sys_clk_freq = int(1e6)
    sim_config = SimConfig()
    sim_config.add_clocker("sys_clk", freq_hz=sys_clk_freq)

    # SoC ------------------------------------------------------------------------------------------
    soc = SimSoC()

    # Build/Run ------------------------------------------------------------------------------------
    builder = Builder(soc)
    builder.build(
        threads          = 1,
        sim_config       = sim_config,
        opt_level        = "O0",
        trace            = True
    )

if __name__ == "__main__":
    main()
