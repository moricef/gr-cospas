#!/usr/bin/env python3
"""
Script de visualisation de fichiers IQ
Affiche amplitude, phase, spectrogramme
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import sys

def visualize_iq(filename, sample_rate, start_sample=0, num_samples=None):
    """
    Visualise un fichier IQ

    Args:
        filename: Chemin du fichier IQ
        sample_rate: Taux d'échantillonnage (Hz)
        start_sample: Échantillon de départ
        num_samples: Nombre d'échantillons à visualiser (None = tout)
    """
    print(f"[VIZ] Lecture de {filename}...")
    iq_data = np.fromfile(filename, dtype=np.complex64)

    if num_samples is None:
        num_samples = len(iq_data) - start_sample

    iq_data = iq_data[start_sample:start_sample+num_samples]

    print(f"[VIZ] {len(iq_data)} échantillons @ {sample_rate} Hz")
    print(f"[VIZ] Amplitude max: {np.max(np.abs(iq_data)):.6f}")
    print(f"[VIZ] Amplitude moyenne: {np.mean(np.abs(iq_data)):.6f}")

    # Axe temporel
    t = np.arange(len(iq_data)) / sample_rate

    # Créer la figure avec 4 sous-graphiques
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    fig.suptitle(f'Visualisation IQ: {filename}', fontsize=14)

    # 1. Amplitude
    amplitude = np.abs(iq_data)
    axes[0].plot(t * 1000, amplitude, linewidth=0.5)
    axes[0].set_ylabel('Amplitude')
    axes[0].set_xlabel('Temps (ms)')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title('Amplitude du signal')

    # 2. Phase
    phase = np.angle(iq_data)
    axes[1].plot(t * 1000, phase, linewidth=0.5)
    axes[1].set_ylabel('Phase (rad)')
    axes[1].set_xlabel('Temps (ms)')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title('Phase du signal')
    axes[1].set_ylim([-np.pi, np.pi])

    # 3. Constellation I/Q
    axes[2].plot(iq_data.real, iq_data.imag, '.', markersize=1, alpha=0.3)
    axes[2].set_xlabel('I (Real)')
    axes[2].set_ylabel('Q (Imag)')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_title('Constellation I/Q')
    axes[2].axis('equal')

    # 4. Spectrogramme
    f, t_spec, Sxx = signal.spectrogram(iq_data, fs=sample_rate, nperseg=1024)
    axes[3].pcolormesh(t_spec * 1000, f / 1000, 10 * np.log10(Sxx + 1e-10),
                       shading='gouraud', cmap='viridis')
    axes[3].set_ylabel('Fréquence (kHz)')
    axes[3].set_xlabel('Temps (ms)')
    axes[3].set_title('Spectrogramme')

    plt.tight_layout()

    # Sauvegarder
    output_file = filename.replace('.iq', '_plot.png').replace('.raw', '_plot.png')
    plt.savefig(output_file, dpi=150)
    print(f"[VIZ] Graphique sauvegardé: {output_file}")

    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: visualize_iq.py <fichier.iq> <sample_rate> [start_sample] [num_samples]")
        print("Exemple: visualize_iq.py capture.iq 40000")
        print("Exemple: visualize_iq.py capture.iq 40000 10000 50000")
        sys.exit(1)

    filename = sys.argv[1]
    sample_rate = int(sys.argv[2])
    start_sample = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    num_samples = int(sys.argv[4]) if len(sys.argv) > 4 else None

    visualize_iq(filename, sample_rate, start_sample, num_samples)
