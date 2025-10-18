#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse d'un fichier I/Q généré par Matlab
Vérifie la structure et les caractéristiques du signal
"""

import numpy as np
import matplotlib.pyplot as plt

def analyze_iq_file(filename, fs=40000):
    """Analyse un fichier I/Q float32"""

    print("="*70)
    print("ANALYSE FICHIER I/Q MATLAB")
    print("="*70)

    # Lire le fichier (float32 entrelacé: I, Q, I, Q, ...)
    data = np.fromfile(filename, dtype=np.float32)

    # Séparer I et Q
    I = data[0::2]
    Q = data[1::2]

    # Signal complexe
    signal = I + 1j * Q

    num_samples = len(signal)
    duration = num_samples / fs

    print(f"\nFichier: {filename.split('/')[-1]}")
    print(f"Échantillons: {num_samples}")
    print(f"Fréquence échantillonnage: {fs} Hz")
    print(f"Durée: {duration:.3f} s")
    print(f"\nAmplitude I: min={I.min():.3f}, max={I.max():.3f}")
    print(f"Amplitude Q: min={Q.min():.3f}, max={Q.max():.3f}")
    print(f"Magnitude: min={np.abs(signal).min():.3f}, max={np.abs(signal).max():.3f}")

    # Calculer la phase
    phase = np.angle(signal)
    phase_diff = np.diff(phase)

    # Unwrap phase differences
    phase_diff = np.where(phase_diff > np.pi, phase_diff - 2*np.pi, phase_diff)
    phase_diff = np.where(phase_diff < -np.pi, phase_diff + 2*np.pi, phase_diff)

    print(f"\nPhase: min={phase.min():.3f}, max={phase.max():.3f}")
    print(f"Diff phase: min={phase_diff.min():.3f}, max={phase_diff.max():.3f}")

    # Détecter la structure (porteuse + données)
    # La porteuse devrait avoir une phase constante
    phase_std = np.std(phase_diff[:int(0.16 * fs)])  # Premiers 160 ms
    print(f"\nÉcart-type phase diff (porteuse): {phase_std:.6f}")

    # Chercher les transitions significatives
    threshold = 0.5
    transitions = np.where(np.abs(phase_diff) > threshold)[0]
    print(f"Transitions > {threshold} rad: {len(transitions)}")

    if len(transitions) > 0:
        first_transition = transitions[0]
        print(f"Première transition à l'échantillon {first_transition} ({first_transition/fs*1000:.1f} ms)")

        # Analyser l'espacement des transitions (devrait être ~100 échantillons)
        if len(transitions) > 1:
            spacings = np.diff(transitions)
            print(f"Espacement moyen: {spacings.mean():.1f} échantillons")
            print(f"Espacement attendu: {fs/400:.1f} échantillons/bit")

    # Afficher les premiers échantillons
    print(f"\nPremiers 10 échantillons:")
    for i in range(min(10, len(signal))):
        print(f"  {i:3d}: I={I[i]:7.4f} Q={Q[i]:7.4f} mag={np.abs(signal[i]):7.4f} phase={phase[i]:7.4f}")

    # Graphiques
    fig, axes = plt.subplots(4, 1, figsize=(14, 10))

    time = np.arange(num_samples) / fs

    # 1. Signal I/Q
    axes[0].plot(time, I, 'b-', label='I', linewidth=0.5)
    axes[0].plot(time, Q, 'r-', label='Q', linewidth=0.5)
    axes[0].set_xlabel('Temps (s)')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Signal I/Q')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim([0, min(0.5, duration)])

    # 2. Magnitude
    axes[1].plot(time, np.abs(signal), 'g-', linewidth=0.5)
    axes[1].set_xlabel('Temps (s)')
    axes[1].set_ylabel('Magnitude')
    axes[1].set_title('Magnitude du signal')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim([0, min(0.5, duration)])

    # 3. Phase
    axes[2].plot(time, phase, 'purple', linewidth=0.5)
    axes[2].set_xlabel('Temps (s)')
    axes[2].set_ylabel('Phase (rad)')
    axes[2].set_title('Phase instantanée')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim([0, min(0.5, duration)])
    axes[2].axhline(1.1, color='r', linestyle='--', alpha=0.5, label='±1.1 rad')
    axes[2].axhline(-1.1, color='r', linestyle='--', alpha=0.5)
    axes[2].legend()

    # 4. Différence de phase (transitions)
    axes[3].plot(time[1:], phase_diff, 'orange', linewidth=0.5)
    axes[3].set_xlabel('Temps (s)')
    axes[3].set_ylabel('Δ Phase (rad)')
    axes[3].set_title('Transitions de phase (dérivée)')
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlim([0, min(0.5, duration)])
    axes[3].axhline(threshold, color='r', linestyle='--', alpha=0.5, label=f'Seuil ±{threshold} rad')
    axes[3].axhline(-threshold, color='r', linestyle='--', alpha=0.5)
    axes[3].legend()

    plt.tight_layout()
    print("\n" + "="*70)
    print("Fermer la fenêtre graphique pour continuer...")
    print("="*70)
    plt.show()

def main():
    import sys

    if len(sys.argv) < 2:
        filename = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"
        print(f"Usage: {sys.argv[0]} <fichier.iq> [sample_rate]")
        print(f"Utilisation du fichier par défaut\n")
    else:
        filename = sys.argv[1]

    fs = 40000  # Fréquence du fichier Matlab
    if len(sys.argv) >= 3:
        fs = int(sys.argv[2])

    analyze_iq_file(filename, fs)

if __name__ == '__main__':
    main()
