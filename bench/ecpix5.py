#!/usr/bin/env python3

#
# This file is part of LiteCAN and derived form LiteScope.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

# Use:
# ./ecpix5.py --build --load
# lxserver --udp (for LiteScope over UDP)
# litescope_cli --help: list the available trigger option.

# TODO: move to bench subdir when litecan is installed properly

import os
import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.lattice.trellis import trellis_args, trellis_argdict
from litex.soc.integration.builder import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.cores.pdm import PDM

from litex_boards.platforms import ecpix5
from litex_boards.targets.ecpix5 import *

from litescope import LiteScopeAnalyzer
from litecan.ctucanfd import CTUCANFD


# LiteScopeSoC -------------------------------------------------------------------------------------
bench_io = [
    ("can", 0,
        Subsignal("tx", Pins("pmod3:6")),
        Subsignal("rx", Pins("pmod3:2")),
        IOStandard("LVCMOS33")
     ),
    ("pdm", 0, Pins("pmod3:0"), IOStandard("LVCMOS33")),
    ("pdm", 1, Pins("pmod3:1"), IOStandard("LVCMOS33")),
]

class LiteScopeSoC(BaseSoC):
    def __init__(self, **kwargs):
        platform = ecpix5.Platform(device="45F", toolchain="trellis", name="ecpix_pdm_canfd")
        platform.add_extension(bench_io)

        # take over some resources so they are not used in the default way by BaseSoC
        pdm0_led = platform.request("rgb_led", 0)
        pdm1_led = platform.request("rgb_led", 1)

        # BaseSoC ----------------------------------------------------------------------------------
        BaseSoC.__init__(self,
            platform = platform,
            sys_clk_freq = int(50e6),
            with_etherbone      = True,
            cpu_type =          "None",
            device =            "45F",
            **kwargs
        )

        # Disable R&B Leds.
        self.comb += [getattr(pdm0_led, n).eq(1) for n in "rb"]
        self.comb += [getattr(pdm1_led, n).eq(1) for n in "rb"]

        # counter for PDM and analyser
        count = Signal(8)
        self.sync += count.eq(count + 1)

        self.pdm0_dac = pdm0_dac = Signal(6)
        self.sync += If(count == 0, pdm0_dac.eq(pdm0_dac + 1))

        # pdm0 has supplied counter and duty (6bit). Runs at sys_clk
        pdm0_pad = platform.request("pdm", 0, loose=True)
        if pdm0_pad is not None:
            self.submodules.pdm0 = PDM(bits_or_duty=self.pdm0_dac, counter=count)
            self.comb += [
                pdm0_pad.eq(self.pdm0.out),
                pdm0_led.g.eq(~self.pdm0.out),
            ]

        # pdm1 has internally generated counter, CSR for duty and runs at 100MHz
        pdm1_pad = platform.request("pdm", 1, loose=True)
        if pdm1_pad is not None:
            self.submodules.pdm1 = PDM(bits_or_duty=8, out=pdm1_pad)
            ClockDomainsRenamer("por")(self.pdm1)
            self.pdm1.add_csr()
            self.comb += [
                pdm1_led.g.eq(~pdm1_pad),
            ]

        can_pads = platform.request("can", loose=True)
        if can_pads is not None:
            name = "ctu_can_fd0"
            self.mem_map[name] = 0x03000000
            can = CTUCANFD(self.platform, pads=can_pads, timestamp=count)
            setattr(self.submodules, name, can)
            if self.irq.enabled:
                self.add_interrupt(name)
            self.bus.add_slave(name, can.bus, SoCRegion(origin=self.mem_map[name], size=65536, mode="rw", cached=False))
            self.add_csr("can")

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
