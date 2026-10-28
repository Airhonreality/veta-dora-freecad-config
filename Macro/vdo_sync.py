#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_sync.py
Sincronización y deploy AGNÓSTICOS al SO entre el repo VDO y FreeCAD.

No usa rutas fijas: descubre macros, user.cfg y repo con vdo_paths.

Uso:
    python3 vdo_sync.py paths                 # muestra las rutas detectadas
    python3 vdo_sync.py init --repo RUTA      # guarda la ruta del repo
    python3 vdo_sync.py push                  # macros locales  -> repo
    python3 vdo_sync.py pull                  # repo -> macros locales
    python3 vdo_sync.py inject                # (re)crea la toolbar en user.cfg
    python3 vdo_sync.py publish               # push + inject + git add/commit/push

También se puede ejecutar dentro de FreeCAD (Macro → Ejecutar → vdo_sync.py),
en cuyo caso usa las rutas oficiales de FreeCAD.
"""

import argparse
import filecmp
import shutil
import subprocess
import sys
from datetime import datetime

import vdo_paths as vp

MACRO_GLOBS = ("*.py", "*.FCMacro", "*.svg", "*.json", "*.yaml", "*.md", "*.txt")


def _macro_files(src):
    for pat in MACRO_GLOBS:
        for f in src.glob(pat):
            if f.is_file() and "__pycache__" not in f.parts:
                yield f


def _sync_dir(src, dst):
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in _macro_files(src):
        d = dst / f.name
        if d.exists() and filecmp.cmp(str(f), str(d), shallow=False):
            continue
        shutil.copy2(str(f), str(d))
        print(f"  -> {f.name}")
        n += 1
    return n


def cmd_paths(_args):
    d = vp.describe()
    print("Rutas detectadas (agnóstico al SO):")
    print(f"  repo     : {d['repo']}")
    print(f"  macro dir: {d['macro']}")
    print(f"  user.cfg : {d['user_cfg']}")
    missing = [k for k, v in d.items() if v is None]
    if missing:
        print(f"\n⚠️  No detectado: {', '.join(missing)}")
        if "repo" in missing:
            print("   Define el repo con:  python3 vdo_sync.py init --repo RUTA"
                  "   (o export VDO_REPO=RUTA)")
    return 0


def cmd_init(args):
    p = vp.save_repo_root(args.repo)
    print(f"✅ Repo guardado en {p}: {args.repo}")
    return 0


def cmd_push(_args):
    repo = vp.get_repo_root()
    macro = vp.get_macro_dir()
    if not repo or not macro:
        print("❌ No se detectó repo o macro dir. Usá 'paths'.")
        return 1
    print(f"📤 {macro}  ->  {repo / 'Macro'}")
    n = _sync_dir(macro, repo / "Macro")
    print(f"✅ {n} archivo(s) sincronizado(s) al repo")
    return 0


def cmd_pull(_args):
    repo = vp.get_repo_root()
    macro = vp.get_macro_dir()
    if not repo or not macro:
        print("❌ No se detectó repo o macro dir. Usá 'paths'.")
        return 1
    print(f"📥 {repo / 'Macro'}  ->  {macro}")
    n = _sync_dir(repo / "Macro", macro)
    print(f"✅ {n} archivo(s) sincronizado(s) a macros")
    return 0


def cmd_inject(_args):
    cfg = vp.get_user_cfg()
    if not cfg:
        print("❌ No se encontró user.cfg de FreeCAD")
        return 1
    import vdo_toolbar_inject as ti
    print(f"🔧 Inyectando toolbar en {cfg}")
    return 0 if ti.inject_toolbar(str(cfg)) else 1


def _git(repo, *args):
    r = subprocess.run(["git", *args], cwd=str(repo),
                       capture_output=True, text=True)
    return r


def cmd_publish(args):
    if cmd_push(args) != 0:
        return 1
    cmd_inject(args)

    repo = vp.get_repo_root()
    print(f"\n🔧 git add/commit/push en {repo}")
    _git(repo, "add", "-A")
    status = _git(repo, "status", "--porcelain")
    if not status.stdout.strip():
        print("ℹ️  Sin cambios para commit")
        return 0
    msg = args.message or f"Sync VDO macros ({datetime.now():%Y-%m-%d %H:%M})"
    c = _git(repo, "commit", "-m", msg)
    if c.returncode != 0:
        print(f"❌ commit: {c.stderr or c.stdout}")
        return 1
    p = _git(repo, "push", "origin", "master")
    if p.returncode != 0:
        print(f"❌ push: {p.stderr or p.stdout}")
        return 1
    print("✅ Publicado en GitHub")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="VDO sync agnóstico al SO")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("paths", help="muestra rutas detectadas")
    p_init = sub.add_parser("init", help="guarda la ruta del repo")
    p_init.add_argument("--repo", required=True)
    sub.add_parser("push", help="macros locales -> repo")
    sub.add_parser("pull", help="repo -> macros locales")
    sub.add_parser("inject", help="crear toolbar en user.cfg")
    p_pub = sub.add_parser("publish", help="push + inject + git push")
    p_pub.add_argument("--message", default=None)

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 0
    return globals()[f"cmd_{args.cmd}"](args)


if __name__ == "__main__":
    raise SystemExit(main())
