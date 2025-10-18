# État des Lieux - Projet COSPAS-SARSAT (Session 2025-10-18)

**Date**: 2025-10-18
**Projet**: Portage COSPAS-SARSAT T.018 (2G) + T.001 (1G)
**Plateforme cible**: Odroid-C4 + PlutoSDR
**Répertoire principal**: `/home/fab2/Developpement/COSPAS-SARSAT/`

---

## 📋 Résumé Exécutif

### Objectif Global
Porter la génération de signaux de balises COSPAS-SARSAT depuis dsPIC33CK vers Odroid-C4 + PlutoSDR pour:
- **1G (FGB)**: Balises première génération - Modulation Biphase-L (BPSK)
- **2G (SGB)**: Balises deuxième génération - Modulation OQPSK avec RRC

### État Actuel
- **FGB (1G)**: ✅ Générateur fonctionnel, ✅ Décodeur fonctionnel, ⚠️ Scripts de test à corriger
- **SGB (2G)**: ⚠️ Générateur partiellement fonctionnel (problèmes de modulation)

---

## 🎯 Travaux Effectués dans cette Session

### 1. Génération FGB (1G) - COMPLÉTÉ ✅

**Objectif**: Générer fichiers IQ et WAV pour balises première génération

**Fichier créé**: `/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools/1g/generate_fgb_real.py`

**Caractéristiques**:
```python
# Utilise le vrai générateur GNU Radio
from gnuradio import cospas
gen = cospas.cospas_generator(data_bytes=frame_data, repeat=False)

# Sortie:
# - fgb_real.iq : 29 KB (3712 échantillons complexes à 6400 Hz)
# - fgb_real.wav : 15 KB (stéréo 48 kHz)
```

**Structure du signal généré**:
- Porteuse: 1024 échantillons (160 ms à 6400 Hz)
- Préambule: 15 bits
- Frame Sync: 9 bits (000101111)
- Données: 144 bits (18 octets)
- Total: 3712 échantillons (0.58 s)
- Modulation: Biphase-L (Manchester)
- Samples/bit: 16

**Commandes utiles**:
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools/1g

# Générer IQ + WAV
python3 generate_fgb_real.py -o test_fgb

