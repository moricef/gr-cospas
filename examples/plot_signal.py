#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualisation du signal généré par le générateur COSPAS-SARSAT
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/python')

from gnuradio import cospas

def main():
    # Créer le générateur avec 1 octet de données (8 bits à '1')
    test_data = bytes([0xFF])
    gen = cospas.cospas_generator(data_bytes=test_data, repeat=False)

    frame = gen.frame

    # Extraire I, Q et phase
    I = np.real(frame)
    Q = np.imag(frame)
    phase = np.angle(frame)
    magnitude = np.abs(frame)

    # Axe temporel en millisecondes
    time_ms = np.arange(len(frame)) / 6.4  # 6400 Hz = 6.4 échantillons/ms

    # Créer les graphiques
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # Graphique 1 : I et Q
    axes[0].plot(time_ms, I, 'b-', label='I (partie réelle)', linewidth=0.8)
    axes[0].plot(time_ms, Q, 'r-', label='Q (partie imaginaire)', linewidth=0.8)
    axes[0].axvline(x=160, color='green', linestyle='--', label='Fin porteuse')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlabel('Temps (ms)')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Signal I/Q')
    axes[0].legend()
    axes[0].set_xlim([0, time_ms[-1]])

    # Graphique 2 : Phase
    axes[1].plot(time_ms, phase, 'g-', linewidth=0.8)
    axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1].axhline(y=1.1, color='red', linestyle='--', label='±1.1 rad', linewidth=1)
    axes[1].axhline(y=-1.1, color='red', linestyle='--', linewidth=1)
    axes[1].axvline(x=160, color='green', linestyle='--', label='Fin porteuse')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlabel('Temps (ms)')
    axes[1].set_ylabel('Phase (radians)')
    axes[1].set_title('Phase du signal')
    axes[1].legend()
    axes[1].set_xlim([0, time_ms[-1]])
    axes[1].set_ylim([-3.5, 3.5])

    # Graphique 3 : Magnitude
    axes[2].plot(time_ms, magnitude, 'purple', linewidth=0.8)
    axes[2].axvline(x=160, color='green', linestyle='--', label='Fin porteuse')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlabel('Temps (ms)')
    axes[2].set_ylabel('Magnitude')
    axes[2].set_title('Magnitude du signal')
    axes[2].legend()
    axes[2].set_xlim([0, time_ms[-1]])

    # Graphique 4 : Zoom sur les premiers bits (160-180 ms)
    zoom_start_idx = 1024  # Début du préambule
    zoom_end_idx = 1024 + 3 * 16  # 3 bits
    axes[3].plot(time_ms[zoom_start_idx:zoom_end_idx],
                 phase[zoom_start_idx:zoom_end_idx],
                 'g.-', linewidth=1, markersize=4)
    axes[3].axhline(y=1.1, color='red', linestyle='--', label='±1.1 rad', linewidth=1)
    axes[3].axhline(y=-1.1, color='red', linestyle='--', linewidth=1)

    # Marquer les limites de bits
    for i in range(4):
        bit_time = 160 + i * 2.5
        axes[3].axvline(x=bit_time, color='blue', linestyle=':', alpha=0.5)

    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlabel('Temps (ms)')
    axes[3].set_ylabel('Phase (radians)')
    axes[3].set_title('Zoom sur les 3 premiers bits du préambule (bits "1")')
    axes[3].legend()
    axes[3].set_ylim([-2, 2])

    plt.tight_layout()
    plt.savefig('/tmp/cospas_signal_analysis.png', dpi=150)
    print("Graphique sauvegardé dans : /tmp/cospas_signal_analysis.png")
    plt.show()

if __name__ == '__main__':
    main()
