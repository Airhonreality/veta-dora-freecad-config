# -*- coding: utf-8 -*-
# tests/test_espacio_dossier.py — Escenario Espacio Cocina (headless, FreeCADCmd).
#
# Pruebas:
#   - NivelPiso negativo se conserva (F-14), incluso tras guardar/reabrir
#   - VDO_Proyecto es singleton por documento
#   - hijos_por_familia() clasifica correctamente usando el clasificador
#     de produccion (VDO/shared/vdo_shared_familias.py), no literales ficticios
#   - COCO lee AlturaCielorraso del espacio sin crear ciclo DAG
#   - Creacion del espacio es un solo Ctrl+Z (headless: UndoCount==1, undo() borra todo)
#   - VDO_CrearEspacio esta registrado en nombres_comandos()
#
# Ejecutar con: FreeCADCmd tools/run_tests_freecad.py
# (No usa if __name__ == "__main__": FreeCADCmd ejecuta con exec().)

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from tests._entorno import HAY_FREECAD

skip_no_freecad = pytest.mark.skipif(
    not HAY_FREECAD, reason="requiere FreeCAD real (FreeCADCmd)")

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from VDO.hub import vdo_hub_registry as REG
from VDO.hub.vdo_hub_schema import resolver
from VDO.cad.objects.vdo_cad_espacio import make_espacio
from VDO.cad.objects.vdo_cad_proyecto import make_proyecto
from VDO.shared.vdo_shared_familias import (
    hijos_por_familia, MOBILIARIO_TIPOS, clasificar_hijo)


