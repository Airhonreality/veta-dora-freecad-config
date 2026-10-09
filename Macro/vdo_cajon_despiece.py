# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cajon_despiece.py
# Fórmulas de despiece del cajón con corredera oculta (Blum Tandem etc)
# Axioma 2: lógica pura, SIN FreeCAD ni UI (testable con python3)
#
# Datos de partida:
#   LI       = ancho libre interior del mueble (pared a pared)
#   ProfInt  = profundidad libre interior del mueble
#   LG       = largo nominal de la guía (auto: max(comerciales ≤ ProfInt))
#   Delta    = reducción por herraje (ej. Blum Tandem 16mm → 49 mm)
#   Gcaja    = grosor de laterales/trasera/frente interior (15-16 mm)
#   Gfondo   = grosor del piso (6-12 mm)
#   Gfrente  = grosor de la fachada (18 mm)
# =====================================================================

import json
import os

# Bootstrap mínimo para leer el manifest (mismo patrón que vdo_defaults)
_here = os.path.dirname(os.path.abspath(__file__))
_manifest_path = os.path.join(_here, "vdo_manifest.json")

with open(_manifest_path, "r", encoding="utf-8") as _f:
    _MANIFEST = json.load(_f)


def obtener_marca(marca_id):
    """Devuelve la definición de una corredera oculta desde el manifest.

    Args:
        marca_id (str): clave en manifest["correderas_ocultas"]
                        ("blum_tandem", "generica", "hafele", "ducasse")

    Returns:
        dict con delta_ancho, longitudes_comerciales, mecanizado, ...
    """
    marcas = _MANIFEST.get("correderas_ocultas", {})
    if marca_id not in marcas:
        raise ValueError(
            f"Marca de corredera desconocida: '{marca_id}'. "
            f"Disponibles: {', '.join(sorted(marcas))}")
    return marcas[marca_id]


def listar_marcas():
    """Lista las claves de correderas ocultas disponibles."""
    return sorted(_MANIFEST.get("correderas_ocultas", {}).keys())


def seleccionar_guia(prof_int, longitudes_comerciales):
    """Selecciona la guía comercial inmediatamente inferior o igual.

    Args:
        prof_int (float): profundidad libre interior del mueble (mm)
        longitudes_comerciales (list): longitudes nominales (mm)

    Returns:
        float: LG seleccionada

    Raises:
        ValueError: si ProfInt es menor que la guía más corta
    """
    validas = sorted(float(l) for l in longitudes_comerciales)
    aptas = [l for l in validas if l <= float(prof_int)]
    if not aptas:
        raise ValueError(
            f"ProfInt={prof_int} mm es menor que la guía comercial mínima "
            f"({validas[0]} mm). No hay corredera que encaje.")
    return aptas[-1]


