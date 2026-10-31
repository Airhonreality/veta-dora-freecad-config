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

BORDES_2D = ("frente", "fondo", "izquierda", "derecha")
ESQUINAS_2D = ("frente_izquierda", "frente_derecha", "fondo_izquierda", "fondo_derecha")
ESQUINAS = ("vertical_domina", "horizontal_domina", "inglete_45", "marco_interior")
ENCUENTROS_ESQUINAS = ESQUINAS
LARGOS_TIRA = ("marco_interior", "punta_a_punta")
DISTANCIA_AL_CANTO_DEFAULT = 0.0
LARGO_TIRA_DEFAULT = "marco_interior"
ENCUENTRO_ESQUINAS_DEFAULT = "vertical_domina"
FABRICACIONES = ("pacha", "independiente")
CHOQUES_NUCLEO = ("retroceso", "mocheo", "interrumpir_tira")
SUFIJOS_BORDE = {
    "frente": "Frente",
    "fondo": "Fondo",
    "izquierda": "Izq",
    "derecha": "Der",
}


class BordeConfig:
    """Configuracion de un borde del tablero.

    Vocabulario de taller:
      - ``distancia_al_canto``: distancia desde el canto del tablero hacia
        adentro (0 = al ras).
      - ``largo_tira``: ``marco_interior`` (respeta la luz de las esquinas)
        o ``punta_a_punta`` (de orilla a orilla del tablero).
      - ``encuentro_esquinas``: como se resuelve el cruce con otro borde.
    """

    def __init__(self, activo=False, ancho=70.0, distancia_al_canto=None,
                 largo_tira=LARGO_TIRA_DEFAULT, espesor=None,
                 encuentro_esquinas=None, offset_borde=None):
        self.activo = bool(activo)
        self.ancho = float(ancho)
        if distancia_al_canto is None:
            distancia_al_canto = (
                offset_borde if offset_borde is not None
                else DISTANCIA_AL_CANTO_DEFAULT)
        self.distancia_al_canto = float(distancia_al_canto)
        self.largo_tira = str(largo_tira or LARGO_TIRA_DEFAULT)
        self.encuentro_esquinas = encuentro_esquinas
        self.espesor = espesor

    @property
    def offset_borde(self):
        """Alias retrocompatible de ``distancia_al_canto``."""
        return self.distancia_al_canto

    @offset_borde.setter
    def offset_borde(self, valor):
        self.distancia_al_canto = float(valor)

    def to_dict(self):
        return {
            "activo": self.activo,
            "ancho": self.ancho,
            "distancia_al_canto": self.distancia_al_canto,
            "largo_tira": self.largo_tira,
            "encuentro_esquinas": self.encuentro_esquinas,
            "espesor": self.espesor,
            "offset_borde": self.distancia_al_canto,
        }

    @classmethod
    def from_dict(cls, datos):
        datos = datos or {}
        return cls(
            activo=datos.get("activo", False),
            ancho=datos.get("ancho", 70.0),
            distancia_al_canto=datos.get("distancia_al_canto"),
            largo_tira=datos.get("largo_tira", LARGO_TIRA_DEFAULT),
            espesor=datos.get("espesor"),
            encuentro_esquinas=datos.get("encuentro_esquinas"),
            offset_borde=datos.get("offset_borde"))


