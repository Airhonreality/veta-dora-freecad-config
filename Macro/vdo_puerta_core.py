# -*- coding: utf-8 -*-
# =====================================================================
# vdo_puerta_core.py
# Capa 2 - PuertaFeature (Part::FeaturePython) con mecanizados booleanos
# y chaflanes para el submódulo de Puertas y Cierres (L2).
# =====================================================================

import FreeCAD as App
import Part

from vdo_facade_contract import (
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    HOLGURA_PERIMETRAL_DEFAULT, SOLAPE_PARCHE_NOMINAL,
    calcular_fachada_base,
)
from vdo_puerta_despiece import (
    bisagras_para_puerta,
    descripcion_piston,
    calcular_corrediza,
    COTA_CAZOLETA_X,
    CAZALETA_PROFUNDIDAD,
    CAZALETA_DIAMETRO,
    necesita_expulsor_magnetico,
    necesita_cantos_45,
    ajuste_altura_apertura,
)

from vdo_module_props import add_common_props


# ---------------------------------------------------------------------
# Utilidades de geometría
# ---------------------------------------------------------------------

def _aristas_en_plano(shape, coord_idx, valor, tol=1e-6):
    """Aristas de ``shape`` cuyos vértices tienen coord_idx == valor."""
    out = []
    for arista in shape.Edges:
        pts = [v.Point for v in arista.Vertexes]
        if all(abs(p[coord_idx] - valor) < tol for p in pts):
            out.append(arista)
    return out


def _arista_borde(shape, coord_fijo, valor_fijo, coord_var, tol=1e-6):
    """Arista donde todos los vértices tienen coord_fijo == valor_fijo."""
    for arista in shape.Edges:
        pts = [v.Point for v in arista.Vertexes]
        if all(abs(p[coord_fijo] - valor_fijo) < tol for p in pts):
            return arista
    return None


def _cilindro_cazoleta(cup_x, cup_z, espesor, radio=None, profundidad=None):
    """Cilindro ciego de cazoleta taladrado desde la cara trasera (Y=espesor)."""
    radio = radio or CAZALETA_DIAMETRO / 2.0
    profundidad = profundidad or CAZALETA_PROFUNDIDAD
    base = App.Vector(cup_x, espesor - profundidad, cup_z)
    direccion = App.Vector(0.0, 1.0, 0.0)
    return Part.makeCylinder(radio, profundidad, base, direccion)


# ---------------------------------------------------------------------
# FeaturePython
# ---------------------------------------------------------------------

