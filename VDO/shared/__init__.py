# -*- coding: utf-8 -*-
"""Modulos compartidos del workbench VDO.

Vivian en la raiz del workbench y se importaban de forma absoluta
(import vdo_shared_guardian). FreeCAD anade cada Mod/<dir> al sys.path global, asi
que esos nombres quedaban expuestos a todo Python y podian colisionar con
otros addons. Encapsularlos aqui hace el paquete autocontenido y portable.
"""
