for i in {1..10}; do
  result=$(python3 decode_iq_matlab_direct.py /home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq 2>&1 | grep "^Hex:" | cut -d' ' -f2)
  echo "$result"
done | sort | uniq -c
