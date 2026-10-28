# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cajon_core.py
# Motor del cajón con corredera oculta VDO (FeaturePython)
# Axioma 2: geometría paramétrica pura, sin UI
# Las fórmulas de despiece viven en vdo_cajon_despiece.py
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
from vdo_cajon_despiece import calcular_despiece, listar_marcas
from vdo_view_base import VDOViewProviderBase


class CajonFeature:
    """FeaturePython que genera la geometría de un cajón con corredera oculta."""

    def __init__(self, obj):
        # === ENTRADA: espacio interior (datos de partida) ===
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

        # === FACHADA ===
        obj.addProperty("App::PropertyLength", "GrosorFachada", "Fachada",
                        "Espesor de la fachada decorativa (18 mm)"
                        ).GrosorFachada = VDO_D.CAJON_FACHADA_DEFAULT

        # === HERRAJE (corredera oculta) ===
        marcas = listar_marcas()
        obj.addProperty("App::PropertyEnumeration", "MarcaCorredera",
                        "Herraje",
                        "Marca de corredera oculta (delta y cotas)"
                        ).MarcaCorredera = marcas
        obj.MarcaCorredera = "blum_tandem" if "blum_tandem" in marcas else marcas[0]
        obj.addProperty("App::PropertyLength", "LongitudGuia", "Herraje",
                        "Largo nominal de la guía (0 = auto según ProfLibre)"
                        ).LongitudGuia = 0.0
        obj.addProperty("App::PropertyEnumeration", "MontajeTrasera", "Herraje",
                        "Montaje de la contra-frente"
                        ).MontajeTrasera = ["entre_laterales", "testa"]
        obj.MontajeTrasera = "entre_laterales"

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
                        ).VDO_Herraje_Ref = "blum_tandem"
        obj.addProperty("App::PropertyString", "VDO_Paneles_JSON", "VDO",
                        "Descripción JSON de las 6 piezas del despiece")
        obj.addProperty("App::PropertyString", "VDO_ResumenDespiece", "VDO",
                        "Resumen legible del despiece (solo lectura)")

        # Pose común VDO (rotación + anclaje). No altera la geometría.
        VDO_MOD.add_common_props(obj)

        obj.Proxy = self

    # -----------------------------------------------------------------
    def _config(self, fp):
        """Construye el dict de entrada para calcular_despiece()."""
        return {
            "ancho_libre": float(fp.AnchoLibre),
            "prof_libre": float(fp.ProfLibre),
            "ancho_modulo": float(fp.AnchoModulo),
            "alto_frente": float(fp.AltoFrente),
            "marca": fp.MarcaCorredera,
            "alto_caja": float(fp.AltoCaja),
            "grosor_caja": float(fp.GrosorCaja),
            "grosor_fondo": float(fp.GrosorFondo),
            "grosor_fachada": float(fp.GrosorFachada),
            "longitud_guia": float(fp.LongitudGuia),
            "montaje_trasera": fp.MontajeTrasera,
            "penetracion_ranura": VDO_D.CAJON_PENETRACION_RANURA,
            "eje_ranura": VDO_D.CAJON_EJE_RANURA,
            "holgura_lateral_fachada": VDO_D.CAJON_HOLGURA_LAT_FACHADA,
            "holgura_superior_fachada": VDO_D.CAJON_HOLGURA_SUP_FACHADA,
            "holgura_inferior_fachada": VDO_D.CAJON_HOLGURA_INF_FACHADA,
            "material_ref": fp.VDO_Material_Ref,
        }

    # -----------------------------------------------------------------
    def execute(self, fp):
        """Reconstruir la geometría del cajón."""
        try:
            d = calcular_despiece(self._config(fp))
        except ValueError as e:
            App.Console.PrintError(f"[VDO] Despiece inválido: {e}\n")
            return

        pos = d["posiciones"]
        caja = d["caja"]
        g_caja = caja["grosor"]
        g_fondo = caja["grosor_piso"]
        z_piso = caja["z_piso"]
        mec = d["mecanizados"]
        prof_ranura = mec["prof_ranura_lateral"]
        diam_t = mec["diam_taladro"]
        prof_t = mec["prof_taladro"]
        dist_t = mec["dist_taladro_borde_trasero"]
        notch_ancho = mec["notch_ancho"]
        notch_alto = mec["notch_alto"]
        lg = caja["largo_lateral"]

        def _box(p):
            return Part.makeBox(p["largo_x"], p["largo_y"], p["largo_z"],
                                App.Vector(p["x"], p["y"], p["z"]))

        solids = []

        # --- Laterales con ranura de piso + taladros de fondo ---
        for clave in ("lateral_izquierdo", "lateral_derecho"):
            p = pos[clave]
            lateral = _box(p)

            # Ranura longitudinal en la cara interna (ancho = Gfondo,
            # profundidad = prof_ranura, base en z_piso)
            es_izq = clave == "lateral_izquierdo"
            if es_izq:
                ranura = Part.makeBox(
                    prof_ranura, lg, g_fondo,
                    App.Vector(p["x"] + g_caja - prof_ranura, 0.0, z_piso))
            else:
                ranura = Part.makeBox(
                    prof_ranura, lg, g_fondo,
                    App.Vector(p["x"], 0.0, z_piso))
            lateral = lateral.cut(ranura)

            # Taladros verticales desde la cara inferior (pin guía trasero)
            y_t = lg - dist_t
            taladro = Part.makeCylinder(
                diam_t / 2.0, prof_t,
                App.Vector(p["x"] + g_caja / 2.0, y_t, 0.0),
                App.Vector(0, 0, 1))
            lateral = lateral.cut(taladro)

            solids.append(lateral)

        # --- Contra-frente con notch inferior en ambos extremos ---
        p_cf = pos["contra_frente"]
        contra = _box(p_cf)
        # Notch en esquina inferior izquierda
        contra = contra.cut(Part.makeBox(
            notch_ancho, p_cf["largo_y"], notch_alto,
            App.Vector(p_cf["x"], p_cf["y"], p_cf["z"])))
        # Notch en esquina inferior derecha
        contra = contra.cut(Part.makeBox(
            notch_ancho, p_cf["largo_y"], notch_alto,
            App.Vector(p_cf["x"] + p_cf["largo_x"] - notch_ancho,
                       p_cf["y"], p_cf["z"])))
        solids.append(contra)

        # --- Frente interior ---
        solids.append(_box(pos["frente_interior"]))

        # --- Piso ---
        solids.append(_box(pos["piso"]))

        # --- Fachada ---
        solids.append(_box(pos["fachada"]))

        # === Exportación: piezas del despiece ===
        # Nombres locales para el JSON (sin prefijo del grupo)
        paneles = json.loads(json.dumps(d["piezas"], ensure_ascii=False))
        for pz in paneles:
            pz["nombre"] = f"{fp.Label}_{pz['nombre'].replace('Cajon_', '')}"
        fp.VDO_Paneles_JSON = json.dumps(paneles, ensure_ascii=False)

        # === Resumen legible ===
        guia = d["guia"]
        fp.VDO_ResumenDespiece = (
            f"Guía {guia['marca']}: LG={guia['lg']:.0f} mm "
            f"({'auto' if guia['auto'] else 'manual'}, Δ={guia['delta']:.0f})\n"
            f"Caja ext: {caja['ancho_exterior']:.0f} x {lg:.0f} x "
            f"{caja['alto_lateral']:.0f} mm (G={g_caja:.0f})\n"
            f"Contra-frente: {caja['ancho_contra']:.0f} x "
            f"{caja['alto_contra']:.1f} mm ({caja['montaje_trasera']})\n"
            f"Piso: {caja['ancho_piso']:.0f} x {caja['largo_piso']:.0f} x "
            f"{g_fondo:.0f} mm (z={z_piso:.1f})\n"
            f"Fachada: {d['fachada']['ancho']:.0f} x "
            f"{d['fachada']['alto']:.0f} x {d['fachada']['espesor']:.0f} mm"
        )
        for aviso in d["avisos"]:
            App.Console.PrintWarning(f"[VDO] ⚠️ {aviso}\n")

        fp.Shape = Part.makeCompound(solids)

    # -----------------------------------------------------------------
    def dumps(self):
        return None

    def loads(self, state):
        return None



