#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du générateur avec la trame réelle capturée
Trame: 8E3E0425A52B002E364FF709674EB7
"""

from gnuradio import gr, blocks
from gnuradio.cospas import cospas_generator, cospas_sarsat_decoder

class test_real_frame(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Test trame réelle COSPAS-SARSAT")

        # Trame réelle capturée (18 octets = 144 bits)
        # Hexadecimal: 8E3E0425A52B002E364FF709674EB7
        self.real_frame = bytes.fromhex("8E3E0425A52B002E364FF709674EB7")

        print("="*70)
        print("TEST AVEC TRAME RÉELLE COSPAS-SARSAT")
        print("="*70)
        print(f"\nTrame capturée (18 octets = 144 bits):")
        print(f"Hex: 8E3E0425A52B002E364FF709674EB7\n")
        print("Informations décodées:")
        print("  - Protocole: 14 (Standard Location - Test)")
        print("  - Pays: France (227)")
        print("  - Position: 42.961°N, 1.371°E (Pyrénées)")
        print("  - ID: LG-STD-00E3-000025A5")
        print()
        print("Données en octets:")
        print("  ", end="")
        for i, byte in enumerate(self.real_frame):
            print(f"0x{byte:02X} ", end="")
            if (i + 1) % 6 == 0:
                print("\n  ", end="")
        print("\n")

        # Générateur avec la trame réelle
        self.generator = cospas_generator(
            data_bytes=self.real_frame,
            repeat=True
        )

        # Head block pour limiter à 2 trames
        samples_per_frame = 1024 + 15*16 + 144*16
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
    tb = test_real_frame()

    try:
        print("Exécution du test avec la trame réelle...\n")
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

            # Afficher les 18 premiers octets (une trame complète)
            comparison_length = min(len(received_data), len(tb.real_frame))
            errors = 0

            for i in range(comparison_length):
                original = tb.real_frame[i]
                received = received_data[i]
                match = "✓" if original == received else "✗"
                print(f"  Octet {i:2d}: 0x{original:02X} -> 0x{received:02X} {match}")
                if original != received:
                    errors += 1

            print()
            print("="*70)
            if errors == 0 and len(received_data) >= len(tb.real_frame):
                print("✅ SUCCÈS: La trame réelle est correctement générée et décodée!")
                print(f"   {len(tb.real_frame)} octets transmis et reçus sans erreur")

                # Reconstruire l'hex
                received_hex = ''.join([f'{b:02X}' for b in received_data[:18]])
                print(f"\n   Trame décodée (hex): {received_hex}")
                print(f"   Trame originale:     8E3E0425A52B002E364FF709674EB7")
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
