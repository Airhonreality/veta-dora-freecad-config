# -*- coding: utf-8 -*-
# =====================================================================
# vdo_puerta_core.py
# Capa 2 - PuertaFeature (Part::FeaturePython) con mecanizados booleanos
# y chaflanes para el submódulo de Puertas y Cierres (L2).
# =====================================================================

import FreeCAD as App
import Part

from VDO.hub.vdo_hub_registry import SPEC_PUERTA
from VDO.hub.vdo_hub_schema import aplicar_esquema, aplicar_config

# Los dominios de enum (APERTURA_*, MONTAJE_SEMIPARCHE/EMBEBIDA) ya no se
# importan aquí: los declara SPEC_PUERTA. Queda lo que execute() usa de
# verdad para calcular.
from VDO.core.vdo_math_facade import (
    MONTAJE_PARCHE,
    HOLGURA_PERIMETRAL_DEFAULT, SOLAPE_PARCHE_NOMINAL,
    calcular_fachada_base,
    calcular_fachada_desde_deltas, calcular_origen_fachada_local,
)
from VDO.core.vdo_math_puerta import (
    bisagras_para_puerta,
    descripcion_piston,
    calcular_corrediza,
    COTA_CAZOLETA_X,
    CAZALETA_PROFUNDIDAD,
    CAZALETA_DIAMETRO,
    necesita_expulsor_magnetico,
    necesita_cantos_45,
    ajuste_altura_apertura,
    DELTA_PARCHE_TOTAL,
)

