#!/usr/bin/env python3

#
# This file is part of Linux-on-LiteX-VexRiscv
#
# Copyright (c) 2019-2021, Linux-on-LiteX-VexRiscv Developers
# SPDX-License-Identifier: BSD-2-Clause

import sys
import argparse
import os

from litex.soc.cores.cpu import VexRiscvSMP
from litex.soc.integration.builder import Builder

from migen.build.generic_platform import Pins, IOStandard, Subsignal, Misc

from soc_linux import SoCLinux

kB = 1024

# Board definition----------------------------------------------------------------------------------

class Board:
    soc_kwargs = {"integrated_rom_size": 0x10000, "l2_size": 0}
    def __init__(self, soc_cls=None, soc_capabilities={}, soc_constants={}, soc_extension=[], bitstream_ext=""):
        self.soc_cls          = soc_cls
        self.soc_capabilities = soc_capabilities
        self.soc_constants    = soc_constants
        self.soc_extension    = soc_extension
        self.bitstream_ext    = bitstream_ext

    def load(self, filename):
        prog = self.platform.create_programmer()
        prog.load_bitstream(filename)

    def flash(self, filename):
        prog = self.platform.create_programmer()
        prog.flash(0, filename)

#---------------------------------------------------------------------------------------------------
# Lattice Boards
#---------------------------------------------------------------------------------------------------

# ECPIX5 support -----------------------------------------------------------------------------------

class ECPIX5(Board):
    SPIFLASH_PAGE_SIZE    = 256
    SPIFLASH_SECTOR_SIZE  = 64*kB
    SPIFLASH_DUMMY_CYCLES = 8
    soc_kwargs = {
        "sys_clk_freq" : int(50e6),
        "l2_size"      : 2048, # Use Wishbone and L2 for memory accesses.
    }
    extension_io = [
        ("can", 0,
            Subsignal("tx", Pins("pmod3:6")),
            Subsignal("rx", Pins("pmod3:2")),
            IOStandard("LVCMOS33")
        ),
    ]

    def __init__(self):
        import ecpix5
        Board.__init__(self, ecpix5.BaseSoC, soc_capabilities={
            # Communication
            "serial",
            "ethernet",
            # GPIO
            #"rgb_led",
            # Storage
            "sata",
            "sdcard",
            "spiflash",
            #"can",
        }, soc_extension=self.extension_io, bitstream_ext=".bit")

#---------------------------------------------------------------------------------------------------
# Build
#---------------------------------------------------------------------------------------------------

supported_boards = {
    # Lattice
    "ecpix5":          ECPIX5,
}

