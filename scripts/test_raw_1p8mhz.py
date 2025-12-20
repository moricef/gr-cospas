#!/usr/bin/env python3
"""Test sur fichier RAW 1.8 MHz sans décimation"""

from gnuradio import gr, blocks, filter
from gnuradio import cospas
import sys

class test_raw_1p8mhz(gr.top_block):
    def __init__(self, filename):
        gr.top_block.__init__(self, "Test RAW 1.8MHz")

        sample_rate_raw = 1800000
        sample_rate_target = 40000
        decimation = int(sample_rate_raw / sample_rate_target)  # 45

        print(f"[TEST] Taux source: {sample_rate_raw} Hz")
        print(f"[TEST] Taux cible: {sample_rate_target} Hz")
        print(f"[TEST] Décimation: {decimation}")

        # Source
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex, filename, False, 0, 0)

        # Décimation avec filtre low-pass intégré GNU Radio
        # Cutoff à 20 kHz, transition 5 kHz
        taps = filter.firdes.low_pass(
            1.0,                    # gain
            sample_rate_raw,        # sample rate
            20000,                  # cutoff freq
            5000                    # transition width
        )

        self.decimator = filter.fir_filter_ccf(decimation, taps)

        print(f"[TEST] Filtre FIR: {len(taps)} taps, cutoff 20kHz")

        # Burst Detector @ 40 kHz
        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate_target,
            buffer_duration_ms=2000,
            threshold=0.1,
            min_burst_duration_ms=200,
            debug_mode=True
        )

        # Router
        self.burst_router = cospas.burst_router(
            sample_rate=sample_rate_target,
            debug_mode=True
        )

        # Démodulateur 1G
        self.demod_1g = cospas.cospas_sarsat_demodulator(
            sample_rate=sample_rate_target,
            debug_mode=True
        )

        # Sinks
        self.null_sink_1g = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        # Connections
        self.connect((self.file_source, 0), (self.decimator, 0))
        self.connect((self.decimator, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.burst_router, 0))
        self.connect((self.burst_router, 0), (self.null_sink_1g, 0))
        self.connect((self.burst_router, 1), (self.null_sink_2g, 0))

        # Messages
        self.msg_connect((self.burst_detector, 'bursts'), (self.burst_router, 'bursts'))
        self.msg_connect((self.burst_router, 'bursts_1g'), (self.demod_1g, 'bursts'))
        # Note: demod outputs to console, no message port

        print("[TEST] Flowgraph créé: Source(1.8MHz) → Decim(÷45) → Detector(40kHz) → Router → Demod")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: test_raw_1p8mhz.py <fichier_raw_1.8mhz.iq>")
        sys.exit(1)

    filename = sys.argv[1]

    tb = test_raw_1p8mhz(filename)
    tb.start()
    print("[TEST] En cours...")
    tb.wait()

    print(f"\n[TEST] Terminé")
    print(f"[TEST] Bursts 1G: {tb.burst_router.get_bursts_1g()}")
    print(f"[TEST] Bursts 2G: {tb.burst_router.get_bursts_2g()}")
