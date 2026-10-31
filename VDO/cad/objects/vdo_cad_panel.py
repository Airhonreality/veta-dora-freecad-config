# -*- coding: utf-8 -*-
# =====================================================================
# vdo_panel_core.py
# Motor unificado de paneles VDO — AXIOMA 5: agnóstico de semántica
# Axioma 2: Lógica geométrica pura, sin dependencias de UI
#
# Modela SOLO una pieza física (tablero) con atributos físicos:
#   - orientacion (OBLIGATORIA, vocabulario del manifiesto)
#   - cantos por lado (RIG / FX / SMRG)
#   - material_ref (opcional)
#   - dimensiones/espesor (expresiones paramétricas)
#
# Migrado a Part::FeaturePython para compartir el marco común VDO
# (clic derecho, doble clic, panel de configuración y colocación).
# =====================================================================

import sys
import json

import FreeCAD as App
import Part

# Bootstrap
from VDO._paths import ensure_sys_path
ensure_sys_path()

from VDO.shared import vdo_shared_guardian
import VDO.hub.vdo_hub_defaults as VDO_D
import VDO.hub.vdo_hub_module_props as VDO_MOD
import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.hub.vdo_hub_registry import SPEC_PANEL
from VDO.hub.vdo_hub_schema import aplicar_esquema, aplicar_config
from VDO.cad.objects.vdo_cad_reengrose_solids import forma_ref
from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase

CANTOS_VALIDOS = ("RIG", "FX", "SMRG")


def add_reengrose_props(obj):
    """Anade las propiedades del motor de reengrose a un panel L1.

    Reenvio a VDO.hub.vdo_hub_module_props.PARAMS_REENGROSE, donde ahora
    vive la declaracion de las doce propiedades. Se conserva el nombre
    aqui porque es API publica: lo llaman vdo_ui_panel_task y los tests.
    """
    return VDO_MOD.add_reengrose_props(obj)



def _al_marco_panel(solido, orientacion, espesor):
    """Lleva un sólido del marco canónico del reengrose al del panel.

    vdo_math_reengrose resuelve las tiras en un marco canónico donde
    largo→X, ancho→Y y espesor→Z, que es el del panel HORIZONTAL. Un panel
    vertical se construye con espesor→X, ancho→Y y largo→Z, así que la
    tira calculada caía atravesada: sobre un lateral de 600×400×18 la tira
    aparecía en X=[0,600] Z=[18,36], invadiendo el tablero en 22 680 mm³
    en vez de quedar pegada a su cara (BUG-001 de docs/05, "fallback w/h
    invertido en forma_ref").

    forma_ref() es un constructor tonto y debe seguir siéndolo: la
    orientación la conoce PanelFeature, y aquí se aplica.

    El giro de -90° sobre Y manda (largo, ancho, espesor) a
    (-espesor, ancho, largo); el desplazamiento en X devuelve el tablero
    base a X=[0, espesor] y deja la tira de cara_a adosada a la cara X=0.
    """
    if solido is None or orientacion != "vertical":
        return solido
    try:
        copia = solido.copy()
        copia.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -90)
        copia.translate(App.Vector(espesor, 0, 0))
        return copia
    except Exception as exc:
        App.Console.PrintWarning(
            f"[VDO] No se pudo orientar una tira de reengrose: {exc}\n")
        return solido


def _validar_orientacion(configuracion):
    """Valida de forma estricta la clave 'orientacion'."""
    if "orientacion" not in configuracion:
        raise ValueError(
            "Configuración inválida: falta la clave obligatoria 'orientacion'. "
            "Ningún panel puede crearse sin definir su orientación "
            f"({', '.join(VDO_D.ORIENTACIONES_VALIDAS)}).")

    orientacion = configuracion["orientacion"]
    if orientacion not in VDO_D.ORIENTACIONES_VALIDAS:
        raise ValueError(
            f"Orientación inválida: '{orientacion}'. "
            f"Debe ser una de: {', '.join(VDO_D.ORIENTACIONES_VALIDAS)}.")
    return orientacion


