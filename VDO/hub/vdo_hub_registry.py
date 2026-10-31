# -*- coding: utf-8 -*-
# =====================================================================
# vdo_hub_registry.py
# EL CATALOGO. Fuente unica de verdad de los modulos VDO.
#
# QUE SUSTITUYE
# Antes, dar de alta un modulo nuevo exigia tocar OCHO sitios:
#   1. VDO/cad/objects/vdo_cad_X.py        (Feature + ViewProvider + make_X)
#   2. VDO/ui/vdo_ui_X_task.py             (TaskPanel a mano)
#   3. vdo_ui_creation_flow.ESPECIFICACIONES
#   4. vdo_initgui: clase CmdX
#   5. vdo_initgui: COMANDOS
#   6. vdo_initgui: TB_MUEBLES
#   7. vdo_cad_view_base: _es_X() + reparar_viewprovider() + abrir_panel_objeto()
#   8. vdo_cam_cutlist: rama del VDO_Tipo
# Olvidar el 7 fue justo lo que paso: reparar_viewprovider() y
# abrir_panel_objeto() nunca conocieron puerta ni tambor. Y olvidar el 8
# dejo las PUERTAS fuera de la lista de corte y del nesting (no declaraban
# VDO_Tipo) y el despiece del TAMBOR sin lector (declaraba VDO_Tipo
# "tambor", que el cutlist no contempla).
#
# Ahora los puntos 3 a 8 se DERIVAN de este archivo.
#
# DOS CONCEPTOS DISTINTOS, A PROPOSITO
#   MODULOS   -> contrato de datos de un modulo geometrico (6 entradas).
#   VARIANTES -> entradas de barra/menu que crean uno (8 entradas).
# "panel estandar", "panel fachada" y "panel division" son tres variantes
# del MISMO contrato. Separarlos evita que el contrato de datos se
# multiplique por los botones de la interfaz.
# =====================================================================

from typing import Dict, Optional, Tuple

import VDO.hub.vdo_hub_defaults as VDO_D
from VDO.hub.vdo_hub_module_props import (
    PARAMS_POSE, PARAMS_REENGROSE, params_retroenlace)
from VDO.hub.vdo_hub_schema import (
    Param, ModuloSpec, VarianteCreacion, PROP_MODULO, aplicar_esquema,
    config_desde_objeto, validar)
from VDO.core.vdo_math_cajon import (
    listar_marcas, CORREDERA_OCULTA, CORREDERA_TELESCOPICA, CAJA_METALICA)
from VDO.core.vdo_math_facade import (
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA)


# Valores de VDO_Tipo que la lista de corte sabe interpretar
# (vdo_cam_cutlist.extraer_piezas_del_documento). Cualquier otro valor
# hace al modulo invisible para fabricacion sin dar ningun error.
VDO_TIPOS_FABRICABLES = ("panel", "contenedor")

MATERIAL_DEFAULT = "melamina_standar"
CANTOS_VALIDOS = ("RIG", "FX", "SMRG")


# =====================================================================
# Bloque de metadatos de fabricacion
# =====================================================================

def params_fabricacion(vdo_tipo, vdo_subtipo, ayuda_material,
                       con_despiece=True, con_resumen=True,
                       material_al_motor=False):
    """Metadatos que todo modulo debe publicar para ser fabricable.

    Declararlos aqui, y no modulo a modulo, es lo que garantiza que no
    vuelva a nacer un modulo invisible para la lista de corte.

    `material_al_motor` solo para los motores que de verdad reciben
    `material_ref` como argumento (zocalo, cajon): declararselo a los que
    no lo aceptan reventaria la llamada con un kwarg inesperado.
    """
    params = [
        Param("VDO_Tipo", "string", "VDO", ayuda="Tipo de objeto",
              default=vdo_tipo, ui=False),
        Param("VDO_Subtipo", "string", "VDO", ayuda="Subtipo",
              default=vdo_subtipo, ui=False),
        Param("VDO_Material_Ref", "string", "VDO", etiqueta="Material",
              ayuda=ayuda_material, default=MATERIAL_DEFAULT,
              clave_motor="material_ref" if material_al_motor else None,
              clave_config="material_ref"),
    ]
    if con_despiece:
        params.append(
            Param("VDO_Paneles_JSON", "string", "VDO",
                  ayuda="Descripción JSON de las piezas del despiece",
                  ui=False))
    if con_resumen:
        params.append(
            Param("VDO_ResumenDespiece", "string", "VDO",
                  etiqueta="Despiece",
                  ayuda="Resumen legible del despiece (solo lectura)",
                  ui=False, solo_lectura=True))
    return tuple(params)


def _marca_default():
    """Marca de corredera preferida, si el catalogo de herrajes la trae.

    Es un default DINAMICO: el dominio del enum sale de
    vdo_hardware_catalog.json, asi que ni el valor inicial ni la lista se
    pueden escribir aqui a mano sin arriesgarse a nombrar una marca que el
    catalogo ya no tenga.
    """
    marcas = listar_marcas()
    if not marcas:
        return None
    return "blum_tandem" if "blum_tandem" in marcas else marcas[0]


def _cantos():
    """Los cuatro cantos del tablero, como enums declarados."""
    ayudas = {
        "Norte": "Borde norte del tablero visto desde la cara A.",
        "Sur": "Borde sur del tablero visto desde la cara A.",
        "Este": "Borde este del tablero visto desde la cara A.",
        "Oeste": "Borde oeste del tablero visto desde la cara A.",
    }
    return tuple(
        Param(f"VDO_Canto_{d}", "enum", "Cantos", etiqueta=d,
              ayuda=f"Canto {d}", default="FX", opciones=CANTOS_VALIDOS)
        for d in ("Norte", "Sur", "Este", "Oeste"))


