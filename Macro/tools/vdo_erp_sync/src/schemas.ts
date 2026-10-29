import { z } from 'zod';

export const HardwareItemSchema = z.object({
  id: z.string().uuid().optional(),
  sku: z.string().min(1, 'SKU requerido'),
  nombre: z.string().min(1, 'Nombre requerido'),
  categoria: z.string().min(1, 'Categoría requerida'),
  ancho: z.number().positive('Ancho debe ser positivo'),
  alto: z.number().positive('Alto debe ser positivo'),
  fondo: z.number().positive('Fondo debe ser positivo'),
  espesor: z.number().positive('Espesor debe ser positivo').optional(),
  material: z.string().min(1, 'Material requerido'),
  proveedor: z.string().min(1, 'Proveedor requerido'),
  precioUnitario: z.number().nonnegative('Precio no puede ser negativo'),
  moneda: z.string().length(3, 'Moneda debe ser ISO 4217 (3 letras)').default('EUR'),
  disponible: z.boolean().default(true),
  updatedAt: z.string().datetime({ offset: true }).optional(),
});

export type HardwareItem = z.infer<typeof HardwareItemSchema>;

export const CatalogIngestionSchema = z.object({
  items: z.array(HardwareItemSchema),
  fuente: z.string().min(1, 'Fuente de ingesta requerida'),
  ingestedAt: z.string().datetime({ offset: true }),
});

export type CatalogIngestion = z.infer<typeof CatalogIngestionSchema>;

export const NeonPushSchema = z.object({
  tabla: z.enum(['hardware_catalog', 'hardware_items']),
  operacion: z.enum(['insert', 'upsert', 'delete']),
  filas: z.array(z.record(z.string(), z.unknown())),
  dryRun: z.boolean().default(true),
});

export type NeonPush = z.infer<typeof NeonPushSchema>;
