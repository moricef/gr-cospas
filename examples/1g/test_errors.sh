#!/bin/bash
for i in {1..5}; do
  echo "=== Test $i ==="
  python3 decode_iq_40khz.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1 | grep -E "(Erreur bit|Octet [0-9]|Correspondance)" | head -5
  echo ""
done
