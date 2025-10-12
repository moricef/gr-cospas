#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Générateur de signal COSPAS-SARSAT 406 MHz en biphase-L
Génère un signal I/Q en bande de base
"""

import numpy as np
from gnuradio import gr

class cospas_generator(gr.sync_block):
    """
    Générateur de trames COSPAS-SARSAT en modulation biphase-L

    Paramètres du signal:
    - Porteuse non modulée: 160 ms
    - Préambule: 15 bits à '1'
    - Données: 144 bits (18 octets)
    - Modulation: Biphase-L ±1.1 radians
    - Débit: 400 bps
    - Fréquence échantillonnage: 6400 Hz
    """

    def __init__(self, data_bytes=None, repeat=True, test_mode=False):
        gr.sync_block.__init__(
            self,
            name="cospas_generator",
            in_sig=[],
            out_sig=[np.complex64]
        )

        # Paramètres du système
        self.SAMPLE_RATE = 6400.0
        self.BIT_RATE = 400.0
        self.SAMPLES_PER_BIT = int(self.SAMPLE_RATE / self.BIT_RATE)  # 16
        self.CARRIER_DURATION = 0.160  # 160 ms
        self.CARRIER_SAMPLES = int(self.CARRIER_DURATION * self.SAMPLE_RATE)  # 1024
        self.PREAMBLE_BITS = 15
        self.FRAME_SYNC_BITS = 9

        # Frame sync patterns
        self.FRAME_SYNC_NORMAL = '000101111'  # Mode normal
        self.FRAME_SYNC_TEST = '011010000'    # Mode self-test

        # Modulation biphase-L
        self.MOD_PHASE = 1.1  # ±1.1 radians

        # Données à transmettre (par défaut: pattern de test)
        if data_bytes is None:
            # Générer 18 octets de test (pattern 0xAA = 10101010)
            self.data_bytes = bytes([0xAA] * 18)
        else:
            self.data_bytes = data_bytes

        self.repeat = repeat
        self.test_mode = test_mode
        self.sample_index = 0

        # Générer la trame complète
        self.generate_frame()

    def generate_frame(self):
        """Génère une trame COSPAS-SARSAT complète"""
        frame_samples = []

        # 1. Porteuse non modulée (160 ms à phase 0)
        carrier = np.exp(1j * 0.0) * np.ones(self.CARRIER_SAMPLES, dtype=np.complex64)
        frame_samples.extend(carrier)

        # 2. Préambule (15 bits à '1')
        for _ in range(self.PREAMBLE_BITS):
            frame_samples.extend(self.generate_bit('1'))

        # 3. Frame synchronization (9 bits)
        frame_sync_pattern = self.FRAME_SYNC_TEST if self.test_mode else self.FRAME_SYNC_NORMAL
        for bit in frame_sync_pattern:
            frame_samples.extend(self.generate_bit(bit))

        # 4. Données
        for byte in self.data_bytes:
            for bit_pos in range(7, -1, -1):  # MSB first
                bit = '1' if (byte >> bit_pos) & 1 else '0'
                frame_samples.extend(self.generate_bit(bit))

        self.frame = np.array(frame_samples, dtype=np.complex64)
        self.frame_length = len(self.frame)

        mode_str = "Self-Test" if self.test_mode else "Normal"
        print(f"[COSPAS Generator] Trame générée (Mode {mode_str}):")
        print(f"  - Porteuse: {self.CARRIER_SAMPLES} échantillons ({self.CARRIER_DURATION*1000} ms)")
        print(f"  - Préambule: {self.PREAMBLE_BITS} bits")
        print(f"  - Frame Sync: {self.FRAME_SYNC_BITS} bits ({frame_sync_pattern})")
        print(f"  - Données: {len(self.data_bytes)} octets = {len(self.data_bytes)*8} bits")
        print(f"  - Total: {self.frame_length} échantillons ({self.frame_length/self.SAMPLE_RATE:.3f} s)")

    def generate_bit(self, bit):
        """
        Génère les échantillons pour un bit en modulation biphase-L

        Biphase-L (également appelé Manchester Différentiel):
        - Bit '1': transition descendante au milieu (+1.1 rad → -1.1 rad)
        - Bit '0': transition montante au milieu (-1.1 rad → +1.1 rad)

        Chaque bit dure 2.5 ms = 16 échantillons à 6400 Hz
        """
        half_bit = self.SAMPLES_PER_BIT // 2  # 8 échantillons

        if bit == '1':
            # Première moitié: +1.1 rad
            first_half = np.exp(1j * self.MOD_PHASE) * np.ones(half_bit, dtype=np.complex64)
            # Deuxième moitié: -1.1 rad
            second_half = np.exp(1j * (-self.MOD_PHASE)) * np.ones(half_bit, dtype=np.complex64)
        else:  # bit == '0'
            # Première moitié: -1.1 rad
            first_half = np.exp(1j * (-self.MOD_PHASE)) * np.ones(half_bit, dtype=np.complex64)
            # Deuxième moitié: +1.1 rad
            second_half = np.exp(1j * self.MOD_PHASE) * np.ones(half_bit, dtype=np.complex64)

        return np.concatenate([first_half, second_half])

    def work(self, input_items, output_items):
        """Génère les échantillons de sortie"""
        out = output_items[0]
        n_output = len(out)
        n_produced = 0

        while n_produced < n_output:
            # Calculer combien d'échantillons on peut produire
            remaining_in_frame = self.frame_length - self.sample_index
            remaining_in_output = n_output - n_produced
            n_to_copy = min(remaining_in_frame, remaining_in_output)

            # Copier les échantillons
            out[n_produced:n_produced + n_to_copy] = \
                self.frame[self.sample_index:self.sample_index + n_to_copy]

            n_produced += n_to_copy
            self.sample_index += n_to_copy

            # Si on a fini la trame
            if self.sample_index >= self.frame_length:
                if self.repeat:
                    self.sample_index = 0
                else:
                    # Remplir le reste avec des zéros
                    if n_produced < n_output:
                        out[n_produced:] = 0
                    return n_output

        return n_produced
