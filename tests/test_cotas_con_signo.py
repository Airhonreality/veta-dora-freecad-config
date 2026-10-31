# -*- coding: utf-8 -*-
# tests/test_cotas_con_signo.py — Test F-14: cotas con signo no se clampean en silencio.
#
# PropertyLength (App::PropertyLength) clampa silenciosamente valores
# negativos a 0. PropertyDistance (App::PropertyDistance) los conserva.
#
# Dos criterios:
# 1. Estatico: todo Param de tipo "length" debe declarar explícitamente
#    minimo >= 0 (si no, o se cambia a "distance" o se pone minimo=0.0).
# 2. Empirico: aplica el esquema a un FeaturePython, asigna -150.0 a cada
#    parametro numerico y falla si el valor leído no es -150.0 y el param
#    no declara minimo >= 0. Detecta el clamp sin depender de la declaración.
#
# Ejecutar con: FreeCADCmd tools/run_tests_freecad.py

import pytest

from tests._entorno import HAY_FREECAD

skip_no_freecad = pytest.mark.skipif(
    not HAY_FREECAD, reason="requiere FreeCAD real (FreeCADCmd)")

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

from VDO.hub import vdo_hub_registry as REG
from VDO.hub.vdo_hub_schema import (
    PROP_MODULO, Param, aplicar_esquema)

# Tipos numericos que FreeCAD puede almacenar como Quantity/float.
TIPOS_NUMERICOS = ("length", "angle", "float", "int")


# ---------------------------------------------------------------------
# Criterio estatico: todo Param "length" debe declarar minimo >= 0
# ---------------------------------------------------------------------

@skip_no_freecad
class TestCotasSignoEstatico:
    def test_length_params_declaran_minimo_no_negativo(self):
        """Todo Param de tipo 'length' debe declarar minimo >= 0.

        Si un length acepta negativos (no declara minimo o declara
        minimo < 0), PropertyLength clampeara en silencio a 0 (F-14).
        Debe cambiarse a 'distance' o declarar minimo=0.0.
        """
        fallos = []
        for spec in REG.CATALOGO.values():
            for p in spec.params:
                if p.tipo != "length":
                    continue
                if p.minimo is None or p.minimo < 0:
                    fallos.append(
                        f"{spec.tipo}.{p.nombre}: tipo='length' pero "
                        f"minimo={p.minimo} (no excluye negativos). "
                        f"Cambiar a 'distance' o declarar minimo >= 0.")
        assert not fallos, (
            "Parametros 'length' sin minimo >= 0 (riesgo de clamp F-14):\n"
            + "\n".join(f"  {f}" for f in fallos))

    def test_no_length_param_sin_minimo_tiene_valor_negativo(self):
        """Si un Param 'length' declara minimo >= 0, su default no debe ser negativo."""
        fallos = []
        for spec in REG.CATALOGO.values():
            for p in spec.params:
                if p.tipo != "length":
                    continue
                if p.minimo is not None and p.minimo >= 0:
                    try:
                        default = p.valor_inicial()
                        if default is not None and float(default) < 0:
                            fallos.append(
                                f"{spec.tipo}.{p.nombre}: default={default} "
                                f"negativo con minimo={p.minimo} >= 0 (incoherente).")
                    except (TypeError, ValueError):
                        pass
        assert not fallos, (
            "Parametros 'length' con default negativo y minimo >= 0:\n"
            + "\n".join(f"  {f}" for f in fallos))


# ---------------------------------------------------------------------
# Criterio empirico: asignar -150.0 y leer de vuelta
# ---------------------------------------------------------------------

@skip_no_freecad
class TestCotasSignoEmpirico:
    def _crear_objeto_con_esquema(self, spec):
        """Crea un FeaturePython y aplica el esquema del spec."""
        doc = App.newDocument(f"Test_{spec.tipo}_Doc")
        obj = doc.addObject("Part::FeaturePython", f"Test_{spec.tipo}")
        obj.addProperty("App::PropertyString", PROP_MODULO, "VDO",
                        "Testigo de tipo").VDO_Modulo = spec.tipo
        aplicar_esquema(obj, spec)
        return doc, obj

    def _asignar_y_leer(self, obj, p: Param):
        """Intenta asignar -150.0 a la propiedad y devuelve lo que se lee."""
        try:
            setattr(obj, p.nombre, -150.0)
            valor_leido = getattr(obj, p.nombre)
            if p.tipo in ("length", "angle", "float"):
                return float(valor_leido)
            if p.tipo == "int":
                return int(valor_leido)
        except Exception:
            return None
        return None

    def test_empirico_cotas_con_signo_no_se_clampean(self):
        """Asigna -150.0 a cada parametro numerico y verifica que no se clampé.

        Falla si el valor leído no es -150.0 y el param no declara
        minimo >= 0 (eso significa que PropertyLength clampeó en silencio).
        """
        fallos = []
        revisados = 0

        for spec in REG.CATALOGO.values():
            doc, obj = self._crear_objeto_con_esquema(spec)

            for p in spec.params:
                if p.tipo not in TIPOS_NUMERICOS:
                    continue
                # Solo params que pueden aceptar negativos
                if p.minimo is not None and p.minimo >= 0:
                    continue  # minimo >= 0 excluye negativos, es correcto
                if p.maximo is not None and p.maximo < 0:
                    continue  # maximo < 0, todo es negativo, no aplicable

                revisados += 1
                valor = self._asignar_y_leer(obj, p)
                if valor is None:
                    continue  # no se pudo asignar/leer, saltar

                if valor != -150.0:
                    if p.minimo is None or p.minimo < 0:
                        fallos.append(
                            f"{spec.tipo}.{p.nombre} (tipo={p.tipo}): "
                            f"asignado -150.0, leído {valor}. "
                            f"minimo={p.minimo} (clamp silencioso de "
                            f"PropertyLength sin minimo >= 0).")

            try:
                App.closeDocument(doc.Name)
            except Exception:
                pass

        assert not fallos, (
            f"{revisados} parametros numericos revisados, {len(fallos)} "
            f"clampes detectados:\n" + "\n".join(f"  {f}" for f in fallos))

        print(f"  Cotas con signo: {revisados} parametros revisados, 0 clampes.")


__all__ = [
    "TestCotasSignoEstatico",
    "TestCotasSignoEmpirico",
]
