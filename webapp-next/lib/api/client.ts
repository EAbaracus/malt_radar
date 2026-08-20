import type { WhiskyListResponse, WhiskyDetail, DistilleryListResponse, WhiskyListParams, FlavorProfile } from './types';
import { assertNoPrice } from '../utils/price-redaction';

const API_BASE_URL = process.env.MALT_RADAR_API_BASE_URL || 'http://localhost:8080';

export class MaltRadarApi {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl?: string, token?: string | null) {
    this.baseUrl = baseUrl || API_BASE_URL;
    this.authToken = token ?? null;
  }

  protected async get(path: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (this.authToken) headers['Authorization'] = `Bearer ${this.authToken}`;
    const res = await fetch(`${this.baseUrl}${path}`, { headers, next: { tags: ['maltradar'] } });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    const data = await res.json();
    // Product Rule: strip any price fields before they reach the UI tier
    assertNoPrice(data, 'api-response');
    return data;
  }

  // Returns null on 404 (allowlist-gated whisky, or ID not found in public allowlist).
  // Non-404 errors are thrown and propagate to the caller.
  async getWhisky(id: string): Promise<WhiskyDetail | null> {
    try {
      return await this.get(`/api/db/public/whiskies/${encodeURIComponent(id)}`);
    } catch (e: any) {
      const msg = e?.message || '';
      if (msg.startsWith('HTTP 404')) return null;
      throw e;
    }
  }

  async getWhiskies(params: WhiskyListParams = {}): Promise<WhiskyListResponse> {
    const limit = Math.min(params.limit ?? 50, 50);
    const offset = params.offset ?? 0;
    const q = params.q;
    const filter = params.filter;
    const searchParams = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (q) searchParams.set('q', q);
    if (filter) searchParams.set('filter', filter);
    return this.get(`/api/db/public/whiskies?${searchParams}`);
  }

  async searchWhiskies(q: string, limit = 50, offset = 0): Promise<WhiskyListResponse> {
    return this.getWhiskies({ q, limit, offset });
  }

  async getDistilleries(limit = 50, offset = 0, filter?: string): Promise<DistilleryListResponse> {
    const searchParams = new URLSearchParams({ limit: String(Math.min(limit, 50)), offset: String(offset) });
    if (filter) searchParams.set('filter', filter);
    return this.get(`/api/db/public/distilleries?${searchParams}`);
  }

  async getFlavorProfile(whiskyId: string): Promise<FlavorProfile> {
    return this.get(`/api/db/public/whiskies/${encodeURIComponent(whiskyId)}/flavor-profile`);
  }

  // Authenticated endpoint for tasting notes (Phase 2)
  // Backend route: /api/db/whiskies/{id}/tasting-notes (requires bearer auth)
  async getTastingNotes(whiskyId: string): Promise<any[]> {
    return this.get(`/api/db/whiskies/${encodeURIComponent(whiskyId)}/tasting-notes`);
  }
}

export default MaltRadarApi;