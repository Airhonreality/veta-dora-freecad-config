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

_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import vdo_guardian
import vdo_defaults as VDO_D
import vdo_module_props as VDO_MOD
from vdo_cajon_despiece import (
    calcular_despiece, listar_marcas,
    CORREDERA_TELESCOPICA, CORREDERA_OCULTA, CAJA_METALICA,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    necesita_bisel_45, necesita_descuento_gola,
)
from vdo_facade_contract import BISEL_45_ANGULO_DEFAULT
from vdo_hardware_hub import resolve_drawer_slide
from vdo_view_base import VDOViewProviderBase


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

    wire = Part.makePolygon([p1, p2, p3], closed=True)
    cara = Part.Face(wire)
    herramienta = cara.extrude(App.Vector(ancho, 0, 0))
    herramienta.translate(App.Vector(pos["x"], pos["y"], pos["z"]))

    return _aplicar_corte(solido, herramienta)


# =====================================================================
# CajonFeature
# =====================================================================

class CajonFeature:
    """FeaturePython que genera la geometría de un cajón (Trinidad v2)."""

    def __init__(self, obj):
        # === ENTRADA: espacio interior ===
        obj.addProperty("App::PropertyLength", "AnchoLibre", "Dimensiones",
                        "Ancho libre interior del mueble LI (mm)"
                        ).AnchoLibre = 564.0
        obj.addProperty("App::PropertyLength", "ProfLibre", "Dimensiones",
                        "Profundidad libre interior del mueble (mm)"
                        ).ProfLibre = 560.0
        obj.addProperty("App::PropertyLength", "AnchoModulo", "Dimensiones",
                        "Ancho total del módulo (para la fachada, mm)"
                        ).AnchoModulo = 600.0
        obj.addProperty("App::PropertyLength", "AltoFrente", "Dimensiones",
                        "Alto total asignado a la fachada (mm)"
                        ).AltoFrente = 225.0

        # === CAJA ===
        obj.addProperty("App::PropertyLength", "AltoCaja", "Caja",
                        "Alto de los laterales de la caja (85/120/150)"
                        ).AltoCaja = VDO_D.CAJON_ALTO_DEFAULT
        obj.addProperty("App::PropertyLength", "GrosorCaja", "Caja",
                        "Espesor del tablero de la caja (15/16 mm)"
                        ).GrosorCaja = VDO_D.CAJON_GROSOR_DEFAULT
        obj.addProperty("App::PropertyLength", "GrosorFondo", "Caja",
                        "Espesor del piso del cajón (6/12 mm)"
                        ).GrosorFondo = VDO_D.CAJON_FONDO_DEFAULT
        obj.addProperty("App::PropertyLength", "GrosorFachada", "Fachada",
                        "Espesor de la fachada decorativa (18 mm)"
                        ).GrosorFachada = VDO_D.CAJON_FACHADA_DEFAULT

        # === HERRAJE (corredera) ===
        marcas = listar_marcas()
        obj.addProperty("App::PropertyEnumeration", "MarcaCorredera",
                        "Herraje", "Marca de corredera oculta (delta y cotas)"
                        ).MarcaCorredera = marcas
        obj.MarcaCorredera = "blum_tandem" if "blum_tandem" in marcas else marcas[0]
        obj.addProperty("App::PropertyLength", "LongitudGuia", "Herraje",
                        "Largo nominal de la guía (0 = auto según ProfLibre)"
                        ).LongitudGuia = 0.0
        obj.addProperty("App::PropertyEnumeration", "MontajeTrasera",
                        "Herraje", "Montaje de la contra-frente"
                        ).MontajeTrasera = ["entre_laterales", "testa"]
        obj.MontajeTrasera = "entre_laterales"

        # === TIPOLOGÍA DE CORREDERA ===
        obj.addProperty("App::PropertyEnumeration", "TipoCorredera",
                        "Herraje",
                        "Tipo de corredera: oculta / telescópica / metálica"
                        ).TipoCorredera = [
                            CORREDERA_OCULTA, CORREDERA_TELESCOPICA, CAJA_METALICA]
        obj.TipoCorredera = CORREDERA_OCULTA

        # === SISTEMA DE APERTURA (fachada) ===
        obj.addProperty("App::PropertyEnumeration", "SistemaApertura",
                        "Fachada",
                        "Sistema de apertura del frente del cajón"
                        ).SistemaApertura = [
                            APERTURA_TIRADOR, APERTURA_GOLA,
                            APERTURA_45_GRADOS, APERTURA_PUSH_OPEN]
        obj.SistemaApertura = APERTURA_TIRADOR

        # === PROPIEDADES DE EXPORTACIÓN (cutting list) ===
        obj.addProperty("App::PropertyString", "VDO_Tipo", "VDO",
                        "Tipo de objeto").VDO_Tipo = "contenedor"
        obj.addProperty("App::PropertyString", "VDO_Subtipo", "VDO",
                        "Subtipo").VDO_Subtipo = "cajon_oculta"
        obj.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO",
                        "Material de las piezas"
                        ).VDO_Material_Ref = "melamina_standar"
        obj.addProperty("App::PropertyString", "VDO_Herraje_Ref", "VDO",
                        "Herraje de corredera oculta"
                        ).VDO_Herraje_Ref = obj.MarcaCorredera
        obj.addProperty("App::PropertyString", "VDO_Paneles_JSON", "VDO",
                        "Descripción JSON de las piezas del despiece")
        obj.addProperty("App::PropertyString", "VDO_ResumenDespiece", "VDO",
                        "Resumen legible del despiece (solo lectura)")

        # Pose común VDO (rotación + anclaje). No altera la geometría.
        VDO_MOD.add_common_props(obj)

        # Vínculo padre-hijo (kinematics de Placement)
        obj.addProperty("App::PropertyLink", "ParentCOCO", "VDO",
                        "Módulo COCO padre")
        obj.addProperty("App::PropertyPlacement", "LocalPlacement", "VDO",
                        "Pose relativa al vano del COCO").LocalPlacement = App.Placement()

        obj.Proxy = self

    # -----------------------------------------------------------------
    def _config(self, fp):
        """Construye el dict de entrada para calcular_despiece()."""
        # Para telescópica: grosor de piso 5.5 mm y eje de ranura a 10 mm
        grosor_fondo = float(fp.GrosorFondo)
        eje_ranura = VDO_D.CAJON_EJE_RANURA
        if fp.TipoCorredera == CORREDERA_TELESCOPICA:
            grosor_fondo = 5.5
            eje_ranura = 10.0

        return {
            "ancho_libre": float(fp.AnchoLibre),
            "prof_libre": float(fp.ProfLibre),
            "ancho_modulo": float(fp.AnchoModulo),
            "alto_frente": float(fp.AltoFrente),
            "marca": fp.MarcaCorredera,
            "alto_caja": float(fp.AltoCaja),
            "grosor_caja": float(fp.GrosorCaja),
            "grosor_fondo": grosor_fondo,
            "grosor_fachada": float(fp.GrosorFachada),
            "longitud_guia": float(fp.LongitudGuia),
            "montaje_trasera": fp.MontajeTrasera,
            "tipo_corredera": fp.TipoCorredera,
            "sistema_apertura": fp.SistemaApertura,
            "penetracion_ranura": VDO_D.CAJON_PENETRACION_RANURA,
            "eje_ranura": eje_ranura,
            "holgura_lateral_fachada": VDO_D.CAJON_HOLGURA_LAT_FACHADA,
            "holgura_superior_fachada": VDO_D.CAJON_HOLGURA_SUP_FACHADA,
            "holgura_inferior_fachada": VDO_D.CAJON_HOLGURA_INF_FACHADA,
            "material_ref": fp.VDO_Material_Ref,
        }

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
    def dumps(self):
        return None

    def loads(self, state):
        return None


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
        from vdo_cajon_task import CajonTaskPanel
        return CajonTaskPanel


