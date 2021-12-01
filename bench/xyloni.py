#!/usr/bin/env python3

#
# Copyright (c) 2021 MoTeC
# SPDX-License-Identifier: BSD-2-Clause

# Use:
# ./xyloni.py --build --flash  --with-can --cpu-type=None --uart-name uartbone --integrated-sram-size 0

import os
import argparse

from litex.build.generic_platform import *

from litex_boards.targets.efinix_xyloni_dev_kit import *

from litecan.ctucanfd import CTUCANFD


# BenchSoC -------------------------------------------------------------------------------------
_io = [
    ("can", 0,
        Subsignal("tx", Pins("pmod:3")),
        Subsignal("rx", Pins("pmod:2")),
        IOStandard("3.3_V_LVTTL_/_LVCMOS")
     ),
]

class BenchSoC(BaseSoC):
    def __init__(self, with_can=False, **kwargs):

        # BaseSoC ----------------------------------------------------------------------------------
        BaseSoC.__init__(self,
            **kwargs
        )
        self.platform.add_extension(_io)

        can_pads = self.platform.request("can", loose=True) if with_can else None
        if can_pads is not None:
            name = "ctu_can_fd0"
            self.mem_map[name] = 0x90000000
            can = CTUCANFD(self.platform, pads=can_pads)
            setattr(self.submodules, name, can)
            if self.irq.enabled:
                self.add_interrupt(name)
            self.bus.add_slave(name, can.bus, SoCRegion(origin=self.mem_map[name], size=65536, mode="rw", cached=False))
            self.add_csr("can")

        # LiteScope Analyzer -----------------------------------------------------------------------
        if False:
            from litescope import LiteScopeAnalyzer
            count = Signal(8)
            self.sync += count.eq(count + 1)
            self.analyzer_signals = [
            count,
            ]
            self.submodules.analyzer = LiteScopeAnalyzer(self.analyzer_signals,
            depth        = 1024,
            clock_domain = "sys",
            #register     = True,
            csr_csv      = "analyzer.csv")
            self.add_csr("analyzer")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteCAN on Xyloni")
    parser.add_argument("--build", action="store_true", help="Build bitstream")
    parser.add_argument("--load",  action="store_true", help="Load bitstream")
    parser.add_argument("--flash", action="store_true", help="Flash Bitstream")
    parser.add_argument("--with-can", action="store_true", help="CAN bus")
    parser.add_argument("--sys-clk-freq",      default=33.333e6, help="System clock frequency (default: 33.333MHz)")
    parser.add_argument("--bios-flash-offset", default=0x40000,  help="BIOS offset in SPI Flash (default: 0x40000)")

    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    soc = BenchSoC(
        bios_flash_offset = args.bios_flash_offset,
        sys_clk_freq      = int(float(args.sys_clk_freq)),
        with_can = args.with_can,
        **soc_core_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, f"outflow/{soc.build_name}.bit"))

    if args.flash:
        from litex.build.openfpgaloader import OpenFPGALoader
        prog = OpenFPGALoader("xyloni_spi")
        prog.flash(0, os.path.join(builder.gateware_dir, f"outflow/{soc.build_name}.hex"))
        prog.flash(args.bios_flash_offset, os.path.join(builder.software_dir, "bios/bios.bin"))

if __name__ == "__main__":
    main()
