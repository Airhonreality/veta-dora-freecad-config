# -*- coding: utf-8 -*-
"""Contrato axiomatico de los modulos VDO.

Este archivo es el guardian de la estructura matricial. Recorre el
catalogo (VDO.hub.vdo_hub_registry.MODULOS) y comprueba que CADA modulo
cumple el mismo contrato, sin excepciones escritas a mano.

QUE BUGS CIERRA PARA SIEMPRE
  * Un modulo que no declara VDO_Tipo (o lo declara con un valor que la
    lista de corte no entiende) es invisible para fabricacion y nadie se
    entera. Paso con la PUERTA (sin VDO_Tipo: fuera del cutlist y del
    nesting) y con el TAMBOR (VDO_Tipo "tambor", que el if/elif del
    cutlist no contempla).
  * Un modulo sin forma de identificarse no se puede reparar ni abrir:
    reparar_viewprovider() y abrir_panel_objeto() nunca conocieron puerta
    ni tambor.
  * Deriva entre la declaracion de propiedades y la realidad del objeto:
    test_inventario_sin_deriva compara contra tests/datos/props_snapshot.json,
    capturado ANTES de pasar los Feature al esquema declarativo.
"""

import json
import os
import sys
from pathlib import Path

import pytest

_AQUI = Path(__file__).resolve().parent
_RAIZ = _AQUI.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from tests._entorno import HAY_FREECAD

from VDO.hub import vdo_hub_registry as REG
from VDO.hub.vdo_hub_schema import (
    PROP_MODULO, Param, WIDGET, inventario_contrato, resolver, validar)

SNAPSHOT = _AQUI / "datos" / "props_snapshot.json"

# Propiedades que el refactor AÑADE a proposito. El test de no-deriva
# prohibe perder o cambiar propiedades, pero permite estas altas.
ALTAS_ESPERADAS = {
    PROP_MODULO,
    # Metadatos de fabricacion que la puerta no tenia (bug: invisible
    # para la lista de corte y para el nesting).
    "VDO_Tipo", "VDO_Subtipo", "VDO_Material_Ref", "VDO_Paneles_JSON",
    "VDO_ResumenDespiece",
    # Contrato de deltas de borde (Concepto 1): propiedad dinamica de Puerta.
    "VDO_Deltas_JSON",
    # Prismas de corte (mocheos) que PanelFeature resta de su caja: llevan
    # las muescas de tiras y divisiones que la caja no puede expresar.
    "VDO_Mocheos_JSON",
}

# Cambios de valor deliberados respecto a la instantanea previa.
CAMBIOS_ESPERADOS = {
    # El tambor publicaba VDO_Tipo "tambor", valor que vdo_cam_cutlist no
    # contempla: su despiece no lo leia nadie.
    ("tambor", "VDO_Tipo"),
}

# Textos de documentacion unificados a proposito. Cada modulo redactaba
# los mismos metadatos a su manera ("Tipo de modulo" / "Tipo de objeto",
# "Despiece de manufactura" / "Descripcion JSON de las piezas del
# zocalo"...). Ahora los declara una sola vez params_fabricacion(), que es
# justamente el punto del refactor. Se listan uno a uno para que la
# unificacion sea una decision registrada y no un hueco por el que se
# cuele una deriva real.
DOCS_UNIFICADOS = {
    ("coco_4c", "VDO_Paneles_JSON"),
    ("coco_4c", "VDO_Subtipo"),
    ("tambor", "VDO_Paneles_JSON"),
    ("tambor", "VDO_Tipo"),
    ("zocalo", "VDO_Paneles_JSON"),
}


# =====================================================================
# 1. Coherencia interna del catalogo (no necesita FreeCAD con documento)
# =====================================================================

MODULOS = sorted(REG.MODULOS)
VARIANTES = sorted(REG.VARIANTES)


