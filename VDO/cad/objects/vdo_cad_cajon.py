# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cajon_core.py
# Motor del cajón con corredera oculta VDO (FeaturePython).
# Trinidad de Cajones v2: geometría paramétrica pura con booleanos.
#
# Tipologías soportadas:
#   CORREDERA_OCULTA   - Blum Tandem / Genérica: notch + pin + piso grueso
#   CORREDERA_TELESCOPICA - Piso delgado 5.5mm en ranura, holgura 12.7mm/lado
#   CAJA_METALICA      - Sin laterales de madera (solo piso + trasera)
#
# Sistemas de apertura (vdo_facade_contract):
#   APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN
#
# Axioma: booleanos generados por prismas en coordenadas calculadas.
# Prohibido indexar caras volátiles (Shape.Faces[n]).
# =====================================================================

import json
import sys

import FreeCAD as App
import Part

from VDO._paths import ensure_sys_path
ensure_sys_path()

from VDO.shared import vdo_shared_guardian
import VDO.hub.vdo_hub_defaults as VDO_D
import VDO.hub.vdo_hub_module_props as VDO_MOD
import VDO.core.vdo_math_frames as VDO_FR
from VDO.core.vdo_math_cajon import (
    calcular_despiece,
    CORREDERA_TELESCOPICA, CORREDERA_OCULTA, CAJA_METALICA,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    necesita_bisel_45, necesita_descuento_gola,
)
# listar_marcas() y los MONTAJE_* los consume SPEC_CAJON, no este archivo.
from VDO.core.vdo_math_facade import BISEL_45_ANGULO_DEFAULT
from VDO.hub.vdo_hub_registry import SPEC_CAJON
from VDO.hub.vdo_hub_schema import (
    aplicar_esquema, aplicar_config, config_desde_objeto)
from VDO.hub.vdo_hub_hardware import resolve_drawer_slide
from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase


# ---------------------------------------------------------------------
# Helpers geométricos puros (coordenadas relativas calculadas)
# ---------------------------------------------------------------------

def _box(pos):
    """Crea un sólido Box desde un dict de posición/dimensiones."""
    return Part.makeBox(
        pos["largo_x"], pos["largo_y"], pos["largo_z"],
        App.Vector(pos["x"], pos["y"], pos["z"]))


def _cilindro(radio, alto, base, direccion):
    """Crea un cilindro para operaciones booleanas."""
    return Part.makeCylinder(radio, alto, base, direccion)


# Sufijo del nombre de pieza -> clave en d["posiciones"].
_ROL_POR_PIEZA = {
    "Lateral_Izq": "lateral_izquierdo",
    "Lateral_Der": "lateral_derecho",
    "Contrafrente": "contra_frente",
    "Frente_Interior": "frente_interior",
    "Piso": "piso",
    "Fachada": "fachada",
}


def _pose_panel(pos):
    """Traduce una caja del despiece a cotas de PanelFeature.

    La aritmetica vive en VDO.core.vdo_math_frames (capa 0) porque el COCO
    necesita exactamente la misma para sus divisiones y repisas.
    """
    return VDO_FR.pose_panel_desde_caja(
        pos["x"], pos["y"], pos["z"],
        pos["largo_x"], pos["largo_y"], pos["largo_z"])


def _enriquecer_piezas_con_pose(paneles, posiciones, etiqueta):
    """Anade rol, pose local y cotas de PanelFeature a cada pieza."""
    for pz in paneles:
        sufijo = pz["nombre"].replace(f"{etiqueta}_", "", 1)
        rol = _ROL_POR_PIEZA.get(sufijo)
        pos = posiciones.get(rol) if rol else None
        if pos is None:
            continue
        pz["rol"] = rol
        pz.update(_pose_panel(pos))