class ReengroseDTO:
    """DTO universal de bordes 2D."""

    def __init__(self, activo=False, esquinas="vertical_domina",
                 fabricacion="pacha", choque_nucleo="retroceso",
                 bordes=None):
        self.activo = bool(activo)
        self.esquinas = esquinas
        self.fabricacion = fabricacion
        self.choque_nucleo = choque_nucleo
        self.bordes = {}
        for borde in BORDES_2D:
            cfg = (bordes or {}).get(borde)
            if isinstance(cfg, BordeConfig):
                self.bordes[borde] = cfg
            else:
                self.bordes[borde] = BordeConfig.from_dict(cfg)

    def to_dict(self):
        return {
            "activo": self.activo,
            "esquinas": self.esquinas,
            "fabricacion": self.fabricacion,
            "choque_nucleo": self.choque_nucleo,
            "bordes": {
                borde: cfg.to_dict()
                for borde, cfg in self.bordes.items()
            },
            "usa_bordes": True,
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
    """DTO puro del modificador de reengrose.

    Mantiene las propiedades planas historicas (orientacion, ancho, cara,
    etc.) y expone ademas ``bordes`` como ``BordeConfig`` para la nueva UI
    de modificador universal.
    """

    def __init__(self, datos=None):
        datos = normalizar_modificador(datos)
        for clave, valor in datos.items():
            if clave == "bordes":
                self.bordes = {
                    borde: BordeConfig.from_dict(cfg)
                    for borde, cfg in valor.items()
                }
            else:
                setattr(self, clave, valor)

    def to_dict(self):
        datos = {clave: getattr(self, clave) for clave in PROPS}
        datos.update({
            "esquinas": self.esquinas,
            "fabricacion": self.fabricacion,
            "choque_nucleo": self.choque_nucleo,
            "bordes": {
                borde: cfg.to_dict()
                for borde, cfg in self.bordes.items()
            },
            "usa_bordes": bool(getattr(self, "usa_bordes", False)),
        })
        return datos

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


def _normalizar_borde_config(datos, ancho_defecto=70.0,
                             espesor_defecto=None):
    if isinstance(datos, BordeConfig):
        datos = datos.to_dict()
    datos = dict(datos or {})
    activo = _a_bool(datos.get("activo", False))
    ancho = _a_float(datos.get("ancho", ancho_defecto), "ancho")
    if ancho is None:
        ancho = float(ancho_defecto)
    distancia = datos.get("distancia_al_canto")
    if distancia is None or distancia == "":
        distancia = datos.get("offset_borde", DISTANCIA_AL_CANTO_DEFAULT)
    distancia = _a_float(distancia, "distancia_al_canto")
    if distancia is None:
        distancia = DISTANCIA_AL_CANTO_DEFAULT
    largo_tira = _validar_enum(
        datos.get("largo_tira", LARGO_TIRA_DEFAULT),
        "largo_tira", LARGOS_TIRA)
    encuentro = datos.get("encuentro_esquinas")
    if encuentro in (None, ""):
        encuentro = None
    else:
        encuentro = _validar_enum(
            encuentro, "encuentro_esquinas", ENCUENTROS_ESQUINAS)
    espesor = _a_float(datos.get("espesor"), "espesor")
    if espesor is not None and espesor <= 0:
        raise ReengroseError("El espesor de la tira debe ser mayor que 0.")
    if ancho < 0:
        raise ReengroseError("El ancho de la tira no puede ser negativo.")
    if activo and ancho <= 0:
        raise ReengroseError("El ancho del borde activo debe ser mayor que 0.")
    if distancia < 0:
        raise ReengroseError(
            "La distancia_al_canto no puede ser negativa.")
    return {
        "activo": activo,
        "ancho": float(ancho),
        "distancia_al_canto": float(distancia),
        "largo_tira": largo_tira,
        "encuentro_esquinas": encuentro,
        "espesor": espesor,
        "offset_borde": float(distancia),
    }


def _normalizar_bordes(datos, ancho_defecto=70.0, espesor_defecto=None):
    datos = datos or {}
    return {
        borde: _normalizar_borde_config(
            datos.get(borde), ancho_defecto, espesor_defecto)
        for borde in BORDES_2D
    }


def _bordes_desde_legacy(datos):
    ancho = float(datos["ancho"])
    espesor = datos["espesor"]
    bordes = {
        borde: {
            "activo": False, "ancho": ancho,
            "distancia_al_canto": 0.0,
            "largo_tira": LARGO_TIRA_DEFAULT,
            "encuentro_esquinas": None,
            "espesor": espesor,
            "offset_borde": 0.0,
        }
        for borde in BORDES_2D
    }
    if datos["activo"] and datos["modo_fabricacion"] != "pacha":
        if datos["orientacion"] == "paralela":
            if datos["alineacion_profundidad"] in ("frente", "fondo"):
                borde = datos["alineacion_profundidad"]
                bordes[borde]["activo"] = True
        elif datos["orientacion"] == "transversal":
            # El modo transversal historico no es un borde: se conserva
            # como geometria legacy y no se usa como marco perimetral.
            pass
    return bordes


def _legacy_desde_bordes(activo, bordes, esquinas, fabricacion,
                         choque, datos):
    activos = [borde for borde in BORDES_2D
               if bordes[borde]["activo"]]
    primero = bordes[activos[0]] if activos else None
    ancho = primero["ancho"] if primero else _a_float(
        datos.get("ancho", DEFAULTS["ancho"]), "ancho")
    espesor = primero["espesor"] if primero else _a_float(
        datos.get("espesor"), "espesor")
    if any(b in activos for b in ("frente", "fondo")):
        orientacion = "paralela"
    elif any(b in activos for b in ("izquierda", "derecha")):
        orientacion = "transversal"
    else:
        orientacion = "paralela"
    if "frente" in activos:
        alineacion = "frente"
    elif "fondo" in activos:
        alineacion = "fondo"
    else:
        alineacion = "centrado"
    cara = _validar_enum(
        datos.get("cara", DEFAULTS["cara"]), "cara", CARAS)
    return {
        "activo": bool(activo),
        "orientacion": orientacion,
        "ancho": ancho if ancho and ancho > 0 else DEFAULTS["ancho"],
        "espesor": espesor,
        "cara": cara,
        "alineacion_profundidad": alineacion,
        "modo_fabricacion": fabricacion,
        "alcance": "parcial",
        "politica_repisa": _MAPA_MODO_LEGACY[choque],
        "prioridad_encuentro_tiras": _prioridad_legacy_desde_esquinas(
            esquinas),
        "comportamiento_choque_nucleo": choque,
    }


def normalizar_modificador(datos=None):
    if isinstance(datos, ReengroseDTO):
        datos = datos.to_dict()
    if isinstance(datos, ReengroseModifier):
        datos = datos.to_dict()
    if datos is None:
        datos = {}
    if not isinstance(datos, dict):
        raise ReengroseError("El modificador de reengrose debe ser un dict.")
    if "modificador_reengrose" in datos:
        datos = datos["modificador_reengrose"] or {}

    if "usa_bordes" in datos:
        nuevo = _a_bool(datos.get("usa_bordes"))
    else:
        nuevo = any(
            clave in datos for clave in
            ("bordes", "esquinas", "fabricacion", "choque_nucleo"))

    if nuevo:
        activo = _a_bool(datos.get("activo", DEFAULTS["activo"]))
        esquinas = _normalizar_encuentro(
            datos.get("esquinas", DEFAULTS["prioridad_encuentro_tiras"]))
        fabricacion = _validar_enum(
            datos.get("fabricacion", DEFAULTS["modo_fabricacion"]),
            "fabricacion", FABRICACIONES)
        choque = _normalizar_modo_choque(
            datos.get("choque_nucleo",
                      datos.get("comportamiento_choque_nucleo",
                                DEFAULTS["comportamiento_choque_nucleo"])),
            "choque_nucleo")
        bordes = _normalizar_bordes(datos.get("bordes"))
        resultado = _legacy_desde_bordes(
            activo, bordes, esquinas, fabricacion, choque, datos)
        resultado.update({
            "esquinas": esquinas,
            "fabricacion": fabricacion,
            "choque_nucleo": choque,
            "bordes": bordes,
            "usa_bordes": True,
        })
        return resultado

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

    resultado = {
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
    bordes = _bordes_desde_legacy(resultado)
    resultado.update({
        "esquinas": prioridad,
        "fabricacion": modo,
        "choque_nucleo": modo_nucleo,
        "bordes": bordes,
        "usa_bordes": False,
    })
    return resultado

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


def _poligono_rect(x0, y0, x1, y1):
    if x1 - x0 <= 1e-9 or y1 - y0 <= 1e-9:
        return []
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _clip_poligono(poligono, a, b, c, sentido=1.0, tolerancia=1e-9):
    """Recorta un poligono contra la semirrecta a*x+b*y=c.

    ``sentido=1`` conserva a*x+b*y >= c; ``sentido=-1`` conserva <=.
    """
    if not poligono:
        return []
    salida = []
    total = len(poligono)
    for i, punto in enumerate(poligono):
        siguiente = poligono[(i + 1) % total]
        f0 = sentido * (a * punto[0] + b * punto[1] - c)
        f1 = sentido * (a * siguiente[0] + b * siguiente[1] - c)
        dentro0 = f0 >= -tolerancia
        dentro1 = f1 >= -tolerancia
        if dentro0:
            salida.append(punto)
        if dentro0 != dentro1:
            den = f0 - f1
            if abs(den) <= 1e-15:
                continue
            t = f0 / den
            salida.append((
                punto[0] + t * (siguiente[0] - punto[0]),
                punto[1] + t * (siguiente[1] - punto[1])))
    limpio = []
    for punto in salida:
        if not limpio or (
                abs(punto[0] - limpio[-1][0]) > 1e-9
                or abs(punto[1] - limpio[-1][1]) > 1e-9):
            limpio.append(punto)
    if len(limpio) > 1 and (
            abs(limpio[0][0] - limpio[-1][0]) <= 1e-9
            and abs(limpio[0][1] - limpio[-1][1]) <= 1e-9):
        limpio.pop()
    return limpio


def _normalizar_encuentro(encuentro_esquinas):
    """Devuelve dict {esquina: tipo} a partir de un str global o un dict."""
    if isinstance(encuentro_esquinas, dict):
        resultado = {}
        for esquina in ESQUINAS_2D:
            valor = encuentro_esquinas.get(esquina, ENCUENTRO_ESQUINAS_DEFAULT)
            resultado[esquina] = _validar_enum(
                valor, "encuentro_esquinas", ENCUENTROS_ESQUINAS)
        return resultado
    # str global: se aplica a las 4 esquinas (compatibilidad).
    tipo = _validar_enum(
        encuentro_esquinas, "encuentro_esquinas", ENCUENTROS_ESQUINAS)
    return {esquina: tipo for esquina in ESQUINAS_2D}


def _prioridad_legacy_desde_esquinas(esquinas):
    """Deriva el enum legacy ``prioridad_encuentro_tiras`` desde el dict."""
    if isinstance(esquinas, str):
        if esquinas in PRIORIDADES_ENCUENTRO:
            return esquinas
        return ENCUENTRO_ESQUINAS_DEFAULT
    valores = {
        (esquinas or {}).get(esquina, ENCUENTRO_ESQUINAS_DEFAULT)
        for esquina in ESQUINAS_2D
    }
    if len(valores) == 1:
        unico = valores.pop()
        return unico if unico in PRIORIDADES_ENCUENTRO else (
            ENCUENTRO_ESQUINAS_DEFAULT)
    primero = (esquinas or {}).get(
        ESQUINAS_2D[0], ENCUENTRO_ESQUINAS_DEFAULT)
    return primero if primero in PRIORIDADES_ENCUENTRO else (
        ENCUENTRO_ESQUINAS_DEFAULT)


def _esquina_bordes(esquina):
    """Devuelve el par de bordes (horizontal, vertical) que se unen en la esquina."""
    return {
        "frente_izquierda": ("frente", "izquierda"),
        "frente_derecha": ("frente", "derecha"),
        "fondo_izquierda": ("fondo", "izquierda"),
        "fondo_derecha": ("fondo", "derecha"),
    }[esquina]


def _inglete_clip(poligonos, rects, esquina, borde_h, borde_v, largo, ancho):
    """Aplica corte a 45° (miter) en una esquina entre dos bordes activos."""
    h0, h1 = rects[borde_h][1], rects[borde_h][3]  # rango Y del borde horizontal
    v0, v1 = rects[borde_v][0], rects[borde_v][2]  # rango X del borde vertical
    if esquina == "frente_izquierda":
        poligonos[borde_h] = _clip_poligono(
            poligonos[borde_h], -1.0, 1.0, h0 - v0, -1.0)
        poligonos[borde_v] = _clip_poligono(
            poligonos[borde_v], 1.0, -1.0, v0 - h0, -1.0)
    elif esquina == "frente_derecha":
        poligonos[borde_h] = _clip_poligono(
            poligonos[borde_h], 1.0, 1.0, v1 + h0, -1.0)
        poligonos[borde_v] = _clip_poligono(
            poligonos[borde_v], 1.0, 1.0, v1 + h0, 1.0)
    elif esquina == "fondo_izquierda":
        poligonos[borde_h] = _clip_poligono(
            poligonos[borde_h], 1.0, 1.0, v0 + h1, 1.0)
        poligonos[borde_v] = _clip_poligono(
            poligonos[borde_v], 1.0, 1.0, v0 + h1, -1.0)
    elif esquina == "fondo_derecha":
        poligonos[borde_h] = _clip_poligono(
            poligonos[borde_h], -1.0, 1.0, h1 - v1, 1.0)
        poligonos[borde_v] = _clip_poligono(
            poligonos[borde_v], -1.0, 1.0, h1 - v1, -1.0)


def generar_tiras_perimetrales(largo_tablero, ancho_tablero, bordes,
                               espesor_madre,
                               encuentro_esquinas=ENCUENTRO_ESQUINAS_DEFAULT):
    """Primitiva perimetral 2D con lenguaje limpio de taller.

    Coordenadas del tablero: x = largo (0..largo_tablero),
    y = ancho/profundidad (0..ancho_tablero).

    Cada borde acepta:
      - ``distancia_al_canto``: separacion desde el canto hacia adentro.
      - ``largo_tira``: ``marco_interior`` o ``punta_a_punta``.
      - ``encuentro_esquinas``: ``vertical_domina``,
        ``horizontal_domina``, ``inglete_45`` o ``marco_interior``.
        Puede ser un str (aplica a las 4 esquinas) o un dict por esquina.

    Reglas de esquina (el tipo de esquina manda sobre el recorte final):
      - vertical_domina: el borde vertical (izq/der) llega al canto; el
        horizontal hace tope.
      - horizontal_domina: el borde horizontal (frente/fondo) llega al
        canto; el vertical hace tope.
      - marco_interior: ninguno llega al canto exterior; hueco en la esquina.
      - inglete_45: ambos llegan al canto con corte a 45° (miter).
    """
    largo = float(largo_tablero)
    ancho = float(ancho_tablero)
    if largo <= 0 or ancho <= 0:
        return []
    encuentro_por_esquina = _normalizar_encuentro(encuentro_esquinas)

    cfgs = {}
    for borde in BORDES_2D:
        cfg = _normalizar_borde_config(
            (bordes or {}).get(borde),
            ancho_defecto=espesor_madre,
            espesor_defecto=espesor_madre)
        esp = cfg["espesor"]
        if esp is None:
            esp = float(espesor_madre)
        cfgs[borde] = {
            "activo": bool(cfg["activo"]),
            "ancho": min(
                float(cfg["ancho"]),
                largo if borde in ("izquierda", "derecha") else ancho),
            "distancia": float(cfg["distancia_al_canto"]),
            "largo_tira": cfg["largo_tira"],
            "espesor": float(esp),
        }

    activos = {b for b in BORDES_2D if cfgs[b]["activo"]}
    if not activos:
        return []

    # Caja interior definida por los bordes y su distancia al canto.
    x0_box = cfgs["izquierda"]["distancia"] if "izquierda" in cfgs else 0.0
    x1_box = largo - (cfgs["derecha"]["distancia"] if "derecha" in cfgs else 0.0)
    y0_box = cfgs["frente"]["distancia"] if "frente" in cfgs else 0.0
    y1_box = ancho - (cfgs["fondo"]["distancia"] if "fondo" in cfgs else 0.0)

    # Rangos largos base segun largo_tira.
    def long_range(borde):
        cfg = cfgs[borde]
        lt = cfg["largo_tira"]
        es_punta = lt == "punta_a_punta"
        if borde == "frente":
            return (0.0 if es_punta else x0_box,
                    largo if es_punta else x1_box)
        if borde == "fondo":
            return (0.0 if es_punta else x0_box,
                    largo if es_punta else x1_box)
        if borde == "izquierda":
            return (0.0 if es_punta else y0_box,
                    ancho if es_punta else y1_box)
        return (0.0 if es_punta else y0_box,
                ancho if es_punta else y1_box)

    frentex0, frentex1 = long_range("frente")
    fondox0, fondox1 = long_range("fondo")
    izquierday0, izquierday1 = long_range("izquierda")
    derechay0, derechay1 = long_range("derecha")

    # Dimension corta (fija por distancia_al_canto).
    def short_range(borde):
        cfg = cfgs[borde]
        w = max(0.0, cfg["ancho"])
        off = cfg["distancia"]
        if borde == "frente":
            return off, off + w
        if borde == "fondo":
            y1 = ancho - off
            return y1 - w, y1
        if borde == "izquierda":
            return off, off + w
        x1 = largo - off
        return x1 - w, x1

    frente_y0, frente_y1 = short_range("frente")
    fondo_y0, fondo_y1 = short_range("fondo")
    izquierda_x0, izquierda_x1 = short_range("izquierda")
    derecha_x0, derecha_x1 = short_range("derecha")
    izquierday0, izquierday1 = long_range("izquierda")
    derechay0, derechay1 = long_range("derecha")

    def wd(borde):
        return max(0.0, cfgs[borde]["ancho"])

    # Recorte por esquina: el tipo de esquina manda sobre el recorte final.
    if "frente" in activos and "izquierda" in activos:
        tipo = encuentro_por_esquina["frente_izquierda"]
        if tipo == "vertical_domina":
            frentex0 = max(frentex0, x0_box + wd("izquierda"))
        elif tipo == "horizontal_domina":
            izquierday0 = max(izquierday0, y0_box + wd("frente"))
        elif tipo == "marco_interior":
            frentex0 = max(frentex0, x0_box + wd("izquierda"))
            izquierday0 = max(izquierday0, y0_box + wd("frente"))

    if "frente" in activos and "derecha" in activos:
        tipo = encuentro_por_esquina["frente_derecha"]
        if tipo == "vertical_domina":
            frentex1 = min(frentex1, x1_box - wd("derecha"))
        elif tipo == "horizontal_domina":
            derechay0 = max(derechay0, y0_box + wd("frente"))
        elif tipo == "marco_interior":
            frentex1 = min(frentex1, x1_box - wd("derecha"))
            derechay0 = max(derechay0, y0_box + wd("frente"))

    if "fondo" in activos and "izquierda" in activos:
        tipo = encuentro_por_esquina["fondo_izquierda"]
        if tipo == "vertical_domina":
            fondox0 = max(fondox0, x0_box + wd("izquierda"))
        elif tipo == "horizontal_domina":
            izquierday1 = min(izquierday1, y1_box - wd("fondo"))
        elif tipo == "marco_interior":
            fondox0 = max(fondox0, x0_box + wd("izquierda"))
            izquierday1 = min(izquierday1, y1_box - wd("fondo"))

    if "fondo" in activos and "derecha" in activos:
        tipo = encuentro_por_esquina["fondo_derecha"]
        if tipo == "vertical_domina":
            fondox1 = min(fondox1, x1_box - wd("derecha"))
        elif tipo == "horizontal_domina":
            derechay1 = min(derechay1, y1_box - wd("fondo"))
        elif tipo == "marco_interior":
            fondox1 = min(fondox1, x1_box - wd("derecha"))
            derechay1 = min(derechay1, y1_box - wd("fondo"))

    def sane(x0, x1):
        if x1 < x0:
            x1 = x0
        return x0, x1

    frentex0, frentex1 = sane(frentex0, frentex1)
    fondox0, fondox1 = sane(fondox0, fondox1)
    izquierday0, izquierday1 = sane(izquierday0, izquierday1)
    derechay0, derechay1 = sane(derechay0, derechay1)

    rects = {
        "frente": [frentex0, frente_y0, frentex1, frente_y1],
        "fondo": [fondox0, fondo_y0, fondox1, fondo_y1],
        "izquierda": [izquierda_x0, izquierday0, izquierda_x1, izquierday1],
        "derecha": [derecha_x0, derechay0, derecha_x1, derechay1],
    }

    poligonos = {}
    for borde in activos:
        x0, y0, x1, y1 = rects[borde]
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        poligonos[borde] = _poligono_rect(x0, y0, x1, y1)

    # Inglete 45° por esquina (sobre parejas activas en esa esquina).
    for esquina in ESQUINAS_2D:
        if encuentro_por_esquina[esquina] != "inglete_45":
            continue
        borde_h, borde_v = _esquina_bordes(esquina)
        if borde_h not in activos or borde_v not in activos:
            continue
        _inglete_clip(poligonos, rects, esquina, borde_h, borde_v, largo, ancho)

    tiras = []
    for borde in BORDES_2D:
        if borde not in activos:
            continue
        poly = poligonos.get(borde) or []
        if len(poly) < 3:
            continue
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        if x1 - x0 <= 1e-9 or y1 - y0 <= 1e-9:
            continue
        ancho_borde = float(x1 - x0)
        largo_borde = float(y1 - y0)
        tiene_inglete = any(
            encuentro_por_esquina[e] == "inglete_45"
            for e in ESQUINAS_2D
            if borde in _esquina_bordes(e))
        tira = {
            "borde": borde,
            "nombre_sufijo": SUFIJOS_BORDE[borde],
            "x": float(x0),
            "y": float(y0),
            "w": ancho_borde,
            "h": largo_borde,
            "largo": max(ancho_borde, largo_borde),
            "ancho": min(ancho_borde, largo_borde),
            "d": float(cfgs[borde]["espesor"]),
            "espesor": float(cfgs[borde]["espesor"]),
            "distancia_al_canto": float(cfgs[borde]["distancia"]),
            "largo_tira": cfgs[borde]["largo_tira"],
            "encuentro_esquinas": dict(encuentro_por_esquina),
            "offset_borde": float(cfgs[borde]["distancia"]),
        }
        if tiene_inglete:
            tira["poligono"] = [
                (float(px), float(py)) for px, py in poly]
            tira["esquinas"] = "inglete_45"
        tiras.append(tira)
    return tiras


def generar_geometria_tiras_perimetrales(ancho_tablero, largo_tablero,
                                         reengrose_dto, espesor_madre):
    """Compatibilidad: tiras perimetrales desde un ReengroseDTO.

    x = largo (0..largo_tablero), y = ancho/profundidad (0..ancho_tablero).
    Devuelve una lista de tiras con x/y/w/h/d y, para inglete, ``poligono``.
    """
    mod = normalizar_modificador(reengrose_dto)
    if not mod["activo"]:
        return []
    return generar_tiras_perimetrales(
        float(largo_tablero), float(ancho_tablero),
        mod["bordes"], espesor_madre, mod["esquinas"])



def _refuerzos_bordes_reengrose(largo, ancho, espesor, nombre, mod):
    tiras = generar_geometria_tiras_perimetrales(
        ancho, largo, mod, espesor)
    caras = ["cara_a", "cara_b"] if mod["cara"] == "ambos" else [mod["cara"]]
    refuerzos = []
    for cara in caras:
        sufijo_cara = ""
        if len(caras) > 1:
            sufijo_cara = "_A" if cara == "cara_a" else "_B"
        for tira in tiras:
            esp_ref = float(tira["d"])
            z0 = espesor if cara == "cara_a" else -esp_ref
            ref = {
                "nombre": (
                    f"{nombre}_Tira_{tira['nombre_sufijo']}{sufijo_cara}"),
                "rol": "refuerzo",
                "largo": float(tira.get("largo", tira["w"])),
                "ancho": float(tira.get("ancho", tira["h"])),
                "espesor": esp_ref,
                "x": float(tira["x"]),
                "y": float(tira["y"]),
                "z": float(z0),
                "w": float(tira["w"]),
                "h": float(tira["h"]),
                "d": esp_ref,
                "borde": tira["borde"],
                "cara": cara,
                "eje_extrusion": "z",
            }
            if tira.get("poligono"):
                ref["poligono"] = [
                    (float(px), float(py), float(z0))
                    for px, py in tira["poligono"]
                ]
            refuerzos.append(ref)
    return refuerzos, tiras


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

    if mod["usa_bordes"]:
        refuerzos, tiras = _refuerzos_bordes_reengrose(
            largo, ancho, espesor, nombre, mod)
        resultado["refuerzos"] = refuerzos
        resultado["tiras"] = tiras
        if mod["fabricacion"] == "pacha" and refuerzos:
            resultado["grupo_pacha"] = f"Pacha_{nombre}"
        return resultado

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
                "w": largo,
                "h": ancho,
                "d": esp_ref,
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
                "w": largo_ref if mod["orientacion"] == "paralela" else ancho_ref,
                "h": ancho_ref if mod["orientacion"] == "paralela" else largo_ref,
                "d": esp_ref,
            }

        resultado["refuerzos"].append(refuerzo)
    if mod["modo_fabricacion"] == "pacha":
        resultado["grupo_pacha"] = f"Pacha_{nombre}"
    return resultado


def _refuerzos_bordes_caja(base, ejes, largo, ancho, espesor,
                           nombre, mod):
    tiras = generar_geometria_tiras_perimetrales(
        ancho, largo, mod, espesor)
    dim_key = {"x": "w", "y": "h", "z": "d"}
    cara_lista = (
        ["cara_a", "cara_b"] if mod["cara"] == "ambos"
        else [mod["cara"]])
    refuerzos = []
    for cara in cara_lista:
        sufijo_cara = ""
        if len(cara_lista) > 1:
            sufijo_cara = "_A" if cara == "cara_a" else "_B"
        for tira in tiras:
            esp_ref = float(tira["d"])
            z_local = espesor if cara == "cara_a" else -esp_ref
            ref = dict(base)
            ref[ejes["largo"]] = base[ejes["largo"]] + float(tira["x"])
            ref[dim_key[ejes["largo"]]] = float(tira["w"])
            ref[ejes["ancho"]] = base[ejes["ancho"]] + float(tira["y"])
            ref[dim_key[ejes["ancho"]]] = float(tira["h"])
            ref[ejes["espesor"]] = base[ejes["espesor"]] + z_local
            ref[dim_key[ejes["espesor"]]] = esp_ref
            ref["nombre"] = (
                f"{nombre}_Tira_{tira['nombre_sufijo']}{sufijo_cara}")
            ref["rol"] = "refuerzo"
            ref["borde"] = tira["borde"]
            ref["cara"] = cara
            ref["eje_extrusion"] = ejes["espesor"]
            if tira.get("poligono"):
                puntos = []
                for px, py in tira["poligono"]:
                    coords = {
                        eje: float(base[eje]) for eje in _EJES
                    }
                    coords[ejes["largo"]] = (
                        base[ejes["largo"]] + float(px))
                    coords[ejes["ancho"]] = (
                        base[ejes["ancho"]] + float(py))
                    coords[ejes["espesor"]] = (
                        base[ejes["espesor"]] + z_local)
                    puntos.append((
                        coords["x"], coords["y"], coords["z"]))
                ref["poligono"] = puntos
            refuerzos.append(ref)
    return refuerzos, tiras


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

    if mod["usa_bordes"]:
        refuerzos, tiras = _refuerzos_bordes_caja(
            base, ejes, largo, ancho, espesor, nombre, mod)
        resultado["refuerzos"] = refuerzos
        resultado["tiras"] = tiras
        if mod["fabricacion"] == "pacha" and refuerzos:
            resultado["grupo_pacha"] = f"Pacha_{nombre}"
        return resultado

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
        # Arrastrar la caja geometrica: es lo unico que sabe DONDE va la
        # subpieza. Sin ella las capas 2/3 materializaban cada division con
        # reengrose y cada tira en el origen, apiladas unas sobre otras
        # (solapes de millones de mm3 en el arbol del COCO).
        "caja_geometrica": dict(base),
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
            "caja_geometrica": dict(ref),
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


def _retroceso_panel(panel_t, tira_t, eje_normal, eje_ancho):
    """Retroceso simetrico panel/tira en el eje de profundidad correcto.

    Si la tira cubre todo el ancho del panel, el panel se retira por su
    eje restante (por ejemplo una division baja para pasar bajo el techo).
    Si solo cubre una franja, el panel retrocede en profundidad hasta la
    cara de la tira. El resultado se expresa como AABB.
    """
    panel = {
        "x": panel_t[0], "y": panel_t[1], "z": panel_t[2],
        "w": panel_t[3], "h": panel_t[4], "d": panel_t[5],
    }
    tira = {
        "x": tira_t[0], "y": tira_t[1], "z": tira_t[2],
        "w": tira_t[3], "h": tira_t[4], "d": tira_t[5],
    }
    dims_p = {"x": panel["w"], "y": panel["h"], "z": panel["d"]}
    dims_t = {"x": tira["w"], "y": tira["h"], "z": tira["d"]}
    tol = 1e-6

    a = eje_ancho
    p0, p1 = panel[a], panel[a] + dims_p[a]
    t0, t1 = tira[a], tira[a] + dims_t[a]
    cubre_ancho = t0 <= p0 + tol and t1 >= p1 - tol

    if cubre_ancho:
        eje = next(
            e for e in _EJES if e not in (eje_normal, eje_ancho))
        p0h, p1h = panel[eje], panel[eje] + dims_p[eje]
        t0h, t1h = tira[eje], tira[eje] + dims_t[eje]
        corte0, corte1 = max(p0h, t0h), min(p1h, t1h)
        if corte1 <= corte0 + tol:
            return _aabb_dict(panel)
        if (t0h + t1h) / 2.0 < (p0h + p1h) / 2.0:
            panel[eje] = corte1
            panel[_DIM[eje]] = max(0.0, p1h - corte1)
        else:
            panel[_DIM[eje]] = max(0.0, corte0 - p0h)
        return _aabb_dict(panel)

    if t0 <= p0 + tol:
        # La tira invade desde el frente del panel: el panel nace detras
        # de su cara posterior y conserva la cota hasta el fondo.
        nuevo = max(p0, t1)
        panel[a] = nuevo
        panel[_DIM[a]] = max(0.0, p1 - nuevo)
    else:
        # La tira esta delante del panel: retroceder el origen hasta su
        # cara posterior. Antes se asignaba la profundidad igual al offset,
        # lo que colapsaba la repisa a una tira flotante.
        nuevo = min(p1, t1)
        panel[a] = nuevo
        panel[_DIM[a]] = max(0.0, p1 - nuevo)
    return _aabb_dict(panel)


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

    # Retroceso simetrico. La tira corre en el mismo eje que la normal del
    # panel (es perpendicular a su cara). El panel retrocede por el eje de
    # ancho de la tira o, si la tira cubre todo ese ancho, por el eje
    # restante. Cubre repisas contra montantes y montantes contra techo/base.
    if eje_largo == eje_normal_panel and eje_ancho != eje_normal_panel:
        plan["panel"] = _retroceso_panel(
            panel_t, tira_t, eje_normal_panel, eje_ancho)
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
    texto = getattr(obj, "VDO_Reengrose_JSON", "") or ""
    if texto:
        try:
            guardado = json.loads(texto)
            if (isinstance(guardado, dict)
                    and any(clave in guardado for clave in
                            ("bordes", "esquinas", "fabricacion",
                             "choque_nucleo"))):
                return ReengroseModifier(guardado)
        except (TypeError, ValueError):
            pass
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
