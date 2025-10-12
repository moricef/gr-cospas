#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser de trames COSPAS-SARSAT
Décode les champs selon le protocole
"""

def parse_cospas_frame(data_bytes):
    """
    Parse une trame COSPAS-SARSAT décodée

    Args:
        data_bytes: bytes décodés (sans préambule ni frame sync)

    Returns:
        dict avec les champs décodés
    """

    if len(data_bytes) < 10:
        return {"error": "Trame trop courte"}

    # Convertir en bits
    bits = []
    for byte in data_bytes:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    result = {}

    # Bit 0 (bit 25 de la trame complète) = Format Flag
    result['format_flag'] = bits[0]
    result['frame_type'] = "LONGUE (144 bits)" if bits[0] == 1 else "COURTE (112 bits)"

    # Bits 1-10 (26-36): Country Code (10 bits)
    country_code = 0
    for i in range(1, 11):
        country_code = (country_code << 1) | bits[i]
    result['country_code'] = country_code
    result['country_code_hex'] = f"0x{country_code:03X}"

    # Pays selon le code (exemples)
    country_names = {
        0x1C7: "France",
        0x1F4: "USA",
        0x1D1: "UK",
        0x1BE: "Germany",
        # etc.
    }
    result['country_name'] = country_names.get(country_code, "Inconnu")

    # Bits 11-36 (37-62): Beacon ID (26 bits)
    beacon_id = 0
    for i in range(11, 37):
        if i < len(bits):
            beacon_id = (beacon_id << 1) | bits[i]
    result['beacon_id'] = beacon_id
    result['beacon_id_hex'] = f"0x{beacon_id:07X}"

    # Pour les trames longues, il y a des données supplémentaires
    if bits[0] == 1 and len(data_bytes) >= 15:
        # Bits 37-85 (protocole location)
        # Simplifié ici - le vrai décodage dépend du type de protocole
        result['has_location'] = True

        # Octets 5-14 contiennent position, altitude, etc.
        result['location_data_hex'] = data_bytes[5:15].hex().upper()
    else:
        result['has_location'] = False

    # Données brutes
    result['raw_hex'] = data_bytes.hex().upper()
    result['raw_bytes'] = len(data_bytes)

    return result


def print_frame_info(data_bytes):
    """Affiche les informations de la trame de façon lisible"""

    info = parse_cospas_frame(data_bytes)

    print("="*70)
    print("TRAME COSPAS-SARSAT DÉCODÉE")
    print("="*70)

    if 'error' in info:
        print(f"❌ Erreur: {info['error']}")
        return

    print(f"\n📡 TYPE DE TRAME: {info['frame_type']}")
    print(f"   Format flag: {info['format_flag']}")

    print(f"\n🌍 PAYS:")
    print(f"   Code: {info['country_code_hex']} ({info['country_code']})")
    print(f"   Nom: {info['country_name']}")

    print(f"\n🔖 IDENTIFICATION BALISE:")
    print(f"   Beacon ID: {info['beacon_id_hex']}")
    print(f"   Decimal: {info['beacon_id']}")

    if info['has_location']:
        print(f"\n📍 DONNÉES DE LOCALISATION:")
        print(f"   Données: {info['location_data_hex']}")
        print(f"   (Décodage détaillé non implémenté)")

    print(f"\n💾 DONNÉES BRUTES:")
    print(f"   Octets: {info['raw_bytes']}")
    print(f"   Hex: {info['raw_hex']}")

    print("\n" + "="*70)


def main():
    import sys

    if len(sys.argv) < 2:
        # Trame de test
        test_hex = "8E3301E2402B002BBA863609670908"
        print(f"Usage: {sys.argv[0]} <fichier.bin|hex_string>")
        print(f"Utilisation de la trame de test: {test_hex}\n")
        data = bytes.fromhex(test_hex)
    else:
        arg = sys.argv[1]

        # Vérifier si c'est un fichier ou une chaîne hex
        try:
            import os
            if os.path.isfile(arg):
                # C'est un fichier
                with open(arg, 'rb') as f:
                    data = f.read()
                print(f"Lecture du fichier: {arg}\n")
            else:
                # C'est une chaîne hex
                data = bytes.fromhex(arg)
        except Exception as e:
            print(f"❌ Erreur de lecture: {e}")
            return

    print_frame_info(data)

    # Afficher aussi le dictionnaire complet
    print("\nDétails (format dict):")
    info = parse_cospas_frame(data)
    for key, value in info.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
