# Comparaison Modulations COSPAS-SARSAT

## 1G vs 2G : Biphase-L vs OQPSK

---

## 📡 Balises Première Génération (1G)

### Caractéristiques Techniques

| Paramètre | Valeur |
|-----------|--------|
| **Modulation** | Biphase-L (Manchester) |
| **Débit** | 400 bps |
| **Phase shift** | ±1.1 radians |
| **Longueur trame** | 112 bits (courte) ou 144 bits (longue) |
| **Fréquence** | 406.0 - 406.1 MHz |
| **Largeur bande** | ~5 kHz |
| **FEC** | CRC uniquement (pas de correction) |

### Principe Biphase-L (Manchester)

```
Bit 0:  ▂▂▂▂▂▔▔▔▔▔   (Bas → Haut au milieu)
Bit 1:  ▔▔▔▔▔▂▂▂▂▂   (Haut → Bas au milieu)
```

**Caractéristique clé** : Transition OBLIGATOIRE au milieu de chaque bit
- Bit 0 : Transition négative → positive
- Bit 1 : Transition positive → négative

### Démodulation Biphase-L (actuelle dans gr-cospas)

**Méthode actuelle** :
1. Détection de porteuse stable (préambule)
2. Accumulation buffer (21000 échantillons minimum)
3. Machine à états : FIND_PREAMBLE → SYNC_FOUND → DECODING
4. Détection de transition de phase au milieu du bit
5. Décodage basé sur direction de transition

**Complexité** : Relativement simple (détection de transitions)

---

## 📡 Balises Seconde Génération (2G)

### Caractéristiques Techniques

| Paramètre | Valeur |
|-----------|--------|
| **Modulation** | OQPSK (Offset QPSK) + DSSS |
| **Débit** | 300 bps (données) |
| **Chip rate** | 2400 chips/s |
| **Étalement spectral** | 8 chips/bit (spreading factor) |
| **Longueur trame** | 250 bits (encodé) |
| **Longueur données** | 202 bits (après BCH) |
| **Fréquence** | 406.0 - 406.1 MHz |
| **Largeur bande** | ~5 kHz |
| **FEC** | BCH(250,202) - Correction 6 erreurs |

### Principe OQPSK + DSSS

#### 1. OQPSK (Offset Quadrature Phase Shift Keying)

```
QPSK Standard:
   I: ▔▔▔▔▔|▂▂▂▂▂
   Q: ▔▔▔▔▔|▂▂▂▂▂
   Transitions simultanées → enveloppe varie

OQPSK (Offset):
   I: ▔▔▔▔▔|▂▂▂▂▂
   Q:   ▔▔▔▔▔|▂▂▂▂▂  (décalé de Tc/2)
   Transitions alternées → enveloppe stable
```

**Avantage** : Évite les transitions de phase de 180° → Enveloppe constante

#### 2. DSSS (Direct Sequence Spread Spectrum)

Chaque bit de données est étalé sur 8 chips avec une séquence PN (Pseudo-Noise).

**Séquence d'étalement (exemple)** :
```
Bit 0 : [+1 -1 +1 +1 -1 +1 -1 -1]  (8 chips)
Bit 1 : [-1 +1 -1 -1 +1 -1 +1 +1]  (inversion)
```

**Avantages** :
- Résistance aux interférences
- Gain de traitement : 10*log10(8) = 9 dB
- Robustesse multi-trajets

### Structure de Trame 2G

```
┌────────────────────────────────────────────────┐
│  250 bits encodés (transmission)               │
├────────────────────────────────────────────────┤
│  202 bits données (après décodage BCH)         │
├────────────────────────────────────────────────┤
│  154 bits message principal (Main Field)       │
│  + 48 bits champ rotatif (Rotating Field)      │
└────────────────────────────────────────────────┘
```

**Main Field (154 bits)** :
- TAC (16 bits) - Type Approval Code
- Serial (14 bits)
- Country (10 bits)
- Position GNSS (47 bits) - Résolution 3.4m
- Vessel ID (44 bits)

**Rotating Field (48 bits)** :
- RF#0 : G.008 Objective Requirements
- RF#1 : In-Flight Emergency
- RF#2 : RLS Acknowledgement
- RF#4 : Two-Way Communication
- RF#15 : Cancellation Message

### Correction d'Erreur BCH(250,202)

**Polynôme générateur** (49 bits) :
```
g(X) = 1110001111110101110000101110111110011110010010111
```

**Capacités** :
- Détecte jusqu'à 12 erreurs
- Corrige jusqu'à 6 erreurs
- Taux de code : 202/250 = 80.8%

---

## 🔧 Défi de Démodulation OQPSK

### Différences Majeures vs Biphase-L

