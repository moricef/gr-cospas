#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décodage d'un fichier I/Q COSPAS-SARSAT à 40 kHz (fichiers Matlab)
SANS ré-échantillonnage - décodeur adaptatif
"""

from gnuradio import gr, blocks
from gnuradio.cospas import cospas_sarsat_decoder
import sys

class decode_iq_40khz(gr.top_block):
    def __init__(self, iq_file):
        gr.top_block.__init__(self, "Décodeur I/Q COSPAS-SARSAT 40 kHz")

        print("="*70)
        print("DÉCODAGE FICHIER I/Q MATLAB (40 kHz)")
        print("="*70)
        print(f"Fichier: {iq_file.split('/')[-1]}")
        print(f"Fréquence: 40000 Hz")
        print(f"Échantillons/bit: 100")
        print("="*70)
        print()

        # Source: fichier I/Q (complex float32)
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            iq_file,
            False  # Ne pas répéter - une seule lecture
        )

        # Décodeur COSPAS-SARSAT configuré pour 40 kHz
        self.decoder = cospas_sarsat_decoder(
            sample_rate=40000,  # 40 kHz natif
            debug_mode=True
        )

        # Sink pour récupérer les données
        self.vector_sink = blocks.vector_sink_b()

        # Connexions (DIRECT - pas de ré-échantillonnage!)
        self.connect((self.file_source, 0), (self.decoder, 0))
        self.connect((self.decoder, 0), (self.vector_sink, 0))


def main():
    if len(sys.argv) < 2:
        iq_file = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"
        print(f"Usage: {sys.argv[0]} <fichier.iq>")
        print(f"Utilisation du fichier par défaut")
        print()
    else:
        iq_file = sys.argv[1]

    tb = decode_iq_40khz(iq_file)

    # IMPORTANT: Forcer une taille de buffer déterministe
    # Cela garantit que noutput_items ne varie pas entre les exécutions
    # 20800 = taille exacte pour 1 trame complète (porteuse + 144 bits)
    tb.set_max_noutput_items(20800)
    print("⚙️  Buffer maximum: 20800 échantillons (1 trame complète)")
    print()

    try:
        print("Démarrage du décodage...")
        print()
        tb.run()
        print()
        print("="*70)

        # Récupérer les données décodées
        data = list(tb.vector_sink.data())

        if len(data) > 0:
            print(f"\n✅ Données décodées: {len(data)} octets")
            print("\nDonnées (hex):")
            print("  " + "".join(f"{b:02X}" for b in data))
            print()

            # Comparer avec les trames connues
            known_frames = [
                "8E3301E2402B002BBA863609670908",
                "8E3301E240298056CF99F61503780B",
                "8E3E0425A52B002E364FF709674EB7"
            ]

            for expected_hex in known_frames:
                expected = bytes.fromhex(expected_hex)
                if len(data) >= len(expected):
                    matches = sum(1 for i in range(len(expected))
                                if data[i] == expected[i])
                    if matches >= len(expected) * 0.8:
                        print(f"Correspondance: {expected_hex}")
                        print(f"  Octets corrects: {matches}/{len(expected)}")
                        if matches == len(expected):
                            print("Décodage OK")
                        break
        else:
            print("\n❌ Aucune donnée décodée")

        print("="*70)

    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