@pytest.mark.parametrize("tipo", MODULOS)
def test_modulo_es_fabricable(tipo):
    """VDO_Tipo tiene que ser un valor que la lista de corte entienda."""
    s = REG.spec(tipo)
    assert s.vdo_tipo in REG.VDO_TIPOS_FABRICABLES, (
        f"{tipo}: VDO_Tipo='{s.vdo_tipo}' no esta en "
        f"{REG.VDO_TIPOS_FABRICABLES}. vdo_cam_cutlist lo descartaria "
        f"en silencio y el modulo no llegaria a fabricacion.")


@pytest.mark.parametrize("tipo", MODULOS)
def test_modulo_declara_metadatos_de_fabricacion(tipo):
    """Todo modulo publica tipo, subtipo y material."""
    s = REG.spec(tipo)
    for prop in ("VDO_Tipo", "VDO_Subtipo", "VDO_Material_Ref"):
        assert s.param(prop) is not None, (
            f"{tipo}: falta el parametro '{prop}' en el esquema.")


@pytest.mark.parametrize("tipo", MODULOS)
def test_modulo_es_identificable(tipo):
    """El modulo tiene respaldo de identificacion para documentos viejos."""
    s = REG.spec(tipo)
    assert s.legacy_props, (
        f"{tipo}: sin legacy_props. Un documento guardado antes de "
        f"{PROP_MODULO} no se podria identificar y su ViewProvider seria "
        f"irreparable.")


def test_subtipos_unicos():
    """Dos modulos no pueden compartir subtipo (seria ambiguo)."""
    vistos = {}
    for tipo, s in REG.MODULOS.items():
        assert s.vdo_subtipo not in vistos, (
            f"'{s.vdo_subtipo}' lo usan {vistos.get(s.vdo_subtipo)} y "
            f"{tipo}.")
        vistos[s.vdo_subtipo] = tipo


def test_legacy_props_no_son_ambiguas():
    """Los respaldos de identificacion no se solapan entre modulos.

    Si las legacy_props de A son un subconjunto de las de B, un objeto de
    B se identificaria como A segun el orden del diccionario. Es
    exactamente el fallo latente que tenian los predicados _es_X().
    """
    for tipo_a, a in REG.MODULOS.items():
        for tipo_b, b in REG.MODULOS.items():
            if tipo_a >= tipo_b:
                continue
            assert not set(a.legacy_props) <= set(b.legacy_props), (
                f"legacy_props de '{tipo_a}' {a.legacy_props} es "
                f"subconjunto de '{tipo_b}' {b.legacy_props}: la "
                f"identificacion de documentos antiguos seria ambigua.")


@pytest.mark.parametrize("tipo", MODULOS)
def test_params_sin_duplicados(tipo):
    s = REG.spec(tipo)
    nombres = [p.nombre for p in s.params]
    duplicados = {n for n in nombres if nombres.count(n) > 1}
    assert not duplicados, f"{tipo}: parametros repetidos {duplicados}."


@pytest.mark.parametrize("tipo", MODULOS)
def test_claves_motor_sin_duplicados(tipo):
    s = REG.spec(tipo)
    claves = [p.clave_motor for p in s.params_motor()]
    duplicados = {c for c in claves if claves.count(c) > 1}
    assert not duplicados, (
        f"{tipo}: dos parametros entran al motor con la misma clave "
        f"{duplicados}; uno pisaria al otro.")


@pytest.mark.parametrize("tipo", MODULOS)
def test_params_tienen_ayuda(tipo):
    """La ayuda es el tooltip Y la documentacion de la propiedad."""
    s = REG.spec(tipo)
    sin_ayuda = [p.nombre for p in s.params if not p.ayuda]
    assert not sin_ayuda, f"{tipo}: parametros sin ayuda {sin_ayuda}."


@pytest.mark.parametrize("tipo", MODULOS)
def test_numericos_acotados(tipo):
    """Todo numerico editable declara su rango EN LA CAPA DE DATOS.

    El motivo del refactor: antes el rango solo existia como setRange()
    del spinbox, asi que editar la propiedad desde el editor de FreeCAD,
    una macro o un test se saltaba toda validacion.
    """
    s = REG.spec(tipo)
    sueltos = [
        p.nombre for p in s.params_formulario()
        if p.tipo in ("length", "float", "int")
        and (p.minimo is None or p.maximo is None)
    ]
    assert not sueltos, (
        f"{tipo}: numericos sin rango declarado {sueltos}. El limite "
        f"volveria a vivir solo en el widget Qt.")


