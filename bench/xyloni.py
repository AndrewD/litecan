#!/usr/bin/env python3

#
# This file is part of LiteCAN and derived from the LiteX-Boards target for Efinix Xyloni.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# Copyright (c) 2021 Franck Jullien <franck.jullien@collshade.fr>
# Copyright (c) 2021 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

# Use:
# ./xyloni.py --build --flash  --with-can --cpu-type=None --uart-name uartbone --integrated-sram-size 0

import os
import argparse

from litex.build.generic_platform import *

from litex_boards.targets.efinix_xyloni_dev_kit import *

from ctucanfd import CTUCANFD


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
            can = CTUCANFD(self.platform, pads=can_pads, variant="ghdl-verilog")
            setattr(self.submodules, name, can)
            if self.irq.enabled:
                self.add_interrupt(name)
            self.bus.add_slave(name, can.bus, SoCRegion(size=0x1000, mode="rw", cached=False))
            self.add_csr("can")

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

    soc_kwargs     = soc_core_argdict(args)
    builder_kwargs = builder_argdict(args)

    bios_options = []
    if args.with_can:
        soc_kwargs["integrated_sram_size"] = 2048
        bios_options = [ "TERM_MINI" ]
        if soc_kwargs.get("cpu_type", "vexriscv") == "vexriscv":
            soc_kwargs["cpu_variant"] = "minimal"

    soc = BenchSoC(
        bios_flash_offset = args.bios_flash_offset,
        sys_clk_freq      = int(float(args.sys_clk_freq)),
        with_can = args.with_can,
        **soc_kwargs)
    builder = Builder(soc, bios_options = bios_options, **builder_kwargs)
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, f"{soc.build_name}.bit"))

    if args.flash:
        from litex.build.openfpgaloader import OpenFPGALoader
        prog = OpenFPGALoader("xyloni_spi")
        prog.flash(0, os.path.join(builder.gateware_dir, f"{soc.build_name}.hex"))
        prog.flash(args.bios_flash_offset, os.path.join(builder.software_dir, "bios/bios.bin"))

if __name__ == "__main__":
    main()
