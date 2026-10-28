# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_spaces.py
# Motor de geometría para divisiones internas del COCO
# Convierte la resolución de vanos v2 en shapes de FreeCAD.
# Axioma 2: Lógica geométrica pura, sin dependencias de UI.
#
# NOTA: las funciones 1D legacy (generar_divisiones_x/y y sus helpers)
# fueron retiradas. La única fuente de verdad es la matriz v2
# (vdo_layout.Layout + VDO_Divisiones).
# =====================================================================

import FreeCAD as App
import Part

import vdo_reengrose as VDO_RE


def _clave_pieza(pieza):
    if pieza.axis == "X":
        return f"division_x:{pieza.path}"
    return f"division_y:{pieza.path}"


def _modificador(reengroses, pieza):
    datos = (reengroses or {}).get(_clave_pieza(pieza))
    if not datos:
        return VDO_RE.ReengroseModifier()
    try:
        return VDO_RE.ReengroseModifier(datos)
    except VDO_RE.ReengroseError:
        return VDO_RE.ReengroseModifier()


def _caja_pieza(pieza, fondo, espesor, x0, z0):
    if pieza.axis == "X":
        return {
            "nombre": pieza.nombre,
            "x": x0 + pieza.x, "y": 0.0, "z": z0 + pieza.z,
            "w": espesor, "h": fondo, "d": pieza.h,
        }
    return {
        "nombre": pieza.nombre,
        "x": x0 + pieza.x, "y": 0.0, "z": z0 + pieza.z,
        "w": pieza.w, "h": fondo, "d": espesor,
    }


def _ejes_pieza(pieza):
    if pieza.axis == "X":
        return {"largo": "z", "ancho": "y", "espesor": "x"}
    return {"largo": "x", "ancho": "y", "espesor": "z"}


def _caja_dict(caja):
    return {
        "x": float(caja.get("x", 0.0)),
        "y": float(caja.get("y", 0.0)),
        "z": float(caja.get("z", 0.0)),
        "w": float(caja.get("w", 0.0)),
        "h": float(caja.get("h", 0.0)),
        "d": float(caja.get("d", 0.0)),
    }


def _fusionar_caja(base, cambios):
    nueva = dict(base)
    nueva.update(_caja_dict(cambios))
    return nueva


def _modo_obstaculo(obstaculo):
    return (
        obstaculo.get("modo_choque")
        or obstaculo.get("comportamiento_choque_nucleo")
        or obstaculo.get("politica")
        or "retroceso"
    )


def _prioridad_obstaculo(obstaculo):
    valor = obstaculo.get("prioridad")
    if valor:
        return valor
    return None


def _corte_expandido(corte, es_vertical):
    corte = dict(corte)
    if es_vertical:
        corte["x"] -= 0.5
        corte["w"] += 1.0
    else:
        corte["z"] -= 0.5
        corte["d"] += 1.0
    return corte


def _aplicar_choques(caja, obstaculos, es_vertical):
    """Ajusta el núcleo de un panel contra tiras perpendiculares.

    Devuelve ``(caja_ajustada, cortes)``. El modo se toma de la tira
    invasora, de modo que el mismo helper sirve para repisas y montantes.
    """
    ajustada = dict(caja)
    cortes = []
    clave_host = caja.get("clave")
    for obstaculo in obstaculos:
        if clave_host and obstaculo.get("host") == clave_host:
            continue
        modo = _modo_obstaculo(obstaculo)
        plan = VDO_RE.resolver_choque_tira_panel(
            obstaculo, ajustada, modo)
        if not plan:
            continue
        if plan["modo"] == "interrumpir_tira":
            obstaculo.setdefault("_interrupciones", []).append(
                _caja_dict(ajustada))
            continue
        if plan.get("panel"):
            ajustada = _fusionar_caja(ajustada, plan["panel"])
        for corte in plan.get("cortes_panel") or []:
            cortes.append(_corte_expandido(corte, es_vertical))
    return ajustada, cortes