@pytest.mark.parametrize("tipo", MODULOS)
def test_enums_tienen_dominio(tipo):
    s = REG.spec(tipo)
    for p in s.params:
        if p.tipo != "enum":
            continue
        valores = p.valores()
        assert valores, f"{tipo}.{p.nombre}: enum sin opciones."
        inicial = p.valor_inicial()
        if inicial is not None:
            assert inicial in valores, (
                f"{tipo}.{p.nombre}: default '{inicial}' fuera del "
                f"dominio {valores}.")


@pytest.mark.parametrize("tipo", MODULOS)
def test_modulo_tiene_formulario(tipo):
    """Un modulo sin parametros en formulario no se podria editar."""
    s = REG.spec(tipo)
    assert s.params_formulario(), f"{tipo}: ningun parametro editable."
    for p in s.params_formulario():
        assert p.widget in WIDGET.values(), (
            f"{tipo}.{p.nombre}: tipo '{p.tipo}' sin control Qt.")


# =====================================================================
# 2. El catalogo apunta a codigo que existe
# =====================================================================

@pytest.mark.parametrize("tipo", MODULOS)
def test_rutas_cad_resuelven(tipo):
    s = REG.spec(tipo)
    for campo in ("feature", "viewprovider", "fabrica"):
        ruta = getattr(s, campo)
        assert resolver(ruta) is not None, f"{tipo}.{campo} -> {ruta}"


@pytest.mark.parametrize("tipo", MODULOS)
def test_motor_resuelve(tipo):
    s = REG.spec(tipo)
    assert s.motor, f"{tipo}: sin motor declarado."
    assert callable(resolver(s.motor)), f"{tipo}.motor -> {s.motor}"


@pytest.mark.parametrize("clave", VARIANTES)
def test_variante_apunta_a_modulo(clave):
    v = REG.variante(clave)
    assert v.modulo in REG.MODULOS, (
        f"variante '{clave}' apunta a modulo inexistente '{v.modulo}'.")


@pytest.mark.parametrize("clave", VARIANTES)
def test_variante_tiene_icono(clave):
    from VDO._paths import ICONS_DIR
    v = REG.variante(clave)
    assert v.icono, f"variante '{clave}': sin icono."
    assert (Path(str(ICONS_DIR)) / v.icono).is_file(), (
        f"variante '{clave}': falta el icono {v.icono}.")


def test_comandos_unicos():
    comandos = [v.comando for v in REG.VARIANTES.values()]
    duplicados = {c for c in comandos if comandos.count(c) > 1}
    assert not duplicados, f"comandos repetidos: {duplicados}."


def test_alias_resuelven():
    for alias, destino in REG.ALIAS.items():
        assert destino in REG.VARIANTES, (
            f"alias '{alias}' -> '{destino}' inexistente.")


def test_creation_flow_deriva_del_registro():
    """ESPECIFICACIONES ya no es una segunda lista escrita a mano."""
    from VDO.ui.vdo_ui_creation_flow import ESPECIFICACIONES
    assert set(ESPECIFICACIONES) == set(REG.VARIANTES), (
        "el registro de creacion y el catalogo divergen: "
        f"{set(ESPECIFICACIONES) ^ set(REG.VARIANTES)}")


def test_comandos_derivan_del_registro():
    """Todo comando de variante entra en el registro del workbench.

    Se comprueba contra REG.nombres_comandos() y no importando
    vdo_initgui: ese modulo define `class VDO_Workbench(Gui.Workbench)` a
    nivel de modulo, y Gui.Workbench no existe en FreeCADCmd. El dato
    vive en el catalogo precisamente para poder verificarlo headless.
    """
    comandos = REG.nombres_comandos()
    assert len(comandos) == len(set(comandos)), "comandos repetidos."
    for v in REG.VARIANTES.values():
        assert v.comando in comandos, (
            f"la variante '{v.clave}' declara el comando {v.comando} "
            f"pero no aparece en nombres_comandos().")
    for fijo in REG.COMANDOS_FIJOS:
        assert fijo in comandos, f"falta el comando fijo {fijo}."