# =====================================================================
# COCO — cofre de 4 caras
# =====================================================================
SPEC_COCO = ModuloSpec(
    tipo="coco",
    etiqueta="COCO",
    vdo_tipo="contenedor",
    vdo_subtipo="COCO_4C",
    feature="VDO.cad.objects.vdo_cad_coco:CocoFeature",
    viewprovider="VDO.cad.objects.vdo_cad_coco:ViewProviderCoco",
    fabrica="VDO.cad.objects.vdo_cad_coco:make_coco",
    panel="VDO.ui.vdo_ui_coco_task:CocoUnifiedTaskPanel",
    motor="VDO.core.vdo_math_layout:resolve_layout",
    legacy_props=("VDO_Divisiones",),
    params=(
        Param("Alto", "length", "Dimensiones", etiqueta="Alto",
              ayuda="Alto total del módulo (mm)",
              default=VDO_D.ALTO_DEFAULT, minimo=1.0, maximo=4000.0,
              sufijo=" mm", clave_motor="alto"),
        Param("Ancho", "length", "Dimensiones", etiqueta="Ancho",
              ayuda="Ancho total del módulo (mm)",
              default=VDO_D.ANCHO_DEFAULT, minimo=1.0, maximo=4000.0,
              sufijo=" mm", clave_motor="ancho"),
        Param("FondoModulo", "length", "Dimensiones", etiqueta="Fondo",
              ayuda="Profundidad total del módulo (mm)",
              default=VDO_D.FONDO_DEFAULT, minimo=1.0, maximo=2000.0,
              sufijo=" mm", clave_motor="fondo_modulo"),
        Param("Espesor", "int", "Dimensiones", etiqueta="Espesor tablero",
              ayuda="Espesor del tablero (mm)",
              default=VDO_D.ESPESOR_DEFAULT, minimo=1, maximo=40,
              decimales=0, sufijo=" mm", clave_motor="espesor"),

        Param("TieneFondo", "bool", "Estructura", etiqueta="Tiene fondo",
              ayuda="Habilitar fondo/respaldo",
              default=VDO_D.FONDO_HABILITADO, clave_motor="tiene_fondo"),
        Param("CalibreFondo", "int", "Estructura", etiqueta="Calibre fondo",
              ayuda="Espesor del fondo (mm)",
              default=VDO_D.FONDO_CALIBRE, minimo=1, maximo=40,
              decimales=0, sufijo=" mm", clave_motor="calibre_fondo"),
        Param("ProfundidadRanura", "float", "Estructura",
              etiqueta="Profundidad de ranura",
              ayuda="Profundidad de ranura para fondo (mm)",
              default=VDO_D.FONDO_PROFUNDIDAD_RANURA, minimo=0.0,
              maximo=40.0, sufijo=" mm", clave_motor="profundidad_ranura"),
        Param("DistanciaBorde", "float", "Estructura",
              etiqueta="Distancia al borde",
              ayuda="Distancia del borde para fondo grueso (mm)",
              default=VDO_D.FONDO_DISTANCIA_BORDE, minimo=0.0, maximo=200.0,
              sufijo=" mm", clave_motor="distancia_borde"),
        Param("Tapa", "enum", "Estructura", etiqueta="Tapa",
              ayuda="Configuración de la tapa",
              opciones=("externo", "interno"), clave_motor="tapa"),
        Param("Base", "enum", "Estructura", etiqueta="Base",
              ayuda="Configuración de la base",
              opciones=("externo", "interno"), clave_motor="base"),
        Param("VDO_Chassis_JSON", "string", "Estructura",
              ayuda="Configuración del chasis 2D (JSON)",
              default="{}", ui=False),

        Param("VDO_Divisiones", "string", "Divisiones",
              ayuda="Matriz de vanos v2 (JSON)", default="", ui=False,
              clave_config="divisiones"),
        Param("ResumenEspacios", "string", "Divisiones",
              ayuda="Resumen legible de espacios calculados (solo lectura)",
              ui=False, solo_lectura=True),
        Param("VDO_Reengrose_JSON", "string", "Reengrose",
              ayuda="Modificadores de reengrose por pieza (JSON)",
              default="{}", ui=False),

        # Metadatos de fabricacion. El COCO no publica VDO_ResumenDespiece:
        # su resumen legible es ResumenEspacios.
        *params_fabricacion("contenedor", "COCO_4C",
                            "Material de los paneles", con_resumen=False),

        Param("Hijos", "link_list_child", "VDO",
              ayuda="Insertos contenidos (puertas, cajones, paneles)",
              default=list, ui=False),
        Param("Piezas_Omitidas", "stringlist", "VDO",
              ayuda="Roles de paneles desvinculados (omitos al recompute)",
              default=list, ui=False),

        *PARAMS_POSE,
    ),
)


