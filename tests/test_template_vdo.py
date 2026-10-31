# -*- coding: utf-8 -*-
# tests/test_template_vdo.py — Test TPL-11: integridad de claves freecad:editable.
#
# Requisitos:
# 1. set(tpl.EditableTexts) == {"vdo_proyecto","vdo_cliente","vdo_espacio",
#    "vdo_lamina","vdo_npt","vdo_escala"} (igualdad exacta, sin '' ni claves extra)
# 2. tpl.Width == 420 y tpl.Height == 297
# 3. El JSON de área útil concuerda con el SVG (misma caja de cajetín y márgenes)
# 4. Round-trip de escritura por reasignación completa del dict (TPL-09)
#
# Nota: un test que solo parsee el XML buscando freecad:editable NO habría
# detectado el bug del <tspan> faltante. Este test pasa por FreeCAD.
#
# Ejecutar con: FreeCADCmd tools/run_tests_freecad.py

import json
from pathlib import Path

import pytest

from tests._entorno import HAY_FREECAD

skip_no_freecad = pytest.mark.skipif(
    not HAY_FREECAD, reason="requiere FreeCAD real (FreeCADCmd)")

_RAIZ = Path(__file__).resolve().parent.parent
SVG_PATH = _RAIZ / "VDO" / "resources" / "templates" / "vdo_template_a3.svg"
JSON_PATH = _RAIZ / "VDO" / "resources" / "templates" / "vdo_template_a3.json"

CLAVE_ESPERADAS = {
    "vdo_proyecto", "vdo_cliente", "vdo_espacio",
    "vdo_lamina", "vdo_npt", "vdo_escala",
}


@skip_no_freecad
class TestTemplateVDO:
    def setup_method(self):
        import FreeCAD as App
        self.doc = App.newDocument("TestTemplateVDO")

    def teardown_method(self):
        import FreeCAD as App
        App.closeDocument(self.doc.Name)

    def _crear_tpl(self):
        import FreeCAD as App
        tpl = self.doc.addObject("TechDraw::DrawSVGTemplate", "Tpl")
        tpl.Template = str(SVG_PATH)
        self.doc.recompute()
        return tpl

    def test_claves_editable_exactas(self):
        """TPL-11: el conjunto de claves freecad:editable es exactamente el
        contractual, sin claves vacías ni de sobra."""
        import FreeCAD as App
        tpl = self._crear_tpl()
        claves = set(tpl.EditableTexts)
        assert claves == CLAVE_ESPERADAS, (
            f"Claves inesperadas: {claves - CLAVE_ESPERADAS}, "
            f"faltantes: {CLAVE_ESPERADAS - claves}")
        assert "" not in claves, "Hay claves vacías en EditableTexts"

    def test_dimensiones_hoja(self):
        """tpl.Width == 420 mm, tpl.Height == 297 mm (A3 horizontal)."""
        tpl = self._crear_tpl()
        assert tpl.Width == 420.0, f"tpl.Width={tpl.Width}, esperado 420.0"
        assert tpl.Height == 297.0, f"tpl.Height={tpl.Height}, esperado 297.0"

    def test_json_area_util_concordante(self):
        """El JSON de área útil concuerda con el SVG (cajetín y márgenes)."""
        tpl = self._crear_tpl()
        with JSON_PATH.open("r", encoding="utf-8") as f:
            datos = json.load(f)
        assert datos["hoja"]["ancho"] == tpl.Width
        assert datos["hoja"]["alto"] == tpl.Height
        assert datos["margen"] == 10
        cajetin = datos["cajetin"]
        assert cajetin["x"] == 290 and cajetin["y"] == 247
        assert cajetin["w"] == 120 and cajetin["h"] == 40
        util = datos["util"]
        assert util["x0"] == 10 and util["y0"] == 10
        assert util["x1"] == 290 and util["y1"] == 247
        assert set(datos["claves_editable"]) == CLAVE_ESPERADAS

    def test_redescritura_dict_completo(self):
        """TPL-09: escritura por reasignación completa del dict EditableTexts.
        La mutación in situ se ignora; solo funciona reasignando el dict entero."""
        import FreeCAD as App
        tpl = self._crear_tpl()

        # Leer dict completo
        datos = dict(tpl.EditableTexts)

        # Mutar copia (no afecta al original)
        datos_copia = dict(datos)
        datos_copia["vdo_proyecto"] = "Nuevo Proyecto"

        # Reasignar dict completo (patrón canónico TechDraw)
        tpl.EditableTexts = datos_copia
        self.doc.recompute()

        # Verificar que el cambio se aplicó
        assert tpl.EditableTexts["vdo_proyecto"] == "Nuevo Proyecto"

        # Verificar que las demás claves se conservaron
        for clave in CLAVE_ESPERADAS - {"vdo_proyecto"}:
            assert clave in tpl.EditableTexts
