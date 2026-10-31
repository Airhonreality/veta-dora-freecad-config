# -*- coding: utf-8 -*-
# =====================================================================
# vdo_hub_schema.py
# Primitivas del esquema declarativo de parametros VDO.
#
# POR QUE EXISTE ESTE MODULO
# Antes, cada parametro de un modulo se escribia CINCO veces:
#   1. obj.addProperty(...) en Feature.__init__   (tipo, grupo, ayuda, default)
#   2. _crear_widget() del TaskPanel              (label, rango, sufijo, ayuda)
#   3. _cargar_valores()                          (objeto -> widget)
#   4. accept()                                   (widget -> objeto)
#   5. _config(fp)                                (objeto -> kwargs del motor)
# Cinco sitios y cinco ocasiones de desincronizarse. Peor: el RANGO VALIDO
# solo existia en el widget Qt, asi que editar la propiedad desde el editor
# de FreeCAD, una macro o un test headless se saltaba toda validacion.
#
# Aqui un parametro se declara UNA vez (Param) y de esa declaracion se
# derivan mecanicamente las cinco. La restriccion sube a la capa de datos.
#
# ESTE MODULO NO IMPORTA NADA DE VDO. Es la base de la piramide: lo usan
# vdo_hub_module_props (bloques comunes), vdo_hub_registry (el catalogo),
# vdo_ui_form_builder (la UI inferida) y los Feature de VDO/cad/objects.
# =====================================================================

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

# FreeCAD es OPCIONAL en este modulo a proposito. Las clases Param y
# ModuloSpec son datos puros, y que el catalogo se pueda leer sin arrancar
# FreeCAD es lo que permite que tools/vdo_verify.py y tools/vdo_audit.py
# pregunten por los comandos y los modulos desde python3 pelado. Las
# funciones que SI tocan un objeto de documento solo se llaman dentro de
# FreeCAD, donde el import siempre resuelve.
try:
    import FreeCAD as App
except ImportError:
    App = None


# =====================================================================
# Vocabulario de tipos
# =====================================================================
# Clave corta -> TypeId de FreeCAD. La clave corta es lo que se escribe
# en el esquema; el TypeId es un detalle de la capa de datos.
TYPEID = {
    "length": "App::PropertyLength",
    "angle": "App::PropertyAngle",
    "float": "App::PropertyFloat",
    "int": "App::PropertyInteger",
    "bool": "App::PropertyBool",
    "enum": "App::PropertyEnumeration",
    "string": "App::PropertyString",
    "stringlist": "App::PropertyStringList",
    "placement": "App::PropertyPlacement",
    "link_hidden": "App::PropertyLinkHidden",
    "link_list_child": "App::PropertyLinkListChild",
    "distance": "App::PropertyDistance",
}

# Tipo corto -> clase de control Qt que lo representa. Los tipos ausentes
# (placement, los links, stringlist) NO tienen representacion en el
# formulario inferido: son estructura, no parametros de usuario.
WIDGET = {
    "length": "spin",
    "angle": "spin",
    "float": "spin",
    "int": "spin_int",
    "bool": "check",
    "string": "line",
    "distance": "spin",
}

# Propiedad testigo del tipo de modulo. Es la UNICA via autoritativa para
# saber que es un objeto VDO; sustituye a los predicados por duck-typing
# (_es_coco, _es_cajon, ...) que adivinaban el tipo mirando si el objeto
# tenia tal o cual dimension y que colisionan en cuanto dos modulos se
# parecen. VDO_Subtipo no sirve para esto: arrastra valores historicos
# ("COCO_4C", "cajon_oculta") en documentos ya guardados.
PROP_MODULO = "VDO_Modulo"


# =====================================================================
# Param: la declaracion de un parametro
# =====================================================================