# =====================================================================
# CAJON — caja + fachada sobre corredera
# =====================================================================
SPEC_CAJON = ModuloSpec(
    tipo="cajon",
    etiqueta="Cajón",
    vdo_tipo="contenedor",
    vdo_subtipo="cajon_oculta",
    feature="VDO.cad.objects.vdo_cad_cajon:CajonFeature",
    viewprovider="VDO.cad.objects.vdo_cad_cajon:ViewProviderCajon",
    fabrica="VDO.cad.objects.vdo_cad_cajon:make_cajon",
    panel="VDO.ui.vdo_ui_cajon_task:CajonTaskPanel",
    motor="VDO.core.vdo_math_cajon:calcular_despiece",
    legacy_props=("AnchoLibre", "MarcaCorredera"),
    params=(
        Param("AnchoLibre", "length", "Dimensiones", etiqueta="Ancho libre",
              ayuda="Ancho libre interior del mueble LI (mm)",
              default=564.0, minimo=1.0, maximo=4000.0, sufijo=" mm",
              clave_motor="ancho_libre"),
        Param("ProfLibre", "length", "Dimensiones", etiqueta="Prof. libre",
              ayuda="Profundidad libre interior del mueble (mm)",
              default=560.0, minimo=1.0, maximo=2000.0, sufijo=" mm",
              clave_motor="prof_libre"),
        Param("AnchoModulo", "length", "Dimensiones", etiqueta="Ancho módulo",
              ayuda="Ancho total del módulo (para la fachada, mm)",
              default=600.0, minimo=1.0, maximo=4000.0, sufijo=" mm",
              clave_motor="ancho_modulo"),
        Param("AltoFrente", "length", "Dimensiones", etiqueta="Alto frente",
              ayuda="Alto total asignado a la fachada (mm)",
              default=225.0, minimo=1.0, maximo=2000.0, sufijo=" mm",
              clave_motor="alto_frente"),

        Param("AltoCaja", "length", "Caja", etiqueta="Alto de caja",
              ayuda="Alto de los laterales de la caja (85/120/150)",
              default=VDO_D.CAJON_ALTO_DEFAULT, minimo=1.0, maximo=1000.0,
              sufijo=" mm", clave_motor="alto_caja"),
        Param("GrosorCaja", "length", "Caja", etiqueta="Grosor de caja",
              ayuda="Espesor del tablero de la caja (15/16 mm)",
              default=VDO_D.CAJON_GROSOR_DEFAULT, minimo=1.0, maximo=40.0,
              sufijo=" mm", clave_motor="grosor_caja"),
        Param("GrosorFondo", "length", "Caja", etiqueta="Grosor de piso",
              ayuda="Espesor del piso del cajón (6/12 mm)",
              default=VDO_D.CAJON_FONDO_DEFAULT, minimo=1.0, maximo=40.0,
              sufijo=" mm", clave_motor="grosor_fondo"),
        Param("GrosorFachada", "length", "Fachada",
              etiqueta="Grosor de fachada",
              ayuda="Espesor de la fachada decorativa (18 mm)",
              default=VDO_D.CAJON_FACHADA_DEFAULT, minimo=1.0, maximo=60.0,
              sufijo=" mm", clave_motor="grosor_fachada"),

        # El dominio de este enum sale del catalogo de herrajes, no de una
        # lista escrita a mano: anadir una marca al JSON la hace aparecer
        # en el combo sin tocar codigo.
        Param("MarcaCorredera", "enum", "Herraje", etiqueta="Marca",
              ayuda="Marca de corredera oculta (delta y cotas)",
              opciones=listar_marcas, default=_marca_default,
              clave_motor="marca"),
        Param("LongitudGuia", "length", "Herraje", etiqueta="Longitud de guía",
              ayuda="Largo nominal de la guía (0 = auto según ProfLibre)",
              default=0.0, minimo=0.0, maximo=1200.0, sufijo=" mm",
              clave_motor="longitud_guia"),
        Param("MontajeTrasera", "enum", "Herraje",
              etiqueta="Montaje de trasera",
              ayuda="Montaje de la contra-frente",
              default="entre_laterales",
              opciones=("entre_laterales", "testa"),
              clave_motor="montaje_trasera"),
        Param("TipoCorredera", "enum", "Herraje", etiqueta="Tipo de corredera",
              ayuda="Tipo de corredera: oculta / telescópica / metálica",
              default=CORREDERA_OCULTA,
              opciones=(CORREDERA_OCULTA, CORREDERA_TELESCOPICA,
                        CAJA_METALICA),
              clave_motor="tipo_corredera"),

        Param("SistemaApertura", "enum", "Fachada",
              etiqueta="Sistema de apertura",
              ayuda="Sistema de apertura del frente del cajón",
              default=APERTURA_TIRADOR,
              opciones=(APERTURA_TIRADOR, APERTURA_GOLA,
                        APERTURA_45_GRADOS, APERTURA_PUSH_OPEN),
              clave_motor="sistema_apertura"),
        Param("TipoMontaje", "enum", "Fachada", etiqueta="Tipo de montaje",
              ayuda="Tipo de montaje de la fachada frente al vano",
              default=MONTAJE_PARCHE,
              opciones=(MONTAJE_PARCHE, MONTAJE_SEMIPARCHE,
                        MONTAJE_EMBEBIDA),
              clave_motor="tipo_montaje_fachada"),

        *params_fabricacion("contenedor", "cajon_oculta",
                            "Material de las piezas",
                            material_al_motor=True),
        Param("VDO_Herraje_Ref", "string", "VDO", etiqueta="Herraje",
              ayuda="Herraje de corredera oculta", ui=False),

        Param("Hijos", "link_list_child", "Estructura Lógica",
              ayuda="Lista de componentes vinculados (paneles, herrajes)",
              ui=False),

        *PARAMS_POSE,
        *params_retroenlace("Módulo COCO padre"),
    ),
)


