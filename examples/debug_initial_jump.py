#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug du saut initial après le ré-échantillonnage
Vérifie pourquoi le décodeur GRC ne détecte pas le saut
"""

import numpy as np
from scipy import signal as scipy_signal

filename = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"

print("="*70)
print("DEBUG DU SAUT INITIAL APRÈS RÉ-ÉCHANTILLONNAGE")
print("="*70)

# Lire le signal original
data = np.fromfile(filename, dtype=np.float32)
I = data[0::2]
Q = data[1::2]
signal_40khz = I + 1j * Q

# Ré-échantillonner
signal_resampled = scipy_signal.resample_poly(signal_40khz, 4, 25)

# Paramètres
fs_resampled = 6400
carrier_duration = 0.160  # 160 ms
carrier_samples = int(carrier_duration * fs_resampled)

print(f"\nSignal ré-échantillonné à 6.4 kHz:")
print(f"  Échantillons: {len(signal_resampled)}")
print(f"  Échantillons de porteuse: {carrier_samples}")

# Analyser la porteuse et le saut
carrier_signal = signal_resampled[:carrier_samples]
after_carrier = signal_resampled[carrier_samples:carrier_samples+100]

phase_carrier = np.angle(carrier_signal)
phase_after = np.angle(after_carrier)

print(f"\nPhase pendant la porteuse:")
print(f"  Moyenne: {np.mean(phase_carrier):.3f} rad")
print(f"  Écart-type: {np.std(phase_carrier):.3f} rad")
print(f"  Min/Max: {phase_carrier.min():.3f} / {phase_carrier.max():.3f}")

print(f"\nPhase après la porteuse (100 premiers échantillons):")
print(f"  Moyenne: {np.mean(phase_after):.3f} rad")
print(f"  Écart-type: {np.std(phase_after):.3f} rad")
print(f"  Min/Max: {phase_after.min():.3f} / {phase_after.max():.3f}")

# Vérifier le saut initial selon la logique du décodeur
phase_avg_carrier = np.mean(phase_carrier[-100:])  # Moyenne des 100 derniers échantillons
phase_first_after = phase_after[0]

jump = abs(phase_first_after - phase_avg_carrier)
print(f"\nSaut initial détecté:")
print(f"  Phase moyenne porteuse: {phase_avg_carrier:.3f} rad")
print(f"  Phase premier échantillon: {phase_first_after:.3f} rad")
print(f"  Saut: {jump:.3f} rad")

# Paramètres du décodeur
JUMP_THRESHOLD = 0.8
MOD_PHASE = 1.1
print(f"\nSeuils du décodeur:")
print(f"  JUMP_THRESHOLD: {JUMP_THRESHOLD:.3f} rad")
print(f"  MOD_PHASE + 0.3: {MOD_PHASE + 0.3:.3f} rad")

if jump > JUMP_THRESHOLD and jump < (MOD_PHASE + 0.3):
    print(f"  ✅ Saut détectable (entre {JUMP_THRESHOLD} et {MOD_PHASE + 0.3})")
else:
    print(f"  ❌ Saut NON détectable")
    if jump <= JUMP_THRESHOLD:
        print(f"     → Trop petit (< {JUMP_THRESHOLD})")
    else:
        print(f"     → Trop grand (> {MOD_PHASE + 0.3})")

# Chercher où le saut apparaît vraiment
print(f"\nRecherche du vrai saut...")
for i in range(carrier_samples-10, carrier_samples+50):
    if i < len(signal_resampled):
        phase = np.angle(signal_resampled[i])
        jump_from_carrier = abs(phase - phase_avg_carrier)
        if jump_from_carrier > JUMP_THRESHOLD:
            print(f"  Échantillon {i}: phase={phase:.3f}, saut={jump_from_carrier:.3f}")
            if i >= carrier_samples:
                print(f"    → Saut à l'échantillon {i - carrier_samples} APRÈS la porteuse")
                break

print("="*70)
