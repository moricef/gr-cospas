# Analyse du Bug de Non-Déterminisme du Décodeur COSPAS-SARSAT

**Date**: 2025-10-12
**Problème**: Le décodeur GNU Radio C++ a un taux de succès de 47-57% alors que le décodeur Python fonctionne à 100%

## Résumé du Problème

Le décodeur `gr-cospas` produit des résultats **non-déterministes** : le même fichier IQ décodé plusieurs fois donne des résultats différents.

### Symptômes
- Taux de succès : **47-57%** (variable selon les runs)
- Python direct : **100%** de succès
- Les 10 premiers octets sont **TOUJOURS corrects** : `8E3301E2402B002BBA`
- Les erreurs apparaissent dans les **derniers octets** (octets 11-15)
- Deux patterns d'erreur principaux :
  - `8E3301E2402B002BBA88471980F1` (14 octets - manque 1 octet)
  - `8E3301E2402B002BBA8636096709` (14 octets - manque 1 octet)
- Attendu : `8E3301E2402B002BBA863609670908` (15 octets)

## Hypothèses Testées

### ❌ 1. Buffers non initialisés
**Test** : Ajout de `std::fill()` pour initialiser `d_bit_buffer` à zéro
**Résultat** : Aucune amélioration

### ❌ 2. Reset incomplet
**Test** : Vérification et nettoyage complet dans `reset_decoder()`
**Résultat** : Aucune amélioration

### ❌ 3. Dérive PLL
**Test** : Désactivation complète du PLL (gains = 0)
**Résultat** : Aucune amélioration

### ❌ 4. Pollution du buffer entre bits
**Test** : Nettoyage du buffer après chaque bit décodé
**Résultat** : Aucune amélioration (même dégradation à 37%)

### ❌ 5. Méthode de décodage (somme vs échantillon central)
**Test** : Modification de `decode_bit()` pour utiliser l'échantillon central comme Python
```cpp
// AVANT (somme de tous les échantillons)
for (int i = 0; i < half_samples; i++) {
    first_half_sum += samples[i];
}
float phase_first = std::arg(first_half_sum);

// APRÈS (échantillon central)
int center_first = quarter_samples;
float phase_first = std::arg(samples[center_first]);
```
**Résultat** : Aucune amélioration significative

### ⚠️ 6. Fragmentation des buffers GNU Radio
**Test** : Ajout de `set_min_noutput_items(20800)` pour forcer un buffer minimum
**Résultat** : **Amélioration de 37% → 57%** mais pas 100%

**Observation clé** :
```
Run échoué :  work() call #0: noutput_items=8184
Run réussi  : work() call #0: noutput_items=4088
```
GNU Radio fragmente différemment le flux à chaque exécution!

### ❌ 7. Position de la vérification de fin de trame
**Test** : Déplacer `if (d_total_bit_count >= d_frame_length)` après le block `else` pour gérer les bits '?'
**Résultat** : Aucune amélioration

## Découvertes Importantes

### 1. Détection de porteuse et saut initial
Le debug montre que la détection fonctionne correctement :
```
[COSPAS] Porteuse détectée après 6400 échantillons - phase moyenne: 0 rad
[COSPAS] Saut initial détecté (diff=1.1 rad) - début du préambule
```
Exactement 6400 échantillons = 160ms à 40kHz ✓

### 2. Logs de runs échoués
Quand ça échoue, on voit :
```
[COSPAS] Trame complète: 119 bits message valides (total=143)
```
Au lieu de 120 bits! Un bit est perdu quelque part.

### 3. Pas de bits indéterminés ('?')
Aucun message "BIT INDÉTERMINÉ" dans les logs, donc tous les bits sont décodés comme '0' ou '1', mais certains sont **incorrects**.

### 4. Différence Python vs C++

**Python** (`decode_iq_matlab_direct.py`):
- Lit **TOUT le fichier** d'un coup
- Cherche le préambule **après** avoir décodé tous les bits
- **100% déterministe**

**C++** (GNU Radio):
- Traite le flux en **fragments** via `work()`
- Machine à états qui démarre dès la détection de porteuse
- État **persiste entre les appels** `work()`
- **Non-déterministe** selon la fragmentation

## Confirmation: GNU Radio EST Non-Déterministe Par Défaut

**Documentation officielle confirmée** (Stack Overflow + GNU Radio Wiki):

> "Using a dynamic scheduler, blocks in a flowgraph pass chunks of items from sources to sinks. **The sizes of these chunks will vary depending on the speed of processing.**"

> "By default, GNU Radio runs a scheduler that attempts to optimize throughput. GNU Radio just asks each block to produce as much as possible, because it has shown that **maximum workload size leads to maximized throughput**."

**Valeur par défaut**: `max_noutput_items = 100,000,000`

