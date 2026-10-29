# -*- coding: utf-8 -*-
# =====================================================================
# vdo_zocalo_core.py
# Motor del zócalo paramétrico VDO (FeaturePython).
#
# El zócalo NO es un reengrose: es una entidad física independiente que
# reutiliza la primitiva perimetral 2D (distancia_al_canto / largo_tira)
# y la extruye verticalmente en Z.
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
import vdo_reengrose as VDO_RE
from vdo_layout import Layout, Track, AXIS_X, resolve_layout
from vdo_view_base import VDOViewProviderBase


class ZocaloError(ValueError):
    """Error de validación del zócalo."""


NOMBRES_BORDE = {
    "frente": "Zocalo_Frente",
    "izquierda": "Zocalo_Lat_Izq",
    "derecha": "Zocalo_Lat_Der",
    "fondo": "Zocalo_Trasero",
}
ROLES_BORDE = {
    "frente": "frente",
    "izquierda": "lateral_izquierdo",
    "derecha": "lateral_derecho",
    "fondo": "trasero",
}
CANTOS_BORDE = {
    "frente": {"norte": "RIG", "sur": "RIG", "este": "RIG", "oeste": "RIG"},
    "izquierda": {"norte": "RIG", "sur": "RIG", "este": "FX", "oeste": "RIG"},
    "derecha": {"norte": "RIG", "sur": "RIG", "este": "RIG", "oeste": "FX"},
    "fondo": {"norte": "FX", "sur": "FX", "este": "FX", "oeste": "FX"},
    "amarre": {"norte": "FX", "sur": "FX", "este": "FX", "oeste": "FX"},
}


def _float_positivo(valor, nombre):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ZocaloError(f"Valor inválido para '{nombre}': {valor!r}.")
    if numero <= 0:
        raise ZocaloError(f"'{nombre}' debe ser mayor que 0.")
    return numero


def _float_no_negativo(valor, nombre):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ZocaloError(f"Valor inválido para '{nombre}': {valor!r}.")
    if numero < 0:
        raise ZocaloError(f"'{nombre}' no puede ser negativo.")
    return numero


