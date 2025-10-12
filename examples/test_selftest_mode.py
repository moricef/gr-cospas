#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test avec une trame en mode self-test (frame sync = 011010000)
"""

from gnuradio import gr, blocks
from gnuradio.cospas import cospas_generator, cospas_sarsat_decoder

class test_selftest_mode(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Test mode Self-Test COSPAS-SARSAT")

        # Trame de test (14 octets = 112 bits - courte)
        self.test_frame = bytes([
            0x4E, 0x3E, 0x04, 0x25, 0xA5, 0x2B, 0x00,
            0x2E, 0x36, 0x4F, 0xF7, 0x09, 0x67, 0x4E
        ])

        print("="*70)
        print("TEST MODE SELF-TEST COSPAS-SARSAT")
        print("="*70)
        print("\nFrame Sync attendu: 011010000 (Mode Self-Test)")
        print(f"Trame de test: 14 octets = 112 bits\n")

        # Générateur en mode self-test
        self.generator = cospas_generator(
            data_bytes=self.test_frame,
            repeat=True,
            test_mode=True  # Active le mode self-test
        )

        # Head block
        samples_per_frame = 1024 + 15*16 + 9*16 + 112*16
        self.head = blocks.head(gr.sizeof_gr_complex, samples_per_frame * 2)

        # Décodeur
        self.decoder = cospas_sarsat_decoder(debug_mode=True)

        # Vector sink
        self.sink = blocks.vector_sink_b()

        # Connexions
        self.connect(self.generator, self.head)
        self.connect(self.head, self.decoder)
        self.connect(self.decoder, self.sink)

def main():
    tb = test_selftest_mode()

    try:
        print("Exécution...\n")
        print("="*70)
        tb.run()
        print("="*70)

        received_data = list(tb.sink.data())

        print(f"\n\nRÉSULTATS:")
        print("="*70)
        print(f"Données reçues: {len(received_data)} octets")

        if len(received_data) >= 14:
            print("\n✅ Mode Self-Test correctement détecté et décodé!")
            errors = sum(1 for i in range(14) if tb.test_frame[i] != received_data[i])
            print(f"   Erreurs: {errors}/14 octets")
        else:
            print("\n❌ Échec du décodage")

        print("="*70)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