# add_common_props() y add_parent_link() ya no se llaman aquí: sus
# propiedades forman parte de SPEC_PUERTA y las aplica aplicar_esquema().
from VDO.hub.vdo_hub_module_props import migrar_parent_link


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
        # Las 18 propiedades de la puerta las declara SPEC_PUERTA.
        #
        # Cuatro de ellas son NUEVAS y cierran un bug real: la puerta era
        # el unico modulo que no declaraba VDO_Tipo, y tanto
        # vdo_cam_cutlist.extraer_piezas_del_documento() como
        # vdo_cam_nesting_workflow filtran por hasattr(obj, "VDO_Tipo").
        # Resultado: toda puerta quedaba fuera de la lista de corte y del
        # nesting sin que nada avisara. Una hoja de puerta es un tablero
        # de melamina: tiene que llegar a fabricacion.
        aplicar_esquema(obj, SPEC_PUERTA)
        obj.Proxy = self

    def onDocumentRestored(self, fp):
        """Migraciones: esquema al dia + ParentCOCO fuera del grafo."""
        aplicar_esquema(fp, SPEC_PUERTA)
        migrar_parent_link(fp)

    def onDelete(self, fp, subelements):
        """Axioma T6: al borrar la puerta, salir de la lista Hijos del padre.

        Si no se hace, ParentCOCO.Hijos arrastra un puntero muerto y el COCO
        marca error en el siguiente recompute.
        """
        try:
            padre = getattr(fp, "ParentCOCO", None)
            if padre is not None and hasattr(padre, "Hijos"):
                padre.Hijos = [h for h in (padre.Hijos or [])
                               if h is not None and h.Name != fp.Name]
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo desregistrar la puerta del padre: {exc}\n")
        return True

    # -----------------------------------------------------------------
    def _publicar_despiece(self, fp, espesor):
        """Escribe el despiece de las hojas en VDO_Paneles_JSON.

        Se deriva de los solidos ya construidos en lugar de recalcularlo
        rama a rama: asi vale igual para batiente (una hoja con solape de
        parche), basculante y corrediza (N hojas), y no se desincroniza
        de la geometria que realmente se ha generado.
        """
        import json

        piezas = []
        try:
            solidos = list(getattr(fp.Shape, "Solids", []) or [])
        except Exception:
            solidos = []

        for indice, solido in enumerate(solidos, start=1):
            bb = solido.BoundBox
            if not bb.isValid():
                continue
            # De las tres medidas de la caja, la menor es el espesor del
            # tablero y las otras dos el largo y el ancho de corte.
            medidas = sorted(
                (bb.XLength, bb.YLength, bb.ZLength), reverse=True)
            largo, ancho, esp = medidas
            if largo <= 0 or ancho <= 0:
                continue
            sufijo = f"_{indice}" if len(solidos) > 1 else ""
            piezas.append({
                "nombre": f"{fp.Label}_Hoja{sufijo}",
                "tipo": "panel",
                "rol": "fachada",
                "orientacion": "vertical",
                "largo": round(float(largo), 2),
                "ancho": round(float(ancho), 2),
                "espesor": round(float(esp or espesor), 2),
                "cantidad": 1,
                "material_ref": getattr(
                    fp, "VDO_Material_Ref", "melamina_standar"),
                # Una hoja de puerta queda vista por sus cuatro bordes.
                "cantos": {"norte": "RIG", "sur": "RIG",
                           "este": "RIG", "oeste": "RIG"},
                "grupo": fp.Label,
                "operacion": "Cantear por separado",
            })

        fp.VDO_Paneles_JSON = json.dumps(piezas, ensure_ascii=False)
        if piezas:
            fp.VDO_ResumenDespiece = "\n".join(
                f"{z['nombre']}: {z['largo']:.1f} × {z['ancho']:.1f} × "
                f"{z['espesor']:.0f} mm" for z in piezas)
        else:
            fp.VDO_ResumenDespiece = "Puerta sin geometría válida."


    def execute(self, fp):
        """Reconstruir la geometría de la puerta."""
        import json

        try:
            sistema = str(fp.TipoSistema)
            montaje = str(fp.TipoMontaje).strip().lower()
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
                self._publicar_despiece(fp, t)
                return

            # Fuerza de pistón (basculante)
            if sistema == "Basculante Horizontal":
                texto, comercial, F = descripcion_piston(W, H)
                fp.FuerzaPistonRecomendada = texto
            else:
                fp.FuerzaPistonRecomendada = ""

            # -------------------- Batiente / Basculante --------------------
            if sistema in ("Batiente Vertical", "Basculante Horizontal"):

                # --- Dimensiones y posicion de la fachada ---
                # Concepto 1: si el objeto lleva VDO_Deltas_JSON, se usa el
                # contrato de deltas netos (alto incluido: gola = norte <0).
                # De lo contrario, se conserva el camino legacy
                # (calcular_fachada_base + centrado simétrico).
                deltas = None
                try:
                    deltas_raw = getattr(fp, "VDO_Deltas_JSON", "") or "{}"
                    deltas = json.loads(deltas_raw) if isinstance(deltas_raw, str) else {}
                except (ValueError, TypeError):
                    deltas = {}

                # Sin vector propio, una fachada inferior hereda Δ_S del COCO
                # padre (H_zocalo − luz_suelo). Un vector local manda.
                if not deltas:
                    deltas = _deltas_heredados_si_inferior(
                        fp, montaje, pz, H, apertura) or {}

                if deltas:
                    w_fach, h_fach = calcular_fachada_desde_deltas(
                        W, H, deltas)
                    px, pz = calcular_origen_fachada_local(px, pz, deltas)
                    # Panel apoyado en el plano exterior de la carcasa (Y=-t)
                    py = py - t
                    # La altura ya incorpora el descuento de gola via
                    # deltas["norte"]; aplicar_sistema_apertura solo aporta
                    # la operacion de canto, no modifica la altura.
                    H_efectiva = h_fach
                else:
                    # Camino legacy: montaje parche/semiparche/embebida con
                    # holgura/solape y centrado simetrico sobre el vano.
                    if montaje == MONTAJE_PARCHE:
                        w_fach, h_fach = calcular_fachada_base(
                            W, H, montaje,
                            holgura=HOLGURA_PERIMETRAL_DEFAULT,
                            solape=SOLAPE_PARCHE_NOMINAL)
                        # Centrar la fachada sobre el hueco del vano
                        px = px - (w_fach - W) / 2.0
                        pz = pz - (h_fach - H) / 2.0
                    else:
                        w_fach, h_fach = W, H
                    # Panel apoyado en el plano exterior de la carcasa (Y=-t)
                    py = py - t
                    # Ajuste de altura por sistema de apertura (gola legacy)
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

            # La hoja es un tablero de melamina y tiene que llegar a la
            # lista de corte. Sin esto la puerta seguiría siendo invisible
            # para fabricación aunque ya declare VDO_Tipo.
            self._publicar_despiece(fp, t)

        except Exception as e:
            App.Console.PrintError(f"[VDO Puerta] Error en execute(): {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            fp.Shape = Part.Shape()
            try:
                self._publicar_despiece(fp, 0.0)
            except Exception:
                pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


# ---------------------------------------------------------------------
# ViewProvider
# ---------------------------------------------------------------------

from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase


class ViewProviderPuerta(VDOViewProviderBase):
    MENU_LABEL = "Propiedades de la Puerta"
    ICON = "vdo_puerta.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_puerta_task import PuertaTaskPanel
        return PuertaTaskPanel


def _deltas_heredados_si_inferior(fp, montaje, pz, H, apertura):
    """Vector de deltas heredado del COCO padre, o None si no aplica.

    Aplica cuando hay ParentCOCO y el vano arranca en el nivel superior del
    zócalo o por debajo (fachada inferior). El descuento de gola se conserva
    en `norte`, porque la rama de deltas no vuelve a aplicar la apertura.
    """
    from VDO.cad.objects.vdo_cad_coco import altura_zocalo_de, luz_suelo_de
    from VDO.core.vdo_math_facade import deltas_heredados_inferior
    padre = getattr(fp, "ParentCOCO", None)
    if padre is None or not hasattr(padre, "Alto"):
        return None
    h_zocalo = altura_zocalo_de(padre)
    if float(pz) > h_zocalo + 1e-6:
        return None
    descuento = max(0.0, float(H) - ajuste_altura_apertura(apertura, H)[0])
    return deltas_heredados_inferior(
        montaje, h_zocalo, luz_suelo_de(padre), norte=-descuento)


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

    aplicar_config(obj, SPEC_PUERTA, configuracion)

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
