# -*- coding: utf-8 -*-
# =====================================================================
# vdo_ui_panel_task.py
# Task Panel del módulo Panel VDO.
#
# PARTE INFERIDA (de SPEC_PANEL): el grupo VDO (etiqueta, orientación,
# material), los cuatro cantos y la colocación. Etiquetas, dominios de
# enum y tooltips salen del esquema.
#
# PARTE A MANO, Y POR QUÉ:
#   - Las tres cotas usan VDO_ExpressionInput, no un spinbox: un panel
#     puede llevar su largo atado a una expresión nativa de FreeCAD
#     ("= COCO_4C.Ancho - 36 mm"). Eso no es un número y el esquema no
#     lo modela.
#   - El reengrose lo edita ReengroseBorderEditor, un widget con
#     previsualización y edición por borde. Las doce propiedades del
#     bloque siguen declaradas en el esquema (capa de datos), pero su
#     interfaz es diseño, no un formulario plano.
# =====================================================================

from PySide import QtGui

from VDO.ui.vdo_ui_qt_compat import VDO_ExpressionInput
from VDO.ui.vdo_ui_form_builder import VDOPanelGenerico
from VDO.hub.vdo_hub_registry import SPEC_PANEL
from VDO.hub.vdo_hub_module_props import PARAMS_REENGROSE
import VDO.core.vdo_math_reengrose as VDO_RE

# API pública histórica: otros módulos importan estos nombres de aquí.
from VDO.cad.objects.vdo_cad_panel import add_reengrose_props  # noqa: F401

COTAS = ("Largo", "Ancho", "Espesor")


class PanelTaskPanel(VDOPanelGenerico):
    """Configuración de un panel VDO (orientación, cantos, cotas y pose)."""

    SPEC = SPEC_PANEL
    VARIANTE = "panel_estandar"
    TITULO_TX = "Editar panel VDO"

    # Grupos inferidos. "Dimensiones" y "Reengrose" se construyen a mano.
    GRUPOS = ("VDO", "Cantos", "Colocación")
    EXCLUIR = COTAS + tuple(p.nombre for p in PARAMS_REENGROSE)

    # -----------------------------------------------------------------
    def widgets_extra(self):
        return [self._crear_grupo_cotas(), self._crear_grupo_reengrose()]

    # -----------------------------------------------------------------
    def _crear_grupo_cotas(self):
        """Las cotas, con modo directo o expresión nativa de FreeCAD."""
        caja = QtGui.QGroupBox("Dimensiones")
        rejilla = QtGui.QGridLayout(caja)

        self.combo_modo = QtGui.QComboBox()
        self.combo_modo.addItems(["Directo", "Expresión (fórmula)"])
        self.combo_modo.setToolTip(
            "Directo: valor numérico libre. "
            "Expresión (fórmula): expresión nativa de FreeCAD que enlaza "
            "cualquier propiedad del proyecto (p. ej. Params.Largo / 2).")
        rejilla.addWidget(self.combo_modo, 0, 0, 1, 2)

        self.cotas = {}
        for fila, nombre in enumerate(COTAS, start=1):
            p = self.SPEC.param(nombre)
            rejilla.addWidget(QtGui.QLabel(f"{p.titulo} (mm):"), fila, 0)
            entrada = VDO_ExpressionInput(numeric_only=False)
            entrada.setToolTip(p.ayuda)
            rejilla.addWidget(entrada, fila, 1)
            self.cotas[nombre] = entrada

        # Alias históricos: los usan otros paneles y los tests.
        self.spin_largo = self.cotas["Largo"]
        self.spin_ancho = self.cotas["Ancho"]
        self.spin_espesor = self.cotas["Espesor"]
        return caja

    def _crear_grupo_reengrose(self):
        from VDO.ui.vdo_ui_reengrose import ReengroseBorderEditor
        self.re_editor = ReengroseBorderEditor()

        # Alias de los controles del editor. Son API de hecho: los usan
        # tests/test_reengrose_l1.py y otros paneles.
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

        self.re_editor.changed.connect(self._on_reengrose_modo_changed)
        return self.re_editor

    # -----------------------------------------------------------------
    # Alias de compatibilidad sobre los controles inferidos
    # -----------------------------------------------------------------
    @property
    def edit_etiqueta(self):
        return self.controles["VDO_Etiqueta"]

    @property
    def edit_material(self):
        return self.controles["VDO_Material_Ref"]

    @property
    def combo_orientacion(self):
        return self.controles["VDO_Orientacion"]

    @property
    def combo_anclaje(self):
        return self.controles["VDO_Anclaje"]

    @property
    def spin_rotacion(self):
        return self.controles["VDO_RotacionZ"]

    @property
    def combo_cantos(self):
        return {d: self.controles[f"VDO_Canto_{d}"]
                for d in ("Norte", "Sur", "Este", "Oeste")}

    # -----------------------------------------------------------------
    # Carga y escritura de lo que se dibuja a mano
    # -----------------------------------------------------------------
    def tras_cargar(self, obj):
        self.combo_modo.setCurrentIndex(0)
        for nombre, entrada in self.cotas.items():
            entrada.setText(str(float(getattr(obj, nombre, 0.0))))
        self._cargar_reengrose(obj)

    def tras_aplicar(self, obj):
        self._aplicar_cotas(obj)
        self._aplicar_reengrose(obj)

    def _aplicar_cotas(self, obj):
        expresion = self.combo_modo.currentIndex() == 1
        for nombre, entrada in self.cotas.items():
            if expresion:
                obj.setExpression(nombre, entrada.value())
                continue
            try:
                obj.clearExpression(nombre)
            except Exception:
                pass
            setattr(obj, nombre, entrada.value_float())

    def _aplicar_reengrose(self, obj):
        VDO_RE.aplicar_a_objeto(obj, self._leer_reengrose())

    # -----------------------------------------------------------------
    def validar_extra(self, obj):
        """El reengrose se valida con su propio motor.

        Un ancho de tira dentro de rango puede seguir siendo imposible
        sobre este tablero concreto (tira más ancha que el panel, pacha
        total con offset, etc.). Eso lo sabe vdo_math_reengrose.
        """
        mod = self._leer_reengrose()
        if not mod.activo:
            return ()
        try:
            VDO_RE.calcular_geometria_reengrose({
                "nombre": obj.Label,
                "largo": self._cota(obj, "Largo"),
                "ancho": self._cota(obj, "Ancho"),
                "espesor": self._cota(obj, "Espesor"),
            }, mod)
        except VDO_RE.ReengroseError as exc:
            return (str(exc),)
        return ()

    def _cota(self, obj, nombre):
        valor = float(getattr(obj, nombre, 0.0) or 0.0)
        return valor if valor > 0 else self.cotas[nombre].value_float()

    # -----------------------------------------------------------------
    # Compatibilidad: API histórica del editor de reengrose
    # -----------------------------------------------------------------
    def _tiene_expresiones(self, obj):
        try:
            return bool(dict(obj.ExpressionEngine or []).get("Largo"))
        except Exception:
            return True

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
        self.re_editor.cargar(VDO_RE.desde_objeto(obj))
        self.re_editor._actualizar_estado()