def main():
    description = "Linux on LiteX-VexRiscv\n\n"
    description += "Available boards:\n"
    for name in supported_boards.keys():
        description += "- " + name + "\n"
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--board",          required=True,            help="FPGA board")
    parser.add_argument("--device",         default=None,             help="FPGA device")
    parser.add_argument("--variant",        default=None,             help="FPGA board variant")
    parser.add_argument("--toolchain",      default=None,             help="Toolchain use to build")
    parser.add_argument("--build",          action="store_true",      help="Build bitstream")
    parser.add_argument("--load",           action="store_true",      help="Load bitstream (to SRAM)")
    parser.add_argument("--flash",          action="store_true",      help="Flash bitstream/images (to SPI Flash)")
    parser.add_argument("--doc",            action="store_true",      help="Build documentation")
    parser.add_argument("--local-ip",       default="192.168.1.50",   help="Local IP address")
    parser.add_argument("--remote-ip",      default="192.168.1.100",  help="Remote IP address of TFTP server")
    parser.add_argument("--spi-data-width", type=int, default=8,      help="SPI data width (maximum transfered bits per xfer)")
    parser.add_argument("--spi-clk-freq",   type=int, default=1e6,    help="SPI clock frequency")
    parser.add_argument("--fdtoverlays",    default="",               help="Device Tree Overlays to apply")
    VexRiscvSMP.args_fill(parser)
    args = parser.parse_args()

    # Board(s) selection ---------------------------------------------------------------------------
    if args.board == "all":
        board_names = list(supported_boards.keys())
    else:
        args.board = args.board.lower()
        args.board = args.board.replace(" ", "_")
        board_names = [args.board]

    # Board(s) iteration ---------------------------------------------------------------------------
    for board_name in board_names:
        board = supported_boards[board_name]()
        soc_kwargs = Board.soc_kwargs
        soc_kwargs.update(board.soc_kwargs)

        # CPU parameters ---------------------------------------------------------------------------
        # Do memory accesses through Wishbone and L2 cache when L2 size is configured.
        args.with_wishbone_memory = soc_kwargs["l2_size"] != 0
        VexRiscvSMP.args_read(args)

        # SoC parameters ---------------------------------------------------------------------------
        if args.device is not None:
            soc_kwargs.update(device=args.device)
        if args.variant is not None:
            soc_kwargs.update(variant=args.variant)
        if args.toolchain is not None:
            soc_kwargs.update(toolchain=args.toolchain)
        if "usb_fifo" in board.soc_capabilities:
            soc_kwargs.update(uart_name="usb_fifo")
        if "usb_acm" in board.soc_capabilities:
            soc_kwargs.update(uart_name="usb_acm")
        if "ethernet" in board.soc_capabilities:
            soc_kwargs.update(with_ethernet=True)
        if "sata" in board.soc_capabilities:
            soc_kwargs.update(with_sata=True)
        if "video_terminal" in board.soc_capabilities:
            soc_kwargs.update(with_video_terminal=True)
        if "framebuffer" in board.soc_capabilities:
            soc_kwargs.update(with_video_framebuffer=True)

        # SoC creation -----------------------------------------------------------------------------
        soc = SoCLinux(board.soc_cls, **soc_kwargs)
        board.platform = soc.platform

        # SoC constants ----------------------------------------------------------------------------
        for k, v in board.soc_constants.items():
            soc.add_constant(k, v)

        # SoC peripherals --------------------------------------------------------------------------
        if board.soc_extension is not None:
            board.platform.add_extension(board.soc_extension)

        if board_name in ["arty", "arty_a7"]:
            from litex_boards.platforms.arty import _sdcard_pmod_io
            board.platform.add_extension(_sdcard_pmod_io)

        if board_name in ["orangecrab"]:
            from litex_boards.platforms.orangecrab import feather_i2c
            board.platform.add_extension(feather_i2c)

        if "mmcm" in board.soc_capabilities:
            soc.add_mmcm(2)
        if "spiflash" in board.soc_capabilities:
            soc.add_spi_flash(dummy_cycles=board.SPIFLASH_DUMMY_CYCLES)
            soc.add_constant("SPIFLASH_PAGE_SIZE", board.SPIFLASH_PAGE_SIZE)
            soc.add_constant("SPIFLASH_SECTOR_SIZE", board.SPIFLASH_SECTOR_SIZE)
        if "spisdcard" in board.soc_capabilities:
            soc.add_spi_sdcard()
        if "sdcard" in board.soc_capabilities:
            soc.add_sdcard()
        if "ethernet" in board.soc_capabilities:
            soc.configure_ethernet(local_ip=args.local_ip, remote_ip=args.remote_ip)
        #if "leds" in board.soc_capabilities:
        #    soc.add_leds()
        if "rgb_led" in board.soc_capabilities:
            soc.add_rgb_led()
        if "switches" in board.soc_capabilities:
            soc.add_switches()
        if "spi" in board.soc_capabilities:
            soc.add_spi(args.spi_data_width, args.spi_clk_freq)
        if "i2c" in board.soc_capabilities:
            soc.add_i2c()
        if "xadc" in board.soc_capabilities:
            soc.add_xadc()
        if "icap_bitstream" in board.soc_capabilities:
            soc.add_icap_bitstream()
        if "can" in board.soc_capabilities:
            soc.add_can()
        soc.configure_boot()

        # Build ------------------------------------------------------------------------------------
        build_dir = os.path.join("build", board_name)
        builder   = Builder(soc,
            output_dir   = os.path.join("build", board_name),
            bios_options = ["TERM_MINI"],
            csr_json     = os.path.join(build_dir, "csr.json"),
            csr_csv      = os.path.join(build_dir, "csr.csv")
        )
        builder.build(run=args.build, build_name=board_name)

        # DTS --------------------------------------------------------------------------------------
        soc.generate_dts(board_name)
        soc.compile_dts(board_name, args.fdtoverlays)

        # DTB --------------------------------------------------------------------------------------
        soc.combine_dtb(board_name, args.fdtoverlays)

        # Load FPGA bitstream ----------------------------------------------------------------------
        if args.load:
            board.load(filename=os.path.join(builder.gateware_dir, soc.build_name + board.bitstream_ext))

        # Flash bitstream/images (to SPI Flash) ----------------------------------------------------
        if args.flash:
            board.flash(filename=os.path.join(builder.gateware_dir, soc.build_name + board.bitstream_ext))

        # Generate SoC documentation ---------------------------------------------------------------
        if args.doc:
            soc.generate_doc(board_name)

if __name__ == "__main__":
    main()