def calcular_despiece(config):
    """Calcula el despiece completo del cajón con corredera oculta.

    Args:
        config (dict): claves obligatorias:
            ancho_libre (LI), prof_libre (ProfInt), ancho_modulo,
            alto_frente, marca (str)
          opcionales:
            alto_caja, grosor_caja, grosor_fondo, grosor_fachada,
            longitud_guia (0 = auto), montaje_trasera
            ("entre_laterales" | "testa"),
            penetracion_ranura, eje_ranura,
            holgura_lateral_fachada, holgura_superior_fachada,
            holgura_inferior_fachada, material_ref

    Returns:
        dict con:
            "guia":        {lg, delta, marca, prof_int}
            "caja":        medidas de las 5 piezas de la caja
            "fachada":     medidas de la fachada
            "posiciones":  coordenadas 3D (X=ancho, Y=prof, Z=alto)
            "piezas":      lista de corte (para VDO_Paneles_JSON)
            "mecanizados": cotas de mecanizado usadas
            "avisos":      lista de advertencias (str)
    """
    # --- Entradas obligatorias ---
    li = float(config["ancho_libre"])
    prof_int = float(config["prof_libre"])
    ancho_modulo = float(config["ancho_modulo"])
    alto_frente = float(config["alto_frente"])
    marca_id = config.get("marca", "blum_tandem")

    marca = obtener_marca(marca_id)
    delta = float(marca["delta_ancho"])
    mecanizado = dict(marca.get("mecanizado", {}))

    # --- Defaults desde manifest (parametros_cajon) ---
    pc = _MANIFEST.get("parametros_cajon", {})

    def _p(clave, fallback):
        return float(pc.get(clave, {}).get("valor", fallback))

    alto_caja = float(config.get("alto_caja") or _p("alto_caja", 120))
    g_caja = float(config.get("grosor_caja") or _p("grosor_caja", 16))
    g_fondo = float(config.get("grosor_fondo") or _p("grosor_fondo", 6))
    g_fachada = float(config.get("grosor_fachada") or _p("grosor_fachada", 18))
    pen_ranura = float(config.get("penetracion_ranura")
                        or _p("penetracion_ranura_piso", 10))
    eje_ranura = float(config.get("eje_ranura")
                       or _p("eje_ranura_piso", 11.5))
    holg_lat = float(config.get("holgura_lateral_fachada")
                     or _p("holgura_lateral_fachada", 2))
    holg_sup = float(config.get("holgura_superior_fachada")
                     or _p("holgura_superior_fachada", 2))
    holg_inf = float(config.get("holgura_inferior_fachada")
                     or _p("holgura_inferior_fachada", 2))
    montaje = config.get("montaje_trasera", "entre_laterales")
    material_ref = config.get("material_ref", "melamina_standar")

    avisos = []

    # --- Validaciones ---
    if g_caja not in (15.0, 16.0):
        avisos.append(
            f"Grosor de caja {g_caja} mm: las correderas ocultas estándar "
            f"están pensadas para 15/16 mm (con 18 mm hay que rebajar el "
            f"canto inferior del lateral).")
    if g_fondo > g_caja:
        avisos.append("El grosor del piso no puede superar el de la caja.")
    if montaje not in ("entre_laterales", "testa"):
        raise ValueError(
            f"montaje_trasera inválido: '{montaje}' "
            f"(use 'entre_laterales' o 'testa')")

    # --- 1. Guía (LG) ---
    lg_manual = float(config.get("longitud_guia") or 0)
    if lg_manual > 0:
        lg = lg_manual
    else:
        lg = seleccionar_guia(prof_int, marca["longitudes_comerciales"])

    # --- 2. Ancho exterior de la caja ---
    ancho_ext = li - delta
    if ancho_ext <= 0:
        raise ValueError(
            f"Ancho exterior de caja inválido: LI({li}) - Delta({delta}) "
            f"= {ancho_ext}. Revise LI o la marca de corredera.")

    # --- 3. Laterales ---
    largo_lateral = lg
    alto_lateral = alto_caja

    # --- 4. Contra-frente y frente interior ---
    if montaje == "entre_laterales":
        ancho_contra = ancho_ext - (2 * g_caja)
        y_trasera = lg - g_caja
    else:  # testa: trasera detrás de los laterales
        ancho_contra = ancho_ext
        y_trasera = lg

    z_piso = eje_ranura
    alto_contra = alto_lateral - (z_piso + g_fondo)  # sobre el piso
    if alto_contra <= 0:
        raise ValueError(
            f"Alto de caja ({alto_caja} mm) demasiado pequeño: "
            f"debe superar eje_ranura({eje_ranura}) + "
            f"grosor_fondo({g_fondo}) = {z_piso + g_fondo} mm.")
    alto_frente_int = alto_contra

    # --- 5. Piso ---
    if montaje == "entre_laterales":
        anchoEntre = ancho_contra  # = ancho_ext - 2*g_caja
    else:
        anchoEntre = ancho_ext - (2 * g_caja)
    ancho_piso = anchoEntre + (2 * pen_ranura)
    largo_piso = lg  # fórmula del usuario (largo = LG)

    # --- 6. Fachada ---
    ancho_fachada = ancho_modulo - (2 * holg_lat)
    alto_fachada = alto_frente - holg_sup - holg_inf
    if ancho_fachada <= 0 or alto_fachada <= 0:
        raise ValueError(
            f"Fachada inválida: {ancho_fachada} x {alto_fachada} mm "
            f"(holguras demasiado grandes).")

    # --- 7. Posiciones 3D (origen = esquina frontales-inferior-izquierda
    #        exterior de la caja) ---
    centro_caja_x = ancho_ext / 2.0  # la caja queda centrada en LI
    x_mueble_izq = centro_caja_x - (ancho_modulo / 2.0)

    posiciones = {
        "lateral_izquierdo": {"x": 0.0, "y": 0.0, "z": 0.0,
                              "largo_x": g_caja, "largo_y": lg,
                              "largo_z": alto_lateral},
        "lateral_derecho": {"x": ancho_ext - g_caja, "y": 0.0, "z": 0.0,
                            "largo_x": g_caja, "largo_y": lg,
                            "largo_z": alto_lateral},
        "contra_frente": {"x": g_caja if montaje == "entre_laterales" else 0.0,
                          "y": y_trasera, "z": z_piso + g_fondo,
                          "largo_x": ancho_contra, "largo_y": g_caja,
                          "largo_z": alto_contra},
        "frente_interior": {"x": g_caja, "y": 0.0, "z": z_piso + g_fondo,
                            "largo_x": ancho_contra,
                            "largo_y": g_caja,
                            "largo_z": alto_frente_int},
        "piso": {"x": g_caja - pen_ranura, "y": 0.0, "z": z_piso,
                 "largo_x": ancho_piso, "largo_y": largo_piso,
                 "largo_z": g_fondo},
        "fachada": {"x": x_mueble_izq + holg_lat, "y": -g_fachada,
                    "z": 0.0,
                    "largo_x": ancho_fachada, "largo_y": g_fachada,
                    "largo_z": alto_fachada},
    }

    # --- 8. Mecanizados (cotas de la ficha técnica) ---
    diam_t = float(mecanizado.get("diam_taladro", 6))
    prof_t = float(mecanizado.get("prof_taladro", 12))
    dist_t_tras = float(mecanizado.get("dist_taladro_borde_trasero", 8))
    prof_ranura = float(mecanizado.get("prof_ranura_lateral", 4))
    notch_ancho = float(mecanizado.get("notch_ancho", 25))
    notch_alto = float(mecanizado.get("notch_alto", 20))

    mecanizados_resumen = {
        "marca": marca_id,
        "diam_taladro": diam_t,
        "prof_taladro": prof_t,
        "dist_taladro_borde_trasero": dist_t_tras,
        "prof_ranura_lateral": prof_ranura,
        "notch_ancho": notch_ancho,
        "notch_alto": notch_alto,
        "eje_ranura": z_piso,
        "grosor_fondo": g_fondo,
    }

    # --- 9. Piezas para cutting list (VDO_Paneles_JSON) ---
    piezas = [
        {
            "nombre": "Cajon_Lateral_Izq",
            "tipo": "panel",
            "largo": largo_lateral,
            "ancho": alto_lateral,
            "espesor": g_caja,
            "cantidad": 1,
            "material_ref": material_ref,
            "mecanizados": [
                {"tipo": "ranura_piso", "cara": "interna",
                 "z_base": z_piso, "ancho": g_fondo,
                 "prof": prof_ranura, "largo": lg},
                {"tipo": "taladro_fondo", "ø": diam_t, "prof": prof_t,
                 "y_desde_trasero": dist_t_tras, "x_centrada": True},
            ],
        },
        {
            "nombre": "Cajon_Lateral_Der",
            "tipo": "panel",
            "largo": largo_lateral,
            "ancho": alto_lateral,
            "espesor": g_caja,
            "cantidad": 1,
            "material_ref": material_ref,
            "mecanizados": [
                {"tipo": "ranura_piso", "cara": "interna",
                 "z_base": z_piso, "ancho": g_fondo,
                 "prof": prof_ranura, "largo": lg},
                {"tipo": "taladro_fondo", "ø": diam_t, "prof": prof_t,
                 "y_desde_trasero": dist_t_tras, "x_centrada": True},
            ],
        },
        {
            "nombre": "Cajon_Contrafrente",
            "tipo": "panel",
            "largo": ancho_contra,
            "ancho": alto_contra,
            "espesor": g_caja,
            "cantidad": 1,
            "material_ref": material_ref,
            "mecanizados": [
                {"tipo": "notch_inferior", "lados": "ambos",
                 "ancho": notch_ancho, "alto": notch_alto},
            ],
        },
        {
            "nombre": "Cajon_Frente_Interior",
            "tipo": "panel",
            "largo": ancho_contra,
            "ancho": alto_frente_int,
            "espesor": g_caja,
            "cantidad": 1,
            "material_ref": material_ref,
            "mecanizados": [
                {"tipo": "zona_locking_device", "cara": "inferior",
                 "nota": "Gancho de acople (locking device) según ficha"},
            ],
        },
        {
            "nombre": "Cajon_Piso",
            "tipo": "panel",
            "largo": largo_piso,
            "ancho": ancho_piso,
            "espesor": g_fondo,
            "cantidad": 1,
            "material_ref": material_ref,
            "mecanizados": [],
        },
        {
            "nombre": "Cajon_Fachada",
            "tipo": "panel",
            "largo": ancho_fachada,
            "ancho": alto_fachada,
            "espesor": g_fachada,
            "cantidad": 1,
            "material_ref": material_ref,
            "mecanizados": [
                {"tipo": "canto", "caras": 4,
                 "nota": "Fachada: 4 cantos (convención VDO)"},
            ],
        },
    ]

    return {
        "guia": {"lg": lg, "delta": delta, "marca": marca_id,
                 "prof_int": prof_int,
                 "auto": lg_manual <= 0},
        "caja": {
            "ancho_exterior": ancho_ext,
            "largo_lateral": largo_lateral,
            "alto_lateral": alto_lateral,
            "grosor": g_caja,
            "ancho_contra": ancho_contra,
            "alto_contra": alto_contra,
            "montaje_trasera": montaje,
            "ancho_piso": ancho_piso,
            "largo_piso": largo_piso,
            "grosor_piso": g_fondo,
            "z_piso": z_piso,
        },
        "fachada": {
            "ancho": ancho_fachada,
            "alto": alto_fachada,
            "espesor": g_fachada,
        },
        "posiciones": posiciones,
        "piezas": piezas,
        "mecanizados": mecanizados_resumen,
        "avisos": avisos,
    }


