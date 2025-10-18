#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI pour le décodeur COSPAS-SARSAT
Affiche les résultats de décodage dans une fenêtre Qt
"""

import sys
from PyQt5 import Qt, QtCore, QtWidgets
from gnuradio import gr, blocks
from gnuradio.cospas import cospas_sarsat_decoder
import time

class DecoderGUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle("Décodeur COSPAS-SARSAT 406 MHz")
        self.setMinimumSize(800, 600)

        # Widget central
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Titre
        title = QtWidgets.QLabel("🛰️ Décodeur COSPAS-SARSAT")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #2196F3;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Sélection fichier
        file_layout = QtWidgets.QHBoxLayout()
        self.file_path = QtWidgets.QLineEdit()
        self.file_path.setPlaceholderText("Chemin du fichier IQ...")
        self.file_path.setText("/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq")
        self.file_path.setStyleSheet("font-size: 14px; padding: 5px;")
        file_layout.addWidget(self.file_path)

        browse_btn = QtWidgets.QPushButton("📁 Parcourir")
        browse_btn.setStyleSheet("font-size: 14px; padding: 5px;")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Paramètres
        params_group = QtWidgets.QGroupBox("Paramètres")
        params_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        params_layout = QtWidgets.QFormLayout()
        params_layout.setLabelAlignment(QtCore.Qt.AlignRight)

        self.sample_rate = QtWidgets.QSpinBox()
        self.sample_rate.setRange(1000, 10000000)
        self.sample_rate.setValue(40000)
        self.sample_rate.setSuffix(" Hz")
        self.sample_rate.setStyleSheet("font-size: 14px; padding: 3px;")

        label_sr = QtWidgets.QLabel("Fréquence d'échantillonnage:")
        label_sr.setStyleSheet("font-size: 14px;")
        params_layout.addRow(label_sr, self.sample_rate)

        self.debug_mode = QtWidgets.QCheckBox()
        self.debug_mode.setChecked(False)
        self.debug_mode.setStyleSheet("font-size: 14px;")

        label_debug = QtWidgets.QLabel("Mode debug:")
        label_debug.setStyleSheet("font-size: 14px;")
        params_layout.addRow(label_debug, self.debug_mode)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Bouton décoder
        self.decode_btn = QtWidgets.QPushButton("▶️ DÉCODER")
        self.decode_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 22px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.decode_btn.clicked.connect(self.start_decode)
        layout.addWidget(self.decode_btn)

        # Barre de progression
        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Zone de résultats
        results_group = QtWidgets.QGroupBox("Résultats du décodage")
        results_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        results_layout = QtWidgets.QVBoxLayout()

        self.results_text = QtWidgets.QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 14px;
                background-color: #1e1e1e;
                color: #d4d4d4;
                line-height: 1.4;
            }
        """)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Barre de statut
        self.statusBar().showMessage("Prêt")

    def browse_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier IQ",
            "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/",
            "Fichiers IQ (*.iq);;Tous les fichiers (*)"
        )
        if filename:
            self.file_path.setText(filename)

    def log(self, text, color=None):
        """Ajoute du texte dans la zone de résultats"""
        if color:
            self.results_text.append(f'<span style="color: {color};">{text}</span>')
        else:
            self.results_text.append(text)
        self.results_text.ensureCursorVisible()
        QtWidgets.QApplication.processEvents()

    def start_decode(self):
        """Lance le décodage"""
        self.results_text.clear()
        self.decode_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Mode indéterminé
        self.statusBar().showMessage("Décodage en cours...")

        try:
            iq_file = self.file_path.text()
            sample_rate = self.sample_rate.value()
            debug_mode = self.debug_mode.isChecked()

            self.log("=" * 70, "#4CAF50")
            self.log("DÉCODAGE FICHIER I/Q COSPAS-SARSAT", "#4CAF50")
            self.log("=" * 70, "#4CAF50")
            self.log(f"Fichier: {iq_file.split('/')[-1]}")
            self.log(f"Fréquence: {sample_rate} Hz")
            self.log(f"Mode debug: {'Activé' if debug_mode else 'Désactivé'}")
            self.log("")

            # Créer le flowgraph
            self.log("🔧 Création du flowgraph GNU Radio...", "#2196F3")

            tb = gr.top_block()

            file_source = blocks.file_source(gr.sizeof_gr_complex, iq_file, False)
            decoder = cospas_sarsat_decoder(sample_rate=sample_rate, debug_mode=debug_mode)
            vector_sink = blocks.vector_sink_b()

            tb.connect(file_source, decoder, vector_sink)

            # Contraindre le buffer pour déterminisme
            tb.set_max_noutput_items(8192)

            self.log("✅ Flowgraph créé", "#4CAF50")
            self.log("")
            self.log("▶️ Démarrage du décodage...", "#2196F3")
            self.log("")

            # Exécuter
            tb.run()

            self.log("✅ Décodage terminé", "#4CAF50")
            self.log("")

            # Récupérer les données
            data = list(vector_sink.data())

            self.log("=" * 70, "#4CAF50")

            if len(data) > 0:
                self.log(f"✅ Données décodées: {len(data)} octets", "#4CAF50")
                self.log("")
                self.log("Données (hexadécimal):", "#FFF")

                # Afficher en format compact
                hex_str = "".join(f"{b:02X}" for b in data)
                self.log(f"  {hex_str}", "#FFD700")
                self.log("")

                # Afficher par octets
                self.log("Données détaillées:", "#FFF")
                for i in range(0, len(data), 8):
                    chunk = data[i:i+8]
                    hex_chunk = " ".join(f"{b:02X}" for b in chunk)
                    self.log(f"  Octets {i:3d}-{min(i+7, len(data)-1):3d}: {hex_chunk}", "#AAA")

                self.log("")

                # Comparer avec trames connues
                known_frames = {
                    "8E3301E2402B002BBA863609670908": "Trame longue #1",
                    "8E3301E240298056CF99F61503780B": "Trame longue #2",
                    "8E3E0425A52B002E364FF709674EB7": "Trame longue #3"
                }

                hex_data = "".join(f"{b:02X}" for b in data)

                for expected_hex, name in known_frames.items():
                    if hex_data == expected_hex:
                        self.log(f"✅ Trame identifiée: {name}", "#00FF00")
                        self.log(f"✅ Décodage validé (correspondance complète)", "#00FF00")
                        break
                    elif hex_data.startswith(expected_hex[:20]):
                        matches = sum(1 for i, c in enumerate(expected_hex) if i < len(hex_data)*2 and hex_data[i] == c) // 2
                        self.log(f"⚠️  Correspondance partielle avec {name}: {matches}/{len(expected_hex)//2} octets", "#FFA500")
                        break

                self.statusBar().showMessage(f"✅ Décodage réussi: {len(data)} octets", 5000)
            else:
                self.log("❌ Aucune donnée décodée", "#FF0000")
                self.log("")
                self.log("Suggestions:", "#FFA500")
                self.log("  - Vérifier que le fichier contient des données valides", "#AAA")
                self.log("  - Vérifier la fréquence d'échantillonnage", "#AAA")
                self.log("  - Activer le mode debug pour plus d'informations", "#AAA")
                self.statusBar().showMessage("❌ Aucune donnée décodée", 5000)

            self.log("=" * 70, "#4CAF50")

        except Exception as e:
            self.log(f"❌ ERREUR: {str(e)}", "#FF0000")
            self.log("")
            import traceback
            tb_str = traceback.format_exc()
            self.log(tb_str, "#FF6B6B")
            self.statusBar().showMessage(f"❌ Erreur: {str(e)}", 5000)

        finally:
            self.decode_btn.setEnabled(True)
            self.progress.setVisible(False)


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Style sombre
    app.setStyle("Fusion")
    palette = Qt.QPalette()
    palette.setColor(Qt.QPalette.Window, Qt.QColor(53, 53, 53))
    palette.setColor(Qt.QPalette.WindowText, Qt.Qt.white)
    palette.setColor(Qt.QPalette.Base, Qt.QColor(25, 25, 25))
    palette.setColor(Qt.QPalette.AlternateBase, Qt.QColor(53, 53, 53))
    palette.setColor(Qt.QPalette.ToolTipBase, Qt.Qt.white)
    palette.setColor(Qt.QPalette.ToolTipText, Qt.Qt.white)
    palette.setColor(Qt.QPalette.Text, Qt.Qt.white)
    palette.setColor(Qt.QPalette.Button, Qt.QColor(53, 53, 53))
    palette.setColor(Qt.QPalette.ButtonText, Qt.Qt.white)
    palette.setColor(Qt.QPalette.BrightText, Qt.Qt.red)
    palette.setColor(Qt.QPalette.Link, Qt.QColor(42, 130, 218))
    palette.setColor(Qt.QPalette.Highlight, Qt.QColor(42, 130, 218))
    palette.setColor(Qt.QPalette.HighlightedText, Qt.Qt.black)
    app.setPalette(palette)

    gui = DecoderGUI()
    gui.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