# =====================================================================
# PUERTA — hoja batiente / basculante / corrediza
# =====================================================================
# Los cuatro metadatos de fabricacion son NUEVOS. Sin ellos la puerta no
# declaraba VDO_Tipo, y tanto vdo_cam_cutlist (filtra por hasattr
# VDO_Tipo) como vdo_cam_nesting_workflow la descartaban en silencio: se
# podian disenar puertas que nunca aparecian en la lista de corte.
SPEC_PUERTA = ModuloSpec(
    tipo="puerta",
    etiqueta="Puerta",
    vdo_tipo="contenedor",
    vdo_subtipo="puerta",
    feature="VDO.cad.objects.vdo_cad_puerta:PuertaFeature",
    viewprovider="VDO.cad.objects.vdo_cad_puerta:ViewProviderPuerta",
    fabrica="VDO.cad.objects.vdo_cad_puerta:make_puerta",
    panel="VDO.ui.vdo_ui_puerta_task:PuertaTaskPanel",
    motor="VDO.core.vdo_math_puerta:calcular_dimensiones_batiente",
    legacy_props=("TipoSistema", "SentidoApertura"),
    params=(
        Param("TipoSistema", "enum", "Sistema", etiqueta="Tipo de sistema",
              ayuda="Tipo de sistema de puerta",
              default="Batiente Vertical",
              opciones=("Batiente Vertical", "Basculante Horizontal",
                        "Corrediza"),
              clave_motor="tipo_sistema"),
        Param("TipoMontaje", "enum", "Montaje", etiqueta="Tipo de montaje",
              ayuda="Tipo de montaje (batiente)", default="Parche",
              opciones=("Parche", "Semiparche", "Embebida"),
              clave_motor="tipo_montaje"),
        Param("SentidoApertura", "enum", "Apertura",
              etiqueta="Sentido de apertura", ayuda="Sentido de apertura",
              default="Izquierda",
              opciones=("Izquierda", "Derecha", "Doble", "Hacia Arriba",
                        "Hacia Abajo", "2 hojas", "3 hojas"),
              clave_motor="sentido_apertura"),
        Param("SistemaApertura", "enum", "Sistema de Apertura",
              etiqueta="Sistema de apertura",
              ayuda="Sistema de apertura/fachada", default=APERTURA_TIRADOR,
              opciones=(APERTURA_TIRADOR, APERTURA_GOLA,
                        APERTURA_45_GRADOS, APERTURA_PUSH_OPEN),
              clave_motor="sistema_apertura"),
        Param("HardwareSKU", "string", "Herraje", etiqueta="SKU de herraje",
              ayuda="SKU comercial del herraje activo", default="",
              clave_config="hardware_sku"),
        Param("VDO_Vano_ID", "string", "Vinculación",
              ayuda="Identificador del vano vinculado (ej. '(x1,y1)')",
              default="", ui=False, clave_config="vdo_vano_id"),
        Param("FuerzaPistonRecomendada", "string", "Físico",
              etiqueta="Pistón recomendado",
              ayuda="Fuerza de pistón recomendada (solo lectura)",
              default="", ui=False, solo_lectura=True),

        Param("VDO_Deltas_JSON", "string", "VDO",
              ayuda="Deltas de borde netos para el contrato de fachada universal (JSON)",
              default="{}", ui=False),

        Param("Ancho", "length", "Dimensiones", etiqueta="Ancho",
              ayuda="Ancho de la puerta (mm)", default=400.0,
              minimo=1.0, maximo=4000.0, sufijo=" mm", clave_motor="ancho"),
        Param("Alto", "length", "Dimensiones", etiqueta="Alto",
              ayuda="Alto de la puerta (mm)", default=700.0,
              minimo=1.0, maximo=4000.0, sufijo=" mm", clave_motor="alto"),
        Param("Espesor", "int", "Dimensiones", etiqueta="Espesor",
              ayuda="Espesor del panel (mm)", default=18,
              minimo=1, maximo=60, decimales=0, sufijo=" mm",
              clave_motor="espesor"),

        Param("PosX", "distance", "Posición", etiqueta="Pos. X",
              ayuda="Posición X de la puerta (mm)", default=0.0,
              minimo=-10000.0, maximo=10000.0, sufijo=" mm",
              clave_config="pos_x"),
        Param("PosY", "distance", "Posición", etiqueta="Pos. Y",
              ayuda="Posición Y de la puerta (mm)", default=0.0,
              minimo=-10000.0, maximo=10000.0, sufijo=" mm",
              clave_config="pos_y"),
        Param("PosZ", "distance", "Posición", etiqueta="Pos. Z",
              ayuda="Posición Z de la puerta (mm)", default=0.0,
              minimo=-10000.0, maximo=10000.0, sufijo=" mm",
              clave_config="pos_z"),

        *params_fabricacion("contenedor", "puerta",
                            "Material de la hoja"),

        *PARAMS_POSE,
        *params_retroenlace("Módulo COCO padre"),
    ),
)


# =====================================================================
# ZOCALO — cajon perimetral de base
# =====================================================================
SPEC_ZOCALO = ModuloSpec(
    tipo="zocalo",
    etiqueta="Zócalo",
    vdo_tipo="contenedor",
    vdo_subtipo="zocalo",
    feature="VDO.cad.objects.vdo_cad_zocalo:ZocaloFeature",
    viewprovider="VDO.cad.objects.vdo_cad_zocalo:ViewProviderZocalo",
    fabrica="VDO.cad.objects.vdo_cad_zocalo:make_zocalo",
    panel="VDO.ui.vdo_ui_zocalo_task:ZocaloTaskPanel",
    motor="VDO.core.vdo_math_zocalo:calcular_geometria_zocalo",
    legacy_props=("AltoZocalo", "DistanciaFrente"),
    params=(
        Param("Ancho", "length", "Dimensiones", etiqueta="Ancho",
              ayuda="Ancho total del mueble (mm)", default=600.0,
              minimo=1.0, maximo=4000.0, sufijo=" mm", clave_motor="ancho"),
        Param("Fondo", "length", "Dimensiones", etiqueta="Fondo",
              ayuda="Fondo total del mueble (mm)", default=580.0,
              minimo=1.0, maximo=2000.0, sufijo=" mm", clave_motor="fondo"),
        Param("AltoZocalo", "length", "Dimensiones", etiqueta="Alto zócalo",
              ayuda="Alto del zócalo (mm)", default=100.0,
              minimo=1.0, maximo=400.0, sufijo=" mm",
              clave_motor="alto_zocalo"),
        Param("EspesorTablero", "length", "Dimensiones",
              etiqueta="Espesor tablero",
              ayuda="Espesor del tablero del zócalo (mm)",
              default=VDO_D.ESPESOR_DEFAULT, minimo=1.0, maximo=40.0,
              decimales=0, sufijo=" mm", clave_motor="espesor_tablero"),

        Param("DistanciaFrente", "length", "Separación",
              etiqueta="Separación frontal",
              ayuda="Distancia desde el frente del mueble (mm)",
              default=50.0, minimo=0.0, maximo=500.0, sufijo=" mm",
              clave_motor="distancia_frente"),
        Param("DistanciaCostados", "length", "Separación",
              etiqueta="Distancia costados",
              ayuda="Distancia desde los costados (mm)",
              default=0.0, minimo=0.0, maximo=500.0, sufijo=" mm",
              clave_motor="distancia_costados"),
        Param("DistanciaTrasera", "length", "Separación",
              etiqueta="Distancia trasera",
              ayuda="Distancia desde el fondo del mueble (mm)",
              default=20.0, minimo=0.0, maximo=500.0, sufijo=" mm",
              clave_motor="distancia_trasera"),

        Param("TieneTrasera", "bool", "Estructura", etiqueta="Tiene trasera",
              ayuda="Cierra el cajón del zócalo por detrás", default=True,
              clave_motor="tiene_trasera"),
        Param("AmarresIntermedios", "int", "Estructura",
              etiqueta="Divisiones interiores",
              ayuda="Costillas de refuerzo entre frente y trasera",
              default=0, minimo=0, maximo=20, decimales=0,
              clave_motor="amarres_intermedios"),

        *params_fabricacion("contenedor", "zocalo",
                            "Material de las piezas",
                            material_al_motor=True),

        *PARAMS_POSE,
    ),
)


