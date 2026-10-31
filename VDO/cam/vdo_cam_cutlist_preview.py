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
except ImportError:
    # sys.exit() aqui abortaba el interprete entero del que importara.
    raise ImportError("VDO: este modulo requiere ejecutarse dentro de FreeCAD")

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide import QtWidgets, QtCore

_macro_dir = Path(__file__).parent
sys.path.insert(0, str(_macro_dir))
import VDO.cam.vdo_cam_cutlist
from VDO.shared import vdo_shared_loader


class CuttingListPreviewPanel:
    """Task Panel para preview y confirmación"""

    def __init__(self, piezas, modo):
        self.piezas = piezas
        self.modo = modo
        self.piezas_coloreadas = []
        self._colores_originales = {}

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
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Nombre", "Medidas (L × A × E)",
            "Canto Norte", "Canto Sur", "Canto Este", "Canto Oeste",
            "Material / Calibre",
        ])
        self.tabla.setRowCount(len(piezas))
        self.tabla.setMaximumHeight(200)

        loader = vdo_shared_loader.get_loader()

        for row, pieza in enumerate(piezas):
            nombre = QtWidgets.QTableWidgetItem(pieza.get("nombre", "???"))
            largo = pieza.get("largo", 0)
            ancho = pieza.get("ancho", 0)
            espesor = pieza.get("espesor", 0)
            medidas = QtWidgets.QTableWidgetItem(
                f"{largo} × {ancho} × {espesor} mm")

            cantos = pieza.get("cantos", {})
            canto_n = QtWidgets.QTableWidgetItem(
                cantos.get("norte", "FX"))
            canto_s = QtWidgets.QTableWidgetItem(
                cantos.get("sur", "FX"))
            canto_e = QtWidgets.QTableWidgetItem(
                cantos.get("este", "FX"))
            canto_o = QtWidgets.QTableWidgetItem(
                cantos.get("oeste", "FX"))

            mat_id = pieza.get("material_ref", "")
            material = loader.get_material(mat_id) if loader else None
            if material:
                mat_str = QtWidgets.QTableWidgetItem(
                    f"{material['nombre']} {espesor}mm")
            else:
                mat_str = QtWidgets.QTableWidgetItem(
                    f"{mat_id} {espesor}mm")

            self.tabla.setItem(row, 0, nombre)
            self.tabla.setItem(row, 1, medidas)
            self.tabla.setItem(row, 2, canto_n)
            self.tabla.setItem(row, 3, canto_s)
            self.tabla.setItem(row, 4, canto_e)
            self.tabla.setItem(row, 5, canto_o)
            self.tabla.setItem(row, 6, mat_str)

        self.tabla.resizeColumnsToContents()
        self.tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla)

        # Resumen (sin precios)
        resumen = QtWidgets.QLabel()
        resumen.setText(
            f"<b>{len(piezas)} piezas de melamina listas para exportar</b>")
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

        # Nombres de las piezas a exportar. Un panel exportable comparte
        # Label con el objeto; un contenedor COCO exporta piezas cuyo
        # nombre es "<Label>_<sufijo>".
        piezas_ids = {pieza.get("nombre") for pieza in self.piezas if pieza.get("nombre")}

        for obj in doc.Objects:
            if not hasattr(obj, "VDO_Tipo"):
                continue

            etiqueta = obj.Label
            exportar = etiqueta in piezas_ids or any(
                nombre.startswith(etiqueta + "_") for nombre in piezas_ids)

            if obj.Name not in self._colores_originales:
                self._colores_originales[obj.Name] = obj.ViewObject.ShapeColor

            if exportar:
                # ROJO: se va a exportar
                obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0, 0.8)
                self.piezas_coloreadas.append(obj)
            else:
                # GRIS: no se exporta
                obj.ViewObject.ShapeColor = (0.7, 0.7, 0.7, 0.5)

        print(f"✅ {len(self.piezas_coloreadas)} piezas coloreadas en ROJO")

    def aceptar(self):
        """Genera CSV y cierra dialog"""
        print(f"\n✅ Exportando {len(self.piezas)} piezas...")

        # Restaurar colores
        self._restaurar_colores()

        # Diálogo para elegir ubicación (con padre = ventana principal de FreeCAD)
        try:
            parent = Gui.getMainWindow()
        except Exception:
            parent = None

        # Ruta sugerida en el HOME (siempre existe); NO usar ~/Desktop
        ruta_sugerida = str(Path.home() / "vdo_cutting_list.csv")

        try:
            output_file, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent,
                "Guardar lista de corte CSV",
                ruta_sugerida,
                "CSV Files (*.csv);;All Files (*)"
            )
        except Exception as e:
            print(f"❌ Error abriendo el diálogo de archivo: {e}")
            App.Console.PrintError(f"[VDO] Error abriendo diálogo: {e}\n")
            return

        if not output_file:
            print("❌ Exportación cancelada (o el diálogo se cerró sin elegir archivo)")
            App.Console.PrintWarning("[VDO] Exportación cancelada\n")
            Gui.Control.closeDialog()
            return

        # Generar CSV
        try:
            ok = vdo_export_cutting_list.generar_csv_opencutlist(
                self.piezas, output_file)
        except Exception as e:
            print(f"❌ Error generando CSV: {e}")
            App.Console.PrintError(f"[VDO] Error generando CSV: {e}\n")
            return

        if ok:
            print(f"✅ CSV generado: {output_file}")
            print("\n📌 Próximo paso: Usa el archivo CSV con tu optimizador de corte")
            App.Console.PrintMessage(f"[VDO] Lista de corte exportada: {output_file}\n")

        Gui.Control.closeDialog()

    def cancelar(self):
        """Cancela y restaura colores"""
        print("❌ Exportación cancelada")
        self._restaurar_colores()
        Gui.Control.closeDialog()

    def _restaurar_colores(self):
        """Restaura los colores originales guardados antes del preview."""
        doc = App.ActiveDocument
        for obj in doc.Objects:
            if not hasattr(obj, "VDO_Tipo"):
                continue
            color = self._colores_originales.get(obj.Name)
            if color is None:
                # Fallback sólo si el objeto no fue coloreado previamente.
                color = (0.8, 0.8, 0.8, 1.0)
            obj.ViewObject.ShapeColor = color
        self._colores_originales.clear()


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

    # Extraer piezas según modo (lógica unificada: paneles + contenedores)
    print(f"\n📦 Extrayendo piezas (modo: {modo})...")
    piezas = vdo_export_cutting_list.extraer_piezas_del_documento(modo)

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
