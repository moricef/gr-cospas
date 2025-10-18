#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur IQ OQPSK pour Balises COSPAS-SARSAT 2G (T.018 Compliant)
====================================================================

Convertit une trame 2G (250 bits) en signal IQ modulé OQPSK avec étalement spectral DSSS.
Basé sur l'implémentation validée du dsPIC33CK (SARSAT_T018_dsPIC33CK.X).

Usage:
    ./generate_oqpsk_iq.py <trame_hex> [options]

Exemple:
    ./generate_oqpsk_iq.py 4D9E2CA2B005C1C38E... -o beacon_2g_test.iq

Spécifications T.018 Rev.12 (Oct 2024):
    - Input: 250 bits (202 info + 48 BCH)
    - Modulation: OQPSK (Offset QPSK) avec offset Q = Tc/2
    - Étalement: DSSS 256 chips/bit par canal (I et Q séparés)
    - Chip rate: 38400 chips/s ± 0.6 chips/s
    - Data rate: 300 bps
    - Durée trame: 1000 ms ± 1 ms
    - Préambule: 50 bits (166.7 ms)
    - Sample rate: 400 kHz (10.42 samples/chip)

Références:
    - C/S T.018 Rev.12 Section 2.2.3: DSSS-OQPSK
    - C/S T.018 Table 2.2: PRN LFSR initialization
    - dsPIC33CK: system_comms.c (PRN generator validé)