class PuertaFeature:
    """Proxy de PuertaFeature para Part::FeaturePython."""

    def __init__(self, obj):
        obj.addProperty("App::PropertyEnumeration", "TipoSistema", "Sistema",
                        "Tipo de sistema de puerta").TipoSistema = [
            "Batiente Vertical", "Basculante Horizontal", "Corrediza"]
        obj.addProperty("App::PropertyEnumeration", "TipoMontaje", "Montaje",
                        "Tipo de montaje (batiente)").TipoMontaje = [
            "Parche", "Semiparche", "Embebida"]
        obj.addProperty("App::PropertyEnumeration", "SentidoApertura",
                        "Apertura", "Sentido de apertura").SentidoApertura = [
            "Izquierda", "Derecha", "Doble",
            "Hacia Arriba", "Hacia Abajo", "2 hojas", "3 hojas"]
        obj.addProperty("App::PropertyEnumeration", "SistemaApertura",
                        "Sistema de Apertura", "Sistema de apertura/fachada").SistemaApertura = [
            APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN]
        obj.addProperty("App::PropertyString", "HardwareSKU", "Herraje",
                        "SKU comercial del herraje activo").HardwareSKU = ""
        obj.addProperty("App::PropertyString", "VDO_Vano_ID", "Vinculación",
                        "Identificador del vano vinculado (ej. '(x1,y1)')").VDO_Vano_ID = ""
        obj.addProperty("App::PropertyString", "FuerzaPistonRecomendada",
                        "Físico", "Fuerza de pistón recomendada (solo lectura)").FuerzaPistonRecomendada = ""

        # Geometría
        obj.addProperty("App::PropertyLength", "Ancho", "Dimensiones",
                        "Ancho de la puerta (mm)").Ancho = 400.0
        obj.addProperty("App::PropertyLength", "Alto", "Dimensiones",
                        "Alto de la puerta (mm)").Alto = 700.0
        obj.addProperty("App::PropertyInteger", "Espesor", "Dimensiones",
                        "Espesor del panel (mm)").Espesor = 18
        obj.addProperty("App::PropertyLength", "PosX", "Posición",
                        "Posición X de la puerta (mm)").PosX = 0.0
        obj.addProperty("App::PropertyLength", "PosY", "Posición",
                        "Posición Y de la puerta (mm)").PosY = 0.0
        obj.addProperty("App::PropertyLength", "PosZ", "Posición",
                        "Posición Z de la puerta (mm)").PosZ = 0.0

        # VDO comunes
        add_common_props(obj)

        # Vínculo padre-hijo (kinematics de Placement)
        obj.addProperty("App::PropertyLink", "ParentCOCO", "VDO",
                        "Módulo COCO padre")
        obj.addProperty("App::PropertyPlacement", "LocalPlacement", "VDO",
                        "Pose relativa al vano del COCO").LocalPlacement = App.Placement()

        obj.Proxy = self

    def execute(self, fp):
        """Reconstruir la geometría de la puerta."""
        import json

        try:
            sistema = str(fp.TipoSistema)
            montaje = str(fp.TipoMontaje)
            sentido = str(fp.SentidoApertura)
            apertura = str(fp.SistemaApertura)

            W = float(fp.Ancho)
            H = float(fp.Alto)
            t = float(fp.Espesor)
            px = float(fp.PosX)
            py = float(fp.PosY)
            pz = float(fp.PosZ)

            if W <= 0 or H <= 0 or t <= 0:
                fp.Shape = Part.Shape()
                return

            # Fuerza de pistón (basculante)
            if sistema == "Basculante Horizontal":
                texto, comercial, F = descripcion_piston(W, H)
                fp.FuerzaPistonRecomendada = texto
            else:
                fp.FuerzaPistonRecomendada = ""

            # -------------------- Batiente / Basculante --------------------
            if sistema in ("Batiente Vertical", "Basculante Horizontal"):

                # Dimensiones de fachada segun montaje (solape para parche)
                if montaje == MONTAJE_PARCHE:
                    w_fach, h_fach = calcular_fachada_base(
                        W, H, montaje,
                        holgura=HOLGURA_PERIMETRAL_DEFAULT,
                        solape=SOLAPE_PARCHE_NOMINAL)
                    # Centrar la fachada sobre el hueco del vano
                    px = px - (w_fach - W) / 2.0
                    pz = pz - (h_fach - H) / 2.0
                    # Panel apoyado en el plano exterior de la carcasa (Y=-t)
                    py = py - t
                else:
                    w_fach, h_fach = W, H

                # Ajuste de altura por sistema de apertura (gola)
                H_efectiva, _descuento = ajuste_altura_apertura(apertura, h_fach)

                shape = Part.makeBox(w_fach, t, H_efectiva)

                # Chaflán 45° en el canto de agarre (borde superior delantero)
                if necesita_cantos_45(apertura):
                    arista = _arista_borde(shape, 2, H_efectiva, 0)
                    if arista is None:
                        arista = _arista_borde(shape, 2, H_efectiva, 1)
                    if arista is not None:
                        try:
                            shape = shape.makeChamfer(3.0, 3.0, [arista])
                        except Exception:
                            shape = shape.makeChamfer(3.0, [arista])

                # Cazoletas de bisagra (solo batiente)
                if sistema == "Batiente Vertical":
                    bis = bisagras_para_puerta(h_fach, montaje,
                                               prefer_sku=fp.HardwareSKU or None)
                    radio = bis["diametro_cazoleta"] / 2.0
                    prof = bis["profundidad_cazoleta"]
                    cota_x = bis["cota_x"]

                    if sentido == "Izquierda":
                        cup_xs = [cota_x]
                    elif sentido == "Derecha":
                        cup_xs = [w_fach - cota_x]
                    elif sentido == "Doble":
                        cup_xs = [cota_x, w_fach - cota_x]
                    else:
                        cup_xs = [cota_x]

                    for cup_z in bis["posiciones_z"]:
                        for cup_x in cup_xs:
                            if 0 < cup_x < w_fach and 0 < cup_z < h_fach:
                                cyl = _cilindro_cazoleta(cup_x, cup_z, t,
                                                         radio, prof)
                                shape = shape.cut(cyl)

                solidos = [s for s in ([shape] if shape is not None else [])
                           if not s.isNull() and s.Volume > 1e-9]
                fp.Shape = Part.makeCompound(solidos) if solidos else Part.Shape()
                # LocalPlacement: geometría ya está en origen local (0,0,0).
                # La posición relativa al vano del COCO se guarda aquí y
                # se combina con ParentCOCO al final de execute().
                fp.LocalPlacement = App.Placement(
                    App.Vector(px, py, pz), App.Rotation())

            # -------------------- Corrediza --------------------
            elif sistema == "Corrediza":
                n_hojas = 3 if sentido == "Doble" else 2
                tipo_mueble = "closet"
                res = calcular_corrediza(W, H, tipo_mueble=tipo_mueble,
                                         n_hojas=n_hojas,
                                         prefer_sku=fp.HardwareSKU or None)
                w_hoja = float(res["ancho_hoja"])
                h_hoja = float(res["alto_hoja"])
                traslape = float(res["traslape_minimo"])

                # Paso en profundidad según el riel del catálogo
                tecnicos = res.get("parametros_tecnicos", {})
                paso_y = float(tecnicos.get("ancho_piso_riel_doble", t + 4.0))
                if paso_y <= 0:
                    paso_y = t + 4.0

                hojas = []
                for i in range(n_hojas):
                    hoja = Part.makeBox(w_hoja, t, h_hoja)
                    # Desfasar en X con traslape y en Y con el paso del riel
                    x_i = i * (w_hoja - traslape)
                    y_i = i * paso_y
                    hoja.Placement = App.Placement(
                        App.Vector(x_i, y_i, 0), App.Rotation())
                    hojas.append(hoja.transformShape(hoja.Placement.toMatrix()))

                # Chaflán 45° si aplica (solo en la hoja delantera)
                if necesita_cantos_45(apertura) and hojas:
                    arista = _arista_borde(hojas[0], 2, h_hoja, 0)
                    if arista is not None:
                        try:
                            hojas[0] = hojas[0].makeChamfer(3.0, 3.0, [arista])
                        except Exception:
                            hojas[0] = hojas[0].makeChamfer(3.0, [arista])

                # Validar que no haya intersección de volúmenes (common == 0)
                for a in range(len(hojas)):
                    for b in range(a + 1, len(hojas)):
                        if hojas[a].common(hojas[b]).Volume > 1e-6:
                            App.Console.PrintWarning(
                                f"[VDO Puerta] Hojas {a+1} y {b+1} se "
                                f"intersectan (common > 0).\n")

                solidos = [h for h in hojas if not h.isNull() and h.Volume > 1e-9]
                fp.Shape = Part.makeCompound(solidos) if solidos else Part.Shape()
                fp.LocalPlacement = App.Placement(
                    App.Vector(px, py, pz), App.Rotation())
                fp.FuerzaPistonRecomendada = ""

            else:
                fp.Shape = Part.Shape()

            # --- Vínculo rígido padre-hijo ---
            # No escribir fp.Placement aquí: solo CocoFeature.execute() es
            # la fuente de verdad del placement mundial del hijo.
            # LocalPlacement almacena la pose relativa al vano del COCO.

        except Exception as e:
            App.Console.PrintError(f"[VDO Puerta] Error en execute(): {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            fp.Shape = Part.Shape()


# ---------------------------------------------------------------------
# ViewProvider
# ---------------------------------------------------------------------

from vdo_view_base import VDOViewProviderBase


class ViewProviderPuerta(VDOViewProviderBase):
    MENU_LABEL = "Propiedades de la Puerta"
    ICON = "vdo_puerta.svg"

    def get_panel_class(self):
        from vdo_puerta_task import PuertaTaskPanel
        return PuertaTaskPanel


def make_puerta(configuracion):
    """Crea un PuertaFeature en el documento activo."""
    doc = App.ActiveDocument
    if doc is None:
        App.Console.PrintError("[VDO Puerta] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "Puerta")
    obj = doc.addObject("Part::FeaturePython", nombre)
    PuertaFeature(obj)

    if App.GuiUp:
        ViewProviderPuerta(obj.ViewObject)

    obj.TipoSistema = configuracion.get("tipo_sistema", "Batiente Vertical")
    obj.TipoMontaje = configuracion.get("tipo_montaje", "Parche")
    obj.SentidoApertura = configuracion.get("sentido_apertura", "Izquierda")
    obj.SistemaApertura = configuracion.get("sistema_apertura",
                                            APERTURA_TIRADOR)
    obj.HardwareSKU = configuracion.get("hardware_sku", "")
    obj.VDO_Vano_ID = configuracion.get("vdo_vano_id", "")
    obj.Ancho = configuracion.get("ancho", 400.0)
    obj.Alto = configuracion.get("alto", 700.0)
    obj.Espesor = configuracion.get("espesor", 18)
    obj.PosX = configuracion.get("pos_x", 0.0)
    obj.PosY = configuracion.get("pos_y", 0.0)
    obj.PosZ = configuracion.get("pos_z", 0.0)
    obj.VDO_Anclaje = configuracion.get(
        "anclaje", "inferior_izquierda_frente")

    # Vínculo padre-hijo: LocalPlacement y ParentCOCO se establecen aquí.
    # La geometría interna se construye en origen local (0,0,0) dentro de
    # execute(); LocalPlacement lleva la posición relativa al vano del COCO.
    local_placement = configuracion.get("local_placement")
    if local_placement is not None:
        obj.LocalPlacement = local_placement
    parent_coco = configuracion.get("parent_coco")
    if parent_coco is not None:
        obj.ParentCOCO = parent_coco

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO Puerta] '{nombre}' creado con FeaturePython.\n")
    return obj


__all__ = ["PuertaFeature", "ViewProviderPuerta", "make_puerta"]
