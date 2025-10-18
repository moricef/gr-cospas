# Roadmap Projet COSPAS-SARSAT

Date: 2025-10-12
Objectif: Récepteur balises 1G/2G + Downlink satellite 1544 MHz

---

## 🎯 Vue d'Ensemble

### Objectifs Finaux

1. **Réception balises directes 406 MHz** (1G Biphase-L + 2G OQPSK)
2. **Réception downlink satellite 1544 MHz** (MEOSAR/LEOSAR)
3. **Plateforme** : Odroid C4 + PlutoSDR
4. **Sortie** : Position GPS, ID balise, données decoded

---

## 📦 Matériel Disponible / À Venir

| Matériel | État | Notes |
|----------|------|-------|
| **Odroid C2** | ✅ Disponible (pas ici) | ARM64, moins puissant que C4 |
| **Dongle SDR** | ✅ Disponible (pas ici) | RTL-SDR ? Limité à RX uniquement |
| **PlutoSDR** | ⏳ En attente (quelques jours) | TX/RX 325 MHz - 3.8 GHz |
| **Odroid C4** | ⏳ Plus tard (après validation) | ARM64, plus puissant que C2 |
| **Parabole 1544 MHz** | ⏳ Plus tard | Réception downlink satellite |
| **Antenne 406 MHz** | ❓ À confirmer | Dipôle simple suffit pour tests |

---

## 📅 Phases de Développement

### ✅ PHASE 0 : Base Fonctionnelle (TERMINÉ)

**Objectif** : Décodage 1G Biphase-L fonctionnel

**Réalisations** :
- ✅ gr-cospas : Démodulateur Biphase-L (100% déterministe)
- ✅ dec406_v1g : Décodeur trames 1G
- ✅ Tests sur fichiers IQ synthétiques (15/15 succès)
- ✅ Buffer accumulation (élimination non-déterminisme)

**Status** : ✅ **VALIDÉ**

---

### 🔨 PHASE 1 : Générateur 2G OQPSK (EN COURS)

**Objectif** : Créer fichiers IQ test pour 2G

**Priorité** : 🔴 HAUTE (bloquant pour phase 2)

**Tasks** :
1. ⏳ Créer `generate_oqpsk_iq.py`
   - Input : Trame 250 bits (hex)
   - Output : Fichier `.iq` (40 kHz, complexe)
   - PN spreading (8 chips/bit)
   - Modulation OQPSK + offset Q

2. ⏳ Valider fichiers générés
   - Format correct (gr_complex)
   - Durée cohérente (~0.83s pour 250 bits)
   - Spectre correct (largeur ~5 kHz)

3. ⏳ Tests avec trames connues
   - Utiliser output de `generate_2g_hex`
   - Comparer avec décodeur dec406_v2g

**Délai estimé** : 1-2 jours

**Dépendances** :
- Séquence PN exacte (C/S T.018 Section 2.3)
- Trame test validée du dsPIC33CK

---

### 🔨 PHASE 2 : Démodulateur 2G OQPSK

**Objectif** : gr-cospas décode 2G OQPSK

**Priorité** : 🟠 MOYENNE (après phase 1)

**Tasks** :
1. ⏳ Architecture démodulateur
   - Carrier recovery (Costas loop ou équivalent)
   - Timing recovery (Gardner ou M&M)
   - OQPSK demodulation (avec offset Q)
   - PN despreading (corrélation 8 chips → 1 bit)

2. ⏳ Intégration BCH decoder
   - BCH(250,202) - 48 bits parité
   - Correction jusqu'à 6 erreurs

3. ⏳ Auto-détection 1G/2G
   - Analyse préambule/pattern
   - Switch automatique Biphase-L ↔ OQPSK

4. ⏳ Tests validation
   - Fichiers `.iq` générés (phase 1)
   - Taux succès > 95%

**Délai estimé** : 5-7 jours

**Dépendances** :
- Phase 1 terminée (fichiers test disponibles)
- Specs OQPSK complètes

---

### 🧪 PHASE 3 : Tests PlutoSDR (ATTENTE MATÉRIEL)

**Objectif** : Validation avec PlutoSDR réel

**Priorité** : 🟡 MOYENNE (matériel en attente)

**Tasks** :
1. ⏳ Configuration PlutoSDR
   - Firmware à jour
   - Tests RX basic (406 MHz)
   - Tests TX basic (génération porteuse)

