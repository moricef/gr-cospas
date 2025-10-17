#!/bin/bash
echo "Test version STABLE - 30 exécutions"
echo "====================================="

for i in {1..30}; do
  output=$(python3 decode_iq_40khz.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1)
  hex=$(echo "$output" | grep -A 1 "Données (hex)" | tail -1 | xargs)
  parfait=$(echo "$output" | grep "DÉCODAGE PARFAIT" | wc -l)
  
  if [ "$parfait" -eq 1 ]; then
    echo "Test $i: ✅ PARFAIT"
  else
    echo "Test $i: ⚠️  $hex"
  fi
done | tee /tmp/stable_results.txt

echo ""
echo "RÉSUMÉ:"
grep "✅ PARFAIT" /tmp/stable_results.txt | wc -l | xargs echo "Réussites:"
grep "⚠️" /tmp/stable_results.txt | wc -l | xargs echo "Échecs:"

# Vérifier l'unicité des résultats
echo ""
echo "DÉTERMINISME:"
grep "⚠️" /tmp/stable_results.txt | cut -d' ' -f3- | sort | uniq -c | sort -rn