# =====================================================================
# PANEL — tablero fisico agnostico de semantica
# =====================================================================
SPEC_PANEL = ModuloSpec(
    tipo="panel",
    etiqueta="Panel",
    vdo_tipo="panel",
    vdo_subtipo="panel",
    feature="VDO.cad.objects.vdo_cad_panel:PanelFeature",
    viewprovider="VDO.cad.objects.vdo_cad_panel:ViewProviderPanel",
    fabrica="VDO.cad.objects.vdo_cad_panel:crear_pieza",
    panel="VDO.ui.vdo_ui_panel_task:PanelTaskPanel",
    motor="VDO.core.vdo_math_reengrose:calcular_geometria_reengrose",
    legacy_props=("VDO_Orientacion", "Largo"),
    params=(
        Param("Largo", "length", "Dimensiones", etiqueta="Largo",
              ayuda="Largo del tablero (mm)", default=VDO_D.ANCHO_DEFAULT,
              minimo=1.0, maximo=4000.0, sufijo=" mm", clave_motor="largo"),
        Param("Ancho", "length", "Dimensiones", etiqueta="Ancho",
              ayuda="Ancho del tablero (mm)", default=VDO_D.FONDO_DEFAULT,
              minimo=1.0, maximo=4000.0, sufijo=" mm", clave_motor="ancho"),
        Param("Espesor", "length", "Dimensiones", etiqueta="Espesor",
              ayuda="Espesor del tablero (mm)",
              default=VDO_D.ESPESOR_DEFAULT, minimo=1.0, maximo=200.0,
              sufijo=" mm", clave_motor="espesor"),

        Param("VDO_Tipo", "string", "VDO", ayuda="Tipo de objeto",
              default="panel", ui=False),
        # VDO_Subtipo es nuevo en el panel: era el unico modulo que no lo
        # declaraba, asi que no habia forma uniforme de clasificarlo.
        Param("VDO_Subtipo", "string", "VDO", ayuda="Subtipo",
              default="panel", ui=False),
        Param("VDO_Orientacion", "enum", "VDO", etiqueta="Orientación",
              ayuda="Orientación del panel",
              default=lambda: VDO_D.ORIENTACION_DEFAULT,
              opciones=lambda: list(VDO_D.ORIENTACIONES_VALIDAS),
              clave_motor="orientacion"),
        Param("VDO_Etiqueta", "string", "VDO", etiqueta="Etiqueta",
              ayuda="Etiqueta libre de la pieza", default="Panel",
              clave_config="etiqueta"),
        Param("VDO_Material_Ref", "string", "VDO", etiqueta="Material",
              ayuda="Material de la pieza", default=MATERIAL_DEFAULT),
        Param("VDO_Rol", "string", "VDO",
              ayuda="Rol del panel dentro del COCO "
                    "(lateral_izquierdo, techo, etc.)",
              default="", ui=False),
        Param("VDO_Mocheos_JSON", "string", "VDO",
              ayuda="Lista de cortes/mocheos a aplicar al solido del panel "
                    "(JSON con cajas {x,y,z,w,h,d} en marco local)",
              default="[]", ui=False),
        Param("VDO_Encastre_mm", "length", "VDO",
              ayuda="Longitud que la pieza suma en la lista de corte para "
                    "encastrar en una ranura (0 = sin encastre)",
              default=0.0, minimo=0.0, maximo=200.0, ui=False),
        Param("VDO_Mecanizados_JSON", "string", "VDO",
              ayuda="Operaciones de mecanizado de taller sobre el panel "
                    "(JSON; no altera la geometria B-Rep)",
              default="[]", ui=False),

        *_cantos(),
        *PARAMS_REENGROSE,
        *PARAMS_POSE,
        # El panel cuelga del COCO directamente, no de un vano: su
        # LocalPlacement se mide contra el marco del padre.
        *params_retroenlace(ayuda_local="Pose relativa al COCO padre"),
    ),
)