@dataclass(frozen=True)
class Param:
    """Un parametro de modulo, declarado una sola vez.

    Args:
        nombre: nombre de la propiedad FreeCAD (p. ej. "AltoZocalo").
        tipo: clave de TYPEID.
        grupo: grupo de la propiedad Y titulo del QGroupBox en la UI.
        etiqueta: texto del QLabel. Vacio => se usa `nombre`.
        ayuda: tooltip UNICO, compartido por la propiedad y el widget.
        default: valor inicial. Puede ser un callable sin argumentos para
            defaults dinamicos (p. ej. la primera marca de corredera
            disponible en el catalogo de herrajes).
        minimo / maximo: limites validos. Alimentan setRange() en la UI y
            validar() en la capa de datos. None = sin limite.
        decimales: decimales del spinbox.
        sufijo: sufijo del spinbox (" mm", " °").
        opciones: valores del enum. Tupla o callable sin argumentos.
        etiquetas_opciones: {valor: texto legible} para el combo.
        clave_motor: clave con la que este valor entra al motor
            matematico. Si es None el parametro no viaja al motor.
        clave_config: clave con la que este valor llega en el dict de
            creacion de las fabricas make_*(configuracion). Por defecto
            es la misma que clave_motor, que es el caso habitual; se
            declara aparte para los parametros que se pueden fijar al
            crear pero no entran al calculo (SKU de herraje, ID de vano,
            pose...).
        ui: False para propiedades que no se editan en el formulario
            (metadatos, JSON internos, enlaces).
        solo_lectura: se muestra deshabilitado en la UI (lo escribe
            execute(), no el usuario).
        ancho_completo: el control ocupa las dos columnas de la rejilla.
    """

    nombre: str
    tipo: str
    grupo: str = "VDO"
    etiqueta: str = ""
    ayuda: str = ""
    default: Any = None
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    decimales: int = 1
    sufijo: str = ""
    opciones: Union[Sequence[str], Callable[[], Sequence[str]]] = ()
    etiquetas_opciones: Optional[Dict[str, str]] = None
    clave_motor: Optional[str] = None
    clave_config: Optional[str] = None
    ui: bool = True
    solo_lectura: bool = False
    ancho_completo: bool = False

    def __post_init__(self):
        if self.tipo not in TYPEID:
            raise ValueError(
                f"Param '{self.nombre}': tipo '{self.tipo}' desconocido. "
                f"Validos: {', '.join(sorted(TYPEID))}.")

    @property
    def typeid(self) -> str:
        return TYPEID[self.tipo]

    @property
    def titulo(self) -> str:
        return self.etiqueta or self.nombre

    @property
    def widget(self) -> Optional[str]:
        return WIDGET.get(self.tipo)

    @property
    def en_formulario(self) -> bool:
        """El parametro se representa en el formulario inferido."""
        return bool(self.ui and self.widget)

    @property
    def clave_de_config(self) -> Optional[str]:
        """Clave con la que llega en el dict de creacion."""
        return self.clave_config or self.clave_motor

    def valores(self) -> Tuple[str, ...]:
        """Opciones del enum, resolviendo el callable si lo hay."""
        ops = self.opciones() if callable(self.opciones) else self.opciones
        return tuple(ops or ())

    def valor_inicial(self) -> Any:
        """Default, resolviendo el callable si lo hay."""
        return self.default() if callable(self.default) else self.default

    def etiqueta_de(self, valor: str) -> str:
        if self.etiquetas_opciones:
            return self.etiquetas_opciones.get(valor, valor)
        return valor


def bloque(params: Sequence[Param], grupo: str) -> Tuple[Param, ...]:
    """Reetiqueta un bloque de params a otro grupo.

    Util para reutilizar un bloque comun (pose, reengrose) colocandolo en
    una pestana distinta segun el modulo.
    """
    return tuple(replace(p, grupo=grupo) for p in params)


# =====================================================================
# ModuloSpec: el contrato de un modulo geometrico
# =====================================================================

