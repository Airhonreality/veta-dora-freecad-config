# -*- coding: utf-8 -*-
"""Motor agnostico de reengroses y pachas para piezas L1.

No importa FreeCAD ni Qt. Trabaja en coordenadas locales del tablero:
    X = largo
    Y = ancho / profundidad de la pieza
    Z = espesor / normal de las caras A (+Z) y B (-Z)

El motor no sabe que es un mueble, un vano o una repisa. Solo recibe una
pieza base y devuelve piezas locales, cantos y datos de colision.
"""

import json


class ReengroseError(ValueError):
    """Error de validacion del modificador de reengrose."""


ORIENTACIONES = ("paralela", "transversal")
CARAS = ("cara_a", "cara_b", "ambos")
ALINEACIONES = ("frente", "centrado", "fondo")
MODOS = ("independiente", "pacha")
ALCANCES = ("parcial", "total")
POLITICAS_REPISA = ("retroceder", "mochear")
PRIORIDADES_ENCUENTRO = (
    "vertical_domina", "horizontal_domina", "inglete_45")
MODOS_CHOQUE_NUCLEO = ("retroceso", "mocheo", "interrumpir_tira")

_MAPA_MODO_CHOQUE = {
    "retroceder": "retroceso",
    "retroceso": "retroceso",
    "mochear": "mocheo",
    "mocheo": "mocheo",
    "interrumpir": "interrumpir_tira",
    "interrumpir_tira": "interrumpir_tira",
}
_MAPA_MODO_LEGACY = {
    "retroceso": "retroceder",
    "mocheo": "mochear",
    "interrumpir_tira": "interrumpir_tira",
}

BORDES = ("norte", "sur", "este", "oeste")
CANTO_VISTO = "RIG"
CANTO_OCULTO = "FX"
CANTOS_VALIDOS = ("RIG", "FX", "SMRG")

PROPS = {
    "activo": "VDO_Reengrose_Activo",
    "orientacion": "VDO_Reengrose_Orientacion",
    "ancho": "VDO_Reengrose_Ancho",
    "espesor": "VDO_Reengrose_Espesor",
    "cara": "VDO_Reengrose_Cara",
    "alineacion_profundidad": "VDO_Reengrose_Alineacion",
    "modo_fabricacion": "VDO_Reengrose_Modo",
    "alcance": "VDO_Reengrose_Alcance",
    "politica_repisa": "VDO_Reengrose_PoliticaRepisa",
    "prioridad_encuentro_tiras": "VDO_Reengrose_PrioridadEncuentro",
    "comportamiento_choque_nucleo": "VDO_Reengrose_ChoqueNucleo",
}

DEFAULTS = {
    "activo": False,
    "orientacion": "paralela",
    "ancho": 70.0,
    "espesor": None,
    "cara": "cara_a",
    "alineacion_profundidad": "frente",
    "modo_fabricacion": "pacha",
    "alcance": "parcial",
    "politica_repisa": "retroceder",
    "prioridad_encuentro_tiras": "vertical_domina",
    "comportamiento_choque_nucleo": "retroceso",
}


def _a_float(valor, nombre, defecto=None):
    if valor is None or valor == "":
        return defecto
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ReengroseError(
            f"Valor numerico invalido para '{nombre}': {valor!r}.")


def _a_bool(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        return valor.strip().lower() in ("1", "true", "si", "sí", "yes", "on")
    return bool(valor)


def _validar_enum(valor, nombre, validos):
    texto = str(valor or "").strip().lower()
    if texto not in validos:
        raise ReengroseError(
            f"Valor invalido para '{nombre}': {valor!r}. "
            f"Validos: {', '.join(validos)}.")
    return texto


def _normalizar_modo_choque(valor, nombre="comportamiento_choque_nucleo"):
    texto = str(valor or "").strip().lower()
    try:
        return _MAPA_MODO_CHOQUE[texto]
    except KeyError:
        raise ReengroseError(
            f"Valor invalido para '{nombre}': {valor!r}. "
            f"Validos: {', '.join(MODOS_CHOQUE_NUCLEO)}.")


class ReengroseModifier:
    """DTO puro del modificador de reengrose."""

    def __init__(self, datos=None):
        datos = normalizar_modificador(datos)
        for clave, valor in datos.items():
            setattr(self, clave, valor)

    def to_dict(self):
        return {clave: getattr(self, clave) for clave in PROPS}

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, datos):
        return cls(datos)

    @classmethod
    def from_json(cls, texto):
        if not texto:
            return cls()
        return cls(json.loads(texto))