def _limpiar_expresion(obj, prop):
    try:
        obj.clearExpression(prop)
    except Exception:
        pass


def congelar_cotas(obj):
    """Convierte expresiones paramétricas en valores numéricos fijos.

    Se usa antes de desvincular un panel del COCO para que el panel
    desvinculado conserve sus cotas calculadas como valores independientes.
    """
    for prop in ("Largo", "Ancho", "Espesor"):
        try:
            if obj.hasExpression(prop):
                valor_actual = float(getattr(obj, prop))
                obj.clearExpression(prop)
                setattr(obj, prop, valor_actual)
        except Exception:
            pass


def romper_vinculo_padre(obj):
    """Rompe el vínculo ParentCOCO del panel. Devuelve el objeto padre previo."""
    prev = getattr(obj, "ParentCOCO", None)
    try:
        obj.ParentCOCO = None
    except Exception:
        pass
    return prev


_EJES_UNIT = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
              "z": (0.0, 0.0, 1.0)}


def _corte_mocheo(m):
    """Solido a restar de la caja del panel para un mocheo declarado.

    Admite dos formas: caja {x,y,z,w,h,d} (mocheos de divisiones) y prisma
    {puntos, eje, largo} (recortes de tiras en inglete, que no son cajas).
    Devuelve None si el mocheo no es valido.
    """
    if "puntos" in m:
        puntos = [App.Vector(*[float(c) for c in q]) for q in m["puntos"]]
        largo = float(m.get("largo", 0.0))
        eje = _EJES_UNIT.get(m.get("eje", "z"))
        if len(puntos) < 3 or largo <= 0 or eje is None:
            return None
        cara = Part.Face(Part.makePolygon(puntos + [puntos[0]]))
        return cara.extrude(App.Vector(*eje) * largo)
    mw = float(m.get("w", 0.0))
    mh = float(m.get("h", 0.0))
    md = float(m.get("d", 0.0))
    if mw <= 0 or mh <= 0 or md <= 0:
        return None
    return Part.makeBox(mw, mh, md, App.Vector(
        float(m.get("x", 0.0)), float(m.get("y", 0.0)),
        float(m.get("z", 0.0))))


