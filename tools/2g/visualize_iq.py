#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualiseur de Fichiers IQ COSPAS-SARSAT 2G
============================================

Affiche les caractéristiques d'un fichier IQ généré pour balise SGB.

Usage:
    ./visualize_iq.py <fichier.iq>
    ./visualize_iq.py trame_france_epirb.iq --plot
"""

import numpy as np
import argparse
import sys

def analyze_iq_file(filename, sample_rate=400000):
    """
    Analyse un fichier IQ et affiche ses caractéristiques.

    Args:
        filename: Chemin vers le fichier .iq
        sample_rate: Fréquence d'échantillonnage (Hz)
    """
    try:
        # Charger le fichier IQ
        iq_data = np.fromfile(filename, dtype=np.complex64)
    except FileNotFoundError:
        print(f"Erreur: Fichier '{filename}' introuvable", file=sys.stderr)
        sys.exit(1)

    if len(iq_data) == 0:
        print(f"Erreur: Fichier vide", file=sys.stderr)
        sys.exit(1)

    # Statistiques
    duration = len(iq_data) / sample_rate
    file_size_mb = iq_data.nbytes / (1024 * 1024)

    i_signal = iq_data.real
    q_signal = iq_data.imag

    magnitude = np.abs(iq_data)
    phase = np.angle(iq_data)

    # Calcul puissance
    power_i = np.mean(i_signal**2)
    power_q = np.mean(q_signal**2)
    power_total = power_i + power_q

    print(f"\n{'='*70}")
    print(f"  Analyse Fichier IQ - {filename}")
    print(f"{'='*70}\n")

    print("Informations Générales:")
    print(f"  Échantillons: {len(iq_data):,}")
    print(f"  Sample rate: {sample_rate:,} Hz")
    print(f"  Durée: {duration:.3f} s")
    print(f"  Taille: {file_size_mb:.2f} MB\n")

    print("Canal I (In-phase):")
    print(f"  Min: {i_signal.min():.6f}")
    print(f"  Max: {i_signal.max():.6f}")
    print(f"  Moyenne: {i_signal.mean():.6f}")
    print(f"  Écart-type: {i_signal.std():.6f}")
    print(f"  Puissance: {power_i:.6f}\n")

    print("Canal Q (Quadrature):")
    print(f"  Min: {q_signal.min():.6f}")
    print(f"  Max: {q_signal.max():.6f}")
    print(f"  Moyenne: {q_signal.mean():.6f}")
    print(f"  Écart-type: {q_signal.std():.6f}")
    print(f"  Puissance: {power_q:.6f}\n")

    print("Signal Complexe:")
    print(f"  Magnitude min: {magnitude.min():.6f}")
    print(f"  Magnitude max: {magnitude.max():.6f}")
    print(f"  Magnitude moyenne: {magnitude.mean():.6f}")
    print(f"  Phase min: {np.degrees(phase.min()):.1f}°")
    print(f"  Phase max: {np.degrees(phase.max()):.1f}°")
    print(f"  Puissance totale: {power_total:.6f}\n")

    # Détection OQPSK
    # Vérifier si les valeurs I et Q sont proches de ±1/√2 ≈ ±0.707
    expected_level = 1.0 / np.sqrt(2)
    i_levels = np.unique(np.round(i_signal, 3))
    q_levels = np.unique(np.round(q_signal, 3))

    print("Vérification OQPSK:")
    print(f"  Niveaux I distincts: {len(i_levels)}")
    print(f"  Niveaux Q distincts: {len(q_levels)}")
    print(f"  Niveau attendu: ±{expected_level:.3f}")

    if len(i_levels) <= 4 and len(q_levels) <= 4:
        print(f"  ✓ Signal OQPSK détecté (niveaux discrets)")
    else:
        print(f"  ⚠️  Signal continu ou bruité")

    # Estimation chip rate
    # Détecter les transitions
    i_diff = np.diff(i_signal)
    transitions = np.where(np.abs(i_diff) > 0.5)[0]

    if len(transitions) > 1:
        avg_chip_duration = np.mean(np.diff(transitions))
        estimated_chip_rate = sample_rate / avg_chip_duration
        print(f"\n  Chip rate estimé: {estimated_chip_rate:.0f} chips/s")
        print(f"  Chip rate attendu: 38,400 chips/s")

        if abs(estimated_chip_rate - 38400) < 1000:
            print(f"  ✓ Chip rate conforme T.018")
        else:
            print(f"  ⚠️  Chip rate différent")

    print(f"\n{'='*70}\n")

    return iq_data

def plot_iq_signal(iq_data, sample_rate=400000, max_samples=5000):
    """
    Affiche les graphiques du signal IQ.

    Args:
        iq_data: Signal IQ (np.array complexe)
        sample_rate: Fréquence d'échantillonnage
        max_samples: Nombre max d'échantillons à afficher
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Erreur: matplotlib non installé", file=sys.stderr)
        print("Installation: pip install matplotlib", file=sys.stderr)
        return

    # Limiter le nombre d'échantillons pour l'affichage
    n_samples = min(len(iq_data), max_samples)
    iq_subset = iq_data[:n_samples]
    time = np.arange(n_samples) / sample_rate * 1000  # ms

    fig = plt.figure(figsize=(14, 10))

    # Subplot 1: I channel
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(time, iq_subset.real, 'b-', linewidth=0.5)
    ax1.set_xlabel('Temps (ms)')
    ax1.set_ylabel('Amplitude')
    ax1.set_title('Canal I (In-phase)')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)

    # Subplot 2: Q channel
    ax2 = plt.subplot(3, 2, 2)
    ax2.plot(time, iq_subset.imag, 'r-', linewidth=0.5)
    ax2.set_xlabel('Temps (ms)')
    ax2.set_ylabel('Amplitude')
    ax2.set_title('Canal Q (Quadrature)')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.3)

    # Subplot 3: Constellation IQ
    ax3 = plt.subplot(3, 2, 3)
    # Échantillonner pour éviter trop de points
    step = max(1, len(iq_data) // 10000)
    ax3.scatter(iq_data.real[::step], iq_data.imag[::step],
                alpha=0.3, s=1, c='blue')
    ax3.set_xlabel('I')
    ax3.set_ylabel('Q')
    ax3.set_title('Constellation IQ')
    ax3.grid(True, alpha=0.3)
    ax3.axis('equal')
    ax3.axhline(y=0, color='k', linestyle='-', alpha=0.2)
    ax3.axvline(x=0, color='k', linestyle='-', alpha=0.2)

    # Subplot 4: Magnitude
    ax4 = plt.subplot(3, 2, 4)
    magnitude = np.abs(iq_subset)
    ax4.plot(time, magnitude, 'g-', linewidth=0.5)
    ax4.set_xlabel('Temps (ms)')
    ax4.set_ylabel('Magnitude')
    ax4.set_title('Magnitude (|IQ|)')
    ax4.grid(True, alpha=0.3)

    # Subplot 5: Phase
    ax5 = plt.subplot(3, 2, 5)
    phase = np.angle(iq_subset)
    ax5.plot(time, np.degrees(phase), 'm-', linewidth=0.5)
    ax5.set_xlabel('Temps (ms)')
    ax5.set_ylabel('Phase (degrés)')
    ax5.set_title('Phase')
    ax5.grid(True, alpha=0.3)
    ax5.axhline(y=0, color='k', linestyle='--', alpha=0.3)

    # Subplot 6: Spectre FFT
    ax6 = plt.subplot(3, 2, 6)
    # FFT sur une fenêtre
    fft_size = min(8192, len(iq_data))
    fft_data = iq_data[:fft_size]
    fft_result = np.fft.fftshift(np.fft.fft(fft_data))
    fft_freq = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/sample_rate)) / 1000  # kHz
    fft_mag = 20 * np.log10(np.abs(fft_result) + 1e-10)

    ax6.plot(fft_freq, fft_mag, 'c-', linewidth=0.5)
    ax6.set_xlabel('Fréquence (kHz)')
    ax6.set_ylabel('Magnitude (dB)')
    ax6.set_title('Spectre FFT')
    ax6.grid(True, alpha=0.3)
    ax6.set_xlim([-50, 50])

    plt.tight_layout()
    plt.show()

def main():
    parser = argparse.ArgumentParser(
        description='Visualiseur de fichiers IQ COSPAS-SARSAT 2G',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s trame_france_epirb.iq
  %(prog)s trame_france_epirb.iq --plot
  %(prog)s trame_france_epirb.iq -s 480000 --plot
        """
    )

    parser.add_argument('fichier',
                       help='Fichier IQ à analyser')
    parser.add_argument('-s', '--sample-rate',
                       type=int,
                       default=400000,
                       help='Sample rate Hz (défaut: 400000)')
    parser.add_argument('-p', '--plot',
                       action='store_true',
                       help='Afficher les graphiques (nécessite matplotlib)')
    parser.add_argument('-n', '--max-samples',
                       type=int,
                       default=5000,
                       help='Nombre max d\'échantillons pour les plots (défaut: 5000)')

    args = parser.parse_args()

    # Analyser le fichier
    iq_data = analyze_iq_file(args.fichier, args.sample_rate)

    # Afficher les plots si demandé
    if args.plot:
        plot_iq_signal(iq_data, args.sample_rate, args.max_samples)

if __name__ == '__main__':
    main()
