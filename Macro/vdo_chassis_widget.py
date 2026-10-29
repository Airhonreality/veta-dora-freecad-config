# -*- coding: utf-8 -*-
"""
vdo_chassis_widget.py

Widget de Corte Transversal Interactivo 2D para la Envolvente / Chasis Paramétrico (Capa 1).
Parte del Sistema VDO (Ergonomía Cognitiva, Semiótica Espacial y Poka-Yoke para CAD/CAM).

Axioma:
    El COCO no es una primitiva; es solo un arquetipo de una envolvente paramétrica
    donde las caras pueden estar Activas o Ausentes, los encuentros de esquina conmutan
    entre las uniones de taller reales (tapa_domina, lateral_domina, inglete_45),
    y la base soporta múltiples estrategias (zócalo, suspendido, patas).

Compatible con PySide, PySide2 y PySide6 mediante vdo_qt.py.
"""

import sys

try:
    from PySide import QtCore, QtGui, QtWidgets, QtSvg
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets, QtSvg

from vdo_qt import VDO_DoubleSpinBox


# ----------------------------------------------------------------------
# Iconografía Vectorial Lucide Embebida (SVG)
# ----------------------------------------------------------------------
LUCIDE_ICONS = {
    # Encuentros de esquina
    "tapa_domina": """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2">
        <rect x="2" y="3" width="20" height="5" fill="#007acc" stroke="#0098ff" rx="1"/>
        <rect x="2" y="8" width="6" height="13" fill="#333333" stroke="#666666" rx="1"/>
    </svg>""",

    "lateral_domina": """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2">
        <rect x="2" y="3" width="6" height="18" fill="#007acc" stroke="#0098ff" rx="1"/>
        <rect x="8" y="3" width="14" height="6" fill="#333333" stroke="#666666" rx="1"/>
    </svg>""",

    "inglete_45": """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 20 L20 4" stroke-width="2.5"/>
        <path d="M4 4 L4 20 L12 20 L12 12 L20 12 L20 4 Z" fill="#252525" stroke="#555555" stroke-width="1"/>
        <circle cx="4" cy="20" r="1.5" fill="#00d4ff"/>
        <circle cx="20" cy="4" r="1.5" fill="#00d4ff"/>
    </svg>""",

    # Estrategias de anclaje
    "zocalo": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="4" width="20" height="10" rx="1" fill="#2b2b2b" stroke="#555555"/>
        <rect x="5" y="14" width="14" height="6" fill="#007acc" stroke="#0098ff"/>
        <line x1="2" y1="20" x2="22" y2="20" stroke="#888888" stroke-dasharray="2 2"/>
    </svg>""",

    "suspendido": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="5" y="3" width="16" height="14" rx="1" fill="#2b2b2b" stroke="#555555"/>
        <line x1="2" y1="3" x2="2" y2="21" stroke="#ffaa00" stroke-width="3"/>
        <path d="M2 6 h3 v4 h-3" fill="#ffaa00"/>
        <line x1="2" y1="21" x2="22" y2="21" stroke="#555555" stroke-dasharray="2 2"/>
    </svg>""",

    "patas": """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="3" width="20" height="11" rx="1" fill="#2b2b2b" stroke="#555555"/>
        <rect x="5" y="14" width="3" height="6" fill="#007acc"/>
        <ellipse cx="6.5" cy="20" rx="3" ry="1" fill="#0098ff"/>
        <rect x="16" y="14" width="3" height="6" fill="#007acc"/>
        <ellipse cx="17.5" cy="20" rx="3" ry="1" fill="#0098ff"/>
        <line x1="2" y1="21" x2="22" y2="21" stroke="#888888" stroke-dasharray="2 2"/>
    </svg>""",

    # Fondo trasero
    "ranura": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#555555" stroke-dasharray="2 2"/>
        <line x1="7" y1="3" x2="7" y2="21" stroke="#00d4ff" stroke-width="3"/>
    </svg>""",

    "galce": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#555555"/>
        <path d="M3 6 h4 v15" stroke="#ffaa00" stroke-width="2.5"/>
    </svg>""",

    "atornillado": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" fill="#252525" stroke="#777777"/>
        <circle cx="6" cy="6" r="1.5" fill="#28a745"/>
        <circle cx="18" cy="6" r="1.5" fill="#28a745"/>
        <circle cx="6" cy="18" r="1.5" fill="#28a745"/>
        <circle cx="18" cy="18" r="1.5" fill="#28a745"/>
    </svg>""",

    "abierto": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#888888" stroke-width="2" stroke-linecap="round">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#555555" stroke-dasharray="3 3"/>
        <line x1="4" y1="4" x2="20" y2="20" stroke="#e74c3c" stroke-width="2"/>
    </svg>""",

    # Arquetipos rápidos
    "coco": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="1"/></svg>""",
    "escritorio": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2"><line x1="2" y1="5" x2="22" y2="5" stroke-width="3"/><line x1="4" y1="5" x2="4" y2="20" stroke-width="2"/><line x1="20" y1="5" x2="20" y2="20" stroke-width="2"/></svg>""",
    "estanteria": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2"><line x1="4" y1="2" x2="4" y2="22" stroke-width="2"/><line x1="20" y1="2" x2="20" y2="22" stroke-width="2"/><line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="4" y1="21" x2="20" y2="21" stroke-width="2.5"/></svg>""",
    "aereo": """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e0e0e0" stroke-width="2"><rect x="4" y="3" width="16" height="14" rx="1"/><line x1="2" y1="2" x2="2" y2="20" stroke="#ffaa00" stroke-width="2"/></svg>""",
}

_ICON_CACHE = {}


