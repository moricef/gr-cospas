#!/bin/bash
for i in {1..10}; do
  echo -n "Test $i: "
  python3 decode_iq_matlab_direct.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1 | grep "hex:" | awk '{print $2}'
done
