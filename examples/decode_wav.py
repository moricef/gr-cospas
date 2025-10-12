#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décodage d'un fichier WAV COSPAS-SARSAT (audio FM démodulé)

Chaîne de traitement:
WAV 48kHz → Filtre passe-bande → Démodulation tonalité → I/Q bande de base 6.4kHz → Décodeur
"""

from gnuradio import gr, blocks, filter, analog
from gnuradio.cospas import cospas_sarsat_decoder
import numpy as np

class decode_wav(gr.top_block):
    def __init__(self, wav_file):
        gr.top_block.__init__(self, "Décodeur WAV COSPAS-SARSAT")

        # Paramètres
        self.audio_rate = 48000      # Fréquence audio du WAV
        self.target_rate = 6400      # Fréquence cible pour le décodeur
        self.carrier_freq = 1000     # Fréquence porteuse approximative dans l'audio

        print("="*70)
        print("DÉCODAGE FICHIER WAV COSPAS-SARSAT")
        print("="*70)
        print(f"Fichier: {wav_file.split('/')[-1]}")
        print(f"Fréquence audio: {self.audio_rate} Hz")
        print(f"Fréquence cible: {self.target_rate} Hz")
        print(f"Porteuse estimée: {self.carrier_freq} Hz")
        print("="*70)
        print()

        ##################################################
        # Blocs
        ##################################################

        # Source: fichier WAV (produit déjà des floats)
        self.wav_source = blocks.wavfile_source(wav_file, False)

        # Filtre passe-bande autour de 1 kHz (800-1200 Hz)
        # pour isoler la porteuse modulée
        bpf_taps = filter.firdes.band_pass(
            1.0,                    # gain
            self.audio_rate,        # sample rate
            800,                    # low cutoff
            1200,                   # high cutoff
            200                     # transition width
        )
        self.band_pass_filter = filter.fir_filter_fff(1, bpf_taps)

        # Quadrature demod pour extraire la modulation de phase
        # sensitivity = (pi * deviation) / sample_rate
        # Pour BPSK avec ±1.1 rad, on utilise une sensibilité faible
        self.quadrature_demod = analog.quadrature_demod_cf(self.audio_rate / (2*np.pi*self.carrier_freq))

        # Générateur de signal complexe à partir du signal réel
        # On crée un signal analytique (Hilbert transform)
        hilbert_taps = filter.firdes.hilbert(65)
        self.hilbert = filter.fir_filter_fcc(1, hilbert_taps)

        # Re-échantillonnage de 48 kHz → 6.4 kHz
        decimation = int(self.audio_rate / self.target_rate)  # 48000 / 6400 = 7.5
        # On va décimer par 7 (48000/7 = 6857 Hz) puis ajuster
        self.rational_resampler = filter.rational_resampler_ccc(
            interpolation=64,
            decimation=480,  # 48000 * 64/480 = 6400
            taps=[],
            fractional_bw=0
        )

        # Normalisation
        self.multiply_const = blocks.multiply_const_cc(1.0)

        # Décodeur COSPAS-SARSAT
        self.decoder = cospas_sarsat_decoder(debug_mode=True)

        # Sink pour les données décodées
        self.vector_sink = blocks.vector_sink_b()

        ##################################################
        # Connexions
        ##################################################

        # Via Hilbert transform
        self.connect((self.wav_source, 0), (self.band_pass_filter, 0))
        self.connect((self.band_pass_filter, 0), (self.hilbert, 0))
        self.connect((self.hilbert, 0), (self.rational_resampler, 0))
        self.connect((self.rational_resampler, 0), (self.multiply_const, 0))
        self.connect((self.multiply_const, 0), (self.decoder, 0))
        self.connect((self.decoder, 0), (self.vector_sink, 0))

def main():
    import sys

    if len(sys.argv) < 2:
        wav_file = "/home/fab2/Developpement/COSPAS-SARSAT/Audio/enregistrement_balise_exercice_zonesud/gqrx_20250918_091106_406028000.wav"
        print(f"Usage: {sys.argv[0]} <fichier.wav>")
        print(f"Utilisation du fichier par défaut: {wav_file}\n")
    else:
        wav_file = sys.argv[1]

    tb = decode_wav(wav_file)

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
            print("\nPremiers octets (hex):")
            print("  ", end="")
            for i, byte in enumerate(data[:min(20, len(data))]):
                print(f"{byte:02X} ", end="")
                if (i + 1) % 10 == 0:
                    print("\n  ", end="")
            print()

            # Comparer avec la trame réelle connue
            expected = bytes.fromhex("8E3E0425A52B002E364FF709674EB7")
            if len(data) >= len(expected):
                matches = sum(1 for i in range(len(expected)) if data[i] == expected[i])
                print(f"\nComparaison avec trame connue:")
                print(f"  Octets correspondants: {matches}/{len(expected)}")
                if matches >= len(expected) * 0.8:
                    print("  ✅ Décodage réussi!")
                else:
                    print("  ⚠️  Décodage partiel ou incorrect")
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