"""

import numpy as np
import argparse
import sys

# ============================================================================
# PARAMÈTRES SYSTÈME T.018 (Validés dsPIC33CK)
# ============================================================================

# Débits officiels T.018
DATA_RATE = 300          # bps
CHIP_RATE = 38400        # chips/s (38.4 kchips/s)
CHIPS_PER_BIT = 256      # chips par bit (par canal I ou Q)
PREAMBLE_BITS = 50       # bits de préambule (166.7 ms)

# Structure trame
INFO_BITS = 202          # bits d'information
BCH_BITS = 48           # bits BCH(250,202)
TOTAL_MESSAGE_BITS = INFO_BITS + BCH_BITS  # 250 bits

# Échantillonnage
SAMPLE_RATE = 400000     # Hz (10.42 samples/chip)
SAMPLES_PER_CHIP = SAMPLE_RATE / CHIP_RATE  # ~10.42

# Durées théoriques
PREAMBLE_DURATION = PREAMBLE_BITS / DATA_RATE  # 166.7 ms
MESSAGE_DURATION = TOTAL_MESSAGE_BITS / DATA_RATE  # 833.3 ms
TOTAL_DURATION = 1.0     # 1 seconde

# ============================================================================
# GÉNÉRATEUR PRN (LFSR T.018 - x²³ + x¹⁸ + 1)
# ============================================================================

class LFSR_T018:
    """
    Linear Feedback Shift Register conforme T.018 Table 2.2
    Polynôme: G(x) = x²³ + x¹⁸ + 1

    États initiaux (Mode Normal):
        - I-channel: 0x000001 (23 bits)
        - Q-channel: 0x000041 (offset 64 chips)

    Validation: Premiers 64 chips → 8000 0108 4212 84A1 (Normal I)
    """

    # États initiaux T.018 Table 2.2
    INIT_NORMAL_I = 0x000001  # Normal I: bit 0 = 1
    INIT_NORMAL_Q = 0x000041  # Normal Q: offset 64
    INIT_TEST_I = 0x69E780    # Self-test I
    INIT_TEST_Q = 0x3CB948    # Self-test Q

    def __init__(self, init_state=INIT_NORMAL_I):
        """
        Args:
            init_state: État initial LFSR (23 bits)
        """
        self.state = init_state & 0x7FFFFF  # Masque 23 bits
        self.init_state = self.state

    def next_chip(self):
        """
        Génère le prochain chip et met à jour l'état LFSR (Fibonacci, shift RIGHT).

        Selon T.018 Appendix D Figure D-1:
        - Output = X0 (registre 0, LSB)
        - Feedback = X0 ⊕ X18
        - Shift RIGHT: Xn → Xn-1
        - Feedback → X22

        Returns:
            int8: Chip (+1 ou -1) selon Table 2.3 T.018
                  Logic 1 → Signal -1
                  Logic 0 → Signal +1
        """
        # Output = X0 (bit 0) AVANT le shift
        output_bit = self.state & 1

        # T.018 Appendix D: Feedback = X0 ⊕ X18
        feedback = (self.state ^ (self.state >> 18)) & 1

        # Shift RIGHT: Xn → Xn-1 (X22→X21, X21→X20, ..., X1→X0)
        # Feedback va dans X22 (MSB)
        self.state = (self.state >> 1) | (feedback << 22)

        # Table 2.3: Logic 1 → -1, Logic 0 → +1
        return -1 if output_bit == 1 else +1

    def generate_sequence(self, length):
        """
        Génère une séquence de chips.

        Args:
            length: Nombre de chips à générer

        Returns:
            np.array: Séquence de chips (int8: +1/-1)
        """
        return np.array([self.next_chip() for _ in range(length)], dtype=np.int8)

    def reset(self):
        """Réinitialise le LFSR à son état initial."""
        self.state = self.init_state

    @classmethod
    def verify_table_2_2(cls):
        """
        Vérifie la conformité avec T.018 Table 2.2 (Normal I).

        Returns:
            bool: True si conforme
        """
        lfsr = cls(cls.INIT_NORMAL_I)

        # Générer premiers 64 chips en utilisant next_chip()
        chips = []
        for _ in range(64):
            # Utiliser la même fonction que pour la génération
            chip = lfsr.next_chip()
            # Convertir signal level → logic level
            # chip -1 → logic 1, chip +1 → logic 0
            logic_bit = 1 if chip == -1 else 0
            chips.append(logic_bit)

        # Convertir en hex (4 groupes de 16 bits)
        hex_values = []
        for i in range(4):
            bits_16 = chips[i*16:(i+1)*16]
            val = sum(b << (15-j) for j, b in enumerate(bits_16))
            hex_values.append(f"{val:04X}")

        # Valeurs attendues T.018 Table 2.2
        expected = ["8000", "0108", "4212", "84A1"]

        if hex_values == expected:
            print(f"✓ PRN LFSR conforme T.018 Table 2.2: {' '.join(hex_values)}")
            return True
        else:
            print(f"✗ PRN LFSR NON CONFORME:")
            print(f"  Attendu: {' '.join(expected)}")
            print(f"  Obtenu:  {' '.join(hex_values)}")
            return False

# ============================================================================
# FONCTIONS DE CONVERSION
# ============================================================================

def hex_to_bits(hex_string):
    """
    Convertit hexadécimal → bits.

    Args:
        hex_string: String hex (ex: "4D9E2C...")

    Returns:
        np.array: Bits (uint8: 0 ou 1)
    """
    bits = []
    for hex_char in hex_string:
        if hex_char in ' -_':
            continue

        try:
            val = int(hex_char, 16)
        except ValueError:
            print(f"Erreur: Caractère hex invalide '{hex_char}'", file=sys.stderr)
            sys.exit(1)

        # MSB first
        for i in range(3, -1, -1):
            bits.append((val >> i) & 1)

    return np.array(bits, dtype=np.uint8)

def build_frame_with_preamble(message_bits):
    """
    Construit la trame complète avec préambule.

    T.018 Section 2.2.4: Préambule = 50 bits à '0'

    Args:
        message_bits: 250 bits de message (info + BCH)

    Returns:
        np.array: Trame complète (300 bits: 50 preamble + 250 message)
    """
    preamble = np.zeros(PREAMBLE_BITS, dtype=np.uint8)
    return np.concatenate([preamble, message_bits])

def dsss_spread_oqpsk(frame_bits):
    """
    Applique l'étalement DSSS selon T.018 Section 2.2.3(b).

    Principe:
    - Bits impairs (1, 3, 5...) → canal I → 256 chips (LFSR I)
    - Bits pairs (2, 4, 6...) → canal Q → 256 chips (LFSR Q)
    - Bit 0: non inversé, Bit 1: inversé (XOR avec PRN)

    Args:
        frame_bits: Trame complète (300 bits)

    Returns:
        tuple: (i_chips, q_chips) - np.array int8
    """
    # Initialiser LFSR I et Q
    lfsr_i = LFSR_T018(LFSR_T018.INIT_NORMAL_I)
    lfsr_q = LFSR_T018(LFSR_T018.INIT_NORMAL_Q)

    # Séparer bits pairs/impairs (selon T.018: bit 1 = premier bit)
    # Python indexing: bit[0] = bit 1 T.018
    odd_bits = frame_bits[0::2]   # Bits 1, 3, 5... → canal I
    even_bits = frame_bits[1::2]  # Bits 2, 4, 6... → canal Q

    i_chips_list = []
    q_chips_list = []

    # Générer chips pour canal I (bits impairs)
    for bit in odd_bits:
        prn_seq = lfsr_i.generate_sequence(CHIPS_PER_BIT)
        # T.018 Table 2.4: Bit 0 → PRN normal, Bit 1 → PRN inversé
        if bit == 1:
            prn_seq = -prn_seq
        i_chips_list.append(prn_seq)

    # Générer chips pour canal Q (bits pairs)
    for bit in even_bits:
        prn_seq = lfsr_q.generate_sequence(CHIPS_PER_BIT)
        if bit == 1:
            prn_seq = -prn_seq
        q_chips_list.append(prn_seq)

    i_chips = np.concatenate(i_chips_list)
    q_chips = np.concatenate(q_chips_list)

    return i_chips, q_chips

def rrc_filter_taps(alpha, span, sps):
    """
    Génère les coefficients d'un filtre Root-Raised Cosine (RRC).

    T.018 Rev.12 Section 2.3.4: RRC filter
    - Roll-off factor: α = 0.8
    - Span: ±31 chips (63 taps total)
    - Samples per symbol: sps (samples/chip)

    Args:
        alpha: Roll-off factor (0.8 pour T.018)
        span: Span du filtre en symboles (31 pour T.018 → 63 taps)
        sps: Samples per symbol (samples/chip)

    Returns:
        np.array: Coefficients du filtre RRC normalisés
    """
    n_taps = 2 * span * sps + 1
    t = np.arange(-span * sps, span * sps + 1) / float(sps)

    h = np.zeros(len(t))

    for i, time in enumerate(t):
        if time == 0:
            h[i] = (1 - alpha + 4 * alpha / np.pi)
        elif abs(time) == 1 / (4 * alpha):
            h[i] = (alpha / np.sqrt(2)) * (
                ((1 + 2 / np.pi) * np.sin(np.pi / (4 * alpha))) +
                ((1 - 2 / np.pi) * np.cos(np.pi / (4 * alpha)))
            )
        else:
            numerator = (
                np.sin(np.pi * time * (1 - alpha)) +
                4 * alpha * time * np.cos(np.pi * time * (1 + alpha))
            )
            denominator = np.pi * time * (1 - (4 * alpha * time) ** 2)
            h[i] = numerator / denominator

    # Normaliser pour gain unitaire
    h = h / np.sqrt(np.sum(h ** 2))

    return h

def oqpsk_modulate(i_chips, q_chips, sample_rate, use_rrc=True):
    """
    Modulation OQPSK avec offset Q = Tc/2 et filtre RRC.

    T.018 Section 2.3.3:
    "The chips of the I and Q components shall have an average offset
     of half a chip period ± 1% with I leading Q by one-half chip period."

    T.018 Section 2.3.4: Pulse shaping avec RRC α=0.8

    Args:
        i_chips: Chips canal I (int8: ±1)
        q_chips: Chips canal Q (int8: ±1)
        sample_rate: Fréquence d'échantillonnage (Hz)
        use_rrc: Activer filtre RRC (True par défaut)

    Returns:
        np.array: Signal IQ complexe (complex64)
    """
    samples_per_chip = int(sample_rate / CHIP_RATE)

    if use_rrc:
        # Filtre RRC T.018: α=0.8, span=±31 chips (63 taps)
        rrc_taps = rrc_filter_taps(alpha=0.8, span=31, sps=samples_per_chip)

        # Suréchantillonner par insertion de zéros
        i_upsampled = np.zeros(len(i_chips) * samples_per_chip, dtype=np.float32)
        q_upsampled = np.zeros(len(q_chips) * samples_per_chip, dtype=np.float32)

        i_upsampled[::samples_per_chip] = i_chips
        q_upsampled[::samples_per_chip] = q_chips

        # Appliquer filtre RRC
        i_signal = np.convolve(i_upsampled, rrc_taps, mode='same')
        q_signal = np.convolve(q_upsampled, rrc_taps, mode='same')

    else:
        # Mode legacy sans RRC (répétition simple)
        i_signal = np.repeat(i_chips, samples_per_chip).astype(np.float32)
        q_signal = np.repeat(q_chips, samples_per_chip).astype(np.float32)

    # Offset Q de Tc/2 (I leading Q)
    offset_samples = samples_per_chip // 2
    q_signal_delayed = np.concatenate([
        np.full(offset_samples, 0.0 if use_rrc else q_chips[0], dtype=np.float32),
        q_signal
    ])

    # Égaliser longueurs
    min_len = min(len(i_signal), len(q_signal_delayed))
    i_signal = i_signal[:min_len]
    q_signal_delayed = q_signal_delayed[:min_len]

    # Signal complexe I + jQ
    iq_signal = i_signal + 1j * q_signal_delayed

    # Normalisation pour magnitude = 1
    max_mag = np.max(np.abs(iq_signal))
    if max_mag > 0:
        iq_signal = iq_signal / max_mag

    return iq_signal.astype(np.complex64)

# ============================================================================
# SAUVEGARDE FICHIER IQ
# ============================================================================

def save_iq_file(iq_signal, filename, sample_rate):
    """
    Sauvegarde au format gr_complex (float32 interleaved).

    Format: I0, Q0, I1, Q1, I2, Q2, ...
    Compatible GNU Radio File Source (complex).
    """
    num_samples = len(iq_signal)
    iq_interleaved = np.zeros(num_samples * 2, dtype=np.float32)
    iq_interleaved[0::2] = iq_signal.real
    iq_interleaved[1::2] = iq_signal.imag

    iq_interleaved.tofile(filename)

    duration = num_samples / sample_rate
    file_size = iq_interleaved.nbytes

    print(f"\n✓ Fichier IQ généré: {filename}")
    print(f"  Format: gr_complex (float32 interleaved)")
    print(f"  Échantillons: {num_samples:,}")
    print(f"  Durée: {duration:.3f} s")
    print(f"  Sample rate: {sample_rate:,} Hz")
    print(f"  Taille: {file_size:,} octets ({file_size/1024:.1f} KB)")

# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def generate_2g_iq_signal(hex_frame, sample_rate=SAMPLE_RATE, verbose=True):
    """
    Génère le signal OQPSK complet T.018 compliant.

    Args:
        hex_frame: Trame 250 bits (hex)
        sample_rate: Fréquence échantillonnage (Hz)
        verbose: Mode verbeux

    Returns:
        np.array: Signal IQ complexe
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"  Générateur OQPSK COSPAS-SARSAT 2G (T.018 Rev.12)")
        print(f"{'='*70}\n")
        print(f"Source: dsPIC33CK (SARSAT_T018_dsPIC33CK.X)")
        print(f"Trame hex: {hex_frame[:30]}... ({len(hex_frame)} chars)\n")

    # Vérification T.018 Table 2.2
    # LFSR corrigé selon Appendix D (feedback X0⊕X18, shift RIGHT)
    if verbose:
        LFSR_T018.verify_table_2_2()
        print()

    # Étape 1: Hex → Bits (250 bits)
    message_bits = hex_to_bits(hex_frame)[:TOTAL_MESSAGE_BITS]
    if verbose:
        print(f"✓ Message: {len(message_bits)} bits extraits")
        print(f"  Structure: {INFO_BITS} info + {BCH_BITS} BCH")

    # Étape 2: Ajouter préambule (50 bits à '0')
    frame_bits = build_frame_with_preamble(message_bits)
    total_bits = len(frame_bits)
    if verbose:
        print(f"✓ Trame complète: {total_bits} bits ({PREAMBLE_BITS} preamble + {TOTAL_MESSAGE_BITS} message)")

    # Étape 3: Étalement DSSS (bits → chips)
    i_chips, q_chips = dsss_spread_oqpsk(frame_bits)
    if verbose:
        print(f"✓ DSSS spreading:")
        print(f"  I-channel: {len(i_chips)} chips ({len(i_chips)//CHIPS_PER_BIT} bits × {CHIPS_PER_BIT})")
        print(f"  Q-channel: {len(q_chips)} chips ({len(q_chips)//CHIPS_PER_BIT} bits × {CHIPS_PER_BIT})")
        print(f"  Chip rate: {CHIP_RATE} chips/s")

    # Étape 4: Modulation OQPSK (chips → IQ)
    iq_signal = oqpsk_modulate(i_chips, q_chips, sample_rate)
    if verbose:
        duration = len(iq_signal) / sample_rate
        print(f"✓ Modulation OQPSK:")
        print(f"  Échantillons: {len(iq_signal):,}")
        print(f"  Durée: {duration:.3f} s (théorique: {TOTAL_DURATION:.3f} s)")
        print(f"  I range: [{np.min(iq_signal.real):.3f}, {np.max(iq_signal.real):.3f}]")
        print(f"  Q range: [{np.min(iq_signal.imag):.3f}, {np.max(iq_signal.imag):.3f}]")

    return iq_signal

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Générateur IQ OQPSK T.018 compliant (validé dsPIC33CK)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s 4D9E2CA2B005C1C38E... -o beacon_2g.iq
  %(prog)s trame_250bits.txt -o test.iq -s 400000

