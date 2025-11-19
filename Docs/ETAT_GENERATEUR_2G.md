# État du Générateur 2G OQPSK

Date: 2025-10-12

## 📊 Situation Actuelle

### ✅ Ce Qui Est FAIT

#### Générateur de Trame 2G (dsPIC33CK)
Emplacement: `/home/fab2/Developpement/COSPAS-SARSAT/MPLABXProjects/SARSAT_T018_dsPIC33CK.X/`

**Capacités** :
- ✅ Génération trame 202 bits (Main Field + Rotating Field)
- ✅ Encodage BCH(250,202) - 48 bits de parité
- ✅ Trame complète 250 bits (validée)
- ✅ Position GPS haute précision (3.4m)
- ✅ Champs rotatifs (RF#0, RF#1, RF#2, RF#4, RF#15)
- ✅ Validation sur décodeur officiel (dec406_v2g)

**Fichiers Clés** :
- `protocol_data.c` : Construction trames 2G
- `error_correction.c` : Encodeur BCH
- `rf_interface.c` : Interface RF (DAC I/Q, ADF7012)

**Output** :
```
250 bits validés → Format hexadécimal
Exemple: "4D9E2CA2B00..." (63 caractères hex)
```

### ❌ Ce Qui MANQUE

#### Modulation OQPSK + DSSS

**Problème** : Le dsPIC33CK a le **hardware** (DAC MCP4922 pour I/Q) mais pas le **software** complet.

**Ce qui manque** :
1. ❌ Séquence d'étalement PN (8 chips/bit)
2. ❌ Modulation OQPSK sur chips
3. ❌ Génération d'échantillons IQ à 2400 chips/s (ou suréchantillonnage)
4. ❌ Export vers fichier `.iq` pour gr-cospas

**Conséquence** :
- On a les **bits** (250 bits validés)
- On n'a pas les **échantillons IQ modulés** pour tester gr-cospas

---

## 🎯 Plan d'Action : Créer le Générateur IQ OQPSK

### Option A : Étendre le Code dsPIC33CK (Complexe)

**Avantages** :
- Hardware déjà présent (DAC MCP4922, ADF7012)
- Peut générer signal RF réel à 406 MHz

**Inconvénients** :
- Fréquence d'échantillonnage limitée par MCU
- Pas d'export fichier `.iq` facilement
- Debugging difficile (matériel requis)

### Option B : Générateur Python/C Standalone (RECOMMANDÉ)

**Architecture** :
```
Trame 250 bits (hex)
      ↓
[ PN Spreading ] → 2000 chips (8 chips × 250 bits)
      ↓
[ OQPSK Modulation ] → Échantillons I/Q complexes
      ↓
[ Suréchantillonnage ] → 40 kHz (comme fichiers 1G)
      ↓
Fichier beacon_2g_test.iq (format gr_complex)
```

**Fichiers à créer** :
1. `generate_oqpsk_iq.py` : Générateur Python
2. `oqpsk_modulator.c` : Version C optimisée (optionnel)

**Avantages** :
- Rapide à développer
- Facile à débugger
- Export direct `.iq`
- Testable immédiatement

---

## 📝 Spécifications Techniques OQPSK

### Séquence d'Étalement PN (C/S T.018 Section 2.3)

**Spreading Factor** : 8 chips/bit

**Séquence PN** (à confirmer dans spec T.018) :
```
Bit 0 → Chips: [+1 -1 +1 +1 -1 +1 -1 -1]
Bit 1 → Chips: [-1 +1 -1 -1 +1 -1 +1 +1]  (inversion)
```

### Modulation OQPSK

**Constellation** :
```
      Q
      ↑
   01 | 11
  ————+————→ I
   00 | 10
```

**Offset** : Canal Q décalé de Tc/2 (demi-période chip)

**Mapping** :
- I : Chip impair
- Q : Chip pair (décalé)

### Paramètres Signal

| Paramètre | Valeur |
|-----------|--------|
| **Débit données** | 300 bps |
| **Chip rate** | 2400 chips/s |
| **Spreading** | 8 chips/bit |
| **Durée bit** | 3.33 ms |
| **Durée chip** | 417 µs |
| **Samples/chip** | ~17 (à 40 kHz) |

---

## 🔧 Implémentation Proposée

### Programme Python : `generate_oqpsk_iq.py`

```python
#!/usr/bin/env python3
"""
Générateur IQ OQPSK pour balises COSPAS-SARSAT 2G
Input: Trame 250 bits (hex)
Output: Fichier .iq (gr_complex, 40 kHz)
"""

import numpy as np
import sys

# Paramètres
CHIP_RATE = 2400  # chips/s
SAMPLE_RATE = 40000  # Hz (comme fichiers 1G)
SAMPLES_PER_CHIP = SAMPLE_RATE // CHIP_RATE  # ~17 échantillons/chip
SPREADING_FACTOR = 8  # chips/bit

# Séquence PN d'étalement (C/S T.018)
PN_SEQUENCE_BIT0 = np.array([+1, -1, +1, +1, -1, +1, -1, -1])
PN_SEQUENCE_BIT1 = -PN_SEQUENCE_BIT0  # Inversion

def hex_to_bits(hex_string):
    """Convertit hex → bits"""
    bits = []
    for hex_char in hex_string:
        val = int(hex_char, 16)
        for i in range(3, -1, -1):
            bits.append((val >> i) & 1)
    return np.array(bits)

def spread_bits(bits):
    """Étalement spectral : bits → chips"""
    chips = []
    for bit in bits:
        if bit == 0:
            chips.extend(PN_SEQUENCE_BIT0)
        else:
            chips.extend(PN_SEQUENCE_BIT1)
    return np.array(chips)

def oqpsk_modulate(chips):
    """Modulation OQPSK avec offset Q"""
    # Chips pairs → I, impairs → Q (avec décalage)
    i_chips = chips[0::2]  # Pairs
    q_chips = chips[1::2]  # Impairs

    # Suréchantillonnage
    i_signal = np.repeat(i_chips, SAMPLES_PER_CHIP)
    q_signal = np.repeat(q_chips, SAMPLES_PER_CHIP)

    # Offset Q de Tc/2
    offset_samples = SAMPLES_PER_CHIP // 2
    q_signal = np.pad(q_signal, (offset_samples, 0), mode='edge')[:-offset_samples]

    # Signal complexe I + jQ
    iq_signal = i_signal + 1j * q_signal

    # Normalisation
    iq_signal = iq_signal / np.max(np.abs(iq_signal))

    return iq_signal

def save_iq_file(iq_signal, filename):
    """Sauvegarde au format gr_complex (float32)"""
    # Interleave I et Q
    iq_interleaved = np.zeros(len(iq_signal) * 2, dtype=np.float32)
    iq_interleaved[0::2] = iq_signal.real
    iq_interleaved[1::2] = iq_signal.imag

    iq_interleaved.tofile(filename)
    print(f"✓ Fichier IQ généré: {filename}")
    print(f"  Échantillons: {len(iq_signal)}")
    print(f"  Durée: {len(iq_signal)/SAMPLE_RATE:.3f} s")

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_oqpsk_iq.py <trame_hex>")
        print("Exemple: generate_oqpsk_iq.py 4D9E2CA2B00...")
        sys.exit(1)

    hex_frame = sys.argv[1].replace(" ", "")

    # Vérification longueur (250 bits = 62.5 hex chars, arrondi à 63)
    expected_bits = 250
    expected_hex_chars = (expected_bits + 3) // 4

    if len(hex_frame) != expected_hex_chars:
        print(f"Erreur: Trame doit faire {expected_hex_chars} caractères hex")
        print(f"        (reçu {len(hex_frame)} caractères)")
        sys.exit(1)

    print(f"Génération IQ OQPSK...")
    print(f"Trame hex: {hex_frame[:20]}...")

    # Étapes
    bits = hex_to_bits(hex_frame)[:expected_bits]  # Limiter à 250 bits
    print(f"✓ {len(bits)} bits extraits")

    chips = spread_bits(bits)
    print(f"✓ {len(chips)} chips générés (spreading x{SPREADING_FACTOR})")

    iq_signal = oqpsk_modulate(chips)
    print(f"✓ {len(iq_signal)} échantillons IQ modulés")

    # Sauvegarde
    output_file = "beacon_2g_test.iq"
    save_iq_file(iq_signal, output_file)

if __name__ == "__main__":
    main()
```

---

## 📊 Workflow Complet

### 1. Génération Trame (dsPIC33CK ou dec406)

```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/dec406_v10.2
./generate_2g_hex > trame_2g.txt
```

Output:
```
4D9E2CA2B005C1C38E... (63 caractères hex)
```

### 2. Génération IQ OQPSK (Python)

```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas
python3 generate_oqpsk_iq.py 4D9E2CA2B005C1C38E...
```

Output:
```
beacon_2g_test.iq (fichier complexe 40 kHz)
```

### 3. Test Démodulation (gr-cospas - FUTUR)

```bash
cd examples
python3 decode_iq_oqpsk.py ../beacon_2g_test.iq
```

Output:
```
✓ Trame 2G décodée: 250 bits
✓ BCH(250,202): Aucune erreur
✓ Données: ...
```

### 4. Validation (dec406_v2g)

```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/dec406_v10.2
./dec406_hex [bits_décodés]
```

---

## 🎯 Prochaines Étapes

### Étape 1 : Créer `generate_oqpsk_iq.py`
- ✅ Spec définie ci-dessus
- ⏳ Implémentation
- ⏳ Tests avec trame connue

### Étape 2 : Valider Fichiers IQ
- Vérifier format (gr_complex)
- Vérifier taux échantillonnage (40 kHz)
- Vérifier durée signal

### Étape 3 : Étendre gr-cospas
- Ajouter démodulateur OQPSK
- Intégrer désétalement PN
- Intégrer décodeur BCH

---

## ❓ Questions Ouvertes

1. **Séquence PN exacte** : À confirmer dans C/S T.018 Section 2.3
2. **Préambule 2G** : Y a-t-il un préambule spécifique avant les 250 bits ?
3. **Filtre de mise en forme** : RRC (Root Raised Cosine) ?
4. **Facteur de roll-off** : Valeur alpha ?

---

## 📚 Références

- **C/S T.018** : Spécifications balises 2G (Section 2.3 pour PN)
- **dsPIC33CK code** : Référence hardware
- **dec406_v2g.c** : Référence décodage trame

---

Tu veux qu'on commence par créer le `generate_oqpsk_iq.py` ? 🚀
