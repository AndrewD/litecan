#!/usr/bin/env python3

import sys
import argparse

from migen import *
from migen.genlib.misc import WaitTimer

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.common import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import *
from litex.soc.interconnect import wishbone

from ctucanfd import CTUCANFD

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

        # CAN-FD Tester ----------------------------------------------------------------------------
        class CANFDTester(Module):
            def __init__(self, can):
                count  = Signal(8)
                offset = Signal(8)
                self.submodules.fsm = fsm = FSM(reset_state="IDLE")
                fsm.act("IDLE",
                    NextValue(count, count + 1),
                    If(count == 128,
                        NextState("DUMP")
                    )
                )
                fsm.act("DUMP",
                    can.bus.stb.eq(1),
                    can.bus.cyc.eq(1),
                    can.bus.adr.eq(offset),
                    If(can.bus.ack,
                        NextState("CHECK-UPDATE")
                    )
                )
                fsm.act("CHECK-UPDATE",
                    NextValue(offset, offset + 1),
                    If(offset == (64-1),
                        NextState("SET-TSTM")
                    ).Else(
                        NextState("DUMP")
                    )
                )
                fsm.act("SET-TSTM",
                    can.bus.stb.eq(1),
                    can.bus.cyc.eq(1),
                    can.bus.we.eq(1),
                    can.bus.sel.eq(0b1111),
                    can.bus.adr.eq(0x004 >> 2),
                    can.bus.dat_w.eq(0x02000210 | 0x100),
                    If(can.bus.ack,
                        NextState("WRITE-TEST-WDATA")
                    )
                )
                fsm.act("WRITE-TEST-WDATA",
                    can.bus.stb.eq(1),
                    can.bus.cyc.eq(1),
                    can.bus.we.eq(1),
                    can.bus.sel.eq(0b1111),
                    can.bus.adr.eq(0x908 >> 2),
                    can.bus.dat_w.eq(0x5aa55aa5),
                    If(can.bus.ack,
                        NextState("READ-TEST-RDATA")
                    )
                )
                fsm.act("READ-TEST-RDATA",
                    can.bus.stb.eq(1),
                    can.bus.cyc.eq(1),
                    can.bus.adr.eq(0x908 >> 2),
                    If(can.bus.ack,
                        NextState("DONE")
                    )
                )
                fsm.act("DONE")

                # Dump Display.
                self.sync += If(can.bus.stb & can.bus.ack,
                    Display("Addr: %08x / RD-Data: %08x / WR-DATA: %08x / WR: %d",
                        can.bus.adr,
                        can.bus.dat_r,
                        can.bus.dat_w,
                        can.bus.we,
                ))

                # Finish when Dump Done.
                finish_timer = WaitTimer(10000)
                self.submodules += finish_timer
                self.comb += finish_timer.wait.eq(fsm.ongoing("DONE"))
                self.sync += If(finish_timer.done, Finish())

        self.submodules.can_fd_tester = CANFDTester(self.can)

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
        trace            = True,
    )

if __name__ == "__main__":
    main()
