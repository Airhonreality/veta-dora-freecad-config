# -*- coding: utf-8 -*-
# =====================================================================
# vdo_ui_start_page.py
# Tarjeta "Mueble VDO" en la pagina de Inicio de FreeCAD.
#
# POR QUE ESTO ES INGENIERIA INVERSA Y NO API:
# Las tarjetas de "Crear nuevo" de la pagina de Inicio estan HARDCODEADAS
# en C++ (StartGui::StartView::configureNewFileButtons): Cuerpo
# parametrico, Ensamblaje, Dibujo 2D, BIM/Arquitectura, Archivo vacio y
# Abrir archivo. No hay parametro de preferencias ni API para anadir una,
# asi que un workbench externo NUNCA puede aparecer ahi por el camino
# oficial. Lo unico publico es el arbol de widgets Qt, y por ahi se
# inyecta la tarjeta.
#
# Estructura verificada en FreeCAD 1.1.4 (rev 45040):
#   StartGui::StartView
#     └ QWidget objectName="CreateNewRow"   (StartGui::FlowLayout)
#         └ QPushButton objectName="newFileButton"  x6
#             └ QHBoxLayout(9,9,18,9), spacing 9
#                 ├ QLabel con pixmap (icono)
#                 └ QLabel negrita (titulo) + QLabel (descripcion)
# El objectName "newFileButton" es lo que hace que la hoja de estilos de
# FreeCAD pinte la tarjeta; por eso se reutiliza tal cual y la marca
# propia viaja en una propiedad dinamica.
#
# Si una version futura renombra esos widgets no se encuentra la fila y
# no pasa nada: la tarjeta no aparece y el workbench sigue estando en el
# selector de bancos de trabajo. Nunca se propaga una excepcion a FreeCAD.
# =====================================================================

import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:  # FreeCADCmd
    Gui = None

from VDO.ui.vdo_ui_qt_compat import QtCore, QtGui, QtWidgets

TITULO = "Mueble VDO"
DESCRIPCION = "Crea un proyecto de carpintería paramétrica"
ICONO = "vdo_coco.svg"

_FILA = "CreateNewRow"          # QWidget que agrupa las tarjetas
_TARJETA = "newFileButton"      # objectName que estiliza cada tarjeta
_MARCA = "vdo_tarjeta_inicio"   # propiedad dinamica: "esta es la nuestra"

# La pagina de Inicio se construye al final del arranque, despues de que
# FreeCAD ejecute los InitGui.py de los Mod. Por eso la instalacion
# reintenta en lugar de darse por vencida al primer intento.
_INTENTOS = 40
_DEMORA_MS = 500


# ---------------------------------------------------------------------
# Localizacion de los widgets de la pagina de Inicio
# ---------------------------------------------------------------------

def _fila_crear_nuevo():
    """QWidget con las tarjetas de 'Crear nuevo', o None si no esta."""
    if Gui is None:
        return None
    mw = Gui.getMainWindow()
    if mw is None:
        return None
    for widget in mw.findChildren(QtWidgets.QWidget, _FILA):
        if widget.layout() is not None:
            return widget
    return None


def _tarjetas(fila):
    """Botones actualmente en la fila, en orden."""
    layout = fila.layout()
    encontrados = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget() if item is not None else None
        if widget is not None:
            encontrados.append(widget)
    return encontrados


def _ya_instalada(fila):
    return any(w.property(_MARCA) for w in _tarjetas(fila))


# ---------------------------------------------------------------------
# Construccion de la tarjeta
# ---------------------------------------------------------------------

def _lado_icono(modelo):
    """Tamano del icono copiado de una tarjeta nativa (device-independent)."""
    if modelo is None:
        return 32
    for etiqueta in modelo.findChildren(QtWidgets.QLabel):
        pixmap = etiqueta.pixmap()
        if pixmap is None or pixmap.isNull():
            continue
        dpr = pixmap.devicePixelRatio() or 1.0
        return max(1, int(round(max(pixmap.width(), pixmap.height()) / dpr)))
    return 32


def _fuentes(modelo):
    """(fuente_titulo, fuente_descripcion) de una tarjeta nativa."""
    if modelo is not None:
        textos = [e for e in modelo.findChildren(QtWidgets.QLabel) if e.text()]
        if len(textos) >= 2:
            return textos[0].font(), textos[1].font()
    titulo = QtGui.QFont()
    titulo.setBold(True)
    return titulo, QtGui.QFont()


class _TarjetaVDO(QtWidgets.QPushButton):
    """Tarjeta que se mide a si misma copiando a sus vecinas nativas.

    StartGui::NewFileButton reimplementa minimumSizeHint() en C++ (264x72
    aqui) y el FlowLayout da a cada tarjeta exactamente esa medida. Copiar
    el numero al construir no sirve: cuando se instala la tarjeta, la
    pagina de Inicio todavia no esta dimensionada y las vecinas responden
    con su medida provisional (106x72), que es justo como salia la tarjeta
    VDO: estrecha. Preguntandoselo en cada consulta de Qt, la respuesta
    llega ya con la pagina montada y las siete tarjetas miden igual.
    """

    def minimumSizeHint(self):
        propia = super().minimumSizeHint()
        try:
            padre = self.parentWidget()
            layout = padre.layout() if padre is not None else None
            for i in range(layout.count() if layout else 0):
                item = layout.itemAt(i)
                vecina = item.widget() if item is not None else None
                if (vecina is None or vecina is self
                        or not isinstance(vecina, QtWidgets.QAbstractButton)):
                    continue
                ajena = vecina.minimumSizeHint()
                return QtCore.QSize(max(propia.width(), ajena.width()),
                                    max(propia.height(), ajena.height()))
        except Exception:
            pass
        return propia