def _preparar_tira(refuerzo, entry, indice):
    pieza = entry["pieza"]
    tira = dict(refuerzo)
    tira["clave"] = (
        f"{_clave_pieza(pieza)}_tira{indice + 1:02d}")
    tira["host"] = _clave_pieza(pieza)
    tira["orientacion_tira"] = (
        "vertical" if pieza.axis == "X" else "horizontal")
    mod = entry["mod"]
    tira["modo_choque"] = mod.comportamiento_choque_nucleo
    prioridad = getattr(mod, "prioridad_encuentro_tiras", None)
    tira["prioridad"] = (
        None if prioridad == VDO_RE.DEFAULTS["prioridad_encuentro_tiras"]
        else prioridad)
    tira["segmentos"] = [_caja_dict(tira)]
    return tira


def _crear_refuerzos(entry):
    mod = entry["mod"]
    if not mod.activo:
        return []
    try:
        geo = VDO_RE.calcular_geometria_caja(
            entry["caja"], mod, entry["ejes"])
    except VDO_RE.ReengroseError:
        return []
    return geo["refuerzos"]


def _cortar_segmentos(segmentos, ganadora):
    nuevos = []
    for segmento in segmentos:
        if VDO_RE.detectar_colision(segmento, ganadora):
            nuevos.extend(
                VDO_RE.recortar_tira_contra_tira(segmento, ganadora))
        else:
            nuevos.append(segmento)
    return nuevos


def _prioridad_par(a, b):
    pa = a.get("prioridad")
    pb = b.get("prioridad")
    if pa and pb:
        if pa == pb:
            return pa
        if "inglete_45" in (pa, pb):
            return "inglete_45"
        return pa
    return pa or pb or "vertical_domina"


def _resolver_tiras_entre_si(tiras):
    """Matriz de prioridades tira contra tira (X/Z, L y T)."""
    for i in range(len(tiras)):
        for j in range(i + 1, len(tiras)):
            a = tiras[i]
            b = tiras[j]
            if a.get("host") and a.get("host") == b.get("host"):
                continue
            segs_a = list(a.get("segmentos") or [])
            segs_b = list(b.get("segmentos") or [])
            if not segs_a or not segs_b:
                continue
            par = None
            for sa in segs_a:
                for sb in segs_b:
                    if VDO_RE.detectar_colision(sa, sb):
                        par = (sa, sb)
                        break
                if par:
                    break
            if par is None:
                continue
            prioridad = _prioridad_par(a, b)
            if prioridad == "inglete_45":
                plan = VDO_RE.resolver_encuentro_tiras(
                    par[0], par[1], "inglete_45")
                if plan.get("inglete"):
                    a.setdefault("ingletes", []).append({
                        "otra": b.get("clave"),
                        "rol": plan["orientacion_a"],
                        "plan": plan["inglete"],
                    })
                    b.setdefault("ingletes", []).append({
                        "otra": a.get("clave"),
                        "rol": plan["orientacion_b"],
                        "plan": plan["inglete"],
                    })
                continue
            res = VDO_RE.resolver_encuentro_tiras(
                par[0], par[1], prioridad)
            if res["perdedor"] == "a":
                for ganadora in segs_b:
                    segs_a = _cortar_segmentos(segs_a, ganadora)
            else:
                for ganadora in segs_a:
                    segs_b = _cortar_segmentos(segs_b, ganadora)
            a["segmentos"] = segs_a
            b["segmentos"] = segs_b


def _aplicar_interrupciones(tira):
    segmentos = list(tira.get("segmentos") or [_caja_dict(tira)])
    for panel in tira.pop("_interrupciones", []):
        segmentos = _cortar_segmentos(segmentos, panel)
    tira["segmentos"] = segmentos


def resolver_tiras(tiras):
    """Aplica interrupciones y la matriz de prioridades sobre tiras vivas."""
    for tira in tiras:
        if "_interrupciones" in tira:
            _aplicar_interrupciones(tira)
    _resolver_tiras_entre_si(tiras)


