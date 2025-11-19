#!/usr/bin/env python3
"""
Analyse les logs de démodulation et affiche les stats OK vs KO
Usage: python3 analyze_logs.py logs_real.log
"""
import sys
import re

if len(sys.argv) < 2:
    print("Usage: python3 analyze_logs.py <log_file>")
    sys.exit(1)

log_file = sys.argv[1]

with open(log_file, 'r') as f:
    content = f.read()

# Extraire toutes les paires REF/DEMOD
refs = re.findall(r'\[REF FR HEX\]: ([0-9A-F]+)', content)
demods = re.findall(r'\[COSPAS\] HEX: ([0-9A-F]+)', content)

if len(demods) == 0:
    print("Aucune trame démodulée trouvée dans le fichier")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"ANALYSE DEMODULATION")
print(f"{'='*60}")

ok_count = sum(1 for r, d in zip(refs, demods) if r == d)
error_count = len(demods) - ok_count
success_rate = 100 * ok_count / len(demods)

print(f"Total trames:  {len(demods)}")
print(f"Trames OK:     {ok_count} ({success_rate:.1f}%)")
print(f"Trames KO:     {error_count} ({100-success_rate:.1f}%)")
print(f"{'='*60}")
