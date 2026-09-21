#!/bin/bash
# =====================================================================
# instalar_vdo.sh
# Script de instalación VDO para Linux/Mac
# =====================================================================

echo "=========================================="
echo "  INSTALADOR VDO - Veta de Oro"
echo "=========================================="
echo ""

# Detectar FreeCAD
FREECAD_CMD=""

# Buscar FreeCAD en ubicaciones comunes
if command -v freecad &> /dev/null; then
    FREECAD_CMD="freecad"
elif [ -f "/usr/bin/freecad" ]; then
    FREECAD_CMD="/usr/bin/freecad"
elif [ -f "/usr/local/bin/freecad" ]; then
    FREECAD_CMD="/usr/local/bin/freecad"
elif [ -f "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD" ]; then
    FREECAD_CMD="/Applications/FreeCAD.app/Contents/MacOS/FreeCAD"
fi

if [ -z "$FREECAD_CMD" ]; then
    echo "❌ FreeCAD no encontrado en el sistema"
    echo ""
    echo "Opciones:"
    echo "  1. Instale FreeCAD y vuelva a ejecutar este script"
    echo "  2. Ejecute manualmente dentro de FreeCAD:"
    echo "     Macro → Ejecutar → seleccione vdo_install.py"
    echo ""
    read -p "Presione Enter para continuar..."
    exit 1
fi

echo "✅ FreeCAD encontrado: $FREECAD_CMD"
echo ""

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPT="$SCRIPT_DIR/vdo_install.py"

if [ ! -f "$INSTALL_SCRIPT" ]; then
    echo "❌ No se encontró vdo_install.py en: $SCRIPT_DIR"
    read -p "Presione Enter para continuar..."
    exit 1
fi

echo "📦 Ejecutando instalador..."
echo "   Script: $INSTALL_SCRIPT"
echo ""

# Ejecutar instalador en FreeCAD
"$FREECAD_CMD" "$INSTALL_SCRIPT"

echo ""
echo "=========================================="
echo "  INSTALACIÓN COMPLETADA"
echo "=========================================="