def make_cajon(configuracion):
    """
    Crea un cajón con corredera (FeaturePython, Trinidad v2).
    """
    doc = vdo_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "Cajon_Oculta")
    obj = doc.addObject("Part::FeaturePython", nombre)
    CajonFeature(obj)

    if App.GuiUp:
        ViewProviderCajon(obj.ViewObject)

    obj.AnchoLibre = configuracion.get("ancho_libre", 564.0)
    obj.ProfLibre = configuracion.get("prof_libre", 560.0)
    obj.AnchoModulo = configuracion.get("ancho_modulo", 600.0)
    obj.AltoFrente = configuracion.get("alto_frente", 225.0)
    obj.AltoCaja = configuracion.get("alto_caja", VDO_D.CAJON_ALTO_DEFAULT)
    obj.GrosorCaja = configuracion.get("grosor_caja", VDO_D.CAJON_GROSOR_DEFAULT)
    obj.GrosorFondo = configuracion.get("grosor_fondo", VDO_D.CAJON_FONDO_DEFAULT)
    obj.GrosorFachada = configuracion.get("grosor_fachada", VDO_D.CAJON_FACHADA_DEFAULT)
    obj.MarcaCorredera = configuracion.get("marca", "blum_tandem")
    obj.LongitudGuia = configuracion.get("longitud_guia", 0.0)
    obj.MontajeTrasera = configuracion.get("montaje_trasera", "entre_laterales")
    obj.TipoCorredera = configuracion.get("tipo_corredera", CORREDERA_OCULTA)
    obj.SistemaApertura = configuracion.get("sistema_apertura", APERTURA_TIRADOR)
    if "material_ref" in configuracion:
        obj.VDO_Material_Ref = configuracion["material_ref"]
    obj.VDO_Herraje_Ref = obj.MarcaCorredera
    rotacion = float(configuracion.get("rotacion", 0.0))
    obj.VDO_RotacionZ = rotacion
    obj.VDO_Anclaje = configuracion.get(
        "anclaje", VDO_MOD.ANCLAJE_DEFAULT)

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
    return obj
