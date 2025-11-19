# Architecture Cible du Projet COSPAS-SARSAT

Date: 2025-10-12

## 🎯 Plateforme Cible : Odroid C4 + PlutoSDR

### Matériel

| Composant | Spécifications | Rôle |
|-----------|----------------|------|
| **Odroid C4** | ARM Cortex-A55 quad-core 2 GHz, 4 GB RAM | Processeur principal GNU Radio |
| **PlutoSDR** | AD9363 (325 MHz - 3.8 GHz), 12-bit ADC/DAC | Réception RF 406 MHz |
| **OS** | Ubuntu/Debian ARM64 | Système GNU Radio |

### Avantages de cette Configuration

✅ **PlutoSDR** :
- Réception RF directe 406.0-406.1 MHz
- Largeur bande > 5 MHz (suffisant pour COSPAS)
- Interface USB vers Odroid C4
- Driver GNU Radio natif (`gr-iio`)

✅ **Odroid C4** :
- Puissance suffisante pour GNU Radio
- Pas de ventilation active nécessaire
- Consommation faible
- Support ARM64 excellent

---

## 📡 Architecture Système Complète

```
┌─────────────────────────────────────────────────────────────┐
│                      ENVIRONNEMENT RF                       │
│                                                             │
│  Balise 1G (Biphase-L, 400 bps)  ──┐                      │
│                                     │  406.0-406.1 MHz     │
│  Balise 2G (OQPSK, 300 bps)     ──┼──→  [Antenne]        │
│                                     │                       │
└─────────────────────────────────────┼───────────────────────┘
                                      │
                                      ↓
                        ┌─────────────────────────┐
                        │      PlutoSDR           │
                        │   (AD9363 RF Frontend)  │
                        │                         │
                        │  • RX: 406.028 MHz      │
                        │  • BW: 5 MHz            │
                        │  • Sample rate: 1 Msps  │
                        └────────────┬────────────┘
                                     │ USB 2.0
                                     │ IQ Stream
                                     ↓
                        ┌─────────────────────────┐
                        │     Odroid C4           │
                        │   (GNU Radio Runtime)   │
                        │                         │
                        │  ┌──────────────────┐   │
                        │  │   gr-iio source  │   │
                        │  │  (PlutoSDR I/Q)  │   │
                        │  └────────┬─────────┘   │
                        │           │             │
                        │           ↓             │
                        │  ┌──────────────────┐   │
                        │  │  Rational        │   │
                        │  │  Resampler       │   │
                        │  │  1M → 40k Hz     │   │
                        │  └────────┬─────────┘   │
                        │           │             │
                        │           ↓             │
                        │  ┌──────────────────┐   │
                        │  │  gr-cospas       │   │
                        │  │  Auto-detect     │   │
                        │  │  1G/2G           │   │
                        │  └────────┬─────────┘   │
                        │           │             │
                        │           ↓             │
                        │  ┌──────────────────┐   │
                        │  │  Decoded bits    │   │
                        │  │  (112/144/250)   │   │
                        │  └────────┬─────────┘   │
                        │           │             │
                        │           ↓             │
                        │  ┌──────────────────┐   │
                        │  │  dec406_v1g/v2g  │   │
                        │  │  Frame Parser    │   │
                        │  └────────┬─────────┘   │
                        │           │             │
                        │           ↓             │
                        │  ┌──────────────────┐   │
                        │  │  Output:         │   │
                        │  │  - Position GPS  │   │
                        │  │  - Beacon ID     │   │
                        │  │  - MMSI/etc      │   │
                        │  └──────────────────┘   │
                        │                         │
                        └─────────────────────────┘
                                     │
                                     ↓
                        ┌─────────────────────────┐
                        │  Notification système   │
                        │  (email, alerte, log)   │
                        └─────────────────────────┘
```

---

## 🔧 Configuration PlutoSDR Optimale

### Paramètres RF

```python
# Configuration PlutoSDR pour COSPAS-SARSAT
pluto_source = iio.pluto_source(
    uri='ip:192.168.2.1',                # Adresse par défaut
    frequency=406028000,                  # 406.028 MHz (centre bande)
    samplerate=1000000,                   # 1 Msps
    bandwidth=5000000,                    # 5 MHz (filtre anti-aliasing)
    buffer_size=32768,                    # Buffer USB
    gain_mode='manual',                   # Gain manuel ou AGC
    gain=40,                              # Gain RF (à ajuster)
    filter='',                            # Pas de filtre FIR custom
    auto_filter=True                      # Auto-config filtres
)
```

