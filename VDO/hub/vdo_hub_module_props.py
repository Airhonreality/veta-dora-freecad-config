# -*- coding: utf-8 -*-
# =====================================================================
# vdo_module_props.py
# Propiedades comunes de colocación para todos los módulos VDO.
# - VDO_RotacionZ: rotación alrededor de Z (pose, no geometría).
# - VDO_Anclaje: esquina del módulo que se alinea con el cursor/snap.
#
# Los bloques comunes (pose, retroenlace, reengrose) se declaran aquí UNA
# vez como tuplas de Param y se reutilizan desde vdo_hub_registry. Las
# funciones add_*_props() se conservan como API pública —las llaman los
# TaskPanel y las fábricas— pero ya no repiten los addProperty(): delegan
# en aplicar_params() sobre esas mismas tuplas.
# =====================================================================

# FreeCAD opcional: ver la nota de vdo_hub_schema. Los bloques de Param
# de este modulo son datos y se leen desde el tooling sin FreeCAD.
try:
    import FreeCAD as App
except ImportError:
    App = None

from VDO.core import vdo_math_frames as VDO_FR
import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.hub.vdo_hub_schema import Param, aplicar_params


ANCLAJES = [
    "inferior_izquierda_frente",
    "inferior_derecha_frente",
    "inferior_izquierda_fondo",
    "inferior_derecha_fondo",
    "superior_izquierda_frente",
    "superior_derecha_frente",
    "superior_izquierda_fondo",
    "superior_derecha_fondo",
    "centro_inferior",
]

ANCLAJE_DEFAULT = "inferior_izquierda_frente"

ANCLAJE_LABELS = {
    "inferior_izquierda_frente": "Inferior izquierda (frente)",
    "inferior_derecha_frente": "Inferior derecha (frente)",
    "inferior_izquierda_fondo": "Inferior izquierda (fondo)",
    "inferior_derecha_fondo": "Inferior derecha (fondo)",
    "superior_izquierda_frente": "Superior izquierda (frente)",
    "superior_derecha_frente": "Superior derecha (frente)",
    "superior_izquierda_fondo": "Superior izquierda (fondo)",
    "superior_derecha_fondo": "Superior derecha (fondo)",
    "centro_inferior": "Centro inferior",
}

ANCLAJE_IDS = {label: idx for idx, label in ANCLAJE_LABELS.items()}


# Tipo del retroenlace hijo -> padre.
#
# TIENE QUE SER "Hidden". El padre referencia a sus hijos con
# App::PropertyLinkListChild (Axioma T3), que SI entra en el grafo de
# dependencias: padre depende de hijos. Si el hijo referencia al padre con
# un App::PropertyLink normal, el hijo depende del padre y se cierra un
# ciclo; FreeCAD aborta el orden de recompute con "The graph must be a
# DAG." y deja los objetos "still touched after recompute" (geometria sin
# reconstruir). LinkScopeHidden mantiene el retroenlace utilizable desde
# Python pero fuera del grafo.
PARENT_LINK_TYPE = "App::PropertyLinkHidden"
PARENT_LINK_PROP = "ParentCOCO"


# =====================================================================
# BLOQUE: pose común (rotación + anclaje + exposición)
# =====================================================================
# Lo comparten los seis módulos. `ui=False` en los lados de exposición
# porque no son un control plano: se editan desde el widget de chasis.
PARAMS_POSE = (
    Param("VDO_RotacionZ", "angle", "Colocación",
          etiqueta="Rotación Z",
          ayuda="Rotación del módulo alrededor del eje Z (pose, no geometría)",
          default=0.0, minimo=-360.0, maximo=360.0, decimales=1,
          sufijo=" °", clave_config="rotacion"),
    Param("VDO_Anclaje", "enum", "Colocación",
          etiqueta="Anclaje",
          ayuda="Esquina del módulo que se alinea con el punto de colocación",
          default=ANCLAJE_DEFAULT, opciones=ANCLAJES,
          etiquetas_opciones=ANCLAJE_LABELS, clave_config="anclaje"),
    Param("VDO_Lados_Vistos", "string", "Exposición",
          ayuda="Lados del módulo visibles desde el espacio (JSON)",
          default=lambda: VDO_FR.serializar_lados([VDO_FR.FRENTE]),
          ui=False),
    Param("VDO_Lados_Apoyados", "string", "Exposición",
          ayuda="Lados del módulo apoyados contra muro/piso (JSON)",
          default=lambda: VDO_FR.serializar_lados([VDO_FR.FONDO]),
          ui=False),
)


def _placement_identidad():
    return App.Placement()


