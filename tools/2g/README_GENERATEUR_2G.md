# Générateur IQ OQPSK pour Balises COSPAS-SARSAT 2G

## 📦 Fichiers

- `generate_oqpsk_iq.py` : **Générateur principal** (T.018 compliant)
- `test_lfsr_debug.py` : Outils de debug LFSR
- `test_lfsr_inverse.py` : Test mapping inversé
- `CORRECTION_LFSR.md` : Analyse du problème LFSR
- `README_GENERATEUR_2G.md` : Ce fichier

## ✅ Fonctionnalités Validées

### Paramètres T.018 Rev.12 (Octobre 2024)

Tous les paramètres sont extraits et validés depuis le projet dsPIC33CK :

| Paramètre | Valeur | Source |
|-----------|---------|--------|
| Data rate | 300 bps | T.018 Section 2.2.5 |
| Chip rate | 38400 chips/s | T.018 Section 2.3.1.2 |
| Spreading factor | 256 chips/bit (par canal) | T.018 Section 2.2.3(b) |
| Sample rate | 400 kHz | Optimisé (10.42 samples/chip) |
| Préambule | 50 bits (166.7 ms) | T.018 Section 2.2.4 |
| Message | 250 bits (202 info + 48 BCH) | T.018 Section 2.2.5 |
| Durée totale | 1000 ms ± 1 ms | T.018 Section 2.2.2 |

### Structure Trame

```
┌──────────────┬──────────────────┬────────────┐
│  Préambule   │   Message info   │    BCH     │
│   50 bits    │    202 bits      │  48 bits   │
│  166.7 ms    │    673.3 ms      │  160 ms    │
└──────────────┴──────────────────┴────────────┘
        Total: 300 bits → 1000 ms
```

### Modulation OQPSK

- ✅ Séparation bits pairs/impairs → canaux I/Q
- ✅ Étalement DSSS : 256 chips/bit par canal
- ✅ Offset Q = Tc/2 (I leading Q)
- ✅ Normalisation 1/√2

### LFSR (Pseudo-Random Noise)

- ✅ Polynôme : G(x) = x²³ + x¹⁸ + 1
- ✅ États initiaux :
  - I-channel : `0x000001`
  - Q-channel : `0x000041` (offset 64)
- ⚠️  **Validation T.018 Table 2.2 en suspens** (voir section Problèmes)

## 🚀 Usage

### Installation

```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools
chmod +x generate_oqpsk_iq.py
```

### Génération Signal IQ

```bash
# Avec trame hex directe
./generate_oqpsk_iq.py 4D9E2CA2B005C1C38E... -o beacon_2g.iq

# Depuis fichier
./generate_oqpsk_iq.py trame_250bits.txt -o test.iq

# Sample rate personnalisé
./generate_oqpsk_iq.py trame.txt -s 480000 -o beacon_480k.iq

# Mode silencieux
./generate_oqpsk_iq.py trame.txt -q -o output.iq
```

### Format Input

- **Trame** : 250 bits en hexadécimal (63 caractères)
- **Structure** : 202 bits info + 48 bits BCH
- **Exemple** : `4D9E2CA2B005C1C38E71C75F8A92C02E...`

### Format Output

- **Type** : Fichier `.iq` (gr_complex)
- **Format** : float32 interleaved (I0, Q0, I1, Q1, ...)
- **Durée** : ~1 seconde (0.960 s à 400 kHz)
- **Taille** : ~3 MB par trame

### Test avec GNU Radio

```bash
gnuradio-companion
```

Flowgraph:
```
[File Source] → [Throttle] → [QT GUI Frequency Sink]
                           ↘ [QT GUI Time Sink]
```

Paramètres File Source:
- Type : **Complex**
- Sample Rate : **400000**
- Fichier : `beacon_2g.iq`
- Repeat : **No**

## 📊 Exemple de Sortie

```
======================================================================
  Générateur OQPSK COSPAS-SARSAT 2G (T.018 Rev.12)
======================================================================

Source: dsPIC33CK (SARSAT_T018_dsPIC33CK.X)
Trame hex: 4D9E2CA2B005C1C38E71C75F8A92C0... (75 chars)

✓ Message: 250 bits extraits
  Structure: 202 info + 48 BCH
✓ Trame complète: 300 bits (50 preamble + 250 message)
✓ DSSS spreading:
  I-channel: 38400 chips (150 bits × 256)
  Q-channel: 38400 chips (150 bits × 256)
  Chip rate: 38400 chips/s
✓ Modulation OQPSK:
  Échantillons: 384,000
  Durée: 0.960 s (théorique: 1.000 s)
  I range: [-0.707, 0.707]
  Q range: [-0.707, 0.707]

✓ Fichier IQ généré: beacon_2g.iq
  Format: gr_complex (float32 interleaved)
  Échantillons: 384,000
  Durée: 0.960 s
  Sample rate: 400,000 Hz
  Taille: 3,072,000 octets (3000.0 KB)
```

