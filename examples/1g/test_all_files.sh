#!/bin/bash
# Test tous les fichiers IQ disponibles

EXPECTED1="8E3301E2402B002BBA863609670908"
EXPECTED2="8E3301E240298056CF99F61503780B"

echo "======================================================================"
echo "TEST DE RÉPÉTABILITÉ - TOUS LES FICHIERS IQ"
echo "======================================================================"
echo ""

# Fichier 1 - petit (326 KB)
echo "=== FICHIER 1: beacon_signal_406mhz_long_msg_144bit.iq ==="
FILE1="/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"
success1=0
for i in {1..10}; do
    result=$(python3 decode_iq_40khz.py "$FILE1" 2>&1 | grep "Données (hex)" -A1 | tail -1 | xargs)
    if [ "$result" = "$EXPECTED1" ]; then
        echo "  Test $i: ✅"
        ((success1++))
    else
        echo "  Test $i: ❌ $result"
    fi
done
echo "  Résultat: $success1/10 réussis"
echo ""

# Fichier 2 - gros (160 MB)
echo "=== FICHIER 2: beacon_signal_406mhz_long_msg_144bit_2.iq ==="
FILE2="/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit_2.iq"
success2=0
for i in {1..5}; do
    result=$(python3 decode_iq_40khz.py "$FILE2" 2>&1 | grep "Données (hex)" -A1 | tail -1 | xargs)
    if [ "$result" = "$EXPECTED2" ]; then
        echo "  Test $i: ✅"
        ((success2++))
    else
        echo "  Test $i: ❌ $result"
    fi
done
echo "  Résultat: $success2/5 réussis"
echo ""

echo "======================================================================"
echo "RÉSUMÉ GLOBAL"
echo "======================================================================"
total_tests=$((10 + 5))
total_success=$((success1 + success2))
echo "Total: $total_success/$total_tests tests réussis"

if [ $total_success -eq $total_tests ]; then
    echo "🎉 TOUS LES TESTS RÉUSSIS - 100% DE DÉTERMINISME!"
else
    percent=$(( (total_success * 100) / total_tests ))
    echo "⚠️  Taux de réussite: ${percent}%"
fi
