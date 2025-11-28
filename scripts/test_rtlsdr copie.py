#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rtlsdr.py - Test simple RTL-SDR → Detector → Router → Demod
Fréquence fixe pour tester la chaîne de démodulation

Usage: python3 test_rtlsdr.py [freq_MHz] [ppm] [timeout_s]
Exemple: python3 test_rtlsdr.py 403.040 0 60
"""

import sys
import time
from datetime import datetime, timezone
from gnuradio import gr, blocks, filter
from gnuradio import cospas


class test_rtlsdr_demod(gr.top_block):
    """Test RTL-SDR avec chaîne de démodulation complète"""

    def __init__(self, freq_mhz=403.040, sample_rate=40000, ppm=0):
        gr.top_block.__init__(self, "Test RTL-SDR Demod")

        self.sample_rate = sample_rate
        self.freq_hz = freq_mhz * 1e6
        self.ppm = ppm

        # RTL-SDR minimum sample rate ~225 kHz
        # Utiliser 240 kHz avec décimation par 6 pour obtenir 40 kHz
        rtl_sample_rate = 240000
        decimation = rtl_sample_rate // sample_rate  # 6

        # RTL-SDR Source
        try:
            import osmosdr
            self.rtl_source = osmosdr.source(args="rtl=0")
            self.rtl_source.set_sample_rate(rtl_sample_rate)
            self.rtl_source.set_center_freq(self.freq_hz)
            self.rtl_source.set_freq_corr(ppm)
            self.rtl_source.set_gain_mode(False)
            self.rtl_source.set_gain(40)
            self.rtl_source.set_if_gain(20)
            self.rtl_source.set_bb_gain(20)
            print(f"[RTL-SDR] {freq_mhz:.3f} MHz, {rtl_sample_rate} Hz → décimation {decimation}x → {sample_rate} Hz")
            print(f"[RTL-SDR] ppm={ppm}, gain=40")
        except ImportError:
            print("[ERREUR] Module osmosdr non disponible")
            print("         sudo apt install gr-osmosdr")
            sys.exit(1)

        # Décimateur (240 kHz → 40 kHz)
        # Filtre passe-bas pour éviter aliasing
        self.decimator = filter.fir_filter_ccf(
            decimation,
            filter.firdes.low_pass(1, rtl_sample_rate, sample_rate/2 * 0.8, sample_rate/2 * 0.2)
        )
        print(f"[DECIMATOR] {rtl_sample_rate} Hz → {sample_rate} Hz (facteur {decimation})")

        # Normalisation du signal RTL-SDR
        # RTL-SDR uint8 → float32 donne amplitude ~1.2, GQRX attend ~0.1
        # Facteur de normalisation ≈ 12
        normalization_factor = 1.0 / 12.0
        self.normalizer = blocks.multiply_const_cc(normalization_factor)
        print(f"[NORMALIZER] Facteur {normalization_factor:.4f} (amplitude GQRX)")

        # Burst Detector
        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate,
            buffer_duration_ms=2000,
            threshold=0.1,
            min_burst_duration_ms=200,
            debug_mode=True  # Debug ON
        )

        # Burst Router
        self.burst_router = cospas.burst_router(
            sample_rate=sample_rate,
            debug_mode=True  # Debug ON
        )

        # Démodulateur 1G
        self.demod_1g = cospas.cospas_sarsat_demodulator(
            sample_rate=sample_rate,
            debug_mode=True  # Debug ON
        )

        # Sinks
        self.null_sink_demod = blocks.null_sink(gr.sizeof_char)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        # Connexions
        self.connect(self.rtl_source, self.decimator)
        self.connect(self.decimator, self.normalizer)
        self.connect(self.normalizer, self.burst_detector)
        self.connect(self.burst_detector, self.burst_router)
        self.connect((self.burst_router, 0), self.demod_1g)
        self.connect(self.demod_1g, self.null_sink_demod)
        self.connect((self.burst_router, 1), self.null_sink_2g)

        print("[FLOWGRAPH] RTL-SDR → Decimator → Normalizer → Detector → Router → Demod 1G")

    def get_statistics(self):
        return {
            'bursts_detected': self.burst_detector.get_bursts_detected(),
            'bursts_1g': self.burst_router.get_bursts_1g(),
            'bursts_2g': self.burst_router.get_bursts_2g(),
            'frames_decoded': self.demod_1g.get_frames_decoded()
        }


def main():
    freq_mhz = 403.040  # Fréquence par défaut
    ppm = 0
    timeout_s = 60

    if len(sys.argv) >= 2:
        freq_mhz = float(sys.argv[1])
    if len(sys.argv) >= 3:
        ppm = float(sys.argv[2])
    if len(sys.argv) >= 4:
        timeout_s = int(sys.argv[3])

    print("=" * 60)
    print("TEST RTL-SDR → DEMODULATION COSPAS-SARSAT")
    print("=" * 60)
    print(f"Fréquence: {freq_mhz:.3f} MHz")
    print(f"PPM: {ppm}")
    print(f"Timeout: {timeout_s}s")
    print("=" * 60)

    tb = test_rtlsdr_demod(freq_mhz, 40000, ppm)

    try:
        utc_start = datetime.now(timezone.utc).strftime('%Hh%Mm%Ss')
        print(f"\n[START] {utc_start} UTC - Capture en cours...")
        print(f"[INFO] Ctrl+C pour arrêter\n")

        tb.start()

        # Afficher les stats périodiquement
        start_time = time.time()
        last_stats = None

        while time.time() - start_time < timeout_s:
            time.sleep(5)
            stats = tb.get_statistics()

            # Afficher seulement si changement
            if stats != last_stats:
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed:3d}s] Bursts={stats['bursts_detected']}, "
                      f"1G={stats['bursts_1g']}, 2G={stats['bursts_2g']}, "
                      f"Trames={stats['frames_decoded']}")
                last_stats = stats

        tb.stop()
        tb.wait()

        # Stats finales
        stats = tb.get_statistics()
        utc_end = datetime.now(timezone.utc).strftime('%Hh%Mm%Ss')

        print(f"\n{'='*60}")
        print(f"RÉSULTATS - {utc_end} UTC")
        print(f"{'='*60}")
        print(f"Bursts détectés:   {stats['bursts_detected']}")
        print(f"Bursts 1G routés:  {stats['bursts_1g']}")
        print(f"Bursts 2G routés:  {stats['bursts_2g']}")
        print(f"Trames démodulées: {stats['frames_decoded']}")
        print(f"{'='*60}")

        if stats['bursts_1g'] > 0:
            ratio = (stats['frames_decoded'] / stats['bursts_1g']) * 100
            print(f"Taux: {stats['frames_decoded']}/{stats['bursts_1g']} = {ratio:.1f}%")

    except KeyboardInterrupt:
        print("\n[STOP] Interruption")
        tb.stop()
        tb.wait()
        stats = tb.get_statistics()
        print(f"\nStats finales: Bursts={stats['bursts_detected']}, "
              f"Trames={stats['frames_decoded']}")


if __name__ == '__main__':
    main()
