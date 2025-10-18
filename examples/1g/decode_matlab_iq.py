#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Décodeur COSPAS-SARSAT Matlab I/Q
# Description: Décodeur COSPAS-SARSAT pour fichiers I/Q Matlab (40 kHz)
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
import pmt
from gnuradio import cospas
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import threading




class decode_matlab_iq(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Décodeur COSPAS-SARSAT Matlab I/Q", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.sample_rate = sample_rate = 40000

        ##################################################
        # Blocks
        ##################################################

        self.cospas_cospas_sarsat_decoder_0 = cospas.cospas_sarsat_decoder(sample_rate, True)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, '/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq', False, 0, 0)
        self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, 'decoded_output.bin', False)
        self.blocks_file_sink_0.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.cospas_cospas_sarsat_decoder_0, 0))
        self.connect((self.cospas_cospas_sarsat_decoder_0, 0), (self.blocks_file_sink_0, 0))


    def get_sample_rate(self):
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate




def main(top_block_cls=decode_matlab_iq, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    tb.wait()


if __name__ == '__main__':
    main()