@dataclass(frozen=True)
class ModuloSpec:
    """Contrato completo de un modulo geometrico VDO.

    Las rutas a clases y funciones son cadenas "modulo:nombre" y se
    resuelven de forma perezosa (ver `resolver`). Asi el registro se puede
    importar en headless y sin Qt sin arrastrar media aplicacion.

    Args:
        tipo: clave canonica del modulo ("zocalo", "cajon", ...). Es el
            valor que se graba en VDO_Modulo.
        etiqueta: nombre legible.
        vdo_tipo: "panel" | "contenedor". Lo consume la lista de corte
            (vdo_cam_cutlist); un valor fuera de estos dos hace que el
            modulo sea INVISIBLE para fabricacion.
        vdo_subtipo: subtipo historico. Se conserva tal cual estaba en los
            documentos ya guardados.
        feature / viewprovider / fabrica: "modulo:nombre" de la capa CAD.
        panel: "modulo:clase" del TaskPanel.
        params: declaracion completa de parametros.
        motor: "modulo:funcion" del calculo geometrico puro.
        publica_despiece: el modulo debe dejar su despiece en
            VDO_Paneles_JSON o materializarlo como PanelFeature hijos.
        legacy_props: propiedades que identifican a este modulo en
            documentos guardados ANTES de que existiera VDO_Modulo. Solo
            se usan como respaldo de resolver_modulo().
    """

    tipo: str
    etiqueta: str
    vdo_tipo: str
    vdo_subtipo: str
    feature: str
    viewprovider: str
    fabrica: str
    panel: str
    params: Tuple[Param, ...] = ()
    motor: Optional[str] = None
    publica_despiece: bool = True
    legacy_props: Tuple[str, ...] = ()

    # -----------------------------------------------------------------
    def params_formulario(self) -> Tuple[Param, ...]:
        return tuple(p for p in self.params if p.en_formulario)

    def grupos(self) -> Tuple[str, ...]:
        """Grupos en orden de primera aparicion (orden de los GroupBox)."""
        vistos = []
        for p in self.params_formulario():
            if p.grupo not in vistos:
                vistos.append(p.grupo)
        return tuple(vistos)

    def params_de(self, grupo: str) -> Tuple[Param, ...]:
        return tuple(p for p in self.params_formulario() if p.grupo == grupo)

    def param(self, nombre: str) -> Optional[Param]:
        for p in self.params:
            if p.nombre == nombre:
                return p
        return None

    def params_motor(self) -> Tuple[Param, ...]:
        return tuple(p for p in self.params if p.clave_motor)

    def params_config(self) -> Tuple[Param, ...]:
        return tuple(p for p in self.params if p.clave_de_config)


@dataclass(frozen=True)
class VarianteCreacion:
    """Una entrada de toolbar/menu que crea un modulo.

    Un mismo ModuloSpec puede tener varias variantes: "panel estandar",
    "panel fachada" y "panel division" son el MISMO contrato de datos con
    distinta configuracion de creacion. Separar variante de contrato es lo
    que permite que el registro de datos no se multiplique por las
    entradas de la barra de herramientas.
    """

    clave: str
    modulo: str
    etiqueta: str
    icono: str
    comando: str
    menu_text: str
    tooltip: str
    config: Dict[str, Any] = field(default_factory=dict)
    orden: int = 100
    # Bloque de la barra "VDO Muebles" en el que cae, separado del resto
    # por un Separator: "modulos" (muebles completos) o "piezas" (tableros
    # y repisas sueltas). Se declara en vez de deducirlo de vdo_tipo, que
    # no distingue un COCO de una repisa entamborada.
    grupo_barra: str = "modulos"
    # False para las variantes creables por API/macro pero sin boton
    # propio en la barra.
    en_barra: bool = True


# =====================================================================
# Resolucion perezosa de "modulo:nombre"
# =====================================================================

def _avisar(mensaje):
    """Aviso por la consola de FreeCAD si la hay; si no, silencio."""
    if App is not None:
        App.Console.PrintWarning(mensaje + "\n")


def resolver(ruta: str):
    """Importa y devuelve el objeto apuntado por "paquete.modulo:nombre"."""
    if ":" not in ruta:
        raise ValueError(
            f"Ruta de esquema invalida: '{ruta}'. Formato: 'modulo:nombre'.")
    modulo, nombre = ruta.split(":", 1)
    mod = __import__(modulo, fromlist=[nombre])
    return getattr(mod, nombre)


# =====================================================================
# Capa de datos: declarar las propiedades
# =====================================================================

def aplicar_param(obj, p: Param) -> bool:
    """Declara un Param como propiedad de `obj`. Idempotente.

    Devuelve True si la creo, False si ya existia.

    El orden de las dos asignaciones del enum no es cosmetico:
    addProperty() devuelve el propio objeto, y hay que asignarle PRIMERO
    la LISTA de valores admitidos y DESPUES el valor por defecto. Al
    reves, FreeCAD rechaza el valor porque todavia no conoce el dominio.
    """
    if hasattr(obj, p.nombre):
        return False

    obj.addProperty(p.typeid, p.nombre, p.grupo, p.ayuda)

    if p.tipo == "enum":
        valores = p.valores()
        if valores:
            setattr(obj, p.nombre, list(valores))
        inicial = p.valor_inicial()
        if inicial is not None:
            setattr(obj, p.nombre, inicial)
        return True

    inicial = p.valor_inicial()
    if inicial is None:
        return True
    if p.tipo == "int":
        inicial = int(inicial)
    elif p.tipo in ("length", "angle", "float"):
        inicial = float(inicial)
    setattr(obj, p.nombre, inicial)
    return True


