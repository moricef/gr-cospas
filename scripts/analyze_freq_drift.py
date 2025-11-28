#!/usr/bin/env python3
"""
Analyse de la dérive de fréquence sur la porteuse COSPAS-SARSAT
"""
import numpy as np

# Paramètres
SAMPLE_RATE = 40000
FILE = 'examples/1g/gqrx_FFE2F8E39048D158AC01E3AA482856824CE_40000.iq'

# Lire le fichier IQ
raw = np.fromfile(FILE, dtype=np.complex64)
print(f"Fichier: {FILE}")
print(f"Échantillons totaux: {len(raw)}")

# Détecter le début du burst (amplitude > seuil)
amplitude = np.abs(raw)
threshold = 0.02
burst_start = np.where(amplitude > threshold)[0][0]
print(f"\nBurst détecté à l'échantillon: {burst_start}")

# Extraire la porteuse (6400 échantillons = 160ms)
carrier_samples = 6400
carrier = raw[burst_start:burst_start + carrier_samples]
print(f"Porteuse: {carrier_samples} échantillons = {carrier_samples/SAMPLE_RATE*1000:.1f} ms")

# Calculer la phase unwrapped
phase = np.angle(carrier)
phase_unwrap = np.unwrap(phase)

# Régression linéaire : phase = a*t + b
t = np.arange(len(phase_unwrap))
coeffs_lin = np.polyfit(t, phase_unwrap, 1)
freq_offset = coeffs_lin[0] / (2*np.pi) * SAMPLE_RATE

print(f"\n=== Régression linéaire ===")
print(f"Phase = {coeffs_lin[0]:.8f}*t + {coeffs_lin[1]:.4f}")
print(f"Offset de fréquence: {freq_offset:.3f} Hz")

# Régression quadratique : phase = a*t² + b*t + c
coeffs_quad = np.polyfit(t, phase_unwrap, 2)
freq_drift = 2*coeffs_quad[0] / (2*np.pi) * SAMPLE_RATE  # Hz/échantillon -> Hz/s

print(f"\n=== Régression quadratique ===")
print(f"Phase = {coeffs_quad[0]:.10f}*t² + {coeffs_quad[1]:.8f}*t + {coeffs_quad[2]:.4f}")
print(f"Offset initial: {coeffs_quad[1] / (2*np.pi) * SAMPLE_RATE:.3f} Hz")
print(f"Dérive: {freq_drift:.6f} Hz/s")
print(f"Dérive sur 360ms (durée trame): {freq_drift * 0.36:.6f} Hz")

# Erreur résiduelle
phase_fit_lin = np.polyval(coeffs_lin, t)
phase_fit_quad = np.polyval(coeffs_quad, t)
error_lin = np.std(phase_unwrap - phase_fit_lin)
error_quad = np.std(phase_unwrap - phase_fit_quad)

print(f"\n=== Qualité du fit ===")
print(f"Erreur std (linéaire): {error_lin:.6f} rad")
print(f"Erreur std (quadratique): {error_quad:.6f} rad")

# Comparer avec estimation sur 2000 échantillons
phase_2000 = phase_unwrap[:2000]
t_2000 = t[:2000]
coeffs_2000 = np.polyfit(t_2000, phase_2000, 1)
freq_2000 = coeffs_2000[0] / (2*np.pi) * SAMPLE_RATE

print(f"\n=== Comparaison ===")
print(f"Estimation sur 2000 ech: {freq_2000:.3f} Hz")
print(f"Estimation sur 6400 ech: {freq_offset:.3f} Hz")
print(f"Différence: {abs(freq_offset - freq_2000):.3f} Hz")

# Impact sur la phase finale
phase_error_360ms = abs(freq_offset - freq_2000) * 0.36 * 2 * np.pi
print(f"Erreur de phase après 360ms: {phase_error_360ms:.4f} rad ({phase_error_360ms*180/np.pi:.2f}°)")
