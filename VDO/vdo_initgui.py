# -*- coding: utf-8 -*-
# =====================================================================
# VDO/vdo_initgui.py
# Implementacion real del workbench VDO - Carpinteria Parametrica.
#
# POR QUE ESTE MODULO EXISTE:
# FreeCAD ejecuta InitGui.py con exec(code, globals, locals) usando dos
# diccionarios DISTINTOS. Las asignaciones de nivel de modulo caen en
# "locals", pero los metodos de las clases resuelven nombres contra
# "globals" -> cualquier helper definido en InitGui.py es invisible desde
# GetResources()/Activated() y lanza NameError al construirse la toolbar.
# Aqui, al ser un modulo importado normalmente, los globals son correctos.
# =====================================================================

import FreeCAD as App
import FreeCADGui as Gui

from VDO._paths import ICONS_DIR, get_icon_path
from VDO.hub import vdo_hub_registry as REG
from VDO.hub.vdo_hub_registry import SPEC_ESPACIO
from VDO.hub.vdo_hub_schema import aplicar_esquema, aplicar_config

ICONO_WB = "vdo_workbench.svg"


# =====================================================================
# Comandos propios VDO
# =====================================================================

class _CmdBase:
    """Base de los comandos VDO.

    IsActive() devuelve siempre True a proposito: las fabricas VDO llaman a
    vdo_shared_guardian.vdo_guard(), que crea el documento si no hay ninguno. Atar
    IsActive a ActiveDocument dejaba toda la barra deshabilitada al entrar al
    workbench sin documento, de modo que nunca se podia llegar al canvas 3D.
    """

    MenuText = ""
    ToolTip = ""
    Icono = ICONO_WB

    def GetResources(self):
        return {
            "Pixmap": get_icon_path(self.Icono),
            "MenuText": self.MenuText,
            "ToolTip": self.ToolTip,
        }

    def IsActive(self):
        return True

    def Activated(self):
        raise NotImplementedError


def _crear(tipo, configuracion=None):
    """Lanza el flujo crear -> configurar -> colocar -> commit de un modulo.

    Nunca abrir un TaskPanel sin objeto: el accept() de todos los paneles
    empieza con "if not self.obj: return True", de modo que el dialogo se
    cerraria devolviendo OK sin crear nada (era el bug del COCO fantasma).
    """
    try:
        from VDO.ui.vdo_ui_creation_flow import crear_modulo_interactivo
        return crear_modulo_interactivo(tipo, configuracion)
    except Exception:
        import traceback
        App.Console.PrintError(
            "[VDO] No se pudo crear el modulo '%s':\n%s\n"
            % (tipo, traceback.format_exc())
        )
        return None


def _seleccion():
    """Objetos seleccionados en el arbol o el 3D, lista vacia si no hay."""
    try:
        return list(Gui.Selection.getSelection())
    except Exception:
        return []


def _asegurar_canvas():
    """Garantiza un documento con vista 3D al entrar al workbench.

    Seleccionar VDO en el desplegable de bancos de trabajo dejaba al
    usuario atrapado en la pagina de Inicio: FreeCAD cambia de workbench
    pero NO crea documento, asi que no hay vista 3D que activar y la
    pantalla no cambia (comprobado: tras activateWorkbench, ActiveDocument
    sigue siendo None y la unica pestana del MDI es "Inicio").

    Solo se crea documento si no hay NINGUNO abierto; si ya hay uno, se
    respeta y como mucho se le asegura la vista 3D. Abrir FreeCAD con un
    .FCStd no dispara ninguna creacion.
    """
    if not App.GuiUp:
        return None
    try:
        doc = App.ActiveDocument
        if doc is None and not App.listDocuments():
            doc = App.newDocument("VDO")
        if doc is None:
            return None
        vista_doc = Gui.getDocument(doc.Name)
        if vista_doc is None:
            return doc
        if vista_doc.activeView() is None:
            vista_doc.createView("Gui::View3DInventor")
        vista = vista_doc.activeView()
        if vista is not None and hasattr(vista, "viewAxonometric"):
            vista.viewAxonometric()
            Gui.SendMsgToActiveView("ViewFit")
        return doc
    except Exception as exc:
        App.Console.PrintWarning(
            "[VDO] No se pudo preparar la vista 3D: %s\n" % exc)
        return None


def _editar_seleccion():
    """Abre el panel del modulo VDO seleccionado (clic derecho / comando)."""
    try:
        from VDO.cad.views.vdo_cad_view_base import abrir_panel_objeto
    except Exception:
        import traceback
        App.Console.PrintError(
            "[VDO] No se pudo cargar el editor de modulos:\n%s\n"
            % traceback.format_exc())
        return False

    seleccion = _seleccion()
    if not seleccion:
        App.Console.PrintWarning(
            "[VDO] Selecciona primero un modulo VDO en el arbol o en el 3D.\n")
        return False
    return abrir_panel_objeto(seleccion[0])