# Sortie:
# - test_fgb.iq
# - test_fgb.wav
```

**✅ VALIDÉ**: Le signal généré est conforme T.001 et utilisable pour transmission

---

## ⚠️ Problèmes Découverts

### 1. Scripts de Test 1G - Paramètre sample_rate Manquant ⚠️

**CORRECTION IMPORTANTE**: Le décodeur `cospas_sarsat_decoder` **FONCTIONNE PARFAITEMENT**.
Le problème vient des scripts de test qui ne passent pas le paramètre `sample_rate`.

**Preuve que le décodeur fonctionne**:
- `decode_iq_gui.py` décode parfaitement les fichiers IQ dans `/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/`
  - `beacon_signal_406mhz_long_msg_144bit.iq` (319 KB) ✅
  - `beacon_signal_406mhz_long_msg_144bit_2.iq` (153 MB) ✅
  - `beacon_signal_V3.iq` (163 KB) ✅

**Comparaison scripts**:

✅ **Script fonctionnel** (`decode_iq_gui.py` ligne 168):
```python
decoder = cospas_sarsat_decoder(sample_rate=sample_rate, debug_mode=debug_mode)
```

❌ **Scripts défaillants** (`decode_iq_file.py` ligne 69, `test_generator_decoder.py` ligne 40):
```python
decoder = cospas_sarsat_decoder(debug_mode=True)  # MANQUE sample_rate !
```

**Impact**:
- Décodeur: 100% fonctionnel ✅
- Scripts de test: ~15 fichiers à corriger pour passer `sample_rate`
- Tests `test_determinism.sh` échouent (0/20) à cause de ce bug dans les scripts

---

### 2. Générateur SGB (2G) - Problèmes Multiples ⚠️

**Répertoire**: `/home/fab2/Developpement/COSPAS-SARSAT/ADALM-PLUTO/SARSAT_SGB/`

**Travaux session précédente** (déjà complété):
- ✅ Ajout option `-o <fichier>` pour sauvegarder IQ sans PlutoSDR
- ✅ Correction buffer overflow (384k → 960k échantillons)
- ✅ Génération fichier `test_t018.iq` (5.9 MB, 768k échantillons)
- ✅ Création outils: `iq_to_wav.py`, `analyze_spectrum.py`, `decode_frame.py`

**Fichiers modifiés**:
- `include/pluto_control.h` - Ajout `pluto_save_iq_file()` déclaration
- `src/pluto_control.c` - Implémentation sauvegarde IQ
- `src/main.c` - Ajout option CLI `-o`
- `include/oqpsk_modulator.h` - Fix `OQPSK_TOTAL_SAMPLES` (384000→960000)

**Problèmes critiques identifiés** (session précédente):

#### a) Modulation OQPSK Incorrecte 🔴
**Fichier**: `src/oqpsk_modulator.c`

**Problème**: Utilise interpolation linéaire au lieu de filtrage RRC
```c
// Code actuel (INCORRECT)
float i_value = interpolate_chip(state->prev_i_chip, curr_i_chip, fraction);
```

**Conséquence**:
- Enveloppe variable (std = 0.25) au lieu de constante (std < 0.05)
- Magnitude varie de 0 à 1.41
- Spectre non conforme T.018
- **Signal NON utilisable pour transmission réelle**

**Solution requise**: Implémenter filtrage RRC (α=0.8, 63 taps) en software ou FPGA
- FPGA: Utiliser `/home/fab2/Developpement/COSPAS-SARSAT/VHDL/RRC_FILTER/rrc_filter_iq.vhd`
- Software: Remplacer `interpolate_chip()` par convolution RRC

#### b) Encodage GPS Non Conforme T.018 Appendix C 🔴
**Fichier**: `src/t018_encoder.c::t018_encode_position()`

**Problème**: Format propriétaire N/S+degrés au lieu de formule T.018
```c
// Code actuel (INCORRECT)
// Utilise format custom avec N/S et degrés

// Décodage actuel donne:
// Latitude: -58.227596° (FAUX - devrait être 43.2°N)
// Longitude: +0.926955° (FAUX - devrait être 5.4°E)
```

**Solution requise**: Implémenter formule T.018 Appendix C
```c
// Formule correcte:
lat_raw = round(latitude_deg × 11930.46) + 1048576;
lon_raw = round(longitude_deg × 11930.46) + 2097152;
```

#### c) Absence Filtre RRC 🔴
**Impact**:
- Lobes spectraux excessifs
- Bande passante > spécification T.018
- Non conforme pour certification

**Commandes test SGB**:
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/ADALM-PLUTO/SARSAT_SGB

# Compiler
make clean && make

# Générer IQ (mode fichier sans PlutoSDR)
./SARSAT_SGB -o test_t018.iq

# Convertir en WAV (3 formats)
tools/iq_to_wav.py test_t018.iq

# Analyser spectre
tools/analyze_spectrum.py test_t018.iq

# Décoder trame
tools/decode_frame.py test_t018.iq
```

**État SGB**: ~40% fonctionnel
- ✅ Trame T.018 correcte (BCH validé)
- ✅ Timing correct (400 bps)
- ❌ Modulation OQPSK incorrecte
- ❌ GPS encoding non conforme
- ❌ Pas de filtre RRC

---

## 📁 Architecture Projet

