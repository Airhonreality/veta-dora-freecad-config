# -*- coding: utf-8 -*-
"""
tests/test_vdo_chassis_widget.py

Suite de pruebas unitarias para VDOChassisControllerWidget (Capa 1).
Verifica:
  - Inicialización y contrato canónico de getChassisConfig() / setChassisConfig().
  - Ciclo de encuentros de esquina (tapa_domina -> lateral_domina -> inglete_45).
  - Conmutación de caras activas/ausentes (superior, inferior, izquierda, derecha, fondo).
  - Cambio de estrategias de base (zócalo, suspendido, patas) y parámetros numéricos.
  - Carga de arquetipos rápidos (COCO, Mesa, Estante, Aéreo).
  - Emisión reactiva de la señal sigChassisChanged.
"""

import unittest
import sys
import os

try:
    from PySide import QtCore, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtWidgets

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import VDO.ui.vdo_ui_chassis_widget as CW

# Asegurar QApplication para pruebas GUI en modo headless
_app = QtWidgets.QApplication.instance()
if not _app:
    _app = QtWidgets.QApplication(sys.argv)


class TestVDOChassisWidget(unittest.TestCase):

    def setUp(self):
        self.widget = CW.VDOChassisControllerWidget()
        self.widget.show()
        self.signal_payloads = []
        self.widget.sigChassisChanged.connect(lambda d: self.signal_payloads.append(d))

    def tearDown(self):
        self.widget.close()

    def test_default_config(self):
        cfg = self.widget.getChassisConfig()
        self.assertIn("caras", cfg)
        self.assertIn("encuentros", cfg)
        self.assertIn("base", cfg)

        # 5 caras presentes y activas por defecto
        for c in ("superior", "inferior", "izquierda", "derecha", "fondo"):
            self.assertIn(c, cfg["caras"])
            self.assertTrue(cfg["caras"][c]["activa"])

        # 4 encuentros
        for e in ("superior_izq", "superior_der", "inferior_izq", "inferior_der"):
            self.assertIn(e, cfg["encuentros"])

        # Base default
        self.assertEqual(cfg["base"]["estrategia"], "zocalo")
        self.assertEqual(cfg["base"]["altura"], 100.0)
        self.assertEqual(cfg["base"]["separacion_frente"], 50.0)

    def test_corner_cycling(self):
        # superior_izq inicia en tapa_domina
        self.assertEqual(self.widget.getChassisConfig()["encuentros"]["superior_izq"], "tapa_domina")

        # Clic 1 -> lateral_domina
        self.widget.btn_esquina["superior_izq"].click()
        self.assertEqual(self.widget.getChassisConfig()["encuentros"]["superior_izq"], "lateral_domina")
        self.assertGreater(len(self.signal_payloads), 0)

        # Clic 2 -> inglete_45
        self.widget.btn_esquina["superior_izq"].click()
        self.assertEqual(self.widget.getChassisConfig()["encuentros"]["superior_izq"], "inglete_45")

        # Clic 3 -> regresa a tapa_domina
        self.widget.btn_esquina["superior_izq"].click()
        self.assertEqual(self.widget.getChassisConfig()["encuentros"]["superior_izq"], "tapa_domina")

    def test_face_toggling(self):
        # Desactivar tapa superior
        self.assertTrue(self.widget.getChassisConfig()["caras"]["superior"]["activa"])
        self.widget.btn_cara_sup.click()
        self.assertFalse(self.widget.getChassisConfig()["caras"]["superior"]["activa"])
        self.assertIn("Ausente", self.widget.btn_cara_sup.text())

        # Reactivar tapa superior
        self.widget.btn_cara_sup.click()
        self.assertTrue(self.widget.getChassisConfig()["caras"]["superior"]["activa"])
        self.assertIn("Activa", self.widget.btn_cara_sup.text())

        # Desactivar base inferior
        self.widget.btn_cara_inf.click()
        self.assertFalse(self.widget.getChassisConfig()["caras"]["inferior"]["activa"])

    def test_fondo_selection(self):
        # Cambiar a abierto
        idx_abierto = self.widget.combo_fondo.findData("abierto")
        self.assertGreaterEqual(idx_abierto, 0)
        self.widget.combo_fondo.setCurrentIndex(idx_abierto)

        cfg = self.widget.getChassisConfig()
        self.assertEqual(cfg["caras"]["fondo"]["tipo"], "abierto")
        self.assertFalse(cfg["caras"]["fondo"]["activa"])

        # Cambiar a atornillado
        idx_atorn = self.widget.combo_fondo.findData("atornillado")
        self.widget.combo_fondo.setCurrentIndex(idx_atorn)
        cfg2 = self.widget.getChassisConfig()
        self.assertEqual(cfg2["caras"]["fondo"]["tipo"], "atornillado")
        self.assertTrue(cfg2["caras"]["fondo"]["activa"])

    def test_estrategia_base_switching(self):
        # Cambiar a suspendido
        self.widget.btn_estrategias["suspendido"].click()
        cfg = self.widget.getChassisConfig()
        self.assertEqual(cfg["base"]["estrategia"], "suspendido")

        # Modificar despegue
        self.widget.spin_despegue_piso.setValue(450.0)
        cfg = self.widget.getChassisConfig()
        self.assertEqual(cfg["base"]["altura"], 450.0)

        # Cambiar a patas
        self.widget.btn_estrategias["patas"].click()
        self.widget.spin_altura_patas.setValue(120.0)
        self.widget.spin_offset_patas.setValue(60.0)
        cfg = self.widget.getChassisConfig()
        self.assertEqual(cfg["base"]["estrategia"], "patas")
        self.assertEqual(cfg["base"]["altura"], 120.0)
        self.assertEqual(cfg["base"]["separacion_frente"], 60.0)

    def test_archetypes(self):
        # Arquetipo Mesa
        self.widget.btn_arquetipos["Mesa"].click()
        cfg = self.widget.getChassisConfig()
        self.assertTrue(cfg["caras"]["superior"]["activa"])
        self.assertFalse(cfg["caras"]["inferior"]["activa"])  # Mesa no tiene base
        self.assertEqual(cfg["caras"]["fondo"]["tipo"], "atornillado")

        # Arquetipo Estante
        self.widget.btn_arquetipos["Estante"].click()
        cfg = self.widget.getChassisConfig()
        self.assertFalse(cfg["caras"]["superior"]["activa"])  # Estante abierto arriba
        self.assertTrue(cfg["caras"]["inferior"]["activa"])
        self.assertEqual(cfg["caras"]["fondo"]["tipo"], "abierto")

        # Arquetipo COCO
        self.widget.btn_arquetipos["COCO"].click()
        cfg = self.widget.getChassisConfig()
        self.assertTrue(cfg["caras"]["superior"]["activa"])
        self.assertTrue(cfg["caras"]["inferior"]["activa"])
        self.assertTrue(cfg["caras"]["izquierda"]["activa"])
        self.assertTrue(cfg["caras"]["derecha"]["activa"])
        self.assertEqual(cfg["base"]["estrategia"], "zocalo")

    def test_set_chassis_config(self):
        custom_cfg = {
            "caras": {
                "superior": {"activa": True, "tipo": "estructural"},
                "inferior": {"activa": False, "tipo": "estructural"},
                "izquierda": {"activa": True, "tipo": "estructural"},
                "derecha": {"activa": True, "tipo": "estructural"},
                "fondo": {"activa": False, "tipo": "abierto"},
            },
            "encuentros": {
                "superior_izq": "inglete_45",
                "superior_der": "inglete_45",
                "inferior_izq": "lateral_domina",
                "inferior_der": "lateral_domina",
            },
            "base": {
                "estrategia": "suspendido",
                "altura": 250.0,
                "separacion_frente": 0.0,
            }
        }
        self.signal_payloads.clear()
        self.widget.setChassisConfig(custom_cfg)

        # No debe emitir señales durante setChassisConfig
        self.assertEqual(len(self.signal_payloads), 0)

        # Lectura debe coincidir
        leido = self.widget.getChassisConfig()
        self.assertEqual(leido["encuentros"]["superior_izq"], "inglete_45")
        self.assertEqual(leido["encuentros"]["superior_der"], "inglete_45")
        self.assertFalse(leido["caras"]["inferior"]["activa"])
        self.assertEqual(leido["caras"]["fondo"]["tipo"], "abierto")
        self.assertEqual(leido["base"]["estrategia"], "suspendido")
        self.assertEqual(leido["base"]["altura"], 250.0)


if __name__ == "__main__":
    unittest.main()
