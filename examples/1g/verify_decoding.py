#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification de l'intégrité du décodage COSPAS-SARSAT
Compare les données émises avec les données reçues
"""

from gnuradio import gr, blocks
from gnuradio.cospas import cospas_generator, cospas_sarsat_decoder
import numpy as np

class verify_decoder(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Vérification décodeur COSPAS")

        # Données de test (18 octets = 144 bits)
        self.test_data = [
            0xAA, 0x55, 0xFF, 0x00, 0x12, 0x34,
            0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
            0x01, 0x23, 0x45, 0x67, 0x89, 0xAB
        ]

        print("="*60)
        print("TEST DE VÉRIFICATION DU DÉCODAGE COSPAS-SARSAT")
        print("="*60)
        print(f"\nDonnées émises ({len(self.test_data)} octets):")
        print("  ", end="")
        for i, byte in enumerate(self.test_data):
            print(f"0x{byte:02X} ", end="")
            if (i + 1) % 6 == 0:
                print("\n  ", end="")
        print("\n")

        # Générateur - répéter plusieurs fois pour remplir le buffer
        self.generator = cospas_generator(
            data_bytes=bytes(self.test_data),
            repeat=True
        )

        # Head block pour limiter le nombre d'échantillons (2 trames complètes)
        # Une trame = 1024 (carrier) + 15*16 (preamble) + 144*16 (data) = 3584 samples
        samples_per_frame = 1024 + 15*16 + 144*16
        self.head = blocks.head(gr.sizeof_gr_complex, samples_per_frame * 2)

        # Décodeur
        self.decoder = cospas_sarsat_decoder(debug_mode=False)

        # Vector sink pour capturer les données décodées
        self.sink = blocks.vector_sink_b()

        # Connexions
        self.connect(self.generator, self.head)
        self.connect(self.head, self.decoder)
        self.connect(self.decoder, self.sink)

def main():
    tb = verify_decoder()

    try:
        print("Exécution du test...")
        tb.run()

        # Récupérer les données décodées
        received_data = list(tb.sink.data())

        print(f"\nDonnées reçues ({len(received_data)} octets):")
        if len(received_data) > 0:
            print("  ", end="")
            for i, byte in enumerate(received_data):
                print(f"0x{byte:02X} ", end="")
                if (i + 1) % 6 == 0:
                    print("\n  ", end="")
            print("\n")
        else:
            print("  AUCUNE DONNÉE REÇUE!\n")

        # Comparaison
        print("="*60)
        print("RÉSULTATS DE LA COMPARAISON")
        print("="*60)

        if len(received_data) == 0:
            print("❌ ÉCHEC: Aucune donnée décodée")
            return False

        if len(received_data) != len(tb.test_data):
            print(f"❌ ERREUR DE LONGUEUR:")
            print(f"   Attendu: {len(tb.test_data)} octets")
            print(f"   Reçu:    {len(received_data)} octets")

        # Comparaison octet par octet
        errors = 0
        for i in range(max(len(tb.test_data), len(received_data))):
            if i >= len(tb.test_data):
                print(f"Octet {i:2d}: ---- != 0x{received_data[i]:02X} ❌ (surplus)")
                errors += 1
            elif i >= len(received_data):
                print(f"Octet {i:2d}: 0x{tb.test_data[i]:02X} != ---- ❌ (manquant)")
                errors += 1
            elif tb.test_data[i] != received_data[i]:
                print(f"Octet {i:2d}: 0x{tb.test_data[i]:02X} != 0x{received_data[i]:02X} ❌")
                errors += 1
            else:
                print(f"Octet {i:2d}: 0x{tb.test_data[i]:02X} == 0x{received_data[i]:02X} ✓")

        print()
        print("="*60)
        if errors == 0:
            print("✅ SUCCÈS: Toutes les données sont correctement décodées!")
            print(f"   {len(tb.test_data)} octets transmis et reçus sans erreur")
        else:
            print(f"❌ ÉCHEC: {errors} erreur(s) détectée(s)")
            print(f"   Taux d'erreur: {100*errors/max(len(tb.test_data), len(received_data)):.1f}%")
        print("="*60)

        return errors == 0

    except Exception as e:
        print(f"\n❌ ERREUR lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
