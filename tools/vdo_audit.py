import ast, re, sys
from pathlib import Path

# Cadenas que son rutas de modulo del paquete: "VDO.ui.vdo_ui_x"
RE_MODULO = re.compile(r"^VDO\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+$")
RAIZ = Path(__file__).resolve().parent.parent  # raiz del repo
EXCL = {"__pycache__", "docs", ".pytest_cache", "node_modules",
        "tools", ".verif", ".git"}

STD = set(sys.stdlib_module_names)
FREECAD = {"FreeCAD","FreeCADGui","Part","Draft","Arch","Sketcher","Mesh","PySide",
           "PySide2","PySide6","Spreadsheet","TechDraw","DraftTools","bimcommands",
           "Arch_rc","nativeifc","WorkingPlane","draftutils","BimStatus","ArchComponent",
           "DraftVecUtils","ArchCommands","Part2DObject","pivy","TechDrawGui","Import"}
EXT = {"numpy","shapely","pytest","yaml","requests","PIL"}

archivos = {}
for p in RAIZ.rglob("*.py"):
    if any(x in p.parts for x in EXCL):
        continue
    archivos[p] = p
for p in RAIZ.glob("macros/*.FCMacro"):
    archivos[p] = p

# modulos disponibles
mods_raiz = {p.stem for p in RAIZ.glob("*.py")}
paquetes = set()
for p in RAIZ.rglob("__init__.py"):
    if any(x in p.parts for x in EXCL): continue
    paquetes.add(".".join(p.relative_to(RAIZ).parts[:-1]))

grafo, roto = {}, []
for p in sorted(archivos):
    try:
        arbol = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError as e:
        roto.append((str(p.relative_to(RAIZ)), f"SyntaxError: {e}")); continue
    deps = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names: deps.add(a.name)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            deps.add(n.module)
            # "from VDO.shared import vdo_shared_finish" tambien es una dependencia
            # de VDO.shared.vdo_shared_finish. Sin esto el grafo solo veia el
            # paquete y reportaba como no alcanzables modulos bien vivos
            # (vdo_shared_finish, vdo_shared_guardian, vdo_shared_manifest), tapando los
            # huerfanos de verdad.
            for a in n.names:
                if a.name != "*":
                    deps.add(f"{n.module}.{a.name}")
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            # Imports dinamicos por cadena: __import__("VDO.ui.x"),
            # las rutas "VDO.modulo:nombre" del catalogo
            # (vdo_hub_registry), el registro ESPECIFICACIONES, etc.
            # Sin esto el grafo no ve esas aristas y marca como huerfanos
            # modulos que SI se cargan (los TaskPanel, los motores).
            #
            # El catalogo usa la forma "paquete.modulo:nombre": se parte
            # por ':' para quedarse con el modulo. Sin este corte los
            # motores y paneles referenciados solo desde el catalogo
            # salian como inalcanzables.
            ruta = n.value.split(":", 1)[0]
            if RE_MODULO.match(ruta):
                deps.add(ruta)
    grafo[str(p.relative_to(RAIZ))] = deps

def resuelve(m):
    top = m.split(".")[0]
    if top in STD or top in FREECAD or top in EXT: return "externo"
    if m in paquetes or any(m.startswith(q+".") for q in paquetes): return "interno"
    if top == "VDO": return "interno" if m.replace(".", "/") else "interno"
    if top in mods_raiz: return "raiz"
    return None

print("="*72); print("IMPORTS NO RESOLUBLES"); print("="*72)
problemas = {}
for f, deps in grafo.items():
    malos = []
    for d in deps:
        if resuelve(d) is None:
            # VDO.x.y -> comprobar fichero
            if d.startswith("VDO."):
                ruta = RAIZ / (d.replace(".", "/") + ".py")
                if ruta.is_file(): continue
            malos.append(d)
    if malos: problemas[f] = sorted(set(malos))
for f, m in sorted(problemas.items()):
    print(f"  {f}")
    for x in m: print(f"      -> {x}")
if not problemas: print("  (ninguno)")

print(); print("="*72); print("ALCANZABLE DESDE InitGui.py"); print("="*72)
def a_ruta(m):
    if m.startswith("VDO."):
        r = RAIZ/(m.replace(".","/")+".py")
        if r.is_file(): return str(r.relative_to(RAIZ))
        r = RAIZ/m.replace(".","/")/"__init__.py"
        if r.is_file(): return str(r.relative_to(RAIZ))
    elif m in mods_raiz: return f"{m}.py"
    return None

alcanz, pend = set(), ["InitGui.py","Init.py"]
while pend:
    f = pend.pop()
    if f in alcanz or f not in grafo: continue
    alcanz.add(f)
    for d in grafo[f]:
        r = a_ruta(d)
        if r: pend.append(r)
print(f"  modulos vivos: {len(alcanz)}")

codigo = {f for f in grafo if not Path(f).name.startswith(("test_","conftest"))}
huerf = sorted(codigo - alcanz)
print(); print("="*72); print(f"NO ALCANZABLES desde el workbench ({len(huerf)})"); print("="*72)
for f in huerf: print(f"  {f}")
if roto:
    print(); print("ARCHIVOS QUE NO COMPILAN:")
    for f,e in roto: print(f"  {f}: {e}")
