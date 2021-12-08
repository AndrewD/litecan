#
# This file depends on LiteX.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# SPDX-License-Identifier: BSD-2-Clause

import os
import subprocess

from migen import *

from litex.build import tools
from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr_eventmanager import *

# CTU CAN FD -----------------------------------------------------------------------------------------

class CTUCANFD(Module, AutoCSR):
    def __init__(self, platform, pads, timestamp=0, variant="ghdl-verilog"):
        # Parameters.
        assert variant in ["vhdl", "ghdl-verilog"]
        self.platform = platform
        self.pads     = pads
        self.variant = variant

        # Wishbone Bus.
        self.bus = wishbone.Interface(data_width=32, adr_width=14)
        self.adr = Signal(16) # 16 in can_top_level but only 12bits implemented
        # wb address is 32bit
        self.comb += self.adr[2:].eq(self.bus.adr)

        # CSRs.
        self.submodules.ev = EventManager()
        self.ev.interrupt = EventSourceLevel()
        self.ev.finalize()

        self._reset = CSRStorage(1, description="""Reset the core.
            Set this flag to ``1`` to hold the core in reset.  Set to ``0`` for normal operation.""")

        # CTU CAN FD Instance.
        if True:
            sbe = Signal(4)
            self.comb += If(self.bus.we,
                sbe.eq(self.bus.sel)
            ).Else(
                sbe.eq(0b1111)
            )
            self.specials += Instance("can_top_level",
                # generic config: defaults are commented
                # TODO: enable parameters when this works with GHDL
                # TODO: See https://github.com/ghdl/ghdl-yosys-plugin/issues/136
                # RX Buffer RAM size (32 bit words)
                # p_rx_buffer_size = 32,
                # Number of supported TX buffers
                # p_txt_buffer_count = 2,
                # Synthesize Filter A-C
                # p_sup_filtA = False,
                # p_sup_filtB = False,
                # p_sup_filtC = False,
                # Synthesize Range Filter
                # p_sup_filtV = False,
                # Synthesize Test registers
                # default is true but not recommended for FPGA??
                # p_sup_test_registers = False,
                # Insert Traffic counters
                # p_sup_traffic_ctrs = False,
                # Target technology (ASIC or FPGA)
                # target_technology = C_TECH_FPGA

                # System clock
                i_clk_sys = ClockSignal("sys"),
                # Asynchronous reset
                i_res_n = ~self._reset.storage, #ResetSignal("sys"),
                # Synchronized reset
                # o_res_n_out
                # DFT support (ASIC only)
                i_scan_enable = 0,

                # Memory interface
                i_data_in = self.bus.dat_w,
                o_data_out = self.bus.dat_r,
                i_adress = self.adr,
                # chip select
                i_scs = self.bus.cyc & self.bus.stb,
                i_srd = ~self.bus.we,
                i_swr = self.bus.we,
                i_sbe = sbe,

                # Interrupt output
                o_irq = self.ev.interrupt.trigger,

                # TX signal to CAN bus
                o_can_tx = pads.tx,
                # RX signal from CAN bus
                i_can_rx = pads.rx,

                # Debug signals for testbench
                # test_probe  : out t_ctu_can_fd_test_probe;

                # 64 bit Timestamp for time based transmission / reception
                i_timestamp = timestamp,
            )
        else:
            # test WB is working
            buf = Signal(32)
            self.sync += If(self.bus.stb & self.bus.cyc & self.bus.we,
                buf.eq(self.bus.dat_w)
            )
            self.comb += self.bus.dat_r.eq(buf)

        # added cs to extend bus cycle with no effect
        self.cs = cs = Signal()
        self.sync += cs.eq(self.bus.stb & self.bus.cyc),
        self.sync += self.bus.ack.eq(cs & self.bus.stb & self.bus.cyc)

        # Add Sources.
        self.add_sources(platform)

    def add_sources(self, platform):
        sources = []
        cdir = os.path.dirname(__file__)
        sdir = os.path.abspath(os.path.join(cdir, 'ctucanfd_ip_core'))

        with open(os.path.join(cdir, 'rtl_lst.txt')) as f:

            for line in f:
                srcfile = os.path.join(sdir, line.strip().replace('rtl', 'src'))
                sources.append(srcfile)

            # Direct VHDL.
            if self.variant == "vhdl":
                platform.add_sources(sdir, *sources, library="ctu_can_fd_rtl")

            # Verilog (through GHDL/VHDL translation).
            if self.variant == "ghdl-verilog":
                ys = []
                ys.append("ghdl --ieee=synopsys -fexplicit -frelaxed-rules --std=08 \\")
                ys.append("--work=ctu_can_fd_rtl \\")
                for source in sources:
                    ys.append(source + " \\")
                ys.append("-e can_top_level")
                ys.append("chformal -assert -remove")
                ys.append("write_verilog {}".format(os.path.join(cdir, "ctucanfd.v")))
                tools.write_to_file("ctucanfd.ys", "\n".join(ys))
                if subprocess.call(["yosys", "-q", "ctucanfd.ys", "-m", "ghdl"]):
                    raise OSError("Unable to convert CTU CAN FD controller to verilog, please check your Yosys install")
                platform.add_source(os.path.join(cdir, "ctucanfd.v"))
