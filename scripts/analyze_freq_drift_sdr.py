#!/usr/bin/env python3
"""
Analyse de la dérive de fréquence sur flux SDR en temps réel
Attend un burst COSPAS-SARSAT et analyse la porteuse
"""
from gnuradio import gr, blocks, filter
import numpy as np
import osmosdr
import time

import sys

SAMPLE_RATE = 240000  # RTL-SDR
DECIMATION = 6        # -> 40 kHz
FINAL_RATE = SAMPLE_RATE // DECIMATION
CENTER_FREQ = 403.040e6
CAPTURE_TIME = 120    # secondes de capture
PPM_CORRECTION = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0

print(f"Capture SDR: {CENTER_FREQ/1e6:.3f} MHz")
print(f"Sample rate: {SAMPLE_RATE} Hz -> décimé à {FINAL_RATE} Hz")
print(f"Correction PPM: {PPM_CORRECTION}")
print(f"Durée capture: {CAPTURE_TIME}s")

class BurstCapture(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)

        # Source RTL-SDR
        self.source = osmosdr.source(args="numchan=1")
        self.source.set_sample_rate(SAMPLE_RATE)
        self.source.set_center_freq(CENTER_FREQ)
        self.source.set_freq_corr(PPM_CORRECTION)
        self.source.set_gain_mode(False)
        self.source.set_gain(40)

        # Décimation
        self.decimator = filter.fir_filter_ccf(
            DECIMATION,
            filter.firdes.low_pass(1, SAMPLE_RATE, 16000, 4000)
        )

        # Pas de normalisation - garder amplitude réelle
        # self.normalize = blocks.multiply_const_cc(1.0/12.0)

        # Capture vers vecteur
        self.sink = blocks.vector_sink_c()

        self.connect(self.source, self.decimator, self.sink)

print("Démarrage capture...")
tb = BurstCapture()
tb.start()
time.sleep(CAPTURE_TIME)
tb.stop()
tb.wait()

samples = np.array(tb.sink.data())
print(f"Échantillons capturés: {len(samples)}")

# Détecter les bursts (amplitude > seuil)
amplitude = np.abs(samples)
# Seuil très bas - juste au dessus du bruit
threshold = np.percentile(amplitude, 95) * 0.3
print(f"Seuil de détection: {threshold:.6f}")
print(f"Amplitude: max={np.max(amplitude):.4f}, p95={np.percentile(amplitude, 95):.6f}")

# Trouver les bursts (minimum 200ms = 8000 échantillons pour un vrai burst)
in_burst = False
burst_starts = []
burst_start_candidate = 0
min_burst_samples = 8000  # 200ms @ 40kHz

for i in range(len(amplitude)):
    if not in_burst and amplitude[i] > threshold:
        burst_start_candidate = i
        in_burst = True
    elif in_burst and amplitude[i] < threshold * 0.3:
        burst_duration = i - burst_start_candidate
        if burst_duration >= min_burst_samples:
            burst_starts.append(burst_start_candidate)
        in_burst = False
if in_burst:
    burst_duration = len(amplitude) - burst_start_candidate
    if burst_duration >= min_burst_samples:
        burst_starts.append(burst_start_candidate)

print(f"Bursts détectés (>{min_burst_samples/FINAL_RATE*1000:.0f}ms): {len(burst_starts)}")

if len(burst_starts) == 0:
    print("Aucun burst détecté. Vérifiez la fréquence et le gain.")
    exit(1)

# Analyser chaque burst
for burst_idx, burst_start in enumerate(burst_starts[:5]):  # Max 5 bursts
    print(f"\n=== Burst #{burst_idx+1} (échantillon {burst_start}) ===")

    # Extraire la porteuse (6400 échantillons = 160ms)
    carrier_samples = 6400
    if burst_start + carrier_samples > len(samples):
        print("Burst tronqué, ignoré")
        continue

    carrier = samples[burst_start:burst_start + carrier_samples]

    # Phase unwrapped
    phase = np.angle(carrier)
    phase_unwrap = np.unwrap(phase)

    # Régression linéaire
    t = np.arange(len(phase_unwrap))
    coeffs_lin = np.polyfit(t, phase_unwrap, 1)
    freq_offset = coeffs_lin[0] / (2*np.pi) * FINAL_RATE

    # Régression quadratique
    coeffs_quad = np.polyfit(t, phase_unwrap, 2)
    freq_drift = 2*coeffs_quad[0] / (2*np.pi) * FINAL_RATE

    print(f"Offset fréquence: {freq_offset:.3f} Hz")
    print(f"Dérive: {freq_drift:.6f} Hz/s")
    print(f"Dérive sur 360ms: {freq_drift * 0.36:.6f} Hz")

    # Comparaison 2000 vs 6400 échantillons
    coeffs_2000 = np.polyfit(t[:2000], phase_unwrap[:2000], 1)
    freq_2000 = coeffs_2000[0] / (2*np.pi) * FINAL_RATE
    diff = abs(freq_offset - freq_2000)
    phase_error = diff * 0.36 * 2 * np.pi

    print(f"Estimation 2000 ech: {freq_2000:.3f} Hz")
    print(f"Estimation 6400 ech: {freq_offset:.3f} Hz")
    print(f"Différence: {diff:.4f} Hz -> erreur phase 360ms: {phase_error:.4f} rad")