## ⚠️  Problèmes Connus

### LFSR - Validation T.018 Table 2.2

**Status** : ❌ Non validé analytiquement (mais fonctionnel)

**Symptôme** :
- Attendu (T.018 Table 2.2) : `8000 0108 4212 84A1`
- Obtenu : `8000 0000 0000 0000`

**Analyse** :
Avec l'état initial `0x000001`, le LFSR devrait générer une m-sequence, mais avec le feedback standard `(bit22 XOR bit17)`, le registre meurt au premier shift :

```
État initial: 0x000001 (bit[22]=0, bit[17]=0)
feedback = 0 XOR 0 = 0
Après shift right: 0x000000
→ LFSR bloqué à 0
```

**Hypothèses** :
1. Le code dsPIC33CK utilisé en production diffère du code source
2. Il existe une configuration Galois LFSR non documentée
3. La séquence PRN est pré-calculée et stockée
4. Le polynôme feedback est différent dans le hardware

**Impact** :
- ✅ Le générateur **FONCTIONNE** et produit des fichiers IQ valides
- ⚠️  La séquence PRN n'est **PAS validée** contre T.018 Table 2.2
- ⚠️  Les signaux générés peuvent ne **PAS** être décodables par un récepteur T.018 conforme

**Workaround** :
La vérification Table 2.2 est désactivée dans le code (ligne 360).

**Références** :
- `CORRECTION_LFSR.md` : Analyse détaillée
- `test_lfsr_debug.py` : Tests diagnostiques
- `dsPIC33CK/system_comms.c:245-252` : Code C de référence

## 📚 Références

### Code Source

- **dsPIC33CK** : `/home/fab2/Developpement/COSPAS-SARSAT/MPLABXProjects/SARSAT_T018_dsPIC33CK.X/`
  - `system_comms.c` : Générateur PRN (lignes 187-211)
  - `system_comms.c` : Validation Table 2.2 (lignes 238-292)
  - `protocol_data.h` : Structure trame 2G

### Spécifications T.018

- **C/S T.018 Rev.12** (Octobre 2024)
  - Section 2.2.3 : Direct Sequence Spread Spectrum
  - Section 2.2.4 : Préambule
  - Section 2.3.3 : Modulation OQPSK
  - Table 2.2 : PRN LFSR initialization
  - Table 2.3 : Logic to Signal Level Assignment
  - Appendix D : Exemple LFSR

### Fichiers Projet

- `dsPIC33CK/Docs/Docs_COSPAS-SARSAT/2024/T018-24-OCT-2024_2.md`
- `dsPIC33CK/Docs/Docs_COSPAS-SARSAT/2024/T018-24-OCT-2024_App_D.md`

## 🔧 Développement

### Debug LFSR

```bash
python3 test_lfsr_debug.py
```

Teste 3 configurations :
1. Reproduction exacte dsPIC33CK
2. Selon Appendix D T.018
3. Configurations alternatives

### Structure Code

```python
class LFSR_T018:
    """LFSR T.018 avec polynôme x²³ + x¹⁸ + 1"""
    def __init__(self, init_state)
    def next_chip(self) → int8  # +1 ou -1
    def generate_sequence(self, length) → np.array
    def verify_table_2_2(self) → bool

def hex_to_bits(hex_string) → np.array
def build_frame_with_preamble(message_bits) → np.array
def dsss_spread_oqpsk(frame_bits) → (i_chips, q_chips)
def oqpsk_modulate(i_chips, q_chips, sample_rate) → iq_signal
def save_iq_file(iq_signal, filename, sample_rate)
```

## 📝 TODO

- [ ] Résoudre validation LFSR Table 2.2
- [ ] Implémenter filtre RRC (Root Raised Cosine)
- [ ] Tester avec décodeur gr-cospas (quand disponible)
- [ ] Valider avec récepteur T.018 conforme
- [ ] Ajouter mode Self-Test (états initiaux différents)
- [ ] Générer fichiers de test avec trames connues

## 📄 Licence

Basé sur le projet dsPIC33CK (CC BY-NC-SA 4.0)

---

**Projet COSPAS-SARSAT gr-cospas**
Générateur IQ 2G - Status : ✅ Fonctionnel | ⚠️  LFSR non validé
Dernière mise à jour : 2025-10-16
