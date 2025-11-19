#!/usr/bin/env python3
"""
Script de rééchantillonnage de fichiers IQ
Convertit un fichier IQ d'un taux d'échantillonnage à un autre
"""

import numpy as np
from scipy import signal
import sys
from math import gcd

def resample_iq_file(input_file, output_file, input_rate, output_rate):
    """
    Rééchantillonne un fichier IQ complex64

    Args:
        input_file: Chemin du fichier IQ source
        output_file: Chemin du fichier IQ de sortie
        input_rate: Taux d'échantillonnage source (Hz)
        output_rate: Taux d'échantillonnage cible (Hz)
    """
    # Calcul du ratio de rééchantillonnage
    g = gcd(int(input_rate), int(output_rate))
    up = int(output_rate / g)
    down = int(input_rate / g)

    print(f"[RESAMPLE] Lecture de {input_file}...")
    iq_data = np.fromfile(input_file, dtype=np.complex64)
    print(f"[RESAMPLE] {len(iq_data)} échantillons lus à {input_rate} Hz")

    # Séparation I et Q
    i_data = iq_data.real
    q_data = iq_data.imag

    print(f"[RESAMPLE] Rééchantillonnage {input_rate} Hz -> {output_rate} Hz (up={up}, down={down})...")
    # Rééchantillonnage avec filtre polyphase
    i_resampled = signal.resample_poly(i_data, up, down)
    q_resampled = signal.resample_poly(q_data, up, down)

    # Reconstruction complexe
    iq_resampled = i_resampled + 1j * q_resampled

    print(f"[RESAMPLE] {len(iq_resampled)} échantillons après rééchantillonnage")
    print(f"[RESAMPLE] Écriture de {output_file}...")
    iq_resampled.astype(np.complex64).tofile(output_file)

    print(f"[RESAMPLE] ✓ Terminé")
    print(f"  Entrée:  {len(iq_data)} échantillons @ {input_rate} Hz")
    print(f"  Sortie:  {len(iq_resampled)} échantillons @ {output_rate} Hz")
    print(f"  Ratio:   {len(iq_resampled)/len(iq_data):.6f}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: resample_iq.py <input.iq> <output.iq> <input_rate> <output_rate>")
        print("Exemple: resample_iq.py input_1800000.iq output_40000.iq 1800000 40000")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    input_rate = int(sys.argv[3])
    output_rate = int(sys.argv[4])

    resample_iq_file(input_file, output_file, input_rate, output_rate)