class CmdNuevoProyecto(_CmdBase):
    MenuText = "Nuevo proyecto VDO"
    ToolTip = "Crea un documento VDO y abre la vista 3D"
    Icono = "vdo_workbench.svg"

    def Activated(self):
        doc = App.newDocument("VDO")
        if App.GuiUp:
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.SendMsgToActiveView("ViewFit")
        App.Console.PrintMessage("[VDO] Proyecto '%s' creado.\n" % doc.Name)


class CmdCrearEspacio(_CmdBase):
    """Crea un VDO_Espacio (contenedor territorial T2)."""

    MenuText = "Crear espacio VDO"
    ToolTip = "Crea un recinto (ej. Cocina) como contenedor de muros y muebles"
    Icono = "vdo_espacio.svg"

    def Activated(self):
        from VDO.cad.objects.vdo_cad_espacio import make_espacio
        from VDO.cad.views.vdo_cad_view_base import abrir_panel_objeto
        obj = make_espacio({"nombre": "ESPACIO_SinNombre"})
        if obj is not None:
            abrir_panel_objeto(obj)


class _CmdEdicionBase(_CmdBase):
    """Base de los comandos que actuan sobre la seleccion.

    Aqui si tiene sentido atar IsActive(): sin seleccion no hay nada que
    editar. Los comandos de creacion siguen siempre activos (ver _CmdBase).
    """

    def IsActive(self):
        return bool(_seleccion())


class CmdCrearModulo(_CmdBase):
    """Comando de creacion generico, parametrizado por una variante.

    SUSTITUYE A SIETE CLASES IDENTICAS. CmdCoco4C, CmdCajon, CmdPuerta,
    CmdZocalo, CmdPanelEstandar, CmdPanelFachada y CmdTambor eran todas
    tres constantes de clase (MenuText, ToolTip, Icono) mas un
    Activated() que llamaba a _crear("<tipo>"). Nada de eso dice algo que
    el catalogo no diga ya, y cada modulo nuevo obligaba a escribir otra
    copia y a acordarse de anadirla a COMANDOS y a TB_MUEBLES.
    """

    VARIANTE = None

    def __init__(self, variante=None):
        if variante is not None:
            self.VARIANTE = variante
        if self.VARIANTE is None:
            raise ValueError("CmdCrearModulo necesita una variante.")
        self.MenuText = self.VARIANTE.menu_text
        self.ToolTip = self.VARIANTE.tooltip
        self.Icono = self.VARIANTE.icono

    def Activated(self):
        _crear(self.VARIANTE.clave)


class CmdDivisionesCOCO(_CmdEdicionBase):
    """Editor de divisiones del COCO seleccionado.

    DivisionesEditor es un QWidget disenado para vivir embebido en la
    pestana "Divisiones" del panel unificado: no tiene accept()/reject()
    y su .form es un QFormLayout, asi que Gui.Control.showDialog() no lo
    acepta. Por eso este comando abre el panel unificado del COCO, que es
    donde vive el editor.

    OJO: no crea nada. Comparte prefijo de nombre con la variante de
    creacion "panel_division" (comando VDO_PanelDivisionNuevo) pero son
    dos cosas distintas.
    """

    MenuText = "Divisiones del modulo"
    ToolTip = "Editar las divisiones del COCO seleccionado"
    Icono = "vdo_panel.svg"

    def Activated(self):
        cocos = [o for o in _seleccion() if hasattr(o, "VDO_Divisiones")]
        if not cocos:
            App.Console.PrintWarning(
                "[VDO] Selecciona un COCO para editar sus divisiones.\n")
            return
        _editar_seleccion()


class CmdEditarVDO(_CmdEdicionBase):
    MenuText = "Propiedades VDO"
    ToolTip = "Abrir el panel del modulo VDO seleccionado"
    Icono = "vdo_herrajes.svg"

    def Activated(self):
        _editar_seleccion()


# =====================================================================
# Registro de comandos y barra: DERIVADOS del catalogo
# =====================================================================
# Antes eran dos listas escritas a mano (COMANDOS y TB_MUEBLES) que habia
# que mantener de acuerdo con las clases Cmd* y con ESPECIFICACIONES.
# Ahora el orden y la composicion los declara vdo_hub_registry, y
# tests/test_contrato_modulos.py comprueba que no divergen.

def _instancias_de_creacion():
    """Una instancia de CmdCrearModulo por variante del catalogo."""
    return {v.comando: CmdCrearModulo(v) for v in REG.variantes_ordenadas()}


_CREACION = _instancias_de_creacion()

