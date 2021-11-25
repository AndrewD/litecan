#!/usr/bin/env python3

#
# This file depends on LiteX.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# This file is part of LiteCan.

import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import SoCRegion

from liteeth.phy.model import LiteEthPHYModel
from litecan import CTUCANFD

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("eth_clocks", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),
    ("eth", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),
    ("can", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),

]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM CAN", _io)

# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, **kwargs):
        platform     = Platform()
        sys_clk_freq = int(1e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteCAN bench Simulation",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # Etherbone --------------------------------------------------------------------------------
        self.submodules.ethphy = LiteEthPHYModel(self.platform.request("eth"))
        self.add_etherbone(phy=self.ethphy, buffer_depth=255)

        # SRAM -------------------------------------------------------------------------------------
        self.add_ram("sram", 0x20000000, 0x1000)

        can_pads = platform.request("can")
        if can_pads is not None:
            name = "ctu_can_fd0"
            self.mem_map[name] = 0x03000000
            can = CTUCANFD(self.platform, pads=can_pads)
            setattr(self.submodules, name, can)
            if self.irq.enabled:
                self.add_interrupt(name)
            self.bus.add_slave(name, can.bus, SoCRegion(origin=self.mem_map[name], size=65536, mode="rw", cached=False))
            self.add_csr("can")

# Main ---------------------------------------------------------------------------------------------

# Build --------------------------------------------------------------------------------------------

def generate_gtkw_savefile(builder, vns, trace_fst):
    from litex.build.sim import gtkwave as gtkw
    dumpfile = os.path.join(builder.gateware_dir, "sim.{}".format("fst" if trace_fst else "vcd"))
    savefile = os.path.join(builder.gateware_dir, "sim.gtkw")
    soc = builder.soc

    with gtkw.GTKWSave(vns, savefile=savefile, dumpfile=dumpfile) as save:
        save.clocks()
        save.fsm_states(soc)
        for s in soc.bus.slaves.keys():
            print(f"slaves: {s}")
        if "ctu_can_fd0" in soc.bus.slaves.keys():
            save.add(soc.bus.slaves["ctu_can_fd0"], mappers=[gtkw.wishbone_sorter(), gtkw.wishbone_colorer()])

def sim_args(parser):
    builder_args(parser)
    soc_core_args(parser)
    parser.add_argument("--trace",                action="store_true",     help="Enable Tracing")
    parser.add_argument("--trace-fst",            action="store_true",     help="Enable FST tracing (default=VCD)")
    parser.add_argument("--trace-start",          default="0",             help="Time to start tracing (ps)")
    parser.add_argument("--trace-end",            default="-1",            help="Time to end tracing (ps)")
    parser.add_argument("--sim-debug",            action="store_true",     help="Add simulation debugging modules")

def main():
    parser = argparse.ArgumentParser(description="LiteCAN Bench Simulation")
    sim_args(parser)
    args = parser.parse_args()

    soc_kwargs     = soc_core_argdict(args)
    builder_kwargs = builder_argdict(args)

    sim_config = SimConfig()
    sim_config.add_clocker("sys_clk", freq_hz=1e6)

    # Configuration --------------------------------------------------------------------------------

    sim_config.add_module("ethernet", "eth", args={"interface": "tap0", "ip": "192.168.1.100"})

    trace_start = int(float(args.trace_start))
    trace_end = int(float(args.trace_end))

    # SoC ------------------------------------------------------------------------------------------
    soc = BenchSoC(
        sim_debug          = args.sim_debug,
        **soc_kwargs)

    # Build/Run ------------------------------------------------------------------------------------
    def pre_run_callback(vns):
        if args.trace:
            generate_gtkw_savefile(builder, vns, args.trace_fst)

    builder_kwargs["csr_csv"] = "csr.csv"
    builder = Builder(soc, **builder_kwargs)
    builder.build(
        sim_config       = sim_config,
        trace            = args.trace,
        trace_fst        = args.trace_fst,
        trace_start      = trace_start,
        trace_end        = trace_end,
        pre_run_callback = pre_run_callback
    )

if __name__ == "__main__":
    main()
