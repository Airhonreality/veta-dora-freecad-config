# -*- coding: utf-8 -*-
# =====================================================================
# vdo_nesting_workflow.py
# Workflow automatizado: Selección → Nesting → Visualización
# =====================================================================

import sys
import os
from pathlib import Path

# Bootstrap
_vdo_macro_dir = os.path.dirname(os.path.abspath(__file__))
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import FreeCAD
import FreeCADGui
from PySide2 import QtWidgets, QtCore

try:
    from freecad.nestingworkbench.Tools.Nesting.nesting_logic import nest
    from freecad.nestingworkbench.Tools.Nesting.shape_preparer import ShapePreparer
except ImportError:
    FreeCAD.Console.PrintError("[VDO Nesting] ERROR: Nesting Workbench no instalado\n")
    FreeCAD.Console.PrintError("             Instala desde: Tools → Addon Manager\n")
    sys.exit(1)

import vdo_nesting_presets as presets_mgr


class NestingDialog(QtWidgets.QDialog):
    """Diálogo para configurar y ejecutar nesting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔲 VDO - Optimizador de Corte (Nesting)")
        self.setMinimumWidth(500)

        self.selected_parts = []
        self.mode = "todo"  # seleccion, grupo, todo

        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz."""
        layout = QtWidgets.QVBoxLayout()

        # === MODO DE SELECCIÓN ===
        group_mode = QtWidgets.QGroupBox("1️⃣ Modo de Selección")
        mode_layout = QtWidgets.QVBoxLayout()

        self.radio_todo = QtWidgets.QRadioButton("📋 TODOS los paneles del documento")
        self.radio_seleccion = QtWidgets.QRadioButton("✋ SELECCIÓN (objetos marcados)")
        self.radio_grupo = QtWidgets.QRadioButton("📦 GRUPO/MÓDULO activo (ej: COCO)")

        self.radio_todo.setChecked(True)

        mode_layout.addWidget(self.radio_todo)
        mode_layout.addWidget(self.radio_seleccion)
        mode_layout.addWidget(self.radio_grupo)
        group_mode.setLayout(mode_layout)
        layout.addWidget(group_mode)

        # === CONFIGURACIÓN DE TABLERO ===
        group_tablero = QtWidgets.QGroupBox("2️⃣ Configuración de Tablero")
        tablero_layout = QtWidgets.QGridLayout()

        # Presets
        tablero_layout.addWidget(QtWidgets.QLabel("Tamaño predefinido:"), 0, 0)
        self.combo_preset = QtWidgets.QComboBox()
        self._populate_presets()
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        tablero_layout.addWidget(self.combo_preset, 0, 1)

        # Ancho
        tablero_layout.addWidget(QtWidgets.QLabel("Ancho (mm):"), 1, 0)
        self.spin_width = QtWidgets.QSpinBox()
        self.spin_width.setMinimum(100)
        self.spin_width.setMaximum(10000)
        self.spin_width.setValue(2440)
        tablero_layout.addWidget(self.spin_width, 1, 1)

        # Alto
        tablero_layout.addWidget(QtWidgets.QLabel("Alto (mm):"), 2, 0)
        self.spin_height = QtWidgets.QSpinBox()
        self.spin_height.setMinimum(100)
        self.spin_height.setMaximum(10000)
        self.spin_height.setValue(1830)
        tablero_layout.addWidget(self.spin_height, 2, 1)

        # Espaciado
        tablero_layout.addWidget(QtWidgets.QLabel("Espaciado (mm):"), 3, 0)
        self.spin_spacing = QtWidgets.QDoubleSpinBox()
        self.spin_spacing.setMinimum(0)
        self.spin_spacing.setMaximum(100)
        self.spin_spacing.setValue(15)
        tablero_layout.addWidget(self.spin_spacing, 3, 1)

        group_tablero.setLayout(tablero_layout)
        layout.addWidget(group_tablero)

        # === PARÁMETROS DE OPTIMIZACIÓN ===
        group_algo = QtWidgets.QGroupBox("3️⃣ Algoritmo de Optimización")
        algo_layout = QtWidgets.QGridLayout()

        algo_layout.addWidget(QtWidgets.QLabel("Algoritmo:"), 0, 0)
        self.combo_algo = QtWidgets.QComboBox()
        self.combo_algo.addItems(["Minkowski (Preciso)", "Physics (Rápido)"])
        algo_layout.addWidget(self.combo_algo, 0, 1)

        algo_layout.addWidget(QtWidgets.QLabel("Optimización:"), 1, 0)
        self.spin_generations = QtWidgets.QSpinBox()
        self.spin_generations.setMinimum(1)
        self.spin_generations.setMaximum(100)
        self.spin_generations.setValue(2)
        algo_layout.addWidget(self.spin_generations, 1, 1)

        group_algo.setLayout(algo_layout)
        layout.addWidget(group_algo)

        # === BOTONES ===
        btn_layout = QtWidgets.QHBoxLayout()

        btn_cancelar = QtWidgets.QPushButton("❌ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        btn_ejecutar = QtWidgets.QPushButton("▶️ Ejecutar Nesting")
        btn_ejecutar.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold;")
        btn_ejecutar.clicked.connect(self.execute_nesting)
        btn_layout.addWidget(btn_ejecutar)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _populate_presets(self):
        """Carga presets disponibles."""
        preset_names = presets_mgr.NestingPresetManager.get_preset_names()
        self.combo_preset.clear()
        self.combo_preset.addItems(preset_names)

    def _on_preset_changed(self):
        """Actualiza dimensiones cuando cambia el preset."""
        preset_name = self.combo_preset.currentText()
        preset = presets_mgr.NestingPresetManager.get_preset(preset_name)

        if preset:
            self.spin_width.setValue(preset["width"])
            self.spin_height.setValue(preset["height"])
            self.spin_spacing.setValue(preset["spacing"])

    def execute_nesting(self):
        """Ejecuta el nesting."""
        doc = FreeCAD.ActiveDocument
        if not doc:
            QtWidgets.QMessageBox.critical(self, "Error", "No hay documento activo")
            return

        # Determinar modo y obtener piezas
        if self.radio_seleccion.isChecked():
            self.mode = "seleccion"
            self.selected_parts = FreeCADGui.Selection.getSelection()
            if not self.selected_parts:
                QtWidgets.QMessageBox.warning(self, "Aviso", "No hay piezas seleccionadas")
                return
        elif self.radio_grupo.isChecked():
            self.mode = "grupo"
            module = doc.ActiveObject
            if not module or not hasattr(module, "Shape"):
                QtWidgets.QMessageBox.warning(self, "Aviso", "No hay módulo/grupo activo")
                return
            self.selected_parts = [module]
        else:
            self.mode = "todo"
            # Obtener todos los paneles
            self.selected_parts = [obj for obj in doc.Objects if hasattr(obj, "VDO_Tipo")]
            if not self.selected_parts:
                QtWidgets.QMessageBox.warning(self, "Aviso", "No hay paneles en el documento")
                return

        # Ejecutar nesting en background
        self.execute_nesting_async()
        self.accept()

    def execute_nesting_async(self):
        """Ejecuta nesting en background."""
        doc = FreeCAD.ActiveDocument

        print("=" * 70)
        print(f"🔲 NESTING - Modo: {self.mode.upper()}")
        print("=" * 70)

        # Preparar piezas
        print(f"\n📦 Preparando {len(self.selected_parts)} pieza(s)...")

        try:
            preparer = ShapePreparer(doc, {
                'deflection': 0.05,
                'simplification': 1.0
            })

            shapes = []
            for obj in self.selected_parts:
                try:
                    shape = preparer.prepare_shape(
                        obj,
                        quantity=1,
                        rotation_steps=4,
                        up_direction="Z+"
                    )
                    shapes.append(shape)
                    print(f"  ✅ {obj.Label}")
                except Exception as e:
                    print(f"  ❌ {obj.Label}: {e}")

            if not shapes:
                FreeCAD.Console.PrintError("No se pudieron preparar piezas\n")
                return

            # Parámetros
            width = self.spin_width.value()
            height = self.spin_height.value()
            spacing = self.spin_spacing.value()
            algo = "Minkowski" if "Minkowski" in self.combo_algo.currentText() else "Physics"
            generations = self.spin_generations.value()

            # Ejecutar nesting
            print(f"\n🔄 Ejecutando nesting ({algo})...")
            print(f"   Tablero: {width}×{height} mm, Espaciado: {spacing} mm")

            sheets, unplaced, steps, elapsed = nest(
                parts=shapes,
                width=width,
                height=height,
                rotation_steps=4,
                spacing=spacing,
                simulate=False,
                algorithm=algo,
                generations=generations if algo == "Minkowski" else 1,
                population_size=1,
                gravity_direction=0,
                verbose=True
            )

            # Resultados
            print(f"\n✅ Nesting completado en {elapsed:.2f}s")
            print(f"   Tableros utilizados: {len(sheets)}")
            print(f"   Piezas no colocadas: {len(unplaced)}")

            for i, sheet in enumerate(sheets):
                efficiency = (sheet.used_area / (sheet.width * sheet.height)) * 100
                print(f"     Sheet {i+1}: {len(sheet.parts)} piezas, {efficiency:.1f}% utilización")

            # Dibujar layouts en documento
            print(f"\n📐 Dibujando layouts...")
            layout_group = doc.addObject("App::DocumentObjectGroup", "NestingLayout")

            for sheet_idx, sheet in enumerate(sheets):
                sheet.parent_group_name = layout_group.Name
                sheet.draw(doc, {
                    'show_bounds': True,
                    'add_labels': True,
                    'label_height': 25,
                    'label_size': 10
                }, parent_group=layout_group)

            doc.recompute()

            print(f"\n📊 Layouts creados: {layout_group.Label}")
            print("   Puedes exportar a DXF si lo necesitas")

            # Mensaje de éxito
            QtWidgets.QMessageBox.information(
                None,
                "✅ Nesting Completado",
                f"Se crearon {len(sheets)} tablero(s)\n"
                f"Eficiencia promedio: {sum(s.used_area/(s.width*s.height)*100 for s in sheets)/len(sheets):.1f}%\n"
                f"\nLos layouts están en: {layout_group.Label}"
            )

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error: {e}\n")
            import traceback
            traceback.print_exc()


def main():
    """Punto de entrada principal."""
    dialog = NestingDialog()
    dialog.exec_()


if __name__ == "__main__":
    main()
