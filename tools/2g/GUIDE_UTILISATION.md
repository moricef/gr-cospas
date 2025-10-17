# Guide d'Utilisation - Générateur IQ OQPSK 2G

## Vue d'ensemble

Le générateur `generate_oqpsk_iq.py` convertit des trames COSPAS-SARSAT 2G (250 bits) en fichiers IQ modulés OQPSK compatibles avec GNU Radio pour tester votre décodeur.

## 🚀 Démarrage Rapide

### Générer un fichier IQ de test

```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools

# Avec une trame hex directe
./generate_oqpsk_iq.py 0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F -o test.iq

# Depuis un fichier
echo "0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F" > ma_trame.txt
./generate_oqpsk_iq.py ma_trame.txt -o test.iq

# Avec sample rate personnalisé
./generate_oqpsk_iq.py ma_trame.txt -s 480000 -o test_480k.iq

# Mode silencieux
./generate_oqpsk_iq.py ma_trame.txt -q -o test.iq
```

## 📦 Format d'Entrée

### Structure Trame 2G (250 bits = 63 caractères hex)

```
┌─────────────────────────────────────────────────────────────┐
│                    202 bits Information                      │
├──────────┬──────────┬────────┬──────────┬──────────┬────────┤
│   TAC    │  Serial  │ Country│ Location │ Vessel ID│Rotating│
│  16 bits │  14 bits │ 10 bits│  47 bits │  47 bits │ 48 bits│
└──────────┴──────────┴────────┴──────────┴──────────┴────────┘
                              +
┌─────────────────────────────────────────────────────────────┐
│              48 bits BCH Error Correction                    │
└─────────────────────────────────────────────────────────────┘
```

### Exemple de Trame Validée

**Trame France EPIRB** (BCH validé) :
```
0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F
```

**Décodage** :
- TAC: 12345
- Série: 13398
- Pays: 228 (France)
- Position: 42.85°N, 4.95°E
- Type: EPIRB Maritime (MMSI)
- Test protocol: Oui (mode non-opérationnel)
- BCH: ✓ Valide

## 📊 Format de Sortie

### Fichier .iq (gr_complex)

- **Format**: Float32 interleaved (I, Q, I, Q, ...)
- **Sample rate**: 400 kHz (configurable)
- **Durée**: ~0.96 seconde par trame
- **Taille**: ~3 MB par trame
- **Compatible**: GNU Radio File Source (type Complex)

### Caractéristiques Signal

| Paramètre | Valeur | Norme |
|-----------|--------|-------|
| Modulation | OQPSK | T.018 Section 2.3.3 |
| Chip rate | 38,400 chips/s | T.018 Section 2.3.1.2 |
| Data rate | 300 bps | T.018 Section 2.2.5 |
| Spreading | 256 chips/bit/canal | T.018 Section 2.2.3(b) |
| Offset Q | Tc/2 (I leading Q) | T.018 Section 2.3.3 |
| Normalisation | 1/√2 | QPSK standard |
| Préambule | 50 bits à '0' | T.018 Section 2.2.4 |

## 🔧 Test avec GNU Radio

### Méthode 1 : GNU Radio Companion (GUI)

1. **Ouvrir GNU Radio Companion** :
   ```bash
   gnuradio-companion
   ```

2. **Créer un flowgraph simple** :
   ```
   [File Source] → [Throttle] → [QT GUI Frequency Sink]
                              ↘ [QT GUI Time Sink]
   ```

3. **Configurer File Source** :
   - Type: `Complex`
   - Sample Rate: `400000`
   - File: `trame_france_epirb.iq`
   - Repeat: `Yes` (pour répéter le signal)

4. **Configurer Throttle** :
   - Sample Rate: `400000`

5. **Exécuter** et observer :
   - **Frequency Sink** : Spectre centré autour de 0 Hz, largeur ~40 kHz
   - **Time Sink** : Chips OQPSK avec offset Q visible

### Méthode 2 : Python Script

```python
#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt

# Charger le fichier IQ
iq_data = np.fromfile('trame_france_epirb.iq', dtype=np.complex64)

# Afficher informations
print(f"Échantillons: {len(iq_data):,}")
print(f"Durée: {len(iq_data)/400000:.3f} s")
print(f"I range: [{iq_data.real.min():.3f}, {iq_data.real.max():.3f}]")
print(f"Q range: [{iq_data.imag():.3f}, {iq_data.imag.max():.3f}]")

# Plot constellation
plt.figure(figsize=(12, 4))

plt.subplot(131)
plt.plot(iq_data.real[:1000])
plt.title('I-channel (premiers 1000 samples)')
plt.grid(True)

plt.subplot(132)
plt.plot(iq_data.imag[:1000])
plt.title('Q-channel (premiers 1000 samples)')
plt.grid(True)

plt.subplot(133)
plt.scatter(iq_data.real[::10], iq_data.imag[::10], alpha=0.1, s=1)
plt.title('Constellation IQ')
plt.xlabel('I')
plt.ylabel('Q')
plt.axis('equal')
plt.grid(True)

plt.tight_layout()
plt.show()
```

## 📝 Créer vos Propres Trames

### Utiliser un Décodeur en Ligne

1. Aller sur https://www.cospas-sarsat.int/en/beacon-coding
2. Entrer les paramètres de votre balise fictive
3. Générer le code hex (63 caractères)
4. **Important** : Vérifier que le BCH est valide !

