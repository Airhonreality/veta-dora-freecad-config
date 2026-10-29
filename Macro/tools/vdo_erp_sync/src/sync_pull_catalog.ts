import * as path from 'path';
import * as fs from 'fs';
import { CatalogIngestionSchema, type CatalogIngestion } from './schemas';

const CATALOG_OUT = path.resolve(__dirname, '../../vdo_hardware_catalog.json');

async function fetchCatalogFromNeon(): Promise<unknown> {
  // Integración con Neon/MCP: reemplazar por llamada real al cliente Neon.
  // Devuelve el payload crudo del catálogo de hardware.
  const resp = await fetch('https://neon.example.com/v1/catalog/hardware', {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) throw new Error(`Neon fetch failed: ${resp.status}`);
  return resp.json();
}

export async function syncPullCatalog(): Promise<void> {
  const raw: unknown = await fetchCatalogFromNeon();
  const ingestion: CatalogIngestion = CatalogIngestionSchema.parse(raw);
  fs.writeFileSync(CATALOG_OUT, JSON.stringify(ingestion.items, null, 2), 'utf-8');
}

if (require.main === module) {
  syncPullCatalog()
    .then(() => {
      // eslint-disable-next-line no-console
      console.log(`Catálogo escrito en ${CATALOG_OUT}`);
    })
    .catch((err: unknown) => {
      // eslint-disable-next-line no-console
      console.error(err);
      process.exit(1);
    });
}