# =====================================================================
# TAMBOR — panel entamborado / repisa flotante
# =====================================================================
# VDO_Tipo era "tambor", valor que vdo_cam_cutlist no contempla: su
# if/elif sobre "panel"/"contenedor" caia al vacio sin avisar y el
# VDO_Paneles_JSON que el modulo rellena no lo leia nadie. Pasa a
# "contenedor", que es lo que es: un conjunto de piezas.
SPEC_TAMBOR = ModuloSpec(
    tipo="tambor",
    etiqueta="Repisa entamborada",
    vdo_tipo="contenedor",
    vdo_subtipo="tambor",
    feature="VDO.cad.objects.vdo_cad_tambor:TamborFeature",
    viewprovider="VDO.cad.objects.vdo_cad_tambor:ViewProviderTambor",
    fabrica="VDO.cad.objects.vdo_cad_tambor:make_tambor",
    panel="VDO.ui.vdo_ui_tambor_task:TamborTaskPanel",
    motor="VDO.core.vdo_math_tambor:calcular_geometria_tambor",
    legacy_props=("EspesorTotal", "AnchoListon"),
    params=(
        Param("Largo", "length", "Dimensiones", etiqueta="Largo X",
              ayuda="Largo en X (Ancho frontal)", default=800.0,
              minimo=1.0, maximo=4000.0, sufijo=" mm", clave_motor="largo"),
        Param("Ancho", "length", "Dimensiones",
              etiqueta="Ancho Y / Profundidad", ayuda="Profundidad en Y",
              default=250.0, minimo=1.0, maximo=2000.0, sufijo=" mm",
              clave_motor="ancho"),
        Param("EspesorTotal", "length", "Dimensiones",
              etiqueta="Espesor total",
              ayuda="Espesor total (sándwich)", default=42.0,
              minimo=1.0, maximo=300.0, sufijo=" mm",
              clave_motor="espesor_total"),

        Param("EspesorTapas", "length", "Estructura", etiqueta="Espesor tapas",
              ayuda="Espesor de las 2 tapas de melamina", default=6.0,
              minimo=1.0, maximo=60.0, sufijo=" mm",
              clave_motor="espesor_tapas"),
        Param("AnchoListon", "length", "Estructura", etiqueta="Ancho listón",
              ayuda="Ancho de listonería interior", default=30.0,
              minimo=1.0, maximo=300.0, sufijo=" mm",
              clave_motor="ancho_liston"),
        Param("CostillasInteriores", "int", "Estructura",
              etiqueta="Costillas interiores", ayuda="Cantidad de costillas",
              default=2, minimo=0, maximo=20, decimales=0,
              clave_motor="costillas"),

        Param("TipoTambor", "enum", "Configuración", etiqueta="Tipo",
              ayuda="Tipo de panel entamborado",
              default="Repisa Flotante (Tenedor)",
              opciones=("Repisa Flotante (Tenedor)", "Panel Cerrado 4 Lados"),
              clave_config="tipo_tambor"),
        Param("ModoTenedor", "enum", "Anclaje", etiqueta="Modo tenedor",
              ayuda="Estrategia para el tenedor a pared",
              default="Hueco Abierto Posterior",
              opciones=("Hueco Abierto Posterior",
                        "Liston Taladrado (Varillas)"),
              clave_config="modo_tenedor"),
        Param("ProfundidadVanoTenedor", "length", "Anclaje",
              etiqueta="Profundidad de vano",
              ayuda="Profundidad libre para varillas", default=140.0,
              minimo=0.0, maximo=2000.0, sufijo=" mm",
              clave_motor="prof_tenedor"),
        Param("DiametroVarillaTenedor", "length", "Anclaje",
              etiqueta="Diámetro de varilla",
              ayuda="Diámetro de varillas de acero", default=12.0,
              minimo=1.0, maximo=60.0, sufijo=" mm",
              clave_motor="diam_varilla"),

        Param("VDO_Modificadores_JSON", "string", "VDO",
              ayuda="Modificadores geométricos embebidos (JSON)",
              default="[]", ui=False),

        *params_fabricacion("contenedor", "tambor", "Material de tapas",
                            con_resumen=False),

        *PARAMS_POSE,
    ),
)


# =====================================================================
# ESPACIO — contenedor territorial (T2, ADR-005)
#
# Nodo relacional puro sin geometria propia: Shape NULA, sin CS local
# propio y sin GeoFeatureGroupExtensionPython. Agrupa por Hijos
# (PropertyLinkListChild) y clasifica por predicado (Arquitectura /
# Mobiliario / Assets), no por carpetas. vdo_tipo="espacio" no pertenece a
# VDO_TIPOS_FABRICABLES: es invisible para lista de corte y nesting
# (no es mueble manufacturable), lo cual es correcto.
# motor=None: no hay calculo geometrico que ejecutar.
# =====================================================================
SPEC_ESPACIO = ModuloSpec(
    tipo="espacio",
    etiqueta="Espacio",
    vdo_tipo="espacio",
    vdo_subtipo="espacio",
    feature="VDO.cad.objects.vdo_cad_espacio:EspacioFeature",
    viewprovider="VDO.cad.objects.vdo_cad_espacio:ViewProviderEspacio",
    fabrica="VDO.cad.objects.vdo_cad_espacio:make_espacio",
    panel="VDO.ui.vdo_ui_espacio_task:EspacioTaskPanel",
    motor=None,
    params=(
        Param("NombreEspacio", "string", "Identificacion",
              ayuda="Nombre legible del recinto (ej. Cocina, Habitacion Juan)",
              default="Espacio", clave_config="nombre_espacio"),
        Param("VDO_Tipo", "string", "Sistema",
              ayuda="Identificador de clase del objeto Espacio",
              default="EspacioFeature", ui=False, solo_lectura=True),
        Param("NivelPiso", "distance", "Datos de obra",
              ayuda="Cota del nivel de piso finito respecto a referencia "
                    "de obra (acepta valores negativos)",
              default=0.0, sufijo=" mm", clave_motor="nivel_piso"),
        Param("AlturaCielorraso", "length", "Datos de obra",
              ayuda="Altura del cielorraso/losa superior respecto a "
                    "NivelPiso",
              default=2400.0, minimo=1.0, maximo=12000.0, sufijo=" mm",
              clave_motor="altura_cielorraso"),
        Param("NotasInstalacion", "string", "Datos de obra",
              ayuda="Notas de instalacion del recinto (multilinea)",
              default="", ui=False),
        Param("RequisitosCliente", "string", "Datos de obra",
              ayuda="Requisitos del cliente para el recinto",
              default="", ui=False),
        Param("Hijos", "link_list_child", "Estructura Logica",
              ayuda="Arquitectura, mobiliario y assets contenidos en el "
                    "espacio",
              default=list, ui=False),
    ),
)


# =====================================================================
# Esquema del proyecto (metadatos, no modulo geometrico)
# =====================================================================