def test_toolbar_deriva_del_registro():
    """La barra "VDO Muebles" sale del catalogo y es coherente."""
    barra = REG.toolbar_muebles()
    botones = [c for c in barra if c != "Separator"]
    assert len(botones) == len(set(botones)), (
        f"botones repetidos en la barra: {botones}")
    for v in REG.VARIANTES.values():
        if v.en_barra:
            assert v.comando in botones, (
                f"{v.comando} ({v.clave}) no aparece en la barra.")
    for c in botones:
        assert c in REG.nombres_comandos(), (
            f"la barra incluye {c}, que nadie registra.")


def test_initgui_consume_el_registro():
    """vdo_initgui no vuelve a escribir las listas a mano.

    Se inspecciona el fuente en vez de importarlo, por el mismo motivo
    que el test anterior.
    """
    fuente = (_RAIZ / "VDO" / "vdo_initgui.py").read_text(encoding="utf-8")
    assert "REG.nombres_comandos()" in fuente, (
        "COMANDOS deberia derivar de REG.nombres_comandos().")
    assert "REG.toolbar_muebles()" in fuente, (
        "TB_MUEBLES deberia derivar de REG.toolbar_muebles().")
    assert "class CmdCrearModulo" in fuente, (
        "falta el comando de creacion generico.")
    # Las siete clases Cmd* por modulo ya no deben existir.
    for muerta in ("class CmdCoco4C", "class CmdCajon", "class CmdPuerta",
                   "class CmdZocalo", "class CmdPanelEstandar",
                   "class CmdPanelFachada", "class CmdTambor"):
        assert muerta not in fuente, (
            f"{muerta} sigue viva: era boilerplate derivable del catalogo.")


def test_view_base_no_adivina_el_tipo():
    """Los predicados por duck-typing han desaparecido de verdad.

    Se comprueba el atributo del modulo, no el texto del fuente: el
    comentario que documenta por que se retiraron los menciona por
    nombre, y buscar la cadena daria un falso positivo.
    """
    from VDO.cad.views import vdo_cad_view_base as VB
    for muerto in ("_es_coco", "_es_cajon", "_es_zocalo", "_es_panel"):
        assert not hasattr(VB, muerto), (
            f"{muerto}() sigue vivo: adivinaba el tipo por las "
            f"propiedades del objeto y no cubria puerta ni tambor.")
    assert hasattr(VB, "modulo_de"), (
        "view_base deberia identificar por el catalogo (modulo_de).")


# =====================================================================
# 3. Comportamiento sobre objetos reales (requiere FreeCAD)
# =====================================================================

pytestmark_fc = pytest.mark.skipif(
    not HAY_FREECAD, reason="requiere FreeCAD real; ejecutar con FreeCADCmd")


@pytest.fixture(scope="module")
def doc():
    if not HAY_FREECAD:
        pytest.skip("requiere FreeCAD real")
    import FreeCAD as App
    documento = App.newDocument("TEST_CONTRATO")
    yield documento
    try:
        App.closeDocument(documento.Name)
    except Exception:
        pass


