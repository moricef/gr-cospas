#!/bin/bash
echo "Test de déterminisme - 20 exécutions"
echo "====================================="

for i in {1..20}; do
  output=$(python3 decode_iq_40khz.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1)
  hex=$(echo "$output" | grep -A 1 "Données (hex)" | tail -1 | xargs)
  parfait=$(echo "$output" | grep "DÉCODAGE PARFAIT" | wc -l)
  
  if [ "$parfait" -eq 1 ]; then
    echo "Test $i: ✅ PARFAIT - $hex"
  else
    echo "Test $i: ⚠️  IMPARFAIT - $hex"
  fi
done | tee /tmp/test_results.txt

echo ""
echo "Résumé:"
grep "✅ PARFAIT" /tmp/test_results.txt | wc -l | xargs echo "Parfaits:"
grep "⚠️  IMPARFAIT" /tmp/test_results.txt | wc -l | xargs echo "Imparfaits:"