def aplicar_params(obj, params: Sequence[Param]) -> int:
    """Declara un bloque de Params. Devuelve cuantos creo."""
    return sum(1 for p in params if aplicar_param(obj, p))


def aplicar_esquema(obj, spec: ModuloSpec) -> int:
    """Declara TODAS las propiedades de un modulo a partir de su esquema.

    Sustituye la cadena de obj.addProperty() de Feature.__init__.
    Idempotente: se puede llamar sobre un objeto restaurado de disco para
    anadirle las propiedades que falten (migracion hacia delante).
    """
    creadas = aplicar_params(obj, spec.params)

    # Testigo del tipo. No se declara en spec.params porque es identico en
    # todos los modulos y su valor lo fija el propio esquema.
    if not hasattr(obj, PROP_MODULO):
        obj.addProperty(
            "App::PropertyString", PROP_MODULO, "VDO",
            "Clave de modulo VDO (testigo de tipo; no editar)")
        creadas += 1
    # Se reescribe siempre: si el esquema cambia de clave, el objeto la
    # adopta al abrirse.
    setattr(obj, PROP_MODULO, spec.tipo)
    return creadas


# =====================================================================
# Capa de datos -> motor
# =====================================================================

def _valor_python(obj, p: Param):
    """Lee una propiedad y la devuelve como tipo Python plano.

    FreeCAD devuelve Quantity para length/angle; el motor matematico es
    agnostico de FreeCAD y espera floats.
    """
    valor = getattr(obj, p.nombre)
    if p.tipo in ("length", "angle", "float"):
        return float(valor)
    if p.tipo == "int":
        return int(valor)
    if p.tipo == "bool":
        return bool(valor)
    if p.tipo in ("enum", "string"):
        return str(valor)
    return valor


def config_desde_objeto(obj, spec: ModuloSpec) -> Dict[str, Any]:
    """Construye el dict de entrada del motor desde las propiedades.

    Sustituye a los `_config(fp)` escritos a mano.
    """
    config = {}
    for p in spec.params_motor():
        if hasattr(obj, p.nombre):
            config[p.clave_motor] = _valor_python(obj, p)
    return config


def _coaccionar(p: Param, valor):
    """Lleva un valor del dict de creacion al tipo de la propiedad."""
    if valor is None:
        return None
    if p.tipo == "int":
        return int(valor)
    if p.tipo in ("length", "angle", "float"):
        return float(valor)
    if p.tipo == "bool":
        return bool(valor)
    if p.tipo in ("enum", "string"):
        return str(valor)
    return valor


def aplicar_config(obj, spec: ModuloSpec, configuracion) -> Tuple[str, ...]:
    """Escribe en `obj` los valores presentes en un dict de creacion.

    Sustituye al bloque de asignaciones literales que cada fabrica
    make_*() repetia:

        obj.Ancho = configuracion.get("ancho", 600.0)
        obj.AltoZocalo = configuracion.get("alto_zocalo", 100.0)
        ...

    Ese bloque era un CUARTO sitio donde vivian los valores por defecto,
    y divergia de los de Feature.__init__ sin que nada lo detectase (en
    el zocalo, por ejemplo, el default de EspesorTablero salia del
    manifiesto en __init__ y se repetia a mano en la fabrica). Ahora el
    default esta solo en el esquema: la fabrica unicamente aplica lo que
    el llamador pasa explicitamente.

    Devuelve los nombres de propiedad escritos.
    """
    configuracion = configuracion or {}
    escritas = []
    for p in spec.params_config():
        clave = p.clave_de_config
        if clave not in configuracion:
            continue
        if not hasattr(obj, p.nombre):
            continue
        try:
            setattr(obj, p.nombre, _coaccionar(p, configuracion[clave]))
            escritas.append(p.nombre)
        except Exception as exc:
            _avisar(
                f"[VDO] {getattr(obj, 'Name', '?')}.{p.nombre}: no se pudo "
                f"aplicar '{clave}'={configuracion[clave]!r} ({exc}).")
    return tuple(escritas)


