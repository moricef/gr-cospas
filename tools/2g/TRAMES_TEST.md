# Trames de Test COSPAS-SARSAT 2G

Collection de trames validées avec BCH correct pour tester le décodeur SGB.

## 📋 Trames Disponibles

### 1. EPIRB France - Mode Opérationnel

**Fichier IQ** : `trame_france_epirb.iq`

**Trame Hex** :
```
0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F
```

**Caractéristiques** :
- **Mode** : Normal (opérationnel) - Left pad: `00`
- **TAC** : 12345
- **Numéro série** : 13398
- **Pays** : 228 (France)
- **Position** : 42.85001°N, 4.95001°E (région Marseille)
- **Type** : EPIRB Maritime (MMSI)
- **MMSI** : 147937762 (MID 147 Unknown)
- **EPIRB-AIS** : 974xx6844
- **Homing** : Désactivé
- **RLS** : Désactivé
- **Test protocol** : Oui (mode test)
- **Beacon type** : EPIRB
- **Rotating field** : Type #0 (C/S G.008)
  - Temps depuis activation : 3 heures
  - Temps depuis dernière position : 5 minutes
  - Altitude : 0 m
  - HDOP/VDOP : ≤1
  - Activation : Manuelle
  - Batterie : ≤5%
  - GNSS fix : No fix
- **BCH** : ✓ Valide

**23 HEX ID** : `9C94C0E7456923456789ABC`

**Usage** : Trame réaliste pour tests complets du décodeur

---

### 2. EPIRB France - Mode Self-Test

**Fichier IQ** : `trame_france_selftest.iq`

**Trame Hex** :
```
89C3F45639195999A02B33326C3EC4400007FFF00C0283200000DCA2C07A361
```

**Caractéristiques** :
- **Mode** : Self-test - Left pad: `10`
- **TAC** : 9999 ⚠️ (< 10000, valeur de test)
- **Numéro série** : 13398
- **Pays** : 228 (France)
- **Position** : 43.20001°N, 5.39999°E (région Marseille/Aix)
- **Type** : EPIRB Maritime (MMSI)
- **MMSI** : 227006600 (MID 227 France)
- **EPIRB-AIS** : 974xx0000
- **Homing** : Désactivé
- **RLS** : Activé
- **Test protocol** : Oui (mode test)
- **Beacon type** : EPIRB
- **Rotating field** : Type #0 (C/S G.008)
  - Temps depuis activation : 3 heures
  - Temps depuis dernière position : 5 minutes
  - Altitude : 0 m
  - HDOP/VDOP : ≤1
  - Activation : Manuelle
  - Batterie : ≤5%
  - GNSS fix : No fix
- **BCH** : ✓ Valide

**23 HEX ID** : `9C949C3F4569361F6220000`

**Usage** : Test du mode self-test et RLS activé

---

## 🔧 Utilisation

### Générer les Fichiers IQ

```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools

# Trame 1 - Mode opérationnel
./generate_oqpsk_iq.py 0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F \
    -o trame_france_epirb.iq

# Trame 2 - Mode self-test
./generate_oqpsk_iq.py 89C3F45639195999A02B33326C3EC4400007FFF00C0283200000DCA2C07A361 \
    -o trame_france_selftest.iq
```

### Tester avec GNU Radio

```bash
gnuradio-companion votre_decodeur.grc
```

Flowgraph de test :
```
[File Source: trame_france_epirb.iq] → [Votre Décodeur SGB] → [Affichage résultats]
     ↓
   Complex, 400kHz
```

### Validation Décodage

**Vérifications attendues** :

1. **Détection préambule** : 50 bits à '0' (166.7 ms)
2. **Synchronisation** : Chip rate 38400 chips/s
3. **Démodulation** : OQPSK avec offset Q = Tc/2
4. **Désétalement** : DSSS 256 chips/bit
5. **BCH** : Vérification 48 bits BCH(250,202)
6. **Extraction** : Tous les champs doivent correspondre aux valeurs ci-dessus

## 📊 Comparaison des Trames

| Paramètre | Trame 1 (EPIRB) | Trame 2 (Self-test) |
|-----------|-----------------|---------------------|
| Mode | Normal (`00`) | Self-test (`10`) |
| TAC | 12345 | 9999 ⚠️ |
| RLS | Désactivé | **Activé** |
| Position | 42.85°N, 4.95°E | 43.20°N, 5.40°E |
| MMSI | 147937762 | 227006600 |
| MID | 147 (Unknown) | 227 (France) |
| Usage | Test réaliste | Test self-test/RLS |

## 🎯 Scénarios de Test