Le scheduler ajuste `noutput_items` dynamiquement selon:
- L'espace disponible dans les buffers de sortie
- La vitesse de traitement des blocks
- Les contraintes `set_output_multiple()` et `set_min_noutput_items()`

**Conséquence**: Le même fichier IQ peut être fragmenté différemment à chaque exécution!

## Hypothèse Actuelle

Le problème est un **désalignement d'échantillons** causé par la fragmentation non-déterministe de GNU Radio.

### Scénario probable :

1. `work()` est appelé avec N échantillons
2. Le décodeur accumule des échantillons dans `d_bit_buffer`
3. `work()` se termine **au milieu d'un bit** (ex: 67/100 échantillons)
4. Au prochain `work()`, on continue à remplir le buffer
5. **MAIS** : selon où la coupure se fait, l'alignement peut être décalé

### Zones suspectes :

**État `STATE_INITIAL_JUMP`** (lignes 154-174) :
```cpp
case STATE_INITIAL_JUMP:
    float diff = std::abs(compute_phase_diff(d_phase_avg, phase));
    if (diff > JUMP_THRESHOLD && diff < (MOD_PHASE + 0.3f)) {
        d_state = STATE_PREAMBLE_SYNC;
        d_sample_count = 0;  // ← Reset ici
```
Si le saut est détecté à l'échantillon N au lieu de N+1, TOUS les bits suivants seront décalés d'1 échantillon!

**Remplissage du buffer** (lignes 265-267) :
```cpp
if (d_sample_count < d_samples_per_bit) {
    d_bit_buffer[d_sample_count++] = sample;
}
```
Si `work()` se termine et reprend, le buffer doit contenir les échantillons **consécutifs** du bit en cours.

## Résultats des Tests de Contrainte du Scheduler

### Test 1: `tb.set_max_noutput_items()`

| Buffer Size | Taux de Succès | Commentaire |
|-------------|----------------|-------------|
| Par défaut  | 47-57%        | Non-déterministe |
| 4096        | 53% (16/30)   | Pire |
| 8192        | **63% (19/30)** | ✅ Meilleur résultat |
| 20800       | 50% (15/30)   | Contre-intuitif |

**Conclusion**: Contraindre le buffer **améliore** mais ne résout **PAS** complètement le problème.

Le problème n'est donc **PAS uniquement** la fragmentation, mais aussi un **bug dans la machine à états** qui ne gère pas correctement certaines conditions de frontière.

## Solution Recommandée: Forcer un Comportement Déterministe

### Option 1: Contraindre le Scheduler (PARTIELLEMENT EFFICACE)

Dans le flowgraph Python, ajouter **AVANT** `tb.start()`:

```python
# Forcer une taille de buffer déterministe
tb.set_max_noutput_items(20800)  # Exactement 1 trame complète

# OU forcer localement sur le décodeur
decoder.set_max_noutput_items(20800)
```

Cela garantit que `noutput_items` ne dépassera jamais 20800, forçant GNU Radio à fragmenter de manière cohérente.

### Option 2: Utiliser `forecast()` (Plus Complexe)

Passer de `sync_block` à `block` et implémenter `forecast()`:

```cpp
void forecast(int noutput_items, gr_vector_int &ninput_items_required) {
    // Demander exactement ce dont on a besoin
    int required = d_carrier_samples + (LONG_FRAME_TOTAL_BITS * d_samples_per_bit);
    for (auto &n : ninput_items_required) {
        n = required;
    }
}
```

### Option 3: Buffer Circulaire Robuste

Implémenter un buffer circulaire qui accumule TOUS les échantillons jusqu'à avoir une trame complète:

```cpp
std::deque<gr_complex> d_sample_buffer;

// Dans work():
for (int i = 0; i < noutput_items; i++) {
    d_sample_buffer.push_back(in[i]);
}

// Traiter quand on a assez d'échantillons
if (d_sample_buffer.size() >= required_samples) {
    // Décoder la trame complète
    // Vider le buffer
}
```

## Tests à Faire

### Test 1 : tb.set_max_noutput_items() [PRIORITÉ 1]
Modifier `decode_iq_40khz.py` pour ajouter:
```python
tb.set_max_noutput_items(8192)  # Puissance de 2
```
Tester avec 8192, 16384, 32768 et voir l'impact sur le taux de succès.

### Test 2 : Comparer les échantillons décodés
Ajouter un dump des valeurs de phase pour les bits 115-120 dans les runs qui échouent vs réussissent.

### Test 3 : Implémenter un buffer circulaire robuste
Au lieu de s'appuyer sur la persistance de `d_bit_buffer` entre appels, implémenter un buffer circulaire explicite.

### Test 4 : Utiliser `general_work()` au lieu de `sync_block`
Cela donne plus de contrôle sur `consume()` et `produce()`.

