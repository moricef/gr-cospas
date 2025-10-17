#!/bin/bash
echo "Analyse des patterns d'erreur"
echo "=============================="

echo ""
echo "Pattern CORRECT attendu:"
echo "8E3301E2402B002BBA863609670908"

echo ""
echo "Patterns ERRONÉS observés:"
echo "1) 8E3301E2402B002BBA88471980F1   (15 fois)"
echo "2) 8E3301E2402B002BBA8636096709   (3 fois - 14 octets)"
echo "3) 8E3301E2402B002BBA84238CC07890 (1 fois)"

echo ""
echo "Comparaison binaire des octets 11-15:"
echo ""
echo "CORRECT: 86 36 09 67 09 08"
echo "Erreur1: 88 47 19 80 F1    (manque 2 octets)"
echo "Erreur2: 86 36 09 67 09    (manque 1 octet)"
echo "Erreur3: 84 23 8C C0 78 90 (6 octets au lieu de 6)"

echo ""
echo "Conversion en binaire des octets qui diffèrent:"
python3 << 'PYEOF'
def show_bits(name, hex_str):
    bytes_list = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
    print(f"\n{name}:")
    for i, b in enumerate(bytes_list[10:], 10):  # Octets 10+
        val = int(b, 16)
        binary = format(val, '08b')
        print(f"  Octet {i}: 0x{b} = {binary}")

show_bits("CORRECT", "8E3301E2402B002BBA863609670908")
show_bits("Erreur1", "8E3301E2402B002BBA88471980F100")
show_bits("Erreur2", "8E3301E2402B002BBA863609670900")
PYEOF

echo ""
echo "Hypothèse: Décalage de bits dans le buffer"
