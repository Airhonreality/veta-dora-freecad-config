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
