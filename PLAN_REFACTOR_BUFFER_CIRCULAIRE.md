# Plan de Refactorisation: Buffer Circulaire pour Décodeur COSPAS-SARSAT

**Date**: 2025-10-12
**Objectif**: Atteindre 100% de déterminisme en utilisant un buffer d'accumulation

## Problème Actuel

Le décodeur utilise une machine à états qui traite les échantillons au fur et à mesure qu'ils arrivent via `work()`. Cette approche est sensible aux fragmentations du scheduler et aux conditions de frontière.

**Taux de succès actuel**: 47-63% selon la taille du buffer

## Solution: Buffer Circulaire d'Accumulation

### Principe

Au lieu de traiter immédiatement les échantillons, **accumuler TOUS les échantillons** dans un buffer jusqu'à avoir assez pour décoder une trame complète.

```
[File Source] → [Accumulation Buffer] → [Décodage Complet] → [Output]
```

### Architecture Proposée

```cpp
class cospas_sarsat_decoder_impl {
private:
    // Buffer d'accumulation
    std::deque<gr_complex> d_sample_accumulator;

    // Seuil de déclenchement
    static constexpr int MIN_SAMPLES_FOR_FRAME = 20800;  // 6400 + 14400

    // État de traitement
    bool d_frame_in_progress;
    int d_frames_processed;
};
```

### Algorithme work()

```cpp
int work(int noutput_items,
         gr_vector_const_void_star &input_items,
         gr_vector_void_star &output_items)
{
    const gr_complex *in = (const gr_complex *) input_items[0];
    uint8_t *out = (uint8_t *) output_items[0];

    // ÉTAPE 1: Accumuler TOUS les échantillons entrants
    for (int i = 0; i < noutput_items; i++) {
        d_sample_accumulator.push_back(in[i]);
    }

    int bytes_produced = 0;

    // ÉTAPE 2: Décoder si on a assez d'échantillons
    while (d_sample_accumulator.size() >= MIN_SAMPLES_FOR_FRAME) {

        // Décoder UNE trame complète
        std::vector<uint8_t> frame_bytes;
        bool success = decode_complete_frame(d_sample_accumulator, frame_bytes);

        if (success) {
            // Copier les octets décodés
            for (uint8_t byte : frame_bytes) {
                out[bytes_produced++] = byte;
            }

            // Consommer les échantillons utilisés
            d_sample_accumulator.erase(
                d_sample_accumulator.begin(),
                d_sample_accumulator.begin() + samples_consumed
            );
        } else {
            // Échec: avancer d'un échantillon et réessayer
            d_sample_accumulator.pop_front();
        }
    }

    consume_each(noutput_items);
    return bytes_produced;
}
```

### Fonction decode_complete_frame()

```cpp
bool decode_complete_frame(const std::deque<gr_complex>& samples,
                           std::vector<uint8_t>& output_bytes)
{
    // 1. Chercher la porteuse (160 ms = 6400 échantillons)
    int carrier_start = find_carrier(samples, 0);
    if (carrier_start < 0) return false;

    int data_start = carrier_start + d_carrier_samples;

    // 2. Détecter le saut de phase initial
    int jump_pos = find_initial_jump(samples, data_start);
    if (jump_pos < 0) return false;

    // 3. Décoder le préambule (15 bits '1')
    int preamble_ones = 0;
    int bit_pos = jump_pos;

    for (int i = 0; i < PREAMBLE_BITS; i++) {
        char bit = decode_bit_at(samples, bit_pos);
        if (bit != '1') return false;  // Échec si pas '1'
        bit_pos += d_samples_per_bit;
        preamble_ones++;
    }

    // 4. Décoder le frame sync (9 bits)
    uint16_t frame_sync_pattern = 0;
    for (int i = 0; i < FRAME_SYNC_BITS; i++) {
        char bit = decode_bit_at(samples, bit_pos);
        if (bit == '?') return false;
        frame_sync_pattern = (frame_sync_pattern << 1) | (bit == '1' ? 1 : 0);
        bit_pos += d_samples_per_bit;
    }

    // Vérifier le frame sync
    if (frame_sync_pattern != FRAME_SYNC_NORMAL &&
        frame_sync_pattern != FRAME_SYNC_TEST) {
        return false;
    }

    // 5. Décoder le message (120 ou 88 bits)
    char format_bit = decode_bit_at(samples, bit_pos);
    bool is_long = (format_bit == '1');
    int msg_bits = is_long ? LONG_MESSAGE_BITS : SHORT_MESSAGE_BITS;

    std::vector<uint8_t> message_bits;
    for (int i = 0; i < msg_bits; i++) {
        char bit = decode_bit_at(samples, bit_pos);
        if (bit == '?') return false;  // Pas de bits indéterminés acceptés!
        message_bits.push_back(bit == '1' ? 1 : 0);
        bit_pos += d_samples_per_bit;
    }

    // 6. Convertir en octets
    for (size_t i = 0; i < message_bits.size(); i += 8) {
        uint8_t byte = 0;
        for (int j = 0; j < 8 && (i + j) < message_bits.size(); j++) {
            byte = (byte << 1) | message_bits[i + j];
        }
        output_bytes.push_back(byte);
    }

    // Indiquer combien d'échantillons ont été consommés
    samples_consumed = bit_pos;

    return true;
}
```