@pytest.fixture(scope="module")
def objetos(doc):
    """Un objeto de cada variante, creado por su fabrica real."""
    from VDO.ui.vdo_ui_creation_flow import crear_modulo_directo
    creados = {}
    for clave in VARIANTES:
        obj = crear_modulo_directo(clave)
        assert obj is not None, f"la fabrica de '{clave}' devolvio None."
        creados[clave] = obj
    doc.recompute()
    return creados


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_objeto_lleva_testigo_de_tipo(objetos, clave):
    obj = objetos[clave]
    esperado = REG.variante(clave).modulo
    assert getattr(obj, PROP_MODULO, "") == esperado, (
        f"{clave}: {PROP_MODULO}='{getattr(obj, PROP_MODULO, None)}', "
        f"se esperaba '{esperado}'.")


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_objeto_se_identifica(objetos, clave):
    """resolver_modulo() devuelve el spec correcto. Sustituye a _es_X()."""
    obj = objetos[clave]
    s = REG.resolver_modulo(obj)
    assert s is not None, f"{clave}: resolver_modulo() no lo reconoce."
    assert s.tipo == REG.variante(clave).modulo


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_objeto_identificable_sin_testigo(objetos, clave):
    """Respaldo legacy: quitando VDO_Modulo, legacy_props lo rescata.

    Simula un documento guardado antes de que existiera el testigo.
    """
    obj = objetos[clave]
    esperado = REG.variante(clave).modulo
    guardado = getattr(obj, PROP_MODULO)
    try:
        setattr(obj, PROP_MODULO, "")
        s = REG.resolver_modulo(obj)
        assert s is not None and s.tipo == esperado, (
            f"{clave}: sin testigo se identifica como "
            f"{getattr(s, 'tipo', None)}, se esperaba {esperado}.")
    finally:
        setattr(obj, PROP_MODULO, guardado)


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_objeto_declara_todo_su_esquema(objetos, clave):
    """Ninguna propiedad del esquema falta en el objeto real."""
    obj = objetos[clave]
    s = REG.spec_de_variante(clave)
    faltan = [p.nombre for p in s.params if not hasattr(obj, p.nombre)]
    assert not faltan, f"{clave}: faltan propiedades {faltan}."


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_objeto_nace_valido(objetos, clave):
    """Los defaults del esquema respetan los limites del esquema."""
    obj = objetos[clave]
    s = REG.spec_de_variante(clave)
    errores = validar(obj, s)
    assert not errores, f"{clave}: nace invalido -> {errores}"


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_config_motor_completa(objetos, clave):
    """config_desde_objeto() entrega todas las claves declaradas."""
    obj = objetos[clave]
    s = REG.spec_de_variante(clave)
    config = REG.config_de(obj)
    esperadas = {p.clave_motor for p in s.params_motor()}
    assert set(config) == esperadas, (
        f"{clave}: el dict del motor difiere -> "
        f"{esperadas ^ set(config)}")


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_objeto_aporta_despiece(objetos, clave):
    """Todo modulo llega a la lista de corte. El bug A y el bug B.

    La puerta no declaraba VDO_Tipo, asi que
    extraer_piezas_del_documento() la descartaba. El tambor declaraba un
    VDO_Tipo que el cutlist no contempla.
    """
    obj = objetos[clave]
    s = REG.spec_de_variante(clave)
    if not s.publica_despiece:
        pytest.skip(f"{clave} no publica despiece por contrato")

    assert hasattr(obj, "VDO_Tipo"), (
        f"{clave}: sin VDO_Tipo, vdo_cam_cutlist y "
        f"vdo_cam_nesting_workflow lo descartan en silencio.")
    assert obj.VDO_Tipo in REG.VDO_TIPOS_FABRICABLES, (
        f"{clave}: VDO_Tipo='{obj.VDO_Tipo}' cae fuera del if/elif de "
        f"vdo_cam_cutlist y su despiece no lo lee nadie.")

    tiene_json = bool((getattr(obj, "VDO_Paneles_JSON", "") or "").strip()
                      not in ("", "[]", "{}"))
    tiene_hijos = bool([h for h in (getattr(obj, "Hijos", None) or [])
                        if h is not None])
    es_pieza = obj.VDO_Tipo == "panel"
    assert tiene_json or tiene_hijos or es_pieza, (
        f"{clave}: no publica despiece ni como VDO_Paneles_JSON ni como "
        f"PanelFeature hijos; es invisible para fabricacion.")