SPEC_PROYECTO = ModuloSpec(
    tipo="proyecto",
    etiqueta="Proyecto",
    vdo_tipo="proyecto",
    vdo_subtipo="proyecto",
    feature="VDO.cad.objects.vdo_cad_proyecto:ProyectoFeature",
    viewprovider="VDO.cad.objects.vdo_cad_proyecto:ViewProviderProyecto",
    fabrica="VDO.cad.objects.vdo_cad_proyecto:make_proyecto",
    panel="VDO.ui.vdo_ui_proyecto_task:ProyectoTaskPanel",
    motor=None,
    params=(
        Param("Nombre", "string", "Identificacion",
              ayuda="Nombre del proyecto (fuente de verdad para el membrete)",
              default="Proyecto VDO", clave_config="nombre"),
        Param("Cliente", "string", "Identificacion",
              ayuda="Nombre del cliente",
              default="", clave_config="cliente"),
        Param("Disenador", "string", "Identificacion",
              ayuda="Nombre del diseñador responsable",
              default="", clave_config="disenador"),
        Param("Fecha", "string", "Identificacion",
              ayuda="Fecha de creacion del proyecto",
              default="", clave_config="fecha"),
        Param("VDO_Tipo", "string", "Sistema",
              ayuda="Identificador de clase del objeto Proyecto",
              default="ProyectoFeature", ui=False, solo_lectura=True),
    ),
)


# =====================================================================
# EL CATALOGO
# =====================================================================

# MODULOS: solo modulos geometricos fabricables (coco, cajon, puerta,
# zocalo, panel, tambor). tests/test_contrato_modulos.py recorre MODULOS
# exigiendo contrato de fabricacion (vdo_tipo en VDO_TIPOS_FABRICABLES,
# VDO_Subtipo, VDO_Material_Ref, legacy_props, motor).
MODULOS: Dict[str, ModuloSpec] = {
    s.tipo: s for s in (
        SPEC_COCO, SPEC_CAJON, SPEC_PUERTA, SPEC_ZOCALO, SPEC_PANEL,
        SPEC_TAMBOR)
}

# ENTIDADES: objetos de nivel proyecto que no son modulos geometricos
# (no entran en lista de corte ni nesting). vdo_tipo no esta en
# VDO_TIPOS_FABRICABLES por diseno.
ENTIDADES: Dict[str, ModuloSpec] = {
    s.tipo: s for s in (
        SPEC_ESPACIO, SPEC_PROYECTO)
}

# CATALOGO: vista unificada para resolver specs (spec, resolver_modulo,
# aplicar, config_de, validar_objeto). Los consumidores que necesitan
# contrato de fabricacion usan MODULOS; los que necesitan resolver cualquier
# objeto VDO usan CATALOGO.
CATALOGO: Dict[str, ModuloSpec] = {**MODULOS, **ENTIDADES}


VARIANTES: Dict[str, VarianteCreacion] = {
    v.clave: v for v in (
        VarianteCreacion(
            clave="coco_4c", modulo="coco", etiqueta="COCO",
            icono="vdo_coco.svg", comando="VDO_Coco4C",
            menu_text="COCO 4C",
            tooltip="Crear un cofre de 4 caras parametrico "
                    "(modulo de mueble)",
            config={"nombre": "COCO_4C"}, orden=10),
        VarianteCreacion(
            clave="cajon", modulo="cajon", etiqueta="Cajon",
            icono="vdo_cajon.svg", comando="VDO_Cajon", menu_text="Cajon",
            tooltip="Crear un cajon parametrico con correderas",
            config={"nombre": "Cajon"}, orden=20),
        VarianteCreacion(
            clave="puerta", modulo="puerta", etiqueta="Puerta",
            icono="vdo_puerta.svg", comando="VDO_Puerta",
            menu_text="Puerta",
            tooltip="Crear una puerta de mueble parametrica",
            config={"nombre": "Puerta"}, orden=30),
        VarianteCreacion(
            clave="zocalo", modulo="zocalo", etiqueta="Zocalo",
            icono="vdo_zocalo.svg", comando="VDO_Zocalo",
            menu_text="Zocalo",
            tooltip="Crear un zocalo parametrico de base",
            config={"nombre": "Zocalo"}, orden=40),
        VarianteCreacion(
            clave="panel_estandar", modulo="panel",
            etiqueta="Panel estandar", icono="vdo_panel_estandar.svg",
            comando="VDO_PanelEstandar", menu_text="Panel Estandar",
            tooltip="Crear un panel estandar parametrico "
                    "(tablero horizontal)",
            # crear_pieza() exige 'orientacion' explicita
            # (_validar_orientacion), no la adivina.
            config={"nombre": "Panel", "etiqueta": "Panel estandar",
                    "orientacion": "horizontal"}, orden=50, grupo_barra="piezas"),
        VarianteCreacion(
            clave="panel_fachada", modulo="panel",
            etiqueta="Panel fachada", icono="vdo_panel_fachada.svg",
            comando="VDO_PanelFachada", menu_text="Panel Fachada",
            tooltip="Crear un panel de fachada parametrico "
                    "(tablero vertical)",
            config={"nombre": "Panel_Fachada", "etiqueta": "Fachada",
                    "orientacion": "vertical"}, orden=60, grupo_barra="piezas"),
        # Creable por API y macro, sin boton propio: el hueco de la barra
        # lo ocupa VDO_PanelDivision, que NO crea un panel sino que abre
        # el editor de divisiones del COCO seleccionado. Son dos cosas
        # distintas que compartian nombre; se mantiene el boton historico
        # y la variante conserva su comando para quien la invoque.
        VarianteCreacion(
            clave="panel_division", modulo="panel",
            etiqueta="Panel division", icono="vdo_panel.svg",
            comando="VDO_PanelDivisionNuevo",
            menu_text="Panel Division",
            tooltip="Crear un panel de division parametrico",
            config={"nombre": "Division", "etiqueta": "Division",
                    "orientacion": "vertical"},
            orden=70, grupo_barra="piezas", en_barra=False),
        VarianteCreacion(
            clave="tambor", modulo="tambor",
            etiqueta="Repisa entamborada", icono="vdo_panel.svg",
            comando="VDO_Tambor", menu_text="Tambor / Repisa",
            tooltip="Crear una repisa entamborada flotante parametrica",
            config={"nombre": "Repisa_Entamborada"}, orden=80, grupo_barra="piezas"),
    )
}

