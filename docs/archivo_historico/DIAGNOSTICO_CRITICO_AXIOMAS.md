# DIAGNÓSTICO CRÍTICO: ¿Son los Bugs Reales y ¿Es Necesario el Plan de Axiomas?
**ARCHIVO HISTÓRICO** — Referencia operativa, no ley de diseño. Origen: `documentacion/Progreso/DIAGNOSTICO_CRITICO_AXIOMAS.md`

**Fecha:** 2026-10-29  
**Evaluador:** Claude Code (Diagnóstico de Alto Nivel)  
**Conclusión General:** Los bugs FUERON reales y críticos, pero YA están reparados. El plan de axiomas es DEFENSIVO (prevención futura), no correctivo.

## PARTE 1: Verificación de Bugs Reales

### ✅ BUG-001: Reengrose Desbordado (w/h invertidos)
**Estado:** VERIFICADO COMO REAL  
**Commit de reparación:** `4c4ee3c` (fix: geometry)  
**Evidencia:** Tira vertical 70×580 mm se calculaba como Box(580, 70) en lugar de Box(70, 580). Ocupaba X: 0-580 en lugar de X: 0-70 (desbordamiento de 7.3x).  
**Código actual:** Ya reparado (fallback correcto en línea 46-55)  
**Criticidad:** ALTA

### ✅ BUG-002: Ancho Fachada Undersized (ancho_ext vs li)
**Estado:** VERIFICADO COMO REAL  
**Commit de reparación:** `4c4ee3c` + `7393eca`  
**Evidencia:** Fachada queda 25.4 mm más estrecha (exactamente delta telescópica).  
**Código actual:** Reparado (línea 361, 401 en vdo_cajon_despiece.py)  
**Criticidad:** ALTA

### ✅ BUG-003: Fachada Descentrada (x respecto a caja vs vano)
**Estado:** VERIFICADO COMO REAL  
**Commit de reparación:** `7393eca`  
**Evidencia:** Antes: margen izq -27.7 mm, margen der -2.3 mm, asimetría 25.4 mm. Después: -15.0 mm ambos lados, asimetría 0.0 mm.  
**Código actual:** Reparado (línea 401, vdo_cajon_despiece.py)  
**Criticidad:** ALTA

### ✅ BUG-004: Cajón Corrido (w vs nominal_w)
**Estado:** VERIFICADO COMO REAL  
**Commit de reparación:** `a7ccc60`  
**Evidencia:** vdo_coco_unified_task.py usaba resuelto.w (neto) en lugar de nominal_w (total). Desplazamiento -25.4 mm.  
**Código actual:** Reparado (línea 1069-1070, vdo_coco_unified_task.py)  
**Criticidad:** ALTA

### ✅ BUG-005: Posición X Cajón Sin Offset Simétrico
**Estado:** VERIFICADO COMO REAL  
**Commit de reparación:** `4c4ee3c`  
**Evidencia:** LocalPlacement ignora delta/2. Desplazamiento -12.7 mm.  
**Código actual:** Reparado (vdo_coco_unified_task.py)  
**Criticidad:** MEDIA

### ⚠️ BUG-006: Doble Aplicación de Offset
**Estado:** VERIFICADO EN COMMIT (revertido)  
**Commit de reparación:** `af8ce9b`  
**Evidencia:** Offset delta/2 se aplicaba dos veces. Se decidió que no es necesario.  
**Código actual:** No existe (fue revertido)  
**Criticidad:** NO APLICA

## PARTE 2: Análisis de Criticidad
Todos los bugs eran CRÍTICOS (altamente visibles). La reparación fue justificada.

| Bug # | Descripción | Impacto Visual | Magnitud | Fácil de Detectar | Fácil de Reparar |
|-------|-------------|----------------|----------|-------------------|------------------|
| 001 | Reengrose 2x | Deformación extrema | 7.3x | ✅ Muy obvio | ✅ 5 min |
| 002 | Fachada -28mm | Incompleta visiblemente | -28 mm | ✅ Obvio | ✅ 10 min |
| 003 | Fachada -27.7/-2.3 | Descentrada completamente | ±25 mm | ✅ Obvio | ✅ 5 min |
| 004 | Cajón -25.4mm | Desplazado visiblemente | -25.4 mm | ✅ Obvio | ✅ 2 min |
| 005 | Pos X -delta/2 | Sutil, se nota | -12.7 mm | ⚠️ Requiere medida | ✅ 10 min |

## PARTE 3: Estado Actual del Código
Todas las reparaciones están verificadas y documentadas en el código con comentarios.

## PARTE 4: ¿Es Necesario el Plan de Axiomas?
**Veredicto:** NO es necesario el plan de axiomas completo (5.5 horas). Costo/beneficio desfavorable.

### Alternativa recomendada: Opción 2 — Tests + Documentación (1.5-2 horas)
1. Crear `/tests/test_axioms_vdo.py`
2. Crear `/Documentación/MAPEO_ANCHO_VDO.md` (versión simplificada)
3. Agregar type hints a `calcular_despiece()` usando `NewType` (AnchoVanoTotal vs AnchoVanoNeto)

**Roadmap recomendado:**
- Fase 1 (0.5h): Tests que validan que todos los bugs están reparados
- Fase 2 (0.5h): MAPEO_ANCHO_VDO.md (tabla de referencia rápida)
- Fase 3 (0.5h): Type hints en calcular_despiece()
- Fase 4 (opcional): Axiomas completos solo si se detectan nuevas confusiones semánticas

*Este archivo es referencia histórica; la ley de diseño vigente está en `documentacion_v2/`.*