def normalizar_modificador(datos=None):
    if isinstance(datos, ReengroseModifier):
        datos = datos.to_dict()
    if datos is None:
        datos = {}
    if not isinstance(datos, dict):
        raise ReengroseError("El modificador de reengrose debe ser un dict.")
    if "modificador_reengrose" in datos:
        datos = datos["modificador_reengrose"] or {}

    activo = _a_bool(datos.get("activo", DEFAULTS["activo"]))
    orientacion = _validar_enum(
        datos.get("orientacion", DEFAULTS["orientacion"]),
        "orientacion", ORIENTACIONES)
    ancho = _a_float(datos.get("ancho", DEFAULTS["ancho"]), "ancho")
    if ancho is None or ancho <= 0:
        raise ReengroseError("El ancho del reengrose debe ser mayor que 0.")
    espesor = _a_float(datos.get("espesor"), "espesor")
    if espesor is not None and espesor <= 0:
        raise ReengroseError("El espesor del reengrose debe ser mayor que 0.")
    cara = _validar_enum(datos.get("cara", DEFAULTS["cara"]), "cara", CARAS)
    alineacion = _validar_enum(
        datos.get("alineacion_profundidad",
                  DEFAULTS["alineacion_profundidad"]),
        "alineacion_profundidad", ALINEACIONES)
    modo = _validar_enum(
        datos.get("modo_fabricacion", DEFAULTS["modo_fabricacion"]),
        "modo_fabricacion", MODOS)
    alcance = _validar_enum(
        datos.get("alcance", DEFAULTS["alcance"]),
        "alcance", ALCANCES)
    # La politica legacy y el nuevo comportamiento de choque se mantienen
    # sincronizados. Si llega la propiedad nueva, tiene prioridad.
    modo_nucleo = None
    if datos.get("comportamiento_choque_nucleo") not in (None, ""):
        modo_nucleo = _normalizar_modo_choque(
            datos.get("comportamiento_choque_nucleo"),
            "comportamiento_choque_nucleo")
    elif datos.get("politica_repisa") not in (None, ""):
        modo_nucleo = _normalizar_modo_choque(
            datos.get("politica_repisa"), "politica_repisa")
    else:
        modo_nucleo = DEFAULTS["comportamiento_choque_nucleo"]
    politica = _MAPA_MODO_LEGACY[modo_nucleo]
    prioridad = _validar_enum(
        datos.get("prioridad_encuentro_tiras",
                  DEFAULTS["prioridad_encuentro_tiras"]),
        "prioridad_encuentro_tiras", PRIORIDADES_ENCUENTRO)

    return {
        "activo": activo,
        "orientacion": orientacion,
        "ancho": ancho,
        "espesor": espesor,
        "cara": cara,
        "alineacion_profundidad": alineacion,
        "modo_fabricacion": modo,
        "alcance": alcance,
        "politica_repisa": politica,
        "prioridad_encuentro_tiras": prioridad,
        "comportamiento_choque_nucleo": modo_nucleo,
    }


def espesor_efectivo(panel_base, modifier):
    mod = normalizar_modificador(modifier)
    if mod["espesor"]:
        return float(mod["espesor"])
    return float(panel_base.get("espesor", 0.0))


def _inicio_alineado(total, tamano, alineacion):
    total = float(total)
    tamano = float(tamano)
    alineacion = str(alineacion or "centrado").lower()
    if alineacion == "frente":
        inicio = 0.0
    elif alineacion == "fondo":
        inicio = total - tamano
    else:
        inicio = (total - tamano) / 2.0
    return max(0.0, inicio)