| Aspect | Biphase-L (1G) | OQPSK (2G) |
|--------|----------------|------------|
| **Signal** | Réel (après démod) | Complexe I+Q |
| **Synchronisation** | Recherche 15 "1" | Recherche préambule PN |
| **Démodulation** | Détection transition | Récupération horloge + DSSS |
| **Constellation** | 2 états (±1) | 4 états (QPSK) |
| **Étalement** | Aucun | 8 chips/bit |
| **Recovery** | Timing simple | Carrier + Timing + Despread |

### Blocs Nécessaires pour OQPSK

```
Échantillons IQ (complexes)
         ↓
┌────────────────────┐
│ Carrier Recovery   │ ← Récupération porteuse (PLL)
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ Matched Filter     │ ← Filtre adapté (RRC)
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ Timing Recovery    │ ← Récupération horloge (Gardner, M&M)
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ OQPSK Demodulator  │ ← Démodulation I/Q avec offset
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ PN Despreading     │ ← Désétalement séquence PN (8 chips → 1 bit)
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ BCH Decoder        │ ← Correction erreur BCH(250,202)
└─────────┬──────────┘
          ↓
  202 bits décodés
```

---

## 🎯 Stratégie d'Implémentation

### Option 1 : Module Unifié (Recommandé)

**Architecture** :
```cpp
class cospas_sarsat_decoder_impl {
    enum ModulationType { BIPHASE_L, OQPSK };
    ModulationType d_modulation;

    // Méthodes communes
    void detect_modulation();  // Auto-détection 1G vs 2G

    // Méthodes spécifiques 1G
    void decode_biphase_l();

    // Méthodes spécifiques 2G
    void decode_oqpsk();
    void pn_despread();
    void bch_decode();
};
```

**Avantages** :
- Un seul bloc GNU Radio
- Auto-détection du type de balise
- Partage du code commun (détection porteuse, etc.)

### Option 2 : Blocs Séparés

**Architecture** :
```
gr-cospas/
├── cospas_sarsat_decoder_1g (Biphase-L)
└── cospas_sarsat_decoder_2g (OQPSK)
```

**Avantages** :
- Code plus simple et isolé
- Tests indépendants
- Maintenance facilitée

**Inconvénient** :
- Duplication de code (détection porteuse, etc.)

### Option 3 : Utiliser Blocs GNU Radio Existants

**Flowgraph GNU Radio Companion** :
```
File Source
    ↓
Polyphase Clock Sync (timing recovery)
    ↓
Costas Loop (carrier recovery)
    ↓
Constellation Decoder (QPSK)
    ↓
PN Despreading (custom block)
    ↓
BCH Decoder (custom block)
    ↓
Frame Decoder
```

**Avantages** :
- Réutilisation blocs éprouvés
- Debugging visuel (GRC)
- Flexibilité

**Inconvénient** :
- Flowgraph complexe
- Pas de bloc unique

---

## 🔬 Références Techniques

### Spécifications

- **C/S T.001** : Spécifications 1G (Biphase-L)
- **C/S T.018** : Spécifications 2G (OQPSK + BCH)
- **C/S G.005** : Return Link Service (RLS)

### Séquences PN (Pseudo-Noise)

La séquence d'étalement exacte est définie dans **C/S T.018 Section 2.3**.

```
Chip sequence (8 chips per bit):
Bit 0: S0 = [c0, c1, c2, c3, c4, c5, c6, c7]
Bit 1: S1 = -S0 (inversion complète)
```

### Polynôme BCH

Défini dans **C/S T.018 Appendix B** :
```
g(x) = x^48 + x^47 + x^46 + x^44 + x^43 + ... + x^2 + x + 1
```

(49 coefficients binaires)

---

## 📝 Prochaines Étapes

1. ✅ Comprendre différences 1G vs 2G (ce document)
2. 🔨 Choisir architecture (Option 1, 2 ou 3)
3. 🔨 Implémenter démodulateur OQPSK de base
4. 🔨 Ajouter PN despreading
5. 🔨 Intégrer décodeur BCH
6. 🧪 Générer fichiers IQ test 2G
7. ✅ Valider décodage 2G

---

## 💡 Questions Ouvertes

1. **Auto-détection 1G/2G** : Comment distinguer automatiquement ?
   - Option A : Analyser préambule (différent entre 1G et 2G)
   - Option B : Tenter décodage 1G, puis 2G si échec
   - Option C : Paramètre utilisateur

2. **Complexité implémentation** : Quelle option ?
   - Option 1 : Module unifié (plus propre mais plus complexe)
   - Option 2 : Blocs séparés (plus simple)
   - Option 3 : Flowgraph GRC (plus flexible)

3. **Tests sans SDR** : Comment valider ?
   - Générer fichiers IQ synthétiques OQPSK
   - Utiliser enregistrements existants ?
   - Simulateur MATLAB/Python ?
