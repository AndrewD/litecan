#!/usr/bin/env python3

#
# This file is part of LiteCAN and derived from LiteScope.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

# Use:
# ./ecpix5.py --build --load
# lxserver --udp (for LiteScope over UDP)
# litescope_cli --help: list the available trigger option.

import os
import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.lattice.trellis import trellis_args, trellis_argdict
from litex.soc.integration.builder import *
from litex.soc.integration.soc import SoCRegion

from litex_boards.platforms import ecpix5
from litex_boards.targets.ecpix5 import *

from litescope import LiteScopeAnalyzer
from ctucanfd import CTUCANFD


# LiteScopeSoC -------------------------------------------------------------------------------------
bench_io = [
    ("can", 0,
        Subsignal("tx", Pins("pmod3:6")),
        Subsignal("rx", Pins("pmod3:2")),
        IOStandard("LVCMOS33")
     ),
]

class LiteScopeSoC(BaseSoC):
    def __init__(self, **kwargs):

        # BaseSoC ----------------------------------------------------------------------------------
        BaseSoC.__init__(self,
            with_etherbone      = True,
            device =            "45F",
            **kwargs
        )
        self.platform.add_extension(bench_io)

        # counter for analyser
        count = Signal(8)
        self.sync += count.eq(count + 1)

        can_pads = self.platform.request("can", loose=True)
        if can_pads is not None:
            name = "ctu_can_fd0"
            can = CTUCANFD(self.platform, pads=can_pads, timestamp=count)
            setattr(self.submodules, name, can)
            if self.irq.enabled:
                self.add_interrupt(name)
            self.bus.add_slave(name, can.bus, SoCRegion(size=0x1000, cached=False))
            #self.add_csr("can")

        # LiteScope Analyzer -----------------------------------------------------------------------
        self.analyzer_signals = [
            can.bus,
            ResetSignal("sys"),
            count,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(self.analyzer_signals,
            depth        = 1024,
            clock_domain = "sys",
            register     = True,
            csr_csv      = "analyzer.csv")
        self.add_csr("analyzer")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SIM4 on ECPIX-5 with LiteScope")
    parser.add_argument("--build", action="store_true", help="Build bitstream")
    parser.add_argument("--load",  action="store_true", help="Load bitstream")
    parser.add_argument("--sys-clk-freq",    default=75e6, help="System clock frequency (default: 75MHz)")
    builder_args(parser)
    soc_core_args(parser)
    trellis_args(parser)
    args = parser.parse_args()
    builder_arguments = builder_argdict(args)
    if builder_arguments["csr_csv"] is None:
        builder_arguments["csr_csv"] = "csr.csv"

    soc     = LiteScopeSoC(**soc_core_argdict(args))
    builder = Builder(soc, **builder_arguments)
    builder.build(**trellis_argdict(args), run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
