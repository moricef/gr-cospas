#!/usr/bin/env python3
"""
Extraire les 64 valeurs 'Out' depuis l'Appendix D
"""

# Valeurs Out extraites manuellement depuis Figure D-1 (lignes 1197-1927)
# État | Out
out_values_str = """
0   1
1   0
2   0
3   0
4   0
5   0
6   0
7   0
8   0
9   0
10  0
11  0
12  0
13  0
14  0
15  0
16  0
17  0
18  0
19  1
20  0
21  0
22  0
23  1
24  0
25  0
26  0
27  0
28  0
29  1
30  0
31  0
32  0
33  0
34  1
35  0
36  0
37  1
38  0
39  0
40  1
41  0
42  0
43  0
44  0
45  1
46  0
47  0
48  0
49  0
50  0
51  1
52  0
53  0
54  0
55  1
56  0
57  0
58  0
59  0
60  1
61  0
62  1
63  0
"""

# Parse
lines = [l.strip() for l in out_values_str.strip().split('\n') if l.strip()]
out_vals = []
for line in lines:
    parts = line.split()
    if len(parts) == 2:
        out_vals.append(int(parts[1]))

print(f"Extrait {len(out_vals)} valeurs Out")
print(f"\nValeurs Out: {''.join(str(v) for v in out_vals)}")

# Convertir en hex (4 groupes de 16 bits)
hex_values = []
for i in range(4):
    bits_16 = out_vals[i*16:(i+1)*16]
    val = sum(b << (15-j) for j, b in enumerate(bits_16))
    hex_values.append(f"{val:04X}")

print(f"\nHex: {' '.join(hex_values)}")
print(f"Attendu: 8000 0108 4212 84A1")

if hex_values == ["8000", "0108", "4212", "84A1"]:
    print("\n✓ Correspondance parfaite avec extraction manuelle !")
else:
    print("\n✗ Différence détectée")
    for i, (got, exp) in enumerate(zip(hex_values, ["8000", "0108", "4212", "84A1"])):
        print(f"  Groupe {i}: obtenu {got}, attendu {exp}")
