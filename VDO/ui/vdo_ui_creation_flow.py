# -*- coding: utf-8 -*-
# =====================================================================
# VDO/ui/vdo_ui_creation_flow.py
# Flujo de creacion de modulos VDO:  crear -> configurar -> colocar -> commit
#
# POR QUE EXISTE ESTE MODULO:
# Los comandos de la toolbar abrian el Task Panel sin objeto
# (CocoUnifiedTaskPanel(), CajonTaskPanel(), ...) y el accept() de todos
# los paneles empieza con "if not self.obj: return True", de modo que el
# dialogo se cerraba devolviendo OK sin crear nada. Las fabricas
# (make_coco, make_cajon, crear_pieza, ...) existian pero ningun comando
# las llamaba. Este modulo es el eslabon que faltaba.
#
# CICLO (docs/02 §4, con una desviacion deliberada):
#   1. vdo_guard()                -> documento asegurado
#   2. openTransaction(...)       -> todo el gesto es un unico Undo
#   3. fabrica(configuracion)     -> el objeto nace en el origen
#   4. TaskPanel(obj, auto_transaction=False)  -> configurar
#   5. iniciar_colocacion(obj)    -> depositar con el mouse (Esc cancela)
#   6. commitTransaction()        -> un bloque de Undo por modulo creado
#   Cancelar en cualquier paso -> abortTransaction(): el objeto desaparece.
#
# DESVIACION vs docs/02 §4: el documento pide "crear objeto oculto". Aqui
# el objeto nace visible. Motivo: el Patron Hibrido Reactivo (C-03) exige
# feedback 3D en vivo mientras se configura el chasis y las divisiones, y
# un COCO oculto no muestra nada (su Shape es nulo por T5 y la geometria
# vive en los PanelFeature hijos). Se gana el preview y se pierde el
# "no saltar al centro del modelo", que ya resuelve nacer en el origen.
# =====================================================================

import FreeCAD as App

from VDO.shared import vdo_shared_guardian
from VDO.hub import vdo_hub_registry as REG

try:
    import FreeCADGui as Gui
    from PySide import QtCore
except ImportError:  # FreeCADCmd
    Gui = None
    QtCore = None


# =====================================================================
# Registro de modulos creables: DERIVADO del catalogo
# =====================================================================
# Esta era la tercera lista escrita a mano del mismo catalogo (junto a
# vdo_initgui.COMANDOS y vdo_initgui.TB_MUEBLES). Ahora se construye de
# VDO.hub.vdo_hub_registry.VARIANTES, que es la fuente unica.
#
# Se conserva la FORMA del dict —("modulo", "nombre") para fabrica y
# panel— porque es API publica: la usan macros y tools/vdo_audit.py.

def _par(ruta):
    """'paquete.modulo:nombre' -> ('paquete.modulo', 'nombre')."""
    modulo, nombre = ruta.split(":", 1)
    return (modulo, nombre)


def _especificaciones():
    espec = {}
    for clave, variante in REG.VARIANTES.items():
        spec = REG.CATALOGO[variante.modulo]
        espec[clave] = {
            "etiqueta": variante.etiqueta,
            "fabrica": _par(spec.fabrica),
            "panel": _par(spec.panel),
            "config": dict(variante.config),
        }
    return espec


ESPECIFICACIONES = _especificaciones()

# Nombres heredados de las macros de la era Macro/.
ALIAS = dict(REG.ALIAS)



def _resolver(ruta_modulo, nombre):
    modulo = __import__(ruta_modulo, fromlist=[nombre])
    return getattr(modulo, nombre)


def _hay_vista_3d():
    if Gui is None:
        return False
    try:
        return (Gui.ActiveDocument is not None
                and Gui.ActiveDocument.ActiveView is not None)
    except Exception:
        return False


