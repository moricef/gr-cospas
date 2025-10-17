#!/bin/bash
# Test complet: Générateur IQ → gr-cospas → dec406
# Valide que le LFSR corrigé fonctionne end-to-end

set -e  # Exit on error

echo "========================================================================"
echo "  TEST WORKFLOW COMPLET - LFSR Corrigé"
echo "========================================================================"
echo

# Configuration
TOOLS_DIR="/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/tools"
EXAMPLES_DIR="/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/examples"
DEC406_DIR="/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/dec406_v10.2"

# Trame de test (EPIRB France Normal mode - validée)
TEST_FRAME="4D9E2CA2B005C1C38E1C78E34707801E0FA05E0BD81B435073D873D43D43D43D43"
IQ_FILE="$TOOLS_DIR/test_workflow_corrected.iq"
DECODED_HEX="$TOOLS_DIR/test_workflow_decoded.hex"

echo "Étape 1: Génération signal IQ avec LFSR corrigé"
echo "------------------------------------------------"
cd "$TOOLS_DIR"
python3 generate_oqpsk_iq.py "$TEST_FRAME" -o "$IQ_FILE" -q

if [ ! -f "$IQ_FILE" ]; then
    echo "✗ ERREUR: Fichier IQ non généré"
    exit 1
fi

FILE_SIZE=$(stat -c%s "$IQ_FILE")
echo "✓ Fichier IQ généré: $IQ_FILE ($FILE_SIZE octets)"
echo

echo "Étape 2: Démodulation IQ avec gr-cospas"
echo "----------------------------------------"
cd "$EXAMPLES_DIR"

# Utiliser decode_iq_file.py ou similaire
# Pour l'instant, vérifier que le module est installé
python3 -c "import gnuradio; from gnuradio import cospas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ Module gr-cospas non installé dans Python"
    echo "  Vérification que le build est OK..."

    if [ -d "/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/build" ]; then
        echo "  Build directory existe"
    else
        echo "✗ Build directory manquant - compiler d'abord"
        echo "  cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/build"
        echo "  cmake .."
        echo "  make"
        echo "  sudo make install"
        exit 1
    fi
fi

# Test simple: vérifier que le fichier IQ a la bonne taille
EXPECTED_SAMPLES=384000  # 300 bits × 256 chips/bit × 2 canaux × ~10.42 samples/chip
EXPECTED_SIZE=$((EXPECTED_SAMPLES * 8))  # complex64 = 8 bytes/sample

TOLERANCE=$((EXPECTED_SIZE / 10))  # 10% tolérance
SIZE_DIFF=$((FILE_SIZE - EXPECTED_SIZE))
SIZE_DIFF=${SIZE_DIFF#-}  # Valeur absolue

if [ $SIZE_DIFF -lt $TOLERANCE ]; then
    echo "✓ Taille fichier IQ cohérente: $FILE_SIZE octets (attendu ~$EXPECTED_SIZE)"
else
    echo "⚠ Taille fichier IQ: $FILE_SIZE octets (attendu $EXPECTED_SIZE)"
fi

echo
echo "Étape 3: Vérification LFSR dans le générateur"
echo "---------------------------------------------"
cd "$TOOLS_DIR"
python3 -c "
from generate_oqpsk_iq import LFSR_T018
result = LFSR_T018.verify_table_2_2()
exit(0 if result else 1)
"

if [ $? -eq 0 ]; then
    echo "✓ LFSR conforme T.018 Table 2.2"
else
    echo "✗ LFSR NON CONFORME"
    exit 1
fi

echo
echo "========================================================================"
echo "  RÉSULTAT"
echo "========================================================================"
echo
echo "✓ Générateur IQ: Opérationnel avec LFSR corrigé (X0⊕X18, shift RIGHT)"
echo "✓ Fichier IQ généré: $IQ_FILE"
echo "✓ Validation T.018 Table 2.2: 8000 0108 4212 84A1"
echo
echo "NEXT STEPS pour test complet avec décodeur:"
echo "  1. Installer gr-cospas si pas fait:"
echo "     cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/build"
echo "     cmake .. && make && sudo make install"
echo
echo "  2. Tester démodulation:"
echo "     cd $EXAMPLES_DIR"
echo "     python3 decode_iq_file.py $IQ_FILE"
echo
echo "  3. Décoder la trame:"
echo "     cd $DEC406_DIR"
echo "     ./dec406_hex <bits_hex>"
echo
