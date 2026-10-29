# -*- coding: utf-8 -*-
# =====================================================================
# vdo_qt.py
# Controles Qt con entrada decimal independiente del locale.
# Acepta tanto "850.5" como "850,5" aunque el sistema use coma.
# =====================================================================

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets

_QDoubleSpinBox = getattr(QtWidgets, "QDoubleSpinBox", getattr(QtGui, "QDoubleSpinBox", None))


class VDO_DoubleSpinBox(_QDoubleSpinBox):
    """QDoubleSpinBox que acepta punto/coma y cualquier nº de decimales."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QtCore.QLocale.c())

    def _numero(self, texto):
        limpio = str(texto).replace(",", ".")
        for extra in (self.suffix(), self.prefix()):
            if extra:
                limpio = limpio.replace(extra, "")
        return limpio.strip()

    def validate(self, texto, posicion):
        limpio = self._numero(texto)
        if limpio in ("", "-", "+", "."):
            return (QtGui.QValidator.Intermediate, texto, posicion)
        try:
            float(limpio)
            return (QtGui.QValidator.Acceptable, texto, posicion)
        except ValueError:
            return (QtGui.QValidator.Invalid, texto, posicion)

    def valueFromText(self, texto):
        try:
            return float(self._numero(texto))
        except ValueError:
            return super().valueFromText(self._numero(texto))

    def fixup(self, texto):
        return self._numero(texto)


# ----------------------------------------------------------------------
# Input de expresión nativa de FreeCAD (reemplaza al QDoubleSpinBox "tonto")
# ----------------------------------------------------------------------
class VDO_ExpressionInput(QtWidgets.QWidget):
    """QLineEdit con botón f(x) para expresiones nativas de FreeCAD.

    Acepta tanto números puros ("850.5") como expresiones algebraicas
    ("= Params.Largo / 2", "COCO_4C.Width - 36 mm"). No bloquea nunca el
    input: el usuario elige entre modo directo y modo fórmula.
    """

    def __init__(self, parent=None, numeric_only=False):
        super().__init__(parent)
        self._numeric_only = numeric_only

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self.edit = QtWidgets.QLineEdit()
        self.edit.setPlaceholderText(
            "0.0" if numeric_only else "= Params.Largo / 2")
        self.edit.setToolTip(
            "Valor numérico o expresión nativa de FreeCAD. "
            "Pulsa fx para editar la fórmula.")
        lay.addWidget(self.edit, 1)

        self.btn_fx = QtWidgets.QToolButton()
        self.btn_fx.setText("fx")
        self.btn_fx.setToolTip(
            "Editar expresión nativa de FreeCAD (enlaza cualquier propiedad del proyecto).")
        self.btn_fx.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_fx.clicked.connect(self._on_fx_clicked)
        lay.addWidget(self.btn_fx)

    def _on_fx_clicked(self):
        self.edit.setFocus()

    def setText(self, texto):
        self.edit.setText(str(texto or ""))

    def text(self):
        return self.edit.text().strip()

    def setValue(self, valor):
        self.edit.setText(str(valor))

    def value(self):
        return self.text()

    def value_float(self, default=0.0):
        try:
            limpio = self.value().replace(",", ".")
            return float(limpio)
        except (TypeError, ValueError):
            return default

    def setEnabled(self, enabled):
        self.edit.setEnabled(enabled)
        self.btn_fx.setEnabled(enabled)

    def isEnabled(self):
        return self.edit.isEnabled()

    def setReadOnly(self, ro):
        self.edit.setReadOnly(ro)
