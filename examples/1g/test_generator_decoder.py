#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du générateur et décodeur COSPAS-SARSAT
"""

from gnuradio import gr, blocks
from gnuradio import cospas
import time

class test_generator_decoder(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Test COSPAS Generator-Decoder")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = 6400

        ##################################################
        # Blocks
        ##################################################

        # Données de test (18 octets)
        test_data = bytes([
            0xAA, 0x55, 0xFF, 0x00,  # Pattern de test
            0x12, 0x34, 0x56, 0x78,  # Données
            0x9A, 0xBC, 0xDE, 0xF0,  # Encore des données
            0x01, 0x23, 0x45, 0x67,  # Et encore
            0x89, 0xAB              # Derniers octets
        ])

        # Générateur de trames COSPAS-SARSAT
        self.cospas_generator = cospas.cospas_generator(
            data_bytes=test_data,
            repeat=False  # Une seule trame pour le test
        )

        # Décodeur COSPAS-SARSAT
        self.cospas_decoder = cospas.cospas_sarsat_decoder(debug_mode=True)

        # Throttle pour éviter la surcharge CPU
        self.throttle = blocks.throttle(gr.sizeof_gr_complex, self.samp_rate, True)

        # File sink pour sauvegarder les bits décodés
        self.file_sink = blocks.file_sink(gr.sizeof_char, '/tmp/cospas_decoded.bin', False)
        self.file_sink.set_unbuffered(False)

        # Null sink pour le signal complexe (optionnel - pour debug)
        self.null_sink = blocks.null_sink(gr.sizeof_gr_complex)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.cospas_generator, 0), (self.throttle, 0))
        self.connect((self.throttle, 0), (self.cospas_decoder, 0))
        self.connect((self.cospas_decoder, 0), (self.file_sink, 0))

        # Connection optionnelle pour visualisation
        self.connect((self.throttle, 0), (self.null_sink, 0))

def main():
    print("=" * 70)
    print("Test COSPAS-SARSAT: Générateur → Décodeur")
    print("=" * 70)
    print()

    tb = test_generator_decoder()

    print("Démarrage du flowgraph...")
    print()

    tb.start()

    # Attendre que la trame soit traitée
    time.sleep(2)

    tb.stop()
    tb.wait()

    print()
    print("=" * 70)
    print("Test terminé")
    print("=" * 70)
    print()
    print("Fichier de sortie: /tmp/cospas_decoded.bin")
    print()

    # Lire et afficher les octets décodés
    try:
        with open('/tmp/cospas_decoded.bin', 'rb') as f:
            decoded_data = f.read()
            if decoded_data:
                print(f"Octets décodés ({len(decoded_data)} octets):")
                for i, byte in enumerate(decoded_data):
                    print(f"  Octet {i:2d}: 0x{byte:02X} (0b{byte:08b})")
            else:
                print("Aucune donnée décodée")
    except FileNotFoundError:
        print("Fichier de sortie non créé")

    print()

if __name__ == '__main__':
    main()