def calcular_geometria_zocalo(ancho, fondo, alto_zocalo, espesor_tablero,
                              distancia_frente=50.0,
                              distancia_costados=0.0,
                              distancia_trasera=20.0,
                              tiene_trasera=True,
                              amarres_intermedios=0,
                              material_ref="melamina_standar"):
    """Calcula tiras, amarres y despiece del zócalo (sin FreeCAD).

    Coordenadas del tablero: X = ancho del mueble, Y = fondo del mueble.
    Las tiras se extruyen después de Z=0 a Z=AltoZocalo.
    """
    ancho = _float_positivo(ancho, "ancho")
    fondo = _float_positivo(fondo, "fondo")
    alto_zocalo = _float_positivo(alto_zocalo, "alto_zocalo")
    espesor = _float_positivo(espesor_tablero, "espesor_tablero")
    dist_frente = _float_no_negativo(distancia_frente, "distancia_frente")
    dist_costados = _float_no_negativo(
        distancia_costados, "distancia_costados")
    dist_trasera = _float_no_negativo(
        distancia_trasera, "distancia_trasera")
    tiene_trasera = bool(tiene_trasera)
    try:
        amarres = int(amarres_intermedios)
    except (TypeError, ValueError):
        raise ZocaloError(
            f"Valor inválido para 'amarres_intermedios': "
            f"{amarres_intermedios!r}.")
    if amarres < 0:
        raise ZocaloError("'amarres_intermedios' no puede ser negativo.")

    if dist_frente + espesor > fondo + 1e-9:
        raise ZocaloError(
            "La distancia frontal deja el zócalo fuera del fondo del mueble.")
    if dist_costados + espesor > ancho / 2.0 + 1e-9:
        raise ZocaloError(
            "La distancia a los costados deja el zócalo sin luz interior.")
    if tiene_trasera:
        if dist_trasera + espesor > fondo + 1e-9:
            raise ZocaloError(
                "La distancia trasera deja el zócalo fuera del fondo.")
        if dist_frente + 2.0 * espesor >= fondo - dist_trasera - 1e-9:
            raise ZocaloError(
                "Las tiras frontal y trasera se solapan en el fondo.")

    bordes = {
        "frente": {
            "activo": True,
            "ancho": espesor,
            "distancia_al_canto": dist_frente,
            "largo_tira": "punta_a_punta",
            "espesor": espesor,
        },
        "izquierda": {
            "activo": True,
            "ancho": espesor,
            "distancia_al_canto": dist_costados,
            "largo_tira": "marco_interior",
            "espesor": espesor,
        },
        "derecha": {
            "activo": True,
            "ancho": espesor,
            "distancia_al_canto": dist_costados,
            "largo_tira": "marco_interior",
            "espesor": espesor,
        },
        "fondo": {
            "activo": tiene_trasera,
            "ancho": espesor,
            "distancia_al_canto": dist_trasera,
            "largo_tira": "marco_interior",
            "espesor": espesor,
        },
    }

    tiras = VDO_RE.generar_tiras_perimetrales(
        ancho, fondo, bordes, espesor, "vertical_domina")
    por_borde = {tira["borde"]: tira for tira in tiras}
    for borde in ("frente", "izquierda", "derecha"):
        if borde not in por_borde:
            raise ZocaloError(
                f"No se pudo generar la tira obligatoria '{borde}'.")

    frente = por_borde["frente"]
    izquierda = por_borde["izquierda"]
    derecha = por_borde["derecha"]
    trasera = por_borde.get("fondo")

    rib_y0 = frente["y"] + frente["h"]
    rib_y1 = trasera["y"] if trasera else fondo
    if rib_y1 <= rib_y0 + 1e-9:
        raise ZocaloError(
            "No hay profundidad útil entre la tira frontal y la trasera.")

    interior_izq = izquierda["x"] + izquierda["w"]
    interior_der = derecha["x"]
    luz = interior_der - interior_izq
    if luz <= 0:
        raise ZocaloError("No hay luz interior entre los laterales.")

    amarres = []
    if amarres_intermedios:
        hueco_w = max(0.0, interior_der - interior_izq)
        hueco_h = max(0.0, rib_y1 - rib_y0)
        if hueco_w <= 0 or hueco_h <= 0:
            raise ZocaloError(
                "No hay hueco interior para los amarres intermedios.")
        columnas = [Track(f"col_{i + 1}") for i in range(amarres_intermedios + 1)]
        filas = [Track("fila_1")]
        layout_zocalo = Layout(columns=columnas, rows=filas)
        resuelto = resolve_layout(
            layout_zocalo, hueco_w, hueco_h, espesor, reengroses=None)
        for indice, pieza in enumerate(
                [p for p in resuelto.pieces
                 if getattr(p, "axis", None) == AXIS_X
                 and str(getattr(p, "path", "")).startswith("x")],
                start=1):
            x0 = interior_izq + float(pieza.x)
            amarres.append({
                "nombre": f"Zocalo_Amarre_{indice:02d}",
                "rol": "amarre",
                "borde": "amarre",
                "x": float(x0),
                "y": float(rib_y0),
                "w": float(pieza.w),
                "h": float(hueco_h),
                "d": float(espesor),
                "espesor": float(espesor),
            })

    piezas = []
    for tira in tiras:
        borde = tira["borde"]
        piezas.append({
            "nombre": NOMBRES_BORDE[borde],
            "tipo": "panel",
            "rol": ROLES_BORDE[borde],
            "borde": borde,
            "orientacion": "vertical",
            "largo": float(tira["largo"]),
            "ancho": float(alto_zocalo),
            "espesor": float(espesor),
            "cantidad": 1,
            "material_ref": material_ref,
            "cantos": dict(CANTOS_BORDE[borde]),
            "grupo": "",
            "operacion": "Cantear por separado",
            "largo_tira": tira["largo_tira"],
            "distancia_al_canto": tira["distancia_al_canto"],
        })

    for amarre in amarres:
        piezas.append({
            "nombre": amarre["nombre"],
            "tipo": "panel",
            "rol": "amarre",
            "borde": "amarre",
            "orientacion": "vertical",
            "largo": float(max(amarre["w"], amarre["h"])),
            "ancho": float(alto_zocalo),
            "espesor": float(espesor),
            "cantidad": 1,
            "material_ref": material_ref,
            "cantos": dict(CANTOS_BORDE["amarre"]),
            "grupo": "",
            "operacion": "Cantear por separado",
            "largo_tira": "punta_a_punta",
            "distancia_al_canto": 0.0,
        })

    lineas = [
        f"Zócalo: {ancho:.0f} × {fondo:.0f} × {alto_zocalo:.0f} mm "
        f"(e={espesor:.0f}, trasera={'sí' if tiene_trasera else 'no'})"
    ]
    for pieza in piezas:
        lineas.append(
            f"{pieza['nombre']}: {pieza['largo']:.1f} × "
            f"{pieza['ancho']:.1f} × {pieza['espesor']:.0f} mm "
            f"({pieza['largo_tira']}, "
            f"canto={pieza['distancia_al_canto']:.1f})")

    return {
        "tiras": tiras,
        "amarres": amarres,
        "piezas": piezas,
        "resumen": "\n".join(lineas),
        "bordes": bordes,
    }


