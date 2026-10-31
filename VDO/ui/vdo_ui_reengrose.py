# -*- coding: utf-8 -*-
"""Editor Qt del modificador universal de bordes de reengrose."""

from PySide import QtCore, QtGui, QtWidgets

import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.ui.vdo_ui_qt_compat import VDO_DoubleSpinBox


LABEL_BORDE = {
    "frente": "Frente",
    "fondo": "Fondo",
    "izquierda": "Izquierda",
    "derecha": "Derecha",
}

LABEL_ESQUINA = {
    "frente_izquierda": "Frente izq.",
    "frente_derecha": "Frente der.",
    "fondo_izquierda": "Fondo izq.",
    "fondo_derecha": "Fondo der.",
}

OPCIONES_ESQUINA = (
    ("A tope lateral (Vertical domina)", "vertical_domina"),
    ("A tope frontal (Horizontal domina)", "horizontal_domina"),
    ("Inglete 45°", "inglete_45"),
    ("Marco interior", "marco_interior"),
)

COLOR_ESQUINA = {
    "vertical_domina": "#00b894",
    "horizontal_domina": "#e67e22",
    "inglete_45": "#9b59b6",
    "marco_interior": "#7f8c8d",
}


class VDOBoardPreview(QtWidgets.QWidget):
    """Vista compacta del tablero con bordes activos y tipo de esquina."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 150)
        self.setMaximumSize(260, 170)
        self._bordes = set()
        self._esquinas = {}

    def set_estado(self, bordes, esquinas):
        self._bordes = set(bordes or [])
        self._esquinas = dict(esquinas or {})
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        ancho = self.width()
        alto = self.height()
        margen = 24
        x0, y0 = margen, margen
        x1, y1 = ancho - margen, alto - margen
        if x1 <= x0 or y1 <= y0:
            return

        painter.setBrush(QtGui.QBrush(QtGui.QColor("#1e1e1e")))
        painter.setPen(QtGui.QPen(QtGui.QColor("#555555"), 1))
        painter.drawRoundedRect(x0, y0, x1 - x0, y1 - y0, 6, 6)

        grosor = 9
        activo = QtGui.QColor("#007acc")
        inactivo = QtGui.QColor("#3a3a3a")

        def color_borde(borde):
            return activo if borde in self._bordes else inactivo

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(color_borde("frente")))
        painter.drawRect(x0, y0, x1 - x0, grosor)
        painter.setBrush(QtGui.QBrush(color_borde("fondo")))
        painter.drawRect(x0, y1 - grosor, x1 - x0, grosor)
        painter.setBrush(QtGui.QBrush(color_borde("izquierda")))
        painter.drawRect(x0, y0, grosor, y1 - y0)
        painter.setBrush(QtGui.QBrush(color_borde("derecha")))
        painter.drawRect(x1 - grosor, y0, grosor, y1 - y0)

        posiciones = {
            "frente_izquierda": (x0 + grosor, y0 + grosor),
            "frente_derecha": (x1 - grosor, y0 + grosor),
            "fondo_izquierda": (x0 + grosor, y1 - grosor),
            "fondo_derecha": (x1 - grosor, y1 - grosor),
        }
        lado = 14
        for esquina, (cx, cy) in posiciones.items():
            tipo = self._esquinas.get(esquina)
            color = QtGui.QColor(COLOR_ESQUINA.get(tipo, "#444444"))
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(QtGui.QColor("#111111"), 1))
            painter.drawRect(cx - lado / 2.0, cy - lado / 2.0, lado, lado)
            if tipo == "inglete_45":
                painter.setPen(QtGui.QPen(QtGui.QColor("#111111"), 1))
                painter.drawLine(cx - lado / 2.0, cy + lado / 2.0,
                                 cx + lado / 2.0, cy - lado / 2.0)
            elif tipo == "marco_interior":
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#1e1e1e")))
                painter.setPen(QtGui.QPen(QtGui.QColor("#bdc3c7"), 1))
                painter.drawRect(cx - lado / 4.0, cy - lado / 4.0,
                                 lado / 2.0, lado / 2.0)

        painter.setPen(QtGui.QPen(QtGui.QColor("#8a8a8a"), 1))
        painter.drawText(
            QtCore.QRectF(x0, y0, x1 - x0, y1 - y0),
            QtCore.Qt.AlignCenter, "Tablero")
        painter.end()


class ReengroseBorderEditor(QtWidgets.QGroupBox):
    """Seccion Figma-like: bordes, distancia al canto, largos y esquinas."""

    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Reengrose / Refuerzo", parent)
        self._cargando = False
        self._construir()
        self._conectar()
        self._actualizar_estado()

    # -----------------------------------------------------------------
    # Construccion
    # -----------------------------------------------------------------
    def _spin(self, valor=70.0, maximo=5000.0):
        spin = VDO_DoubleSpinBox()
        spin.setRange(0.0, maximo)
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        spin.setValue(valor)
        return spin

    def _construir(self):
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.chk_activo = QtWidgets.QCheckBox(
            "Activar Reengrose en esta pieza")
        self.chk_activo.setToolTip(
            "Activa el modificador universal de bordes del tablero.")
        grid.addWidget(self.chk_activo, 0, 0, 1, 4)

        fila = QtWidgets.QHBoxLayout()
        self.btn_all = QtWidgets.QPushButton("All")
        self.btn_all.setCheckable(True)
        self.btn_all.setToolTip(
            "Enciende o apaga los cuatro bordes a la vez.")
        fila.addWidget(self.btn_all)
        self.btn_borde = {}
        for borde in VDO_RE.BORDES_2D:
            btn = QtWidgets.QToolButton()
            btn.setText(LABEL_BORDE[borde])
            btn.setCheckable(True)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.setToolTip(
                f"Activa una tira de refuerzo en el borde {borde}.")
            self.btn_borde[borde] = btn
            fila.addWidget(btn)
        fila.addStretch()
        grid.addLayout(fila, 1, 0, 1, 4)

        fila_medidas = QtWidgets.QHBoxLayout()
        self.chk_uniforme = QtWidgets.QCheckBox("🔗 Uniforme")
        self.chk_uniforme.setChecked(True)
        self.chk_uniforme.setToolTip(
            "Encadenado: mismo ancho, distancia al canto y largo de tira "
            "para todos los bordes. Desmarcalo para dar medidas "
            "independientes.")
        fila_medidas.addWidget(self.chk_uniforme)
        fila_medidas.addSpacing(10)
        fila_medidas.addWidget(QtWidgets.QLabel("Ancho:"))
        self.spin_ancho = self._spin(70.0)
        self.spin_ancho.setToolTip(
            "Ancho de la tira. 70 mm es habitual para bisagras; "
            "100 mm para zocalos.")
        fila_medidas.addWidget(self.spin_ancho)
        fila_medidas.addWidget(QtWidgets.QLabel("Distancia:"))
        self.spin_offset = self._spin(0.0, 500.0)
        self.spin_offset.setToolTip(
            "Distancia desde el canto del tablero hacia adentro.")
        fila_medidas.addWidget(self.spin_offset)
        fila_medidas.addWidget(QtWidgets.QLabel("Espesor:"))
        self.spin_espesor = self._spin(0.0, 100.0)
        self.spin_espesor.setSpecialValueText("Auto")
        self.spin_espesor.setToolTip(
            "Espesor de la tira. Auto usa el espesor del tablero madre.")
        fila_medidas.addWidget(self.spin_espesor)
        fila_medidas.addStretch()
        grid.addLayout(fila_medidas, 2, 0, 1, 4)

        fila_largo = QtWidgets.QHBoxLayout()
        fila_largo.addWidget(QtWidgets.QLabel("Largo de tira:"))
        self.combo_largo_tira = QtWidgets.QComboBox()
        self.combo_largo_tira.addItem(
            "Marco interior (hace tope)", "marco_interior")
        self.combo_largo_tira.addItem(
            "Punta a punta (largo completo)", "punta_a_punta")
        self.combo_largo_tira.setToolTip(
            "Marco interior recorta la tira contra las vecinas; "
            "punta a punta conserva el largo total del borde.")
        fila_largo.addWidget(self.combo_largo_tira, 1)
        grid.addLayout(fila_largo, 3, 0, 1, 4)

        self.preview = VDOBoardPreview()
        caja_preview = QtWidgets.QVBoxLayout()
        caja_preview.setContentsMargins(0, 0, 0, 0)
        caja_preview.addWidget(self.preview)
        leyenda = QtWidgets.QLabel(
            '<span style="color:#00b894">■</span> Vertical &nbsp;'
            '<span style="color:#e67e22">■</span> Horizontal &nbsp;'
            '<span style="color:#9b59b6">■</span> Inglete &nbsp;'
            '<span style="color:#7f8c8d">■</span> Marco')
        leyenda.setTextFormat(QtCore.Qt.RichText)
        leyenda.setStyleSheet("font-size: 10px;")
        caja_preview.addWidget(leyenda)

        panel = QtWidgets.QHBoxLayout()
        panel.addLayout(caja_preview, 0)
        panel.addLayout(self._construir_rejilla_esquinas(), 1)
        grid.addLayout(panel, 4, 0, 1, 4)

        self.chk_sync_esquinas = QtWidgets.QCheckBox(
            "🔗 Sincronizar todas las esquinas")
        self.chk_sync_esquinas.setChecked(True)
        self.chk_sync_esquinas.setToolTip(
            "Activo: al cambiar una esquina se aplica el mismo tipo a las "
            "cuatro. Desactivado: cada esquina se configura por separado.")
        grid.addWidget(self.chk_sync_esquinas, 5, 0, 1, 4)

        self.widget_custom = self._construir_tabla_bordes()
        grid.addWidget(self.widget_custom, 6, 0, 1, 4)

        self.combo_fabricacion = QtWidgets.QComboBox()
        self.combo_fabricacion.addItem(
            "Pacha (bloque unificado)", "pacha")
        self.combo_fabricacion.addItem(
            "Independiente (cantear aparte)", "independiente")
        self.combo_fabricacion.setToolTip(
            "Fabricacion de las tiras y su canteado.")
        grid.addWidget(QtWidgets.QLabel("Fabricación:"), 7, 0)
        grid.addWidget(self.combo_fabricacion, 7, 1, 1, 3)

        self.combo_choque = QtWidgets.QComboBox()
        self.combo_choque.addItem("Retroceso (corte recto)", "retroceso")
        self.combo_choque.addItem("Mocheo / rebaje", "mocheo")
        self.combo_choque.addItem(
            "Interrumpir tira", "interrumpir_tira")
        self.combo_choque.setToolTip(
            "Comportamiento de la tira al chocar con el nucleo.")
        grid.addWidget(QtWidgets.QLabel("Choque núcleo:"), 8, 0)
        grid.addWidget(self.combo_choque, 8, 1, 1, 3)

        self.combo_cara = QtWidgets.QComboBox()
        self.combo_cara.addItem("Cara A (+)", "cara_a")
        self.combo_cara.addItem("Cara B (−)", "cara_b")
        self.combo_cara.addItem("Ambas caras", "ambos")
        self.combo_cara.setToolTip(
            "Cara del tablero donde se pegan las tiras.")
        grid.addWidget(QtWidgets.QLabel("Cara de pegado:"), 9, 0)
        grid.addWidget(self.combo_cara, 9, 1, 1, 3)

        self.lbl_resumen = QtWidgets.QLabel("Sin reengrose.")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setStyleSheet(
            "QLabel { background: #2b2b2b; color: #e0e0e0; padding: 5px; "
            "border: 1px solid #4a4a4a; }")
        grid.addWidget(self.lbl_resumen, 10, 0, 1, 4)

        self._aplicar_estilo_botones()

    def _construir_rejilla_esquinas(self):
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        titulo = QtWidgets.QLabel("Encuentro de esquinas")
        titulo.setStyleSheet("font-weight: bold;")
        grid.addWidget(titulo, 0, 0, 1, 2)
        posiciones = {
            "frente_izquierda": (1, 0),
            "frente_derecha": (1, 1),
            "fondo_izquierda": (2, 0),
            "fondo_derecha": (2, 1),
        }
        self.combo_esquina = {}
        for esquina in VDO_RE.ESQUINAS_2D:
            fila, col = posiciones[esquina]
            caja = QtWidgets.QVBoxLayout()
            caja.setSpacing(1)
            etiqueta = QtWidgets.QLabel(LABEL_ESQUINA[esquina])
            etiqueta.setStyleSheet("font-size: 11px;")
            combo = QtWidgets.QComboBox()
            for texto, dato in OPCIONES_ESQUINA:
                combo.addItem(texto, dato)
            combo.setToolTip(
                "Como se resuelve esta esquina entre los dos bordes "
                "que se cruzan.")
            self.combo_esquina[esquina] = combo
            caja.addWidget(etiqueta)
            caja.addWidget(combo)
            grid.addLayout(caja, fila, col)
        # Alias retrocompatible para paneles que usaban un combo global.
        self.combo_esquinas = self.combo_esquina["frente_izquierda"]
        return grid

    def _construir_tabla_bordes(self):
        contenedor = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(contenedor)
        grid.setContentsMargins(18, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)
        self.spin_ancho_borde = {}
        self.spin_offset_borde = {}
        grid.addWidget(QtWidgets.QLabel(""), 0, 0)
        for col, borde in enumerate(VDO_RE.BORDES_2D, start=1):
            etiqueta = QtWidgets.QLabel(LABEL_BORDE[borde])
            etiqueta.setStyleSheet(
                "font-weight: bold; font-size: 11px;")
            grid.addWidget(etiqueta, 0, col)
            ancho = self._spin(70.0)
            ancho.setMaximumWidth(96)
            offset = self._spin(0.0, 500.0)
            offset.setMaximumWidth(96)
            self.spin_ancho_borde[borde] = ancho
            self.spin_offset_borde[borde] = offset
            grid.addWidget(ancho, 1, col)
            grid.addWidget(offset, 2, col)
        grid.addWidget(QtWidgets.QLabel("ancho"), 1, 0)
        grid.addWidget(QtWidgets.QLabel("dist."), 2, 0)
        contenedor.setVisible(False)
        return contenedor

    def _aplicar_estilo_botones(self):
        """QSS para los botones checkables de bordes."""
        estilo = """
        QPushButton, QToolButton {
            background-color: #333333;
            color: #e0e0e0;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 5px 10px;
            font-weight: bold;
        }
        QPushButton:hover, QToolButton:hover {
            background-color: #444444;
            border-color: #777777;
        }
        QPushButton:checked, QToolButton:checked {
            background-color: #007acc;
            color: #ffffff;
            border: 1px solid #0098ff;
        }
        QPushButton:disabled, QToolButton:disabled {
            background-color: #222222;
            color: #777777;
            border: 1px solid #333333;
        }
        """
        self.btn_all.setStyleSheet(estilo)
        for btn in self.btn_borde.values():
            btn.setStyleSheet(estilo)

    def _conectar(self):
        self.chk_activo.toggled.connect(self._on_activo)
        self.btn_all.clicked.connect(self._on_all)
        for borde, btn in self.btn_borde.items():
            btn.toggled.connect(
                lambda estado, b=borde: self._on_borde(b, estado))
        self.chk_uniforme.toggled.connect(self._on_uniforme)
        self.spin_ancho.valueChanged.connect(self._on_uniforme_spin)
        self.spin_offset.valueChanged.connect(self._on_uniforme_spin)
        self.spin_espesor.valueChanged.connect(self._on_uniforme_spin)
        self.combo_largo_tira.currentIndexChanged.connect(
            self._on_uniforme_spin)
        for borde in VDO_RE.BORDES_2D:
            self.spin_ancho_borde[borde].valueChanged.connect(
                self._on_custom_spin)
            self.spin_offset_borde[borde].valueChanged.connect(
                self._on_custom_spin)
        for esquina, combo in self.combo_esquina.items():
            combo.currentIndexChanged.connect(
                lambda _idx, e=esquina: self._on_esquina_changed(e))
        self.chk_sync_esquinas.toggled.connect(self._on_sync_toggled)
        self.combo_fabricacion.currentIndexChanged.connect(self._emitir)
        self.combo_choque.currentIndexChanged.connect(self._emitir)
        self.combo_cara.currentIndexChanged.connect(self._emitir)

    # -----------------------------------------------------------------
    # Estado y lectura
    # -----------------------------------------------------------------
    def _emitir(self, *args):
        if self._cargando:
            return
        self._actualizar_preview()
        self._actualizar_resumen()
        self.changed.emit()

    def _bordes_activos(self):
        return [b for b in VDO_RE.BORDES_2D
                if self.btn_borde[b].isChecked()]

    def _esquinas_actuales(self):
        return {
            esquina: combo.currentData()
            for esquina, combo in self.combo_esquina.items()
        }

    def _on_activo(self, activo):
        if self._cargando:
            return
        if activo and not self._bordes_activos():
            self._cargando = True
            self.btn_borde["frente"].setChecked(True)
            self._cargando = False
        self._actualizar_estado()
        self._emitir()

    def _on_borde(self, borde, estado):
        if self._cargando:
            return
        self._actualizar_estado_all()
        self._emitir()

    def _actualizar_estado_all(self):
        """Sincroniza el botón [All] con el estado de los 4 bordes."""
        if self._cargando:
            return
        todos = all(self.btn_borde[b].isChecked()
                    for b in VDO_RE.BORDES_2D)
        self.btn_all.blockSignals(True)
        self.btn_all.setChecked(todos)
        self.btn_all.blockSignals(False)

    def _on_all(self):
        objetivo = len(self._bordes_activos()) < len(VDO_RE.BORDES_2D)
        self._cargando = True
        self.btn_all.blockSignals(True)
        self.btn_all.setChecked(objetivo)
        self.btn_all.blockSignals(False)
        for btn in self.btn_borde.values():
            btn.blockSignals(True)
            btn.setChecked(objetivo)
            btn.blockSignals(False)
        self._cargando = False
        self._emitir()

    def _on_uniforme(self, uniforme):
        if self._cargando:
            return
        if uniforme:
            self._cargando = True
            for borde in VDO_RE.BORDES_2D:
                self.spin_ancho_borde[borde].setValue(
                    self.spin_ancho.value())
                self.spin_offset_borde[borde].setValue(
                    self.spin_offset.value())
            self._cargando = False
        self._actualizar_estado()
        self._emitir()

    def _on_uniforme_spin(self, *args):
        if self._cargando:
            return
        if self.chk_uniforme.isChecked():
            self._cargando = True
            for borde in VDO_RE.BORDES_2D:
                self.spin_ancho_borde[borde].setValue(
                    self.spin_ancho.value())
                self.spin_offset_borde[borde].setValue(
                    self.spin_offset.value())
            self._cargando = False
        self._emitir()

    def _on_custom_spin(self, *args):
        if self._cargando or self.chk_uniforme.isChecked():
            return
        self._emitir()

    def _on_esquina_changed(self, esquina):
        if self._cargando:
            return
        if self.chk_sync_esquinas.isChecked():
            valor = self.combo_esquina[esquina].currentData()
            self._cargando = True
            for otra, combo in self.combo_esquina.items():
                if otra == esquina:
                    continue
                combo.blockSignals(True)
                self._set_combo_data(combo, valor)
                combo.blockSignals(False)
            self._cargando = False
        self._emitir()

    def _on_sync_toggled(self, activo):
        if self._cargando:
            return
        if activo:
            valor = self.combo_esquina["frente_izquierda"].currentData()
            self._cargando = True
            for combo in self.combo_esquina.values():
                combo.blockSignals(True)
                self._set_combo_data(combo, valor)
                combo.blockSignals(False)
            self._cargando = False
        self._emitir()

    def _actualizar_estado(self):
        activo = self.chk_activo.isChecked()
        self.btn_all.setEnabled(activo)
        for btn in self.btn_borde.values():
            btn.setEnabled(activo)
        self.chk_uniforme.setEnabled(activo)
        self.spin_ancho.setEnabled(activo and self.chk_uniforme.isChecked())
        self.spin_offset.setEnabled(
            activo and self.chk_uniforme.isChecked())
        self.spin_espesor.setEnabled(activo)
        self.combo_largo_tira.setEnabled(activo)
        self.widget_custom.setVisible(
            activo and not self.chk_uniforme.isChecked())
        self.chk_sync_esquinas.setEnabled(activo)
        for combo in self.combo_esquina.values():
            combo.setEnabled(activo)
        for combo in (self.combo_fabricacion, self.combo_choque,
                      self.combo_cara):
            combo.setEnabled(activo)
        self._actualizar_preview()
        self._actualizar_resumen()

    def _actualizar_preview(self):
        activos = self._bordes_activos() if self.chk_activo.isChecked() else []
        self.preview.set_estado(activos, self._esquinas_actuales())

    def _actualizar_resumen(self):
        if not self.chk_activo.isChecked():
            self.lbl_resumen.setText("Sin reengrose.")
            return
        activos = self._bordes_activos()
        if not activos:
            self.lbl_resumen.setText("Sin bordes activos.")
            return
        if self.chk_uniforme.isChecked():
            anchos = {f"{self.spin_ancho.value():.1f}"}
            offsets = {f"{self.spin_offset.value():.1f}"}
        else:
            anchos = {
                f"{self.spin_ancho_borde[b].value():.1f}"
                for b in activos}
            offsets = {
                f"{self.spin_offset_borde[b].value():.1f}"
                for b in activos}
        tipos = set(self._esquinas_actuales().values())
        if len(tipos) == 1:
            texto_esquinas = self.combo_esquina[
                "frente_izquierda"].currentText()
        else:
            texto_esquinas = "esquinas mixtas"
        ancho = "/".join(sorted(anchos))
        offset = "/".join(sorted(offsets))
        largo = self.combo_largo_tira.currentText()
        nombre = ", ".join(LABEL_BORDE[b] for b in activos)
        self.lbl_resumen.setText(
            f"{len(activos)} bordes ({nombre}) · ancho {ancho} mm · "
            f"distancia al canto {offset} mm · {largo} · "
            f"{texto_esquinas} · "
            f"{self.combo_fabricacion.currentText()}.")

    # -----------------------------------------------------------------
    # API para paneles/editor
    # -----------------------------------------------------------------
    def cargar(self, modifier):
        if isinstance(modifier, VDO_RE.ReengroseDTO):
            mod = VDO_RE.ReengroseModifier(modifier)
        elif isinstance(modifier, VDO_RE.ReengroseModifier):
            mod = modifier
        else:
            mod = VDO_RE.ReengroseModifier(modifier)

        bordes = {}
        if getattr(mod, "usa_bordes", False):
            for borde in VDO_RE.BORDES_2D:
                cfg = mod.bordes.get(borde)
                if isinstance(cfg, VDO_RE.BordeConfig):
                    bordes[borde] = cfg
                else:
                    bordes[borde] = VDO_RE.BordeConfig.from_dict(cfg)
        else:
            activo_legacy = None
            if mod.activo and mod.orientacion == "paralela":
                if mod.alineacion_profundidad in ("frente", "fondo"):
                    activo_legacy = mod.alineacion_profundidad
            if mod.activo and activo_legacy is None:
                activo_legacy = "frente"
            for borde in VDO_RE.BORDES_2D:
                bordes[borde] = VDO_RE.BordeConfig(
                    activo=(borde == activo_legacy),
                    ancho=mod.ancho,
                    offset_borde=0.0,
                    espesor=mod.espesor)

        activos = [b for b in VDO_RE.BORDES_2D
                   if bordes[b].activo]
        primero = bordes[activos[0]] if activos else None
        ancho = primero.ancho if primero else mod.ancho
        offset = primero.offset_borde if primero else 0.0
        largo_tira = (primero.largo_tira if primero
                      else VDO_RE.LARGO_TIRA_DEFAULT)
        uniforme = True
        if activos:
            uniforme = all(
                abs(bordes[b].ancho - ancho) <= 1e-6
                and abs(bordes[b].offset_borde - offset) <= 1e-6
                and bordes[b].largo_tira == largo_tira
                for b in activos)

        esquinas_raw = getattr(
            mod, "esquinas", VDO_RE.ENCUENTRO_ESQUINAS_DEFAULT)
        if not esquinas_raw:
            esquinas_raw = VDO_RE.ENCUENTRO_ESQUINAS_DEFAULT
        esquinas = VDO_RE._normalizar_encuentro(esquinas_raw)
        uniforme_esq = len(set(esquinas.values())) == 1

        self._cargando = True
        self.chk_activo.setChecked(bool(mod.activo))
        for borde in VDO_RE.BORDES_2D:
            cfg = bordes[borde]
            self.btn_borde[borde].setChecked(bool(cfg.activo))
            self.spin_ancho_borde[borde].setValue(float(cfg.ancho))
            self.spin_offset_borde[borde].setValue(
                float(cfg.offset_borde))
        self.spin_ancho.setValue(float(ancho))
        self.spin_offset.setValue(float(offset))
        self._set_combo_data(self.combo_largo_tira, largo_tira)
        self.spin_espesor.setValue(
            0.0 if mod.espesor is None else float(mod.espesor))
        self.chk_uniforme.setChecked(uniforme)
        for esquina in VDO_RE.ESQUINAS_2D:
            self._set_combo_data(
                self.combo_esquina[esquina], esquinas[esquina])
        self.chk_sync_esquinas.setChecked(uniforme_esq)
        self._set_combo_data(self.combo_fabricacion, mod.fabricacion)
        self._set_combo_data(self.combo_choque, mod.choque_nucleo)
        self._set_combo_data(self.combo_cara, mod.cara)
        self._cargando = False
        self._actualizar_estado()

    @staticmethod
    def _set_combo_data(combo, valor):
        idx = combo.findData(valor)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _datos_bordes(self):
        espesor = self.spin_espesor.value()
        espesor = espesor if espesor > 0 else None
        largo_tira = self.combo_largo_tira.currentData()
        bordes = {}
        for borde in VDO_RE.BORDES_2D:
            if self.chk_uniforme.isChecked():
                ancho = self.spin_ancho.value()
                offset = self.spin_offset.value()
            else:
                ancho = self.spin_ancho_borde[borde].value()
                offset = self.spin_offset_borde[borde].value()
            bordes[borde] = {
                "activo": self.btn_borde[borde].isChecked(),
                "ancho": ancho,
                "distancia_al_canto": offset,
                "largo_tira": largo_tira,
                "offset_borde": offset,
                "espesor": espesor,
            }
        return bordes

    def leer_modificador(self):
        return VDO_RE.ReengroseModifier({
            "activo": self.chk_activo.isChecked(),
            "bordes": self._datos_bordes(),
            "esquinas": self._esquinas_actuales(),
            "fabricacion": self.combo_fabricacion.currentData(),
            "choque_nucleo": self.combo_choque.currentData(),
            "cara": self.combo_cara.currentData(),
            "usa_bordes": True,
        })

    def set_activar_si_vacio(self):
        if not self._bordes_activos():
            self._cargando = True
            self.btn_borde["frente"].setChecked(True)
            self._cargando = False
            self._actualizar_estado()
