#!/usr/bin/env python3
"""
Test du bloc cospas_burst_detector
"""

import numpy as np
from gnuradio import gr, blocks
import gnuradio.cospas as cospas
import sys

def test_burst_detector(input_file, sample_rate):
    """Teste le détecteur de bursts sur un fichier IQ"""

    print(f"[TEST] Fichier: {input_file}")
    print(f"[TEST] Sample rate: {sample_rate} Hz")

    # Lire le fichier IQ
    iq_data = np.fromfile(input_file, dtype=np.complex64)
    print(f"[TEST] Échantillons: {len(iq_data)}")

    # Créer le flowgraph
    tb = gr.top_block()

    # Source
    src = blocks.vector_source_c(iq_data.tolist(), False)

    # Détecteur de bursts
    burst_detector = cospas.cospas_burst_detector(
        sample_rate=sample_rate,
        buffer_duration_ms=1500,  # 1.5 secondes
        threshold=0.1,             # Seuil de détection
        min_burst_duration_ms=200, # Burst minimum 200ms
        debug_mode=True            # Debug activé
    )

    # Sink pour collecter les bursts
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='_bursts.iq') as f:
        bursts_file = f.name

    sink = blocks.file_sink(gr.sizeof_gr_complex, bursts_file)

    # Connecter
    tb.connect(src, burst_detector)
    tb.connect(burst_detector, sink)

    # Exécuter
    print("\n[TEST] Démarrage du détecteur de bursts...")
    tb.run()
    tb.wait()

    # Résultats
    bursts_detected = burst_detector.get_bursts_detected()
    print(f"\n[TEST] Bursts détectés: {bursts_detected}")

    # Lire les bursts extraits
    bursts_data = np.fromfile(bursts_file, dtype=np.complex64)
    print(f"[TEST] Échantillons de bursts extraits: {len(bursts_data)}")
    print(f"[TEST] Fichier de bursts: {bursts_file}")

    return bursts_detected, len(bursts_data)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <fichier.iq> <sample_rate>")
        sys.exit(1)

    input_file = sys.argv[1]
    sample_rate = float(sys.argv[2])

    bursts, samples = test_burst_detector(input_file, sample_rate)

    print(f"\n[TEST] Résumé:")
    print(f"  Bursts détectés: {bursts}")
    print(f"  Échantillons extraits: {samples}")

    if bursts > 0:
        print(f"  Durée moyenne par burst: {samples/bursts:.0f} samples ({samples/bursts/sample_rate*1000:.1f} ms)")