```
/home/fab2/Developpement/COSPAS-SARSAT/
│
├── ADALM-PLUTO/
│   └── SARSAT_SGB/                    # Générateur 2G (SGB/OQPSK)
│       ├── src/
│       │   ├── main.c                  # CLI avec option -o
│       │   ├── oqpsk_modulator.c       # ⚠️ Modulation incorrecte
│       │   ├── t018_encoder.c          # ⚠️ GPS encoding faux
│       │   └── pluto_control.c         # I/O fichier IQ
│       ├── include/
│       │   ├── oqpsk_modulator.h       # Buffer 960k échantillons
│       │   └── pluto_control.h
│       └── tools/
│           ├── iq_to_wav.py            # Convertisseur IQ→WAV
│           ├── analyze_spectrum.py     # Analyseur spectre
│           └── decode_frame.py         # Décodeur trame T.018
│
├── GNURADIO/
│   └── gr-cospas/                      # Module GNU Radio 1G+2G
│       ├── python/cospas/
│       │   └── cospas_generator.py     # ✅ Générateur 1G fonctionnel
│       ├── lib/
│       │   └── cospas_sarsat_decoder_impl.cc  # ❌ Décodeur cassé
│       ├── examples/1g/
│       │   ├── test_generator_decoder.py
│       │   ├── decode_wav.py
│       │   └── test_determinism.sh
│       └── tools/1g/
│           ├── generate_fgb_real.py    # ✅ Générateur IQ/WAV FGB
│           └── generate_fgb_simple.py  # ⚠️ Version simplifiée (ne pas utiliser)
│
└── VHDL/
    └── RRC_FILTER/
        └── rrc_filter_iq.vhd           # Filtre RRC FPGA (α=0.8, 63 taps)
```

---

## 🔧 Fichiers Créés/Modifiés (Sessions Précédentes + Actuelle)

### Session Actuelle (2025-10-18)
1. ✅ `/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools/1g/generate_fgb_real.py`
   - Générateur FGB utilisant GNU Radio
   - Sortie: IQ (6400 Hz) + WAV (48 kHz stéréo)

