# -*- coding: utf-8 -*-
# =====================================================================
# VDO/cam/vdo_cam_optimizer_dialog.py
# (antes macros/vdo_optimizer.FCMacro; movido para ser alcanzable desde
#  el workbench, D55)
# Optimizador de corte 2D para tableros VDO — autocontenido.
#
# Axioma 1 (independencia): este archivo es solo UI/visualización.
#   El cálculo vive en VDO/cam/vdo_cam_optimizer_engine.py (sin UI).
# Axioma 2 (mínima información): un único diálogo con preview embebido.
#   No abre navegador, no usa terminal, no crea objetos en el 3D.
#
# Entrada:  CSV de lista de corte (vdo_cutting_list).
# Salida:   plano dibujado en pantalla (piezas + retales) + sumatoria.
# =====================================================================

import os
import sys

import FreeCAD as App

try:
    import FreeCADGui as Gui  # noqa: F401
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
    except ImportError:
        from PySide import QtWidgets, QtCore, QtGui
    _GUI = True
except Exception:
    QtWidgets = QtCore = QtGui = None
    _GUI = False

import VDO.cam.vdo_cam_optimizer_engine as core
import VDO.cam.vdo_cam_optimizer_view as view


class OptimizerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VDO · Optimizador de corte")
        self.resize(1080, 660)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(split, 1)

        # ---- Panel izquierdo: configuración ----
        left = QtWidgets.QWidget()
        form = QtWidgets.QVBoxLayout(left)

        form.addWidget(QtWidgets.QLabel("<b>Lista de corte</b>"))
        row = QtWidgets.QHBoxLayout()
        self.edit_csv = QtWidgets.QLineEdit()
        default_csv = os.path.join(os.path.expanduser("~"), "Desktop",
                                   "vdo_cutting_list.csv")
        if os.path.exists(default_csv):
            self.edit_csv.setText(default_csv)
        btn = QtWidgets.QPushButton("Examinar…")
        btn.clicked.connect(self._pick_csv)
        row.addWidget(self.edit_csv)
        row.addWidget(btn)
        form.addLayout(row)
        self.lbl_csv = QtWidgets.QLabel("—")
        self.lbl_csv.setStyleSheet("color:#777; font-size:11px;")
        form.addWidget(self.lbl_csv)
        self.edit_csv.textChanged.connect(self._inspect_csv)

        form.addSpacing(8)
        form.addWidget(QtWidgets.QLabel("<b>Tablero</b>"))
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(list(core.PRESETS.keys()))
        self.combo.currentTextChanged.connect(self._on_preset)
        form.addWidget(self.combo)

        g = QtWidgets.QGridLayout()
        g.addWidget(QtWidgets.QLabel("Ancho (mm)"), 0, 0)
        self.spin_w = QtWidgets.QSpinBox(); self.spin_w.setRange(100, 10000)
        g.addWidget(self.spin_w, 0, 1)
        g.addWidget(QtWidgets.QLabel("Alto (mm)"), 1, 0)
        self.spin_h = QtWidgets.QSpinBox(); self.spin_h.setRange(100, 10000)
        g.addWidget(self.spin_h, 1, 1)
        form.addLayout(g)

        form.addSpacing(8)
        form.addWidget(QtWidgets.QLabel("<b>Corte</b>"))
        g2 = QtWidgets.QGridLayout()
        g2.addWidget(QtWidgets.QLabel("Kerf sierra (mm)"), 0, 0)
        self.spin_kerf = QtWidgets.QDoubleSpinBox(); self.spin_kerf.setRange(0, 30)
        self.spin_kerf.setValue(core.KERF_DEFAULT)
        g2.addWidget(self.spin_kerf, 0, 1)
        g2.addWidget(QtWidgets.QLabel("Margen (mm)"), 1, 0)
        self.spin_margin = QtWidgets.QDoubleSpinBox(); self.spin_margin.setRange(0, 100)
        self.spin_margin.setValue(core.MARGIN_DEFAULT)
        g2.addWidget(self.spin_margin, 1, 1)
        form.addLayout(g2)

        self.chk_rotate = QtWidgets.QCheckBox("Permitir rotar piezas")
        self.chk_rotate.setChecked(True)
        form.addWidget(self.chk_rotate)

        form.addStretch(1)
        self.btn_run = QtWidgets.QPushButton("▶  Optimizar")
        self.btn_run.setStyleSheet(
            "background:#0066cc; color:white; font-weight:bold; padding:6px;")
        self.btn_run.clicked.connect(self._run)
        form.addWidget(self.btn_run)

        left.setMinimumWidth(280)
        left.setMaximumWidth(360)
        split.addWidget(left)

        # ---- Panel derecho: preview ----
        self.view = view.BoardView()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.view)
        scroll.setStyleSheet("background:#fafafa;")
        split.addWidget(scroll)
        split.setStretchFactor(1, 1)

        # ---- Barra inferior: sumatoria ----
        bar = QtWidgets.QHBoxLayout()
        self.lbl_summary = QtWidgets.QLabel("Sin optimizar.")
        self.lbl_summary.setStyleSheet("font-size:12px;")
        bar.addWidget(self.lbl_summary, 1)
        btn_close = QtWidgets.QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        bar.addWidget(btn_close)
        root.addLayout(bar)

        if self.combo.count():
            self._on_preset(self.combo.currentText())
        self._inspect_csv()

    # ------------------------------------------------------------------
    def _on_preset(self, name):
        p = core.PRESETS.get(name)
        if p:
            self.spin_w.setValue(int(p[0]))
            self.spin_h.setValue(int(p[1]))

    def _pick_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Elegir lista de corte", self.edit_csv.text() or
            os.path.expanduser("~"), "CSV (*.csv);;Todos (*)")
        if path:
            self.edit_csv.setText(path)

    def _inspect_csv(self):
        path = self.edit_csv.text().strip()
        if not path or not os.path.exists(path):
            self.lbl_csv.setText("—")
            return
        try:
            parts = core.read_cutting_csv(path)
        except Exception as e:
            self.lbl_csv.setText(f"✖ {e}")
            return
        if not parts:
            self.lbl_csv.setText("✖ sin piezas válidas")
            return
        mats = {p["material"] for p in parts}
        esp = {p["thickness"] for p in parts}
        n = sum(p["qty"] for p in parts)
        self.lbl_csv.setText(
            f"✔ {n} piezas · {len(mats)} material(es) · {len(esp)} espesor(es)")

    # ------------------------------------------------------------------
    def _run(self):
        path = self.edit_csv.text().strip()
        if not path or not os.path.exists(path):
            QtWidgets.QMessageBox.warning(self, "Aviso",
                                          "Elegí un archivo CSV válido.")
            return

        parts = core.read_cutting_csv(path)
        if not parts:
            QtWidgets.QMessageBox.warning(self, "Aviso",
                                          "El CSV no tiene piezas válidas.")
            return

        board_w = float(self.spin_w.value())
        board_h = float(self.spin_h.value())
        if self.spin_kerf.value() * 2 + self.spin_margin.value() * 2 >= min(board_w, board_h):
            QtWidgets.QMessageBox.warning(
                self, "Tablero inválido",
                "El kerf y el margen no dejan espacio útil en el tablero.")
            return

        try:
            groups = core.optimize_by_group(
                core.expand_pieces(parts),
                board_w=board_w, board_h=board_h,
                kerf=float(self.spin_kerf.value()),
                margin=float(self.spin_margin.value()),
                allow_rotation=self.chk_rotate.isChecked())
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", str(e))
            return

        self.view.set_groups(groups)

        tot = core.resumen_global(groups, board_w, board_h)
        txt = (f"<b>{tot['n_placed']}/{tot['n_total']} piezas</b> · "
               f"{tot['n_boards']} tablero(s) · "
               f"aprovechamiento <b>{tot['efficiency']:.1f}%</b> · "
               f"retal {tot['retal_m2']:.2f} m² · "
               f"desperdicio {tot['waste_m2']:.2f} m²")
        if tot["n_unplaced"]:
            txt += f" · <span style='color:#c00'>no colocadas: {tot['n_unplaced']}</span>"
        self.lbl_summary.setText(txt)

        App.Console.PrintMessage(
            f"[VDO] Optimizado: {tot['n_placed']}/{tot['n_total']} piezas, "
            f"{tot['n_boards']} tablero(s), {tot['efficiency']:.1f}%\n")


def main():
    if not _GUI:
        App.Console.PrintError(
            "[VDO] El optimizador necesita la interfaz gráfica de FreeCAD.\n")
        return
    OptimizerDialog().exec_()


if __name__ == "__main__":
    main()
