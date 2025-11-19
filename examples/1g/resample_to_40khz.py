#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertit un fichier I/Q 2.5 MHz en 40 kHz (pour comparaison avec fichiers Matlab)
"""
import numpy as np
from scipy import signal
import sys

def resample_iq(input_file, output_file, input_rate=2500000, output_rate=40000):
    """Ré-échantillonne un fichier I/Q"""

    print(f"Lecture de {input_file}...")
    # Lire le fichier I/Q (complex64)
    iq_data = np.fromfile(input_file, dtype=np.complex64)
    print(f"  {len(iq_data)} échantillons lus ({len(iq_data)/input_rate:.2f} secondes)")

    # Calculer le facteur de décimation
    decim_factor = input_rate // output_rate
    print(f"\nDécimation: {input_rate} Hz → {output_rate} Hz (facteur {decim_factor})")

    # Filtre anti-aliasing et décimation
    print("Application du filtre anti-aliasing...")
    iq_resampled = signal.decimate(iq_data, decim_factor, ftype='fir', zero_phase=True)

    print(f"  {len(iq_resampled)} échantillons en sortie ({len(iq_resampled)/output_rate:.2f} secondes)")

    # Sauvegarder
    print(f"\nÉcriture de {output_file}...")
    iq_resampled.astype(np.complex64).tofile(output_file)

    # Statistiques
    print("\n=== Statistiques ===")
    print(f"Fichier d'entrée:  {len(iq_data)*8/1024/1024:.1f} MB")
    print(f"Fichier de sortie: {len(iq_resampled)*8/1024/1024:.1f} MB")
    print(f"Amplitude moyenne: {np.abs(iq_resampled).mean():.3f}")
    print(f"Amplitude max:     {np.abs(iq_resampled).max():.3f}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fichier_2.5MHz.iq> [fichier_40kHz.iq]")
        print("\nConvertit un fichier I/Q de 2.5 MHz vers 40 kHz")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.iq', '_40khz.iq')

    resample_iq(input_file, output_file)
    print(f"\n✅ Conversion terminée: {output_file}")