2. ⏳ Boucle TX/RX locale
   - PlutoSDR TX : Signal 1G/2G synthétique
   - PlutoSDR RX : Réception + décodage
   - Atténuateur entre TX et RX (éviter saturation)

3. ⏳ Tests signaux réels
   - Balise test 1G (si disponible)
   - Balise test 2G (dsPIC33CK ou simulateur)

4. ⏳ Optimisation performances
   - Latence minimale
   - CPU usage acceptable (Odroid C2/C4)

**Délai estimé** : 3-4 jours (après réception PlutoSDR)

**Dépendances** :
- PlutoSDR livré ⏳
- Phases 1 et 2 terminées
- Antenne 406 MHz disponible

---

### 🚀 PHASE 4 : Réception Satellite 1544 MHz (FUTUR)

**Objectif** : Réception downlink MEOSAR/LEOSAR

**Priorité** : 🟢 BASSE (long terme)

**Context** :
- **Downlink satellite** : 1544 MHz (bande L)
- **Protocole** : Messages MEOSAR (Return Link Service)
- **Modulation** : Différente de 406 MHz (à confirmer specs)
- **Antenne** : Parabole avec LNA

**Tasks** :
1. ⏳ Étude specs downlink 1544 MHz
   - C/S G.005 (MEOSAR specifications)
   - Format messages RLS
   - Modulation utilisée

2. ⏳ Adaptation gr-cospas
   - Nouveau bloc démodulateur 1544 MHz
   - Ou flowgraph séparé ?

3. ⏳ Configuration parabole
   - Pointage satellites MEOSAR
   - LNA (Low Noise Amplifier)
   - Câblage PlutoSDR

4. ⏳ Tests réception satellite
   - Décodage messages MEOSAR
   - Validation positions

**Délai estimé** : 2-3 semaines

**Dépendances** :
- Phases 1-3 validées
- Parabole 1544 MHz disponible
- Specs C/S G.005 complètes

---

## 🔧 Contraintes Techniques

### Odroid C2 vs C4

| Caractéristique | Odroid C2 | Odroid C4 |
|-----------------|-----------|-----------|
| **CPU** | Cortex-A53 quad 2 GHz | Cortex-A55 quad 2 GHz |
| **RAM** | 2 GB | 4 GB |
| **Performance** | ~80% du C4 | 100% (référence) |
| **GNU Radio** | ✅ OK (mais plus lent) | ✅ Optimal |

**Stratégie** :
- Développer sur PC (rapide)
- Valider sur C2 (limites basses)
- Optimiser pour C4 (production)

### PlutoSDR Limitations

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| **Fréquence RX** | 325 MHz - 3.8 GHz | ✅ 406 MHz OK, ✅ 1544 MHz OK |
| **Sample rate** | 65 kHz - 61.44 MHz | ✅ Largement suffisant |
| **Bandwidth** | 0.2 MHz - 56 MHz | ✅ 5 MHz pour COSPAS OK |
| **TX power** | Variable | ⚠️ Tests boucle uniquement |
| **Dynamic range** | ~50 dB | ⚠️ Attention saturation |

---

## 📊 Planning Estimé

```
Aujourd'hui (2025-10-12)
    │
    ├─ Phase 1: Générateur 2G (1-2 jours)
    │   └─ generate_oqpsk_iq.py ✅
    │
    ├─ Phase 2: Démodulateur 2G (5-7 jours)
    │   └─ gr-cospas OQPSK ✅
    │
    ├─ Réception PlutoSDR (quelques jours)
    │
    ├─ Phase 3: Tests PlutoSDR (3-4 jours)
    │   └─ Validation TX/RX ✅
    │
    ├─ Acquisition Odroid C4
    │
    ├─ Phase 4: Satellite 1544 MHz (2-3 semaines)
    │   └─ Downlink MEOSAR ✅
    │
    └─ Production (livraison système complet)
```

**Total estimé** : ~4-6 semaines (hors délais matériel)

---

## 🎯 Prochaines Actions Immédiates

### Cette Semaine (PlutoSDR pas encore là)

1. **Créer générateur OQPSK** (`generate_oqpsk_iq.py`)
   - Trouver séquence PN dans spec T.018
   - Implémenter modulation complète
   - Générer fichiers test