def _aplicar_corte(solido, herramienta):
    """Aplica una sustracción booleana segura."""
    if solido is None or herramienta is None:
        return solido
    try:
        resultado = solido.cut(herramienta)
        if resultado is not None and resultado.isValid():
            return resultado
    except Exception:
        pass
    return solido


def _corte_notch_lateral(solido, pos, notch_ancho, notch_alto, lg):
    """
    Cajeado trasero en lateral: sustrae prisma de notch_ancho (profundidad Y)
    x notch_alto (altura Z) en el talón inferior-trasero.
    """
    caja_notch = Part.makeBox(
        pos["largo_x"],           # X: todo el grosor del lateral
        notch_ancho,              # Y: 35 mm desde el borde trasero
        notch_alto,               # Z: 12 mm desde el borde inferior
        App.Vector(
            pos["x"],
            pos["y"] + lg - notch_ancho,  # Y: desde lg-ancho hasta lg
            pos["z"],
        ),
    )
    return _aplicar_corte(solido, caja_notch)


def _corte_pin_trasero(solido, pos, diam, profundidad, z_piso, g_fondo,
                       alto_contra, ancho_contra, g_caja):
    """
    Taladro para pin de bloqueo en cara posterior del testero trasero.
    Cilindro Ødiam x profundidad mm, partiendo de la cara trasera
    y yendo hacia adelante (-Y).
    """
    cx = pos["x"] + ancho_contra / 2.0
    cy = pos["y"] + pos["largo_y"]       # cara posterior (Y max)
    cz = pos["z"] + alto_contra / 2.0    # centro en Z
    pin = _cilindro(diam / 2.0, profundidad,
                    App.Vector(cx, cy, cz),
                    App.Vector(0, -1, 0))
    return _aplicar_corte(solido, pin)


def _corte_ranura_piso(solido, pos, prof_ranura, z_piso, grosor_piso, lg):
    """
    Ranura perimetral para piso delgado (telescópica).
    Sustrae prisma de prof_ranura (profundidad X) x grosor_piso (altura Z)
    en la cara interna del lateral, a la altura del piso.
    """
    caja_ranura = Part.makeBox(
        prof_ranura,              # X: profundidad de la ranura desde cara interna
        lg,                       # Y: todo el largo del lateral
        grosor_piso,              # Z: grosor del piso
        App.Vector(
            pos["x"] + pos["largo_x"] - prof_ranura,  # X: cara interna
            pos["y"],
            z_piso,               # Z: altura del piso
        ),
    )
    return _aplicar_corte(solido, caja_ranura)


def _aplicar_bisel_45_fachada(solido, pos, ancho, alto, bisel_dist=5.0):
    """
    Bisel paramétrico a 45° en la arista superior frontal de la fachada.
    Crea una cara triangular en el plano Y-Z y la extruye a lo largo de X.
    """
    # Puntos del triángulo a remover (plano Y-Z en la cara frontal):
    #   p1: esquina superior-frente  (y=0, z=alto)
    #   p2: retrasado en cima        (y=-bisel_dist, z=alto)
    #   p3: abajo en cara frontal    (y=0, z=alto-bisel_dist)
    p1 = App.Vector(0, 0, alto)
    p2 = App.Vector(0, -bisel_dist, alto)
    p3 = App.Vector(0, 0, alto - bisel_dist)

    # Part.makePolygon no acepta argumentos por nombre: el cierre se
    # expresa repitiendo el primer punto, como en vdo_cad_divisiones.py y
    # vdo_cad_reengrose_solids.py. Con `closed=True` esta funcion lanzaba
    # TypeError siempre, asi que el bisel a 45 grados nunca se aplicaba a
    # ninguna fachada (solo se nota con APERTURA_45_GRADOS, y el mock de
    # los tests aceptaba el kwarg y tapaba el fallo).
    wire = Part.makePolygon([p1, p2, p3, p1])
    cara = Part.Face(wire)
    herramienta = cara.extrude(App.Vector(ancho, 0, 0))
    herramienta.translate(App.Vector(pos["x"], pos["y"], pos["z"]))

    return _aplicar_corte(solido, herramienta)