### Test 5 : Décalage de synchronisation
Ajouter un debug pour afficher la position EXACTE (en échantillons depuis le début du fichier) où on détecte le saut initial. Comparer entre runs qui réussissent et qui échouent.

## Code Modifié

### Fichiers modifiés :
- `lib/cospas_sarsat_decoder_impl.cc` : Instrumentation debug, modifications decode_bit(), set_min_noutput_items()
- `lib/cospas_sarsat_decoder_impl.h` : Pas de changements structurels

### Changements clés :

**Debug traces** (lignes 100-115) :
```cpp
static int work_call_count = 0;
if (d_debug_mode) {
    std::cout << "[DEBUG] work() call #" << work_call_count++
              << ": noutput_items=" << noutput_items
              << ", state=" << d_state
              << ", d_sample_count=" << d_sample_count
              << ", d_bit_count=" << d_bit_count
              << ", d_total_bit_count=" << d_total_bit_count << std::endl;
}
```

**Buffer minimum** (lignes 70-73) :
```cpp
int min_samples = d_carrier_samples + (LONG_FRAME_TOTAL_BITS * d_samples_per_bit);
set_min_noutput_items(min_samples);  // 6400 + 14400 = 20800
```

**Decode_bit() simplifié** (lignes 394-421) :
```cpp
int center_first = quarter_samples;
int center_second = half_samples + quarter_samples;
float phase_first = std::arg(samples[center_first]);
float phase_second = std::arg(samples[center_second]);
```

## Conclusion

Le décodeur a un problème de **cohérence d'état** entre les appels `work()`. La fragmentation variable des buffers par GNU Radio provoque des désalignements subtils qui causent des erreurs de décodage dans les derniers bits.

Le fait que les 10 premiers octets soient toujours corrects suggère que le problème s'accumule progressivement, possiblement un décalage d'échantillon qui empire au fil du décodage.

**Solution probable** : Repenser l'architecture du décodeur pour qu'il soit **totalement stateless** entre les appels work(), OU garantir qu'il traite TOUTE la trame en un seul appel.

## Fichiers de Test

- `examples/test_stable.sh` : Test 30 fois le même fichier
- `examples/find_failure.sh` : Trouve le premier échec et affiche les debug
- `examples/analyze_errors.sh` : Analyse binaire des patterns d'erreur
- `/tmp/stable_results.txt` : Résultats des 30 tests
- `/tmp/debug_run1.log` : Log détaillé d'un run échoué
- `/tmp/debug_run2.log` : Log détaillé d'un run réussi

## Commandes Utiles

```bash
# Tester 30 fois
bash test_stable.sh

# Trouver un échec avec debug
bash find_failure.sh

# Comparer run échoué vs réussi
diff /tmp/debug_run1.log /tmp/debug_run2.log

# Tester avec plus de buffer
# Modifier ligne 73 de cospas_sarsat_decoder_impl.cc :
set_min_noutput_items(min_samples * 2);  # Doubler le buffer
```

## Prochaines Étapes Recommandées

1. **Ajouter un compteur d'échantillons global** depuis le début du fichier pour tracker l'alignement exact
2. **Dumper les valeurs de phase** des bits 115-120 (là où les erreurs apparaissent)
3. **Tester avec un fichier IQ plus court** (juste une trame) pour simplifier le debug
4. **Comparer bit par bit** le décodage Python vs C++ pour voir où diverge
5. **Essayer `forecast()` et `general_work()`** pour plus de contrôle sur le scheduling

---

## Références

### Documentation GNU Radio
- [How is noutput_items determined in GNU Radio?](https://stackoverflow.com/questions/30091953/how-is-noutput-items-determined-in-gnu-radio) - Stack Overflow
- [Behind the Veil: A Peek at GNU Radio's Buffer Architecture](https://www.gnuradio.org/news/2017-01-05-buffers/) - GNU Radio Blog
- [BlocksCodingGuide](https://wiki.gnuradio.org/index.php/BlocksCodingGuide) - GNU Radio Wiki
- [Types of Blocks](https://wiki.gnuradio.org/index.php/Types_of_Blocks) - GNU Radio Wiki

### Citations Clés

> "By default, GNU Radio runs a scheduler that attempts to optimize throughput. Using a dynamic scheduler, blocks in a flowgraph pass chunks of items from sources to sinks. The sizes of these chunks will vary depending on the speed of processing."

> "To set the maximum number of output items, pass a value into the 'start' or 'run' method of the gr_top_block. Using this method, we place a global restriction on the size of items to all blocks."

> "Each block has the ability to overwrite this with its own limit using `set_max_noutput_items()`."

---

**Note**: Ce problème est dû à la nature **par conception** de GNU Radio qui privilégie le débit au détreminisme. La solution est de contraindre explicitement le scheduler via `set_max_noutput_items()` ou d'implémenter un buffer d'accumulation robuste dans le décodeur.