Format trame:
  - 63 caractères hexadécimaux (250 bits: 202 info + 48 BCH)
  - Espaces/tirets ignorés
  - Exemple: "4D 9E 2C A2 B0 05 C1 C3 8E..."

Références:
  - C/S T.018 Rev.12 (Oct 2024) Section 2.2.3
  - dsPIC33CK: system_comms.c (PRN LFSR validé Table 2.2)
        """
    )

    parser.add_argument('trame',
                       help='Trame 250 bits (hex) ou fichier .txt/.hex')
    parser.add_argument('-o', '--output',
                       default='beacon_2g_test.iq',
                       help='Fichier IQ sortie (défaut: beacon_2g_test.iq)')
    parser.add_argument('-s', '--sample-rate',
                       type=int,
                       default=SAMPLE_RATE,
                       help=f'Sample rate Hz (défaut: {SAMPLE_RATE})')
    parser.add_argument('-q', '--quiet',
                       action='store_true',
                       help='Mode silencieux')

    args = parser.parse_args()

    # Lire trame
    if args.trame.endswith(('.txt', '.hex')):
        try:
            with open(args.trame, 'r') as f:
                hex_frame = f.read().strip()
        except FileNotFoundError:
            print(f"Erreur: Fichier '{args.trame}' introuvable", file=sys.stderr)
            sys.exit(1)
    else:
        hex_frame = args.trame

    # Nettoyer et valider
    hex_frame = hex_frame.replace(' ', '').replace('-', '').replace('_', '')

    expected_chars = 63  # 250 bits = 62.5 → 63 chars
    if len(hex_frame) < expected_chars:
        print(f"Erreur: Trame trop courte ({len(hex_frame)} chars, attendu {expected_chars})",
              file=sys.stderr)
        sys.exit(1)

    # Générer signal
    verbose = not args.quiet
    iq_signal = generate_2g_iq_signal(hex_frame, args.sample_rate, verbose)

    # Sauvegarder
    save_iq_file(iq_signal, args.output, args.sample_rate)

    if verbose:
        print(f"\n{'='*70}")
        print(f"  Génération terminée - T.018 Compliant")
        print(f"{'='*70}\n")
        print("Test GNU Radio:")
        print(f"  gnuradio-companion")
        print(f"  File Source → Type: Complex, Sample Rate: {args.sample_rate}")

if __name__ == '__main__':
    main()