def get_svg_icon(name: str, size: int = 22) -> QtGui.QIcon:
    """Renderiza un string SVG a QIcon de manera autónoma."""
    key = (name, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    svg_str = LUCIDE_ICONS.get(name, "")
    if not svg_str:
        return QtGui.QIcon()
    svg_bytes = QtCore.QByteArray(svg_str.encode("utf-8"))
    renderer = QtSvg.QSvgRenderer(svg_bytes)
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    icon = QtGui.QIcon(pixmap)
    _ICON_CACHE[key] = icon
    return icon


# ----------------------------------------------------------------------
# Constantes Semióticas de Chasis
# ----------------------------------------------------------------------
CARAS = ("superior", "inferior", "izquierda", "derecha", "fondo")
ENCUENTROS = ("superior_izq", "superior_der", "inferior_izq", "inferior_der")
TIPOS_ENCUENTRO = ("tapa_domina", "lateral_domina", "inglete_45")

ENCUENTRO_TOOLTIPS = {
    "tapa_domina": "Tapa/Base domina: El tablero horizontal vuela continuo de lado a lado (soporta cargas superiores de granito/mesones).",
    "lateral_domina": "Lateral domina: El costado vertical sube completo de punta a punta (ideal para módulos suspendidos o laterales a piso).",
    "inglete_45": "Inglete 45°: Ambas caras cortadas a bisel diagonal continuo (máxima estética de veta continua sin cantos vistos).",
}

ENCUENTRO_LABELS = {
    "tapa_domina": "Tapa/Base pasa",
    "lateral_domina": "Lateral pasa",
    "inglete_45": "Inglete 45°",
}

TIPOS_FONDO = [
    ("ranurado_5mm", "Ranura 5 mm", "ranura", "Fondo delgado de 5.5mm embutido en canal perimetral."),
    ("ranurado_3mm", "Ranura 3 mm", "ranura", "Fondo estándar de 3mm (MDF/Durolac) embutido en canal."),
    ("galce", "Galce / Rebaje", "galce", "Fondo embutido en rebaje fresado perimetral posterior."),
    ("atornillado", "Atornillado 15/18 mm", "atornillado", "Fondo estructural grueso de arriostramiento atornillado a tope."),
    ("abierto", "Abierto / Sin fondo", "abierto", "Mueble pasante sin trasera (estantería o mueble de paso)."),
]

ESTRATEGIAS_BASE = ("zocalo", "suspendido", "patas")


# ----------------------------------------------------------------------
# Canvas 2D de Sección Transversal
# ----------------------------------------------------------------------
class _VDOChassisCrossSectionCanvas(QtWidgets.QWidget):
    """
    Lienzo gráfico interactivo que renderiza el corte transversal 2D del chasis.
    Muestra en tiempo real:
      - Canto y espesor de las 4 caras (Activas en color sólido o Ausentes en línea punteada).
      - Cortes exactos en las 4 esquinas según el tipo de encuentro (tapa pasa, lateral pasa, inglete 45°).
      - Visualización del fondo trasero (canal de ranura, rebaje de galce o vacío abierto).
      - Estructura de anclaje inferior (zócalo retranqueado, herrajes suspendidos o patas regulables).
    """

    faceClicked = QtCore.Signal(str)
    cornerClicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(240, 200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._caras = {
            "superior": {"activa": True, "tipo": "estructural"},
            "inferior": {"activa": True, "tipo": "estructural"},
            "izquierda": {"activa": True, "tipo": "estructural"},
            "derecha": {"activa": True, "tipo": "estructural"},
            "fondo": {"activa": True, "tipo": "ranurado_5mm"},
        }
        self._encuentros = {
            "superior_izq": "tapa_domina",
            "superior_der": "tapa_domina",
            "inferior_izq": "lateral_domina",
            "inferior_der": "lateral_domina",
        }
        self._base = {
            "estrategia": "zocalo",
            "altura": 100.0,
            "separacion_frente": 50.0,
        }

        self._hover_target = None
        self.setMouseTracking(True)

    def update_state(self, caras, encuentros, base):
        self._caras = caras
        self._encuentros = encuentros
        self._base = base
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # Fondo general del canvas
        rect = self.rect()
        p.fillRect(rect, QtGui.QColor("#181818"))
        p.setPen(QtGui.QPen(QtGui.QColor("#262626"), 1))
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

        # Dimensiones del chasis en el canvas
        margin_x = 36
        margin_top = 28
        margin_bottom = 44  # Espacio para zócalo/patas
        w = self.width() - (2 * margin_x)
        h = self.height() - margin_top - margin_bottom

        if w < 100 or h < 80:
            p.end()
            return

        x0 = margin_x
        y0 = margin_top
        T = 14  # Espesor gráfico del tablero en píxeles

        # -------------------------------------------------------------
        # 1. Dibujar el Fondo Trasero (Cavidad Interior)
        # -------------------------------------------------------------
        cavidad_rect = QtCore.QRectF(x0 + T, y0 + T, w - (2 * T), h - (2 * T))
        p.fillRect(cavidad_rect, QtGui.QColor("#1f1f1f"))

        tipo_fondo = self._caras["fondo"].get("tipo", "ranurado_5mm")
        activa_fondo = self._caras["fondo"].get("activa", True)

        if activa_fondo and tipo_fondo != "abierto":
            if "ranurado" in tipo_fondo:
                # Línea cian discontinua representando canal fresado
                pen_ranura = QtGui.QPen(QtGui.QColor("#00d4ff"), 1.5, QtCore.Qt.DashLine)
                p.setPen(pen_ranura)
                # Canal a 8px del borde exterior
                inset = 6
                p.drawRect(QtCore.QRectF(x0 + inset, y0 + inset, w - 2 * inset, h - 2 * inset))
            elif tipo_fondo == "galce":
                # Rebaje escalonado perimetral ámbar
                pen_galce = QtGui.QPen(QtGui.QColor("#ffaa00"), 1.5, QtCore.Qt.DotLine)
                p.setPen(pen_galce)
                p.drawRect(QtCore.QRectF(x0 + 4, y0 + 4, w - 8, h - 8))
            elif tipo_fondo == "atornillado":
                # Tapa posterior sólida completa con tornillos verdes en esquinas
                p.fillRect(cavidad_rect.adjusted(2, 2, -2, -2), QtGui.QColor("#24272b"))
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(QtGui.QColor("#28a745"))
                p.drawEllipse(QtCore.QPointF(cavidad_rect.left() + 8, cavidad_rect.top() + 8), 2.5, 2.5)
                p.drawEllipse(QtCore.QPointF(cavidad_rect.right() - 8, cavidad_rect.top() + 8), 2.5, 2.5)
                p.drawEllipse(QtCore.QPointF(cavidad_rect.left() + 8, cavidad_rect.bottom() - 8), 2.5, 2.5)
                p.drawEllipse(QtCore.QPointF(cavidad_rect.right() - 8, cavidad_rect.bottom() - 8), 2.5, 2.5)
        else:
            # Abierto: rayitas de vacío diagonal suave
            p.setPen(QtGui.QPen(QtGui.QColor("#2a2a2a"), 1, QtCore.Qt.DotLine))
            p.drawLine(cavidad_rect.topLeft(), cavidad_rect.bottomRight())
            p.drawLine(cavidad_rect.bottomLeft(), cavidad_rect.topRight())

        # -------------------------------------------------------------
        # 2. Dibujar Estructura de Apoyo Inferior (Base / Anclaje)
        # -------------------------------------------------------------
        estrategia_base = self._base.get("estrategia", "zocalo")
        y_piso = y0 + h + 24

        # Línea de piso de taller
        pen_piso = QtGui.QPen(QtGui.QColor("#444444"), 1, QtCore.Qt.DashLine)
        p.setPen(pen_piso)
        p.drawLine(x0 - 15, int(y_piso), x0 + w + 15, int(y_piso))
        p.setPen(QtGui.QColor("#777777"))
        p.setFont(QtGui.QFont("SansSerif", 7))
        p.drawText(x0 - 15, int(y_piso) + 10, "PISO")

        if estrategia_base == "zocalo":
            # Zócalo de taller: bloque central retranqueado
            z_offset = 12  # Retranqueo visual
            z_w = w - (2 * z_offset)
            z_h = y_piso - (y0 + h)
            rect_zocalo = QtCore.QRectF(x0 + z_offset, y0 + h, z_w, z_h)
            p.fillRect(rect_zocalo, QtGui.QColor("#2b2b2b"))
            p.setPen(QtGui.QPen(QtGui.QColor("#007acc"), 1.5))
            p.drawRect(rect_zocalo)
            p.setPen(QtGui.QColor("#00d4ff"))
            p.drawText(rect_zocalo, QtCore.Qt.AlignCenter, "ZÓCALO")

        elif estrategia_base == "patas":
            # Dos patas regulables
            pata_w = 6
            pata_h = y_piso - (y0 + h)
            pata_x1 = x0 + 16
            pata_x2 = x0 + w - 16 - pata_w
            # Pata izquierda
            p.fillRect(QtCore.QRectF(pata_x1, y0 + h, pata_w, pata_h), QtGui.QColor("#007acc"))
            p.fillRect(QtCore.QRectF(pata_x1 - 4, y_piso - 3, pata_w + 8, 3), QtGui.QColor("#0098ff"))
            # Pata derecha
            p.fillRect(QtCore.QRectF(pata_x2, y0 + h, pata_w, pata_h), QtGui.QColor("#007acc"))
            p.fillRect(QtCore.QRectF(pata_x2 - 4, y_piso - 3, pata_w + 8, 3), QtGui.QColor("#0098ff"))

        elif estrategia_base == "suspendido":
            # Módulo flotando; soportes laterales en pared
            pen_muro = QtGui.QPen(QtGui.QColor("#ffaa00"), 3)
            p.setPen(pen_muro)
            p.drawLine(x0 - 4, y0 + 10, x0 - 4, y0 + 40)
            p.setPen(QtGui.QColor("#ffaa00"))
            p.drawText(x0 - 25, y0 + 28, "🧗")

        # -------------------------------------------------------------
        # 3. Dibujar las 4 Caras con Encuentros de Esquina Físicos
        # -------------------------------------------------------------
        caras = self._caras
        enc = self._encuentros

        color_activa = QtGui.QColor("#2f353d")
        border_activa = QtGui.QColor("#007acc")
        color_ausente = QtGui.QColor("#1c1c1c")
        border_ausente = QtGui.QColor("#444444")

        # Configuración de límites por encuentro
        # Superior:
        sup_x1 = x0 if enc["superior_izq"] in ("tapa_domina", "inglete_45") else x0 + T
        sup_x2 = x0 + w if enc["superior_der"] in ("tapa_domina", "inglete_45") else x0 + w - T
        sup_y = y0

        # Inferior:
        inf_x1 = x0 if enc["inferior_izq"] in ("tapa_domina", "inglete_45") else x0 + T
        inf_x2 = x0 + w if enc["inferior_der"] in ("tapa_domina", "inglete_45") else x0 + w - T
        inf_y = y0 + h - T

        # Izquierda:
        izq_y1 = y0 if enc["superior_izq"] in ("lateral_domina", "inglete_45") else y0 + T
        izq_y2 = y0 + h if enc["inferior_izq"] in ("lateral_domina", "inglete_45") else y0 + h - T
        izq_x = x0

        # Derecha:
        der_y1 = y0 if enc["superior_der"] in ("lateral_domina", "inglete_45") else y0 + T
        der_y2 = y0 + h if enc["inferior_der"] in ("lateral_domina", "inglete_45") else y0 + h - T
        der_x = x0 + w - T

        # A. Cara Superior
        rect_sup = QtCore.QRectF(sup_x1, sup_y, sup_x2 - sup_x1, T)
        if caras["superior"]["activa"]:
            p.fillRect(rect_sup, color_activa)
            p.setPen(QtGui.QPen(border_activa, 1.5))
            p.drawRect(rect_sup)
        else:
            p.fillRect(rect_sup, color_ausente)
            p.setPen(QtGui.QPen(border_ausente, 1, QtCore.Qt.DashLine))
            p.drawRect(rect_sup)
            p.setPen(QtGui.QColor("#666666"))
            p.drawText(rect_sup, QtCore.Qt.AlignCenter, "TAPA AUSENTE")

        # B. Cara Inferior
        rect_inf = QtCore.QRectF(inf_x1, inf_y, inf_x2 - inf_x1, T)
        if caras["inferior"]["activa"]:
            p.fillRect(rect_inf, color_activa)
            p.setPen(QtGui.QPen(border_activa, 1.5))
            p.drawRect(rect_inf)
        else:
            p.fillRect(rect_inf, color_ausente)
            p.setPen(QtGui.QPen(border_ausente, 1, QtCore.Qt.DashLine))
            p.drawRect(rect_inf)
            p.setPen(QtGui.QColor("#666666"))
            p.drawText(rect_inf, QtCore.Qt.AlignCenter, "BASE AUSENTE")

        # C. Lateral Izquierdo
        rect_izq = QtCore.QRectF(izq_x, izq_y1, T, izq_y2 - izq_y1)
        if caras["izquierda"]["activa"]:
            p.fillRect(rect_izq, color_activa)
            p.setPen(QtGui.QPen(border_activa, 1.5))
            p.drawRect(rect_izq)
        else:
            p.fillRect(rect_izq, color_ausente)
            p.setPen(QtGui.QPen(border_ausente, 1, QtCore.Qt.DashLine))
            p.drawRect(rect_izq)

        # D. Lateral Derecho
        rect_der = QtCore.QRectF(der_x, der_y1, T, der_y2 - der_y1)
        if caras["derecha"]["activa"]:
            p.fillRect(rect_der, color_activa)
            p.setPen(QtGui.QPen(border_activa, 1.5))
            p.drawRect(rect_der)
        else:
            p.fillRect(rect_der, color_ausente)
            p.setPen(QtGui.QPen(border_ausente, 1, QtCore.Qt.DashLine))
            p.drawRect(rect_der)

        # -------------------------------------------------------------
        # 4. Líneas Diagonales de Inglete 45°
        # -------------------------------------------------------------
        pen_inglete = QtGui.QPen(QtGui.QColor("#00d4ff"), 2)
        if enc["superior_izq"] == "inglete_45" and caras["superior"]["activa"] and caras["izquierda"]["activa"]:
            p.setPen(pen_inglete)
            p.drawLine(QtCore.QPointF(x0, y0), QtCore.QPointF(x0 + T, y0 + T))

        if enc["superior_der"] == "inglete_45" and caras["superior"]["activa"] and caras["derecha"]["activa"]:
            p.setPen(pen_inglete)
            p.drawLine(QtCore.QPointF(x0 + w, y0), QtCore.QPointF(x0 + w - T, y0 + T))

        if enc["inferior_izq"] == "inglete_45" and caras["inferior"]["activa"] and caras["izquierda"]["activa"]:
            p.setPen(pen_inglete)
            p.drawLine(QtCore.QPointF(x0, y0 + h), QtCore.QPointF(x0 + T, y0 + h - T))

        if enc["inferior_der"] == "inglete_45" and caras["inferior"]["activa"] and caras["derecha"]["activa"]:
            p.setPen(pen_inglete)
            p.drawLine(QtCore.QPointF(x0 + w, y0 + h), QtCore.QPointF(x0 + w - T, y0 + h - T))

        p.end()

    def mousePressEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()

        margin_x = 36
        margin_top = 28
        margin_bottom = 44
        w = self.width() - (2 * margin_x)
        h = self.height() - margin_top - margin_bottom
        x0 = margin_x
        y0 = margin_top
        T = 18

        # Zonas de clic para las caras
        if y0 <= y <= y0 + T and x0 <= x <= x0 + w:
            self.faceClicked.emit("superior")
            return
        if y0 + h - T <= y <= y0 + h and x0 <= x <= x0 + w:
            self.faceClicked.emit("inferior")
            return
        if x0 <= x <= x0 + T and y0 <= y <= y0 + h:
            self.faceClicked.emit("izquierda")
            return
        if x0 + w - T <= x <= x0 + w and y0 <= y <= y0 + h:
            self.faceClicked.emit("derecha")
            return

        # Clic en el centro (fondo)
        if x0 + T < x < x0 + w - T and y0 + T < y < y0 + h - T:
            self.faceClicked.emit("fondo")
            return

        super().mousePressEvent(event)


# ----------------------------------------------------------------------
# Widget Principal: VDOChassisControllerWidget
# ----------------------------------------------------------------------
class VDOChassisControllerWidget(QtWidgets.QWidget):
    """
    Controlador semiótico 2D para la Envolvente / Chasis Paramétrico (Capa 1).
    Permite conmutar caras activas/ausentes, ciclar uniones de esquina y
    definir la estrategia de base de forma interactiva y Poka-Yoke.
    """

    sigChassisChanged = QtCore.Signal(dict)
    sigConfigChanged = sigChassisChanged  # Alias de conveniencia

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cargando = False

        # Estado del modelo de Capa 1
        self._caras = {
            "superior": {"activa": True, "tipo": "estructural"},
            "inferior": {"activa": True, "tipo": "estructural"},
            "izquierda": {"activa": True, "tipo": "estructural"},
            "derecha": {"activa": True, "tipo": "estructural"},
            "fondo": {"activa": True, "tipo": "ranurado_5mm"},
        }
        self._encuentros = {
            "superior_izq": "tapa_domina",
            "superior_der": "tapa_domina",
            "inferior_izq": "lateral_domina",
            "inferior_der": "lateral_domina",
        }
        self._base = {
            "estrategia": "zocalo",
            "altura": 100.0,
            "separacion_frente": 50.0,
        }

        self._init_ui()
        self._aplicar_estilos()
        self._actualizar_ui()

    def _init_ui(self):
        layout_raiz = QtWidgets.QVBoxLayout(self)
        layout_raiz.setContentsMargins(8, 8, 8, 8)
        layout_raiz.setSpacing(8)

        # -------------------------------------------------------------
        # 1. Barra Superior: Título y Arquetipos Rápidos
        # -------------------------------------------------------------
        barra_sup = QtWidgets.QHBoxLayout()
        barra_sup.setSpacing(6)

        lbl_titulo = QtWidgets.QLabel("🪵 <b>CHASIS PARAMÉTRICO</b>")
        lbl_titulo.setStyleSheet("font-size: 11px; color: #e0e0e0; letter-spacing: 0.5px;")
        barra_sup.addWidget(lbl_titulo)

        barra_sup.addStretch()

        lbl_arq = QtWidgets.QLabel("Arquetipos:")
        lbl_arq.setStyleSheet("font-size: 9px; color: #888888;")
        barra_sup.addWidget(lbl_arq)

        self.btn_arquetipos = {}
        arquetipos = [
            ("COCO", "coco", "Carcasa estándar con 5 caras activas"),
            ("Mesa", "escritorio", "Sin base inferior (escritorio / mesa)"),
            ("Estante", "estanteria", "Sin tapa superior ni fondo"),
            ("Aéreo", "aereo", "Módulo suspendido para muro"),
        ]
        for nombre, icono_id, tip in arquetipos:
            b = QtWidgets.QPushButton(nombre)
            b.setIcon(get_svg_icon(icono_id, 14))
            b.setToolTip(tip)
            b.setProperty("class", "arquetipo-chip")
            b.setFixedHeight(22)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.clicked.connect(lambda _, n=nombre: self._on_arquetipo_clicked(n))
            barra_sup.addWidget(b)
            self.btn_arquetipos[nombre] = b

        layout_raiz.addLayout(barra_sup)

        # -------------------------------------------------------------
        # 2. Matriz 3x3 del Corte Transversal Interactivo
        # -------------------------------------------------------------
        frame_matriz = QtWidgets.QFrame()
        frame_matriz.setObjectName("frameMatriz")
        grid = QtWidgets.QGridLayout(frame_matriz)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(4)

        # Esquinas (4 botones interactivos con iconos de encuentro)
        self.btn_esquina = {}
        esquinas_spec = [
            ("superior_izq", 0, 0, "Sup-Izq"),
            ("superior_der", 0, 2, "Sup-Der"),
            ("inferior_izq", 2, 0, "Inf-Izq"),
            ("inferior_der", 2, 2, "Inf-Der"),
        ]
        for clave, fila, col, tag in esquinas_spec:
            btn = QtWidgets.QPushButton()
            btn.setProperty("class", "btn-esquina")
            btn.setFixedSize(36, 36)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setIconSize(QtCore.QSize(22, 22))
            btn.clicked.connect(lambda _, c=clave: self._on_esquina_clicked(c))
            grid.addWidget(btn, fila, col)
            self.btn_esquina[clave] = btn

        # Botón Tapa Superior (Borde Norte)
        self.btn_cara_sup = QtWidgets.QPushButton("── TAPA SUPERIOR · Activa ──")
        self.btn_cara_sup.setCheckable(True)
        self.btn_cara_sup.setChecked(True)
        self.btn_cara_sup.setProperty("class", "btn-cara-horiz")
        self.btn_cara_sup.setFixedHeight(28)
        self.btn_cara_sup.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cara_sup.clicked.connect(lambda: self._on_cara_toggled("superior"))
        grid.addWidget(self.btn_cara_sup, 0, 1)

        # Botón Lateral Izquierdo (Borde Oeste)
        self.btn_cara_izq = QtWidgets.QPushButton("│\nL\nA\nT\n.\n\nI\nZ\nQ\n│")
        self.btn_cara_izq.setCheckable(True)
        self.btn_cara_izq.setChecked(True)
        self.btn_cara_izq.setProperty("class", "btn-cara-vert")
        self.btn_cara_izq.setFixedWidth(28)
        self.btn_cara_izq.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cara_izq.clicked.connect(lambda: self._on_cara_toggled("izquierda"))
        grid.addWidget(self.btn_cara_izq, 1, 0)

        # Centro: Canvas de Sección 2D
        self.canvas = _VDOChassisCrossSectionCanvas()
        self.canvas.faceClicked.connect(self._on_cara_toggled)
        grid.addWidget(self.canvas, 1, 1)

        # Botón Lateral Derecho (Borde Este)
        self.btn_cara_der = QtWidgets.QPushButton("│\nL\nA\nT\n.\n\nD\nE\nR\n│")
        self.btn_cara_der.setCheckable(True)
        self.btn_cara_der.setChecked(True)
        self.btn_cara_der.setProperty("class", "btn-cara-vert")
        self.btn_cara_der.setFixedWidth(28)
        self.btn_cara_der.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cara_der.clicked.connect(lambda: self._on_cara_toggled("derecha"))
        grid.addWidget(self.btn_cara_der, 1, 2)

        # Botón Base Inferior (Borde Sur)
        self.btn_cara_inf = QtWidgets.QPushButton("── BASE INFERIOR · Activa ──")
        self.btn_cara_inf.setCheckable(True)
        self.btn_cara_inf.setChecked(True)
        self.btn_cara_inf.setProperty("class", "btn-cara-horiz")
        self.btn_cara_inf.setFixedHeight(28)
        self.btn_cara_inf.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cara_inf.clicked.connect(lambda: self._on_cara_toggled("inferior"))
        grid.addWidget(self.btn_cara_inf, 2, 1)

        layout_raiz.addWidget(frame_matriz)

        # -------------------------------------------------------------
        # 3. Micro-Panel de Fondo Trasero
        # -------------------------------------------------------------
        layout_fondo = QtWidgets.QHBoxLayout()
        layout_fondo.setSpacing(6)

        lbl_fondo = QtWidgets.QLabel("Fondo Trasero:")
        lbl_fondo.setStyleSheet("font-size: 10px; color: #aaaaaa;")
        layout_fondo.addWidget(lbl_fondo)

        self.combo_fondo = QtWidgets.QComboBox()
        self.combo_fondo.setProperty("class", "combo-fondo")
        for val, label, icono_id, tip in TIPOS_FONDO:
            self.combo_fondo.addItem(get_svg_icon(icono_id, 16), label, val)
        self.combo_fondo.currentIndexChanged.connect(self._on_fondo_changed)
        layout_fondo.addWidget(self.combo_fondo, 1)

        layout_raiz.addLayout(layout_fondo)

        # -------------------------------------------------------------
        # 4. Estrategia de Base / Anclaje al Piso
        # -------------------------------------------------------------
        grupo_base = QtWidgets.QGroupBox("ESTRATEGIA DE ANCLAJE AL PISO")
        grupo_base.setProperty("class", "grupo-base")
        layout_base = QtWidgets.QVBoxLayout(grupo_base)
        layout_base.setContentsMargins(6, 6, 6, 6)
        layout_base.setSpacing(6)

        # Selector de 3 estrategias
        fila_estrategias = QtWidgets.QHBoxLayout()
        fila_estrategias.setSpacing(4)
        self.btn_estrategias = {}

        estrategias_spec = [
            ("zocalo", "🪵 Zócalo Taller", "zocalo", "Tarima / zócalo frontal de taller"),
            ("suspendido", "🧗 Suspendido", "suspendido", "Fijación a muro estructural sin apoyo en piso"),
            ("patas", "🛞 Patas / Niveladores", "patas", "Patas plásticas regulables en altura"),
        ]
        for key, label, icono_id, tip in estrategias_spec:
            btn = QtWidgets.QPushButton(label)
            btn.setIcon(get_svg_icon(icono_id, 16))
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setProperty("class", "estrategia-btn")
            btn.setFixedHeight(28)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._on_estrategia_clicked(k))
            fila_estrategias.addWidget(btn)
            self.btn_estrategias[key] = btn

        self.btn_estrategias["zocalo"].setChecked(True)
        layout_base.addLayout(fila_estrategias)

        # Parámetros dinámicos según estrategia
        self.stack_params = QtWidgets.QStackedWidget()

        # Página Zócalo
        page_zocalo = QtWidgets.QWidget()
        lay_pz = QtWidgets.QHBoxLayout(page_zocalo)
        lay_pz.setContentsMargins(0, 0, 0, 0)
        lay_pz.setSpacing(6)

        lay_pz.addWidget(QtWidgets.QLabel("Altura zócalo:"))
        self.spin_altura_zocalo = VDO_DoubleSpinBox()
        self.spin_altura_zocalo.setRange(20.0, 300.0)
        self.spin_altura_zocalo.setValue(100.0)
        self.spin_altura_zocalo.setSuffix(" mm")
        self.spin_altura_zocalo.valueChanged.connect(self._on_param_base_changed)
        lay_pz.addWidget(self.spin_altura_zocalo)

        lay_pz.addWidget(QtWidgets.QLabel("Separación:"))
        self.spin_offset_zocalo = VDO_DoubleSpinBox()
        self.spin_offset_zocalo.setRange(0.0, 150.0)
        self.spin_offset_zocalo.setValue(50.0)
        self.spin_offset_zocalo.setSuffix(" mm")
        self.spin_offset_zocalo.valueChanged.connect(self._on_param_base_changed)
        lay_pz.addWidget(self.spin_offset_zocalo)
        self.stack_params.addWidget(page_zocalo)

        # Página Suspendido
        page_susp = QtWidgets.QWidget()
        lay_ps = QtWidgets.QHBoxLayout(page_susp)
        lay_ps.setContentsMargins(0, 0, 0, 0)
        lay_ps.setSpacing(6)

        lay_ps.addWidget(QtWidgets.QLabel("Despegue de piso:"))
        self.spin_despegue_piso = VDO_DoubleSpinBox()
        self.spin_despegue_piso.setRange(50.0, 1500.0)
        self.spin_despegue_piso.setValue(300.0)
        self.spin_despegue_piso.setSuffix(" mm")
        self.spin_despegue_piso.valueChanged.connect(self._on_param_base_changed)
        lay_ps.addWidget(self.spin_despegue_piso)

        lbl_camar = QtWidgets.QLabel("🧗 Herrajes Camar / Scilm")
        lbl_camar.setStyleSheet("color: #ffaa00; font-size: 10px;")
        lay_ps.addWidget(lbl_camar)
        self.stack_params.addWidget(page_susp)

        # Página Patas
        page_patas = QtWidgets.QWidget()
        lay_pp = QtWidgets.QHBoxLayout(page_patas)
        lay_pp.setContentsMargins(0, 0, 0, 0)
        lay_pp.setSpacing(6)

        lay_pp.addWidget(QtWidgets.QLabel("Altura patas:"))
        self.spin_altura_patas = VDO_DoubleSpinBox()
        self.spin_altura_patas.setRange(50.0, 200.0)
        self.spin_altura_patas.setValue(100.0)
        self.spin_altura_patas.setSuffix(" mm")
        self.spin_altura_patas.valueChanged.connect(self._on_param_base_changed)
        lay_pp.addWidget(self.spin_altura_patas)

        lay_pp.addWidget(QtWidgets.QLabel("Retranqueo:"))
        self.spin_offset_patas = VDO_DoubleSpinBox()
        self.spin_offset_patas.setRange(0.0, 100.0)
        self.spin_offset_patas.setValue(50.0)
        self.spin_offset_patas.setSuffix(" mm")
        self.spin_offset_patas.valueChanged.connect(self._on_param_base_changed)
        lay_pp.addWidget(self.spin_offset_patas)
        self.stack_params.addWidget(page_patas)

        layout_base.addWidget(self.stack_params)
        layout_raiz.addWidget(grupo_base)

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            }
            #frameMatriz {
                background-color: #161616;
                border: 1px solid #2d2d2d;
                border-radius: 6px;
            }
            .arquetipo-chip {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 9px;
                color: #cccccc;
            }
            .arquetipo-chip:hover {
                background-color: #383838;
                border-color: #007acc;
                color: #ffffff;
            }
            .btn-cara-horiz {
                background-color: #25282c;
                border: 1.5px solid #007acc;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            .btn-cara-horiz:!checked {
                background-color: #1a1a1a;
                border: 1px dashed #555555;
                color: #777777;
            }
            .btn-cara-vert {
                background-color: #25282c;
                border: 1.5px solid #007acc;
                border-radius: 4px;
                font-size: 8px;
                font-weight: bold;
                color: #ffffff;
                line-height: 10px;
            }
            .btn-cara-vert:!checked {
                background-color: #1a1a1a;
                border: 1px dashed #555555;
                color: #777777;
            }
            .btn-esquina {
                background-color: #262626;
                border: 1px solid #444444;
                border-radius: 5px;
            }
            .btn-esquina:hover {
                background-color: #333333;
                border-color: #0098ff;
            }
            .btn-esquina:pressed {
                background-color: #007acc;
            }
            .grupo-base {
                border: 1px solid #333333;
                border-radius: 5px;
                margin-top: 6px;
                padding-top: 8px;
                font-size: 9px;
                font-weight: bold;
                color: #888888;
            }
            .estrategia-btn {
                background-color: #282828;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                font-size: 10px;
                color: #cccccc;
            }
            .estrategia-btn:checked {
                background-color: #007acc;
                border-color: #0098ff;
                color: #ffffff;
                font-weight: bold;
            }
            .estrategia-btn:hover:!checked {
                background-color: #333333;
                color: #ffffff;
            }
            QComboBox {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
            }
            QComboBox:hover {
                border-color: #007acc;
            }
            QDoubleSpinBox {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 10px;
                color: #ffffff;
            }
            QDoubleSpinBox:focus {
                border-color: #007acc;
            }
        """)

    # ------------------------------------------------------------------
    # Manejadores de Eventos
    # ------------------------------------------------------------------
    def _on_cara_toggled(self, cara):
        if self._cargando:
            return
        if cara not in self._caras:
            return

        nueva_activa = not self._caras[cara]["activa"]
        self._caras[cara]["activa"] = nueva_activa

        self._actualizar_botones_caras()
        self.canvas.update_state(self._caras, self._encuentros, self._base)
        self._emitir_cambio()

    def _on_esquina_clicked(self, esquina):
        if self._cargando:
            return
        actual = self._encuentros.get(esquina, "tapa_domina")
        idx = (TIPOS_ENCUENTRO.index(actual) + 1) % len(TIPOS_ENCUENTRO)
        nuevo_tipo = TIPOS_ENCUENTRO[idx]

        self._encuentros[esquina] = nuevo_tipo
        self._actualizar_botones_esquinas()
        self.canvas.update_state(self._caras, self._encuentros, self._base)
        self._emitir_cambio()

    def _on_fondo_changed(self):
        if self._cargando:
            return
        tipo = self.combo_fondo.currentData()
        self._caras["fondo"]["tipo"] = tipo
        self._caras["fondo"]["activa"] = tipo != "abierto"
        self.canvas.update_state(self._caras, self._encuentros, self._base)
        self._emitir_cambio()

    def _on_estrategia_clicked(self, estrategia):
        if self._cargando:
            return
        self._base["estrategia"] = estrategia

        for k, btn in self.btn_estrategias.items():
            btn.blockSignals(True)
            btn.setChecked(k == estrategia)
            btn.blockSignals(False)

        idx_stack = {"zocalo": 0, "suspendido": 1, "patas": 2}.get(estrategia, 0)
        self.stack_params.setCurrentIndex(idx_stack)

        self._actualizar_valores_base_dict()
        self.canvas.update_state(self._caras, self._encuentros, self._base)
        self._emitir_cambio()

    def _on_param_base_changed(self):
        if self._cargando:
            return
        self._actualizar_valores_base_dict()
        self.canvas.update_state(self._caras, self._encuentros, self._base)
        self._emitir_cambio()

    def _actualizar_valores_base_dict(self):
        estrategia = self._base.get("estrategia", "zocalo")
        if estrategia == "zocalo":
            self._base["altura"] = float(self.spin_altura_zocalo.value())
            self._base["separacion_frente"] = float(self.spin_offset_zocalo.value())
        elif estrategia == "suspendido":
            self._base["altura"] = float(self.spin_despegue_piso.value())
            self._base["separacion_frente"] = 0.0
        elif estrategia == "patas":
            self._base["altura"] = float(self.spin_altura_patas.value())
            self._base["separacion_frente"] = float(self.spin_offset_patas.value())

    def _on_arquetipo_clicked(self, nombre):
        if self._cargando:
            return

        if nombre == "COCO":
            cfg = {
                "caras": {
                    "superior": {"activa": True, "tipo": "estructural"},
                    "inferior": {"activa": True, "tipo": "estructural"},
                    "izquierda": {"activa": True, "tipo": "estructural"},
                    "derecha": {"activa": True, "tipo": "estructural"},
                    "fondo": {"activa": True, "tipo": "ranurado_5mm"},
                },
                "encuentros": {
                    "superior_izq": "tapa_domina",
                    "superior_der": "tapa_domina",
                    "inferior_izq": "lateral_domina",
                    "inferior_der": "lateral_domina",
                },
                "base": {"estrategia": "zocalo", "altura": 100.0, "separacion_frente": 50.0},
            }
        elif nombre == "Mesa":
            cfg = {
                "caras": {
                    "superior": {"activa": True, "tipo": "estructural"},
                    "inferior": {"activa": False, "tipo": "estructural"},
                    "izquierda": {"activa": True, "tipo": "estructural"},
                    "derecha": {"activa": True, "tipo": "estructural"},
                    "fondo": {"activa": True, "tipo": "atornillado"},
                },
                "encuentros": {
                    "superior_izq": "tapa_domina",
                    "superior_der": "tapa_domina",
                    "inferior_izq": "lateral_domina",
                    "inferior_der": "lateral_domina",
                },
                "base": {"estrategia": "patas", "altura": 20.0, "separacion_frente": 0.0},
            }
        elif nombre == "Estante":
            cfg = {
                "caras": {
                    "superior": {"activa": False, "tipo": "estructural"},
                    "inferior": {"activa": True, "tipo": "estructural"},
                    "izquierda": {"activa": True, "tipo": "estructural"},
                    "derecha": {"activa": True, "tipo": "estructural"},
                    "fondo": {"activa": False, "tipo": "abierto"},
                },
                "encuentros": {
                    "superior_izq": "lateral_domina",
                    "superior_der": "lateral_domina",
                    "inferior_izq": "lateral_domina",
                    "inferior_der": "lateral_domina",
                },
                "base": {"estrategia": "zocalo", "altura": 80.0, "separacion_frente": 0.0},
            }
        elif nombre == "Aéreo":
            cfg = {
                "caras": {
                    "superior": {"activa": True, "tipo": "estructural"},
                    "inferior": {"activa": True, "tipo": "estructural"},
                    "izquierda": {"activa": True, "tipo": "estructural"},
                    "derecha": {"activa": True, "tipo": "estructural"},
                    "fondo": {"activa": True, "tipo": "ranurado_5mm"},
                },
                "encuentros": {
                    "superior_izq": "lateral_domina",
                    "superior_der": "lateral_domina",
                    "inferior_izq": "lateral_domina",
                    "inferior_der": "lateral_domina",
                },
                "base": {"estrategia": "suspendido", "altura": 300.0, "separacion_frente": 0.0},
            }
        else:
            return

        self.setChassisConfig(cfg)
        self._emitir_cambio()

    # ------------------------------------------------------------------
    # Sincronización Visual
    # ------------------------------------------------------------------
    def _actualizar_ui(self):
        self._actualizar_botones_caras()
        self._actualizar_botones_esquinas()
        self._actualizar_combo_fondo()
        self._actualizar_estrategia_base()
        self.canvas.update_state(self._caras, self._encuentros, self._base)

    def _actualizar_botones_caras(self):
        act_sup = self._caras["superior"]["activa"]
        self.btn_cara_sup.blockSignals(True)
        self.btn_cara_sup.setChecked(act_sup)
        self.btn_cara_sup.setText("── TAPA SUPERIOR · Activa ──" if act_sup else "┄ TAPA SUPERIOR · Ausente ┄")
        self.btn_cara_sup.blockSignals(False)

        act_inf = self._caras["inferior"]["activa"]
        self.btn_cara_inf.blockSignals(True)
        self.btn_cara_inf.setChecked(act_inf)
        self.btn_cara_inf.setText("── BASE INFERIOR · Activa ──" if act_inf else "┄ BASE INFERIOR · Ausente ┄")
        self.btn_cara_inf.blockSignals(False)

        act_izq = self._caras["izquierda"]["activa"]
        self.btn_cara_izq.blockSignals(True)
        self.btn_cara_izq.setChecked(act_izq)
        self.btn_cara_izq.blockSignals(False)

        act_der = self._caras["derecha"]["activa"]
        self.btn_cara_der.blockSignals(True)
        self.btn_cara_der.setChecked(act_der)
        self.btn_cara_der.blockSignals(False)

    def _actualizar_botones_esquinas(self):
        for e, btn in self.btn_esquina.items():
            tipo = self._encuentros.get(e, "tapa_domina")
            btn.setIcon(get_svg_icon(tipo, 22))
            btn.setToolTip(f"<b>{ENCUENTRO_LABELS.get(tipo, tipo)}</b><br>{ENCUENTRO_TOOLTIPS.get(tipo, '')}")

    def _actualizar_combo_fondo(self):
        tipo = self._caras["fondo"].get("tipo", "ranurado_5mm")
        idx = self.combo_fondo.findData(tipo)
        if idx >= 0:
            self.combo_fondo.blockSignals(True)
            self.combo_fondo.setCurrentIndex(idx)
            self.combo_fondo.blockSignals(False)

    def _actualizar_estrategia_base(self):
        estrategia = self._base.get("estrategia", "zocalo")
        for k, btn in self.btn_estrategias.items():
            btn.blockSignals(True)
            btn.setChecked(k == estrategia)
            btn.blockSignals(False)

        idx_stack = {"zocalo": 0, "suspendido": 1, "patas": 2}.get(estrategia, 0)
        self.stack_params.setCurrentIndex(idx_stack)

        self.spin_altura_zocalo.blockSignals(True)
        self.spin_offset_zocalo.blockSignals(True)
        self.spin_despegue_piso.blockSignals(True)
        self.spin_altura_patas.blockSignals(True)
        self.spin_offset_patas.blockSignals(True)

        if estrategia == "zocalo":
            self.spin_altura_zocalo.setValue(float(self._base.get("altura", 100.0)))
            self.spin_offset_zocalo.setValue(float(self._base.get("separacion_frente", 50.0)))
        elif estrategia == "suspendido":
            self.spin_despegue_piso.setValue(float(self._base.get("altura", 300.0)))
        elif estrategia == "patas":
            self.spin_altura_patas.setValue(float(self._base.get("altura", 100.0)))
            self.spin_offset_patas.setValue(float(self._base.get("separacion_frente", 50.0)))

        self.spin_altura_zocalo.blockSignals(False)
        self.spin_offset_zocalo.blockSignals(False)
        self.spin_despegue_piso.blockSignals(False)
        self.spin_altura_patas.blockSignals(False)
        self.spin_offset_patas.blockSignals(False)

    def _emitir_cambio(self):
        if not self._cargando:
            self.sigChassisChanged.emit(self.getChassisConfig())

    # ------------------------------------------------------------------
    # Contrato Público API (Capa 1)
    # ------------------------------------------------------------------
    def setChassisConfig(self, cfg: dict):
        """Carga la configuración sin emitir señales redundantes."""
        if not isinstance(cfg, dict):
            return

        self._cargando = True
        try:
            # Caras
            caras_cfg = cfg.get("caras", {})
            for c in CARAS:
                if c in caras_cfg:
                    self._caras[c] = dict(caras_cfg[c])

            # Encuentros
            enc_cfg = cfg.get("encuentros", {})
            for e in ENCUENTROS:
                if e in enc_cfg:
                    self._encuentros[e] = enc_cfg[e]

            # Base
            base_cfg = cfg.get("base", {})
            if base_cfg:
                self._base.update(base_cfg)

            self._actualizar_ui()
        finally:
            self._cargando = False

    def getChassisConfig(self) -> dict:
        """Devuelve el diccionario canónico de Capa 1 para el chasis."""
        return {
            "caras": {
                c: dict(self._caras[c]) for c in CARAS
            },
            "encuentros": {
                e: self._encuentros[e] for e in ENCUENTROS
            },
            "base": {
                "estrategia": self._base.get("estrategia", "zocalo"),
                "altura": float(self._base.get("altura", 100.0)),
                "separacion_frente": float(self._base.get("separacion_frente", 50.0)),
            }
        }

    # Aliases de compatibilidad y estilo snake_case
    set_chassis_config = setChassisConfig
    get_chassis_config = getChassisConfig


# ----------------------------------------------------------------------
# Ejecución Standalone para Validación Visual Directa
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    # Paleta oscura global coherente
    paleta = QtGui.QPalette()
    paleta.setColor(QtGui.QPalette.Window, QtGui.QColor("#1e1e1e"))
    paleta.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#e0e0e0"))
    paleta.setColor(QtGui.QPalette.Base, QtGui.QColor("#252525"))
    paleta.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#1e1e1e"))
    paleta.setColor(QtGui.QPalette.Text, QtGui.QColor("#e0e0e0"))
    paleta.setColor(QtGui.QPalette.Button, QtGui.QColor("#2b2b2b"))
    paleta.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#ffffff"))
    paleta.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#007acc"))
    paleta.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
    app.setPalette(paleta)

    ventana = QtWidgets.QMainWindow()
    ventana.setWindowTitle("VDO Chassis Controller - Corte Transversal Interactivo 2D")
    ventana.setMinimumSize(360, 480)

    widget = VDOChassisControllerWidget()

    def on_change(cfg):
        activas = [c for c, d in cfg["caras"].items() if d.get("activa")]
        print(f"[VDO Chassis Event] Caras activas: {activas} | Encuentros: {cfg['encuentros']} | Base: {cfg['base']['estrategia']}")

    widget.sigChassisChanged.connect(on_change)

    ventana.setCentralWidget(widget)
    ventana.show()
    exec_func = getattr(app, "exec", getattr(app, "exec_", None))
    sys.exit(exec_func())