# =====================================================================
# BLOQUE: retroenlace al padre + pose relativa
# =====================================================================
# Solo lo llevan los módulos que pueden vivir dentro de un COCO.
# El tipo Hidden es obligatorio: ver la nota de PARENT_LINK_TYPE arriba.
def params_retroenlace(descripcion="COCO padre (vinculación jerárquica)",
                       ayuda_local="Pose relativa al vano del COCO"):
    return (
        Param(PARENT_LINK_PROP, "link_hidden", "VDO",
              ayuda=descripcion, ui=False),
        # Placement perezoso: App.Placement se resuelve al aplicar el
        # esquema, no al declararlo, para que el bloque se pueda leer sin
        # FreeCAD cargado.
        Param("LocalPlacement", "placement", "VDO",
              ayuda=ayuda_local, default=_placement_identidad, ui=False),
    )


# =====================================================================
# BLOQUE: motor de reengrose (pacha / tira de refuerzo)
# =====================================================================
# Vivía en vdo_cad_panel.add_reengrose_props() como once addProperty()
# consecutivos. Sube al hub porque es un bloque de PROPIEDADES, y las
# propiedades son capa de datos: así el registro puede componerlo sin que
# hub tenga que importar cad (que está por encima).
PARAMS_REENGROSE = (
    Param("VDO_Reengrose_Activo", "bool", "Reengrose",
          etiqueta="Activo",
          ayuda="Activa una tira o duplicado de refuerzo sobre el panel",
          default=False),
    Param("VDO_Reengrose_Orientacion", "enum", "Reengrose",
          etiqueta="Orientación",
          ayuda="Paralela al largo del panel o transversal cruzando el ancho",
          default="paralela", opciones=lambda: list(VDO_RE.ORIENTACIONES)),
    Param("VDO_Reengrose_Ancho", "length", "Reengrose",
          etiqueta="Ancho de tira",
          ayuda="Ancho de la tira de refuerzo en mm",
          default=70.0, minimo=0.0, maximo=4000.0, sufijo=" mm"),
    Param("VDO_Reengrose_Espesor", "length", "Reengrose",
          etiqueta="Espesor de tira",
          ayuda="Espesor de la tira; 0 usa el espesor del panel base",
          default=0.0, minimo=0.0, maximo=200.0, sufijo=" mm"),
    Param("VDO_Reengrose_Cara", "enum", "Reengrose",
          etiqueta="Cara",
          ayuda="Cara del tablero donde se adhiere el refuerzo",
          default="cara_a", opciones=lambda: list(VDO_RE.CARAS)),
    Param("VDO_Reengrose_Alineacion", "enum", "Reengrose",
          etiqueta="Alineación",
          ayuda="Posicion de la tira hacia el frente, centro o fondo",
          default="frente", opciones=lambda: list(VDO_RE.ALINEACIONES)),
    Param("VDO_Reengrose_Modo", "enum", "Reengrose",
          etiqueta="Modo",
          ayuda="Tira independiente o pacha encolada y canteada en bloque",
          default="pacha", opciones=lambda: list(VDO_RE.MODOS)),
    Param("VDO_Reengrose_Alcance", "enum", "Reengrose",
          etiqueta="Alcance",
          ayuda="Pacha parcial en tira o pacha total de toda la cara",
          default="parcial", opciones=lambda: list(VDO_RE.ALCANCES)),
    Param("VDO_Reengrose_PoliticaRepisa", "enum", "Reengrose",
          etiqueta="Choque con repisa",
          ayuda="Ante colision con repisa: retroceder o mochear en escuadra",
          default="retroceder",
          opciones=lambda: list(VDO_RE.POLITICAS_REPISA)),
    Param("VDO_Reengrose_PrioridadEncuentro", "enum", "Reengrose",
          etiqueta="Prioridad de encuentro",
          ayuda="Prioridad al cruzar tiras: vertical, horizontal o inglete 45",
          default="vertical_domina",
          opciones=lambda: list(VDO_RE.PRIORIDADES_ENCUENTRO)),
    Param("VDO_Reengrose_ChoqueNucleo", "enum", "Reengrose",
          etiqueta="Choque con núcleo",
          ayuda="Choque contra panel nucleo: retroceso, mocheo o interrumpir tira",
          default="retroceso",
          opciones=lambda: list(VDO_RE.MODOS_CHOQUE_NUCLEO)),
    Param("VDO_Reengrose_JSON", "string", "Reengrose",
          ayuda="Instantanea JSON del modificador de reengrose",
          default="", ui=False),
)


def add_reengrose_props(obj):
    """Añade las propiedades del motor de reengrose. Idempotente."""
    return aplicar_params(obj, PARAMS_REENGROSE)


