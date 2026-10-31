# Índice de archivo_historico/
**Propósito:** Referencia operativa y bitácoras históricas. NO es ley de diseño. La ley de diseño vigente está en los 6 documentos canónicos de `documentacion_v2/` (00 a 05).

## Contenido

| Archivo | Origen | Qué contiene |
|---------|--------|--------------|
| `06_INFORME_BRECHAS_FORENSE.md` | `documentacion_v2/` (entregable de auditoría) | Informe forense de brechas: inventario completo de `documentacion/`, matriz de gaps, plan de integración. |
| `PROGRESO_VDO.md` | `documentacion/Progreso/PROGRESO_VDO.md` | Historial de versiones v1.0-1.8, sesiones 20/09, 22/10, 26/10, funcionalidades implementadas, tests pendientes. |
| `PROGRESO_VDO.yaml` | `documentacion/Progreso/PROGRESO_VDO.yaml` | Registro YAML con checkpoints detallados (2026-09-18 → 2026-10-26), archivos creados/modificados por checkpoint, siguientes pasos. |
| `Plan_de_Acciones_VDO.md` | `documentacion/Progreso/Plan_de_Acciones_VDO.md` | Plan de acción 6 fases para incompatibilidad reactiva, matriz de dependencias, checklist, criterios de éxito. |
| `Refactorización_Plan_Óptimo.md` | `documentacion/Progreso/Refactorización_Plan_Óptimo.md` | Plan óptimo de transacciones: focusIn/focusOut, timer 100ms, tabla comparativa antes/después, lecciones aprendidas. |
| `Correcciones_Aplicadas.md` | `documentacion/Progreso/Correcciones_Aplicadas.md` | 4 correcciones a `vdo_universal_inspector.py` (timer stop/start, micro-header, chasis, herrajes). |
| `DIAGNOSTICO_CRITICO_AXIOMAS.md` | `documentacion/Progreso/DIAGNOSTICO_CRITICO_AXIOMAS.md` | Verificación de 5 bugs reales (BUG-001 a 005), análisis de necesidad del plan de axiomas, recomendación Opción 2 (tests + docs). |
| `Revision_Codigo_VDO.md` | `documentacion/Progreso/Revision_Codigo_VDO.md` | 6 hallazgos de código en `vdo_universal_inspector.py` (timer bug, recompute sin transacción ×3, métodos largos), plan de correcciones. |
| `SESION_20_SEPT_2026.md` | `documentacion/Progreso/SESION_20_SEPT_2026.md` | Informe de sesión 20/09/2026: motor unificado paneles, lógica fondo, Task Panel PySide, 5 errores corregidos, estructura de archivos. |

## Nota para el Agente 2
Estos archivos son **historia operativa**. No contienen reglas de arquitectura vigentes. Para decisiones canónicas, consultar exclusivamente:
- `00_MATRIZ_CONTRADICCIONES_Y_RESOLUCION.md`
- `01_LOGICA_NEGOCIO_Y_CARPINTERIA.md`
- `02_ARQUITECTURA_TECNICA_FREECAD.md`
- `03_INVESTIGACIONES_TECNICAS_INVS.md`
- `04_DECISIONES_ADR_Y_AXIOMAS.md`
- `05_PLAN_REFACTORIZACION_CODIGO.md`

*Este índice es parte de `archivo_historico/` y no debe considerarse ley de diseño.*