class ViewProviderCajon(VDOViewProviderBase):
    """ViewProvider del cajón FeaturePython."""

    MENU_LABEL = "Propiedades del Cajón"
    ICON = "vdo_cajon.svg"

    def get_panel_class(self):
        from vdo_cajon_task import CajonTaskPanel
        return CajonTaskPanel


def make_cajon(configuracion):
    """
    Crea un cajón con corredera oculta (FeaturePython).

    Args:
        configuracion (dict): ver CajonTaskPanel / vdo_cajon_oculta.FCMacro.
            Claves: ancho_libre, prof_libre, ancho_modulo, alto_frente,
            alto_caja, grosor_caja, grosor_fondo, grosor_fachada,
            marca, longitud_guia, montaje_trasera, nombre.

    Returns:
        App.DocumentObject: el objeto creado o None.
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

    # Aplicar configuración (defaults desde vdo_manifest.json)
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
    if "material_ref" in configuracion:
        obj.VDO_Material_Ref = configuracion["material_ref"]
    obj.VDO_Herraje_Ref = obj.MarcaCorredera
    rotacion = float(configuracion.get("rotacion", 0.0))
    obj.VDO_RotacionZ = rotacion
    obj.VDO_Anclaje = configuracion.get(
        "anclaje", VDO_MOD.ANCLAJE_DEFAULT)
    if rotacion:
        obj.Placement = App.Placement(
            obj.Placement.Base, VDO_MOD.rotacion_z(rotacion))

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] Cajón '{nombre}' creado "
        f"(marca={obj.MarcaCorredera}, LI={float(obj.AnchoLibre):.0f}, "
        f"ProfLibre={float(obj.ProfLibre):.0f}).\n")
    return obj
