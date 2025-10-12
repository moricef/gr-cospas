#!/bin/bash
# Find first failure and save debug output

EXPECTED="8E3301E2402B002BBA863609670908"

for i in {1..20}; do
  result=$(python3 decode_iq_40khz.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1 | grep "Données (hex)" -A 1 | tail -1 | xargs)

  if [ "$result" != "$EXPECTED" ]; then
    echo "ÉCHEC trouvé à iteration $i"
    echo "Résultat: $result"
    echo ""
    echo "Détails du décodage:"
    python3 decode_iq_40khz.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1 | grep -E "(DEBUG work|BIT INDÉTERMINÉ|Trame complète)"
    exit 0
  else
    echo "Test $i: OK"
  fi
done

echo "Tous les tests ont réussi"
