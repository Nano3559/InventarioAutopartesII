// Display-only examples. Never passed to inference, ranking, training or the API.
export const DEMONSTRATION_HISTORY = {
  version: "display-history-2026-v1",
  seed: 42,
  origin: "SYNTHETIC_ILLUSTRATION_NOT_DATASET_OR_FORECAST",
  start: "2026-01",
  end: "2026-10",
} as const;

function hash(value: string): number {
  let result = 2166136261;
  for (const char of value) result = Math.imul(result ^ char.charCodeAt(0), 16777619);
  return result >>> 0;
}

export function demonstrationHistory2026(productId: number, locationId: number) {
  if (!Number.isSafeInteger(productId) || productId < 1 || !Number.isSafeInteger(locationId) || locationId < 1) throw new Error("Referencia de demostración inválida.");
  const key = `${DEMONSTRATION_HISTORY.seed}:${productId}:${locationId}`;
  const identity = hash(key);
  const rotations = [3, 16, 45];
  const rotation = rotations[identity % rotations.length];
  const storeEffect = 0.85 + (hash(`${key}:store`) % 31) / 100;
  const phase = (hash(`${key}:phase`) % 12) / 12 * 2 * Math.PI;
  return Array.from({ length: 10 }, (_, i) => {
    const noise = 0.85 + (hash(`${key}:${i}:noise`) % 31) / 100;
    const season = 1 + 0.2 * Math.sin(i / 12 * 2 * Math.PI + phase);
    const trend = 1 + i * 0.015;
    const units = rotation === 3 && hash(`${key}:${i}:zero`) % 5 === 0 ? 0 : Math.max(0, Math.round(rotation * storeEffect * season * trend * noise));
    const wholesaleUnits = Math.floor(units * (0.1 + (hash(`${key}:${i}:channel`) % 21) / 100));
    return { month: `2026-${String(i + 1).padStart(2,"0")}`, units, retailUnits: units - wholesaleUnits, wholesaleUnits };
  });
}