def calcular_geometria_reengrose(panel_base, modifier):
    """Calcula la pieza base y los refuerzos en coordenadas del tablero."""
    mod = normalizar_modificador(modifier)
    largo = float(panel_base.get("largo", 0.0))
    ancho = float(panel_base.get("ancho", 0.0))
    espesor = float(panel_base.get("espesor", 0.0))
    nombre = str(panel_base.get("nombre", "Panel"))

    resultado = {
        "base": {
            "nombre": nombre,
            "rol": "base",
            "largo": largo,
            "ancho": ancho,
            "espesor": espesor,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
        "refuerzos": [],
        "grupo_pacha": "",
        "modificador": mod,
    }
    if not mod["activo"]:
        return resultado

    if largo <= 0 or ancho <= 0 or espesor <= 0:
        raise ReengroseError("El panel base debe tener dimensiones positivas.")

    esp_ref = espesor_efectivo(panel_base, mod)
    caras = ["cara_a", "cara_b"] if mod["cara"] == "ambos" else [mod["cara"]]

    for cara in caras:
        z0 = espesor if cara == "cara_a" else -esp_ref
        sufijo = ""
        if len(caras) > 1:
            sufijo = "_A" if cara == "cara_a" else "_B"

        if mod["modo_fabricacion"] == "pacha" and mod["alcance"] == "total":
            refuerzo = {
                "nombre": f"{nombre}_Pacha{sufijo}",
                "rol": "refuerzo",
                "largo": largo,
                "ancho": ancho,
                "espesor": esp_ref,
                "x": 0.0,
                "y": 0.0,
                "z": z0,
            }
        else:
            if mod["orientacion"] == "paralela":
                largo_ref = largo
                ancho_ref = mod["ancho"]
                if ancho_ref > ancho + 1e-6:
                    raise ReengroseError(
                        "El ancho del reengrose paralelo no cabe en la pieza.")
                x0 = 0.0
                y0 = _inicio_alineado(
                    ancho, ancho_ref, mod["alineacion_profundidad"])
            else:
                largo_ref = ancho
                ancho_ref = mod["ancho"]
                if ancho_ref > largo + 1e-6:
                    raise ReengroseError(
                        "El ancho del reengrose transversal no cabe en la pieza.")
                x0 = _inicio_alineado(largo, ancho_ref, "centrado")
                y0 = 0.0

            refuerzo = {
                "nombre": f"{nombre}_Reengrose{sufijo}",
                "rol": "refuerzo",
                "largo": largo_ref,
                "ancho": ancho_ref,
                "espesor": esp_ref,
                "x": x0,
                "y": y0,
                "z": z0,
            }

        resultado["refuerzos"].append(refuerzo)
    if mod["modo_fabricacion"] == "pacha":
        resultado["grupo_pacha"] = f"Pacha_{nombre}"
    return resultado


def calcular_geometria_caja(caja, modifier, ejes=None):
    """Calcula refuerzos de una pieza en coordenadas de modulo.

    ``caja`` usa x/y/z como origen y w/h/d como dimensiones (w=X, h=Y, d=Z).
    ``ejes`` indica que eje de la caja actua como largo, ancho y espesor:
        vertical:  {"largo": "z", "ancho": "y", "espesor": "x"}
        horizontal:{"largo": "x", "ancho": "y", "espesor": "z"}
        fondo:     {"largo": "x", "ancho": "z", "espesor": "y"}
    """
    mod = normalizar_modificador(modifier)
    base = {clave: float(caja.get(clave, 0.0))
            for clave in ("x", "y", "z", "w", "h", "d")}
    nombre = str(caja.get("nombre", "Pieza"))
    ejes = dict(ejes or {"largo": "x", "ancho": "y", "espesor": "z"})
    for clave in ("largo", "ancho", "espesor"):
        eje = str(ejes.get(clave, "")).lower()
        if eje not in ("x", "y", "z"):
            raise ReengroseError(f"Eje invalido para '{clave}': {eje!r}.")
        ejes[clave] = eje
    if len(set(ejes.values())) != 3:
        raise ReengroseError("Los ejes largo/ancho/espesor deben ser distintos.")

    resultado = {
        "base": dict(base),
        "refuerzos": [],
        "grupo_pacha": "",
        "modificador": mod,
    }
    if not mod["activo"]:
        return resultado

    dim_key = {"x": "w", "y": "h", "z": "d"}
    dims = {eje: base[dim_key[eje]] for eje in ("x", "y", "z")}
    largo = dims[ejes["largo"]]
    ancho = dims[ejes["ancho"]]
    espesor = dims[ejes["espesor"]]
    if largo <= 0 or ancho <= 0 or espesor <= 0:
        raise ReengroseError("La caja base debe tener dimensiones positivas.")

    esp_ref = float(mod["espesor"] or espesor)
    caras = ["cara_a", "cara_b"] if mod["cara"] == "ambos" else [mod["cara"]]

    for cara in caras:
        intervalos = {}
        if mod["modo_fabricacion"] == "pacha" and mod["alcance"] == "total":
            intervalos[ejes["largo"]] = (0.0, largo)
            intervalos[ejes["ancho"]] = (0.0, ancho)
        elif mod["orientacion"] == "paralela":
            if mod["ancho"] > ancho + 1e-6:
                raise ReengroseError(
                    "El ancho del reengrose paralelo no cabe en la pieza.")
            intervalos[ejes["largo"]] = (0.0, largo)
            intervalos[ejes["ancho"]] = (
                _inicio_alineado(
                    ancho, mod["ancho"], mod["alineacion_profundidad"]),
                mod["ancho"])
        else:
            if mod["ancho"] > largo + 1e-6:
                raise ReengroseError(
                    "El ancho del reengrose transversal no cabe en la pieza.")
            intervalos[ejes["largo"]] = (
                (largo - mod["ancho"]) / 2.0, mod["ancho"])
            intervalos[ejes["ancho"]] = (0.0, ancho)

        if cara == "cara_a":
            intervalos[ejes["espesor"]] = (espesor, esp_ref)
            sufijo = "_A"
        else:
            intervalos[ejes["espesor"]] = (-esp_ref, esp_ref)
            sufijo = "_B"
        if len(caras) == 1:
            sufijo = ""

        ref = dict(base)
        for eje, (inicio, tamano) in intervalos.items():
            ref[eje] = base[eje] + inicio
            ref[dim_key[eje]] = tamano
        ref["nombre"] = (
            f"{nombre}_Pacha{sufijo}"
            if mod["modo_fabricacion"] == "pacha"
            and mod["alcance"] == "total"
            else f"{nombre}_Reengrose{sufijo}")
        ref["rol"] = "refuerzo"
        ref["cara"] = cara
        resultado["refuerzos"].append(ref)

    if mod["modo_fabricacion"] == "pacha":
        resultado["grupo_pacha"] = f"Pacha_{nombre}"
    return resultado


def extras_por_cara(modifier, espesor_panel):
    """Devuelve el espesor extra que invade cada cara (+/-) del panel."""
    mod = normalizar_modificador(modifier)
    if not mod["activo"]:
        return (0.0, 0.0)
    extra = float(mod["espesor"] or espesor_panel)
    if mod["cara"] == "ambos":
        return (extra, extra)
    if mod["cara"] == "cara_a":
        return (extra, 0.0)
    return (0.0, extra)


def _cantos_completos(tipo=CANTO_VISTO):
    return {borde: tipo for borde in BORDES}


def resolver_politica_cantos(panel_base, modifier):
    """Traduce el modo de fabricacion en un plan de cantos por pieza."""
    mod = normalizar_modificador(modifier)
    cantos_base = dict(panel_base.get("cantos") or {})
    for borde in BORDES:
        valor = str(cantos_base.get(borde, CANTO_OCULTO)).upper()
        cantos_base[borde] = valor if valor in CANTOS_VALIDOS else CANTO_OCULTO

    if not mod["activo"]:
        return {"base": cantos_base, "tira": {}, "bloque": {}}
    if mod["modo_fabricacion"] == "independiente":
        return {
            "base": cantos_base,
            "tira": _cantos_completos(CANTO_VISTO),
            "bloque": {},
        }
    return {
        "base": _cantos_completos(CANTO_OCULTO),
        "tira": _cantos_completos(CANTO_OCULTO),
        "bloque": _cantos_completos(CANTO_VISTO),
    }


def despiece_panel(nombre, largo, ancho, espesor, modifier,
                   cantos=None, material_ref="melamina_standar",
                   orientacion="vertical"):
    """Devuelve las subpiezas fisicas de un panel con reengrose."""
    panel = {
        "nombre": nombre,
        "largo": float(largo),
        "ancho": float(ancho),
        "espesor": float(espesor),
        "cantos": dict(cantos or {}),
        "material_ref": material_ref,
    }
    mod = normalizar_modificador(modifier)
    geo = calcular_geometria_reengrose(panel, mod)
    plan = resolver_politica_cantos(panel, mod)
    grupo = geo["grupo_pacha"]
    modo = mod["modo_fabricacion"] if mod["activo"] else ""

    piezas = []
    base = geo["base"]
    base.update({
        "tipo": "panel",
        "orientacion": orientacion,
        "cantidad": 1,
        "material_ref": material_ref,
        "cantos": plan["base"],
        "grupo": grupo,
        "grupo_pacha": grupo,
        "operacion": (
            "Encolar + canto de bloque unificado" if grupo
            else ("Cantear por separado" if modo else "")),
        "rol_reengrose": "base",
    })
    piezas.append(base)

    for refuerzo in geo["refuerzos"]:
        refuerzo.update({
            "tipo": "panel",
            "orientacion": orientacion,
            "cantidad": 1,
            "material_ref": material_ref,
            "cantos": plan["tira"],
            "grupo": grupo,
            "grupo_pacha": grupo,
            "operacion": (
                "Encolar + canto de bloque unificado" if grupo
                else "Cantear por separado"),
            "rol_reengrose": "refuerzo",
        })
        if plan["bloque"]:
            refuerzo["cantos_bloque"] = dict(plan["bloque"])
        piezas.append(refuerzo)

    if plan["bloque"] and piezas:
        piezas[0]["cantos_bloque"] = dict(plan["bloque"])
    return piezas


def despiece_caja(caja, modifier, ejes, cantos=None,
                  material_ref="melamina_standar",
                  orientacion="vertical", cantos_bloque=None):
    """Despiece de una pieza de modulo con reengrose.

    ``caja`` usa x/y/z + w/h/d y ``ejes`` define largo/ancho/espesor.
    Devuelve subpiezas con dimensiones de tablero y grupo de pacha.
    """
    mod = normalizar_modificador(modifier)
    geo = calcular_geometria_caja(caja, mod, ejes)
    plan = resolver_politica_cantos({"cantos": cantos or {}}, mod)
    if cantos_bloque is not None:
        plan["bloque"] = dict(cantos_bloque)
    grupo = geo["grupo_pacha"]
    modo = mod["modo_fabricacion"] if mod["activo"] else ""
    dim_key = {"x": "w", "y": "h", "z": "d"}
    ejes = dict(ejes)
    base = geo["base"]

    def medidas(caja_pieza):
        return (
            float(caja_pieza[dim_key[ejes["largo"]]]),
            float(caja_pieza[dim_key[ejes["ancho"]]]),
            float(caja_pieza[dim_key[ejes["espesor"]]]),
        )

    piezas = []
    largo, ancho, espesor = medidas(base)
    piezas.append({
        "nombre": caja.get("nombre", "Pieza"),
        "tipo": "panel",
        "orientacion": orientacion,
        "largo": largo,
        "ancho": ancho,
        "espesor": espesor,
        "cantidad": 1,
        "material_ref": material_ref,
        "cantos": dict(plan["base"]),
        "grupo": grupo,
        "grupo_pacha": grupo,
        "operacion": (
            "Encolar + canto de bloque unificado" if grupo
            else ("Cantear por separado" if modo else "")),
        "rol_reengrose": "base",
    })
    for ref in geo["refuerzos"]:
        largo, ancho, espesor = medidas(ref)
        pieza = {
            "nombre": ref["nombre"],
            "tipo": "panel",
            "orientacion": orientacion,
            "largo": largo,
            "ancho": ancho,
            "espesor": espesor,
            "cantidad": 1,
            "material_ref": material_ref,
            "cantos": dict(plan["tira"]),
            "grupo": grupo,
            "grupo_pacha": grupo,
            "operacion": (
                "Encolar + canto de bloque unificado" if grupo
                else "Cantear por separado"),
            "rol_reengrose": "refuerzo",
        }
        if plan["bloque"]:
            pieza["cantos_bloque"] = dict(plan["bloque"])
        piezas.append(pieza)

    if plan["bloque"] and piezas:
        piezas[0]["cantos_bloque"] = dict(plan["bloque"])
    return piezas


def _aabb(valor):
    if isinstance(valor, dict):
        return (
            float(valor.get("x", 0.0)),
            float(valor.get("y", 0.0)),
            float(valor.get("z", 0.0)),
            float(valor.get("w", valor.get("largo", 0.0))),
            float(valor.get("h", valor.get("ancho", 0.0))),
            float(valor.get("d", valor.get("espesor", 0.0))),
        )
    if isinstance(valor, (list, tuple)) and len(valor) == 6:
        return tuple(float(v) for v in valor)
    raise ReengroseError("AABB invalido: se esperaba dict o tupla de 6.")


def detectar_colision(a, b, tolerancia=1e-6):
    ax, ay, az, aw, ah, ad = _aabb(a)
    bx, by, bz, bw, bh, bd = _aabb(b)
    return not (
        ax + aw <= bx + tolerancia or bx + bw <= ax + tolerancia
        or ay + ah <= by + tolerancia or by + bh <= ay + tolerancia
        or az + ad <= bz + tolerancia or bz + bd <= az + tolerancia
    )


def calcular_vano_neto_con_reengrose(vano_original, division_con_reengrose):
    """Reduce el vano neto segun el lado invadido por el reengrose."""
    vano = dict(vano_original)
    division = dict(division_con_reengrose)
    ancho = float(vano.get("ancho", vano.get("w", 0.0)))
    alto = float(vano.get("alto", vano.get("h", 0.0)))
    extra = float(division.get("espesor_extra", division.get("extra", 0.0)))
    lado = str(division.get("lado_afectado", "")).lower()

    dx = 0.0
    dz = 0.0
    if lado == "izquierda":
        ancho = max(0.0, ancho - extra)
        dx = extra
    elif lado == "derecha":
        ancho = max(0.0, ancho - extra)
    elif lado == "inferior":
        alto = max(0.0, alto - extra)
        dz = extra
    elif lado == "superior":
        alto = max(0.0, alto - extra)

    return {
        "ancho": ancho,
        "alto": alto,
        "desplazamiento_x": dx,
        "desplazamiento_z": dz,
        "lado_afectado": lado,
    }


# =====================================================================
# Anclaje topologico y encuentros entre tiras
# =====================================================================
_EJES = ("x", "y", "z")
_DIM = {"x": "w", "y": "h", "z": "d"}


def _aabb_dict(caja):
    x, y, z, w, h, d = _aabb(caja)
    return {"x": x, "y": y, "z": z, "w": w, "h": h, "d": d}


def _dimensiones(aabb):
    return {"x": aabb[3], "y": aabb[4], "z": aabb[5]}


def _eje_mayor(aabb):
    dims = _dimensiones(aabb)
    return max(_EJES, key=lambda eje: dims[eje])


def _eje_menor(aabb):
    dims = _dimensiones(aabb)
    return min(_EJES, key=lambda eje: dims[eje])


def _eje_restante(aabb, usados):
    dims = _dimensiones(aabb)
    restantes = [eje for eje in _EJES if eje not in usados]
    if not restantes:
        return "y"
    return max(restantes, key=lambda eje: dims[eje])


def _interseccion_aabb(a, b, tolerancia=1e-6):
    ax, ay, az, aw, ah, ad = _aabb(a)
    bx, by, bz, bw, bh, bd = _aabb(b)
    x0 = max(ax, bx)
    x1 = min(ax + aw, bx + bw)
    y0 = max(ay, by)
    y1 = min(ay + ah, by + bh)
    z0 = max(az, bz)
    z1 = min(az + ad, bz + bd)
    if (x1 - x0 <= tolerancia or y1 - y0 <= tolerancia
            or z1 - z0 <= tolerancia):
        return None
    return (x0, y0, z0, x1, y1, z1)


def orientacion_tira(tira):
    """Devuelve 'vertical' u 'horizontal' para una tira AABB."""
    if isinstance(tira, dict):
        pista = str(
            tira.get("orientacion_tira")
            or tira.get("orientacion")
            or tira.get("eje_largo")
            or "").strip().lower()
        if pista in ("vertical", "horizontal"):
            return pista
        if pista == "z":
            return "vertical"
        if pista in ("x", "y"):
            return "horizontal"
    eje = _eje_mayor(_aabb(tira))
    return "vertical" if eje == "z" else "horizontal"


def vector_anclaje_y(panel_real):
    """Vector de anclaje relativo en Y de la cara real del panel.

    El frente funcional VDO es Y-. El resultado nunca usa coordenadas
    absolutas del mueble: nace del BoundingBox real del panel huesped.
    """
    x, y, z, w, h, d = _aabb(panel_real)
    return {
        "frente": y,
        "fondo": y + h,
        "centro": y + h / 2.0,
        "origen": (x, y, z),
    }


def frente_panel(panel_real):
    return vector_anclaje_y(panel_real)["frente"]


def anclar_refuerzo_a_panel(refuerzo, panel_real, alineacion="frente"):
    """Ancla una tira de ancho Y a la cara real del panel padre."""
    datos = _aabb_dict(refuerzo)
    px, py, pz, pw, ph, pd = _aabb(panel_real)
    alineacion = str(alineacion or "frente").strip().lower()
    alto_tira = min(datos["h"], ph)
    if alineacion == "fondo":
        datos["y"] = py + ph - alto_tira
    elif alineacion == "centrado":
        datos["y"] = py + (ph - alto_tira) / 2.0
    else:
        datos["y"] = py
    datos["h"] = alto_tira
    return datos


def anclar_refuerzos_a_panel(panel_real, refuerzos, alineacion="frente"):
    return [
        anclar_refuerzo_a_panel(ref, panel_real, alineacion)
        for ref in (refuerzos or [])
    ]


def recortar_tira_contra_tira(perdedora, ganadora, tolerancia=1e-6):
    """Parte la tira perdedora fuera del volumen de la tira ganadora.

    Devuelve una lista de AABB. En un cruce en T produce dos tramos; en
    una esquina en L deja un solo tramo. No modifica la ganadora.
    """
    inter = _interseccion_aabb(perdedora, ganadora, tolerancia)
    if inter is None:
        return [_aabb_dict(perdedora)]

    base = _aabb_dict(perdedora)
    eje = _eje_mayor(_aabb(perdedora))
    dim = _DIM[eje]
    idx = _EJES.index(eje)
    inicio = base[eje]
    fin = inicio + base[dim]
    corte_ini = inter[idx]
    corte_fin = inter[idx + 3]
    tramos = []
    if corte_ini > inicio + tolerancia:
        tramo = dict(base)
        tramo[dim] = corte_ini - inicio
        tramos.append(tramo)
    if corte_fin < fin - tolerancia:
        tramo = dict(base)
        tramo[eje] = corte_fin
        tramo[dim] = fin - corte_fin
        tramos.append(tramo)
    return tramos


def _plan_inglete(a, b):
    """Datos minimos para construir un bisel a 45 grados en Capa 2."""
    inter = _interseccion_aabb(a, b)
    if inter is None:
        return None
    oa = orientacion_tira(a)
    ob = orientacion_tira(b)
    if oa == ob:
        return None
    vertical = a if oa == "vertical" else b
    horizontal = a if oa == "horizontal" else b
    eje_v = _eje_menor(_aabb(vertical))
    eje_h = _eje_menor(_aabb(horizontal))
    if eje_v == eje_h:
        return None
    extrusion = next(
        eje for eje in _EJES if eje not in (eje_v, eje_h))
    idx_v = _EJES.index(eje_v)
    idx_h = _EJES.index(eje_h)
    idx_e = _EJES.index(extrusion)
    return {
        "plano": "".join(sorted({eje_v.upper(), eje_h.upper()})),
        "eje_vertical": eje_v,
        "eje_horizontal": eje_h,
        "extrusion": extrusion,
        "rango_vertical": (inter[idx_v], inter[idx_v + 3]),
        "rango_horizontal": (inter[idx_h], inter[idx_h + 3]),
        "rango_extrusion": (inter[idx_e], inter[idx_e + 3]),
        "interseccion": _aabb_dict({
            "x": inter[0], "y": inter[1], "z": inter[2],
            "w": inter[3] - inter[0],
            "h": inter[4] - inter[1],
            "d": inter[5] - inter[2],
        }),
    }


def resolver_encuentro_tiras(tira_a, tira_b, prioridad="vertical_domina"):
    """Resuelve el encuentro entre dos tiras sin solape booleano.

    Devuelve las tiras resultantes ya segmentadas. En ``inglete_45``
    devuelve las cajas originales mas un plan de bisel para Capa 2.
    """
    prioridad = _validar_enum(
        prioridad or "vertical_domina", "prioridad_encuentro_tiras",
        PRIORIDADES_ENCUENTRO)
    resultado = {
        "colision": False,
        "modo": prioridad,
        "prioridad": prioridad,
        "orientacion_a": orientacion_tira(tira_a),
        "orientacion_b": orientacion_tira(tira_b),
        "ganador": None,
        "perdedor": None,
        "tira_a": [_aabb_dict(tira_a)],
        "tira_b": [_aabb_dict(tira_b)],
        "recortes": [],
        "inglete": None,
    }
    if not detectar_colision(tira_a, tira_b):
        return resultado

    resultado["colision"] = True
    if prioridad == "inglete_45":
        plan = _plan_inglete(tira_a, tira_b)
        if plan is None:
            prioridad = "vertical_domina"
            resultado["modo"] = prioridad
        else:
            resultado["inglete"] = plan
            return resultado

    oa = resultado["orientacion_a"]
    ob = resultado["orientacion_b"]
    if prioridad == "vertical_domina":
        if ob == "vertical" and oa != "vertical":
            ganador, perdedor = "b", "a"
        else:
            ganador, perdedor = "a", "b"
    else:
        if ob == "horizontal" and oa != "horizontal":
            ganador, perdedor = "b", "a"
        else:
            ganador, perdedor = "a", "b"

    g = tira_a if ganador == "a" else tira_b
    p = tira_b if perdedor == "b" else tira_a
    segmentos = recortar_tira_contra_tira(p, g)
    resultado["ganador"] = ganador
    resultado["perdedor"] = perdedor
    if perdedor == "a":
        resultado["tira_a"] = segmentos
    else:
        resultado["tira_b"] = segmentos
    inter = _interseccion_aabb(tira_a, tira_b)
    if inter is not None:
        resultado["recortes"] = [_aabb_dict({
            "x": inter[0], "y": inter[1], "z": inter[2],
            "w": inter[3] - inter[0],
            "h": inter[4] - inter[1],
            "d": inter[5] - inter[2],
        })]
    return resultado


def resolver_choque_tira_panel(tira, panel_perpendicular, modo="retroceso"):
    """Resuelve el choque entre una tira y un panel perpendicular.

    Es simetrico: sirve tanto para una repisa contra un montante como para
    un montante contra una tira de techo/base.

    Devuelve un plan con ``panel`` ajustado (retroceso recto), ``cortes_panel``
    (mocheo o cajeados) y ``tira_segmentos`` cuando se interrumpe la tira.
    """
    modo = _normalizar_modo_choque(modo)
    inter = _interseccion_aabb(tira, panel_perpendicular)
    if inter is None:
        return None

    tira_t = _aabb(tira)
    panel_t = _aabb(panel_perpendicular)
    eje_largo = _eje_mayor(tira_t)
    eje_corto = _eje_menor(tira_t)
    eje_ancho = _eje_restante(tira_t, {eje_largo, eje_corto})
    eje_normal_panel = _eje_menor(panel_t)
    plan = {
        "colision": True,
        "modo": modo,
        "panel": _aabb_dict(panel_perpendicular),
        "panel_original": _aabb_dict(panel_perpendicular),
        "tira": _aabb_dict(tira),
        "cortes_panel": [],
        "tira_segmentos": [],
        "eje_largo": eje_largo,
        "eje_corto": eje_corto,
        "eje_ancho": eje_ancho,
        "eje_normal_panel": eje_normal_panel,
    }

    if modo == "interrumpir_tira":
        plan["tira_segmentos"] = recortar_tira_contra_tira(
            tira, panel_perpendicular)
        return plan

    if modo == "mocheo":
        plan["cortes_panel"].append(_aabb_dict({
            "x": inter[0], "y": inter[1], "z": inter[2],
            "w": inter[3] - inter[0],
            "h": inter[4] - inter[1],
            "d": inter[5] - inter[2],
        }))
        return plan

    # Retroceso recto clasico: una repisa horizontal frente a un montante
    # vertical retira su profundidad hasta la cara trasera de la tira.
    if eje_normal_panel == "z" and eje_largo == "z" and eje_ancho == "y":
        x, y, z, w, h, d = panel_t
        tx, ty, tz, tw, th, td = tira_t
        cubre_fondo = (
            ty <= y + 1e-6 and ty + th >= y + h - 1e-6)
        if cubre_fondo:
            if tx + tw / 2.0 < x + w / 2.0:
                nuevo_x = max(x, tx + tw)
                plan["panel"] = _aabb_dict({
                    "x": nuevo_x, "y": y, "z": z,
                    "w": max(0.0, x + w - nuevo_x), "h": h, "d": d})
            else:
                plan["panel"] = _aabb_dict({
                    "x": x, "y": y, "z": z,
                    "w": max(0.0, tx - x), "h": h, "d": d})
            return plan
        if ty <= y + 1e-6:
            nuevo_y = max(y, ty + th)
            plan["panel"] = _aabb_dict({
                "x": x, "y": nuevo_y, "z": z,
                "w": w, "h": max(0.0, y + h - nuevo_y), "d": d})
        else:
            plan["panel"] = _aabb_dict({
                "x": x, "y": y, "z": z,
                "w": w, "h": max(0.0, ty - y), "d": d})
        return plan

    # Paneles verticales (o encuentros no clasicos): cajeado recto en la
    # banda exacta de invasion. Esto evita partir la tira del techo.
    plan["cortes_panel"].append(_aabb_dict({
        "x": inter[0], "y": inter[1], "z": inter[2],
        "w": inter[3] - inter[0],
        "h": inter[4] - inter[1],
        "d": inter[5] - inter[2],
    }))
    return plan


def generar_mocheo_repisa(repisa, reengrose_vertical, politica=None):
    """Detecta colision repisa/reengrose y devuelve retroceso o mocheo."""
    if not detectar_colision(repisa, reengrose_vertical):
        return None

    mod = _validar_enum(
        politica or "retroceder", "politica_repisa", POLITICAS_REPISA)
    rx, ry, rz, rw, rh, rd = _aabb(repisa)
    gx, gy, gz, gw, gh, gd = _aabb(reengrose_vertical)

    x0 = max(rx, gx)
    x1 = min(rx + rw, gx + gw)
    y0 = max(ry, gy)
    y1 = min(ry + rh, gy + gh)
    recorte_x = max(0.0, x1 - x0)
    recorte_y = max(0.0, y1 - y0)

    if mod == "mochear":
        return {
            "modo": "mochear",
            "moche": {
                "x": x0 - rx,
                "y": y0 - ry,
                "w": recorte_x,
                "h": recorte_y,
            },
        }

    lado = "derecha" if (gx + gw / 2.0) >= (rx + rw / 2.0) else "izquierda"
    return {
        "modo": "retroceder",
        "lado": lado,
        "recorte_x": recorte_x,
        "recorte_y": recorte_y,
        "ancho_neto": max(0.0, rw - recorte_x),
    }


def desde_objeto(obj):
    datos = {}
    for clave, prop in PROPS.items():
        datos[clave] = getattr(obj, prop, DEFAULTS[clave])
    datos["espesor"] = _a_float(datos.get("espesor"), "espesor")
    if datos.get("espesor") == 0.0:
        datos["espesor"] = None
    return ReengroseModifier(datos)


def aplicar_a_objeto(obj, modifier):
    mod = ReengroseModifier(modifier)
    datos = mod.to_dict()
    for clave, prop in PROPS.items():
        valor = datos[clave]
        if clave == "espesor" and valor is None:
            valor = 0.0
        setattr(obj, prop, valor)
    obj.VDO_Reengrose_JSON = mod.to_json()
    return mod


if __name__ == "__main__":
    # Pruebas de asercion de la Capa 0 (sin FreeCAD ni Qt).
    _panel = {"nombre": "P", "largo": 600, "ancho": 400, "espesor": 18}
    _mod = ReengroseModifier({
        "activo": True, "ancho": 50, "cara": "cara_b",
        "alineacion_profundidad": "frente"})
    _ref = calcular_geometria_reengrose(_panel, _mod)["refuerzos"][0]
    assert _ref["y"] == 0.0

    _caja = {"nombre": "R", "x": 0, "y": 30, "z": 200,
             "w": 500, "h": 300, "d": 18}
    _geo = calcular_geometria_caja(
        _caja, _mod, {"largo": "x", "ancho": "y", "espesor": "z"})
    assert _geo["refuerzos"][0]["y"] == 30.0

    _repisa = {"x": 0, "y": 0, "z": 0, "w": 500, "h": 400, "d": 18}
    _montante = {"x": 480, "y": 0, "z": 0, "w": 18, "h": 50, "d": 400}
    _plan = resolver_choque_tira_panel(_montante, _repisa, "retroceso")
    assert _plan["panel"]["y"] == 50.0
    assert _plan["panel"]["h"] == 350.0

    _techo = {"x": 0, "y": 0, "z": 684, "w": 600, "h": 50, "d": 18}
    _division = {"x": 273, "y": 0, "z": 18, "w": 18, "h": 580, "d": 684}
    _plan = resolver_choque_tira_panel(_techo, _division, "retroceso")
    assert _plan["panel"]["h"] == 580.0
    assert _plan["cortes_panel"]

    _v = {"x": 273, "y": 0, "z": 0, "w": 18, "h": 50, "d": 700}
    _h = {"x": 0, "y": 0, "z": 684, "w": 600, "h": 50, "d": 18}
    _res = resolver_encuentro_tiras(_v, _h, "vertical_domina")
    assert _res["colision"] and _res["ganador"] == "a"
    assert len(_res["tira_b"]) == 2
    for _tramo in _res["tira_b"]:
        assert not detectar_colision(_tramo, _v)

    _res = resolver_choque_tira_panel(_techo, _division, "interrumpir_tira")
    assert _res["tira_segmentos"]
    for _tramo in _res["tira_segmentos"]:
        assert not detectar_colision(_tramo, _division)

    print("vdo_reengrose: pruebas Capa 0 OK")
