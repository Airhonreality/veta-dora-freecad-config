# -*- coding: utf-8 -*-
# =====================================================================
# vdo_ui_form_builder.py
# UI inferida: construye el formulario de un modulo desde su esquema.
#
# QUE SUSTITUYE
# Cada TaskPanel repetia tres bloques mecanicos:
#   _crear_widget()   -> QLabel + control + setRange + setSuffix + tooltip
#   _cargar_valores() -> if hasattr(obj, "X"): spin_x.setValue(float(obj.X))
#   accept()          -> self.obj.X = self.spin_x.value()
# Eran ~200 lineas por panel que no decian nada que el esquema no diga ya,
# y donde vivian en exclusiva los rangos validos: el limite 1..400 mm de
# AltoZocalo solo existia dentro de un setRange(), asi que editar la
# propiedad desde el editor de FreeCAD o una macro no validaba nada.
#
# QUE NO SUSTITUYE, A PROPOSITO
# Los paneles del COCO (1509 lineas) y de divisiones (1741) llevan
# editores de arbol, arrastrar y soltar y previsualizacion 2D. Eso no se
# infiere ni debe inferirse. VDOPanelGenerico deja el gancho
# `widgets_extra()` para injertar esos controles junto a los generados:
# la UI inferida cubre lo plano y se aparta donde hay diseno de verdad.
# =====================================================================

import FreeCAD as App

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # PySide6 / PySide2
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets

from VDO.ui.vdo_ui_qt_compat import VDO_DoubleSpinBox
from VDO.ui.vdo_ui_task_base import VDOTransactionMixin, cerrar_dialogo
from VDO.hub.vdo_hub_module_props import aplicar_rotacion
from VDO.hub.vdo_hub_schema import Param, ModuloSpec, validar


# =====================================================================
# Un Param -> un control Qt
# =====================================================================

def crear_control(p: Param, parent=None):
    """Instancia el control Qt que corresponde al tipo declarado.

    Rango, decimales, sufijo y tooltip salen todos del Param: no hay
    ningun numero magico en esta funcion.
    """
    if p.tipo == "bool":
        w = QtWidgets.QCheckBox(p.titulo, parent)
        w.setToolTip(p.ayuda)
        return w

    if p.tipo == "enum":
        w = QtWidgets.QComboBox(parent)
        for valor in p.valores():
            # El valor canonico va en itemData; la etiqueta legible, a la
            # vista. Asi el combo nunca escribe en la propiedad un texto
            # traducido en vez del valor del dominio.
            w.addItem(p.etiqueta_de(valor), valor)
        w.setToolTip(p.ayuda)
        return w

    if p.tipo == "string":
        w = QtWidgets.QLineEdit(parent)
        w.setToolTip(p.ayuda)
        if p.solo_lectura:
            w.setReadOnly(True)
        return w

    if p.tipo == "int":
        w = QtWidgets.QSpinBox(parent)
        w.setRange(int(p.minimo if p.minimo is not None else -2 ** 31),
                   int(p.maximo if p.maximo is not None else 2 ** 31 - 1))
        if p.sufijo:
            w.setSuffix(p.sufijo)
        w.setToolTip(p.ayuda)
        return w

    # length / angle / float
    w = VDO_DoubleSpinBox(parent)
    w.setRange(float(p.minimo if p.minimo is not None else -1e9),
               float(p.maximo if p.maximo is not None else 1e9))
    w.setDecimals(int(p.decimales))
    if p.sufijo:
        w.setSuffix(p.sufijo)
    if p.tipo == "angle":
        w.setWrapping(True)
    w.setToolTip(p.ayuda)
    if p.solo_lectura:
        w.setReadOnly(True)
    return w


def leer_control(p: Param, w):
    """Valor del control, ya en el tipo de la propiedad."""
    if p.tipo == "bool":
        return bool(w.isChecked())
    if p.tipo == "enum":
        dato = w.currentData()
        return dato if dato is not None else w.currentText()
    if p.tipo == "string":
        return w.text().strip()
    if p.tipo == "int":
        w.interpretText()
        return int(w.value())
    w.interpretText()
    return float(w.value())


def escribir_control(p: Param, w, valor):
    """Lleva el valor de la propiedad al control."""
    if p.tipo == "bool":
        w.setChecked(bool(valor))
        return
    if p.tipo == "enum":
        idx = w.findData(str(valor))
        if idx >= 0:
            w.setCurrentIndex(idx)
        return
    if p.tipo == "string":
        w.setText(str(valor or ""))
        return
    if p.tipo == "int":
        w.setValue(int(valor))
        return
    w.setValue(float(valor))


def senal_de_cambio(p: Param, w):
    """Senal "el usuario ha tocado esto", para refrescar cabeceras."""
    if p.tipo == "bool":
        return w.toggled
    if p.tipo == "enum":
        return w.currentIndexChanged
    if p.tipo == "string":
        return w.textChanged
    return w.valueChanged