class FlujoCreacion:
    """Orquesta crear -> configurar -> colocar -> commit de un modulo VDO."""

    def __init__(self, tipo, configuracion=None, colocar=True):
        tipo = ALIAS.get(tipo, tipo)
        if tipo not in ESPECIFICACIONES:
            raise ValueError(
                f"Tipo de modulo VDO desconocido: '{tipo}'. "
                f"Disponibles: {', '.join(sorted(ESPECIFICACIONES))}.")
        self.tipo = tipo
        self.spec = ESPECIFICACIONES[tipo]
        self.config = dict(self.spec["config"])
        if configuracion:
            self.config.update(configuracion)
        self.colocar = colocar
        self.doc = None
        self.obj = None
        self.panel = None
        self._tx_abierta = False
        self._cerrado = False

    # -----------------------------------------------------------------
    # Transaccion
    # -----------------------------------------------------------------
    def _abrir_tx(self):
        try:
            self.doc.openTransaction(f"Crear {self.spec['etiqueta']} VDO")
            self._tx_abierta = True
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo abrir transaccion de creacion: {exc}\n")
            self._tx_abierta = False

    def _commit(self):
        if self._cerrado:
            return
        self._cerrado = True
        if self._tx_abierta:
            try:
                self.doc.commitTransaction()
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo confirmar la creacion: {exc}\n")
            self._tx_abierta = False

    def _abortar(self):
        """Cancelacion: la transaccion deshace tambien el addObject."""
        if self._cerrado:
            return
        self._cerrado = True
        nombre = getattr(self.obj, "Name", "?")
        if self._tx_abierta:
            try:
                self.doc.abortTransaction()
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo abortar la creacion: {exc}\n")
            self._tx_abierta = False
        else:
            # Sin transaccion viva hay que retirar el objeto a mano.
            self._borrar_objeto()
        self.obj = None
        App.Console.PrintMessage(
            f"[VDO] Creacion de {self.spec['etiqueta']} cancelada "
            f"({nombre}).\n")

    def _borrar_objeto(self):
        if self.obj is None or self.doc is None:
            return
        try:
            for hijo in list(getattr(self.obj, "Hijos", []) or []):
                if hijo is not None and self.doc.getObject(hijo.Name):
                    self.doc.removeObject(hijo.Name)
            if self.doc.getObject(self.obj.Name):
                self.doc.removeObject(self.obj.Name)
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo retirar el objeto a medio crear: {exc}\n")

    # -----------------------------------------------------------------
    # Paso 1-3: documento, transaccion, fabrica
    # -----------------------------------------------------------------
    def iniciar(self):
        self.doc = vdo_shared_guardian.vdo_guard()
        if self.doc is None:
            App.Console.PrintError(
                "[VDO] No se pudo asegurar un documento activo.\n")
            return None

        self._abrir_tx()

        try:
            fabrica = _resolver(*self.spec["fabrica"])
            self.obj = fabrica(self.config)
        except Exception:
            import traceback
            App.Console.PrintError(
                f"[VDO] Fallo la fabrica de {self.spec['etiqueta']}:\n"
                f"{traceback.format_exc()}\n")
            self._abortar()
            return None

        if self.obj is None:
            App.Console.PrintError(
                f"[VDO] La fabrica de {self.spec['etiqueta']} devolvio None.\n")
            self._abortar()
            return None

        # Sin GUI el flujo termina aqui: objeto creado y confirmado.
        if not App.GuiUp or Gui is None:
            self._commit()
            return self.obj

        if not self._abrir_panel():
            # Sin panel disponible no se pierde el objeto: se coloca igual.
            self.tras_configurar()
        return self.obj

    # -----------------------------------------------------------------
    # Paso 4: Task Panel de configuracion
    # -----------------------------------------------------------------
    def _abrir_panel(self):
        try:
            panel_cls = _resolver(*self.spec["panel"])
        except Exception:
            import traceback
            App.Console.PrintError(
                f"[VDO] No se pudo cargar el panel de "
                f"{self.spec['etiqueta']}:\n{traceback.format_exc()}\n")
            return False

        try:
            # auto_transaction=False: la transaccion es de este flujo, el
            # panel no debe confirmarla ni abortarla por su cuenta.
            self.panel = panel_cls(
                self.obj,
                on_accept=self.tras_configurar,
                on_cancel=self._abortar,
                auto_transaction=False,
            )
        except Exception:
            import traceback
            App.Console.PrintError(
                f"[VDO] No se pudo construir el panel de "
                f"{self.spec['etiqueta']}:\n{traceback.format_exc()}\n")
            return False

        try:
            if Gui.Control.activeDialog():
                Gui.Control.closeDialog()
            Gui.Control.showDialog(self.panel)
            return True
        except Exception:
            import traceback
            App.Console.PrintError(
                f"[VDO] No se pudo mostrar el panel de "
                f"{self.spec['etiqueta']}:\n{traceback.format_exc()}\n")
            return False

    # -----------------------------------------------------------------
    # Paso 5: colocacion con el mouse
    # -----------------------------------------------------------------
    def tras_configurar(self):
        """El panel acepto. Colocar con el mouse y confirmar."""
        if self._cerrado or self.obj is None:
            return
        if not (self.colocar and _hay_vista_3d()):
            self._finalizar()
            return
        try:
            from VDO.cad.objects.vdo_cad_placement import iniciar_colocacion
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] Colocacion interactiva no disponible ({exc}); "
                "el modulo queda en el origen.\n")
            self._finalizar()
            return

        iniciado = iniciar_colocacion(
            self.obj,
            on_done=self._finalizar,
            on_cancel=self._abortar,
        )
        if not iniciado and not self._cerrado:
            # No se pudo arrancar ni Snapper ni el fallback Coin3D.
            self._finalizar()

    # -----------------------------------------------------------------
    # Paso 6: commit
    # -----------------------------------------------------------------
    def _finalizar(self):
        if self._cerrado or self.obj is None:
            return
        nombre = self.obj.Name
        try:
            self.doc.recompute()
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] Recompute final con avisos: {exc}\n")
        self._commit()
        self._seleccionar(nombre)
        App.Console.PrintMessage(
            f"[VDO] {self.spec['etiqueta']} '{nombre}' creado.\n")

    def _seleccionar(self, nombre):
        if Gui is None or not App.GuiUp:
            return
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(self.doc.Name, nombre)
        except Exception:
            pass


