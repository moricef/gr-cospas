#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du système avec Message Ports
Détection de burst → Router 1G/2G → Démodulation
"""

from gnuradio import gr, blocks
from gnuradio import cospas
import numpy as np
import sys

class test_message_ports(gr.top_block):
    def __init__(self, filename, sample_rate=40000):
        gr.top_block.__init__(self, "Test Message Ports", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.sample_rate = sample_rate

        ##################################################
        # Blocks
        ##################################################

        # Source : fichier IQ (repeat=False pour s'arrêter à la fin)
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            filename,
            False,  # no repeat
            0,      # offset
            0       # length (0 = all)
        )

        # Head block pour limiter les échantillons et éviter null_source infini
        # On limite au nombre d'échantillons du fichier
        import os
        file_size = os.path.getsize(filename)
        num_samples = file_size // 8  # 8 bytes per complex sample
        self.head = blocks.head(gr.sizeof_gr_complex, num_samples)

        # Burst Detector avec message port "bursts"
        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate,
            buffer_duration_ms=2000,
            threshold=0.1,
            min_burst_duration_ms=200,
            debug_mode=True
        )

        # Burst Router avec message ports
        self.burst_router = cospas.burst_router(
            sample_rate=sample_rate,
            debug_mode=True
        )

        # Message sinks pour consommer les messages du router
        self.msg_debug_1g = blocks.message_debug()
        self.msg_debug_2g = blocks.message_debug()

        # Sources et Sinks (pour connecter les ports stream obligatoires)
        self.null_source = blocks.null_source(gr.sizeof_gr_complex)
        self.null_sink_detector = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_1g = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        ##################################################
        # Connections
        ##################################################

        # Stream : Source → Burst Detector → Null Sink
        self.connect((self.file_source, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.null_sink_detector, 0))

        # Stream : Null Source → Head → Router (limité aux échantillons du fichier)
        self.connect((self.null_source, 0), (self.head, 0))
        self.connect((self.head, 0), (self.burst_router, 0))

        # Message Ports : Burst Detector → Router → Message Debug
        self.msg_connect((self.burst_detector, 'bursts'), (self.burst_router, 'bursts'))
        self.msg_connect((self.burst_router, 'bursts_1g'), (self.msg_debug_1g, 'store'))
        self.msg_connect((self.burst_router, 'bursts_2g'), (self.msg_debug_2g, 'store'))

        # Stream : Router → Null Sinks
        self.connect((self.burst_router, 0), (self.null_sink_1g, 0))  # Port 0 = 1G
        self.connect((self.burst_router, 1), (self.null_sink_2g, 0))  # Port 1 = 2G

        print("[TEST] Flowgraph avec Message Ports créé")
        print("  Source → Burst Detector")
        print("  Burst Detector (msg 'bursts') → Router (msg 'bursts')")
        print("  Router port 0 (1G) → Null Sink")
        print("  Router port 1 (2G) → Null Sink")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fichier_iq> [sample_rate]")
        print("Exemple:")
        print(f"  {sys.argv[0]} examples/1g/gqrx_20251115_081026_403040000_40000.iq 40000")
        sys.exit(1)

    filename = sys.argv[1]
    sample_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 40000.0

    print(f"[TEST] Démarrage du test Message Ports")
    print(f"  Fichier: {filename}")
    print(f"  Sample rate: {sample_rate} Hz")
    print()

    # Créer et lancer le flowgraph
    tb = test_message_ports(filename, sample_rate)

    try:
        tb.start()
        print("[TEST] Flowgraph en cours d'exécution...")
        tb.wait()
        print("[TEST] Flowgraph terminé, attente du traitement des messages...")
        import time
        time.sleep(1)  # Donner du temps aux messages d'être traités
        print("[TEST] Fin de l'attente")

        # Statistiques
        bursts_detected = tb.burst_detector.get_bursts_detected()
        bursts_1g = tb.burst_router.get_bursts_1g()
        bursts_2g = tb.burst_router.get_bursts_2g()

        print()
        print("=" * 60)
        print("STATISTIQUES FINALES")
        print("=" * 60)
        print(f"Bursts détectés:    {bursts_detected}")
        print(f"Bursts 1G routés:   {bursts_1g}")
        print(f"Bursts 2G routés:   {bursts_2g}")
        print("=" * 60)

        # Vérification
        if bursts_detected > 0:
            if bursts_1g + bursts_2g == bursts_detected:
                print("✓ Tous les bursts ont été routés correctement")
            else:
                print(f"✗ ERREUR: {bursts_detected} détectés mais {bursts_1g + bursts_2g} routés")
        else:
            print("⚠ Aucun burst détecté")

    except KeyboardInterrupt:
        print("\n[TEST] Interruption utilisateur")
        tb.stop()
        tb.wait()

    return 0

if __name__ == '__main__':
    sys.exit(main())