class PanelFeature:
    """FeaturePython que genera la geometría de un tablero VDO."""

    def __init__(self, obj):
        # Las 31 propiedades del panel (dimensiones, los 4 cantos, el
        # bloque de 12 de reengrose, pose y retroenlace) las declara
        # SPEC_PANEL. Antes eran 62 lineas aqui mas las 91 de
        # add_reengrose_props(), que ahora vive en el hub como
        # PARAMS_REENGROSE.
        aplicar_esquema(obj, SPEC_PANEL)
        obj.Proxy = self


    def execute(self, fp):
        try:
            largo = float(fp.Largo)
            ancho = float(fp.Ancho)
            espesor = float(fp.Espesor)
            if largo <= 0 or ancho <= 0 or espesor <= 0:
                fp.Shape = Part.Shape()
                return

            # Convención VDO: espesor siempre en Z (grosor del tablero).
            # Para paneles verticales (laterales, fachadas): X=espesor, Y=fondo, Z=alto
            # Para paneles horizontales (base, techo): X=largo, Y=fondo, Z=espesor
            orientacion = getattr(fp, "VDO_Orientacion", "vertical")
            if orientacion == "vertical":
                base = Part.makeBox(espesor, ancho, largo)
            else:
                base = Part.makeBox(largo, ancho, espesor)

            # Aplicar mocheos/cortes declarados en VDO_Mocheos_JSON (marco local
            # del panel). Cada mocheo es una caja {x,y,z,w,h,d} que se resta del
            # solido base. Esto permite que divisiones con mocheo de reengrose no
            # solapen con tiras de techo/base que las atraviesan.
            try:
                _mocheos_raw = getattr(fp, "VDO_Mocheos_JSON", "") or "[]"
                _mocheos = json.loads(_mocheos_raw) if isinstance(
                    _mocheos_raw, str) else []
            except (ValueError, TypeError):
                _mocheos = []
            for _m in _mocheos:
                try:
                    _corte = _corte_mocheo(_m)
                    if _corte is None:
                        continue
                    if (_corte is not None and not _corte.isNull()
                            and base.BoundBox.intersect(_corte.BoundBox)):
                        base = base.cut(_corte)
                        if base.isNull() or base.Volume <= 1e-9:
                            base = Part.Shape()
                            break
                except Exception:
                    continue

            try:
                mod = VDO_RE.desde_objeto(fp)
                if hasattr(fp, "VDO_Reengrose_JSON"):
                    fp.VDO_Reengrose_JSON = mod.to_json()
                if not mod.activo:
                    fp.Shape = base
                    return
                geo = VDO_RE.calcular_geometria_reengrose(
                    {"nombre": fp.Label or fp.Name,
                     "largo": largo, "ancho": ancho, "espesor": espesor},
                    mod)
                shapes = [base]
                for pieza in geo["refuerzos"]:
                    forma = forma_ref(pieza)
                    if forma is not None:
                        shapes.append(
                            _al_marco_panel(forma, orientacion, espesor))
                fp.Shape = Part.makeCompound(shapes)
            except VDO_RE.ReengroseError as exc:
                App.Console.PrintWarning(
                    f"[VDO] Reengrose ignorado en '{fp.Label}': {exc}\n")
                fp.Shape = base
        except Exception as exc:
            App.Console.PrintError(
                f"[VDO] Error generando panel: {exc}\n")

    def onDelete(self, fp, subelements):
        """Axioma T6: al borrar el panel, salir de la lista Hijos del padre.

        Un panel no tiene hijos propios, pero si queda referenciado en
        ParentCOCO.Hijos el COCO arrastra un enlace muerto y se marca en
        error en el siguiente recompute.
        """
        try:
            padre = getattr(fp, "ParentCOCO", None)
            if padre is not None and hasattr(padre, "Hijos"):
                padre.Hijos = [h for h in (padre.Hijos or [])
                               if h is not None and h.Name != fp.Name]
                rol = getattr(fp, "VDO_Rol", "")
                if rol and hasattr(padre, "Piezas_Omitidas"):
                    omitidas = list(padre.Piezas_Omitidas or [])
                    if rol not in omitidas:
                        padre.Piezas_Omitidas = omitidas + [rol]
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo desregistrar el panel del padre: {exc}\n")
        return True

    def onDocumentRestored(self, fp):
        """Migraciones: esquema al dia + ParentCOCO fuera del grafo.

        aplicar_esquema() sustituye al parche manual de LocalPlacement
        que habia aqui: ya no hay que acordarse de anadir a mano cada
        propiedad nueva, el esquema repone todas las que falten.
        """
        aplicar_esquema(fp, SPEC_PANEL)
        VDO_MOD.migrar_parent_link(fp)

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderPanel(VDOViewProviderBase):
    """ViewProvider del panel VDO."""

    MENU_LABEL = "Propiedades del Panel"
    ICON = "vdo_panel.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_panel_task import PanelTaskPanel
        return PanelTaskPanel

    def setupContextMenu(self, vobj, menu):
        """Menú contextual: propiedades + desvinculación amigable del COCO."""
        try:
            # Acción estándar de propiedades
            action = menu.addAction(self.MENU_LABEL)
            action.triggered.connect(
                lambda checked=False, o=vobj.Object: self._abrir_panel(o))

            # Separador y acción de desvinculación si el panel tiene COCO padre
            menu.addSeparator()
            from VDO.cad.objects.vdo_cad_unlink import (
                _encontrar_coco_padre, vdo_desvincular_pieza)
            doc = App.ActiveDocument
            coco = _encontrar_coco_padre(doc, vobj.Object) if doc else None
            if coco is not None and getattr(vobj.Object, "VDO_Rol", ""):
                action_desv = menu.addAction("Desvincular del COCO")
                action_desv.setToolTip(
                    "Congela cotas, rompe el vínculo con el COCO y registra "
                    "el rol en Piezas_Omitidas para evitar crasheos al recompute.")
                action_desv.triggered.connect(
                    lambda checked=False, o=vobj.Object: vdo_desvincular_pieza(o))
            return False
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo crear el menú contextual del panel: {exc}\n")
            return False


