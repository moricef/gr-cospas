#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple monitor block that listens for decode_complete messages
"""

from gnuradio import gr
import pmt


class decode_monitor(gr.sync_block):
    """
    Monitor block that listens for decode_complete messages from the demodulator.
    Sets a flag when decode is complete.
    """

    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="decode_monitor",
            in_sig=None,     # No stream input
            out_sig=None     # No stream output
        )

        # Register input message port
        self.message_port_register_in(pmt.intern("decode_complete"))
        self.set_msg_handler(pmt.intern("decode_complete"), self.handle_decode_complete)

        # Flag to signal decode completion
        self.decode_complete = False

    def handle_decode_complete(self, msg):
        """Handler called when decode_complete message is received"""
        self.decode_complete = True

    def is_complete(self):
        """Check if decode is complete"""
        return self.decode_complete

    def reset(self):
        """Reset the completion flag"""
        self.decode_complete = False

    def work(self, input_items, output_items):
        """No processing needed - all done via messages"""
        return 0