class ZocaloFeature:
    """FeaturePython que genera la geometría de un zócalo."""

    def __init__(self, obj):
        obj.addProperty("App::PropertyLength", "Ancho", "Dimensiones",
                        "Ancho total del mueble (mm)").Ancho = 600.0
        obj.addProperty("App::PropertyLength", "Fondo", "Dimensiones",
                        "Fondo total del mueble (mm)").Fondo = 580.0
        obj.addProperty("App::PropertyLength", "AltoZocalo", "Dimensiones",
                        "Alto del zócalo (mm)").AltoZocalo = 100.0
        obj.addProperty("App::PropertyLength", "EspesorTablero", "Dimensiones",
                        "Espesor del tablero del zócalo (mm)"
                        ).EspesorTablero = VDO_D.ESPESOR_DEFAULT

        obj.addProperty("App::PropertyLength", "DistanciaFrente", "Separación",
                        "Distancia desde el frente del mueble (mm)"
                        ).DistanciaFrente = 50.0
        obj.addProperty("App::PropertyLength", "DistanciaCostados",
                        "Separación",
                        "Distancia desde los costados (mm)"
                        ).DistanciaCostados = 0.0
        obj.addProperty("App::PropertyLength", "DistanciaTrasera", "Separación",
                        "Distancia desde el fondo del mueble (mm)"
                        ).DistanciaTrasera = 20.0
        obj.addProperty("App::PropertyBool", "TieneTrasera", "Estructura",
                        "Cierra el cajón del zócalo por detrás"
                        ).TieneTrasera = True
        obj.addProperty("App::PropertyInteger", "AmarresIntermedios",
                        "Estructura",
                        "Costillas de refuerzo entre frente y trasera"
                        ).AmarresIntermedios = 0

        obj.addProperty("App::PropertyString", "VDO_Tipo", "VDO",
                        "Tipo de objeto").VDO_Tipo = "contenedor"
        obj.addProperty("App::PropertyString", "VDO_Subtipo", "VDO",
                        "Subtipo").VDO_Subtipo = "zocalo"
        obj.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO",
                        "Material de las piezas"
                        ).VDO_Material_Ref = "melamina_standar"
        obj.addProperty("App::PropertyString", "VDO_Paneles_JSON", "VDO",
                        "Descripción JSON de las piezas del zócalo")
        obj.addProperty("App::PropertyString", "VDO_ResumenDespiece", "VDO",
                        "Resumen legible del despiece (solo lectura)")

        VDO_MOD.add_common_props(obj)

        obj.Proxy = self

    def _config(self, fp):
        return {
            "ancho": float(fp.Ancho),
            "fondo": float(fp.Fondo),
            "alto_zocalo": float(fp.AltoZocalo),
            "espesor_tablero": float(fp.EspesorTablero),
            "distancia_frente": float(fp.DistanciaFrente),
            "distancia_costados": float(fp.DistanciaCostados),
            "distancia_trasera": float(fp.DistanciaTrasera),
            "tiene_trasera": bool(fp.TieneTrasera),
            "amarres_intermedios": int(fp.AmarresIntermedios),
            "material_ref": fp.VDO_Material_Ref,
        }

    def execute(self, fp):
        try:
            geo = calcular_geometria_zocalo(**self._config(fp))
        except ValueError as exc:
            App.Console.PrintError(f"[VDO] Zócalo inválido: {exc}\n")
            fp.Shape = Part.Shape()
            fp.VDO_Paneles_JSON = "[]"
            fp.VDO_ResumenDespiece = f"Zócalo inválido: {exc}"
            return

        alto = float(fp.AltoZocalo)
        solidos = []
        for tira in geo["tiras"]:
            solidos.append(Part.makeBox(
                tira["w"], tira["h"], alto,
                App.Vector(tira["x"], tira["y"], 0.0)))
        for amarre in geo["amarres"]:
            solidos.append(Part.makeBox(
                amarre["w"], amarre["h"], alto,
                App.Vector(amarre["x"], amarre["y"], 0.0)))

        fp.Shape = Part.makeCompound(solidos)

        piezas = []
        for pieza in geo["piezas"]:
            dato = dict(pieza)
            dato["grupo"] = fp.Label
            dato["material_ref"] = fp.VDO_Material_Ref
            piezas.append(dato)
        fp.VDO_Paneles_JSON = json.dumps(piezas, ensure_ascii=False)
        fp.VDO_ResumenDespiece = geo["resumen"]

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderZocalo(VDOViewProviderBase):
    """ViewProvider del zócalo FeaturePython."""

    MENU_LABEL = "Propiedades del Zócalo"
    ICON = "vdo_zocalo.svg"

    def get_panel_class(self):
        from vdo_zocalo_task import ZocaloTaskPanel
        return ZocaloTaskPanel