2. **Commencer démodulateur OQPSK**
   - Architecture de base
   - Tests avec fichiers synthétiques
   - Intégration BCH

3. **Documentation**
   - Specs techniques détaillées
   - Guide utilisation
   - Plan tests validation

### Semaine Prochaine (avec PlutoSDR)

1. **Configuration PlutoSDR**
   - Tests basiques RX/TX
   - Calibration

2. **Tests boucle locale**
   - TX signal 1G
   - TX signal 2G
   - Validation décodage

3. **Optimisation**
   - Performances Odroid C2
   - Latence minimale
   - Robustesse

---

## 📚 Ressources Nécessaires

### Spécifications

- ✅ C/S T.001 : Balises 1G (Biphase-L)
- ⏳ C/S T.018 : Balises 2G (OQPSK) - **Section 2.3 critique**
- ⏳ C/S G.005 : MEOSAR downlink 1544 MHz

### Outils Développement

- ✅ GNU Radio 3.10+
- ✅ Python 3.8+
- ✅ gr-cospas (OOT module)
- ⏳ PlutoSDR drivers (gr-iio)
- ⏳ Odroid C2/C4 avec GNU Radio

### Matériel Test

- ⏳ PlutoSDR (quelques jours)
- ⏳ Antenne 406 MHz (dipôle simple)
- ⏳ Atténuateur RF (tests TX/RX)
- ⏳ Câbles SMA
- ⏳ Parabole 1544 MHz (long terme)

---

## 💡 Décisions Architecture

### Démodulateur Unifié vs Séparé ?

**Décision** : Module **UNIFIÉ** `gr-cospas`

**Raisons** :
- Auto-détection 1G/2G plus facile
- Code partagé (détection porteuse, etc.)
- Maintenance simplifiée
- Expérience utilisateur meilleure

**Structure** :
```cpp
class cospas_sarsat_decoder_impl {
    enum Modulation { BIPHASE_L, OQPSK };
    Modulation detect_modulation();  // Auto-detect

    void decode_1g();  // Biphase-L
    void decode_2g();  // OQPSK + BCH
};
```

### Downlink 1544 MHz : Bloc Séparé ?

**À décider** : Module séparé `gr-meosar` ou intégré ?

**Facteurs** :
- Modulation différente (probablement pas OQPSK)
- Fréquence très différente (1544 vs 406 MHz)
- Décodage messages RLS différent

**Recommandation provisoire** : Bloc séparé, décision finale après étude specs G.005

---

## 🔍 Points de Vigilance

### Séquence PN 2G

⚠️ **CRITIQUE** : Trouver séquence exacte dans C/S T.018 Section 2.3

Sans ça :
- Générateur faux
- Démodulateur ne marche pas
- Tests impossibles

**Action** : Lire spec ou reverse-engineer depuis dsPIC33CK

### Performance Odroid C2

⚠️ **RISQUE** : C2 moins puissant que C4

Mitigation :
- Optimiser code (NEON SIMD si possible)
- Réduire taux échantillonnage si besoin
- Tests précoces sur C2

### Compatibilité Downlink Satellite

⚠️ **INCERTITUDE** : Specs 1544 MHz à confirmer

Mitigation :
- Étude préalable C/S G.005
- Prototype séparé avant intégration
- Tests validation avec passes satellitaires réelles

---

## ✅ Critères de Succès

### Phase 1 (Générateur)
- ✅ Fichier `.iq` généré
- ✅ Format correct (gr_complex)
- ✅ Durée cohérente
- ✅ Visualisation spectre OK

### Phase 2 (Démodulateur)
- ✅ Décode fichiers synthétiques > 95%
- ✅ BCH correction fonctionne
- ✅ Auto-détection 1G/2G

### Phase 3 (PlutoSDR)
- ✅ RX balise simulée (TX Pluto)
- ✅ RX balise réelle (si dispo)
- ✅ Latence < 100 ms
- ✅ CPU < 60% sur Odroid C2

### Phase 4 (Satellite)
- ✅ Réception messages MEOSAR
- ✅ Décodage positions satellites
- ✅ Tracking temps réel

---

Ça te convient comme roadmap ? Veux-tu qu'on commence par le générateur OQPSK pendant que tu attends le PlutoSDR ? 🚀