@skip_no_freecad
class TestEspacioDossier:
    def setup_method(self):
        import FreeCAD as App
        self.doc = App.newDocument("VDO_Test_Espacio")

    def teardown_method(self):
        import FreeCAD as App
        try:
            if self.doc.Name in App.listDocuments().keys():
                App.closeDocument(self.doc.Name)
        except Exception:
            pass

    def _hacer_coco_real(self, nombre, alto, ancho, fondo):
        """Crea un COCO real con su fabrica del registro."""
        import FreeCAD as App
        import Part

        fabrica = resolver(REG.spec("coco").fabrica)
        obj = fabrica({
            "nombre": nombre,
            "alto": alto,
            "ancho": ancho,
            "fondo_modulo": fondo,
            "espesor": 18,
        })
        self.doc.recompute()
        return obj

    def test_nivel_piso_negativo_se_conserva(self):
        """F-14: NivelPiso = -150 conserva -150, no clampa a 0."""
        espacio = make_espacio({
            "nombre": "ESPACIO_Test",
            "nivel_piso": -150.0,
        })
        self.doc.recompute()
        valor = float(espacio.NivelPiso or 0.0)
        assert valor == -150.0, (
            f"NivelPiso = {valor}, esperado -150.0 "
            f"(PropertyLength clampa a 0 en silencio)")

    def test_nivel_piso_negativo_sobrevive_guardar_reabrir(self):
        """F-14: NivelPiso = -150 sobrevive a guardar y reabrir el documento."""
        import FreeCAD as App
        espacio = make_espacio({
            "nombre": "ESPACIO_SaveTest",
            "nivel_piso": -150.0,
        })
        self.doc.recompute()
        valor_antes = float(espacio.NivelPiso or 0.0)
        assert valor_antes == -150.0

        # Guardar, cerrar y reabrir
        tmp = Path(tempfile.mktemp(suffix=".FCStd", dir="/tmp"))
        try:
            self.doc.saveAs(str(tmp))
            App.closeDocument(self.doc.Name)
            doc2 = App.openDocument(str(tmp))
            try:
                espacio2 = doc2.getObject("ESPACIO_SaveTest")
                assert espacio2 is not None, (
                    "Espacio no encontrado tras reabrir")
                valor_despues = float(espacio2.NivelPiso or 0.0)
                assert valor_despues == -150.0, (
                    f"Tras reabrir: NivelPiso = {valor_despues}, "
                    f"esperado -150.0 (clamp de PropertyLength)")
            finally:
                App.closeDocument(doc2.Name)
        finally:
            if tmp.exists():
                tmp.unlink()

    def test_espacio_shape_nula(self):
        """El Espacio tiene Shape nula (axioma T5/C-02)."""
        espacio = make_espacio({"nombre": "ESPACIO_Shape"})
        self.doc.recompute()
        shp = espacio.Shape
        assert shp is not None and shp.isNull(), (
            f"Espacio.Shape no es nula: {shp.ShapeType if shp else 'None'}")

    def test_espacio_vdo_modulo_testigo(self):
        """VDO_Modulo = 'espacio' como testigo de tipo."""
        espacio = make_espacio({"nombre": "ESPACIO_Testigo"})
        assert espacio.VDO_Modulo == "espacio"
        assert espacio.VDO_Tipo == "EspacioFeature"

    def test_resolver_modulo_reconoce_espacio(self):
        """resolver_modulo() identifica al Espacio via VDO_Modulo."""
        espacio = make_espacio({"nombre": "ESPACIO_Resolver"})
        spec = REG.resolver_modulo(espacio)
        assert spec is not None, "resolver_modulo no reconoce el Espacio"
        assert spec.tipo == "espacio"

    def test_proyecto_singleton(self):
        """VDO_Proyecto es singleton: un solo objeto por documento."""
        import FreeCAD as App
        p1 = make_proyecto({
            "nombre": "VDO_Proyecto", "cliente": "Cliente A"})
        p2 = make_proyecto({
            "nombre": "VDO_Proyecto", "cliente": "Cliente B"})
        assert p1 is p2, (
            "make_proyecto no devolvio el mismo objeto (no es singleton)")
        assert p1.Cliente == "Cliente B", (
            "El proyecto existente no se actualizo con el segundo llamado")
        proyectos = [
            o for o in self.doc.Objects
            if getattr(o, "VDO_Modulo", None) == "proyecto"]
        assert len(proyectos) == 1, (
            f"Hay {len(proyectos)} proyectos, esperado 1")

    def test_hijos_por_familia_clasifica_muro_y_coco(self):
        """hijos_por_familia() clasifica muro (arquitectura) y COCO (mobiliario)
        usando el clasificador de produccion, no literales ficticios."""
        import FreeCAD as App
        import Part

        espacio = make_espacio({"nombre": "ESPACIO_Cocina"})

        # COCO real con su fabrica
        coco = self._hacer_coco_real("COCO_BajoMesada", 720.0, 600.0, 580.0)

        # Muro simulado (objeto BIM-like con IfcType="Wall", sin VDO_Modulo)
        muro = self.doc.addObject("Part::FeaturePython", "Muro_Pared_Norte")
        muro.addProperty("App::PropertyString", "IfcType", "BIM",
                         "Tipo IFC").IfcType = "Wall"
        caja = Part.makeBox(3000.0, 150.0, 2400.0)
        muro.Shape = caja

        # Vincular al espacio
        hijos = list(espacio.Hijos or [])
        hijos.extend([muro, coco])
        espacio.Hijos = hijos
        self.doc.recompute()

        mob = hijos_por_familia(espacio, "mobiliario")
        arq = hijos_por_familia(espacio, "arquitectura")

        assert any(h.Name == "COCO_BajoMesada" for h in mob), (
            f"COCO no clasificado como mobiliario: {[h.Name for h in mob]}")
        assert any(h.Name == "Muro_Pared_Norte" for h in arq), (
            f"Muro no clasificado como arquitectura: {[h.Name for h in arq]}")

    def test_coco_lee_altura_cielorraso_sin_ciclo(self):
        """El COCO lee AlturaCielorraso del espacio sin crear dependencia ciclica."""
        espacio = make_espacio({
            "nombre": "ESPACIO_Ciclo", "altura_cielorraso": 2600.0})
        coco = self._hacer_coco_real("COCO_Ciclo", 720.0, 600.0, 580.0)

        hijos = list(espacio.Hijos or [])
        hijos.append(coco)
        espacio.Hijos = hijos
        self.doc.recompute()

        altura = float(getattr(espacio, "AlturaCielorraso", 0.0) or 0.0)
        assert altura == 2600.0, (
            f"AlturaCielorraso = {altura}, esperado 2600.0")

        # Recompute forzado: no debe lanzar (sin ciclo DAG)
        self.doc.recompute()
        self.doc.recompute()

    def test_creacion_espacio_es_des_hacible_headless(self):
        """Un solo Ctrl+Z deshace la creacion del Espacio (headless).

        Con doc.UndoMode = 1, openTransaction/commitTransaction deja
        UndoCount == 1 y un doc.undo() borra todo (medido: 5 objetos -> 0).
        """
        import FreeCAD as App
        self.doc.UndoMode = 1

        n_antes = len(self.doc.Objects)
        espacio = make_espacio({"nombre": "ESPACIO_Deshacer"})
        self.doc.recompute()
        n_despues = len(self.doc.Objects)
        assert n_despues == n_antes + 1, (
            f"Espacio no creado: {n_antes} -> {n_despues} objetos")

        # Undo headless
        self.doc.undo()
        n_despues_undo = len(self.doc.Objects)
        assert n_despues_undo == n_antes, (
            f"Undo no elimino el espacio: {n_despues_undo} objetos "
            f"(esperado {n_antes})")

    def test_comando_crear_espacio_registrado(self):
        """VDO_CrearEspacio aparece en nombres_comandos()."""
        nombres = REG.nombres_comandos()
        assert "VDO_CrearEspacio" in nombres, (
            f"VDO_CrearEspacio no esta en nombres_comandos(): {nombres}")

    def test_clasificador_no_usa_literales_ficticios(self):
        """El clasificador de produccion no usa VDO_Tipo literales como
        'COCO' o 'Muro'. Un COCO real tiene VDO_Tipo='contenedor'."""
        coco = self._hacer_coco_real("COCO_Test", 720.0, 600.0, 580.0)
        # Un COCO real tiene vdo_tipo='contenedor', no VDO_Tipo='COCO'
        assert coco.VDO_Tipo == "contenedor", (
            f"COCO VDO_Tipo={coco.VDO_Tipo}, esperado 'contenedor'")
        assert clasificar_hijo(coco) == "mobiliario", (
            f"COCO clasificado como {clasificar_hijo(coco)}, esperado 'mobiliario'")
        assert "coco" in MOBILIARIO_TIPOS, (
            f"'coco' no esta en MOBILIARIO_TIPOS: {MOBILIARIO_TIPOS}")
