# VDO — Carpintería Paramétrica

Workbench de FreeCAD para diseño, modulación y fabricación de carpintería
paramétrica y mobiliario. Integra las herramientas BIM/Arch clásicas (muros,
puertas, ventanas, espacios) con un motor propio de módulos de mueble.

Requiere **FreeCAD 1.0 o superior** y el workbench **BIM** (incluido en FreeCAD).

## Instalación

```bash
git clone <url> VDO-CarpinteriaParametrica
cd VDO-CarpinteriaParametrica
python3 tools/install.py --copy     # en otro equipo
python3 tools/install.py            # en desarrollo (enlace simbólico)
```

El instalador pregunta a FreeCAD dónde está su directorio de usuario; no lo
adivina. Reinicia FreeCAD y elige **VDO - Muebles Paramétricos**.

Verifica la instalación:

```bash
python3 tools/vdo_verify.py --gui        # registro real en la GUI
python3 tools/vdo_verify.py --e2e        # crea un mueble, lo guarda y lo reabre,
                                         # y comprueba el contenido de vano (N5)
python3 tools/vdo_verify.py --insertos   # sólo el N5: cajones del COCO
```

Del N3 en adelante el arnés usa *sondas*: macros que corren en el FreeCAD
real, dejan un JSON en `.verif/` y cierran la ventana. Cómo escribir una y
qué medir en ella: `docs/05` §5.

## Estructura

```
Init.py  InitGui.py      Cascarones de arranque (ver "Trampas" abajo)
package.xml metadata.txt Manifiestos del Addon Manager
VDO/                     Paquete Python único y autocontenido
  _paths.py              Fuente de verdad de todas las rutas
  vdo_initgui.py         Comandos y clase del workbench
  hub/                   EL CATÁLOGO: esquema de parámetros y registro
    vdo_hub_schema.py      Param / ModuloSpec y sus derivaciones
    vdo_hub_registry.py    Los 6 módulos y las 8 variantes creables
    vdo_hub_module_props.py  Bloques comunes (pose, retroenlace, reengrose)
    vdo_hub_defaults.py    Defaults desde vdo_manifest.json
  core/                  Matemática pura (vdo_math_*), sin FreeCAD
  cad/                   Objetos paramétricos (vdo_cad_*) y ViewProviders
  ui/                    Paneles de tarea Qt (vdo_ui_*)
  cam/                   Listas de corte, nesting, optimizador (vdo_cam_*)
  shared/                Módulos compartidos (vdo_shared_*)
  resources/icons/       SVG
tools/                   install.py, vdo_verify.py, vdo_audit.py
tests/  docs/  macros/
```

## Tres trampas de FreeCAD que condicionan el diseño

Descubiertas por ingeniería inversa comparando con BIM, Draft y Nesting. El
arnés de verificación las comprueba como invariantes para que no reaparezcan.

**1. `__file__` no existe en `Init.py` / `InitGui.py`.** FreeCAD los ejecuta
con `exec()` sin definirlo. Hay que derivar la ruta de
`FreeCAD.getUserAppDataDir()` / `getResourceDir()`, como hacen BIM y Draft.

**2. `exec()` usa diccionarios `globals` y `locals` distintos.** Lo que se
asigna a nivel de módulo en `InitGui.py` cae en `locals`, pero los métodos de
una clase definida ahí resuelven contra `globals`: cualquier helper queda
invisible y revienta con `NameError` al construirse la toolbar, no al cargar.
Por eso `InitGui.py` es solo un cascarón y las clases viven en
`VDO/vdo_initgui.py`, que sí es un módulo importado de verdad.

**3. FreeCAD añade cada `Mod/<dir>` al `sys.path` global.** Un módulo
`vdo_guardian.py` en la raíz del workbench queda visible para todo Python y
puede colisionar con otro addon. Todo va encapsulado en `VDO.shared.*`.

## El catálogo: cómo se añade un módulo

Cada parámetro de un módulo se declara **una sola vez**, como un `Param` en
`VDO/hub/vdo_hub_registry.py`. De esa declaración se derivan:

| Derivado | Quién lo hace |
|---|---|
| Las propiedades del `FeaturePython` | `aplicar_esquema(obj, spec)` |
| El dict de entrada del motor | `config_desde_objeto(obj, spec)` |
| Lo que escribe la fábrica `make_*` | `aplicar_config(obj, spec, config)` |
| El formulario del Task Panel | `construir_formulario(spec)` |
| La validación de rangos | `validar(obj, spec)` — también headless |
| El comando y su sitio en la barra | `CmdCrearModulo` + `toolbar_muebles()` |
| La identificación del tipo | `resolver_modulo(obj)` vía `VDO_Modulo` |

**Para dar de alta un módulo nuevo hacen falta dos ediciones:**

1. `VDO/cad/objects/vdo_cad_<x>.py` con `XFeature` (su `__init__` es una
   llamada a `aplicar_esquema`), `ViewProviderX` y `make_x`; y su motor en
   `VDO/core/vdo_math_<x>.py`.
2. Un `ModuloSpec` y una `VarianteCreacion` en `vdo_hub_registry.py`.

`tests/test_contrato_modulos.py` recorre el catálogo y falla si el módulo
nuevo no cumple el contrato: `VDO_Tipo` que la lista de corte entienda,
metadatos de fabricación, despiece publicado, rangos declarados, identificable
sin ambigüedad, icono presente y panel resoluble. Ese test existe porque la
convención *no escrita* ya se incumplió dos veces: la **puerta** no declaraba
`VDO_Tipo` y quedaba fuera del cutlist y del nesting, y el **tambor** lo
declaraba con un valor que el cutlist no contempla.

Si cambias las propiedades de un módulo, regenera la instantánea de contrato:

```bash
FreeCADCmd tools/vdo_snapshot_props.py   # tests/datos/props_snapshot.json
```

## Desarrollo

`tools/vdo_audit.py` levanta el grafo de imports, detecta imports irresolubles
y módulos no alcanzables desde el workbench.

Al añadir un comando: la implementación va en `VDO/vdo_initgui.py`, **nunca**
en `InitGui.py`. Los comandos de creación no se escriben a mano: salen de
`vdo_hub_registry.VARIANTES` vía `CmdCrearModulo`.
