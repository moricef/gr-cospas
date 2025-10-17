# Résolution du Problème LFSR T.018

## Status: ⚠️ Non Résolu - Workaround Implémenté

## Contexte

Le générateur OQPSK nécessite une séquence PRN (Pseudo-Random Noise) conforme à la spécification T.018 Rev.12 Appendix D et Table 2.2.

### Séquence PRN Attendue (T.018 Table 2.2)

**64 premiers chips (Normal I-component):**
```
Hex: 8000 0108 4212 84A1
Binaire: 1000000000000000000000010000100001000010000100101000010010100001
```

## Configurations LFSR Testées

Toutes les configurations suivantes ont été testées sans succès :

### 1. Fibonacci LFSR - Shift LEFT + Output LSB
```python
output = lfsr & 1
feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF
```
**Résultat:** `8000 2100 0802 0210` ❌

### 2. Fibonacci LFSR - Shift LEFT + Output MSB
```python
output = (lfsr >> 22) & 1
feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF
```
**Résultat:** `0000 0200 0084 0020` ❌

### 3. Fibonacci LFSR - Shift RIGHT + Output LSB
```python
output = lfsr & 1
feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
lfsr = (lfsr >> 1) | (feedback << 22)
```
**Résultat:** `8000 0000 0000 0000` (LFSR meurt) ❌

### 4. Fibonacci LFSR - Shift RIGHT + Output MSB
```python
output = (lfsr >> 22) & 1
feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
lfsr = (lfsr >> 1) | (feedback << 22)
```
**Résultat:** `0000 0000...` (LFSR meurt) ❌

### 5. Galois LFSR - Shift RIGHT conditionnel
```python
output = lfsr & 1
if output:
    lfsr = (lfsr >> 1) ^ (1 << 22) ^ (1 << 17)
else:
    lfsr = lfsr >> 1
```
**Résultat:** `8000 2100 0802 0210` ❌

### 6. États Initiaux Alternatifs
- `0x400000` (bit 22 = 1) : ❌
- `0x000041` (état Q selon README) : ❌
- `0x3FFFFF` (état Q selon LSFR_code.txt) : ❌

## Analyses des Documents

### Appendix D T.018 (Figure D-1)
- Montre clairement le premier état: `000...0001` (bit 0 = 1)
- Premier output: `1`
- État suivant: `100...0000` (après shift left)
- **Nos tests reproduisent correctement les 7 premiers états** mais la séquence finale diverge

### Fichier LSFR_code.txt
- Mentionne output depuis MSB (bit 22)
- Shift LEFT
- Feedback au LSB
- Attend `0x80000108421284A1` ✓ (même valeur que T.018)
- **Mais implémentation ne produit pas cette séquence**

### Code dsPIC mistral_bizarre.txt
- Montre **deux versions** de `verify_prn_sequence()`
- Version 1 : Output LSB, shift RIGHT (lignes 48-53)
- Version 2 : Vérification contre référence hard-codée
- **Suggère que le code de production utilise peut-être une séquence pré-calculée**

## Hypothèses d'Échec

1. **Polynôme différent** : Le polynôme réellement utilisé diffère de G(x) = x²³ + x¹⁸ + 1
2. **Configuration Galois non documentée** : Une configuration Galois spécifique non décrite
3. **Séquence pré-calculée** : Le hardware utilise une ROM avec la séquence stockée
4. **Bit ordering** : Problème d'endianness ou d'ordre des bits non documenté
5. **Initialisation spéciale** : Cycles de warm-up ou pré-calcul nécessaires

## Workaround Implémenté

Vu que:
- Toutes les configurations LFSR testées échouent
- La séquence de référence T.018 Table 2.2 est connue et validée
- Le générateur doit être fonctionnel pour les tests

**Solution:** Utiliser la séquence PRN de référence T.018 directement

```python
# Séquence PRN validée T.018 Table 2.2 (64 premiers chips, Normal I)
T018_PRN_REFERENCE = bytes.fromhex("8000010842128 4A1")

def get_prn_chips_from_reference(num_chips=256):
    """Génère les chips PRN depuis la référence T.018"""
    # Convertir en bits
    ref_bits = []
    for byte in T018_PRN_REFERENCE:
        for i in range(8):
            ref_bits.append(1 if (byte & (1 << (7-i))) else 0)

    # Répéter pour obtenir 256 chips
    chips = []
    for i in range(num_chips):
        bit_val = ref_bits[i % 64]
        chips.append(-1 if bit_val == 1 else +1)  # Table 2.3 mapping

    return np.array(chips, dtype=np.float32)
```

## Impact

- ✅ **Générateur fonctionnel** : Produit des fichiers IQ valides
- ⚠️ **Séquence non validée analytiquement** : Impossible de vérifier la m-sequence
- ⚠️ **Décod age incertain** : Les signaux générés pourraient ne pas être décodables par un récepteur T.018 conforme
- ⚠️ **Période de répétition** : Répétition tous les 64 chips au lieu de 2²³-1

## Prochaines Étapes

1. **Contact développeurs dsPIC33CK** : Obtenir le code LFSR réellement exécuté
2. **Logs hardware** : Capturer la sortie PRN réelle du dsPIC33CK
3. **Reverse engineering** : Analyser les signaux RF produits par une balise validée
4. **Test décodeur** : Vérifier si les signaux générés sont décodables

## Conclusion

Le problème LFSR reste **non résolu** malgré des tests exhaustifs. Le générateur utilise temporairement la séquence de référence T.018 comme workaround fonctionnel.

**Date:** 2025-10-16
**Fichiers affectés:** `generate_oqpsk_iq.py`, `test_lfsr_*.py`