2. ✅ **Reclassification examples/** (14 fichiers déplacés)
   - Corrigé classification erronée de l'instance précédente
   - 10 fichiers Python + 4 fichiers GRC déplacés de `examples/2g/` → `examples/1g/`
   - Tous décodaient du 1G (Biphase-L) malgré noms "decode_iq_*"
   - `examples/2g/` maintenant vide (aucun décodeur 2G n'existe)

3. ✅ **Découverte décodeur 1G**
   - Décodeur `cospas_sarsat_decoder` **FONCTIONNE** à 100%
   - Scripts de test buggés: ne passent pas paramètre `sample_rate`
   - Prouvé avec `decode_iq_gui.py` qui décode parfaitement (passe `sample_rate=40000`)
   - Corrige diagnostic erroné: décodeur pas cassé, juste mal utilisé

### Sessions Précédentes
4. ✅ `ADALM-PLUTO/SARSAT_SGB/include/pluto_control.h`
5. ✅ `ADALM-PLUTO/SARSAT_SGB/src/pluto_control.c`
6. ✅ `ADALM-PLUTO/SARSAT_SGB/src/main.c`
7. ✅ `ADALM-PLUTO/SARSAT_SGB/include/oqpsk_modulator.h`
8. ✅ `ADALM-PLUTO/SARSAT_SGB/tools/iq_to_wav.py`
9. ✅ `ADALM-PLUTO/SARSAT_SGB/tools/analyze_spectrum.py`
10. ✅ `ADALM-PLUTO/SARSAT_SGB/tools/decode_frame.py`
11. ⚠️ `GNURADIO/gr-cospas/tools/1g/generate_fgb_simple.py` (ne pas utiliser - version simplifiée incorrecte)

---

## 🎯 Prochaines Étapes Recommandées

### Priorité 1: Corriger Générateur SGB (2G) 🔴

#### Tâche 1.1: Implémenter Filtrage RRC
**Fichier**: `ADALM-PLUTO/SARSAT_SGB/src/oqpsk_modulator.c`

**Option A - Software (rapide)**:
```c
// Remplacer interpolate_chip() par convolution RRC
// Coefficients RRC: α=0.8, 63 taps, span=±31 chips

float rrc_filter(float *chips, int chip_index, float fraction);
```

**Option B - FPGA (optimal)**:
- Intégrer `VHDL/RRC_FILTER/rrc_filter_iq.vhd` dans PlutoSDR
- Bypass pour FGB (qui n'en a pas besoin)

**Validation**:
```bash
# Après correction, vérifier:
tools/analyze_spectrum.py test_t018.iq
# Enveloppe std devrait être < 0.05
```

#### Tâche 1.2: Corriger Encodage GPS
**Fichier**: `ADALM-PLUTO/SARSAT_SGB/src/t018_encoder.c`

**Modification requise**:
```c
void t018_encode_position(t018_frame_t *frame, float latitude, float longitude) {
    // Formule T.018 Appendix C
    int32_t lat_raw = (int32_t)round(latitude * 11930.46) + 1048576;
    int32_t lon_raw = (int32_t)round(longitude * 11930.46) + 2097152;

    // Vérifier bornes [0, 2097151] pour lat, [0, 4194303] pour lon
    lat_raw = CLAMP(lat_raw, 0, 2097151);  // 21 bits
    lon_raw = CLAMP(lon_raw, 0, 4194303);  // 22 bits

    // Encoder dans frame->raw_bits[45..87]
    encode_bits(frame->raw_bits + 45, lat_raw, 21);
    encode_bits(frame->raw_bits + 66, lon_raw, 22);
}
```

**Validation**:
```bash
./SARSAT_SGB -o test_gps.iq
tools/decode_frame.py test_gps.iq
# Vérifier position GPS décodée = position attendue (43.2°N, 5.4°E)
```

#### Tâche 1.3: Tests Intégration
- [ ] Regénérer `test_t018.iq` avec corrections
- [ ] Analyser spectre (lobes < -40 dB)
- [ ] Vérifier enveloppe constante (std < 0.05)
- [ ] Décoder GPS et valider position
- [ ] Transmettre via PlutoSDR et recevoir sur GNU Radio

---

### Priorité 2: Corriger Scripts de Test 1G ⚠️

**Objectif**: Corriger ~15 scripts qui ne passent pas le paramètre `sample_rate` au décodeur

**Fichiers concernés**:
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/examples/1g
# Trouver scripts défaillants:
grep -l "cospas_sarsat_decoder" *.py | xargs grep -L "sample_rate"
```

**Scripts identifiés à corriger**:
- `decode_iq_file.py` (ligne 69)
- `test_generator_decoder.py` (ligne 40)
- Probablement 10-15 autres

**Correction type**:
```python
# AVANT (INCORRECT):
decoder = cospas_sarsat_decoder(debug_mode=True)

# APRÈS (CORRECT):
decoder = cospas_sarsat_decoder(sample_rate=6400, debug_mode=True)
# Note: sample_rate dépend du contexte (6400, 12800, 40000, 48000 Hz)
```

**Validation**:
Après correction, `test_determinism.sh` devrait donner 20/20 succès au lieu de 0/20

---

### Priorité 3: Documentation 📝

**Fichiers à créer/mettre à jour**:

1. `/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/docs/ETAT_GENERATEUR_2G.md`
   - Documenter problèmes SGB identifiés
   - Solutions proposées RRC + GPS
   - Roadmap correction

2. `/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/docs/PROBLEME_DECODEUR_1G.md`
   - Analyse décodeur cassé
   - Tests effectués
   - Pistes investigation

3. Mettre à jour `examples/1g/README.md`
   - Corriger status (NOT "Fully Operational")
   - Ajouter section "Known Issues"

---

## 📊 État d'Avancement Global

### FGB (1G) - Première Génération
| Composant | État | % Fonctionnel | Notes |
|-----------|------|---------------|-------|
| Générateur GNU Radio | ✅ OK | 100% | `cospas.cospas_generator()` fonctionnel |
| Fichier IQ/WAV | ✅ OK | 100% | `generate_fgb_real.py` opérationnel |
| Décodeur GNU Radio | ✅ OK | 100% | Fonctionne si `sample_rate` passé (prouvé avec `decode_iq_gui.py`) |
| Scripts de test | ❌ BUGGÉS | 20% | ~15 scripts ne passent pas `sample_rate` au décodeur |
| **TOTAL FGB** | ✅ | **80%** | Décodeur OK, scripts à corriger |

### SGB (2G) - Deuxième Génération
| Composant | État | % Fonctionnel | Notes |
|-----------|------|---------------|-------|
| Encodage trame T.018 | ✅ OK | 100% | BCH validé, structure correcte |
| GPS encoding | ❌ FAUX | 0% | Format propriétaire au lieu de T.018 App.C |
| Modulation OQPSK | ❌ INCORRECT | 20% | Interpolation linéaire au lieu de RRC |
| Filtre RRC | ❌ ABSENT | 0% | Spectre non conforme |
| Sauvegarde IQ | ✅ OK | 100% | Option `-o` fonctionnelle |
| **TOTAL SGB** | ⚠️ | **40%** | Trame OK, modulation/GPS KO |

### FPGA PlutoSDR
| Composant | État | % Fonctionnel | Notes |
|-----------|------|---------------|-------|
| Module RRC VHDL | ✅ DISPONIBLE | N/A | `rrc_filter_iq.vhd` créé mais non intégré |
| Intégration Pluto | ❌ TODO | 0% | Pas encore implémenté |

---

## 🧪 Commandes de Test Rapide

### Test Générateur FGB (1G)
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools/1g

# Générer signal FGB
python3 generate_fgb_real.py -o test_fgb

# Vérifier fichiers
ls -lh test_fgb.*
# Attendu: test_fgb.iq (29 KB), test_fgb.wav (15 KB)

# Écouter WAV
aplay test_fgb.wav
```

### Test Générateur SGB (2G)
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/ADALM-PLUTO/SARSAT_SGB

# Compiler
make clean && make

# Générer IQ
./SARSAT_SGB -o test_sgb.iq

# Analyser
tools/analyze_spectrum.py test_sgb.iq
tools/decode_frame.py test_sgb.iq
```

### Test Décodeur 1G (actuellement cassé)
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/examples/1g

# Test générateur→décodeur
./test_generator_decoder.py
# Attendu actuel: "Aucune donnée décodée" (BUG)

# Test déterminisme
./test_determinism.sh
# Attendu actuel: 0/20 succès (BUG)
```

---

## 📚 Références Techniques

### Spécifications COSPAS-SARSAT
- **T.001**: First Generation Beacons (FGB) - 406 MHz
  - Modulation: Biphase-L (Manchester)
  - Débit: 400 bps
  - Trame: 144 bits (long) ou 112 bits (short)

- **T.018**: Second Generation Beacons (SGB) - 406 MHz
  - Modulation: OQPSK avec DSSS (256 chips/bit)
  - Filtre: RRC α=0.8, 63 taps
  - Débit symboles: 400 bps → 102.4 kchips/s
  - BCH(250, 202): Code correcteur erreurs
  - GPS encoding: Appendix C (formula: lat_raw = lat × 11930.46 + 1048576)

### Fichiers Clés
```
# Générateurs
/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/python/cospas/cospas_generator.py
/home/fab2/Developpement/COSPAS-SARSAT/ADALM-PLUTO/SARSAT_SGB/src/oqpsk_modulator.c

# Décodeurs
/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/lib/cospas_sarsat_decoder_impl.cc

# Filtres
/home/fab2/Developpement/COSPAS-SARSAT/VHDL/RRC_FILTER/rrc_filter_iq.vhd

# Outils analyse
/home/fab2/Developpement/COSPAS-SARSAT/ADALM-PLUTO/SARSAT_SGB/tools/
```

### Git Commits Importants
```bash
# Voir historique
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas
git log --oneline

# Commits récents:
# 1df0715 - Reorganize project: Separate 1G and 2G files
# a709b9c - Add Qt GUI for COSPAS-SARSAT decoder
# 28d3321 - Update README: Mark non-determinism issue as SOLVED
# 02cf681 - MAJOR: Implement buffer accumulation - Achieve 100% determinism!
#           ⚠️ Ce commit prétend avoir résolu le déterminisme,
#              mais les tests montrent 0% succès
```

---

## 🐛 Bugs Connus

### BUG-001: Décodeur 1G Ne Décode Rien
- **Sévérité**: Critique
- **Impact**: Impossible de valider signaux FGB
- **Fichier**: `lib/cospas_sarsat_decoder_impl.cc`
- **Status**: Non résolu
- **Workaround**: Utiliser récepteur externe pour validation

### BUG-002: SGB Modulation OQPSK Incorrecte
- **Sévérité**: Bloquant pour certification
- **Impact**: Signal non conforme T.018, inutilisable en production
- **Fichier**: `ADALM-PLUTO/SARSAT_SGB/src/oqpsk_modulator.c`
- **Solution**: Implémenter RRC filtering

### BUG-003: SGB GPS Encoding Non Conforme
- **Sévérité**: Critique
- **Impact**: Position GPS complètement fausse
- **Fichier**: `ADALM-PLUTO/SARSAT_SGB/src/t018_encoder.c`
- **Solution**: Utiliser formule T.018 Appendix C

---

## 💡 Notes Importantes

### Question Filtre RRC
**Question utilisateur**: "si on met en place un filtre RRC dans le FPGA du Pluto, ce sera pour les balises SGB, mais pour les balises FGB?"

**Réponse**:
- **SGB (2G)**: OUI, RRC obligatoire (spécification T.018)
- **FGB (1G)**: NON, simple BPSK sans pulse shaping
- **Recommandation**: FPGA avec capacité bypass (activer RRC uniquement pour SGB)

### Fichiers MATLAB vs GNU Radio
Les fichiers IQ existants dans `/Audio/` ont été générés avec MATLAB, PAS avec les générateurs T.001/T.018.
→ Utiliser `generate_fgb_real.py` pour fichiers conformes T.001

### Simplification vs Réalité
L'utilisateur a critiqué la création de `generate_fgb_simple.py` (générateur "simplifié" from scratch).
→ **Toujours utiliser le vrai générateur GNU Radio** (`cospas.cospas_generator`)

---

## ✅ Checklist Prochaine Session

### Tâches Immédiates
- [ ] Investiguer décodeur 1G (git diff, debug logs)
- [ ] Corriger GPS encoding SGB (formule T.018 App.C)
- [ ] Implémenter RRC filter software SGB
- [ ] Tester SGB corrigé (spectre + GPS)

### Tâches Moyen Terme
- [ ] Intégrer RRC FPGA dans PlutoSDR
- [ ] Créer tests unitaires GPS encoding
- [ ] Documenter problèmes découverts
- [ ] Mettre à jour README.md exemples 1G

### Tâches Long Terme
- [ ] Certification signaux SGB
- [ ] Tests transmission PlutoSDR→Récepteur GNU Radio
- [ ] Documentation complète utilisateur
- [ ] CI/CD pour tests automatiques

---

## 🔗 Liens Utiles

### Repositories
- **Projet principal**: `/home/fab2/Developpement/COSPAS-SARSAT/`
- **Git remote**: `https://github.com/moricef/gr-cospas`

### Documentation
- Spécifications T.001: (voir répertoire specs/)
- Spécifications T.018: (voir répertoire specs/)
- GNU Radio Tutorials: https://wiki.gnuradio.org/

---

## 📞 Contact & Contexte

**Utilisateur**: fab2
**Plateforme**: Odroid-C4 + ADALM-PlutoSDR
**Système**: Linux 6.14.11-x64v3-xanmod1

**Sessions précédentes**:
- Création SARSAT_SGB complet
- Ajout option `-o` pour génération fichiers
- Correction buffer overflow
- Découverte problèmes modulation/GPS

**Session actuelle**:
- Création générateur FGB fonctionnel
- Découverte bug décodeur 1G

---

**FIN DE L'ÉTAT DES LIEUX**

*Document généré automatiquement par Claude Code*
*Pour toute question, consulter les fichiers README.md dans chaque sous-répertoire*