# =====================================================================
# API publica
# =====================================================================

def crear_modulo_interactivo(tipo, configuracion=None, colocar=True):
    """Crea un modulo VDO con el ciclo crear -> configurar -> colocar -> commit.

    Args:
        tipo (str): clave de ESPECIFICACIONES ("coco_4c", "cajon", ...).
        configuracion (dict): sobrescribe la configuracion base de creacion.
        colocar (bool): pedir el punto de colocacion con el mouse al aceptar.

    Returns:
        App.DocumentObject | None: el objeto creado (aun sin confirmar si
        el panel esta abierto) o None si la creacion fallo.
    """
    return FlujoCreacion(tipo, configuracion, colocar=colocar).iniciar()


def crear_modulo_directo(tipo, configuracion=None):
    """Crea un modulo sin panel ni colocacion (scripts, tests, headless)."""
    flujo = FlujoCreacion(tipo, configuracion, colocar=False)
    flujo.doc = vdo_shared_guardian.vdo_guard()
    if flujo.doc is None:
        return None
    flujo._abrir_tx()
    try:
        fabrica = _resolver(*flujo.spec["fabrica"])
        flujo.obj = fabrica(flujo.config)
    except Exception:
        import traceback
        App.Console.PrintError(
            f"[VDO] Fallo la fabrica de {flujo.spec['etiqueta']}:\n"
            f"{traceback.format_exc()}\n")
        flujo._abortar()
        return None
    if flujo.obj is None:
        flujo._abortar()
        return None
    flujo._commit()
    return flujo.obj


def tipos_disponibles():
    return sorted(ESPECIFICACIONES)


__all__ = [
    "ESPECIFICACIONES", "FlujoCreacion", "crear_modulo_interactivo",
    "crear_modulo_directo", "tipos_disponibles",
]
