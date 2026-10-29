# -*- coding: utf-8 -*-
"""Gestor visual de herrajes VDO (Capa H - UI).

Diálogo flotante en PySide para inspeccionar y editar el catálogo de
herrajes (vdo_hardware_catalog.json). 100% compatible con el tema oscuro
de FreeCAD.
"""

import json
import os

from PySide import QtCore, QtGui, QtWidgets

from vdo_qt import VDO_DoubleSpinBox
import vdo_hardware_hub as H

_HERE = os.path.dirname(os.path.abspath(__file__))
_CATALOGO_PATH = os.path.join(_HERE, "vdo_hardware_catalog.json")

FAMILIAS = {
    "bisagra_cazoleta": "Bisagras de Cazoleta",
    "sistema_corredizo": "Sistemas Corredizos",
}

# Mapeo clave tecnica -> etiqueta legible
ETIQUETAS = {
    "diametro_cazoleta": "Ø Cazoleta (mm)",
    "profundidad_cazoleta": "Profundidad cazoleta (mm)",
    "cota_k_default": "Cota K (mm)",
    "solape_nominal": "Solape nominal (mm)",
    "holgura_perimetral_min": "Holgura perím. mín. (mm)",
    "descuento_altura_hoja": "Descuento altura hoja (mm)",
    "traslape_minimo": "Traslape mín. (mm)",
    "ancho_piso_riel_doble": "Ancho riel doble (mm)",
    "espesor_hoja_min": "Espesor hoja mín. (mm)",
    "capacidad_peso_kg": "Capacidad peso (kg)",
    "ancho_minimo_hoja": "Ancho hoja mín. (mm)",
    "espesor_vidrio_max": "Espesor vidrio máx. (mm)",
    "luz_cerrada_sin_cenefa": "Luz cerrada sin cenefa",
    "distancia_base_frente": "Distancia base-frente (mm)",
    "separacion_tornillos_base": "Sep. tornillos base (mm)",
    "holgura_luz": "Holgura luz (mm)",
}

# Claves que se editan como casilla de verificacion (booleano)
CLAVES_BOOL = ("luz_cerrada_sin_cenefa",)


def _resumen_cotas(sku, tecnicos):
    """Texto corto de cotas clave para la columna resumen de la tabla."""
    tipo = tecnicos.get("tipo_montaje")
    partes = []
    if tipo in ("parche", "semiparche", "embebida"):
        partes.append("Ø{}".format(tecnicos.get("diametro_cazoleta", 35)))
        if "cota_k_default" in tecnicos:
            partes.append("K={}".format(tecnicos["cota_k_default"]))
        if "solape_nominal" in tecnicos:
            partes.append("solape {}".format(tecnicos["solape_nominal"]))
        elif "holgura_perimetral_min" in tecnicos:
            partes.append("holgura {}".format(tecnicos["holgura_perimetral_min"]))
    else:
        if "descuento_altura_hoja" in tecnicos:
            partes.append("desc. {}".format(tecnicos["descuento_altura_hoja"]))
        if "traslape_minimo" in tecnicos:
            partes.append("traslape {}".format(tecnicos["traslape_minimo"]))
        if "ancho_piso_riel_doble" in tecnicos:
            partes.append("riel {}".format(tecnicos["ancho_piso_riel_doble"]))
    return " | ".join(partes) if partes else "-"


