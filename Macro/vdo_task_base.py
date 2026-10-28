# -*- coding: utf-8 -*-
# =====================================================================
# vdo_task_base.py
# Utilidades comunes para Task Panels VDO.
# - Gestión de transacciones con propiedad explícita.
# - Callbacks on_accept / on_cancel para el flujo de creación.
# - Cierre seguro del diálogo.
# =====================================================================

import FreeCAD as App
from PySide import QtCore


def cerrar_dialogo():
    """Cierra el Task Panel activo sin asumir que estamos en modo edición."""
    try:
        import FreeCADGui as Gui
        Gui.Control.closeDialog()
    except Exception:
        pass


class VDOTransactionMixin:
    """Mixin para Task Panels VDO.

    Reglas:
    - `auto_transaction=True`: el panel abre y confirma su propia
      transacción (edición normal).
    - `auto_transaction=False`: la transacción la gestiona un flujo
      externo (creación de módulo). El panel nunca confirma ni aborta.
    """

    def _init_vdo_task(self, on_accept=None, on_cancel=None,
                       auto_transaction=True,
                       transaction_name="Editar módulo VDO"):
        self._vdo_on_accept = on_accept
        self._vdo_on_cancel = on_cancel
        self.auto_transaction = auto_transaction
        self.transaction_name = transaction_name
        self._vdo_tx_open = False

    # -----------------------------------------------------------------
    # Transacciones
    # -----------------------------------------------------------------
    def _vdo_begin(self):
        if not self.auto_transaction:
            return False
        doc = App.ActiveDocument
        if doc is None:
            return False
        if doc.HasPendingTransaction:
            # No abrimos una transacción si ya hay una ajena en curso.
            self._vdo_tx_open = False
            return False
        try:
            doc.openTransaction(self.transaction_name)
            self._vdo_tx_open = True
            return True
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo abrir transacción: {exc}\n")
            self._vdo_tx_open = False
            return False

    def _vdo_commit(self):
        if not self.auto_transaction or not self._vdo_tx_open:
            return
        doc = App.ActiveDocument
        try:
            if doc is not None:
                doc.commitTransaction()
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo confirmar transacción: {exc}\n")
        finally:
            self._vdo_tx_open = False

    def _vdo_abort(self):
        if not self.auto_transaction or not self._vdo_tx_open:
            return
        doc = App.ActiveDocument
        try:
            if doc is not None:
                doc.abortTransaction()
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo abortar transacción: {exc}\n")
        finally:
            self._vdo_tx_open = False

    # -----------------------------------------------------------------
    # Callbacks de flujo
    # -----------------------------------------------------------------
    def _vdo_call_accept(self):
        if self._vdo_on_accept:
            QtCore.QTimer.singleShot(0, self._vdo_on_accept)

    def _vdo_call_cancel(self):
        if self._vdo_on_cancel:
            QtCore.QTimer.singleShot(0, self._vdo_on_cancel)
