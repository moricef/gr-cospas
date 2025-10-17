#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualisation complète du signal WAV COSPAS-SARSAT
Affiche tout le signal temporel pour identifier les problèmes
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile

# Fichier WAV à analyser
wav_file = "/home/fab2/Developpement/COSPAS-SARSAT/Audio/enregistrement_balise_exercice_zonesud/gqrx_20250918_091106_406028000.wav"

print("="*70)
print("VISUALISATION COMPLÈTE DU SIGNAL WAV")
print("="*70)

# Lire le fichier WAV
sample_rate, audio_data = wavfile.read(wav_file)

# Convertir en float et normaliser
if audio_data.dtype == np.int16:
    audio_data = audio_data.astype(np.float32) / 32768.0
elif audio_data.dtype == np.int32:
    audio_data = audio_data.astype(np.float32) / 2147483648.0

duration = len(audio_data) / sample_rate
time_axis = np.arange(len(audio_data)) / sample_rate

print(f"\nFichier: {wav_file.split('/')[-1]}")
print(f"Durée: {duration:.2f} secondes")
print(f"Échantillons: {len(audio_data)}")
print(f"Fréquence: {sample_rate} Hz")
print(f"Amplitude min/max: {audio_data.min():.3f} / {audio_data.max():.3f}")

# Calculer l'enveloppe (amplitude RMS sur fenêtres)
window_size = int(sample_rate * 0.1)  # Fenêtre de 100 ms
envelope = []
envelope_time = []

for i in range(0, len(audio_data) - window_size, window_size // 4):
    window = audio_data[i:i+window_size]
    rms = np.sqrt(np.mean(window**2))
    envelope.append(rms)
    envelope_time.append(i / sample_rate)

envelope = np.array(envelope)
envelope_time = np.array(envelope_time)

# Trouver les zones d'activité (amplitude > seuil)
threshold = 0.1
active_regions = envelope > threshold

print(f"\nSeuil de détection: {threshold:.3f}")
print(f"Fenêtres actives: {np.sum(active_regions)} / {len(active_regions)}")

# Créer les graphiques
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 1. Signal complet
axes[0].plot(time_axis, audio_data, linewidth=0.5, alpha=0.7)
axes[0].set_xlabel('Temps (s)')
axes[0].set_ylabel('Amplitude')
axes[0].set_title(f'Signal audio complet ({duration:.1f} secondes)')
axes[0].grid(True, alpha=0.3)
axes[0].set_xlim([0, duration])

# Marquer les zones actives
for i, active in enumerate(active_regions):
    if active:
        axes[0].axvspan(envelope_time[i],
                       envelope_time[i] + 0.1 if i < len(envelope_time)-1 else duration,
                       alpha=0.2, color='green')

# 2. Enveloppe RMS
axes[1].plot(envelope_time, envelope, linewidth=2)
axes[1].axhline(threshold, color='r', linestyle='--', label=f'Seuil = {threshold}')
axes[1].set_xlabel('Temps (s)')
axes[1].set_ylabel('Amplitude RMS')
axes[1].set_title('Enveloppe du signal (fenêtre 100 ms)')
axes[1].grid(True, alpha=0.3)
axes[1].legend()
axes[1].set_xlim([0, duration])

# 3. Zoom sur les 5 dernières secondes (pour voir le bruit de fin)
zoom_start = max(0, duration - 5)
zoom_mask = time_axis >= zoom_start
axes[2].plot(time_axis[zoom_mask], audio_data[zoom_mask], linewidth=0.5)
axes[2].set_xlabel('Temps (s)')
axes[2].set_ylabel('Amplitude')
axes[2].set_title('Zoom sur les 5 dernières secondes (bruit NFM ?)')
axes[2].grid(True, alpha=0.3)
axes[2].set_xlim([zoom_start, duration])

# Statistiques par zone
print("\n" + "="*70)
print("STATISTIQUES PAR ZONE:")
print("="*70)

zones = [
    (0, 10, "Début (0-10s)"),
    (10, 20, "Milieu 1 (10-20s)"),
    (20, 30, "Milieu 2 (20-30s)"),
    (30, duration, "Fin (30s-fin)")
]

for start, end, label in zones:
    mask = (time_axis >= start) & (time_axis < end)
    zone_data = audio_data[mask]
    if len(zone_data) > 0:
        rms = np.sqrt(np.mean(zone_data**2))
        peak = np.max(np.abs(zone_data))
        print(f"{label:<20} : RMS={rms:.4f}  Peak={peak:.4f}")

plt.tight_layout()
print("\n" + "="*70)
print("Fermer la fenêtre pour terminer...")
print("="*70)
plt.show()