# Nombres heredados de las macros de la era Macro/.
ALIAS = {
    "coco": "coco_4c",
    "coco_4": "coco_4c",
    "cajon_oculta": "cajon",
    "panel": "panel_estandar",
    "fachada": "panel_fachada",
    "division": "panel_division",
    "repisa": "tambor",
}


# =====================================================================
# API de consulta
# =====================================================================

def spec_de_variante(clave: str) -> ModuloSpec:
    """ModuloSpec de una clave de variante (acepta alias)."""
    return MODULOS[variante(clave).modulo]


def variante(clave: str) -> VarianteCreacion:
    clave = ALIAS.get(clave, clave)
    if clave not in VARIANTES:
        raise ValueError(
            f"Variante de modulo VDO desconocida: '{clave}'. "
            f"Disponibles: {', '.join(sorted(VARIANTES))}.")
    return VARIANTES[clave]


def variantes_ordenadas() -> Tuple[VarianteCreacion, ...]:
    return tuple(sorted(VARIANTES.values(), key=lambda v: (v.orden, v.clave)))


# Comandos que no crean un modulo geometrico y por tanto no salen del catalogo.
# Son cuatro y estan aqui para que el orden de la barra siga siendo una
# sola declaracion, no dos listas que hay que mantener de acuerdo.
COMANDO_NUEVO_PROYECTO = "VDO_NuevoProyecto"
COMANDO_CREAR_ESPACIO = "VDO_CrearEspacio"
COMANDO_DIVISIONES = "VDO_PanelDivision"
COMANDO_EDITAR = "VDO_Editar"

COMANDOS_FIJOS = (COMANDO_NUEVO_PROYECTO, COMANDO_CREAR_ESPACIO,
                  COMANDO_DIVISIONES, COMANDO_EDITAR)


def comandos_de_creacion() -> Tuple[str, ...]:
    """Nombres de comando de las variantes, en orden de catalogo."""
    return tuple(v.comando for v in variantes_ordenadas())


def nombres_comandos() -> Tuple[str, ...]:
    """Todos los comandos del workbench, en orden de registro.

    Lo consume vdo_initgui.COMANDOS. Vive aqui, y no alli, porque es
    DATO: asi se puede comprobar en un test headless sin importar
    FreeCADGui (cuya clase Workbench no existe en FreeCADCmd).
    """
    return ((COMANDO_NUEVO_PROYECTO, COMANDO_CREAR_ESPACIO)
            + comandos_de_creacion()
            + (COMANDO_DIVISIONES, COMANDO_EDITAR))


def toolbar_muebles() -> Tuple[str, ...]:
    """Barra "VDO Muebles", derivada del catalogo.

    Los separadores agrupan contenedores (COCO, cajon, puerta, zocalo)
    frente a piezas sueltas (paneles, tambor), que es el criterio con el
    que estaba escrita a mano.
    """
    def bloque(nombre):
        return tuple(v.comando for v in variantes_ordenadas()
                     if v.en_barra and v.grupo_barra == nombre)

    return ((COMANDO_NUEVO_PROYECTO, COMANDO_CREAR_ESPACIO, "Separator")
            + bloque("modulos") + ("Separator",)
            + bloque("piezas") + (COMANDO_DIVISIONES,)
            + ("Separator", COMANDO_EDITAR))


def spec(tipo: str) -> ModuloSpec:
    if tipo not in CATALOGO:
        raise ValueError(
            f"Modulo VDO desconocido: '{tipo}'. "
            f"Disponibles: {', '.join(sorted(CATALOGO))}.")
    return CATALOGO[tipo]


def resolver_modulo(obj) -> Optional[ModuloSpec]:
    """Identifica de que modulo VDO es `obj`, o None si no lo es.

    Sustituye a los predicados por duck-typing de vdo_cad_view_base
    (_es_coco, _es_cajon, _es_zocalo, _es_panel), que adivinaban el tipo
    por la presencia de ciertas dimensiones. Dos modulos futuros con
    medidas parecidas colisionaban sin remedio; y puerta y tambor nunca
    tuvieron predicado, asi que eran irreparables e inabribles.

    1. VDO_Modulo, el testigo explicito (via autoritativa).
    2. legacy_props, respaldo para documentos guardados antes del testigo.
    """
    if obj is None:
        return None

    clave = getattr(obj, PROP_MODULO, None)
    if clave and clave in CATALOGO:
        return CATALOGO[clave]

    for s in CATALOGO.values():
        if s.legacy_props and all(hasattr(obj, p) for p in s.legacy_props):
            return s
    return None


def aplicar(obj, tipo: str) -> int:
    """Declara en `obj` el esquema del modulo `tipo`."""
    return aplicar_esquema(obj, spec(tipo))


def config_de(obj) -> Dict[str, object]:
    """Dict de entrada del motor del modulo al que pertenece `obj`."""
    s = resolver_modulo(obj)
    return config_desde_objeto(obj, s) if s else {}


def validar_objeto(obj) -> Tuple[str, ...]:
    """Errores de rango/dominio de `obj` segun su esquema."""
    s = resolver_modulo(obj)
    return validar(obj, s) if s else ()


__all__ = [
    "MODULOS", "ENTIDADES", "CATALOGO", "VARIANTES", "ALIAS",
    "VDO_TIPOS_FABRICABLES",
    "MATERIAL_DEFAULT", "CANTOS_VALIDOS",
    "SPEC_COCO", "SPEC_CAJON", "SPEC_PUERTA", "SPEC_ZOCALO", "SPEC_PANEL",
    "SPEC_TAMBOR", "SPEC_ESPACIO", "SPEC_PROYECTO",
    "spec", "variante", "spec_de_variante", "variantes_ordenadas",
    "resolver_modulo", "aplicar", "config_de", "validar_objeto",
    "params_fabricacion", "nombres_comandos", "toolbar_muebles",
    "comandos_de_creacion", "COMANDOS_FIJOS", "COMANDO_EDITAR",
    "COMANDO_DIVISIONES", "COMANDO_NUEVO_PROYECTO", "COMANDO_CREAR_ESPACIO",
]