def _shape_caja(caja):
    if (caja["w"] <= 1e-9 or caja["h"] <= 1e-9
            or caja["d"] <= 1e-9):
        return None
    return Part.makeBox(
        caja["w"], caja["h"], caja["d"],
        App.Vector(caja["x"], caja["y"], caja["z"]))


def _punto_inglete(plan, coord_v, coord_h, coord_e):
    coords = {"x": 0.0, "y": 0.0, "z": 0.0}
    coords[plan["eje_vertical"]] = float(coord_v)
    coords[plan["eje_horizontal"]] = float(coord_h)
    coords[plan["extrusion"]] = float(coord_e)
    return App.Vector(coords["x"], coords["y"], coords["z"])


def _prisma_inglete(inglete):
    """Prisma triangular complementario para biselar una tira a 45 grados."""
    plan = inglete.get("plan") or {}
    try:
        v0, v1 = plan["rango_vertical"]
        h0, h1 = plan["rango_horizontal"]
        e0, e1 = plan["rango_extrusion"]
    except (KeyError, TypeError, ValueError):
        return None
    if v1 - v0 <= 1e-9 or h1 - h0 <= 1e-9:
        return None
    if inglete.get("rol") == "vertical":
        triangulo = [(v0, h1), (v1, h1), (v1, h0)]
    else:
        triangulo = [(v0, h0), (v1, h0), (v0, h1)]
    margen = 0.5
    puntos = [
        _punto_inglete(plan, cv, ch, e0 - margen)
        for cv, ch in triangulo
    ]
    try:
        wire = Part.makePolygon(puntos + [puntos[0]])
        cara = Part.Face(wire)
        vector = {"x": 0.0, "y": 0.0, "z": 0.0}
        vector[plan["extrusion"]] = (e1 - e0) + margen * 2.0
        return cara.extrude(App.Vector(
            vector["x"], vector["y"], vector["z"]))
    except Exception:
        return None


def _shape_tira(tira):
    piezas = []
    for segmento in tira.get("segmentos") or []:
        shape = _shape_caja(segmento)
        if shape is not None:
            piezas.append(shape)
    for inglete in tira.get("ingletes") or []:
        prisma = _prisma_inglete(inglete)
        if prisma is None:
            continue
        nuevas = []
        for pieza in piezas:
            if not pieza.BoundBox.intersect(prisma.BoundBox):
                nuevas.append(pieza)
                continue
            try:
                corte = pieza.cut(prisma)
            except ValueError:
                nuevas.append(pieza)
                continue
            if corte.isNull() or corte.Volume <= 1e-9:
                continue
            nuevas.extend(
                solido for solido in corte.Solids
                if not solido.isNull() and solido.Volume > 1e-9)
        piezas = nuevas
    if not piezas:
        return None
    if len(piezas) == 1:
        return piezas[0]
    return Part.makeCompound(piezas)


