#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rtlsdr.py - Test simple RTL-SDR -> Detector -> Router -> Demod
Frequence fixe pour tester la chaine de demodulation

Usage:
  python3 test_rtlsdr.py [freq_MHz] [ppm] [timeout_s] 2>&1 | tee logs_tracking_m-20_g0.2-0.1_YYYYMMDD_HHMMSS.log

Exemple:
  python3 test_rtlsdr.py 403.040 0 300 2>&1 | tee logs_tracking_m-20_g0.2-0.1_$(date +%Y%m%d_%H%M%S).log
"""

import sys
import time
import re
from datetime import datetime, timezone
from gnuradio import gr, blocks, filter
from gnuradio import cospas


class test_rtlsdr_demod(gr.top_block):
    """Test RTL-SDR avec chaine de demodulation complete"""

    def __init__(self, freq_mhz=403.040, sample_rate=40000, ppm=0):
        gr.top_block.__init__(self, "Test RTL-SDR Demod")
        self.sample_rate = sample_rate
        self.freq_hz = freq_mhz * 1e6
        self.ppm = ppm

        # Reference frame pour comparaison
        self.ref_frame = "FFFE2F8E39048D158AC01E3AA482856824CE"
        self.frames_ok = 0
        self.frames_error = 0
        self.demodulated_frames = []
        # RTL-SDR minimum sample rate ~225 kHz
        # Utiliser 240 kHz avec decimation par 6 pour obtenir 40 kHz
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
            print(f"[RTL-SDR] {freq_mhz:.3f} MHz, {rtl_sample_rate} Hz -> decimation {decimation}x -> {sample_rate} Hz")
            print(f"[RTL-SDR] ppm={ppm}, gain=40")
        except ImportError:
            print("[ERREUR] Module osmosdr non disponible")
            print("         sudo apt install gr-osmosdr")
            sys.exit(1)
        # Decimateur (240 kHz -> 40 kHz)
        # Filtre passe-bas pour eviter aliasing
        self.decimator = filter.fir_filter_ccf(
            decimation,
            filter.firdes.low_pass(1, rtl_sample_rate, sample_rate/2 * 0.8, sample_rate/2 * 0.2)
        )
        print(f"[DECIMATOR] {rtl_sample_rate} Hz -> {sample_rate} Hz (facteur {decimation})")

        # Filtre passe-bas pour COSPAS-SARSAT
        # Signal BPSK 400 bps + offset frequence + Manchester encoding occupe ~±10 kHz
        # 20 kHz donne les meilleurs resultats (68% vs 50% avec 10 kHz)
        bandpass_high = 20000    # 20 kHz
        transition_width = 2000  # 2 kHz de transition
        self.bandpass = filter.fir_filter_ccf(
            1,
            filter.firdes.low_pass(1, sample_rate, bandpass_high, transition_width)
        )
        print(f"[LOWPASS] DC a {bandpass_high/1000:.0f} kHz (bande etroite anti-bruit)")

        # Normalisation du signal RTL-SDR
        # RTL-SDR uint8 -> float32 donne amplitude ~1.2, GQRX attend ~0.1
        # Augmente a 0.25 pour ameliorer la robustesse en fin de burst
        normalization_factor = 0.15
        self.normalizer = blocks.multiply_const_cc(normalization_factor)
        print(f"[NORMALIZER] Facteur {normalization_factor:.4f} (amplitude augmentee x3)")
        
        # Burst Detector
        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate,
            buffer_duration_ms=2000,
            threshold=0.05,  # Reduit de 0.1 a 0.05 pour capturer signal faible en fin de burst
            min_burst_duration_ms=200,
            debug_mode=False  # Debug OFF
        )

        # Burst Router
        self.burst_router = cospas.burst_router(
            sample_rate=sample_rate,
            debug_mode=False  # Debug OFF
        )

        # Demodulateur 1G
        self.demod_1g = cospas.cospas_sarsat_demodulator(
            sample_rate=sample_rate,
            debug_mode=False  # Debug OFF - garde seulement les logs essentiels
        )
        
        # Sinks
        self.null_sink_1g = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)
        
        # Connexions
        self.connect(self.rtl_source, self.decimator)
        self.connect(self.decimator, self.bandpass)
        self.connect(self.bandpass, self.normalizer)
        self.connect(self.normalizer, self.burst_detector)
        self.connect(self.burst_detector, self.burst_router)
        
        self.msg_connect((self.burst_detector, "bursts"), (self.burst_router, "bursts"))
        self.msg_connect((self.burst_router, "bursts_1g"), (self.demod_1g, "bursts"))
        
        self.connect((self.burst_router, 0), self.null_sink_1g)  # Sortie 1G
        self.connect((self.burst_router, 1), self.null_sink_2g)
        print("[FLOWGRAPH] RTL-SDR -> Decimator -> Bandpass -> Normalizer -> Detector -> Router -> Demod 1G")

    def get_statistics(self):
        return {
            'bursts_detected': self.burst_detector.get_bursts_detected(),
            'bursts_1g': self.burst_router.get_bursts_1g(),
            'bursts_2g': self.burst_router.get_bursts_2g(),
            'frames_decoded': self.demod_1g.get_frames_decoded()
        }

def main():
    freq_mhz = 403.040  # Frequence par defaut
    ppm = 0
    timeout_s = 60

    if len(sys.argv) >= 2:
        freq_mhz = float(sys.argv[1])
    if len(sys.argv) >= 3:
        ppm = float(sys.argv[2])
    if len(sys.argv) >= 4:
        timeout_s = int(sys.argv[3])

    print("=" * 60)
    print("TEST RTL-SDR -> DEMODULATION COSPAS-SARSAT")
    print("=" * 60)
    print(f"Frequence: {freq_mhz:.3f} MHz")
    print(f"PPM: {ppm}")
    print(f"Timeout: {timeout_s}s")
    print("=" * 60)
    print("Tracking params: d_mu_init=-20, gains=0.2/0.1, bounds=±25")
    print("=" * 60)

    # Force unbuffered output pour que les logs C++ apparaissent immediatement
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    tb = test_rtlsdr_demod(freq_mhz=freq_mhz, sample_rate=40000, ppm=ppm)
    try:
        utc_start = datetime.now(timezone.utc).strftime('%Hh%Mm%Ss')
        print(f"\n[START] {utc_start} UTC - Capture en cours...")
        print(f"[INFO] Ctrl+C pour arreter\n")
        tb.start()
        # Afficher les stats periodiquement
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
        print(f"RESULTATS - {utc_end} UTC")
        print(f"{'='*60}")
        print(f"Bursts detectes:   {stats['bursts_detected']}")
        print(f"Bursts 1G routes:  {stats['bursts_1g']}")
        print(f"Bursts 2G routes:  {stats['bursts_2g']}")
        print(f"Trames demodulees: {stats['frames_decoded']}")
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



def analyze_results_from_stderr():
    """
    Parse stderr pour extraire les trames et comparer avec la reference
    Note: Cette fonction doit etre appelee si stderr est capture
    """
    import sys
    ref_frame = "FFFE2F8E39048D158AC01E3AA482856824CE"

    # Lire depuis stderr (qui contient les logs C++)
    stderr_content = ""
    # Cette fonction sera utilisee dans un contexte ou stderr est redirige

    refs = re.findall(r'\[REF FR HEX\]: ([0-9A-F]+)', stderr_content)
    demods = re.findall(r'\[COSPAS\] HEX: ([0-9A-F]+)', stderr_content)

    if len(demods) > 0:
        ok_count = sum(1 for r, d in zip(refs, demods) if r == d)
        error_count = len(demods) - ok_count
        success_rate = 100 * ok_count / len(demods)

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"ANALYSE DEMODULATION", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        print(f"Trames OK:  {ok_count}/{len(demods)} ({success_rate:.1f}%)", file=sys.stderr)
        print(f"Trames KO:  {error_count}/{len(demods)} ({100-success_rate:.1f}%)", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)


if __name__ == '__main__':
        main()
