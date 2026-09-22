#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_cutting_list_preview.py
Preview visual antes de exportar a OpenCutList

Flujo:
  1. Usuario elige: Selección / Grupo / Todo
  2. Preview colorea piezas en ROJO
  3. Task Panel muestra confirmación
  4. Usuario navega 3D, verifica
  5. Click "Aceptar" → CSV generado
"""

import sys
from pathlib import Path

try:
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide2 import QtWidgets, QtCore
except ImportError:
    print("❌ Esto debe ejecutarse dentro de FreeCAD")
    sys.exit(1)

_macro_dir = Path(__file__).parent
sys.path.insert(0, str(_macro_dir))
import vdo_export_cutting_list
import vdo_loader


class CuttingListPreviewPanel:
    """Task Panel para preview y confirmación"""

    def __init__(self, piezas, modo):
        self.piezas = piezas
        self.modo = modo
        self.piezas_coloreadas = []

        # Crear form
        self.form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        # Header
        header = QtWidgets.QLabel()
        header.setText(f"<b>📊 Preview Exportación - {modo.upper()}</b>")
        header.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(header)

        # Info
        info = QtWidgets.QLabel()
        info.setText(f"Se va a exportar <b>{len(piezas)}</b> piezas de melamina")
        layout.addWidget(info)

        # Tabla de piezas
        self.tabla = QtWidgets.QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Material", "L×A×E", "Cantidad", "Costo"])
        self.tabla.setRowCount(len(piezas))
        self.tabla.setMaximumHeight(200)

        loader = vdo_loader.get_loader()
        total_costo = 0

        for row, pieza in enumerate(piezas):
            nombre = QtWidgets.QTableWidgetItem(pieza.get("nombre", "???"))
            mat_id = pieza.get("material_ref", "")
            material = loader.get_material(mat_id) if loader else None
            mat_str = material["nombre"] if material else mat_id
            mat_item = QtWidgets.QTableWidgetItem(mat_str)

            dims = f"{pieza.get('largo', 0)}×{pieza.get('ancho', 0)}×{pieza.get('espesor', 0)}"
            dims_item = QtWidgets.QTableWidgetItem(dims)

            qty = QtWidgets.QTableWidgetItem(str(pieza.get("cantidad", 1)))

            # Costo
            if material:
                area_m2 = (pieza["largo"] * pieza["ancho"]) / 1000000
                costo = loader.calcular_costo_material(mat_id, area_m2)
                total_costo += costo
                costo_item = QtWidgets.QTableWidgetItem(f"${costo:.2f}")
            else:
                costo_item = QtWidgets.QTableWidgetItem("???")

            self.tabla.setItem(row, 0, nombre)
            self.tabla.setItem(row, 1, mat_item)
            self.tabla.setItem(row, 2, dims_item)
            self.tabla.setItem(row, 3, qty)
            self.tabla.setItem(row, 4, costo_item)

        self.tabla.resizeColumnsToContents()
        layout.addWidget(self.tabla)

        # Resumen
        resumen = QtWidgets.QLabel()
        resumen.setText(f"<b>💰 Costo total material: ${total_costo:.2f}</b>")
        resumen.setStyleSheet("color: #0066cc; font-weight: bold;")
        layout.addWidget(resumen)

        # Instrucciones
        instrucciones = QtWidgets.QLabel()
        instrucciones.setText(
            "✅ Las piezas están <span style='color: red;'>COLOREADAS EN ROJO</span> en el 3D viewer\n"
            "👁️ Navega para verificar que se van a exportar las piezas correctas\n"
            "📋 Luego haz click en 'Aceptar' para generar el CSV"
        )
        layout.addWidget(instrucciones)

        layout.addSpacing(10)

        # Botones
        btn_layout = QtWidgets.QHBoxLayout()

        btn_cancelar = QtWidgets.QPushButton("❌ Cancelar")
        btn_cancelar.clicked.connect(self.cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_aceptar = QtWidgets.QPushButton("✅ Aceptar - Generar CSV")
        btn_aceptar.setStyleSheet("background-color: #00cc00; color: white; font-weight: bold;")
        btn_aceptar.clicked.connect(self.aceptar)
        btn_layout.addWidget(btn_aceptar)

        layout.addLayout(btn_layout)

        self.form.setLayout(layout)
        self.colorear_piezas()

    def colorear_piezas(self):
        """Colorea en rojo las piezas que se van a exportar"""
        doc = App.ActiveDocument

        # Obtener IDs de piezas a exportar
        piezas_ids = {pieza.get("nombre") for pieza in self.piezas}

        for obj in doc.Objects:
            if hasattr(obj, "VDO_Tipo") and obj.Label in piezas_ids:
                # ROJO: se va a exportar
                obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0, 0.8)
                self.piezas_coloreadas.append(obj)
            elif hasattr(obj, "VDO_Tipo"):
                # GRIS: no se exporta
                obj.ViewObject.ShapeColor = (0.7, 0.7, 0.7, 0.5)

        print(f"✅ {len(self.piezas_coloreadas)} piezas coloreadas en ROJO")

    def aceptar(self):
        """Genera CSV y cierra dialog"""
        print(f"\n✅ Exportando {len(self.piezas)} piezas...")

        # Restaurar colores
        self._restaurar_colores()

        # Diálogo para elegir ubicación y nombre del archivo
        from PySide2 import QtWidgets
        file_dialog = QtWidgets.QFileDialog()
        output_file, _ = file_dialog.getSaveFileName(
            None,
            "Guardar lista de corte CSV",
            str(Path.home() / "Desktop" / "vdo_cutting_list.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )

        if not output_file:
            print("❌ Exportación cancelada por el usuario")
            Gui.Control.closeDialog()
            return

        # Generar CSV
        vdo_export_cutting_list.generar_csv_opencutlist(self.piezas, output_file)

        print(f"✅ CSV generado: {output_file}")
        print("\n📌 Próximo paso: Usa el archivo CSV con tu optimizador de corte")

        Gui.Control.closeDialog()

    def cancelar(self):
        """Cancela y restaura colores"""
        print("❌ Exportación cancelada")
        self._restaurar_colores()
        Gui.Control.closeDialog()

    def _restaurar_colores(self):
        """Restaura colores originales"""
        doc = App.ActiveDocument
        for obj in doc.Objects:
            if hasattr(obj, "VDO_Tipo"):
                # Color por defecto
                obj.ViewObject.ShapeColor = (0.8, 0.8, 0.8, 1.0)


def mostrar_preview(piezas, modo):
    """Muestra el panel de preview"""
    panel = CuttingListPreviewPanel(piezas, modo)
    Gui.Control.showDialog(panel)


def main(modo="todo"):
    """
    Modo: "seleccion" | "grupo" | "todo"
    """
    print("=" * 70)
    print(f"🔍 CUTTING LIST PREVIEW - {modo.upper()}")
    print("=" * 70)

    doc = App.ActiveDocument
    if not doc:
        print("❌ No hay documento activo")
        return False

    # Extraer piezas según modo
    piezas = []

    if modo == "seleccion":
        print("\n📦 Extrayendo piezas SELECCIONADAS...")
        selected = Gui.Selection.getSelectionEx()
        for sel in selected:
            obj = sel.Object
            if hasattr(obj, "VDO_Tipo") and obj.VDO_Tipo == "panel":
                piezas.append(vdo_export_cutting_list.extraer_pieza(obj))

    elif modo == "grupo":
        print("\n📦 Extrayendo piezas del GRUPO/MÓDULO seleccionado...")
        modulo_activo = doc.ActiveObject
        if modulo_activo and hasattr(modulo_activo, "VDO_Tipo"):
            # Extraer todas las piezas del módulo
            piezas.append(vdo_export_cutting_list.extraer_pieza(modulo_activo))

    elif modo == "todo":
        print("\n📦 Extrayendo TODAS las piezas del documento...")
        for obj in doc.Objects:
            if hasattr(obj, "VDO_Tipo") and obj.VDO_Tipo == "panel":
                piezas.append(vdo_export_cutting_list.extraer_pieza(obj))

    if not piezas:
        print("❌ No se encontraron piezas de melamina para exportar")
        return False

    print(f"✅ {len(piezas)} piezas encontradas")

    # Mostrar preview
    print("\n🎨 Mostrando preview (piezas en ROJO)...")
    mostrar_preview(piezas, modo)

    return True


if __name__ == "__main__":
    main(modo="todo")