# =====================================================================
# Un ModuloSpec -> un formulario completo
# =====================================================================

def construir_formulario(spec: ModuloSpec, parent=None, grupos=None,
                         excluir=()):
    """Crea un QWidget con un QGroupBox por grupo declarado.

    Args:
        spec: el esquema del modulo.
        grupos: subconjunto de grupos a construir, en ese orden. None =
            todos, en el orden de aparicion en el esquema.
        excluir: nombres de propiedad a omitir (las que el panel dibuja
            a mano con un control especializado).

    Returns:
        (widget, controles) donde controles es {nombre_propiedad: QWidget}.
    """
    widget = QtWidgets.QWidget(parent)
    layout = QtWidgets.QVBoxLayout(widget)
    controles = {}

    for grupo in (grupos if grupos is not None else spec.grupos()):
        params = [p for p in spec.params_de(grupo) if p.nombre not in excluir]
        if not params:
            continue
        caja = QtWidgets.QGroupBox(grupo, widget)
        rejilla = QtWidgets.QGridLayout(caja)
        fila = 0
        for p in params:
            control = crear_control(p, caja)
            if p.tipo == "bool" or p.ancho_completo:
                # El checkbox ya lleva su propio texto: no necesita label.
                rejilla.addWidget(control, fila, 0, 1, 2)
            else:
                rejilla.addWidget(
                    QtWidgets.QLabel(f"{p.titulo}:", caja), fila, 0)
                rejilla.addWidget(control, fila, 1)
            controles[p.nombre] = control
            fila += 1
        layout.addWidget(caja)

    return widget, controles


def cargar_valores(obj, spec: ModuloSpec, controles):
    """Objeto -> controles. Sustituye a los _cargar_valores() a mano."""
    for nombre, w in controles.items():
        p = spec.param(nombre)
        if p is None or not hasattr(obj, nombre):
            continue
        try:
            escribir_control(p, w, _valor_plano(obj, p))
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo mostrar {nombre}: {exc}\n")


def _valor_plano(obj, p: Param):
    valor = getattr(obj, p.nombre)
    if p.tipo in ("length", "angle", "float"):
        return float(valor)
    if p.tipo == "int":
        return int(valor)
    return valor


def aplicar_valores(obj, spec: ModuloSpec, controles, omitir=()):
    """Controles -> objeto. Sustituye al bloque de asignaciones de accept().

    La rotacion se escribe con aplicar_rotacion(), que mantiene el punto
    de anclaje fijo; asignar VDO_RotacionZ a secas giraria el modulo
    alrededor del origen del documento.
    """
    for nombre, w in controles.items():
        if nombre in omitir:
            continue
        p = spec.param(nombre)
        if p is None or p.solo_lectura or not hasattr(obj, nombre):
            continue
        if nombre == "VDO_RotacionZ":
            continue
        setattr(obj, nombre, leer_control(p, w))

    if "VDO_Anclaje" in controles and hasattr(obj, "VDO_Anclaje"):
        anclaje = controles["VDO_Anclaje"].currentData()
        if anclaje:
            obj.VDO_Anclaje = anclaje
    if "VDO_RotacionZ" in controles and hasattr(obj, "VDO_RotacionZ"):
        p = spec.param("VDO_RotacionZ")
        aplicar_rotacion(obj, leer_control(p, controles["VDO_RotacionZ"]))


def valores_de_controles(spec: ModuloSpec, controles):
    """Lee los controles sin tocar el objeto (para validar antes)."""
    valores = {}
    for nombre, w in controles.items():
        p = spec.param(nombre)
        if p is None:
            continue
        try:
            valores[nombre] = leer_control(p, w)
        except Exception:
            pass
    return valores


# =====================================================================
# Panel de tareas generico
# =====================================================================