def add_parent_link(obj, grupo="VDO",
                    descripcion="COCO padre (vinculación jerárquica)"):
    """Añade el retroenlace al padre fuera del grafo de dependencias."""
    if hasattr(obj, PARENT_LINK_PROP):
        return getattr(obj, PARENT_LINK_PROP)
    obj.addProperty(PARENT_LINK_TYPE, PARENT_LINK_PROP, grupo, descripcion)
    return None


def migrar_parent_link(obj):
    """Convierte un ParentCOCO heredado (App::PropertyLink) a Hidden.

    Los documentos guardados antes de este cambio llevan el retroenlace
    dentro del grafo y arrastran el ciclo padre<->hijo. Se llama desde
    onDocumentRestored() de cada módulo.
    """
    if not hasattr(obj, PARENT_LINK_PROP):
        return False
    try:
        if obj.getTypeIdOfProperty(PARENT_LINK_PROP) == PARENT_LINK_TYPE:
            return False
    except Exception:
        return False
    try:
        previo = getattr(obj, PARENT_LINK_PROP)
        obj.removeProperty(PARENT_LINK_PROP)
        obj.addProperty(PARENT_LINK_TYPE, PARENT_LINK_PROP, "VDO",
                        "COCO padre (vinculación jerárquica)")
        if previo is not None:
            setattr(obj, PARENT_LINK_PROP, previo)
        App.Console.PrintLog(
            f"[VDO] {obj.Name}: ParentCOCO migrado a {PARENT_LINK_TYPE}.\n")
        return True
    except Exception as exc:
        App.Console.PrintWarning(
            f"[VDO] No se pudo migrar ParentCOCO de {obj.Name}: {exc}\n")
        return False


def add_common_props(obj):
    """Añade las propiedades de colocación si no existen (idempotente).

    Deriva de PARAMS_POSE: la declaración de estas cuatro propiedades
    (tipo, grupo, ayuda, default) vive ahí y en ningún otro sitio.
    """
    return aplicar_params(obj, PARAMS_POSE)


def leer_rotacion(obj):
    """Devuelve la rotación en grados."""
    try:
        return float(getattr(obj, "VDO_RotacionZ", 0.0))
    except (TypeError, ValueError):
        return 0.0


def rotacion_z(grados):
    """Crea una rotación Z a partir de grados.

    En FreeCAD 1.1.4 el constructor `App.Rotation(axis, angle)` recibe el
    ángulo en GRADOS; `Rotation.Angle` sí devuelve radianes.
    """
    return App.Rotation(App.Vector(0.0, 0.0, 1.0), float(grados))


def aplicar_rotacion(obj, grados):
    """Aplica rotación Z alrededor del anclaje, manteniéndolo fijo."""
    ancla = ancla_local(obj)
    p = obj.Placement
    ancla_global = p.multVec(ancla)
    rot = rotacion_z(grados)
    base = ancla_global - rot.multVec(ancla)
    obj.Placement = App.Placement(base, rot)
    if hasattr(obj, "VDO_RotacionZ"):
        obj.VDO_RotacionZ = float(grados)


def _boundbox_local(obj):
    """BoundBox en coordenadas locales (FreeCAD 1.1 aplica Placement a Shape)."""
    try:
        shape = obj.Shape.copy()
        if shape.isNull():
            return None
        shape.transformShape(obj.Placement.inverse().toMatrix(), True)
        bb = shape.BoundBox
        return bb if bb.isValid() else None
    except Exception:
        return None


def ancla_local(obj, anclaje=None):
    """Devuelve el punto local (Vector) de la esquina de anclaje.

    Convención de ejes:
      X: izquierda (min) / derecha (max)
      Y: frente (min) / fondo (max)
      Z: inferior (min) / superior (max)
    """
    anclaje = anclaje or getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
    bb = _boundbox_local(obj)
    if bb is None:
        xmin = xmax = ymin = ymax = zmin = zmax = 0.0
    else:
        xmin, xmax = bb.XMin, bb.XMax
        ymin, ymax = bb.YMin, bb.YMax
        zmin, zmax = bb.ZMin, bb.ZMax

    izquierda = anclaje.startswith("inferior_izquierda") or anclaje.startswith(
        "superior_izquierda")
    derecha = anclaje.startswith("inferior_derecha") or anclaje.startswith(
        "superior_derecha")
    frente = anclaje.endswith("_frente")
    fondo = anclaje.endswith("_fondo")
    superior = anclaje.startswith("superior_")
    centro_inferior = anclaje == "centro_inferior"

    if centro_inferior:
        return App.Vector((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, zmin)
    return App.Vector(
        xmin if izquierda else (xmax if derecha else (xmin + xmax) / 2.0),
        ymin if frente else (ymax if fondo else (ymin + ymax) / 2.0),
        zmax if superior else zmin,
    )
