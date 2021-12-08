#
# CTU CAN-FD Core Wrapper for LiteX.
#
# Copyright (c) 2021 Andrew Dennison <andrew@motec.com.au>
# Copyright (c) 2021 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import os
import subprocess

from migen import *

from litex.build import tools
from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr_eventmanager import *

# CTU CAN-FD ---------------------------------------------------------------------------------------

class CTUCANFD(Module, AutoCSR):
    def __init__(self, platform, pads, timestamp=0, variant="ghdl-verilog"):
        # Parameters.
        assert variant in ["vhdl", "ghdl-verilog"]
        self.platform = platform
        self.pads     = pads
        self.variant = variant

        # Wishbone Bus.
        self.bus = wishbone.Interface(data_width=32)

        # CSRs.
        self.submodules.ev = EventManager()
        self.ev.interrupt = EventSourceLevel()
        self.ev.finalize()

        self._reset = CSRStorage(1, description="""Reset the core.
            Set this flag to ``1`` to hold the core in reset.  Set to ``0`` for normal operation.""")

        # CTU CAN-FD Instance ----------------------------------------------------------------------
        self.core_params = dict()

        # Wishbone to CTU CAN-FD Memory Bus adaptation.
        mem_scs      = Signal()
        mem_srd      = Signal()
        mem_swr      = Signal()
        mem_sbe      = Signal(4)
        mem_adress   = Signal(16)
        mem_data_in  = Signal(32)
        mem_data_out = Signal(32)

        self.comb += [
            # Set scs on Access cycle.
            mem_scs.eq(self.bus.cyc & self.bus.stb),

            # Set swr on Write and use sel as sbe.
            If(self.bus.we,
                mem_swr.eq(1),
                mem_sbe.eq(self.bus.sel)

            # Set srd on Read and set sbe to 0b1111.
            ).Else(
                mem_srd.eq(1),
                mem_sbe.eq(0b1111)
            ),

            # Convert 32-bit word addressing to bytes addressing.
            mem_adress.eq(Cat(Signal(2), self.bus.adr)),

            # Connect data_in/out.
            mem_data_in.eq(self.bus.dat_w),
            self.bus.dat_r.eq(mem_data_out),
        ]
        cs = Signal()
        self.sync += cs.eq(self.bus.stb & self.bus.cyc),
        self.sync += self.bus.ack.eq(cs & self.bus.stb & self.bus.cyc)

        # CTU CAN-FD Parameters.
        if variant == "ghdl-verilog":
            print("WARNING: Using default CTU CAN-FD parameters due to a GHDL limitation!")
            print("See: https://github.com/ghdl/ghdl-yosys-plugin/issues/136")
        else:
            self.core_params.udate(
                # TX/RX Buffers.
                p_txt_buffer_count = 2,  # Number of TX Buffers.
                p_rx_buffer_size   = 32, # RX Buffer size (in 32-bit words).

                # Filter A-C.
                p_sup_filtA = False,
                p_sup_filtB = False,
                p_sup_filtC = False,

                # Range Filter.
                p_sup_filtV = False,

                # Test registers.
                p_sup_test_registers = False, # True by default but not recommended for FPGA?

                # Traffic counters.
                p_sup_traffic_ctrs = False,

                # Target technology (ASIC or FPGA)
                #p_target_technology = C_TECH_FPGA
        )

        # CTU CAN-FD Signals.

        self.core_params.update(
            # Clk / Rst.
            i_clk_sys = ClockSignal("sys"),
            i_res_n   = ~(ResetSignal("sys") | self._reset.storage),

            # DFT support (ASIC only).
            i_scan_enable = 0,

            # Memory interface.
            i_scs      = mem_scs,
            i_srd      = mem_srd,
            i_swr      = mem_swr,
            i_sbe      = mem_sbe,
            i_adress   = mem_adress,
            i_data_in  = mem_data_in,
            o_data_out = mem_data_out,

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
        self.specials += Instance("can_top_level", **self.core_params)

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
