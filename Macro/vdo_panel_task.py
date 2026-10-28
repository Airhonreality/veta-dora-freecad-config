# -*- coding: utf-8 -*-
# =====================================================================
# vdo_panel_task.py
# Panel de configuración del módulo Panel VDO.
# =====================================================================

import FreeCAD as App
from PySide import QtGui

from vdo_qt import VDO_DoubleSpinBox

import vdo_defaults as VDO_D
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_module_props import (
    ANCLAJES, ANCLAJE_DEFAULT, ANCLAJE_LABELS,
    add_common_props, aplicar_rotacion
)
from vdo_panel_core import (
    CANTOS_VALIDOS, add_reengrose_props, aplicar_mapeo_orientacion
)
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

        self.chk_params = QtGui.QCheckBox(
            "Tomar dimensiones de la hoja Params")
        self.chk_params.setToolTip(
            "Si se desmarca, las medidas se editan manualmente y se "
            "eliminan las expresiones paramétricas.")
        grid_dim.addWidget(self.chk_params, 0, 0, 1, 2)

        grid_dim.addWidget(QtGui.QLabel("Largo (mm):"), 1, 0)
        self.spin_largo = VDO_DoubleSpinBox()
        self.spin_largo.setRange(1, 5000)
        self.spin_largo.setDecimals(1)
        self.spin_largo.setSuffix(" mm")
        self.spin_largo.setToolTip(
            "Largo real de la cara del tablero, no la diagonal ni el desarrollo.")
        grid_dim.addWidget(self.spin_largo, 1, 1)

        grid_dim.addWidget(QtGui.QLabel("Ancho (mm):"), 2, 0)
        self.spin_ancho = VDO_DoubleSpinBox()
        self.spin_ancho.setRange(1, 5000)
        self.spin_ancho.setDecimals(1)
        self.spin_ancho.setSuffix(" mm")
        self.spin_ancho.setToolTip(
            "Ancho de la cara del tablero. En un lateral vertical suele ser "
            "la profundidad del mueble.")
        grid_dim.addWidget(self.spin_ancho, 2, 1)

        grid_dim.addWidget(QtGui.QLabel("Espesor (mm):"), 3, 0)
        self.spin_espesor = VDO_DoubleSpinBox()
        self.spin_espesor.setRange(1, 100)
        self.spin_espesor.setDecimals(1)
        self.spin_espesor.setSuffix(" mm")
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

        self.chk_params.toggled.connect(self._on_params_toggled)
        self.chk_reengrose.toggled.connect(self._on_reengrose_toggled)
        self.combo_re_modo.currentIndexChanged.connect(
            self._on_reengrose_modo_changed)
        self.combo_re_alcance.currentIndexChanged.connect(
            self._on_reengrose_modo_changed)
        self.combo_re_orientacion.currentIndexChanged.connect(
            self._on_reengrose_modo_changed)
        return widget

    def _crear_grupo_reengrose(self):
        grupo = QtGui.QGroupBox("Reengrose / Pacha")
        grid = QtGui.QGridLayout(grupo)

        self.chk_reengrose = QtGui.QCheckBox("Activar reengrose")
        self.chk_reengrose.setToolTip(
            "<b>Reengrose / Pacha</b><br>"
            "Activa una tira de refuerzo sobre una cara del tablero. "
            "Ejemplo típico: 70 mm en el nudo de bisagras de una división "
            "central de 18 mm.")
        grid.addWidget(self.chk_reengrose, 0, 0, 1, 4)

        grid.addWidget(QtGui.QLabel("Orientación:"), 1, 0)
        self.combo_re_orientacion = QtGui.QComboBox()
        self.combo_re_orientacion.addItem(
            "Paralela a la pieza", "paralela")
        self.combo_re_orientacion.addItem(
            "Transversal / cruzada", "transversal")
        self.combo_re_orientacion.setToolTip(
            "Paralela: la tira corre a lo largo del panel, como un refuerzo "
            "vertical en un lateral. Transversal: cruza el ancho, como un "
            "tope horizontal o un refuerzo de esquina.")
        grid.addWidget(self.combo_re_orientacion, 1, 1)

        grid.addWidget(QtGui.QLabel("Ancho tira:"), 1, 2)
        self.spin_re_ancho = VDO_DoubleSpinBox()
        self.spin_re_ancho.setRange(1.0, 5000.0)
        self.spin_re_ancho.setDecimals(1)
        self.spin_re_ancho.setSuffix(" mm")
        self.spin_re_ancho.setValue(70.0)
        self.spin_re_ancho.setToolTip(
            "Ancho de la tira. 70 mm es la medida habitual para el nudo de "
            "bisagras; 100 mm se usa para zócalos o refuerzos grandes.")
        grid.addWidget(self.spin_re_ancho, 1, 3)

        grid.addWidget(QtGui.QLabel("Espesor tira:"), 2, 0)
        self.spin_re_espesor = VDO_DoubleSpinBox()
        self.spin_re_espesor.setRange(0.0, 100.0)
        self.spin_re_espesor.setDecimals(1)
        self.spin_re_espesor.setSuffix(" mm")
        self.spin_re_espesor.setSpecialValueText("Auto")
        self.spin_re_espesor.setValue(0.0)
        self.spin_re_espesor.setToolTip(
            "Espesor de la tira. En <b>Auto</b> usa el mismo espesor que el "
            "panel base. Editable para proyectos especiales.")
        grid.addWidget(self.spin_re_espesor, 2, 1)

        grid.addWidget(QtGui.QLabel("Cara:"), 2, 2)
        self.combo_re_cara = QtGui.QComboBox()
        self.combo_re_cara.addItem("Cara A (+)", "cara_a")
        self.combo_re_cara.addItem("Cara B (−)", "cara_b")
        self.combo_re_cara.setToolTip(
            "Cara del tablero donde se pega el refuerzo. En un panel "
            "vertical, una cara mira al vano izquierdo y la otra al derecho.")
        grid.addWidget(self.combo_re_cara, 2, 3)

        grid.addWidget(QtGui.QLabel("Alineación:"), 3, 0)
        self.combo_re_alineacion = QtGui.QComboBox()
        self.combo_re_alineacion.addItem("Frente", "frente")
        self.combo_re_alineacion.addItem("Centrado", "centrado")
        self.combo_re_alineacion.addItem("Fondo", "fondo")
        self.combo_re_alineacion.setToolTip(
            "Posición de la tira sobre la cara: junto al frente de la puerta, "
            "centrada o contra el fondo del mueble.")
        grid.addWidget(self.combo_re_alineacion, 3, 1)

        grid.addWidget(QtGui.QLabel("Fabricación:"), 3, 2)
        self.combo_re_modo = QtGui.QComboBox()
        self.combo_re_modo.addItem("Independiente", "independiente")
        self.combo_re_modo.addItem("Pacha", "pacha")
        self.combo_re_modo.setToolTip(
            "Independiente: la tira se corta y cantea aparte. "
            "Pacha: se pega en bruto y se cantea como un bloque macizo.")
        grid.addWidget(self.combo_re_modo, 3, 3)

        grid.addWidget(QtGui.QLabel("Alcance:"), 4, 0)
        self.combo_re_alcance = QtGui.QComboBox()
        self.combo_re_alcance.addItem("Parcial (tira)", "parcial")
        self.combo_re_alcance.addItem("Total (área completa)", "total")
        self.combo_re_alcance.setToolTip(
            "Parcial: refuerzo en una franja. Total: duplica toda la cara "
            "del panel para lograr un espesor doble.")
        grid.addWidget(self.combo_re_alcance, 4, 1)

        grid.addWidget(QtGui.QLabel("Repisa:"), 4, 2)
        self.combo_re_politica = QtGui.QComboBox()
        self.combo_re_politica.addItem("Retroceder", "retroceder")
        self.combo_re_politica.addItem("Mochear / rebaje", "mochear")
        self.combo_re_politica.setToolTip(
            "Si una repisa choca contra el reengrose: retroceder es un corte "
            "recto a 90°; mochear hace un rebaje en escuadra para abrazarlo.")
        grid.addWidget(self.combo_re_politica, 4, 3)

        self.lbl_re_resumen = QtGui.QLabel("Sin reengrose.")
        self.lbl_re_resumen.setWordWrap(True)
        self.lbl_re_resumen.setStyleSheet(
            "QLabel { background: #f4f4f2; padding: 5px; "
            "border: 1px solid #d0d0d0; }")
        grid.addWidget(self.lbl_re_resumen, 5, 0, 1, 4)
        return grupo

    def _tiene_expresiones(self, obj):
        try:
            return bool(dict(obj.ExpressionEngine or []).get("Largo"))
        except Exception:
            return True

    def _on_params_toggled(self, activo):
        for spin in (self.spin_largo, self.spin_ancho, self.spin_espesor):
            spin.setEnabled(not activo)

    def _cargar_valores(self, obj):
        self.edit_etiqueta.setText(getattr(obj, "VDO_Etiqueta", ""))
        self.edit_material.setText(
            getattr(obj, "VDO_Material_Ref", "melamina_standar"))
        idx = self.combo_orientacion.findText(
            getattr(obj, "VDO_Orientacion", "horizontal"))
        if idx >= 0:
            self.combo_orientacion.setCurrentIndex(idx)

        self.spin_largo.setValue(float(getattr(obj, "Largo", 0.0)))
        self.spin_ancho.setValue(float(getattr(obj, "Ancho", 0.0)))
        self.spin_espesor.setValue(float(getattr(obj, "Espesor", 0.0)))

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

        usar_params = self._tiene_expresiones(obj)
        self.chk_params.setChecked(usar_params)
        self._on_params_toggled(usar_params)
        self._cargar_reengrose(obj)

    @staticmethod
    def _set_combo_data(combo, valor):
        idx = combo.findData(valor)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _leer_reengrose(self):
        espesor = self.spin_re_espesor.value()
        modo = self.combo_re_modo.currentData()
        alcance = (
            self.combo_re_alcance.currentData()
            if modo == "pacha" else "parcial")
        return VDO_RE.ReengroseModifier({
            "activo": self.chk_reengrose.isChecked(),
            "orientacion": self.combo_re_orientacion.currentData(),
            "ancho": self.spin_re_ancho.value(),
            "espesor": espesor if espesor > 0 else None,
            "cara": self.combo_re_cara.currentData(),
            "alineacion_profundidad": self.combo_re_alineacion.currentData(),
            "modo_fabricacion": modo,
            "alcance": alcance,
            "politica_repisa": self.combo_re_politica.currentData(),
        })

    def _actualizar_resumen_reengrose(self):
        if not self.chk_reengrose.isChecked():
            self.lbl_re_resumen.setText("Sin reengrose.")
            return
        try:
            mod = self._leer_reengrose()
            geo = VDO_RE.calcular_geometria_reengrose({
                "nombre": self.edit_etiqueta.text().strip() or "Panel",
                "largo": self.spin_largo.value(),
                "ancho": self.spin_ancho.value(),
                "espesor": self.spin_espesor.value(),
            }, mod)
        except Exception as exc:
            self.lbl_re_resumen.setText(f"⚠ {exc}")
            return

        pieza = geo["refuerzos"][0]
        modo = mod.modo_fabricacion
        alcance = "total" if mod.alcance == "total" else "parcial"
        self.lbl_re_resumen.setText(
            f"{modo.capitalize()} {alcance}: "
            f"{pieza['largo']:.1f} × {pieza['ancho']:.1f} × "
            f"{pieza['espesor']:.1f} mm · cara {mod.cara[-1].upper()} · "
            f"{mod.orientacion}.")

    def _on_reengrose_toggled(self, activo):
        self._on_reengrose_modo_changed()

    def _on_reengrose_modo_changed(self):
        activo = self.chk_reengrose.isChecked()
        es_pacha = self.combo_re_modo.currentData() == "pacha"
        es_total = (
            es_pacha and self.combo_re_alcance.currentData() == "total")
        es_transversal = (
            self.combo_re_orientacion.currentData() == "transversal")
        self.combo_re_alcance.setEnabled(activo and es_pacha)
        self.spin_re_ancho.setEnabled(activo and not es_total)
        self.combo_re_orientacion.setEnabled(activo and not es_total)
        self.combo_re_alineacion.setEnabled(
            activo and not es_total and not es_transversal)
        self.spin_re_espesor.setEnabled(activo)
        self.combo_re_cara.setEnabled(activo)
        self.combo_re_politica.setEnabled(activo)
        self._actualizar_resumen_reengrose()

    def _cargar_reengrose(self, obj):
        mod = VDO_RE.desde_objeto(obj)
        self.chk_reengrose.setChecked(mod.activo)
        self._set_combo_data(
            self.combo_re_orientacion, mod.orientacion)
        self._set_combo_data(self.combo_re_cara, mod.cara)
        self._set_combo_data(
            self.combo_re_alineacion, mod.alineacion_profundidad)
        self._set_combo_data(self.combo_re_modo, mod.modo_fabricacion)
        self._set_combo_data(self.combo_re_alcance, mod.alcance)
        self._set_combo_data(
            self.combo_re_politica, mod.politica_repisa)
        self.spin_re_ancho.setValue(mod.ancho)
        self.spin_re_espesor.setValue(mod.espesor or 0.0)
        self._on_reengrose_modo_changed()

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

            for spin in (self.spin_largo, self.spin_ancho,
                         self.spin_espesor, self.spin_re_ancho,
                         self.spin_re_espesor, self.spin_rotacion):
                spin.interpretText()

            self.obj.VDO_Etiqueta = self.edit_etiqueta.text().strip()
            self.obj.VDO_Orientacion = self.combo_orientacion.currentText()
            self.obj.VDO_Material_Ref = self.edit_material.text().strip()

            for direccion in ["Norte", "Sur", "Este", "Oeste"]:
                self.obj.__setattr__(
                    f"VDO_Canto_{direccion}",
                    self.combo_cantos[direccion].currentText())

            if self.chk_params.isChecked():
                aplicar_mapeo_orientacion(
                    self.obj, self.combo_orientacion.currentText())
            else:
                for prop in ("Largo", "Ancho", "Espesor"):
                    try:
                        self.obj.clearExpression(prop)
                    except Exception:
                        pass
                self.obj.Largo = self.spin_largo.value()
                self.obj.Ancho = self.spin_ancho.value()
                self.obj.Espesor = self.spin_espesor.value()

            mod_reengrose = self._leer_reengrose()
            if mod_reengrose.activo:
                try:
                    VDO_RE.calcular_geometria_reengrose({
                        "nombre": self.obj.Label,
                        "largo": self.spin_largo.value(),
                        "ancho": self.spin_ancho.value(),
                        "espesor": self.spin_espesor.value(),
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