def generar_divisiones_matriz(divisiones_json, ancho_cavidad, alto_cavidad,
                              fondo, espesor, x0=0.0, z0=0.0,
                              espacios_x="", espacios_y="",
                              reengroses=None, obstaculos=None):
    """Genera la matriz de vanos v2, con reengroses y colisiones opcionales.

    ``reengroses``: dict clave -> modificador. ``obstaculos``: cajas AABB de
    reengroses externos (por ejemplo laterales) con su política de choque.
    """
    from vdo_layout import Layout, resolve_layout

    if divisiones_json:
        layout = Layout.loads(divisiones_json)
        avisos = []
    else:
        layout, avisos = Layout.from_legacy(espacios_x, espacios_y)

    reengroses = reengroses or {}
    obstaculos = list(obstaculos or [])
    resuelto = resolve_layout(
        layout, ancho_cavidad, alto_cavidad, espesor,
        reengroses=reengroses)

    entries = []
    for pieza in resuelto.pieces:
        entries.append({
            "pieza": pieza,
            "clave": _clave_pieza(pieza),
            "caja": _caja_pieza(pieza, fondo, espesor, x0, z0),
            "ejes": _ejes_pieza(pieza),
            "mod": _modificador(reengroses, pieza),
            "refuerzos": [],
            "tiras": [],
            "cortes": [],
        })
        entries[-1]["caja"]["clave"] = entries[-1]["clave"]

    tiras = []

    # 1) Los montantes verticales aportan sus tiras primero: son las que
    #    definen el retranqueo de repisas.
    for entry in entries:
        if entry["pieza"].axis != "X" or not entry["mod"].activo:
            continue
        entry["refuerzos"] = _crear_refuerzos(entry)
        for i, ref in enumerate(entry["refuerzos"]):
            tira = _preparar_tira(ref, entry, i)
            entry["tiras"].append(tira)
            tiras.append(tira)

    # 2) Repisas: se ajustan contra tiras verticales y obstáculos externos.
    #    Después se recalculan sus tiras desde la caja real ya retranqueada.
    for entry in entries:
        if entry["pieza"].axis != "Y":
            continue
        ajustada, cortes = _aplicar_choques(
            entry["caja"], obstaculos + tiras, es_vertical=False)
        entry["caja"] = ajustada
        entry["cortes"].extend(cortes)
        entry["refuerzos"] = _crear_refuerzos(entry)
        entry["tiras"] = []
        for i, ref in enumerate(entry["refuerzos"]):
            tira = _preparar_tira(ref, entry, i)
            tira["anclaje_y"] = VDO_RE.vector_anclaje_y(entry["caja"])
            entry["tiras"].append(tira)
            tiras.append(tira)

    # 3) Montantes: choque simétrico contra tiras horizontales (techo,
    #    base, repisas). El techo ya no parte la tira: el montante cajea.
    for entry in entries:
        if entry["pieza"].axis != "X":
            continue
        ajustada, cortes = _aplicar_choques(
            entry["caja"], obstaculos + tiras, es_vertical=True)
        entry["caja"] = ajustada
        entry["cortes"].extend(cortes)

    for tira in tiras:
        _aplicar_interrupciones(tira)
    _resolver_tiras_entre_si(tiras)

    shapes = []
    piezas = []
    for entry in entries:
        pieza = entry["pieza"]
        caja = entry["caja"]
        core_shape = _shape_caja(caja)
        if core_shape is not None:
            for corte in entry["cortes"]:
                if (corte["w"] <= 1e-9 or corte["h"] <= 1e-9
                        or corte["d"] <= 1e-9):
                    continue
                pieza_corte = Part.makeBox(
                    corte["w"], corte["h"], corte["d"],
                    App.Vector(corte["x"], corte["y"], corte["z"]))
                core_shape = core_shape.cut(pieza_corte)
            shapes.append(core_shape)
        for tira in entry["tiras"]:
            shape = _shape_tira(tira)
            tira["shape"] = shape
            if shape is not None:
                shapes.append(shape)

        if pieza.axis == "X":
            largo = fondo
            ancho = caja["d"]
        else:
            largo = caja["w"]
            ancho = caja["h"]

        datos = {
            "nombre": pieza.nombre,
            "tipo": "panel",
            "rol": "division_x" if pieza.axis == "X" else "division_y",
            "largo": largo,
            "ancho": ancho,
            "espesor": espesor,
            "orientacion": "vertical" if pieza.axis == "X" else "horizontal",
            "cantidad": 1,
        }
        datos["caja_geometrica"] = caja
        if entry["cortes"]:
            datos["mocheos"] = list(entry["cortes"])
        if entry["mod"].activo:
            datos["clave_reengrose"] = entry["clave"]
            datos["reengrose"] = entry["mod"].to_dict()
            datos["caja"] = caja
            datos["ejes"] = entry["ejes"]
            if entry["mod"].modo_fabricacion == "pacha":
                datos["grupo_pacha"] = f"Pacha_{pieza.nombre}"
        piezas.append(datos)

    resuelto.tiras = tiras
    resumen = resuelto.summary()
    if avisos:
        resumen += "\n" + "\n".join(avisos)
    return shapes, resumen, piezas, resuelto