# =====================================================================
# SELF-TEST (python3 Macro/vdo_cajon_despiece.py)
# =====================================================================
if __name__ == "__main__":
    print("=" * 64)
    print("[VDO] Self-test vdo_cajon_despiece.py")
    print("=" * 64)

    config = {
        "ancho_libre": 600.0,      # LI
        "prof_libre": 580.0,       # ProfInt
        "ancho_modulo": 640.0,
        "alto_frente": 225.0,
        "marca": "blum_tandem",
        "alto_caja": 120.0,
        "grosor_caja": 16.0,
        "grosor_fondo": 6.0,
        "grosor_fachada": 18.0,
    }
    d = calcular_despiece(config)

    # --- Aritmética de referencia ---
    assert d["guia"]["lg"] == 550.0, d["guia"]          # 580 → 550
    assert d["guia"]["delta"] == 49.0
    assert d["caja"]["ancho_exterior"] == 551.0         # 600 - 49
    assert d["caja"]["ancho_contra"] == 519.0           # 551 - 32
    assert abs(d["caja"]["alto_contra"] - 102.5) < 1e-9  # 120 - 17.5
    assert d["caja"]["ancho_piso"] == 539.0             # 519 + 2*10
    assert d["caja"]["largo_piso"] == 550.0
    assert d["fachada"]["ancho"] == 636.0               # 640 - 4
    assert d["fachada"]["alto"] == 221.0                # 225 - 4
    assert len(d["piezas"]) == 6

    # --- Montaje a testa ---
    d2 = calcular_despiece(dict(config, montaje_trasera="testa"))
    assert d2["caja"]["ancho_contra"] == 551.0          # ancho completo

    # --- Guía manual ---
    d3 = calcular_despiece(dict(config, longitud_guia=500))
    assert d3["guia"]["lg"] == 500.0 and d3["guia"]["auto"] is False

    # --- Guía imposible ---
    try:
        calcular_despiece(dict(config, prof_libre=200))
        raise AssertionError("Debía fallar con ProfInt=200")
    except ValueError:
        pass

    # --- Grosor 18mm avisa ---
    d4 = calcular_despiece(dict(config, grosor_caja=18.0))
    assert any("15/16" in a for a in d4["avisos"]), d4["avisos"]

    print("✅ Todas las aserciones pasaron")
    print(f"   LG={d['guia']['lg']}  ancho_ext={d['caja']['ancho_exterior']}"
          f"  ancho_contra={d['caja']['ancho_contra']}"
          f"  piso={d['caja']['ancho_piso']}x{d['caja']['largo_piso']}")
    print(f"   Piezas: {[p['nombre'] for p in d['piezas']]}")
    if d["avisos"]:
        print(f"   ⚠️  Avisos: {d['avisos']}")