class VDOHardwareManagerDialog(QtWidgets.QDialog):
    """Diálogo de inspeccion y edicion del catalogo de herrajes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestor de Herrajes VDO")
        self.setMinimumSize(980, 620)
        self.resize(1100, 700)

        self._cargando = False
        self._sku_actual = None
        self._catalogo = self._cargar_catalogo()
        self._editores = {}  # clave -> widget

        self._construir_ui()
        self._aplicar_estilo_oscuro()
        self._cargar_familia_actual()
        self._conectar_senales()

    # ------------------------------------------------------------------
    # Carga / persistencia del JSON
    # ------------------------------------------------------------------
    def _cargar_catalogo(self):
        try:
            with open(_CATALOGO_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(
                self, "Error de catálogo",
                f"No se pudo leer el catálogo de herrajes:\n{exc}")
            return {"bisagra_cazoleta": {}, "sistema_corredizo": {}}

    def _guardar_catalogo(self):
        with open(_CATALOGO_PATH, "w", encoding="utf-8") as fh:
            json.dump(self._catalogo, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ---- Selector de familia ----
        fila_familia = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Familia de herraje:")
        lbl.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        fila_familia.addWidget(lbl)
        self.combo_familia = QtWidgets.QComboBox()
        for clave, etiqueta in FAMILIAS.items():
            self.combo_familia.addItem(etiqueta, clave)
        fila_familia.addWidget(self.combo_familia)
        fila_familia.addStretch(1)
        layout.addLayout(fila_familia)

        # ---- Tabla de productos ----
        self.tabla = QtWidgets.QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(
            ["SKU", "Nombre comercial", "Proveedor", "Precio (USD)", "Cotas clave (resumen)"])
        self.tabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tabla.verticalHeader().hide()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeToContents)
        layout.addWidget(self.tabla, stretch=2)

        # ---- Panel de detalle / edicion tecnica ----
        grupo = QtWidgets.QGroupBox("Inspeccion y edicion tecnica (parametros_tecnicos)")
        grupo.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #e0e0e0; border: 1px solid #555555; "
            "border-radius: 6px; margin-top: 10px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }")
        self.grid_detalle = QtWidgets.QGridLayout(grupo)
        self.grid_detalle.setHorizontalSpacing(12)
        self.grid_detalle.setVerticalSpacing(6)
        layout.addWidget(grupo, stretch=1)

        self.lbl_sku_detalle = QtWidgets.QLabel("SKU: -")
        self.lbl_sku_detalle.setStyleSheet(
            "font-weight: bold; color: #007acc; font-size: 12px;")
        self.grid_detalle.addWidget(self.lbl_sku_detalle, 0, 0, 1, 4)

        self.scroll_detalle = QtWidgets.QScrollArea()
        self.scroll_detalle.setWidgetResizable(True)
        self.scroll_detalle.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.widget_detalle = QtWidgets.QWidget()
        self.form_detalle = QtWidgets.QFormLayout(self.widget_detalle)
        self.form_detalle.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.scroll_detalle.setWidget(self.widget_detalle)
        self.grid_detalle.addWidget(self.scroll_detalle, 1, 0, 1, 4)

        # ---- Botones de accion ----
        fila_botones = QtWidgets.QHBoxLayout()
        self.btn_guardar = QtWidgets.QPushButton("💾 Guardar Cambios")
        self.btn_nuevo = QtWidgets.QPushButton("➕ Nuevo Herraje")
        self.btn_cerrar = QtWidgets.QPushButton("Cerrar")
        for btn in (self.btn_guardar, self.btn_nuevo, self.btn_cerrar):
            btn.setMinimumHeight(30)
        fila_botones.addWidget(self.btn_guardar)
        fila_botones.addWidget(self.btn_nuevo)
        fila_botones.addStretch(1)
        fila_botones.addWidget(self.btn_cerrar)
        layout.addLayout(fila_botones)

    def _aplicar_estilo_oscuro(self):
        estilo = """
        QDialog { background-color: #2b2b2b; color: #e0e0e0; }
        QLabel { color: #e0e0e0; }
        QComboBox {
            background-color: #3a3a3a; color: #e0e0e0;
            border: 1px solid #555555; border-radius: 4px; padding: 4px;
        }
        QComboBox QAbstractItemView {
            background-color: #3a3a3a; color: #e0e0e0;
            selection-background-color: #007acc;
        }
        QTableWidget {
            background-color: #333333; color: #e0e0e0;
            gridline-color: #444444; border: 1px solid #555555;
        }
        QTableWidget::item:selected {
            background-color: #007acc; color: #ffffff;
        }
        QTableWidget::item:alternate {
            background-color: #3a3a3a;
        }
        QHeaderView::section {
            background-color: #3a3a3a; color: #e0e0e0;
            border: 1px solid #555555; padding: 4px; font-weight: bold;
        }
        QDoubleSpinBox, QLineEdit, QSpinBox {
            background-color: #3a3a3a; color: #e0e0e0;
            border: 1px solid #555555; border-radius: 3px; padding: 3px;
        }
        QDoubleSpinBox:focus, QLineEdit:focus {
            border-color: #007acc;
        }
        QCheckBox { color: #e0e0e0; }
        QCheckBox::indicator {
            width: 16px; height: 16px;
            background-color: #3a3a3a; border: 1px solid #555555;
        }
        QCheckBox::indicator:checked {
            background-color: #007acc; border: 1px solid #0098ff;
        }
        QPushButton {
            background-color: #3a3a3a; color: #e0e0e0;
            border: 1px solid #555555; border-radius: 4px;
            padding: 6px 14px; font-weight: bold;
        }
        QPushButton:hover { background-color: #444444; border-color: #777777; }
        QPushButton:pressed { background-color: #007acc; color: #ffffff; }
        QGroupBox { color: #e0e0e0; }
        QScrollArea { background-color: #2b2b2b; border: none; }
        """
        self.setStyleSheet(estilo)

    def _conectar_senales(self):
        self.combo_familia.currentIndexChanged.connect(self._cargar_familia_actual)
        self.tabla.itemSelectionChanged.connect(self._cargar_detalle_seleccion)
        self.btn_guardar.clicked.connect(self._guardar_cambios)
        self.btn_nuevo.clicked.connect(self._nuevo_herraje)
        self.btn_cerrar.clicked.connect(self.reject)

    # ------------------------------------------------------------------
    # Llenado de tabla
    # ------------------------------------------------------------------
    def _clave_familia_actual(self):
        return self.combo_familia.itemData(self.combo_familia.currentIndex())

    def _cargar_familia_actual(self):
        self._cargando = True
        self.tabla.setRowCount(0)
        clave = self._clave_familia_actual()
        productos = self._catalogo.get(clave, {})
        for sku, datos in productos.items():
            self._agregar_fila_tabla(sku, datos)
        self._cargando = False
        self._sku_actual = None
        self._limpiar_detalle()

    def _agregar_fila_tabla(self, sku, datos):
        tecnicos = datos.get("parametros_tecnicos", {})
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        items = [
            sku,
            datos.get("nombre", ""),
            datos.get("proveedor", ""),
            f"{datos.get('precio_unitario', 0):.2f}",
            _resumen_cotas(sku, tecnicos),
        ]
        for col, texto in enumerate(items):
            item = QtWidgets.QTableWidgetItem(str(texto))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            if col == 3:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.tabla.setItem(fila, col, item)

    # ------------------------------------------------------------------
    # Detalle de un herraje
    # ------------------------------------------------------------------
    def _cargar_detalle_seleccion(self):
        filas = self.tabla.selectionModel().selectedRows()
        if not filas:
            return
        fila = filas[0].row()
        sku = self.tabla.item(fila, 0).text()
        self._mostrar_detalle(sku)

    def _mostrar_detalle(self, sku):
        self._cargando = True
        self._sku_actual = sku
        clave = self._clave_familia_actual()
        datos = self._catalogo.get(clave, {}).get(sku, {})
        tecnicos = datos.get("parametros_tecnicos", {})

        self.lbl_sku_detalle.setText(f"SKU: {sku}  |  {datos.get('nombre','')}")

        # Limpiar editores previos
        while self.form_detalle.rowCount() > 0:
            self.form_detalle.removeRow(0)
        self._editores.clear()

        fila_form = 0
        for clave_tec, valor in tecnicos.items():
            etiqueta = ETIQUETAS.get(clave_tec, clave_tec)
            widget = self._crear_editor(clave_tec, valor)
            self._editores[clave_tec] = widget
            self.form_detalle.addRow(etiqueta, widget)
            fila_form += 1

        if not self._editores:
            lbl = QtWidgets.QLabel("(Sin parámetros técnicos registrados)")
            lbl.setStyleSheet("color: #8a8a8a; font-style: italic;")
            self.form_detalle.addRow(lbl)

        self._cargando = False

    def _crear_editor(self, clave, valor):
        if clave in CLAVES_BOOL:
            chk = QtWidgets.QCheckBox()
            chk.setChecked(bool(valor))
            return chk
        if isinstance(valor, bool):
            chk = QtWidgets.QCheckBox()
            chk.setChecked(valor)
            return chk
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            spin = VDO_DoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(-999999.0, 999999.0)
            spin.setValue(float(valor))
            return spin
        edit = QtWidgets.QLineEdit(str(valor))
        return edit

    def _limpiar_detalle(self):
        self.lbl_sku_detalle.setText("SKU: -")
        while self.form_detalle.rowCount() > 0:
            self.form_detalle.removeRow(0)
        self._editores.clear()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _leer_editores(self):
        tecnicos = {}
        for clave, widget in self._editores.items():
            if isinstance(widget, QtWidgets.QCheckBox):
                tecnicos[clave] = widget.isChecked()
            elif isinstance(widget, (VDO_DoubleSpinBox, QtWidgets.QDoubleSpinBox,
                                     QtWidgets.QSpinBox)):
                tecnicos[clave] = widget.value()
            else:
                texto = widget.text().strip()
                tecnicos[clave] = texto
        return tecnicos

    def _guardar_cambios(self):
        if not self._sku_actual:
            QtWidgets.QMessageBox.information(
                self, "Sin selección", "Seleccione un herraje en la tabla primero.")
            return
        clave = self._clave_familia_actual()
        tecnicos = self._leer_editores()
        datos = self._catalogo.get(clave, {}).get(self._sku_actual)
        if datos is None:
            return
        datos["parametros_tecnicos"] = tecnicos
        try:
            self._guardar_catalogo()
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self, "Error al guardar", f"No se pudo guardar el catálogo:\n{exc}")
            return
        # Refrescar resumen de la tabla
        filas = self.tabla.selectionModel().selectedRows()
        if filas:
            fila = filas[0].row()
            item = QtWidgets.QTableWidgetItem(
                _resumen_cotas(self._sku_actual, tecnicos))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.tabla.setItem(fila, 4, item)
        QtWidgets.QMessageBox.information(
            self, "Guardado", "Cambios guardados en vdo_hardware_catalog.json")

    def _nuevo_herraje(self):
        clave = self._clave_familia_actual()
        sku, ok = QtWidgets.QInputDialog.getText(
            self, "Nuevo herraje", "SKU del nuevo herraje:")
        if not ok or not sku.strip():
            return
        sku = sku.strip()
        if sku in self._catalogo.get(clave, {}):
            QtWidgets.QMessageBox.warning(
                self, "SKU duplicado", f"El SKU {sku} ya existe en esta familia.")
            return
        nombre, ok2 = QtWidgets.QInputDialog.getText(
            self, "Nuevo herraje", "Nombre comercial:")
        if not ok2:
            return
        self._catalogo.setdefault(clave, {})[sku] = {
            "nombre": nombre or sku,
            "proveedor": "Personalizado",
            "precio_unitario": 0.0,
            "moneda": "USD",
            "parametros_tecnicos": {},
        }
        self._guardar_catalogo()
        self._cargar_familia_actual()
        # Seleccionar la fila recién creada
        for fila in range(self.tabla.rowCount()):
            if self.tabla.item(fila, 0).text() == sku:
                self.tabla.selectRow(fila)
                break


def lanzar_gestor_herrajes(parent=None):
    """Punto de entrada para lanzar el diálogo desde FreeCAD o tests."""
    dialogo = VDOHardwareManagerDialog(parent)
    return dialogo.exec_()


if __name__ == "__main__":
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialogo = VDOHardwareManagerDialog()
    dialogo.show()
    app.exec_()