### Taux d'Échantillonnage

| Étage | Fréquence | Justification |
|-------|-----------|---------------|
| **PlutoSDR RX** | 1 Msps | Confortable pour 5 kHz BW |
| **Après décimation** | 40 kHz | Même que fichiers test actuels |
| **Chip rate (2G)** | 2.4 kHz | 2400 chips/s OQPSK |
| **Bit rate (1G)** | 400 bps | Biphase-L |
| **Bit rate (2G)** | 300 bps | OQPSK + BCH |

### Chaîne de Décimation

```
PlutoSDR: 1 Msps
    ↓ Decimation 25:1
gr-cospas input: 40 kHz
```

---

## 💾 Stockage et Logging

### Sur Odroid C4

```
/home/odroid/cospas-sarsat/
├── gr-cospas/              # OOT module GNU Radio
│   ├── lib/                # Démodulateurs 1G/2G
│   └── examples/           # Flowgraphs GRC
├── dec406_v10.2/           # Décodeurs trames
│   ├── dec406_v1g          # Décodeur 1G
│   └── dec406_v2g          # Décodeur 2G
├── logs/                   # Logs décodage
│   ├── beacons_1g.log
│   └── beacons_2g.log
├── recordings/             # Enregistrements IQ (optionnel)
│   └── 2025-10-12_beacon.iq
└── config/
    └── pluto_config.json   # Config PlutoSDR
```

---

## 🚀 Flowgraph GNU Radio Companion Final

### Version Simplifiée (Recommandée)

```
┌────────────────┐
│  PlutoSDR      │
│  Source        │  1 Msps, 406.028 MHz
└───────┬────────┘
        │
        ↓
┌────────────────┐
│  Rational      │
│  Resampler     │  1M → 40k Hz
│  (25:1)        │
└───────┬────────┘
        │
        ↓
┌────────────────┐
│  gr-cospas     │
│  SARSAT        │  Auto-detect 1G/2G
│  Decoder       │
└───────┬────────┘
        │
        ↓
┌────────────────┐
│  Message       │
│  Debug         │  Affiche trames décodées
└────────────────┘
```

### Version Avancée (Debug/Test)

```
                    ┌────────────────┐
              ┌────→│  File Sink     │  Enregistrement IQ
              │     │  (optionnel)   │
              │     └────────────────┘
              │
┌─────────────┴──┐
│  PlutoSDR      │
│  Source        │
└───────┬────────┘
        │
        ├────→ [QT GUI Freq Sink]      # Visualisation spectre
        │
        ├────→ [QT GUI Waterfall]      # Cascade spectrale
        │
        ↓
┌────────────────┐
│  Rational      │
│  Resampler     │
└───────┬────────┘
        │
        ├────→ [QT GUI Time Sink]      # Forme d'onde
        │
        ↓
┌────────────────┐
│  gr-cospas     │
│  Decoder       │
└───────┬────────┘
        │
        ├────→ [Message Debug]          # Console
        │
        └────→ [ZMQ PUB Sink]           # → Application externe
```

---

## 📊 Performances Attendues

### CPU (Odroid C4)

| Charge | Usage CPU Estimé | Notes |
|--------|------------------|-------|
| **Réception PlutoSDR** | ~10-15% | Driver `gr-iio` optimisé |
| **Resampling 1M→40k** | ~5-10% | Filtre FIR |
| **gr-cospas 1G** | ~10-20% | Démodulation Biphase-L |
| **gr-cospas 2G** | ~20-30% | OQPSK + BCH |
| **Total** | ~35-50% | Marge confortable |

### Mémoire

- **GNU Radio Runtime** : ~100-200 MB
- **Buffers PlutoSDR** : ~10-20 MB
- **gr-cospas** : ~5-10 MB
- **Total** : ~200 MB (sur 4 GB disponibles)

### Latence

| Étape | Latence |
|-------|---------|
| PlutoSDR USB buffer | ~30-50 ms |
| GNU Radio processing | ~10-20 ms |
| Décodage trame | ~5-10 ms |
| **Total** | ~50-80 ms |

---

## 🔒 Mode de Fonctionnement

### Mode Service (Recommandé)

Exécution continue en arrière-plan :

