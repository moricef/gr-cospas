#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Décodeur COSPAS-SARSAT I/Q
# Description: Décodeur COSPAS-SARSAT pour fichiers I/Q
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
import pmt
from gnuradio import cospas
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import threading




class decode_cospas_iq(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Décodeur COSPAS-SARSAT I/Q", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.target_rate = target_rate = 6400
        self.input_rate = input_rate = 40000

        ##################################################
        # Blocks
        ##################################################

        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=target_rate,
                decimation=input_rate,
                taps=[],
                fractional_bw=0)
        self.cospas_cospas_sarsat_decoder_0 = cospas.cospas_sarsat_decoder(True)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex*1, input_rate,True)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, '/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq', False, 0, 0)
        self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, 'decoded_output.bin', False)
        self.blocks_file_sink_0.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.cospas_cospas_sarsat_decoder_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.cospas_cospas_sarsat_decoder_0, 0))


    def get_target_rate(self):
        return self.target_rate

    def set_target_rate(self, target_rate):
        self.target_rate = target_rate

    def get_input_rate(self):
        return self.input_rate

    def set_input_rate(self, input_rate):
        self.input_rate = input_rate
        self.blocks_throttle_0.set_sample_rate(self.input_rate)




def main(top_block_cls=decode_cospas_iq, options=None):
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
