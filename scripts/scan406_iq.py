#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan406_iq.py - Scanner COSPAS-SARSAT avec démodulation I/Q
Reproduit le comportement de scan406.pl mais avec traitement I/Q direct
Intègre les optimisations validées:
- Autocorrélation burst detection (dec406_V7)
- Seuils adaptatifs (variance phase 0.15-0.7 rad selon SNR)
- Lowpass 20kHz, normalisation 0.15, seuil 0.05
- Validation bit sync stricte (>=13/15 bits)

Usage: python3 scan406_iq.py <f1_MHz> <f2_MHz> [ppm] [snr_threshold]
Exemple: python3 scan406_iq.py 403.000 403.100 0 7
         python3 scan406_iq.py 406.000 406.100 55 7
"""

import sys
import os
import time
import subprocess
import tempfile
import csv
from datetime import datetime, timezone
from gnuradio import gr, blocks, filter
from gnuradio import cospas


class cospas_receiver(gr.top_block):
    """Récepteur COSPAS-SARSAT I/Q temps réel"""

    def __init__(self, freq_hz, sample_rate=40000, ppm=0):
        gr.top_block.__init__(self, "COSPAS-SARSAT I/Q Receiver")

        self.sample_rate = sample_rate
        self.freq_hz = freq_hz
        self.ppm = ppm
        self.bits_file = None

        # RTL-SDR Source (osmosdr)
        # RTL-SDR minimum sample rate ~225 kHz
        # Utiliser 240 kHz avec décimation par 6 pour obtenir 40 kHz
        rtl_sample_rate = 240000
        decimation = rtl_sample_rate // sample_rate  # 6

        try:
            import osmosdr
            self.rtl_source = osmosdr.source(args="rtl=0")
            self.rtl_source.set_sample_rate(rtl_sample_rate)
            self.rtl_source.set_center_freq(freq_hz)
            self.rtl_source.set_freq_corr(ppm)
            self.rtl_source.set_gain_mode(False)
            self.rtl_source.set_gain(40)
            self.rtl_source.set_if_gain(20)
            self.rtl_source.set_bb_gain(20)
            print(f"[RTL-SDR] {freq_hz/1e6:.3f} MHz, {rtl_sample_rate} Hz → {sample_rate} Hz, ppm={ppm}")
        except ImportError:
            print("[ERREUR] Module osmosdr non disponible")
            print("         Installer: sudo apt install gr-osmosdr")
            sys.exit(1)

        # Décimateur (240 kHz → 40 kHz)
        self.decimator = filter.fir_filter_ccf(
            decimation,
            filter.firdes.low_pass(1, rtl_sample_rate, sample_rate/2 * 0.8, sample_rate/2 * 0.2)
        )

        # Filtre passe-bas pour COSPAS-SARSAT
        # Signal BPSK 400 bps + offset frequence + Manchester encoding occupe ~±10 kHz
        # 20 kHz donne les meilleurs resultats (68% vs 50% avec 10 kHz)
        bandpass_high = 20000    # 20 kHz
        transition_width = 2000  # 2 kHz de transition
        self.bandpass = filter.fir_filter_ccf(
            1,
            filter.firdes.low_pass(1, sample_rate, bandpass_high, transition_width)
        )

        # Normalisation du signal RTL-SDR
        # RTL-SDR uint8 -> float32 donne amplitude ~1.2, GQRX attend ~0.1
        # Augmente a 0.15 pour ameliorer la robustesse en fin de burst
        normalization_factor = 0.15
        self.normalizer = blocks.multiply_const_cc(normalization_factor)

        # Burst Detector (tampon circulaire)
        self.burst_detector = cospas.cospas_burst_detector(
            sample_rate=sample_rate,
            buffer_duration_ms=2000,
            threshold=0.05,  # Reduit de 0.1 a 0.05 pour capturer signal faible en fin de burst
            min_burst_duration_ms=200,
            debug_mode=False
        )

        # Burst Router
        self.burst_router = cospas.burst_router(
            sample_rate=sample_rate,
            debug_mode=False
        )

        # Démodulateur 1G (BPSK)
        self.demod_1g = cospas.cospas_sarsat_demodulator(
            sample_rate=sample_rate,
            debug_mode=False
        )

        # Monitor pour détecter la fin du décodage
        self.decode_monitor = cospas.decode_monitor()

        # Fichier de sortie pour les bits
        self.bits_file = tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bits', delete=False
        )
        self.file_sink = blocks.file_sink(gr.sizeof_char, self.bits_file.name, False)
        self.file_sink.set_unbuffered(True)

        # Null sinks pour les sorties stream du router
        self.null_sink_1g = blocks.null_sink(gr.sizeof_gr_complex)
        self.null_sink_2g = blocks.null_sink(gr.sizeof_gr_complex)

        # Connexions (stream)
        self.connect(self.rtl_source, self.decimator)
        self.connect(self.decimator, self.bandpass)
        self.connect(self.bandpass, self.normalizer)
        self.connect(self.normalizer, self.burst_detector)
        self.connect(self.burst_detector, self.burst_router)

        # Connexions (messages)
        self.msg_connect((self.burst_detector, "bursts"), (self.burst_router, "bursts"))
        self.msg_connect((self.burst_router, "bursts_1g"), (self.demod_1g, "bursts"))
        self.msg_connect((self.demod_1g, "decode_complete"), (self.decode_monitor, "decode_complete"))

        # Sorties stream du router vers null sinks
        self.connect((self.burst_router, 0), self.null_sink_1g)
        self.connect((self.burst_router, 1), self.null_sink_2g)

        print(f"[FLOWGRAPH] RTL-SDR → Decimator → Lowpass 20kHz → Normalizer → Detector → Router → Demod 1G")

    def get_bits_file(self):
        return self.bits_file.name if self.bits_file else None

    def get_statistics(self):
        return {
            'bursts_detected': self.burst_detector.get_bursts_detected(),
            'bursts_1g': self.burst_router.get_bursts_1g(),
            'bursts_2g': self.burst_router.get_bursts_2g(),
            'frames_decoded': self.demod_1g.get_frames_decoded()
        }

    def is_decode_complete(self):
        """Vérifie si le décodage est terminé via le message PMT"""
        return self.decode_monitor.is_complete()


def scan_frequency_range(f1_mhz, f2_mhz, ppm, csv_file):
    """
    Scanne une plage de fréquence avec rtl_power
    Retourne le fichier CSV généré
    """
    # Convertir en Hz pour rtl_power
    f1_hz = int(f1_mhz * 1e6)
    f2_hz = int(f2_mhz * 1e6)

    # rtl_power -p ppm -f f1:f2:step -i interval -P -O -1 -e duration -w hamming output.csv
    cmd = [
        "rtl_power",
        "-p", str(ppm),
        "-f", f"{f1_hz}:{f2_hz}:400",  # Pas de 400 Hz
        "-i", "55",                      # Intervalle 55s
        "-P",                            # Peak hold (off)
        "-O",                            # Offset tuning
        "-1",                            # Un seul scan
        "-e", "55",                      # Durée 55s
        "-w", "hamming",                 # Fenêtre Hamming
        csv_file
    ]

    print(f"[SCAN] rtl_power {f1_mhz:.3f}-{f2_mhz:.3f} MHz (pas=400Hz, durée=55s)")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # Timeout généreux
        )
        if result.returncode != 0:
            print(f"[SCAN] Erreur rtl_power: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("[SCAN] Timeout rtl_power")
        return False
    except FileNotFoundError:
        print("[ERREUR] rtl_power non trouvé. Installer: sudo apt install rtl-sdr")
        return False


def find_strongest_frequency(csv_file, snr_threshold=10):
    """
    Analyse le CSV de rtl_power pour trouver la fréquence la plus forte
    Retourne (freq_hz, max_db, mean_db) ou None si rien trouvé
    """
    if not os.path.exists(csv_file):
        return None

    max_db = -200
    freq_hz = 0
    all_db_values = []

    try:
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 7:
                    continue

                # Format CSV: date, time, f1, f2, step, num_samples, db[0], db[1], ...
                f1 = float(row[2])
                step = float(row[4])
                db_values = [float(x) for x in row[6:]]

                all_db_values.extend(db_values)

                # Chercher le maximum dans cette ligne
                for j, db in enumerate(db_values):
                    if db > max_db:
                        max_db = db
                        freq_hz = f1 + j * step

        if not all_db_values:
            return None

        # Calculer la moyenne
        mean_db = sum(all_db_values) / len(all_db_values)
        squelch = mean_db + snr_threshold

        print(f"[SCAN] Max={max_db:.1f} dB, Moyenne={mean_db:.1f} dB, Squelch={squelch:.1f} dB")

        if max_db > squelch:
            return (freq_hz, max_db, mean_db)
        else:
            print(f"[SCAN] Signal trop faible (max < squelch)")
            return None

    except Exception as e:
        print(f"[SCAN] Erreur lecture CSV: {e}")
        return None


def freq_balise_autorisee(freq_mhz):
    """
    Vérifie si la fréquence est dans les canaux autorisés (T.012 Table H.2)
    Retourne True si email autorisé, False si filtré (calibration/réservé)
    """
    # Canaux autorisés pour balises de détresse
    canaux_autorises = [
        # ⚠️ TEST UNIQUEMENT - À RETIRER EN PRODUCTION ⚠️
        (403.040, "TEST"),  # Balise test locale - RETIRER AVANT PRODUCTION

        # Canaux actifs avec balises de détresse
        (406.025, "B"),  # Beacons TA < 01/01/2002
        (406.028, "C"),  # Beacons TA < 01/01/2007
        (406.031, "D"),  # Beacons TA < 01/07/2025
        (406.037, "F"),  # Beacons TA < 01/01/2012
        (406.040, "G"),  # Beacons TA < 01/01/2017

        # Canaux futurs pour développements
        (406.049, "J"),  # Future developments
        (406.052, "K"),  # Future developments
        (406.061, "N"),  # Future developments
        (406.064, "O"),  # Future developments
        (406.073, "R"),  # Future developments

        # Nouveau canal depuis 2025
        (406.076, "S"),  # Beacons TA > 01/01/2025
    ]

    # Vérifier si la fréquence est dans un canal autorisé (±2 kHz)
    for freq, nom in canaux_autorises:
        if abs(freq_mhz - freq) <= 0.002:
            print(f"[FILTRE] Canal {nom} ({freq:.3f} MHz) → Email AUTORISÉ")
            return True

    # Canaux filtrés (pas d'email)
    # - Canal A (406.022): Balises système/calibration
    # - Canaux E,H,I,L,M,P,Q: Réservés non assignés
    print(f"[FILTRE] {freq_mhz:.3f} MHz → Email FILTRÉ (calibration/réservé)")
    return False


def bits_to_hex(bits_data):
    """Convertit les bits bruts en hex"""
    if len(bits_data) < 144:
        return None

    hex_str = ""
    for i in range(0, min(144, len(bits_data)), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits_data):
                byte = (byte << 1) | (bits_data[i + j] & 1)
        hex_str += f"{byte:02X}"

    return hex_str


def parse_trames_from_file(trame_file):
    """
    Parse le fichier trame pour extraire chaque trame individuellement
    Retourne une liste de trames UNIQUES (dédupliquées par HEX ID)
    """
    if not os.path.exists(trame_file) or os.path.getsize(trame_file) == 0:
        return []

    with open(trame_file, 'r') as f:
        content = f.read()

    import re

    # Une trame complète commence par [COSPAS] HEX: ou === 406 MHz BEACON DECODE
    # et se termine avant le prochain [COSPAS] HEX: ou === 406 MHz BEACON DECODE

    # Chercher toutes les positions de début de trame
    pattern = r'(?:^|\n)(?=\[COSPAS\] HEX:|=== 406 MHz BEACON DECODE)'
    splits = list(re.finditer(pattern, content))

    if not splits:
        # Aucun pattern trouvé, retourner tout le contenu
        if content.strip():
            return [content.strip()]
        return []

    # Extraire chaque trame et déduper par HEX ID
    trames_dict = {}  # {hex_id: trame_content}

    for i in range(len(splits)):
        start = splits[i].start()
        end = splits[i+1].start() if i+1 < len(splits) else len(content)
        trame = content[start:end].strip()

        if trame:
            # Extraire le HEX ID de la trame pour déduplication
            hex_match = re.search(r'\[COSPAS\] HEX: ([0-9A-F]+)', trame)
            if hex_match:
                hex_id = hex_match.group(1)
                # Garder seulement la première occurrence de chaque HEX ID
                if hex_id not in trames_dict:
                    trames_dict[hex_id] = trame
            else:
                # Si pas de HEX trouvé, ajouter quand même
                trames_dict[f'unknown_{i}'] = trame

    return list(trames_dict.values())


def send_email_simple(trame_file, utc_time, freq_mhz, config):
    """Envoie UN email avec le fichier trame.asc (comme scan406.pl)"""
    if not config:
        print("[EMAIL] Configuration email non disponible")
        return False

    try:
        subject = "Alerte_Balise_406"
        message = f"Date et Heure (UTC) du decodage: {utc_time}"

        # Log file comme scan406.pl
        log_file = config.get('log_file', '../data/mail.log')

        cmd = [
            "sendemail",
            "-l", log_file,
            "-f", config['utilisateur'],
            "-u", subject,
            "-t", config['destinataires'],
            "-s", config['smtp_serveur'],
            "-o", "tls=yes",
            "-xu", config['utilisateur'],
            "-xp", config['password'],
            "-m", message,
            "-a", trame_file
        ]

        subprocess.run(cmd, capture_output=True, timeout=30)
        print(f"[EMAIL] Alerte envoyée à {config['destinataires']}")
        return True

    except Exception as e:
        print(f"[EMAIL] Erreur: {e}")
        return False


def reset_rtlsdr_usb():
    """
    Réinitialise le dongle RTL-SDR USB (comme reset_dvbt() dans scan406.pl)
    Trouve le device Realtek RTL2832/2838 et le reset via ioctl
    """
    try:
        # Trouver le device RTL-SDR via lsusb
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False

        for line in result.stdout.split('\n'):
            # Chercher "Realtek" et ID 2832 ou 2838
            if 'Realtek' in line and ('2832' in line or '2838' in line):
                # Format: "Bus 001 Device 006: ID 0bda:2838 Realtek..."
                parts = line.split()
                if len(parts) >= 4:
                    bus = parts[1]
                    device = parts[3].rstrip(':')
                    usb_path = f"/dev/bus/usb/{bus}/{device}"

                    # Appeler reset_usb
                    reset_cmd = ['../utils/reset_usb', usb_path]
                    subprocess.run(reset_cmd, timeout=2)
                    print(f"[USB] Reset RTL-SDR: {usb_path}")
                    time.sleep(1)  # Laisser le temps au device de se réinitialiser
                    return True

        print("[USB] RTL-SDR non trouvé via lsusb")
        return False

    except Exception as e:
        print(f"[USB] Erreur reset: {e}")
        return False


def load_mail_config(config_file):
    """Charge la configuration email"""
    config = {}
    if not os.path.exists(config_file):
        return config

    try:
        with open(config_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    except Exception as e:
        print(f"[CONFIG] Erreur lecture {config_file}: {e}")
    return config


def main():
    # Arguments obligatoires
    if len(sys.argv) < 3:
        print("Usage: python3 scan406_iq.py <f1_MHz> <f2_MHz> [ppm] [snr_threshold]")
        print("Exemple: python3 scan406_iq.py 403.000 403.100 0 7")
        print("         python3 scan406_iq.py 406.000 406.100 55 7")
        sys.exit(1)

    f1_mhz = float(sys.argv[1])
    f2_mhz = float(sys.argv[2])
    ppm = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    snr_threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 7.0  # Seuil abaissé pour signaux faibles

    timeout_s = 56  # Comme scan406.pl - correspond aux 50s entre bursts des vraies balises

    print("=" * 60)
    print("SCANNER COSPAS-SARSAT (I/Q)")
    print("=" * 60)
    print(f"Plage de scan: {f1_mhz:.3f} - {f2_mhz:.3f} MHz")
    print(f"Correction PPM: {ppm}")
    print(f"SNR threshold: {snr_threshold} dB")
    print(f"Timeout capture: {timeout_s}s")
    print("=" * 60)

    # Charger config email
    mail_config = load_mail_config('../data/config_mail.txt')
    if mail_config:
        print(f"[CONFIG] Email configuré vers {mail_config.get('destinataires', 'N/A')}")
    else:
        print("[CONFIG] Email non configuré")

    # Fichiers de travail
    csv_file = '../data/scan_rtlpower.csv'  # Fichier fixe dans data/
    trame_dir = '../data'
    os.makedirs(trame_dir, exist_ok=True)

    # Boucle principale (comme scan406.pl)
    while True:
        # Reset USB au début de chaque cycle (comme scan406.pl ligne 80)
        reset_rtlsdr_usb()

        utc_time = datetime.now(timezone.utc).strftime('%d %m %Y   %Hh%Mm%Ss')
        print(f"\n{'='*60}")
        print(f"[SCAN] {utc_time} UTC")
        print(f"{'='*60}")

        # ÉTAPE 1: Scanner la plage de fréquence
        freq_trouvee = None

        if f1_mhz != f2_mhz:
            # Mode scan
            if not scan_frequency_range(f1_mhz, f2_mhz, ppm, csv_file):
                print("[SCAN] Échec du scan, retry dans 10s...")
                time.sleep(10)
                continue

            result = find_strongest_frequency(csv_file, snr_threshold)
            if result:
                freq_hz, max_db, mean_db = result
                freq_trouvee = freq_hz
                print(f"[SCAN] Signal trouvé: {freq_hz/1e6:.6f} MHz ({max_db:.1f} dB)")
            else:
                print("[SCAN] Aucun signal détecté, pause 3s avant nouveau scan...")
                time.sleep(3)  # Laisser le temps au dongle de se libérer
                continue
        else:
            # Mode fréquence fixe
            freq_trouvee = f1_mhz * 1e6
            print(f"[SCAN] Mode fréquence fixe: {f1_mhz:.3f} MHz")

        # ÉTAPE 2: Capture et démodulation sur la fréquence trouvée
        # Délai de sécurité avant ouverture du dongle
        time.sleep(2)

        utc_time = datetime.now(timezone.utc).strftime('%d %m %Y   %Hh%Mm%Ss')
        print(f"\n[DEMOD] Lancement capture sur {freq_trouvee/1e6:.6f} MHz")
        print(f"[DEMOD] {utc_time} UTC")
        print(f"[DEMOD] Flowgraph ouvert pour {timeout_s}s (mode continu)")

        # Créer le récepteur UNE FOIS pour tout le cycle de 56s
        try:
            tb = cospas_receiver(freq_trouvee, 40000, ppm)
        except Exception as e:
            print(f"[ERREUR] Impossible de créer le récepteur: {e}")
            time.sleep(10)
            continue

        bits_file = tb.get_bits_file()
        trames_trouvees = 0

        # Créer fichier trame (.asc) pour capturer stdout du décodeur C++
        trame_file = os.path.join(trame_dir, 'trame.asc')

        # Sauvegarder l'objet stdout Python original (une seule fois)
        if 'stdout_original' not in locals():
            stdout_original = sys.stdout
            stdout_fd = stdout_original.fileno()

        try:
            # Message avant redirection
            print(f"[DEMOD] Capture en cours ({timeout_s}s)...")
            sys.stdout.flush()

            # Rediriger stdout vers fichier au niveau système
            trame_fd = os.open(trame_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            stdout_backup_fd = os.dup(stdout_fd)
            os.dup2(trame_fd, stdout_fd)
            os.close(trame_fd)

            # Écrire la fréquence au début du fichier (stdout maintenant redirigé)
            print(f"Frequence: {freq_trouvee/1e6:.6f} MHz")
            sys.stdout.flush()

            # Démarrer la capture (le flowgraph reste ouvert pendant 56s)
            tb.start()

            # Capturer pendant 56s et envoyer email après chaque trame
            start_time = time.time()

            while time.time() - start_time < timeout_s:
                # Poll rapide (100ms) pour détecter les trames
                time.sleep(0.1)

                # Vérifier si une trame est décodée (message PMT du C++)
                if tb.is_decode_complete():
                    trames_trouvees += 1

                    # Forcer sync du fichier trame avant de le traiter
                    os.fsync(stdout_fd)

                    # Restaurer temporairement stdout pour afficher les messages
                    os.dup2(stdout_backup_fd, stdout_fd)
                    sys.stdout = stdout_original

                    # Récupérer timestamp pour l'email
                    utc_time = datetime.now(timezone.utc).strftime('%d %m %Y   %Hh%Mm%Ss')

                    print(f"[DECODE] Trame #{trames_trouvees} détectée à {utc_time}")

                    # Vérifier si fréquence autorisée pour email
                    freq_mhz_actuelle = freq_trouvee / 1e6

                    # Afficher le décodage dans un bloc séparé
                    if os.path.exists(trame_file) and os.path.getsize(trame_file) > 0:
                        print("\n" + "="*80)
                        with open(trame_file, 'r') as f:
                            print(f.read())
                        print("="*80 + "\n")

                    if freq_balise_autorisee(freq_mhz_actuelle):
                        # Envoyer email immédiatement (comme scan406.pl)
                        if mail_config:
                            send_email_simple(trame_file, utc_time, freq_mhz_actuelle, mail_config)
                        else:
                            print("[EMAIL] Configuration manquante, email non envoyé")

                    # Réinitialiser le flag pour écouter la prochaine trame
                    tb.decode_monitor.reset()

                    # Ré-ouvrir le fichier trame en mode TRUNC pour écraser le contenu (nouvelle trame)
                    trame_fd = os.open(trame_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                    os.dup2(trame_fd, stdout_fd)
                    os.close(trame_fd)

                    # Écrire la fréquence dans le nouveau fichier (pour le C++)
                    print(f"Frequence: {freq_trouvee/1e6:.6f} MHz")
                    sys.stdout.flush()

                    # Restaurer sys.stdout pour que les messages Python aillent au terminal
                    sys.stdout = stdout_original

                    print(f"[DEMOD] En attente de nouvelles trames... ({int(timeout_s - (time.time() - start_time))}s restantes)")

            # Après 56s, arrêter le flowgraph
            # Restaurer stdout si nécessaire
            try:
                os.dup2(stdout_backup_fd, stdout_fd)
                os.close(stdout_backup_fd)
            except:
                pass
            sys.stdout = stdout_original

            tb.stop()
            tb.wait()

            # Récupérer les statistiques finales
            stats = tb.get_statistics()

            print(f"\n[CYCLE TERMINÉ] Durée: {timeout_s}s")
            print(f"[STATS] Bursts détectés: {stats['bursts_detected']}")
            print(f"[STATS] Bursts 1G routés: {stats['bursts_1g']}")
            print(f"[STATS] Trames démodulées: {stats['frames_decoded']}")
            print(f"[STATS] Trames envoyées par email: {trames_trouvees}")

            # Décider si on continue sur cette fréquence ou on rescanne
            if trames_trouvees == 0:
                print("[DEMOD] Aucune trame détectée, retour au scan...")
                time.sleep(3)
            else:
                print(f"[DEMOD] {trames_trouvees} trame(s) détectée(s), nouveau cycle sur cette fréquence...")

        except KeyboardInterrupt:
            # Restaurer stdout
            try:
                os.dup2(stdout_backup_fd, stdout_fd)
                os.close(stdout_backup_fd)
            except:
                pass
            sys.stdout = stdout_original
            print("\n[STOP] Interruption utilisateur")
            tb.stop()
            tb.wait()
            raise

        except Exception as e:
            # Restaurer stdout
            try:
                os.dup2(stdout_backup_fd, stdout_fd)
                os.close(stdout_backup_fd)
            except:
                pass
            sys.stdout = stdout_original
            print(f"[ERREUR] {e}")
            import traceback
            traceback.print_exc()
            tb.stop()
            tb.wait()
            time.sleep(2)

        finally:
            # Nettoyer le flowgraph (RTL-SDR fermé après 56s)
            if 'tb' in locals():
                try:
                    del tb
                    print("[FLOWGRAPH] Flowgraph détruit, RTL-SDR fermé")
                except:
                    pass

            # Nettoyer fichier bits temporaire
            if bits_file and os.path.exists(bits_file):
                try:
                    os.unlink(bits_file)
                except:
                    pass

    # Nettoyage final
    if os.path.exists(csv_file):
        os.unlink(csv_file)

    print("\n[FIN] Scanner arrêté")


if __name__ == '__main__':
    main()
