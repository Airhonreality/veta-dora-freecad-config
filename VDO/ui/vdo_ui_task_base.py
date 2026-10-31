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
        """Abre la transacción del panel. Idempotente.

        La idempotencia es necesaria porque ahora se llama de forma
        perezosa en la primera edición en vivo y otra vez en accept(). Sin
        el primer corte, la segunda llamada veía HasPendingTransaction
        (la nuestra) y ponía _vdo_tx_open = False, perdiendo la propiedad
        de la transacción: el commit y el abort se volvían no-ops.
        """
        if not self.auto_transaction:
            return False
        if self._vdo_tx_open:
            return True
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
    # Red de seguridad: panel abierto sin objeto
    # -----------------------------------------------------------------
    def _vdo_asegurar_objeto(self, tipo, configuracion=None):
        """Garantiza que self.obj exista antes de aplicar los valores.

        El camino normal es VDO.ui.vdo_ui_creation_flow, que crea el objeto
        y luego abre el panel. Este metodo cubre cualquier otra via de
        entrada (macro antigua, consola, comando mal cableado) para que
        pulsar "Aceptar" no vuelva a ser un no-op silencioso: antes, todos
        los accept() empezaban con `if not self.obj: return True` y el
        dialogo se cerraba devolviendo OK sin crear nada.

        Devuelve True si hay objeto utilizable.
        """
        if getattr(self, "obj", None) is not None:
            return True
        try:
            from VDO.ui.vdo_ui_creation_flow import crear_modulo_directo
            obj = crear_modulo_directo(tipo, configuracion)
        except Exception:
            import traceback
            App.Console.PrintError(
                "[VDO] No se pudo crear el modulo '%s' desde el panel:\n%s\n"
                % (tipo, traceback.format_exc()))
            return False
        if obj is None:
            App.Console.PrintError(
                f"[VDO] El panel no pudo crear el modulo '{tipo}'.\n")
            return False

        self.obj = obj
        # Hook opcional: el panel anade las propiedades que normalmente
        # inyecta en __init__ cuando recibe un objeto.
        preparar = getattr(self, "_vdo_preparar_objeto", None)
        if callable(preparar):
            try:
                preparar(obj)
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] Aviso preparando '{obj.Name}': {exc}\n")
        return True

    # -----------------------------------------------------------------
    # Callbacks de flujo
    # -----------------------------------------------------------------
    def _vdo_call_accept(self):
        if self._vdo_on_accept:
            QtCore.QTimer.singleShot(0, self._vdo_on_accept)

    def _vdo_call_cancel(self):
        if self._vdo_on_cancel:
            QtCore.QTimer.singleShot(0, self._vdo_on_cancel)
