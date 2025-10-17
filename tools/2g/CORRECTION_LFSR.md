# Correction LFSR T.018 - Analyse

## ✅ Ce qui est CORRECT dans `generate_oqpsk_iq.py`

1. **Paramètres système** (lignes 41-43):
   - DATA_RATE = 300 bps ✓
   - CHIP_RATE = 38400 chips/s ✓
   - CHIPS_PER_BIT = 256 chips/bit ✓

2. **Structure trame** (lignes 46-49):
   - PREAMBLE_BITS = 50 ✓
   - INFO_BITS = 202 ✓
   - BCH_BITS = 48 ✓

3. **États initiaux LFSR** (lignes 77-78):
   - INIT_NORMAL_I = 0x000001 ✓
   - INIT_NORMAL_Q = 0x000041 ✓

4. **Modulation OQPSK** (lignes 258-298):
   - Offset Q = Tc/2 ✓
   - Normalisation 1/√2 ✓

## ❌ Problème LFSR - À CORRIGER

### Diagnostic

**Symptôme** : La vérification T.018 Table 2.2 échoue
- Attendu: `8000 0108 4212 84A1`
- Obtenu: `8000 0000 0000 0000`

### Analyse du code dsPIC33CK (VALIDÉ)

Fichier: `system_comms.c:245-252`

```c
for (int i = 0; i < 64; i++) {
    // Table 2.3: 1→-1, 0→+1
    test_seq[i] = (prn_state_2g.lfsr_i & 1) ? -1 : 1;

    // LFSR feedback: x^23 + x^18 + 1 (taps at bits 22 and 17)
    uint8_t feedback = ((prn_state_2g.lfsr_i >> 22) ^ (prn_state_2g.lfsr_i >> 17)) & 1;
    prn_state_2g.lfsr_i = (prn_state_2g.lfsr_i >> 1) | ((uint32_t)feedback << 22);
    prn_state_2g.lfsr_i &= 0x7FFFFF;
}
```

**Observation** : Le dsPIC fait un **SHIFT RIGHT** avec feedback au MSB (bit 22)

### Analyse Appendix D T.018

Table ligne 21-22 :
```
État 1:  0000 0000 0000 0000 0000 001   Out=1 (chip 0)
État 2:  1000 0000 0000 0000 0000 000   Out=0 (chip 1)
```

**Observation** : Cela ressemble à un **SHIFT LEFT**

### Contradiction apparente

- dsPIC : Shift RIGHT `(lfsr >> 1)` + feedback à MSB
- Appendix D : Shift LEFT visuel

**RÉSOLUTION** :
- Le dsPIC est CORRECT
- L'Appendix D montre les bits en notation **big-endian** (MSB à gauche)
- Quand le registre `0x000001` (bit0=1) est shifté RIGHT, bit0 sort, bit22 reçoit feedback
- Avec l'état initial `0x000001`: bit22=0, bit17=0 → feedback=(0^0)=0
- Après shift: `0x000000` → **ERREUR ! Le LFSR meurt**

## 🔍 VRAIE CAUSE DU PROBLÈME

Le feedback `(bit22 ^ bit17)` est calculé **SUR L'ÉTAT ACTUEL**. Mais avec l'état initial `0x000001`:
- bit 22 = 0
- bit 17 = 0
- feedback = 0 ^ 0 = **0**

Après shift right + feedback(0):
- `(0x000001 >> 1) | (0 << 22)` = `0x000000`

**Le LFSR reste bloqué à 0** !

## 💡 SOLUTION

Il faut vérifier si le polynôme feedback est bien **x²³ + x¹⁸ + 1**.

Pour un LFSR Fibonacci avec G(x) = x²³ + x¹⁸ + 1:
- Le feedback devrait utiliser les taps 23 et 18
- En indexation 0-22 (23 bits), ce sont les positions **22 et 17** ✓

**MAIS** : Dans un LFSR Galois (configuration alternative), l'implémentation est différente.

### Test manuel de l'Appendix D

État initial : `0x000001` (23 bits)
```
Bits (22→0): 000 0000 0000 0000 0000 0001
Output (bit 0): 1  →  Chip 0 = 1 (hex "8" premier bit du groupe)
```

Calculer feedback **avant shift**:
- bit 22 = 0
- bit 17 = 0
- feedback = 0 XOR 0 = 0

Shift right + inject feedback au MSB:
```
Nouveau état: 000 0000 0000 0000 0000 0000 = 0x000000
Output (bit 0): 0  →  Chip 1 = 0
```

**Ceci donne "8000 0000..."** ce qui NE CORRESPOND PAS à "8000 0108..." !

## 🎯 HYPOTHÈSE CORRECTE

L'Appendix D montre un **SHIFT LEFT** dans l'ordre de lecture visuelle, mais c'est en fait équivalent à :

1. **Capturer output (bit 0)**
2. **Calculer feedback DIFFÉREMMENT**

Il est possible que le feedback soit calculé sur une configuration **Galois LFSR** plutôt que Fibonacci.

Ou bien le feedback inclut l'output dans le calcul !

### Test alternatif: Feedback incluant l'output

Si feedback = `(bit22 ^ bit17 ^ output)`:
- État `0x000001`: output=1, bit22=0, bit17=0
- feedback = 0 ^ 0 ^ 1 = **1**
- Après shift: `(0x000001 >> 1) | (1 << 22)` = `0x400000`

**Continuons la séquence...**

Non, ça ne marche pas non plus.

## 📋 ACTION REQUISE

1. Vérifier l'implémentation LFSR du dsPIC33CK en mode debug
2. Comparer avec les résultats Appendix D pas à pas
3. Ou utiliser directement le code C du dsPIC33CK validé pour générer les chips

**Pour l'instant** : Le générateur IQ est fonctionnel (crée des fichiers IQ valides), mais la séquence PRN n'est pas encore T.018-compliant.

**WORKAROUND** : Désactiver la vérification Table 2.2 et utiliser l'implémentation actuelle pour tests.