def crear_pieza(configuracion):
    """Función principal del motor de paneles (agnóstica de semántica).

    Args:
        configuracion (dict): {
            "nombre": str,
            "etiqueta": str,      # tag libre, NO dirige geometría
            "orientacion": "horizontal" | "vertical",   # OBLIGATORIO
            "cantos": {"norte": str, "sur": str, "este": str, "oeste": str},
            "material_ref": str,  # opcional
            "largo"/"ancho"/"espesor": float,  # opcional
            "rotacion": float, "anclaje": str  # opcionales
        }

    Returns:
        App.DocumentObject: El panel FeaturePython creado.
    """
    orientacion = _validar_orientacion(configuracion)

    doc = vdo_shared_guardian.vdo_guard()
    if not doc:
        print("❌ [VDO Error] No hay documento activo.")
        return None

    nombre = configuracion.get("nombre", "Panel")
    cantos = configuracion.get("cantos", {})
    etiqueta = configuracion.get("etiqueta", nombre)
    material_ref = configuracion.get(
        "material_ref", "melamina_standar")

    es_nuevo = False
    panel = doc.getObject(nombre)
    if panel is not None and not isinstance(
            getattr(panel, "Proxy", None), PanelFeature):
        if panel.TypeId != "Part::Box":
            raise ValueError(
                f"Ya existe un objeto '{nombre}' ({panel.TypeId}) que no es "
                "un panel VDO. Usa otro nombre.")
        # Migración: un Part::Box viejo no puede tener ViewProvider Python.
        doc.removeObject(panel.Name)
        panel = None

    if panel:
        print(f"⚠️ '{nombre}' ya existe. Actualizando...")
        add_reengrose_props(panel)
    else:
        panel = doc.addObject("Part::FeaturePython", nombre)
        PanelFeature(panel)
        es_nuevo = True

    if App.GuiUp:
        ViewProviderPanel(panel.ViewObject)

    panel.VDO_Orientacion = orientacion
    panel.VDO_Etiqueta = etiqueta
    panel.VDO_Material_Ref = material_ref

    for direccion in ["Norte", "Sur", "Este", "Oeste"]:
        prop_name = f"VDO_Canto_{direccion}"
        canto_value = cantos.get(direccion.lower(), "FX")
        if canto_value not in CANTOS_VALIDOS:
            raise ValueError(
                f"Canto inválido en '{direccion}': '{canto_value}'. "
                f"Debe ser uno de: {', '.join(CANTOS_VALIDOS)}.")
        setattr(panel, prop_name, canto_value)

    # Las cotas pueden venir de una expresión heredada; se limpia antes de
    # escribir un valor literal.
    for prop in ("Largo", "Ancho", "Espesor"):
        _limpiar_expresion(panel, prop)

    # Las tres cotas se reponen a su default si el llamador no las pasa.
    # Es el comportamiento que tenía esta fábrica y lo conserva el camino
    # de "panel ya existente, actualizando"; la diferencia es que el
    # default ahora sale del esquema y no de una copia de las constantes.
    efectiva = {p.clave_de_config: p.valor_inicial()
                for p in SPEC_PANEL.params
                if p.nombre in ("Largo", "Ancho", "Espesor")}
    efectiva.update(configuracion)
    aplicar_config(panel, SPEC_PANEL, efectiva)

    if "reengrose" in configuracion:
        VDO_RE.aplicar_a_objeto(panel, configuracion.get("reengrose"))

    rotacion = float(getattr(panel, "VDO_RotacionZ", 0.0))

    if rotacion:
        panel.Placement = App.Placement(
            panel.Placement.Base, VDO_MOD.rotacion_z(rotacion))
    elif es_nuevo:
        panel.Placement = App.Placement()

    doc.recompute()
    print(f"✅ Panel '{nombre}' configurado: orientacion='{orientacion}'")
    return panel
