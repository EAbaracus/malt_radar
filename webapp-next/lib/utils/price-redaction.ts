import type { WhiskySummary, FlavorProfile, DistillerySummary } from '../api/types';

/**
 * Compile-time guard: ensures price fields never appear on whisky/distillery
 * types used for rendering. Price data exists in the backend but is stripped
 * before reaching the web tier — this guard enforces that at the TypeScript level.
 *
 * Per AGENTS.md "Product Rule": Price information must NEVER be exposed in UI or API responses.
 */
export type NoPrice<T> = Omit<T, 'price' | 'price_value' | 'price_currency' | 'price_history' | 'prices'>;

/**
 * Runtime assertion: throws at SSR/render time if a price field is present on
 * the object. This is a defense-in-depth complement to the compile-time NoPrice<T>
 * type — it catches any object that somehow carries price data from the backend.
 */
export function assertNoPrice(obj: unknown, context: string = 'render'): void {
  if (obj === null || typeof obj !== 'object') return;
  const record = obj as Record<string, unknown>;
  const priceFields = ['price', 'price_value', 'price_currency', 'price_history', 'prices'];
  for (const field of priceFields) {
    if (field in record && record[field] !== undefined && record[field] !== null) {
      throw new Error(
        `PRICING LEAK DETECTED [${context}]: field "${field}" is present on object. ` +
        `Price data must never reach the UI tier. This is a hard invariant (AGENTS.md Product Rule).`
      );
    }
  }
}

/**
 * Strips price fields from any object at runtime. Returns a new object
 * without price-related keys. Used as a sanitizer at the API boundary.
 */
export function stripPrice<T extends Record<string, unknown>>(obj: T): NoPrice<T> {
  const priceFields = ['price', 'price_value', 'price_currency', 'price_history', 'prices'];
  const result: Record<string, unknown> = {};
  for (const key of Object.keys(obj)) {
    if (!priceFields.includes(key)) {
      result[key] = obj[key];
    }
  }
  return result as NoPrice<T>;
}

/**
 * Type guard: returns true if the object contains any price field.
 * Used in tests and conditional rendering paths.
 */
export function hasPriceField(obj: unknown): boolean {
  if (obj === null || typeof obj !== 'object') return false;
  const record = obj as Record<string, unknown>;
  const priceFields = ['price', 'price_value', 'price_currency', 'price_history', 'prices'];
  return priceFields.some((f) => f in record && record[f] !== undefined && record[f] !== null);
}
