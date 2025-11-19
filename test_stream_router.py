#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du router avec approche Stream + Tags (fiable)
Burst Detector → Router (stream) → Démodulateur 1G / 2G
"""

from gnuradio import gr, blocks
from gnuradio import cospas
import sys

class test_stream_router(gr.top_block):
    def __init__(self, filename, sample_rate=40000):
        gr.top_block.__init__(self, "Test Stream Router")

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

        # Sinks
        self.null_sink_1g = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        # Connections STREAM (pas de message ports)
        self.connect((self.file_source, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.burst_router, 0))
        self.connect((self.burst_router, 0), (self.null_sink_1g, 0))  # Port 0 = 1G
        self.connect((self.burst_router, 1), (self.null_sink_2g, 0))  # Port 1 = 2G

        print("[TEST] Flowgraph Stream + Tags créé")
        print("  Source → Detector → Router → Sinks")
        print("  Routing par tags (burst_start/burst_end)")

if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else "examples/1g/gqrx_20251115_081026_40000.iq"
    sample_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 40000.0

    print(f"[TEST] Fichier: {filename}")
    print(f"[TEST] Sample rate: {sample_rate} Hz\n")

    tb = test_stream_router(filename, sample_rate)

    try:
        tb.start()
        print("[TEST] En cours...")
        tb.wait()
        print("[TEST] Terminé\n")

        # Statistiques
        bursts_detected = tb.burst_detector.get_bursts_detected()
        bursts_1g = tb.burst_router.get_bursts_1g()
        bursts_2g = tb.burst_router.get_bursts_2g()

        print("=" * 60)
        print("STATISTIQUES")
        print("=" * 60)
        print(f"Bursts détectés:    {bursts_detected}")
        print(f"Bursts 1G routés:   {bursts_1g}")
        print(f"Bursts 2G routés:   {bursts_2g}")
        print("=" * 60)

        if bursts_detected > 0:
            if bursts_1g + bursts_2g == bursts_detected:
                print("✓ Tous les bursts routés correctement (100%)")
            else:
                print(f"✗ ERREUR: {bursts_detected} détectés, {bursts_1g + bursts_2g} routés")
        else:
            print("⚠ Aucun burst détecté")

    except KeyboardInterrupt:
        print("\n[TEST] Interruption")
        tb.stop()
        tb.wait()
