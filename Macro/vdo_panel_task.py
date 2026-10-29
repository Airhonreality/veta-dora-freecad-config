# -*- coding: utf-8 -*-
# =====================================================================
# vdo_panel_task.py
# Panel de configuración del módulo Panel VDO.
# =====================================================================

import FreeCAD as App
from PySide import QtGui

from vdo_qt import VDO_DoubleSpinBox, VDO_ExpressionInput

import vdo_defaults as VDO_D
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_module_props import (
    ANCLAJES, ANCLAJE_DEFAULT, ANCLAJE_LABELS,
    add_common_props, aplicar_rotacion
)
from vdo_panel_core import (
    CANTOS_VALIDOS, add_reengrose_props)
import vdo_reengrose as VDO_RE


class PanelTaskPanel(VDOTransactionMixin):
    """Configuración de un panel VDO (orientación, cantos y pose)."""

    def __init__(self, obj=None, on_accept=None, on_cancel=None,
                 auto_transaction=True):
        self.obj = obj
        self._vdo_aceptado = False
        self._init_vdo_task(
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=auto_transaction,
            transaction_name="Editar panel VDO",
        )
        self.form = self._crear_widget()
        if obj:
            add_reengrose_props(obj)
            add_common_props(obj)
            self._cargar_valores(obj)

    def _crear_widget(self):
        widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout(widget)

        grupo_general = QtGui.QGroupBox("Panel")
        grid = QtGui.QGridLayout(grupo_general)

        grid.addWidget(QtGui.QLabel("Etiqueta:"), 0, 0)
        self.edit_etiqueta = QtGui.QLineEdit()
        self.edit_etiqueta.setToolTip(
            "Nombre visible de la pieza en el árbol y en la lista de corte.")
        grid.addWidget(self.edit_etiqueta, 0, 1)

        grid.addWidget(QtGui.QLabel("Orientación:"), 1, 0)
        self.combo_orientacion = QtGui.QComboBox()
        self.combo_orientacion.addItems(VDO_D.ORIENTACIONES_VALIDAS)
        self.combo_orientacion.setToolTip(
            "Horizontal: el largo corre a lo ancho del mueble. "
            "Vertical: el largo corre en altura.")
        grid.addWidget(self.combo_orientacion, 1, 1)

        grid.addWidget(QtGui.QLabel("Material:"), 2, 0)
        self.edit_material = QtGui.QLineEdit()
        self.edit_material.setToolTip(
            "Referencia de material del manifiesto, por ejemplo "
            "melamina_standar.")
        grid.addWidget(self.edit_material, 2, 1)

        main_layout.addWidget(grupo_general)

        grupo_dim = QtGui.QGroupBox("Dimensiones")
        grid_dim = QtGui.QGridLayout(grupo_dim)

        self.combo_modo = QtGui.QComboBox()
        self.combo_modo.addItems(["Directo", "Expresión (fórmula)"])
        self.combo_modo.setToolTip(
            "Directo: valor numérico libre. "
            "Expresión (fórmula): expresión nativa de FreeCAD que enlaza "
            "cualquier propiedad del proyecto (p. ej. Params.Largo / 2).")
        grid_dim.addWidget(self.combo_modo, 0, 0, 1, 2)

        grid_dim.addWidget(QtGui.QLabel("Largo (mm):"), 1, 0)
        self.spin_largo = VDO_ExpressionInput(numeric_only=False)
        self.spin_largo.setToolTip(
            "Largo real de la cara del tablero, no la diagonal ni el desarrollo.")
        grid_dim.addWidget(self.spin_largo, 1, 1)

        grid_dim.addWidget(QtGui.QLabel("Ancho (mm):"), 2, 0)
        self.spin_ancho = VDO_ExpressionInput(numeric_only=False)
        self.spin_ancho.setToolTip(
            "Ancho de la cara del tablero. En un lateral vertical suele ser "
            "la profundidad del mueble.")
        grid_dim.addWidget(self.spin_ancho, 2, 1)

        grid_dim.addWidget(QtGui.QLabel("Espesor (mm):"), 3, 0)
        self.spin_espesor = VDO_ExpressionInput(numeric_only=False)
        self.spin_espesor.setToolTip(
            "Espesor del tablero. El reengrose usa este valor por defecto.")
        grid_dim.addWidget(self.spin_espesor, 3, 1)

        main_layout.addWidget(grupo_dim)

        grupo_cantos = QtGui.QGroupBox("Cantos")
        grid_cantos = QtGui.QGridLayout(grupo_cantos)
        self.combo_cantos = {}
        ayudas_canto = {
            "Norte": "Borde norte del tablero visto desde la cara A.",
            "Sur": "Borde sur del tablero visto desde la cara A.",
            "Este": "Borde este del tablero visto desde la cara A.",
            "Oeste": "Borde oeste del tablero visto desde la cara A.",
        }
        for fila, direccion in enumerate(["Norte", "Sur", "Este", "Oeste"]):
            grid_cantos.addWidget(QtGui.QLabel(f"{direccion}:"), fila, 0)
            combo = QtGui.QComboBox()
            combo.addItems(list(CANTOS_VALIDOS))
            combo.setToolTip(
                ayudas_canto[direccion] +
                " RIG = canto rígido, SMRG = semi-rígido, FX = sin canto.")
            self.combo_cantos[direccion] = combo
            grid_cantos.addWidget(combo, fila, 1)

        main_layout.addWidget(grupo_cantos)

        main_layout.addWidget(self._crear_grupo_reengrose())

        grupo_coloc = QtGui.QGroupBox("Colocación")
        grid_coloc = QtGui.QGridLayout(grupo_coloc)

        grid_coloc.addWidget(QtGui.QLabel("Rotación Z:"), 0, 0)
        self.spin_rotacion = VDO_DoubleSpinBox()
        self.spin_rotacion.setRange(-360.0, 360.0)
        self.spin_rotacion.setDecimals(1)
        self.spin_rotacion.setSuffix(" °")
        self.spin_rotacion.setWrapping(True)
        self.spin_rotacion.setToolTip(
            "Rotación de colocación alrededor de Z. No cambia las medidas "
            "del tablero.")
        grid_coloc.addWidget(self.spin_rotacion, 0, 1)

        grid_coloc.addWidget(QtGui.QLabel("Anclaje:"), 1, 0)
        self.combo_anclaje = QtGui.QComboBox()
        for anclaje in ANCLAJES:
            self.combo_anclaje.addItem(
                ANCLAJE_LABELS.get(anclaje, anclaje), anclaje)
        self.combo_anclaje.setToolTip(
            "Esquina del panel que se apoya en el punto de colocación.")
        grid_coloc.addWidget(self.combo_anclaje, 1, 1)

        main_layout.addWidget(grupo_coloc)
        main_layout.addStretch()

        botones = QtGui.QDialogButtonBox()
        btn_ok = botones.addButton(
            "Crear y colocar" if not self.auto_transaction else "Aplicar",
            QtGui.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtGui.QDialogButtonBox.RejectRole)
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        btn_ok.setToolTip(
            "Guarda los cambios en el panel y recalcula la geometría.")
        btn_cancelar.setToolTip("Cierra sin aplicar los cambios.")
        main_layout.addWidget(botones)

        self.re_editor.changed.connect(self._on_reengrose_modo_changed)
        return widget

    def _crear_grupo_reengrose(self):
        from vdo_reengrose_ui import ReengroseBorderEditor
        self.re_editor = ReengroseBorderEditor()
        self.chk_reengrose = self.re_editor.chk_activo
        self.spin_re_ancho = self.re_editor.spin_ancho
        self.spin_re_espesor = self.re_editor.spin_espesor
        self.combo_re_cara = self.re_editor.combo_cara
        self.combo_re_modo = self.re_editor.combo_fabricacion
        self.combo_re_politica = self.re_editor.combo_choque
        self.combo_re_prioridad = self.re_editor.combo_esquinas
        self.combo_re_esquinas = self.re_editor.combo_esquinas
        self.combo_re_choque = self.re_editor.combo_choque
        self.spin_re_offset = self.re_editor.spin_offset
        self.chk_re_uniforme = self.re_editor.chk_uniforme
        self.btn_all = self.re_editor.btn_all
        self.btn_borde = self.re_editor.btn_borde
        self.btn_borde_frente = self.re_editor.btn_borde["frente"]
        self.btn_borde_fondo = self.re_editor.btn_borde["fondo"]
        self.btn_borde_izquierda = self.re_editor.btn_borde["izquierda"]
        self.btn_borde_derecha = self.re_editor.btn_borde["derecha"]
        self.spin_re_ancho_borde = self.re_editor.spin_ancho_borde
        self.spin_re_offset_borde = self.re_editor.spin_offset_borde
        self.lbl_re_resumen = self.re_editor.lbl_resumen
        self.chk_sync_esquinas = self.re_editor.chk_sync_esquinas
        self.combo_esquina = self.re_editor.combo_esquina
        self.preview_reengrose = self.re_editor.preview

        # Controles legacy ocultos para compatibilidad de API.
        self.combo_re_orientacion = QtGui.QComboBox()
        self.combo_re_orientacion.addItem("Paralela", "paralela")
        self.combo_re_orientacion.addItem("Transversal", "transversal")
        self.combo_re_alineacion = QtGui.QComboBox()
        self.combo_re_alineacion.addItem("Frente", "frente")
        self.combo_re_alineacion.addItem("Centrado", "centrado")
        self.combo_re_alineacion.addItem("Fondo", "fondo")
        self.combo_re_alcance = QtGui.QComboBox()
        self.combo_re_alcance.addItem("Parcial", "parcial")
        self.combo_re_alcance.addItem("Total", "total")
        return self.re_editor

    def _tiene_expresiones(self, obj):
        try:
            return bool(dict(obj.ExpressionEngine or []).get("Largo"))
        except Exception:
            return True

    def _cargar_valores(self, obj):
        self.edit_etiqueta.setText(getattr(obj, "VDO_Etiqueta", ""))
        self.edit_material.setText(
            getattr(obj, "VDO_Material_Ref", "melamina_standar"))
        idx = self.combo_orientacion.findText(
            getattr(obj, "VDO_Orientacion", "horizontal"))
        if idx >= 0:
            self.combo_orientacion.setCurrentIndex(idx)

        for direccion in ["Norte", "Sur", "Este", "Oeste"]:
            valor = getattr(obj, f"VDO_Canto_{direccion}", "FX")
            idx = self.combo_cantos[direccion].findText(valor)
            if idx >= 0:
                self.combo_cantos[direccion].setCurrentIndex(idx)

        self.spin_rotacion.setValue(
            float(getattr(obj, "VDO_RotacionZ", 0.0)))
        anclaje = getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
        for i in range(self.combo_anclaje.count()):
            if self.combo_anclaje.itemData(i) == anclaje:
                self.combo_anclaje.setCurrentIndex(i)
                break

        usar_expr = self._tiene_expresiones(obj)
        self.combo_modo.setCurrentIndex(1 if usar_expr else 0)
        if usar_expr:
            expr_engine = dict(obj.ExpressionEngine or [])
            self.spin_largo.setText(expr_engine.get("Largo", ""))
            self.spin_ancho.setText(expr_engine.get("Ancho", ""))
            self.spin_espesor.setText(expr_engine.get("Espesor", ""))
        else:
            self.spin_largo.setValue(float(getattr(obj, "Largo", 0.0)))
            self.spin_ancho.setValue(float(getattr(obj, "Ancho", 0.0)))
            self.spin_espesor.setValue(float(getattr(obj, "Espesor", 0.0)))

        self._cargar_reengrose(obj)

    @staticmethod
    def _set_combo_data(combo, valor):
        idx = combo.findData(valor)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _leer_reengrose(self):
        return self.re_editor.leer_modificador()

    def _actualizar_resumen_reengrose(self):
        self.re_editor._actualizar_resumen()

    def _on_reengrose_toggled(self, activo):
        self._on_reengrose_modo_changed()

    def _on_reengrose_modo_changed(self, *args):
        self.re_editor._actualizar_estado()

    def _cargar_reengrose(self, obj):
        mod = VDO_RE.desde_objeto(obj)
        self.re_editor.cargar(mod)
        self.re_editor._actualizar_estado()

    def _on_ok(self):
        if self.accept():
            cerrar_dialogo()

    def _on_cancel(self):
        self.reject()
        cerrar_dialogo()

    def accept(self):
        if not self.obj:
            return True
        try:
            self._vdo_begin()

            for spin in (self.spin_re_ancho,
                         self.spin_re_espesor, self.spin_rotacion):
                spin.interpretText()

            self.obj.VDO_Etiqueta = self.edit_etiqueta.text().strip()
            self.obj.VDO_Orientacion = self.combo_orientacion.currentText()
            self.obj.VDO_Material_Ref = self.edit_material.text().strip()

            for direccion in ["Norte", "Sur", "Este", "Oeste"]:
                self.obj.__setattr__(
                    f"VDO_Canto_{direccion}",
                    self.combo_cantos[direccion].currentText())

            if self.combo_modo.currentIndex() == 1:
                for prop, spin in (("Largo", self.spin_largo),
                                   ("Ancho", self.spin_ancho),
                                   ("Espesor", self.spin_espesor)):
                    self.obj.setExpression(prop, spin.value())
            else:
                for prop, spin in (("Largo", self.spin_largo),
                                   ("Ancho", self.spin_ancho),
                                   ("Espesor", self.spin_espesor)):
                    try:
                        self.obj.clearExpression(prop)
                    except Exception:
                        pass
                    setattr(self.obj, prop, spin.value_float())

            mod_reengrose = self._leer_reengrose()
            if mod_reengrose.activo:
                try:
                    VDO_RE.calcular_geometria_reengrose({
                        "nombre": self.obj.Label,
                        "largo": self.spin_largo.value_float(),
                        "ancho": self.spin_ancho.value_float(),
                        "espesor": self.spin_espesor.value_float(),
                    }, mod_reengrose)
                except VDO_RE.ReengroseError as exc:
                    QtGui.QMessageBox.warning(
                        self.form, "Reengrose / Pacha", str(exc))
                    self._vdo_abort()
                    return False
            VDO_RE.aplicar_a_objeto(self.obj, mod_reengrose)

            anclaje = self.combo_anclaje.currentData()
            if anclaje:
                self.obj.VDO_Anclaje = anclaje
            aplicar_rotacion(self.obj, self.spin_rotacion.value())

            App.ActiveDocument.recompute()
            self._vdo_commit()
            self._vdo_aceptado = True
            self._vdo_call_accept()
            return True
        except Exception as exc:
            self._vdo_abort()
            App.Console.PrintError(
                f"[VDO] Error aceptando panel: {exc}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            return False

    def reject(self):
        if getattr(self, "_vdo_aceptado", False):
            return True
        self._vdo_abort()
        self._vdo_call_cancel()
        return True

    def clicked(self, button):
        pass

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def helpRequested(self):
        pass