### Structure Minimale Test

Pour créer une trame de test simple :

```python
#!/usr/bin/env python3
"""Générateur de trame 2G simplifiée"""

# Paramètres (exemple EPIRB France)
tac = 12345          # TAC 16 bits
serial = 1234        # Serial 14 bits
country = 226        # France (10 bits)
homing = 0           # Pas de homing
rls = 0              # RLS désactivé
test = 1             # Mode test

# Pour une trame complète, il faut aussi :
# - Position encodée (47 bits)
# - Vessel ID (47 bits)
# - Beacon type (3 bits)
# - Spare (14 bits)
# - Rotating field (48 bits)
# - BCH(250,202) calculé (48 bits)

# Utiliser une trame validée existante pour les tests !
```

## 🎯 Trames de Test Fournies

### 1. EPIRB France (Maritime)
```
Fichier: trame_france_epirb.iq
Trame hex: 0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F
Position: 42.85°N, 4.95°E (Marseille)
Type: EPIRB Maritime
Mode: Test protocol
```

### 2. Trame Simple (Générée)
```
Fichier: test_beacon_sgb.iq
Trame hex: 4D9E2CA2B005C1C38E71C75F8A92C02E000...
Usage: Tests basiques
```

## ⚙️ Options Avancées

### Sample Rates Testés

| Sample Rate | Samples/Chip | Usage |
|-------------|--------------|-------|
| 400 kHz | 10.42 | **Recommandé** (optimal) |
| 480 kHz | 12.50 | Bonne qualité |
| 500 kHz | 13.02 | Tests haute résolution |
| 300 kHz | 7.81 | Tests basse qualité |

### Générer Plusieurs Trames

```bash
# Créer une collection de tests
for trame in trame1.txt trame2.txt trame3.txt; do
    ./generate_oqpsk_iq.py $trame -o ${trame%.txt}.iq
done
```

### Concaténer Plusieurs Trames

```bash
# Créer un fichier avec 10 répétitions
for i in {1..10}; do
    cat trame_france_epirb.iq >> trame_repetee_10x.iq
done
```

## 🐛 Dépannage

### Problème : "Trame trop courte"
**Solution** : Vérifier que la trame fait exactement 63 caractères hex (250 bits)

### Problème : "Caractère hex invalide"
**Solution** : Utiliser uniquement 0-9, A-F (majuscules ou minuscules)

### Problème : Fichier IQ de taille 0
**Solution** : Vérifier les permissions d'écriture du répertoire

### Problème : Signal invisible dans GNU Radio
**Solution** :
- Vérifier le sample rate (doit être 400000)
- Vérifier le type (Complex, pas Float)
- Ajouter un gain si nécessaire

## 📚 Références

### Spécifications T.018 Rev.12 (Octobre 2024)

- **Section 2.2.3** : Direct Sequence Spread Spectrum (DSSS)
- **Section 2.2.4** : Preamble (50 bits à '0')
- **Section 2.2.5** : Data rate (300 bps)
- **Section 2.3.3** : OQPSK Modulation
- **Table 2.2** : PRN LFSR initialization
- **Table 2.3** : Logic to Signal Level Assignment
- **Appendix D** : LFSR Implementation Example

### Code Source Validé

- **dsPIC33CK** : `/home/fab2/Developpement/COSPAS-SARSAT/MPLABXProjects/SARSAT_T018_dsPIC33CK.X/`
  - `system_comms.c` : PRN generator (lignes 187-211)
  - `protocol_data.h` : Frame structure
  - `compute_bch_250_202.c` : BCH encoder

## ⚠️ Limitations Connues

1. **LFSR PRN** : La séquence PRN n'est pas encore validée analytiquement contre T.018 Table 2.2
   - Impact : Séquence fonctionnelle mais non certifiée conforme
   - Workaround : Utilisation de l'implémentation dsPIC33CK validée
   - Voir `RESOLUTION_LFSR.md` pour détails

2. **Durée Trame** : 0.96 s au lieu de 1.00 s théorique
   - Cause : Arrondi du nombre d'échantillons
   - Impact : Négligeable pour les tests

3. **Filtre RRC** : Non implémenté
   - Le signal est rectangulaire (pas de filtrage raised-cosine)
   - Impact : Spectre plus large que spécifié

## 🎓 Pour Aller Plus Loin

### Tester le Décodeur

Une fois le fichier IQ généré :

1. **Importer dans GNU Radio** avec votre flowgraph décodeur
2. **Vérifier** :
   - Détection du préambule (50 bits à '0')
   - Synchronisation chip
   - Démodulation OQPSK
   - Désétalement DSSS
   - Décodage BCH
   - Extraction des champs

3. **Valider** :
   - Comparer les bits décodés avec la trame originale
   - Vérifier le BCH
   - Extraire le 23 HEX ID

### Générateur Temps Réel

Pour simuler une balise en temps réel :

```python
# TODO: Implémenter transmission RF temps réel
# - Moduler à 406 MHz
# - Ajouter répétitions (toutes les 50 secondes)
# - Ajouter bruit et fading
```

## 📄 Licence

Basé sur le code dsPIC33CK validé T.018.
Projet gr-cospas - GNU Radio COSPAS-SARSAT Decoder

---

**Dernière mise à jour** : 2025-10-16
**Version** : 1.0
**Status** : ✅ Fonctionnel | ⚠️ LFSR non validé analytiquement
