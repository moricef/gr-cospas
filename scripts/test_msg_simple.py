#!/usr/bin/env python3
"""Test minimal : Detector → Message Debug"""

from gnuradio import gr, blocks
from gnuradio import cospas
import sys

class test_simple(gr.top_block):
    def __init__(self, filename, sample_rate=40000):
        gr.top_block.__init__(self, "Test Simple")

        # Source
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex, filename, False, 0, 0)

        # Burst Detector
        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate,
            buffer_duration_ms=2000,
            threshold=0.1,
            min_burst_duration_ms=200,
            debug_mode=True
        )

        # Message Debug pour voir tous les messages
        self.msg_debug = blocks.message_debug()

        # Sinks
        self.null_sink = blocks.null_sink(gr.sizeof_gr_complex)

        # Connections
        self.connect((self.file_source, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.null_sink, 0))
        self.msg_connect((self.burst_detector, 'bursts'), (self.msg_debug, 'store'))

        print("[TEST] Flowgraph simple créé: Detector → Message Debug")

if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else "examples/1g/gqrx_20251115_081026_40000.iq"
    sample_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 40000.0

    tb = test_simple(filename, sample_rate)
    tb.start()
    print("[TEST] En cours...")
    tb.wait()
    print(f"[TEST] Terminé - messages reçus: {tb.msg_debug.num_messages()}")
