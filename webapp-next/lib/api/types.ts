export interface WhiskySummary {
  whisky_id: string;
  name: string;
  brand?: string | null;
  distillery_id?: string | null;
  distillery_name?: string | null;
  region?: string | null;
  country?: string | null;
  type?: string | null;
  age?: string | null;
  abv?: number | null;
  // NO price fields — AGENTS.md Product Rule
  flavor_profile?: any | null;
  data_confidence?: string | null;
}

export interface WhiskyDetail extends WhiskySummary {
  original_name?: string | null;
  meta_critic_score?: number | null;
  user_score?: number | null;
  age_statement?: string | null;
  nas?: number | null;
  bottle_size?: string | null;
  cask_type?: string | null;
  finish_type?: string | null;
  cask_strength?: number | null;
  notes_for_review?: string | null;
  superseded_by?: string | null;
}

export interface DistillerySummary {
  distillery_id: string;
  name: string;
  whisky_count: number;
}

export interface FlavorProfile {
  whisky_id: string;
  whisky_name?: string;
  flavor_vector?: string | null;
  flavor_profile?: string | null;
  flavor_tags?: string | null;
  flavor_source?: string | null;
  flavor_data_confidence?: string | null;
  production_rating?: string | null;
  production_region?: string | null;
  notes_for_review?: string | null;
  source_count?: number;
  evidence_count?: number;
  enrichment_version?: string | null;
}

export interface WhiskyListResponse {
  items: WhiskySummary[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface DistilleryListResponse {
  items: DistillerySummary[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface SearchResult extends WhiskySummary {}

export interface FilterParams {
  category?: string;
  region?: string;
  flavor?: string;
}

export interface WhiskyListParams {
  limit?: number;
  offset?: number;
  q?: string;
  // distillery_id NOT supported by PUBLIC endpoint
  filter?: string;
}

export type NoPrice<T> = Omit<T, 'production_price' | 'price_value' | 'price_context' | 'price_currency' | 'price_per_ml' | 'pour_size_ml'>;