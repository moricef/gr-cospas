#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test avec une trame courte (format flag = 0, 112 bits)
"""

from gnuradio import gr, blocks
from gnuradio.cospas import cospas_generator, cospas_sarsat_decoder

class test_short_frame(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Test trame courte COSPAS-SARSAT")

        # Trame courte de test (112 bits = 14 octets)
        # Bit 1 (Format Flag) = 0 → trame courte
        # On commence avec 0x4E (01001110) pour avoir Format Flag = 0
        self.short_frame = bytes([
            0x4E, 0x3E, 0x04, 0x25, 0xA5, 0x2B, 0x00,
            0x2E, 0x36, 0x4F, 0xF7, 0x09, 0x67, 0x4E
        ])

        print("="*70)
        print("TEST AVEC TRAME COURTE COSPAS-SARSAT")
        print("="*70)
        print(f"\nTrame courte de test (14 octets = 112 bits):")
        print("Premier bit (Format Flag) = 0 → Trame COURTE")
        print()
        print("Données en octets:")
        print("  ", end="")
        for i, byte in enumerate(self.short_frame):
            print(f"0x{byte:02X} ", end="")
            if (i + 1) % 7 == 0:
                print("\n  ", end="")
        print("\n")

        # Générateur avec la trame courte
        self.generator = cospas_generator(
            data_bytes=self.short_frame,
            repeat=True
        )

        # Head block pour limiter à 2 trames
        samples_per_frame = 1024 + 15*16 + 112*16  # Trame courte
        self.head = blocks.head(gr.sizeof_gr_complex, samples_per_frame * 2)

        # Décodeur
        self.decoder = cospas_sarsat_decoder(debug_mode=True)

        # Vector sink pour capturer les données décodées
        self.sink = blocks.vector_sink_b()

        # Connexions
        self.connect(self.generator, self.head)
        self.connect(self.head, self.decoder)
        self.connect(self.decoder, self.sink)

def main():
    tb = test_short_frame()

    try:
        print("Exécution du test avec la trame courte...\n")
        print("="*70)
        tb.run()
        print("="*70)

        # Récupérer les données décodées
        received_data = list(tb.sink.data())

        print(f"\n\nRÉSULTATS:")
        print("="*70)
        print(f"Données reçues: {len(received_data)} octets")

        if len(received_data) > 0:
            print("\nComparaison avec la trame originale:")
            print()

            comparison_length = min(len(received_data), len(tb.short_frame))
            errors = 0

            for i in range(comparison_length):
                original = tb.short_frame[i]
                received = received_data[i]
                match = "✓" if original == received else "✗"
                print(f"  Octet {i:2d}: 0x{original:02X} -> 0x{received:02X} {match}")
                if original != received:
                    errors += 1

            print()
            print("="*70)
            if errors == 0 and len(received_data) >= len(tb.short_frame):
                print("✅ SUCCÈS: La trame courte est correctement décodée!")
                print(f"   {len(tb.short_frame)} octets transmis et reçus sans erreur")
            else:
                print(f"❌ ÉCHEC: {errors} erreur(s) détectée(s)")
            print("="*70)
        else:
            print("❌ AUCUNE DONNÉE REÇUE")

    except Exception as e:
        print(f"\n❌ ERREUR lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