_FIJOS = {
    REG.COMANDO_NUEVO_PROYECTO: CmdNuevoProyecto(),
    REG.COMANDO_CREAR_ESPACIO: CmdCrearEspacio(),
    REG.COMANDO_DIVISIONES: CmdDivisionesCOCO(),
    REG.COMANDO_EDITAR: CmdEditarVDO(),
}

# [(nombre, instancia)] en el orden que declara el catalogo.
# ---------------------------------------------------------------------
# CAM (D55): lista de corte, optimizador, nesting y dossier.
# Las importaciones son perezosas: el modulo carga sin GUI (headless).
# ---------------------------------------------------------------------
def _nesting_disponible():
    """El nesting depende del addon externo freecad.nestingworkbench."""
    import importlib.util
    try:
        return importlib.util.find_spec(
            "freecad.nestingworkbench.Tools.Nesting.nesting_logic") is not None
    except (ImportError, ValueError):
        return False


class CmdListaCorte(_CmdBase):
    MenuText = "Lista de corte"
    ToolTip = "Exporta la lista de corte (CSV) con preview visual"
    Icono = "vdo_panel.svg"

    def Activated(self):
        from VDO.cam import vdo_cam_cutlist_preview
        vdo_cam_cutlist_preview.main(modo="todo")


class CmdOptimizador(_CmdBase):
    MenuText = "Optimizador de corte"
    ToolTip = "Distribuye las piezas del CSV en tableros"
    Icono = "vdo_panel_estandar.svg"

    def Activated(self):
        from VDO.cam import vdo_cam_optimizer_dialog
        vdo_cam_optimizer_dialog.main()


class CmdNesting(_CmdBase):
    MenuText = "Nesting"
    ToolTip = "Nesting automatico (requiere el addon Nesting Workbench)"
    Icono = "vdo_panel_estandar.svg"

    def IsActive(self):
        return _nesting_disponible()

    def Activated(self):
        try:
            from VDO.cam import vdo_cam_nesting_workflow
        except ImportError as exc:
            App.Console.PrintError(
                "[VDO] Nesting no disponible: %s\n" % exc)
            return
        vdo_cam_nesting_workflow.main()


class CmdDossier(_CmdBase):
    MenuText = "Generar dossier del espacio"
    ToolTip = "Genera las laminas (planta y fichas) del VDO_Espacio seleccionado"
    Icono = "vdo_proyecto.svg"

    def Activated(self):
        from VDO.cam.vdo_cam_dossier import generar_dossier
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("[VDO] No hay documento activo.\n")
            return
        espacios = [o for o in doc.Objects
                    if getattr(o, "VDO_Tipo", "") == "EspacioFeature"]
        seleccion = [o for o in Gui.Selection.getSelection(doc.Name)
                     if o in espacios]
        espacio = seleccion[0] if seleccion else (
            espacios[0] if len(espacios) == 1 else None)
        if espacio is None:
            App.Console.PrintWarning(
                "[VDO] Selecciona un VDO_Espacio para generar su dossier.\n")
            return
        paginas = generar_dossier(doc, espacio)
        App.Console.PrintMessage(
            "[VDO] Dossier de '%s': %d lamina(s).\n"
            % (espacio.Label, len(paginas)))


class CmdFachadas(_CmdBase):
    """Mostrar u ocultar las fachadas (frentes y puertas) del documento.

    Accion de primera clase: el mismo criterio (VDO_Rol == "fachada" o
    modulo puerta) alimenta las vistas «vanos libres» y «cerrado» del dossier.
    """
    MenuText = "Mostrar / ocultar fachadas"
    ToolTip = "Alterna la visibilidad de todas las fachadas (frentes y puertas)"
    Icono = "vdo_puerta.svg"

    def Activated(self):
        from VDO.shared.vdo_shared_fachadas import alternar_fachadas
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintWarning("[VDO] No hay documento activo.\n")
            return
        n, visibles = alternar_fachadas(doc)
        if n == 0:
            App.Console.PrintMessage("[VDO] No hay fachadas en el documento.\n")
            return
        App.Console.PrintMessage(
            "[VDO] Fachadas (%d): %s\n"
            % (n, "visibles" if visibles else "ocultas"))


COMANDOS_VISTA = [("VDO_Fachadas", CmdFachadas())]


COMANDOS_CAM = [
    ("VDO_ListaCorte", CmdListaCorte()),
    ("VDO_Optimizador", CmdOptimizador()),
    ("VDO_Nesting", CmdNesting()),
    ("VDO_Dossier", CmdDossier()),
]


COMANDOS = [
    (nombre, _CREACION.get(nombre) or _FIJOS[nombre])
    for nombre in REG.nombres_comandos()
]

TB_MUEBLES = list(REG.toolbar_muebles())