# =====================================================================
# CajonFeature
# =====================================================================

class CajonFeature:
    """FeaturePython que genera la geometría de un cajón (Trinidad v2)."""

    PROPS_GEOM_CAJON = frozenset({
        "AnchoLibre", "ProfLibre", "AnchoModulo", "AltoFrente",
        "AltoCaja", "GrosorCaja", "GrosorFondo", "GrosorFachada",
    })

    def __init__(self, obj):
        # Las 26 propiedades del cajon las declara SPEC_CAJON. El dominio
        # del enum MarcaCorredera sale del catalogo de herrajes, no de una
        # lista escrita a mano: anadir una marca al JSON la hace aparecer
        # en el combo sin tocar este archivo.
        aplicar_esquema(obj, SPEC_CAJON)
        obj.Proxy = self


    def _config(self, fp):
        """Construye el dict de entrada para calcular_despiece().

        Las 15 claves que son copia literal de una propiedad las deriva
        config_desde_objeto() de las `clave_motor` del esquema. Aqui solo
        queda lo que es LOGICA y no declaracion: las holguras del
        manifiesto (que no son propiedades del objeto) y las dos cotas que
        la corredera telescopica impone.
        """
        config = config_desde_objeto(fp, SPEC_CAJON)

        config.update({
            "penetracion_ranura": VDO_D.CAJON_PENETRACION_RANURA,
            "eje_ranura": VDO_D.CAJON_EJE_RANURA,
            "holgura_lateral_fachada": VDO_D.CAJON_HOLGURA_LAT_FACHADA,
            "holgura_superior_fachada": VDO_D.CAJON_HOLGURA_SUP_FACHADA,
            "holgura_inferior_fachada": VDO_D.CAJON_HOLGURA_INF_FACHADA,
        })

        # Telescopica: piso de 5.5 mm y eje de ranura a 10 mm. No es
        # configurable, lo fija el herraje.
        if config.get("tipo_corredera") == CORREDERA_TELESCOPICA:
            config["grosor_fondo"] = 5.5
            config["eje_ranura"] = 10.0

        return config

    # -----------------------------------------------------------------
    def execute(self, fp):
        """Reconstruir la geometría del cajón con booleanos limpios."""
        try:
            d = calcular_despiece(self._config(fp))
        except (ValueError, KeyError, TypeError) as e:
            App.Console.PrintError(f"[VDO] Despiece inválido: {e}\n")
            fp.Shape = Part.Shape()
            return

        tipo_corredera = d.get("tipo_corredera", CORREDERA_OCULTA)
        sistema_apertura = d.get("sistema_apertura", APERTURA_TIRADOR)

        caja = d["caja"]
        posiciones = d["posiciones"]
        mecanizados = d["mecanizados"]

        g_caja = caja["grosor"]
        g_fondo = caja["grosor_piso"]
        z_piso = caja["z_piso"]
        lg = caja["largo_lateral"]
        alto_lateral = caja["alto_lateral"]
        ancho_ext = caja["ancho_exterior"]
        ancho_contra = caja["ancho_contra"]
        alto_contra = caja["alto_contra"]

        notch_ancho = float(mecanizados.get("notch_ancho", 35.0))
        notch_alto = float(mecanizados.get("notch_alto", 12.0))
        diam_t = float(mecanizados.get("diam_taladro", 6.0))
        prof_t = float(mecanizados.get("prof_taladro", 10.0))
        prof_ranura = float(mecanizados.get("prof_ranura_lateral", 4.0))

        solids = []

        # -----------------------------------------------------------------
        # 1. Laterales (solo si no es caja metálica)
        # -----------------------------------------------------------------
        if tipo_corredera != CAJA_METALICA:
            for clave in ("lateral_izquierdo", "lateral_derecho"):
                lateral = _box(posiciones[clave])

                if tipo_corredera == CORREDERA_OCULTA:
                    # Notch: 35 x 12 mm en talón inferior-trasero
                    lateral = _corte_notch_lateral(
                        lateral, posiciones[clave],
                        notch_ancho, notch_alto, lg)
                    # Pin de bloqueo en cara posterior del lateral
                    lateral = _corte_pin_trasero(
                        lateral, posiciones[clave],
                        diam_t, prof_t, z_piso, g_fondo,
                        alto_lateral, lg, g_caja)

                elif tipo_corredera == CORREDERA_TELESCOPICA:
                    # Ranura para piso delgado (5.5 mm) en cara interna
                    lateral = _corte_ranura_piso(
                        lateral, posiciones[clave],
                        prof_ranura, z_piso, g_fondo, lg)

                solids.append(lateral)

        # -----------------------------------------------------------------
        # 2. Contra-frente (trasera de madera - siempre presente)
        # -----------------------------------------------------------------
        contra = _box(posiciones["contra_frente"])
        if tipo_corredera == CORREDERA_OCULTA:
            # Notch en esquinas inferiores de la contra-frente
            contra = _corte_notch_lateral(
                contra, posiciones["contra_frente"],
                notch_ancho, notch_alto,
                posiciones["contra_frente"]["largo_y"])
            # Pin de bloqueo en cara posterior del testero trasero
            contra = _corte_pin_trasero(
                contra, posiciones["contra_frente"],
                diam_t, prof_t, z_piso, g_fondo,
                alto_contra, ancho_contra, g_caja)
        solids.append(contra)

        # -----------------------------------------------------------------
        # 3. Frente interior (solo si no es caja metálica)
        # -----------------------------------------------------------------
        if tipo_corredera != CAJA_METALICA:
            solids.append(_box(posiciones["frente_interior"]))

        # -----------------------------------------------------------------
        # 4. Piso
        # -----------------------------------------------------------------
        piso = _box(posiciones["piso"])
        solids.append(piso)

        # -----------------------------------------------------------------
        # 5. Fachada (con integración de contrato universal)
        # -----------------------------------------------------------------
        fachada_pos = posiciones["fachada"]
        fachada_solid = _box(fachada_pos)

        if necesita_bisel_45(sistema_apertura):
            fachada_solid = _aplicar_bisel_45_fachada(
                fachada_solid, fachada_pos,
                fachada["ancho"], fachada["alto"],
                bisel_dist=BISEL_45_ANGULO_DEFAULT / 9.0  # ~5 mm bisel
            )

        solids.append(fachada_solid)

        # -----------------------------------------------------------------
        # Exportación: piezas del despiece
        # -----------------------------------------------------------------
        paneles = json.loads(json.dumps(d["piezas"], ensure_ascii=False))
        if tipo_corredera == CAJA_METALICA:
            # Para caja metálica, no reportar madera en costados
            paneles = [p for p in paneles
                       if p["nombre"] not in ("Cajon_Lateral_Izq",
                                              "Cajon_Lateral_Der")]
        for pz in paneles:
            pz["nombre"] = f"{fp.Label}_{pz['nombre'].replace('Cajon_', '')}"

        # Volcar rol, pose local y mapeo de cotas a PanelFeature.
        # Sin esto, _sincronizar_paneles_hijos() creaba las 6 piezas
        # apiladas en el origen; d["posiciones"] es lo unico que sabe
        # donde va cada una, y solo estaba disponible aqui dentro.
        _enriquecer_piezas_con_pose(paneles, posiciones, fp.Label)

        fp.VDO_Paneles_JSON = json.dumps(paneles, ensure_ascii=False)

        # -----------------------------------------------------------------
        # Resumen legible
        # -----------------------------------------------------------------
        guia = d["guia"]
        fp.VDO_ResumenDespiece = (
            f"Cajón Trinidad v2 ({tipo_corredera})\n"
            f"Guía {guia['marca']}: LG={guia['lg']:.0f} mm "
            f"({'auto' if guia['auto'] else 'manual'}, Δ={guia['delta']:.0f} mm)\n"
            f"Caja ext: {ancho_ext:.0f} x {lg:.0f} x {alto_lateral:.0f} mm "
            f"(G={g_caja:.0f})\n"
            f"Contra-frente: {ancho_contra:.0f} x {alto_contra:.1f} mm "
            f"({caja['montaje_trasera']})\n"
            f"Piso: {caja['ancho_piso']:.0f} x {caja['largo_piso']:.0f} x "
            f"{g_fondo:.0f} mm (z={z_piso:.1f})\n"
            f"Fachada: {d['fachada']['ancho']:.0f} x {d['fachada']['alto']:.0f} x {d['fachada']['espesor']:.0f} mm ({sistema_apertura})\n"
            f"Tipo corredera: {tipo_corredera}"
        )
        for aviso in d["avisos"]:
            App.Console.PrintWarning(f"[VDO] ⚠️ {aviso}\n")

        # Axioma T5: el contenedor no duplica la geometría de sus hijos.
        #
        # MATIZ: T5 existe para evitar DUPLICAR geometría (Z-fighting, doble
        # masa, doble corte en CAM/Nesting). Si el cajón todavía no tiene
        # PanelFeature hijos con volumen, no hay nada que duplicar y poner
        # Shape nula hace que el módulo sea invisible: `solids` se calculaba
        # entero (laterales con notch y pin, contrafrente, piso, fachada con
        # bisel) y se tiraba a la basura en cada recompute.
        # Mientras los hijos no existan, el compuesto ES la única geometría.
        hijos_con_volumen = False
        for hijo in list(getattr(fp, "Hijos", None) or []):
            try:
                if hijo is not None and hijo.Shape.Volume > 1e-6:
                    hijos_con_volumen = True
                    break
            except Exception:
                continue

        if hijos_con_volumen or not solids:
            fp.Shape = Part.Shape()
        else:
            fp.Shape = Part.makeCompound(solids)

        # --- Vínculo rígido padre-hijo ---
        # No escribir fp.Placement aquí: solo CocoFeature.execute() es
        # la fuente de verdad del placement mundial del hijo.
        # LocalPlacement almacena la pose relativa al vano del COCO.
        # Validar que LocalPlacement no contenga NaN.
        lp = fp.LocalPlacement
        base = lp.Base
        if any(
            not isinstance(v, (int, float))
            or v != v  # NaN check
            for v in (base.x, base.y, base.z)
        ):
            fp.LocalPlacement = App.Placement(
                App.Vector(0.0, 0.0, 0.0), App.Rotation())

    # -----------------------------------------------------------------
    def onChanged(self, fp, prop):
        """Propaga la pose y las cotas del cajón a sus piezas (fuera de execute()).

        Igual que CocoFeature.onChanged() y por el mismo motivo (R-03/R-04):
        fuera de execute(), para que mover el mueble recoloque la cadena
        completa al instante y editar AnchoLibre/AltoCaja/etc. re-dimensione
        las PanelFeature hijas sin abrir TaskPanel.
        """
        if prop != "Placement" and prop not in self.PROPS_GEOM_CAJON:
            return
        # La guarda vive en el proxy (self): el DocumentObject de FreeCAD no
        # admite atributos Python arbitrarios aqui y el fallo se tragaba
        # dentro de onChanged, dejando el cajon sin Shape.
        if getattr(self, "_bloqueo_sync", False):
            return
        try:
            self._bloqueo_sync = True
            if prop == "Placement":
                self._propagar_placement(fp)
            elif prop in self.PROPS_GEOM_CAJON:
                self._propagar_dimensiones_hijos(fp)
        finally:
            self._bloqueo_sync = False

    def _propagar_placement(self, fp):
        """hijo.Placement = fp.Placement * hijo.LocalPlacement."""
        try:
            base = fp.Placement
        except Exception:
            return
        for hijo in list(getattr(fp, "Hijos", None) or []):
            local = getattr(hijo, "LocalPlacement", None) if hijo else None
            if local is None:
                continue
            try:
                hijo.Placement = base.multiply(local)
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo reposicionar "
                    f"{getattr(hijo, 'Name', '?')}: {exc}\n")

    def _calcular_cotas_teoricas_cajon(self, fp):
        """Cotas teoricas de cada pieza del cajon en el marco de PanelFeature.

        Re-ejecuta el despiece (matematica pura, sin solidos) y devuelve
        {rol: (panel_largo, panel_ancho, panel_espesor, pos, rot_z)}.
        """
        try:
            config = self._config(fp)
            d = calcular_despiece(config)
        except Exception:
            return {}
        posiciones = d.get("posiciones") or {}
        resultado = {}
        for pz in (d.get("piezas") or []):
            nombre = pz.get("nombre", "")
            sufijo = nombre.replace("Cajon_", "", 1)
            rol = _ROL_POR_PIEZA.get(sufijo)
            if not rol or rol not in posiciones:
                continue
            pos = posiciones[rol]
            try:
                pose = VDO_FR.pose_panel_desde_caja(
                    pos["x"], pos["y"], pos["z"],
                    pos["largo_x"], pos["largo_y"], pos["largo_z"])
            except Exception:
                continue
            resultado[rol] = (
                float(pose["panel_largo"]), float(pose["panel_ancho"]),
                float(pose["panel_espesor"]), pose["pos"], float(pose["rot_z"]))
        return resultado

    def _propagar_dimensiones_hijos(self, fp):
        """Empuja las cotas teoricas del cajon a los PanelFeature hijos existentes.

        Solo actualiza numericos en objetos ya creados: no crea ni destruye.
        Tolerancia 1e-4 para no disparar eventos fantasmas.
        """
        nuevas_piezas = self._calcular_cotas_teoricas_cajon(fp)
        if not nuevas_piezas:
            return
        for hijo in list(getattr(fp, "Hijos", None) or []):
            if hijo is None:
                continue
            rol = getattr(hijo, "VDO_Rol", None)
            if not rol or rol not in nuevas_piezas:
                continue
            nl, na, ne, npos, nrot = nuevas_piezas[rol]
            try:
                if abs(float(getattr(hijo, "Largo", 0) or 0) - nl) > 1e-4:
                    hijo.Largo = nl
                if abs(float(getattr(hijo, "Ancho", 0) or 0) - na) > 1e-4:
                    hijo.Ancho = na
                if abs(float(getattr(hijo, "Espesor", 0) or 0) - ne) > 1e-4:
                    hijo.Espesor = ne
                if npos:
                    local_actual = getattr(hijo, "LocalPlacement", None)
                    base = local_actual.Base if local_actual is not None else None
                    if base is None or (App.Vector(*npos) - base).Length > 1e-4:
                        hijo.LocalPlacement = App.Placement(
                            App.Vector(*npos),
                            App.Rotation(App.Vector(0, 0, 1), nrot))
                        hijo.Placement = fp.Placement.multiply(hijo.LocalPlacement)
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo sincronizar dimensiones del hijo "
                    f"{getattr(hijo, 'Name', '?')}: {exc}\n")

    # -----------------------------------------------------------------
    def onDocumentRestored(self, fp):
        """Migraciones: esquema al dia + ParentCOCO fuera del grafo."""
        aplicar_esquema(fp, SPEC_CAJON)
        VDO_MOD.migrar_parent_link(fp)

    def dumps(self):
        return None

    def loads(self, state):
        return None

    # -----------------------------------------------------------------
    # Borrado en cascada (T6)
    # -----------------------------------------------------------------
    def onDelete(self, fp, subelements):
        """Elimina objetos hijos dependientes al borrar el padre cajón."""
        doc = fp.Document
        if doc is None:
            return True
        hijos = getattr(fp, "Hijos", None) or []
        for hijo in hijos:
            if hijo is not None and doc.getObject(hijo.Name):
                try:
                    doc.removeObject(hijo.Name)
                except Exception:
                    pass
        return True

    # ------------------------------------------------------------------
    # Sincronización de PanelFeature hijos (T2)
    # ------------------------------------------------------------------
    def sincronizar_paneles_hijos(self, fp, doc=None):
        """Crea/actualiza PanelFeature para cada panel del despiece del cajón.

        Los paneles se registran en fp.Hijos (App::PropertyLinkListChild)
        sin crear grupos intermedios (Axioma T2).

        SE LLAMA FUERA DE execute() (Axioma R-04): desde make_cajon() al
        crear y desde CajonTaskPanel.accept() al editar. Antes NADIE la
        llamaba: el cajón calculaba sus 6 piezas, las exportaba a
        VDO_Paneles_JSON y se quedaba con Shape nula por T5, de modo que el
        módulo no producía ninguna geometría visible.
        """
        doc = doc or fp.Document
        try:
            paneles_data = json.loads(fp.VDO_Paneles_JSON or "[]")
        except (TypeError, ValueError):
            paneles_data = []

        hijos_actuales = list(fp.Hijos) if fp.Hijos else []
        nombres_actuales = {h.Name for h in hijos_actuales if h is not None}

        for pz in paneles_data:
            nombre = pz.get("nombre", "")
            if not nombre:
                continue
            panel = doc.getObject(nombre)
            es_nuevo = panel is None
            if es_nuevo:
                panel = doc.addObject("Part::FeaturePython", nombre)
                from VDO.cad.objects.vdo_cad_panel import PanelFeature, ViewProviderPanel
                PanelFeature(panel)
                if App.GuiUp:
                    ViewProviderPanel(panel.ViewObject)

            # panel_* son las cotas en el marco de PanelFeature (ver
            # _pose_panel); largo/ancho/espesor siguen siendo las del
            # despiece para CAM y no se tocan.
            panel.Largo = float(pz.get("panel_largo", pz.get("largo", 0)))
            panel.Ancho = float(pz.get("panel_ancho", pz.get("ancho", 0)))
            panel.Espesor = float(
                pz.get("panel_espesor", pz.get("espesor", 18.0)))
            panel.VDO_Orientacion = pz.get("orientacion", "vertical")
            panel.VDO_Etiqueta = pz.get("nombre", nombre)
            panel.VDO_Material_Ref = pz.get(
                "material_ref", fp.VDO_Material_Ref)
            panel.VDO_Rol = pz.get("rol", "")
            # El padre jerárquico inmediato es el cajón (sub-ensamblaje)
            panel.ParentCOCO = fp

            # Pose dentro del cajón. LocalPlacement es la relativa (la que
            # persiste); Placement se recompone desde la del padre.
            pos = pz.get("pos")
            if pos:
                local = App.Placement(
                    App.Vector(*pos),
                    App.Rotation(App.Vector(0, 0, 1),
                                 float(pz.get("rot_z", 0.0))))
                panel.LocalPlacement = local
                panel.Placement = fp.Placement.multiply(local)

            cantos = pz.get("cantos", {})
            for direccion in ["Norte", "Sur", "Este", "Oeste"]:
                prop_name = f"VDO_Canto_{direccion}"
                valor = cantos.get(direccion.lower(), "FX")
                try:
                    setattr(panel, prop_name, valor)
                except Exception:
                    pass

            if es_nuevo and nombre not in nombres_actuales:
                hijos_actuales.append(panel)

        # Retirar las piezas que el despiece ya no contempla (p. ej. los
        # laterales de madera cuando se pasa a caja metalica).
        vigentes = {pz.get("nombre") for pz in paneles_data}
        conservados = []
        for hijo in hijos_actuales:
            if hijo is None:
                continue
            if hijo.Name in vigentes or not getattr(hijo, "VDO_Rol", ""):
                conservados.append(hijo)
                continue
            try:
                hijo.ParentCOCO = None
                doc.removeObject(hijo.Name)
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo retirar {hijo.Name}: {exc}\n")
                conservados.append(hijo)

        # Registrar hijos en la propiedad de enlace (no en un grupo)
        fp.Hijos = conservados

    # Nombre anterior, conservado para no romper llamadas externas.
    _sincronizar_paneles_hijos = sincronizar_paneles_hijos


