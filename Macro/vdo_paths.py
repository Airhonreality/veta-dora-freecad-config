#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_paths.py
Resolución AGNÓSTICA al SO de las rutas de FreeCAD y del repo VDO.

Principio: el repo guarda contenido relativo (agnóstico); este módulo
descubre DÓNDE viven las cosas en la máquina local, sin rutas fijas.

- macro dir   : App.getUserMacroDir(True) si hay FreeCAD; si no, candidatos
                native / flatpak / snap / macOS / Windows.
- user.cfg    : App.getUserConfigDir() si hay FreeCAD; si no, candidatos.
- repo VDO    : variable de entorno VDO_REPO, o ~/.config/vdo/sync.json,
                o búsqueda en ubicaciones conocidas.

Sin dependencias. Importable dentro y fuera de FreeCAD.
"""

import os
import json
from pathlib import Path

try:
    import FreeCAD as App  # noqa: N816  (API de FreeCAD)
except Exception:
    App = None

_REPO_CONFIG = Path(os.path.expanduser("~/.config/vdo/sync.json"))
_REPO_CONFIG_ALT = Path(os.path.expanduser("~/.vdo_sync.json"))


def _existing(candidates):
    out = []
    for c in candidates:
        if not c:
            continue
        p = Path(os.path.expanduser(c))
        if p.is_dir():
            out.append(p)
    return out


def get_macro_dir():
    """Directorio de macros de FreeCAD (Path) o None."""
    if App is not None:
        try:
            return Path(App.getUserMacroDir(True))
        except Exception:
            pass
    cands = [
        "~/.local/share/FreeCAD/Macro",
        "~/.local/share/FreeCAD/v1-1/Macro",
        "~/.var/app/org.freecad.FreeCAD/data/FreeCAD/v1-1/Macro",
        "~/.var/app/org.freecad.FreeCAD/data/FreeCAD/Macro",
        "~/snap/freecad/common/FreeCAD/Macro",
        "~/Library/Application Support/FreeCAD/Macro",        # macOS
        os.path.join(os.environ.get("APPDATA", ""), "FreeCAD", "Macro"),  # Windows
    ]
    dirs = _existing(cands)
    return dirs[0] if dirs else None


def get_user_cfg():
    """Ruta a user.cfg local (Path) o None."""
    if App is not None:
        try:
            cfg = Path(App.getUserConfigDir()) / "user.cfg"
            if cfg.is_file():
                return cfg
        except Exception:
            pass
    cands = [
        "~/.config/FreeCAD/v1-1/user.cfg",
        "~/.config/FreeCAD/user.cfg",
        "~/.var/app/org.freecad.FreeCAD/config/FreeCAD/v1-1/user.cfg",
        "~/.var/app/org.freecad.FreeCAD/config/FreeCAD/user.cfg",
        "~/snap/freecad/common/FreeCAD/user.cfg",
        "~/Library/Preferences/FreeCAD/user.cfg",             # macOS
        os.path.join(os.environ.get("APPDATA", ""), "FreeCAD", "user.cfg"),
    ]
    for c in cands:
        if not c:
            continue
        p = Path(os.path.expanduser(c))
        if p.is_file():
            return p
    return None


def get_config_dir():
    cfg = get_user_cfg()
    return cfg.parent if cfg else None


def _is_repo(p):
    return (p / ".git").is_dir() and (p / "Macro").is_dir()


def get_repo_root():
    """Raíz del repo VDO (Path) o None."""
    # 1. Variable de entorno
    env = os.environ.get("VDO_REPO")
    if env:
        p = Path(os.path.expanduser(env))
        if _is_repo(p):
            return p

    # 2. Archivo de configuración
    for cf in (_REPO_CONFIG, _REPO_CONFIG_ALT):
        if cf.is_file():
            try:
                data = json.loads(cf.read_text(encoding="utf-8"))
                p = Path(os.path.expanduser(str(data.get("repo", ""))))
                if p and _is_repo(p):
                    return p
            except Exception:
                pass

    # 3. Ubicaciones conocidas
    cands = [
        "~/Proyectos/DEVs/veta-dora-freecad-config",
        "~/Proyectos/veta-dora-freecad-config",
        "~/veta-dora-freecad-config",
        "~/repos/veta-dora-freecad-config",
        "~/git/veta-dora-freecad-config",
        "~/Documentos/veta-dora-freecad-config",
    ]
    for c in cands:
        p = Path(os.path.expanduser(c))
        if _is_repo(p):
            return p

    # 4. Búsqueda acotada en ~/Proyectos
    base = Path(os.path.expanduser("~/Proyectos"))
    if base.is_dir():
        for marker in base.rglob("Macro/vdo_manifest.json"):
            p = marker.parent.parent
            if _is_repo(p):
                return p
    return None


def save_repo_root(path):
    """Persiste la ruta del repo en ~/.config/vdo/sync.json."""
    p = Path(os.path.expanduser(str(path)))
    _REPO_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _REPO_CONFIG.write_text(json.dumps({"repo": str(p)}, indent=2),
                            encoding="utf-8")
    return _REPO_CONFIG


def describe():
    return {
        "repo": get_repo_root(),
        "macro": get_macro_dir(),
        "user_cfg": get_user_cfg(),
    }