```bash
# Systemd service
sudo systemctl start cospas-decoder
sudo systemctl enable cospas-decoder  # Démarrage auto
```

### Mode Manuel (Debug)

```bash
# Lancer GNU Radio Companion
gnuradio-companion pluto_cospas_decoder.grc

# Ou flowgraph Python direct
python3 pluto_cospas_decoder.py
```

---

## 🌐 Interface Utilisateur

### Option 1 : Web Dashboard (Recommandé)

```
┌────────────────────────────────────────┐
│  COSPAS-SARSAT Beacon Monitor          │
├────────────────────────────────────────┤
│  Status: ● ACTIVE                      │
│  PlutoSDR: Connected (406.028 MHz)     │
│                                        │
│  Last Beacon Decoded:                  │
│  ┌──────────────────────────────────┐  │
│  │ Time: 2025-10-12 14:32:15        │  │
│  │ Type: 2G EPIRB                   │  │
│  │ Position: 43.2°N, 5.4°E          │  │
│  │ MMSI: 227006600                  │  │
│  │ Hex ID: 9E2CA2B005C1C38E...      │  │
│  └──────────────────────────────────┘  │
│                                        │
│  [View Map] [Export CSV] [Settings]    │
└────────────────────────────────────────┘
```

Technologie : Flask/FastAPI + HTML/JS

### Option 2 : CLI Simple

```bash
$ cospas-monitor
[2025-10-12 14:32:15] BEACON DETECTED
  Type: 2G EPIRB (Second Generation)
  Position: 43.200°N, 5.400°E
  MMSI: 227006600
  Country: France (MID 228)
  Hex ID: 9E2CA2B005C1C38E...
  Map: https://www.openstreetmap.org/?mlat=43.2&mlon=5.4

[2025-10-12 14:35:42] BEACON DETECTED
  Type: 1G ELT (First Generation)
  Position: 45.123°N, 3.456°E
  ...
```

---

## 🎯 Implications pour le Développement

### Ce Qui Change

1. **Pas besoin de générateur hardware** :
   - PlutoSDR génère les signaux test via TX
   - Ou fichiers `.iq` pré-générés

2. **Tests réalistes possibles** :
   - PlutoSDR peut TX → RX en boucle locale
   - Permet validation sans balise réelle

3. **Architecture unifiée** :
   - Même flowgraph pour test et production
   - Juste changer source (File → PlutoSDR)

4. **Performance prioritaire** :
   - Optimiser pour ARM64
   - Minimiser latence CPU

---

## 📋 TODO Mis à Jour

### Phase 1 : Générateur IQ (Prioritaire)
- ✅ Créer `generate_oqpsk_iq.py`
- ⏳ Valider fichiers `.iq` 2G

### Phase 2 : Démodulateur OQPSK
- ⏳ Implémenter dans gr-cospas
- ⏳ Tester avec fichiers `.iq`

### Phase 3 : Intégration PlutoSDR
- ⏳ Créer flowgraph GRC avec PlutoSDR
- ⏳ Tester sur Odroid C4
- ⏳ Optimiser performances ARM64

### Phase 4 : Production
- ⏳ Service systemd
- ⏳ Interface web/CLI
- ⏳ Notification système

---

## 🔧 Installation sur Odroid C4

### Dépendances

```bash
# GNU Radio 3.10
sudo apt install gnuradio gr-iio

# Python dependencies
pip3 install numpy scipy

# PlutoSDR firmware
sudo apt install libiio-utils

# Compilation gr-cospas
cd gr-cospas
mkdir build && cd build
cmake ..
make -j4
sudo make install
sudo ldconfig
```

---

## 📝 Notes Importantes

1. **PlutoSDR peut aussi TRANSMETTRE** :
   - Utile pour tests en boucle
   - Génération signaux 1G/2G pour validation

2. **Odroid C4 = Pas de GPU** :
   - Limiter visualisations QT GUI en production
   - Utiliser mode headless + web dashboard

3. **Antenne 406 MHz** :
   - Dipôle λ/4 : ~18 cm
   - Gain modeste suffit pour réception locale

4. **Refroidissement** :
   - Odroid C4 : Radiateur passif OK
   - PlutoSDR : Dissipateur thermique recommandé si TX longue

---

Ça change la vision du projet ? Veux-tu qu'on adapte la stratégie de développement ? 🚀