class ViewProviderCajon(VDOViewProviderBase):
    """ViewProvider del cajón FeaturePython (Trinidad v2)."""

    MENU_LABEL = "Propiedades del Cajón"
    ICON = "vdo_cajon.svg"

    def __init__(self, vobj):
        super().__init__(vobj)
        try:
            vobj.Visibility = True
        except Exception:
            pass

    def get_panel_class(self):
        from VDO.ui.vdo_ui_cajon_task import CajonTaskPanel
        return CajonTaskPanel

    def claimChildren(self):
        """Retorna los hijos directos del cajón (reflejo de fp.Hijos, T4)."""
        if App.GuiUp is False:
            return []
        obj = self.Object
        if obj is None:
            return []
        hijos = getattr(obj, "Hijos", None) or []
        return [h for h in hijos if h is not None]

    def getIcon(self):
        import os
        if self.ICON:
            from VDO._paths import get_icon_path
            icon_path = get_icon_path(self.ICON)
            if os.path.exists(icon_path):
                return icon_path
        return "Part_Box"


def make_cajon(configuracion):
    """
    Crea un cajón con corredera (FeaturePython, Trinidad v2).
    """
    doc = vdo_shared_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "Cajon_Oculta")
    obj = doc.addObject("Part::FeaturePython", nombre)
    CajonFeature(obj)

    if App.GuiUp:
        ViewProviderCajon(obj.ViewObject)

    aplicar_config(obj, SPEC_CAJON, configuracion)
    # Espejo del herraje activo para la lista de corte. Derivado, no
    # configurable: sigue a MarcaCorredera.
    obj.VDO_Herraje_Ref = obj.MarcaCorredera

    # Vínculo padre-hijo: LocalPlacement y ParentCOCO se establecen aquí.
    # La geometría interna se construye en coordenadas locales del vano
    # dentro de execute(); LocalPlacement lleva la posición relativa al COCO.
    local_placement = configuracion.get("local_placement")
    if local_placement is not None:
        obj.LocalPlacement = local_placement
    parent_coco = configuracion.get("parent_coco")
    if parent_coco is not None:
        obj.ParentCOCO = parent_coco

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] Cajón '{nombre}' creado "
        f"(tipo={obj.TipoCorredera}, marca={obj.MarcaCorredera}, "
        f"LI={float(obj.AnchoLibre):.0f}, ProfLibre={float(obj.ProfLibre):.0f}).\n")

    # Materializar las piezas como PanelFeature hijos, fuera de execute()
    # (Axioma R-04). Sin esta llamada el cajón se quedaba sin geometría:
    # Shape nula por T5 y cero hijos que la llevasen.
    try:
        obj.Proxy.sincronizar_paneles_hijos(obj, doc)
    except Exception as exc:
        App.Console.PrintWarning(
            f"[VDO] Aviso al crear las piezas del cajón: {exc}\n")

    # Segundo recompute: los PanelFeature recién creados generan su B-Rep
    # y el cajón pasa a Shape nula al detectar que ya hay hijos con volumen.
    doc.recompute()
    return obj