# Herramientas BIM/Arch clasicas: espacios y envolvente del local.
# Nombres verificados contra Gui.listCommands() tras importar bimcommands.
TB_BIM = [
    "Arch_Site", "Arch_Building", "Arch_Level", "Arch_Space", "Separator",
    "Arch_Wall", "BIM_Door", "Arch_Window", "Separator",
    "Arch_Structure", "BIM_Column", "BIM_Beam", "BIM_Slab", "Separator",
    "Arch_Stairs", "Arch_Roof",
]

TB_DIBUJO = [
    "Draft_Line", "Draft_Wire", "Draft_Rectangle", "Draft_Circle", "Separator",
    "Draft_Move", "Draft_Rotate", "Draft_Offset", "Draft_Trimex", "Separator",
    "Draft_SelectPlane", "Draft_ToggleGrid",
]

MODULOS_BIM = ("Arch_rc", "DraftTools", "bimcommands")


class VDO_Workbench(Gui.Workbench):
    """Workbench VDO - Carpinteria Parametrica."""

    MenuText = "VDO - Muebles Parametricos"
    ToolTip = "Motor parametrico Veta de Oro: carpinteria y mobiliario"
    Icon = get_icon_path(ICONO_WB)

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        Gui.addIconPath(str(ICONS_DIR))

        self.bim_disponible = True
        for modulo in MODULOS_BIM:
            try:
                __import__(modulo)
            except Exception as exc:
                self.bim_disponible = False
                App.Console.PrintWarning(
                    "[VDO] No se pudo cargar '%s' (%s); las herramientas BIM "
                    "no estaran disponibles.\n" % (modulo, exc)
                )

        self.appendToolbar("VDO Muebles", TB_MUEBLES)
        self.appendMenu("VDO", [n for n, _ in COMANDOS])
        self.appendToolbar("VDO Vista", [n for n, _ in COMANDOS_VISTA])
        self.appendMenu(["VDO", "Vista"], [n for n, _ in COMANDOS_VISTA])
        self.appendToolbar("VDO CAM", [n for n, _ in COMANDOS_CAM])
        self.appendMenu(["VDO", "CAM"], [n for n, _ in COMANDOS_CAM])

        if self.bim_disponible:
            registrados = Gui.listCommands()
            bim = [c for c in TB_BIM if c == "Separator" or c in registrados]
            dibujo = [c for c in TB_DIBUJO if c == "Separator" or c in registrados]
            self.appendToolbar("VDO BIM", bim)
            self.appendToolbar("VDO Dibujo", dibujo)
            self.appendMenu(["VDO", "BIM - Espacios"], [c for c in bim if c != "Separator"])
            self.appendMenu(["VDO", "Dibujo 2D"], [c for c in dibujo if c != "Separator"])

        App.Console.PrintLog("[VDO] Workbench inicializado.\n")

    def Activated(self):
        """Prepara el entorno de trabajo, igual que hace el workbench BIM."""
        try:
            if hasattr(Gui, "draftToolBar"):
                Gui.draftToolBar.Activated()
            if hasattr(Gui, "Snapper"):
                Gui.Snapper.show()
        except Exception as exc:
            App.Console.PrintWarning("[VDO] Entorno Draft no disponible: %s\n" % exc)

        _asegurar_canvas()
        try:
            from VDO.ui.vdo_ui_start_page import instalar_tarjeta_inicio
            instalar_tarjeta_inicio(intentos=0)
        except Exception:
            pass

    def Deactivated(self):
        try:
            if hasattr(Gui, "Snapper"):
                Gui.Snapper.hide()
        except Exception:
            pass

    def ContextMenu(self, recipient):
        self.appendContextMenu("VDO", ["VDO_Editar"])


def register():
    """Registra comandos y workbench. Idempotente."""
    registrados = Gui.listCommands()
    for nombre, comando in COMANDOS:
        if nombre not in registrados:
            # COMANDOS lleva INSTANCIAS, no clases: los comandos de
            # creacion son todos CmdCrearModulo parametrizado con su
            # variante, asi que la instancia es lo que los distingue.
            Gui.addCommand(nombre, comando)
    for nombre, comando in COMANDOS_CAM + COMANDOS_VISTA:
        if nombre not in registrados:
            Gui.addCommand(nombre, comando)
    Gui.addWorkbench(VDO_Workbench())

    # La tarjeta de la pagina de Inicio se pide YA, no en Initialize():
    # Initialize() solo corre cuando el usuario entra al workbench por
    # primera vez, y para entonces la pagina de Inicio lleva un buen rato
    # en pantalla sin nuestra tarjeta. La instalacion se reprograma sola
    # hasta que la pagina existe (se construye al final del arranque).
    try:
        from VDO.ui.vdo_ui_start_page import instalar_tarjeta_inicio
        instalar_tarjeta_inicio()
    except Exception:
        import traceback
        App.Console.PrintLog(
            "[VDO] Pagina de Inicio sin tarjeta VDO:\n%s\n"
            % traceback.format_exc())