def _construir_tarjeta(fila, modelo):
    boton = _TarjetaVDO(fila)
    boton.setObjectName(_TARJETA)
    boton.setProperty(_MARCA, True)
    boton.setToolTip(DESCRIPCION)
    boton.setCursor(QtCore.Qt.PointingHandCursor)

    caja = QtWidgets.QHBoxLayout(boton)
    caja.setContentsMargins(9, 9, 18, 9)
    caja.setSpacing(9)

    lado = _lado_icono(modelo)
    from VDO._paths import get_icon_path
    icono = QtWidgets.QLabel(boton)
    icono.setPixmap(QtGui.QIcon(get_icon_path(ICONO)).pixmap(lado, lado))
    caja.addWidget(icono)

    fuente_titulo, fuente_desc = _fuentes(modelo)
    textos = QtWidgets.QVBoxLayout()
    textos.setContentsMargins(0, 0, 0, 0)
    textos.setSpacing(0)
    etiqueta_titulo = QtWidgets.QLabel(TITULO, boton)
    etiqueta_titulo.setFont(fuente_titulo)
    etiqueta_desc = QtWidgets.QLabel(DESCRIPCION, boton)
    etiqueta_desc.setFont(fuente_desc)
    # Las tarjetas nativas parten la descripcion en dos lineas; sin esto la
    # nuestra se queda cortada a lo ancho de la tarjeta.
    etiqueta_desc.setWordWrap(True)
    textos.addWidget(etiqueta_titulo)
    textos.addWidget(etiqueta_desc)
    caja.addLayout(textos)
    caja.addStretch(1)

    if modelo is not None:
        # El ancho/alto los resuelve _TarjetaVDO.minimumSizeHint(); aqui
        # solo se copia como crece la tarjeta dentro de la fila.
        boton.setSizePolicy(modelo.sizePolicy())

    boton.clicked.connect(_nuevo_proyecto)
    return boton


def _documento_reutilizable():
    """True si el documento activo esta vacio y sin guardar.

    Pulsar la tarjeta con la pagina de Inicio recien abierta no debe dejar
    dos documentos: el que crea Activated() del workbench al entrar y el
    que pediria la tarjeta.
    """
    doc = App.ActiveDocument
    return doc is not None and not doc.Objects and not doc.FileName


def _nuevo_proyecto():
    """Igual que las tarjetas nativas: entra al banco y abre un documento."""
    try:
        Gui.activateWorkbench("VDO_Workbench")
        if not _documento_reutilizable():
            Gui.runCommand("VDO_NuevoProyecto")
    except Exception as exc:
        App.Console.PrintError(
            "[VDO] No se pudo crear el proyecto desde la pagina de "
            "Inicio: %s\n" % exc)


# ---------------------------------------------------------------------
# Instalacion
# ---------------------------------------------------------------------

def _insertar_primera(fila, boton):
    """Coloca la tarjeta al principio de la fila.

    StartGui::FlowLayout solo sabe anadir al final (es el FlowLayout de
    los ejemplos de Qt), asi que para abrir hueco hay que vaciar la fila y
    volver a montarla. Si algo falla a mitad se restaura el orden original
    y la tarjeta se anade al final, que es peor estetica pero nunca deja
    la pagina de Inicio rota.
    """
    layout = fila.layout()
    previas = _tarjetas(fila)
    try:
        while layout.count():
            layout.takeAt(0)
        layout.addWidget(boton)
        for widget in previas:
            layout.addWidget(widget)
    except Exception:
        for widget in previas:
            if layout.indexOf(widget) < 0:
                layout.addWidget(widget)
        if layout.indexOf(boton) < 0:
            layout.addWidget(boton)
        raise
    fila.updateGeometry()


def instalar_tarjeta_inicio(intentos=_INTENTOS):
    """Anade la tarjeta VDO a la pagina de Inicio. Idempotente.

    Reintenta mientras la pagina no exista todavia (arranque en curso).
    Devuelve True si la tarjeta quedo puesta.
    """
    if Gui is None or not App.GuiUp:
        return False
    try:
        fila = _fila_crear_nuevo()
        if fila is None:
            if intentos > 0:
                QtCore.QTimer.singleShot(
                    _DEMORA_MS, lambda: instalar_tarjeta_inicio(intentos - 1))
            return False
        if _ya_instalada(fila):
            return True

        # La fila se crea vacia y las tarjetas nativas se anaden despues.
        # Sin ninguna a la vista no hay de donde copiar icono, fuentes ni
        # medidas, asi que se espera al siguiente intento.
        modelos = [w for w in _tarjetas(fila)
                   if isinstance(w, QtWidgets.QAbstractButton)]
        if not modelos:
            if intentos > 0:
                QtCore.QTimer.singleShot(
                    _DEMORA_MS, lambda: instalar_tarjeta_inicio(intentos - 1))
            return False

        boton = _construir_tarjeta(fila, modelos[0])
        try:
            _insertar_primera(fila, boton)
        except Exception:
            pass  # ya se quedo al final; el orden es lo de menos
        boton.show()
        App.Console.PrintLog("[VDO] Tarjeta anadida a la pagina de Inicio.\n")
        return True
    except Exception:
        import traceback
        App.Console.PrintLog(
            "[VDO] No se pudo anadir la tarjeta a la pagina de Inicio:\n%s\n"
            % traceback.format_exc())
        return False