def make_zocalo(configuracion):
    """Crea un zócalo paramétrico (FeaturePython).

    Args:
        configuracion (dict): claves ancho, fondo, alto_zocalo,
            espesor_tablero, distancia_frente, distancia_costados,
            distancia_trasera, tiene_trasera, amarres_intermedios,
            material_ref, rotacion/anclaje/nombre.

    Returns:
        App.DocumentObject: el objeto creado o None.
    """
    doc = vdo_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "Zocalo")
    obj = doc.addObject("Part::FeaturePython", nombre)
    ZocaloFeature(obj)

    if App.GuiUp:
        ViewProviderZocalo(obj.ViewObject)

    obj.Ancho = configuracion.get("ancho", 600.0)
    obj.Fondo = configuracion.get("fondo", 580.0)
    obj.AltoZocalo = configuracion.get("alto_zocalo", 100.0)
    obj.EspesorTablero = configuracion.get(
        "espesor_tablero", VDO_D.ESPESOR_DEFAULT)
    obj.DistanciaFrente = configuracion.get("distancia_frente", 50.0)
    obj.DistanciaCostados = configuracion.get("distancia_costados", 0.0)
    obj.DistanciaTrasera = configuracion.get("distancia_trasera", 20.0)
    obj.TieneTrasera = configuracion.get("tiene_trasera", True)
    obj.AmarresIntermedios = configuracion.get("amarres_intermedios", 0)
    obj.VDO_Material_Ref = configuracion.get(
        "material_ref", "melamina_standar")

    rotacion = float(configuracion.get("rotacion", 0.0))
    obj.VDO_RotacionZ = rotacion
    obj.VDO_Anclaje = configuracion.get(
        "anclaje", VDO_MOD.ANCLAJE_DEFAULT)
    if rotacion:
        obj.Placement = App.Placement(
            obj.Placement.Base, VDO_MOD.rotacion_z(rotacion))

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] Zócalo '{nombre}' creado "
        f"({float(obj.Ancho):.0f} × {float(obj.Fondo):.0f} × "
        f"{float(obj.AltoZocalo):.0f} mm).\n")
    return obj
