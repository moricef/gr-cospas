# tools/2g - Second Generation (2G) COSPAS-SARSAT Tools

**Status**: IQ Generator Ready ✓ | Demodulator Missing ✗

## Overview

Tools for **2nd generation COSPAS-SARSAT beacons** (T.018 Rev.12 compliant).

### 2G Beacon Specifications
- **Modulation**: OQPSK with DSSS
- **Data Rate**: 300 bps
- **Chip Rate**: 38.4 kchips/s
- **Spreading**: 256 chips/bit per channel (I/Q)
- **Frame Length**: 252 bits (2 header + 250 data)
- **Error Correction**: BCH(250,202) with 48-bit parity
- **LFSR**: x²³ + x¹⁸ + 1 (T.018 Table 2.2 validated)

## Available Tools

### IQ + WAV Signal Generator (RECOMMANDÉ)
**generate_sgb_iq_wav.py** - Générateur complet IQ + WAV

```bash
# Générer avec trame par défaut
./generate_sgb_iq_wav.py -o beacon_sgb

# Générer depuis fichier trame
./generate_sgb_iq_wav.py -f test_frame_2g.txt -o custom

# Générer depuis trame hex directe
./generate_sgb_iq_wav.py -t 89C3F45639195999A... -o beacon
```

**Sortie**:
- `beacon_sgb.iq` (3 MB) - Signal IQ complexe float32, 384 kHz - **Pour PlutoSDR**
- `beacon_sgb.wav` (181 KB) - I/Q baseband stéréo int16, 48 kHz - **Pour GNU Radio**

**Features**:
- ✓ Filtre RRC intégré (α=0.8, 63 taps)
- ✓ LFSR conforme T.018 Table 2.2
- ✓ Sample rate optimisé PlutoSDR (384 kHz)
- ✓ OQPSK modulation avec offset Tc/2
- ✓ DSSS spreading (256 chips/bit)
- ✓ T.018 Rev.12 compliant (validé)

### ⚠️ À PROPOS DES FICHIERS .WAV

**IMPORTANT**: Les fichiers `.wav` générés contiennent des **données I/Q baseband**, PAS du son audio !

- **Si vous jouez le WAV avec `aplay` ou VLC**: Vous entendrez du **bruit blanc** - c'est NORMAL
- **Format**: Stéréo (canal gauche = I, canal droit = Q)
- **Usage**: Entrée pour GNU Radio Companion, SDR++, ou autres logiciels SDR

**Comment utiliser le WAV dans GNU Radio**:
```
WAV File Source → Complex to Float → (votre flowgraph)
  - File: beacon_sgb.wav
  - Sample rate: 48000
  - Output type: Float
  - Channels: 2
```

**Pour transmettre avec PlutoSDR, utilisez le fichier `.iq` (format natif, meilleure qualité)**

### Démonstration: Charger WAV I/Q en Python
**demo_load_wav.py** - Script de démonstration pour charger et analyser les WAV I/Q

```bash
./demo_load_wav.py beacon_sgb.wav
```

**Sortie**:
- Statistiques I/Q (range, mean, RMS)
- Analyse spectrale (puissance, largeur de bande)
- Graphiques: constellation, signal temporel, spectre FFT, distribution magnitude
- Sauvegarde graphiques en `wav_analysis.png`

Ce script montre comment charger correctement les fichiers WAV I/Q dans Python
et les convertir en échantillons complexes pour traitement SDR.

### IQ Signal Generator (Core)
**generate_oqpsk_iq.py** - Générateur IQ de base (utilisé par generate_sgb_iq_wav.py)

```bash
# Utiliser generate_sgb_iq_wav.py à la place (génère IQ + WAV)
# Ou appeler directement pour IQ seulement:
./generate_oqpsk_iq.py <250bit_hex_frame> -o output.iq
```

### Validated Test Frames

**Frame 1** (EPIRB France Normal mode):
```
89C3F45639195999A02B33326C3EC4400007FFF00C0283200000DCA2C07A361
✓ BCH valid, France EPIRB, TAC:9999, 43.20°N 5.40°E
```

**Frame 2** (EPIRB France):
```
0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F
✓ BCH valid, France EPIRB, TAC:12345, 42.85°N 4.95°E
```

## IMPORTANT LIMITATIONS

### ⚠ No 2G Demodulator Yet

The gr-cospas module (/lib/cospas_sarsat_decoder_impl.cc) currently supports **1G beacons ONLY** (Biphase-L).

**Missing for 2G**:
- OQPSK demodulator
- PN despreading (256 chips → 1 bit)
- Carrier/timing recovery
- BCH(250,202) error correction

### 📋 Standalone IQ Demodulator Attempt (PAUSED)

A standalone C implementation was developed in the [dec406_v10.2 project](~/Developpement/COSPAS-SARSAT/balise_406MHz/dec406_v10.2/):
- **Files**: `main_iq.c`, `dsss_demod.c`, `prn_generator.c`
- **Status**: PAUSED at ~60% bit accuracy (target >95%)

**Achieved**:
- ✅ Timing recovery: 99.997% symbols recovered (38,399/38,400)
- ✅ OQPSK Tc/2 delay correction applied
- ✅ PRN LFSR validated (T.018 Table 2.2)
- ✅ Exhaustive parameter search (96 combinations)

**Limitation**:
- ❌ Phase/despreading plateau at 70% correlation
- ❌ Architectural limitation identified

**Documentation**: See `~/Developpement/COSPAS-SARSAT/balise_406MHz/dec406_v10.2/BILAN_CORRECTION_BUGS.md`

### 🎯 Recommended Approach

**Use GNU Radio blocks** for carrier/timing sync (validated components) + custom Python block for DSSS despreading:

```
File Source (.iq) → AGC + Freq Xlating FIR
  ↓
Costas Loop (phase/freq sync) ← ✅ Validated
  ↓
Symbol Sync (M&M/Gardner) ← ✅ Validated
  ↓
Custom Python Block:
  - OQPSK→QPSK (Tc/2 delay)
  - PRN despreading (reuse prn_generator.c logic)
  ↓
Binary Sink → dec406_v2g decoder ← ✅ Already operational
```

**Advantages**:
- Reuses validated carrier/timing recovery from GNU Radio
- Focus on DSSS-specific logic only
- Real-time debugging with constellation plots
- Estimated development: 1-2 days, 80% success probability

**Development Time**: Estimated 1-2 days for GNU Radio approach, vs weeks for from-scratch implementation.

---

**Last Updated**: 2025-10-23
**LFSR Fix**: 2025-10-16 (X0 ⊕ X18, validated Table 2.2)
**IQ Demodulator**: 2025-10-23 (PAUSED - 70% plateau, recommend GNU Radio)