@pytestmark_fc
def test_cutlist_ve_todos_los_modulos(objetos):
    """Prueba de extremo a extremo del contrato de fabricacion."""
    from VDO.cam.vdo_cam_cutlist import extraer_piezas_del_documento
    piezas = extraer_piezas_del_documento("todo")
    assert piezas, "la lista de corte sale vacia con un documento lleno."


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_panel_de_tareas_resuelve(objetos, clave):
    """El TaskPanel declarado existe y es construible sin GUI."""
    s = REG.spec_de_variante(clave)
    clase = resolver(s.panel)
    assert clase is not None, f"{clave}: panel {s.panel} no resuelve."


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_viewprovider_declara_panel(objetos, clave):
    """Todo ViewProvider sabe que panel abrir (contrato de la base)."""
    s = REG.spec_de_variante(clave)
    vp_cls = resolver(s.viewprovider)
    assert "get_panel_class" in dir(vp_cls), (
        f"{clave}: {s.viewprovider} no implementa get_panel_class().")


@pytestmark_fc
@pytest.mark.parametrize("clave", VARIANTES)
def test_validacion_rechaza_fuera_de_rango(objetos, clave):
    """La validacion muerde de verdad: no es decorativa."""
    obj = objetos[clave]
    s = REG.spec_de_variante(clave)
    candidato = next(
        (p for p in s.params_formulario()
         if p.tipo in ("length", "float") and p.maximo is not None),
        None)
    if candidato is None:
        pytest.skip(f"{clave}: sin numerico acotado")

    original = getattr(obj, candidato.nombre)
    try:
        setattr(obj, candidato.nombre, float(candidato.maximo) + 1000.0)
        errores = validar(obj, s)
        assert any(candidato.titulo in e for e in errores), (
            f"{clave}.{candidato.nombre}: se acepto un valor por encima "
            f"del maximo {candidato.maximo} sin protestar.")
    finally:
        setattr(obj, candidato.nombre, original)


# =====================================================================
# 4. No-deriva respecto al estado previo al refactor
# =====================================================================

@pytestmark_fc
def test_inventario_sin_deriva(objetos):
    """Pasar los Feature al esquema no cambio ni una propiedad.

    tests/datos/props_snapshot.json se capturo con
    `FreeCADCmd tools/vdo_snapshot_props.py` ANTES de sustituir las
    cadenas de addProperty() por aplicar_esquema(). Aqui se comprueba que
    el objeto resultante es indistinguible: mismo nombre, mismo TypeId,
    mismo grupo, misma documentacion, mismo valor y mismo dominio de
    enum. Las altas deliberadas se listan en ALTAS_ESPERADAS.
    """
    assert SNAPSHOT.is_file(), (
        f"falta la instantanea {SNAPSHOT}. Regenerala con "
        f"FreeCADCmd tools/vdo_snapshot_props.py")
    previo = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    problemas = []
    for clave, antes in previo.items():
        obj = objetos.get(clave)
        if obj is None:
            problemas.append(f"{clave}: ya no se puede crear.")
            continue
        ahora = inventario_contrato(obj)

        for prop, esperado in antes.items():
            if prop not in ahora:
                problemas.append(f"{clave}.{prop}: DESAPARECIO.")
                continue
            actual = ahora[prop]
            for campo in ("typeid", "grupo", "doc", "enum", "valor"):
                if campo not in esperado or campo not in actual:
                    continue
                if (clave, prop) in CAMBIOS_ESPERADOS and campo == "valor":
                    continue
                if (clave, prop) in DOCS_UNIFICADOS and campo == "doc":
                    continue
                if esperado[campo] != actual[campo]:
                    problemas.append(
                        f"{clave}.{prop}.{campo}: "
                        f"{esperado[campo]!r} -> {actual[campo]!r}")

        altas = set(ahora) - set(antes) - ALTAS_ESPERADAS
        if altas:
            problemas.append(f"{clave}: altas no declaradas {sorted(altas)}")

    assert not problemas, (
        "deriva respecto a la instantanea previa al refactor:\n  "
        + "\n  ".join(problemas))
