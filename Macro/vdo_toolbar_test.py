#!/usr/bin/env python3
"""
Test mínimo: registrar comandos + toolbar en FreeCAD desde Python.
Uso: freecadcmd vdo_toolbar_test.py
"""
import sys
import os

macro_dir = os.path.expanduser("~/.local/share/FreeCAD/Macro")
if macro_dir not in sys.path:
    sys.path.insert(0, macro_dir)

try:
    import FreeCAD
    import FreeCADGui as Gui
except ImportError:
    print("ERROR: No se pudo importar FreeCAD. Ejecutar con freecadcmd o freecad.")
    sys.exit(1)

# Verificar que tenemos GUI disponible
if not hasattr(FreeCAD, 'GuiUp') or not FreeCAD.GuiUp:
    print("ERROR: FreeCAD no tiene GUI activa. Ejecutar con 'freecad' (no freecadcmd).")
    sys.exit(1)

print("[TEST] FreeCAD version:", FreeCAD.Version())
print("[TEST] Macro dir:", macro_dir)

# ============================================================
# 1. Definir acciones (comandos)
# ============================================================

class TestCmd1:
    """Crea una caja de prueba."""
    def Activated(self):
        doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Test")
        obj = doc.addObject("Part::Box", "CajaTest")
        obj.Length = 100.0
        obj.Width = 50.0
        obj.Height = 30.0
        doc.recompute()
        FreeCAD.Console.PrintMessage("[VDO] Caja creada: 100x50x30\n")

    def GetResources(self):
        return {
            "Pixmap": "Part_Box",
            "MenuText": "Crear Caja",
            "ToolTip": "Crea una caja de prueba 100x50x30"
        }

    def IsActive(self):
        return True


class TestCmd2:
    """Crea una esfera de prueba."""
    def Activated(self):
        doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Test")
        obj = doc.addObject("Part::Sphere", "EsferaTest")
        obj.Radius = 25.0
        doc.recompute()
        FreeCAD.Console.PrintMessage("[VDO] Esfera creada: radio 25\n")

    def GetResources(self):
        return {
            "Pixmap": "Part_Sphere",
            "MenuText": "Crear Esfera",
            "ToolTip": "Crea una esfera de prueba"
        }

    def IsActive(self):
        return True


class TestCmd3:
    """Imprime mensaje de prueba."""
    def Activated(self):
        FreeCAD.Console.PrintMessage("[VDO] ¡Toolbar VDO funcionando correctamente!\n")

    def GetResources(self):
        return {
            "Pixmap": "Macro-python",
            "MenuText": "Test VDO",
            "ToolTip": "Verifica que la toolbar funciona"
        }

    def IsActive(self):
        return True


# ============================================================
# 2. Registrar comandos
# ============================================================

print("[TEST] Registrando comandos...")

Gui.addCommand("VDO_Test_Caja", TestCmd1())
Gui.addCommand("VDO_Test_Esfera", TestCmd2())
Gui.addCommand("VDO_Test_Mensaje", TestCmd3())

for cmd in ["VDO_Test_Caja", "VDO_Test_Esfera", "VDO_Test_Mensaje"]:
    c = Gui.Command.get(cmd)
    if c:
        print(f"  ✓ {cmd} registrado OK")
    else:
        print(f"  ✗ {cmd} FALLÓ")

# ============================================================
# 3. Crear toolbar con workbench mínimo
# ============================================================

print("[TEST] Creando workbench...")

class VDOTestWorkbench(Gui.Workbench):
    MenuText = "VDO Test"
    ToolTip = "Test de toolbar VDO"

    def Initialize(self):
        cmds = ["VDO_Test_Caja", "VDO_Test_Esfera", "VDO_Test_Mensaje"]
        self.appendToolbar("VDO Test", cmds)
        print("[TEST] Toolbar 'VDO Test' creada con", len(cmds), "botones")

    def Activated(self):
        print("[TEST] VDO Test workbench activado")

    def Deactivated(self):
        print("[TEST] VDO Test workbench desactivado")

    def GetClassName(self):
        return "Gui::PythonWorkbench"


    Gui.addWorkbench(VDOTestWorkbench())
print("[TEST] Workbench registrado")

# Activar el workbench (FreeCAD usa el nombre de la CLASE, no MenuText)
try:
    Gui.activateWorkbench("VDOTestWorkbench")
    print("[TEST] Workbench activado - toolbar debería ser visible")
except Exception as e:
    print(f"[TEST] Error activando workbench: {e}")

print("")
print("=" * 50)
print("TEST COMPLETADO")
print("=" * 50)
print("Si no ves la toolbar 'VDO Test':")
print("  1. Reinicia FreeCAD")
print("  2. Selecciona 'VDO Test' en el selector de workbenches")
print("  3. Aparecerán 3 botones: Caja, Esfera, Test")
print("=" * 50)