### Fonction decode_bit_at()

```cpp
char decode_bit_at(const std::deque<gr_complex>& samples, int start_pos)
{
    if (start_pos + d_samples_per_bit > samples.size()) {
        return '?';  // Pas assez d'échantillons
    }

    // Échantillon au centre de chaque moitié (comme Python!)
    int half = d_samples_per_bit / 2;
    int quarter = half / 2;

    int center_first = start_pos + quarter;
    int center_second = start_pos + half + quarter;

    float phase_first = std::arg(samples[center_first]);
    float phase_second = std::arg(samples[center_second]);
    float phase_diff = compute_phase_diff(phase_first, phase_second);

    if (phase_diff < -0.5f) return '1';
    else if (phase_diff > 0.5f) return '0';
    else return '?';
}
```

## Avantages de cette Approche

1. **✅ Déterministe**: Traite TOUJOURS les mêmes échantillons de la même façon
2. **✅ Indépendant de la fragmentation**: Accumule d'abord, décode ensuite
3. **✅ Robuste aux erreurs**: Si le décodage échoue, avance d'un échantillon et réessaye
4. **✅ Alignement garanti**: Cherche activement la porteuse et le saut initial
5. **✅ Pas de conditions de frontière**: Plus de problèmes de `d_sample_count` entre appels

## Inconvénients

1. **Latence**: Attend d'avoir 20800 échantillons (0.52 seconde à 40 kHz)
2. **Mémoire**: Buffer peut grandir si le décodage est lent
3. **Complexité**: Code plus long mais plus clair

## Plan d'Implémentation

### Phase 1: Créer une nouvelle branche
```bash
cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas
git checkout -b refactor-buffer-circulaire
```

### Phase 2: Modifier le header
- Ajouter `std::deque<gr_complex> d_sample_accumulator;`
- Ajouter méthodes privées: `decode_complete_frame()`, `decode_bit_at()`, `find_carrier()`, `find_initial_jump()`

### Phase 3: Réécrire work()
- Supprimer la machine à états
- Implémenter l'accumulation
- Appeler `decode_complete_frame()` quand assez d'échantillons

### Phase 4: Implémenter les fonctions helper
- `decode_complete_frame()`
- `decode_bit_at()`
- `find_carrier()`
- `find_initial_jump()`

### Phase 5: Tester
```bash
bash test_stable.sh
# Objectif: 100% de succès (30/30)
```

### Phase 6: Comparer les performances
- Taux de succès
- Latence
- Utilisation mémoire

## Estimation

- **Temps d'implémentation**: 2-3 heures
- **Risque**: Faible (on garde l'ancienne version dans git)
- **Gain attendu**: 100% de déterminisme

## Alternative Plus Simple

Si le refactoring complet est trop long, une approche intermédiaire:

```cpp
int work(...) {
    // Accumuler jusqu'à avoir UNE trame complète
    for (int i = 0; i < noutput_items; i++) {
        d_buffer.push_back(in[i]);
    }

    // Si on n'a pas encore assez, attendre
    if (d_buffer.size() < 20800) {
        consume_each(noutput_items);
        return 0;  // Pas de sortie pour l'instant
    }

    // On a assez: utiliser la machine à états EXISTANTE
    // mais sur le buffer accumulé
    int bytes_produced = process_accumulated_buffer();

    consume_each(noutput_items);
    return bytes_produced;
}
```

Cette approche réutilise la machine à états existante mais garantit qu'elle traite toujours un buffer complet.

---

**Recommandation**: Commencer par l'**approche intermédiaire** pour valider le concept, puis faire le refactoring complet si ça fonctionne.