# =====================================================================
# Validacion (vive en la capa de datos, no en el widget)
# =====================================================================

def validar(obj, spec: ModuloSpec) -> Tuple[str, ...]:
    """Comprueba los limites del esquema sobre un objeto ya escrito.

    Devuelve una tupla de mensajes; vacia si todo esta en rango. Antes
    estos limites solo existian como setRange() del spinbox, de modo que
    cualquier via que no fuese el TaskPanel (editor de propiedades, macro,
    test headless) los ignoraba por completo.
    """
    errores = []
    for p in spec.params:
        if not hasattr(obj, p.nombre):
            continue
        try:
            valor = _valor_python(obj, p)
        except Exception as exc:
            errores.append(f"{p.titulo}: valor ilegible ({exc}).")
            continue

        if p.tipo == "enum":
            valores = p.valores()
            if valores and valor not in valores:
                errores.append(
                    f"{p.titulo}: '{valor}' no esta en "
                    f"{{{', '.join(valores)}}}.")
            continue

        if p.tipo not in ("length", "angle", "float", "int"):
            continue
        if p.minimo is not None and valor < p.minimo:
            errores.append(
                f"{p.titulo}: {valor:g} es menor que el minimo "
                f"{p.minimo:g}{p.sufijo}.")
        if p.maximo is not None and valor > p.maximo:
            errores.append(
                f"{p.titulo}: {valor:g} supera el maximo "
                f"{p.maximo:g}{p.sufijo}.")
    return tuple(errores)


# =====================================================================
# Inventario de contrato (para el test de no-deriva)
# =====================================================================

# Propiedades cuyo VALOR es volatil o calculado: se compara su
# declaracion (tipo/grupo/ayuda) pero nunca su contenido.
VALOR_VOLATIL = frozenset({
    "Proxy", "Shape", "ShapeMaterial", "Label", "Label2", "Visibility",
    "ExpressionEngine", "_ElementMapVersion", "Placement",
    "VDO_Paneles_JSON", "VDO_ResumenDespiece", "ResumenEspacios",
    "VDO_Reengrose_JSON", "Hijos", "LocalPlacement", "ParentCOCO",
    "FuerzaPistonRecomendada",
})


def inventario_contrato(obj) -> Dict[str, Dict[str, Any]]:
    """Proyeccion comparable del inventario de propiedades de un objeto.

    La usan tools/vdo_snapshot_props.py y
    tests/test_contrato_modulos.py::test_inventario_sin_deriva para
    verificar que pasar un Feature al esquema declarativo deja un objeto
    INDISTINGUIBLE del que producian los addProperty() a mano.
    """
    datos = {}
    for nombre in obj.PropertiesList:
        entrada = {
            "typeid": obj.getTypeIdOfProperty(nombre),
            "grupo": obj.getGroupOfProperty(nombre),
            "doc": obj.getDocumentationOfProperty(nombre),
        }
        if entrada["typeid"] == "App::PropertyEnumeration":
            try:
                entrada["enum"] = list(obj.getEnumerationsOfProperty(nombre))
            except Exception:
                pass
        if nombre not in VALOR_VOLATIL:
            entrada["valor"] = _serializable(obj, nombre)
        datos[nombre] = entrada
    return datos


def _serializable(obj, nombre):
    try:
        v = getattr(obj, nombre)
    except Exception as exc:
        return f"<error:{exc}>"
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if hasattr(v, "Value"):                      # Quantity
        return round(float(v.Value), 9)
    if hasattr(v, "Base") and hasattr(v, "Rotation"):   # Placement
        b, r = v.Base, v.Rotation
        return {"base": [round(b.x, 9), round(b.y, 9), round(b.z, 9)],
                "axis": [round(r.Axis.x, 9), round(r.Axis.y, 9),
                         round(r.Axis.z, 9)],
                "angle": round(r.Angle, 9)}
    if isinstance(v, (list, tuple)):
        return [getattr(i, "Name", str(i)) for i in v]
    return str(v)


__all__ = [
    "TYPEID", "WIDGET", "PROP_MODULO", "VALOR_VOLATIL",
    "Param", "ModuloSpec", "VarianteCreacion", "bloque", "resolver",
    "aplicar_param", "aplicar_params", "aplicar_esquema",
    "config_desde_objeto", "aplicar_config", "validar",
    "inventario_contrato",
]
