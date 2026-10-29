# MCP Agent Manual — Protocolo de fichas técnicas VDO

Ubicación: `tools/vdo_erp_sync/MCP_AGENT_MANUAL.md`

Este documento define el protocolo canónico que todo agente MCP debe seguir al procesar fichas técnicas de fabricante para el sistema VDO (Neon + FreeCAD Macros).

---

## 1. Alcance

Procesar cotas de fabricante (hardware/herrajes) → validar → persistir en Neon → dejar `vdo_hardware_catalog.json` disponible en la raíz de macros para lectura directa de FreeCAD.

Todo el código vive en: `tools/vdo_erp_sync/`

---

## 2. Flujo canónico

```
Ingesta de cotas (fabricante)
        ↓
Tipado Zod  (src/schemas.ts)
        ↓
Validación CAD local
        ↓
Push atómico a Neon  (--dry-run obligatorio)
        ↓
Escritura de vdo_hardware_catalog.json en raíz de macros
```

### Paso A — Ingesta de cotas de fabricante

El agente recibe una ficha técnica con al menos:

- `sku` (código fabricante)
- `nombre`
- `categoria`
- `ancho`, `alto`, `fondo` (mm)
- `material`, `proveedor`
- `precioUnitario`, `moneda`

### Paso B — Tipado Zod (`src/schemas.ts`)

Validar el payload de entrada contra `CatalogIngestionSchema`:

```ts
import { CatalogIngestionSchema } from './schemas';

const ingestion = CatalogIngestionSchema.parse(payloadFabricante);
```

Cualquier cotaza inválida (negativa, cero, SKU vacío) rechaza la ingesta con `ZodError` antes de tocar Neon.

### Paso C — Validación CAD local

Antes del push, el agente debe verificar:

1. Todas las cotas son > 0.
2. `espesor` (si existe) > 0 y ≤ min(ancho, alto, fondo).
3. `moneda` cumple ISO 4217 (3 letras).
4. No hay SKUs duplicados dentro del lote.

Si falla, abortar y reportar al operador. No continuar hacia Neon.

### Paso D — Push atómico a Neon (`--dry-run` obligatorio)

El push a Neon se modela con `NeonPushSchema`:

```ts
import { NeonPushSchema } from './schemas';

const push: NeonPush = NeonPushSchema.parse({
  tabla: 'hardware_catalog',
  operacion: 'upsert',
  filas: [...],
  dryRun: true, // OBLIGATORIO
});
```

Regla de oro: **nunca** enviar `dryRun: false` sin aprobación explícita del operador y previa ejecución exitosa con `dryRun: true`. El push atómico significa: todo el lote o nada (transacción).

### Paso E — Salida del catálogo a la raíz de macros

`src/sync_pull_catalog.ts` expone `syncPullCatalog()` que:

1. Pull del catálogo actualizado desde Neon.
2. Valida con `CatalogIngestionSchema`.
3. Escribe `vdo_hardware_catalog.json` en:

   ```
   path.resolve(__dirname, '../../vdo_hardware_catalog.json')
   ```

   Desde `tools/vdo_erp_sync/src/` eso resuelve a la raíz de macros donde FreeCAD lo lee directamente.

---

## 3. Comandos de verificación

Desde `tools/vdo_erp_sync/`:

```bash
npm install
npx tsc --noEmit        # 0 errores de compilación TypeScript
npm run typecheck
```

---

## 4. Reglas de seguridad para agentes

- No modificar archivos `.py` ni `.FCMacro` de la raíz de macros.
- No ejecutar operaciones destructivas (`rm -rf`) fuera del árbol local `tools/vdo_erp_sync/`.
- Mantener la raíz del repo libre de `package.json`, `tsconfig.json` y `node_modules` a primer nivel; todo el tooling vive dentro de `tools/vdo_erp_sync/`.
- `--dry-run` es obligatorio en cualquier push a Neon.