### Test 1 : Décodage Basique
**Objectif** : Vérifier que le décodeur détecte et décode une trame complète

**Trame** : `trame_france_epirb.iq`

**Validation** :
- ✓ Préambule détecté
- ✓ Synchronisation chips
- ✓ Démodulation OQPSK
- ✓ BCH valide
- ✓ TAC = 12345
- ✓ Pays = 228 (France)

---

### Test 2 : Mode Self-Test
**Objectif** : Détecter le mode self-test (left pad = `10`)

**Trame** : `trame_france_selftest.iq`

**Validation** :
- ✓ Mode self-test détecté (bits 0-1 = `10`)
- ✓ RLS activé détecté (bit 42 = `1`)
- ✓ TAC = 9999
- ✓ MMSI France valide (MID 227)

---

### Test 3 : Robustesse au Bruit

```python
# Ajouter du bruit blanc au signal IQ
import numpy as np

# Charger signal
iq_clean = np.fromfile('trame_france_epirb.iq', dtype=np.complex64)

# Ajouter bruit (SNR = 10 dB)
noise_power = np.var(iq_clean) / 10  # 10 dB SNR
noise = np.sqrt(noise_power/2) * (np.random.randn(len(iq_clean)) +
                                    1j*np.random.randn(len(iq_clean)))
iq_noisy = iq_clean + noise.astype(np.complex64)

# Sauvegarder
iq_noisy.tofile('trame_france_epirb_noisy_10dB.iq')
```

**Validation** :
- ✓ Décodage réussi avec SNR ≥ 5 dB
- ✓ BCH correction d'erreurs fonctionnelle

---

### Test 4 : Synchronisation

**Objectif** : Tester la robustesse de la synchronisation chip

**Méthode** :
1. Décaler le signal de quelques échantillons
2. Vérifier que le décodeur se synchronise correctement

```python
# Décaler de 100 échantillons
iq = np.fromfile('trame_france_epirb.iq', dtype=np.complex64)
iq_shifted = np.concatenate([np.zeros(100, dtype=np.complex64), iq])
iq_shifted.tofile('trame_france_epirb_shifted.iq')
```

---

### Test 5 : Trames Multiples

**Objectif** : Décodage de plusieurs trames consécutives

```bash
# Créer un fichier avec 5 trames
cat trame_france_epirb.iq trame_france_selftest.iq \
    trame_france_epirb.iq trame_france_selftest.iq \
    trame_france_epirb.iq > trames_multiples.iq
```

**Validation** :
- ✓ Décodage des 5 trames
- ✓ Alternance mode normal / self-test détectée
- ✓ Pas de faux positifs entre trames

## 📝 Template de Rapport de Test

```markdown
# Test Décodeur SGB - [Date]

## Configuration
- Décodeur version : x.x.x
- GNU Radio version : x.x.x
- Sample rate : 400 kHz

## Test 1 : trame_france_epirb.iq
- [ ] Préambule détecté
- [ ] Synchronisation OK
- [ ] BCH valide
- [ ] TAC = 12345
- [ ] Pays = 228
- [ ] Position = 42.85°N, 4.95°E
- [ ] 23 HEX ID = 9C94C0E7456923456789ABC

**Résultat** : ✓ PASS / ✗ FAIL

**Notes** :
...

## Test 2 : trame_france_selftest.iq
- [ ] Mode self-test détecté
- [ ] RLS activé détecté
- [ ] BCH valide
- [ ] TAC = 9999
- [ ] MMSI = 227006600

**Résultat** : ✓ PASS / ✗ FAIL

**Notes** :
...

## Conclusion
...
```

## 🔗 Ressources

- **Guide d'utilisation** : `GUIDE_UTILISATION.md`
- **Générateur** : `generate_oqpsk_iq.py`
- **Spécifications** : C/S T.018 Rev.12 (Octobre 2024)
- **Code de référence** : dsPIC33CK (SARSAT_T018_dsPIC33CK.X)

## 📊 Propriétés Signal IQ

| Propriété | Valeur |
|-----------|--------|
| Format | gr_complex (float32 interleaved) |
| Sample rate | 400,000 Hz |
| Échantillons | 384,000 |
| Durée | 0.960 s |
| Taille fichier | 3,072,000 octets (3 MB) |
| I/Q range | [-0.707, +0.707] |
| Modulation | OQPSK |
| Chip rate | 38,400 chips/s |
| Spreading | 256 chips/bit/canal |

---

**Dernière mise à jour** : 2025-10-16
**Status** : ✅ Trames validées (BCH correct)
**Prêt pour** : Tests décodeur SGB
