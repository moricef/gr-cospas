#!/usr/bin/env python3
"""Test fichier IQ avec chaîne complète Detector → Router → Demod (mode message)"""

import sys
from gnuradio import gr, blocks
from gnuradio import cospas

class test_file_message_mode(gr.top_block):
    def __init__(self, input_file, sample_rate=40000):
        gr.top_block.__init__(self)

        self.file_source = blocks.file_source(gr.sizeof_gr_complex, input_file, False)

        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate,
            buffer_duration_ms=2000,
            threshold=0.5,
            min_burst_duration_ms=200,
            debug_mode=True
        )

        # Burst Router
        self.burst_router = cospas.burst_router(sample_rate, False)

        # Démodulateur 1G (mode message)
        self.demod_1g = cospas.cospas_sarsat_demodulator(sample_rate, True)

        # Null sinks pour les sorties stream non utilisées du router
        self.null_sink_1g = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        # Connexions stream
        self.connect(self.file_source, self.burst_detector)
        self.connect(self.burst_detector, (self.burst_router, 0))
        self.connect((self.burst_router, 0), self.null_sink_1g)
        self.connect((self.burst_router, 1), self.null_sink_2g)

        # Connexions message
        self.msg_connect((self.burst_detector, "bursts"), (self.burst_router, "bursts"))
        self.msg_connect((self.burst_router, "bursts_1g"), (self.demod_1g, "bursts"))

        print(f"Fichier: {input_file}")
        print(f"Sample rate: {sample_rate} Hz")
        print("Chaîne: File → Detector (autocorrélation) → Router → Demod")
        print("")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fichier.iq> [sample_rate]")
        sys.exit(1)

    input_file = sys.argv[1]
    sample_rate = int(sys.argv[2]) if len(sys.argv) > 2 else 40000

    tb = test_file_message_mode(input_file, sample_rate)
    tb.run()
    tb.wait()

    print("\nTerminé")

if __name__ == '__main__':
    main()
