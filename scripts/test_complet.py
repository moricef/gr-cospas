#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet : Source → Detector → Router → Démodulateur 1G
"""

from gnuradio import gr, blocks
from gnuradio import cospas
import sys

class test_complet(gr.top_block):
    def __init__(self, filename, sample_rate=40000):
        gr.top_block.__init__(self, "Test Complet")

        self.sample_rate = sample_rate

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

        # Burst Router (stream + tags)
        self.burst_router = cospas.burst_router(
            sample_rate=sample_rate,
            debug_mode=True
        )

        # Démodulateur 1G (BPSK)
        self.demod_1g = cospas.cospas_sarsat_demodulator(
            sample_rate=sample_rate,
            debug_mode=True
        )

        # Sinks
        self.null_sink_demod = blocks.null_sink(gr.sizeof_char)  # Démod sort des bytes
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        # Connections
        self.connect((self.file_source, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.burst_router, 0))
        self.connect((self.burst_router, 0), (self.demod_1g, 0))      # 1G → Démod
        self.connect((self.demod_1g, 0), (self.null_sink_demod, 0))   # Démod → Null
        self.connect((self.burst_router, 1), (self.null_sink_2g, 0))  # 2G → Null

        print("[TEST] Chaîne complète créée")
        print("  Source → Detector → Router → Démodulateur 1G")

if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else "examples/1g/gqrx_20251115_081026_40000.iq"
    sample_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 40000.0

    print(f"[TEST] Fichier: {filename}")
    print(f"[TEST] Sample rate: {sample_rate} Hz\n")

    tb = test_complet(filename, sample_rate)

    try:
        tb.start()
        print("[TEST] En cours...\n")
        tb.wait()
        print("\n[TEST] Terminé\n")

        # Statistiques
        bursts_detected = tb.burst_detector.get_bursts_detected()
        bursts_1g = tb.burst_router.get_bursts_1g()
        bursts_2g = tb.burst_router.get_bursts_2g()
        frames_decoded = tb.demod_1g.get_frames_decoded()

        print("=" * 60)
        print("STATISTIQUES")
        print("=" * 60)
        print(f"Bursts détectés:     {bursts_detected}")
        print(f"Bursts 1G routés:    {bursts_1g}")
        print(f"Bursts 2G routés:    {bursts_2g}")
        print(f"Trames démodulées:   {frames_decoded}")
        print("=" * 60)

        if bursts_1g > 0:
            ratio = (frames_decoded / bursts_1g) * 100
            print(f"Taux de démodulation: {frames_decoded}/{bursts_1g} = {ratio:.1f}%")
            if ratio >= 90:
                print("✓ Excellent taux de décodage")
            elif ratio >= 70:
                print("⚠ Taux de décodage moyen")
            else:
                print("✗ Faible taux de décodage")

    except KeyboardInterrupt:
        print("\n[TEST] Interruption")
        tb.stop()
        tb.wait()
