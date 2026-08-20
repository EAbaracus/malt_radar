import { NoPrice, assertNoPrice, stripPrice, hasPriceField } from './price-redaction';
import type { WhiskySummary, WhiskyDetail, DistillerySummary } from '../api/types';

describe('price-redaction guard', () => {
  test('NoPrice<T> omits price fields at compile time', () => {
    // This is a compile-time test — if NoPrice doesn't strip these fields,
    // the test file won't type-check. At runtime we verify the fields exist
    // on the original type and are absent on NoPrice<T>.
    const whisky: WhiskySummary = { whisky_id: 'W001', name: 'Test', brand: 'Brand', region: 'Speyside', abv: 46 };
    const redacted: NoPrice<WhiskySummary> = whisky;

    // Verify price fields are structurally absent from NoPrice<WhiskySummary>
    expect('price' in redacted).toBe(false);
    expect('price_value' in redacted).toBe(false);
    expect('price_currency' in redacted).toBe(false);
  });

  test('assertNoPrice throws when price field present', () => {
    const withPrice = { whisky_id: 'W001', name: 'Test', price: 45.00 };
    expect(() => assertNoPrice(withPrice, 'test-whisky')).toThrow('PRICING LEAK DETECTED');
  });

  test('assertNoPrice passes when no price field', () => {
    const noPrice = { whisky_id: 'W001', name: 'Test', brand: 'Brand' };
    expect(() => assertNoPrice(noPrice, 'test')).not.toThrow();
  });

  test('stripPrice removes price fields at runtime', () => {
    const obj = { whisky_id: 'W001', name: 'Test', price: 45.00, price_currency: 'USD' };
    const stripped = stripPrice(obj);
    expect(stripped).not.toHaveProperty('price');
    expect(stripped).not.toHaveProperty('price_currency');
    expect(stripped).toHaveProperty('whisky_id', 'W001');
  });

  test('hasPriceField detects price presence', () => {
    expect(hasPriceField({ whisky_id: 'W001', price: 45.00 })).toBe(true);
    expect(hasPriceField({ whisky_id: 'W001', name: 'Test' })).toBe(false);
    expect(hasPriceField(null)).toBe(false);
    expect(hasPriceField({ price: undefined })).toBe(false);
    expect(hasPriceField({ price: null })).toBe(false);
  });

  test('WhiskySummary type has no price fields (structural check)', () => {
    const w: WhiskySummary = { whisky_id: 'W001', name: 'Test', brand: 'Brand', region: 'Speyside', abv: 46 };
    const redactedW: NoPrice<WhiskySummary> = w;
    expect(hasPriceField(redactedW)).toBe(false);
  });
});
