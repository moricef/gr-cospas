# Démonstration gr-cospas - Décodeur COSPAS-SARSAT

## Vue d'ensemble

Module GNU Radio pour le décodage de signaux COSPAS-SARSAT 406 MHz.

**Caractéristiques:**
- Démodulation BPSK Biphase-L (±1.1 rad)
- Détection de porteuse (160 ms)
- Synchronisation sur préambule (15 bits)
- Vérification frame sync (9 bits)
- Support trames courtes (112 bits) et longues (144 bits)
- Décodeur adaptatif: fonctionne à n'importe quel taux d'échantillonnage

## Tests validés ✅

### 1. Fichiers Matlab I/Q (40 kHz)

**Fichier 1:** `beacon_signal_406mhz_long_msg_144bit.iq`
```bash
./decode_iq_40khz.py
```
**Résultat:** `8E3301E2402B002BBA863609670908` (15 octets, 100% correct)

**Fichier 2:** `beacon_signal_406mhz_long_msg_144bit_2.iq`
```bash
./decode_iq_40khz.py /path/to/file2.iq
```
**Résultat:** `8E3301E240298056CF99F61503780B` (15 octets, 100% correct)

### 2. GNU Radio Companion

**Flowgraph:** `decode_iq_matlab.grc`

Ouvrir dans GRC:
```bash
gnuradio-companion decode_iq_matlab.grc
```

Ou compiler et exécuter directement:
```bash
grcc decode_iq_matlab.grc
./decode_matlab_iq.py
```

**Sortie:** `decoded_output.bin` contient les données décodées

### 3. Signal synthétique (6.4 kHz)

Générer un signal de test:
```python
from gnuradio.cospas import cospas_generator
data = bytes.fromhex("8E3E0425A52B002E364FF709674EB7")
gen = cospas_generator(data_bytes=data, repeat=False)
gen.generate_and_save("/tmp/test.iq")
```

Décoder avec GRC ou Python.

## Architecture

### Bloc GNU Radio

**Nom:** `cospas_sarsat_decoder`

**Paramètres:**
- `sample_rate`: Fréquence d'échantillonnage (Hz) - défaut: 6400
- `debug_mode`: Active les messages de debug - défaut: False

**Entrée:** `complex` (signal I/Q en bande de base)

**Sortie:** `byte` (données décodées)

### Exemples fournis

| Fichier | Description | Utilisation |
|---------|-------------|-------------|
| `decode_iq_40khz.py` | Flowgraph Python pour fichiers Matlab 40 kHz | SDR, fichiers réels |
| `decode_iq_matlab.grc` | Flowgraph GRC pour fichiers Matlab | Interface graphique |
| `decode_iq_matlab_direct.py` | Décodeur Python pur (sans GNU Radio) | Debug, validation |
| `analyze_iq_matlab.py` | Analyse spectrale et temporelle | Diagnostic |
| `cospas_generator.py` | Générateur de signaux synthétiques | Tests |

## Utilisation typique - Réception SDR

Pour recevoir et décoder en temps réel avec un dongle SDR:

1. **Créer un flowgraph dans GRC:**
   - Source: `RTL-SDR Source` ou `UHD: USRP Source`
   - Fréquence centrale: 406.028 MHz
   - Taux d'échantillonnage: 250 kHz (ou plus)
   - Filtre passe-bande autour de 1200 Hz (fréquence audio du signal)
   - **Ré-échantillonneur** pour adapter au décodeur
   - **COSPAS Decoder** avec `sample_rate` approprié
   - Sink: `File Sink` ou traitement custom

2. **Recommandations:**
   - Utiliser un sample_rate multiple de 400 (débit symbole)
   - Exemples: 6400, 12800, 25600, 40000 Hz
   - Plus le taux est élevé, meilleure est la précision (mais plus de calculs)

## Performance

- ✅ **Signaux synthétiques (6.4 kHz):** Décodage parfait
- ✅ **Fichiers Matlab (40 kHz):** Décodage parfait (2/2 fichiers testés)
- ⚠️ **Ré-échantillonnage 40kHz→6.4kHz:** Perte de synchronisation (artefacts de filtre)

**Recommandation:** Utiliser le décodeur à la fréquence native du signal, sans ré-échantillonnage quand possible.

## Détails techniques

### Modulation Biphase-L

- **Bit '1':** Phase +1.1 rad → -1.1 rad (transition descendante)
- **Bit '0':** Phase -1.1 rad → +1.1 rad (transition montante)
- **Transition:** Au milieu de chaque bit

### Structure de trame

```
| Porteuse (160 ms) | Préambule (15×'1') | Frame Sync (9 bits) | Format Flag (1 bit) | Données |
```

**Frame Sync:**
- Mode Normal: `000101111`
- Mode Self-Test: `011010000`

**Format Flag:**
- `0`: Trame courte (112 bits total = 87 bits données)
- `1`: Trame longue (144 bits total = 119 bits données)

### Décodage

Le décodeur analyse la phase instantanée:
1. Détecte la porteuse (phase stable ~0 rad pendant 160 ms)
2. Détecte le saut initial (0 → ±1.1 rad)
3. Synchronise sur le préambule (15 bits à '1')
4. Vérifie le frame sync (9 bits)
5. Détecte le type de trame (format flag)
6. Décode les données bit par bit

## Intégration dans un projet

### CMakeLists.txt

```cmake
find_package(Gnuradio REQUIRED cospas)
target_link_libraries(your_target gnuradio::gnuradio-cospas)
```

### Python

```python
from gnuradio import cospas

# Créer un décodeur
decoder = cospas.cospas_sarsat_decoder(
    sample_rate=40000,  # Hz
    debug_mode=True
)
```

### C++

```cpp
#include <gnuradio/cospas/cospas_sarsat_decoder.h>

auto decoder = gr::cospas::cospas_sarsat_decoder::make(
    40000.0f,  // sample_rate
    true       // debug_mode
);
```

## Auteurs

Module développé pour le projet COSPAS-SARSAT.

## Licence

[Votre licence]