class VDOPanelGenerico(VDOTransactionMixin):
    """TaskPanel construido a partir de un ModuloSpec.

    Un panel concreto solo declara SPEC y, si hace falta, sobreescribe
    los ganchos. Todo lo demas —formulario, carga, validacion, escritura,
    transaccion, botones— lo aporta esta clase.

    Ganchos disponibles:
        widgets_extra()       widgets propios, se insertan tras los grupos
        tras_cargar(obj)      despues de volcar el objeto a los controles
        tras_aplicar(obj)     despues de escribir los controles al objeto
        al_cambiar()          cualquier control editado (refrescar cabecera)
        validar_extra(obj)    validaciones que el esquema no expresa
    """

    SPEC = None                  # ModuloSpec (obligatorio)
    VARIANTE = None              # clave de variante para crear si falta objeto
    TITULO_TX = "Editar módulo VDO"
    GRUPOS = None                # subconjunto/orden de grupos; None = todos
    EXCLUIR = ()                 # propiedades que dibuja el panel a mano

    def __init__(self, obj=None, on_accept=None, on_cancel=None,
                 auto_transaction=True):
        if self.SPEC is None:
            raise NotImplementedError(
                f"{type(self).__name__} debe declarar SPEC.")
        self.obj = obj
        self.controles = {}
        self._vdo_aceptado = False
        self._init_vdo_task(
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=auto_transaction,
            transaction_name=self.TITULO_TX,
        )
        self.form = self._crear_widget()
        if obj:
            self._vdo_preparar_objeto(obj)
            self._cargar_valores(obj)

    # -----------------------------------------------------------------
    # Ganchos (vacios por defecto)
    # -----------------------------------------------------------------
    def widgets_extra(self):
        return []

    def tras_cargar(self, obj):
        pass

    def tras_aplicar(self, obj):
        pass

    def al_cambiar(self):
        pass

    def validar_extra(self, obj):
        return ()

    # -----------------------------------------------------------------
    # Construccion
    # -----------------------------------------------------------------
    def _crear_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        for extra in self.widgets_extra():
            if extra is not None:
                layout.addWidget(extra)

        cuerpo, self.controles = construir_formulario(
            self.SPEC, widget, grupos=self.GRUPOS, excluir=self.EXCLUIR)
        cuerpo.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(cuerpo)
        layout.addStretch()

        layout.addWidget(self._crear_botones())

        for nombre, control in self.controles.items():
            p = self.SPEC.param(nombre)
            try:
                senal_de_cambio(p, control).connect(self._on_cambio)
            except Exception:
                pass

        return widget

    def _crear_botones(self):
        botones = QtWidgets.QDialogButtonBox()
        btn_ok = botones.addButton(
            "Aplicar" if self.auto_transaction else "Crear y colocar",
            QtWidgets.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtWidgets.QDialogButtonBox.RejectRole)
        btn_ok.setToolTip("Guarda los cambios y recalcula la geometría.")
        btn_cancelar.setToolTip("Cierra sin aplicar los cambios.")
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        return botones

    def _on_cambio(self, *_args):
        try:
            self.al_cambiar()
        except Exception as exc:
            App.Console.PrintWarning(f"[VDO] Aviso al refrescar: {exc}\n")

    # -----------------------------------------------------------------
    # Objeto <-> controles
    # -----------------------------------------------------------------
    def _vdo_preparar_objeto(self, obj):
        """El esquema repone lo que falte (objeto viejo o recien creado)."""
        from VDO.hub.vdo_hub_schema import aplicar_esquema
        aplicar_esquema(obj, self.SPEC)

    def _cargar_valores(self, obj):
        cargar_valores(obj, self.SPEC, self.controles)
        self.tras_cargar(obj)
        self._on_cambio()

    # -----------------------------------------------------------------
    # Aceptar / cancelar
    # -----------------------------------------------------------------
    def _on_ok(self):
        if self.accept():
            cerrar_dialogo()

    def _on_cancel(self):
        self.reject()
        cerrar_dialogo()

    def accept(self):
        variante = self.VARIANTE or self.SPEC.tipo
        if not self._vdo_asegurar_objeto(variante):
            return True
        try:
            self._vdo_begin()
            aplicar_valores(self.obj, self.SPEC, self.controles)

            # La validacion corre sobre el OBJETO ya escrito, con las
            # cotas del esquema. Antes esto no existia: el unico control
            # era el setRange() del spinbox.
            errores = tuple(validar(self.obj, self.SPEC))
            errores += tuple(self.validar_extra(self.obj) or ())
            if errores:
                self._vdo_abort()
                QtWidgets.QMessageBox.warning(
                    self.form, self.SPEC.etiqueta, "\n".join(errores))
                return False

            self.tras_aplicar(self.obj)
            App.ActiveDocument.recompute()
            self._vdo_commit()
            self._vdo_aceptado = True
            self._vdo_call_accept()
            return True
        except Exception as exc:
            self._vdo_abort()
            App.Console.PrintError(
                f"[VDO] Error aceptando {self.SPEC.etiqueta}: {exc}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            return False

    def reject(self):
        if getattr(self, "_vdo_aceptado", False):
            return True
        self._vdo_abort()
        self._vdo_call_cancel()
        return True

    # -----------------------------------------------------------------
    # Protocolo de Gui.Control
    # -----------------------------------------------------------------
    def clicked(self, button):
        pass

    def getStandardButtons(self):
        return (QtGui.QDialogButtonBox.Ok
                | QtGui.QDialogButtonBox.Cancel)

    def helpRequested(self):
        pass


__all__ = [
    "crear_control", "leer_control", "escribir_control", "senal_de_cambio",
    "construir_formulario", "cargar_valores", "aplicar_valores",
    "valores_de_controles", "VDOPanelGenerico",
]
