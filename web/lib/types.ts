export type Body = "moon" | "mars";
export type ValueType = "measured" | "modeled" | "provisional" | "synthetic" | "missing";

export interface Criterion { id: string; label: string; description: string; earth_proxy: string; source_families: string[] }
export interface Objective { id: string; label: string; description: string; multipliers: Record<string, number> }

export interface DataStatus {
  synthetic: boolean;
  label: string;
  data_dir_name: string;
  files: Record<string, string>;
  counts: Record<string, number>;
  value_types: Record<string, number>;
  issues: { level: string; file: string; message: string }[];
  error_count: number;
  warning_count: number;
  collection_meta: Record<string, unknown>;
}

export interface Meta {
  data_status: DataStatus;
  criteria: Criterion[];
  objectives: Objective[];
  default_objective: string;
  default_reference: Record<Body, string>;
  body_weights: Record<Body, Record<string, number>>;
  reference_multipliers: Record<string, Record<string, number>>;
  min_completeness: number;
  value_type_confidence: Record<string, number>;
  non_replicable: Record<Body, string[]>;
  analog_types: Record<string, string>;
  scoring_meta: Record<string, unknown>;
  climates: string[];
  countries: string[];
}

export interface Breakdown {
  criterion_id: string;
  label: string;
  value: number | null;
  value_type: ValueType;
  confidence: number | null;
  base_weight: number;
  effective_weight: number;
  contribution: number | null;
  share: number | null;
  missing: boolean;
  source_id: string;
}

export interface ScoreResult {
  site_id: string;
  ref_id: string;
  objective: string;
  score: number | null;
  score_low: number;
  score_high: number;
  completeness: number;
  confidence: number;
  status: "scored" | "insufficient_evidence" | "no_data";
  breakdown: Breakdown[];
  missing_criteria: string[];
  trait_matches: string[];
  body_relevant: boolean;
  rank: number | null;
}

export interface Site {
  site_id: string;
  name: string;
  country: string;
  region: string;
  lat: number;
  lon: number;
  analog_types: string[];
  climate: string;
  geology: string;
  target_bodies: Body[];
  mission_objectives: string[];
  environment: Record<string, unknown>;
  elevation_m: number | null;
  description: string;
  limitations: string[];
  imagery: { url: string; credit: string; license: string } | null;
  provenance: string;
  coordinate_note: string;
  feature_count: number;
  citations?: string[];
  score_status?: string;
  // present when listed with a reference
  score?: number | null;
  score_low?: number;
  score_high?: number;
  rank?: number | null;
  completeness?: number;
  confidence?: number;
  status?: string;
  trait_matches?: string[];
  missing_criteria?: string[];
  distance_km?: number;
}

export interface FeatureValue { site_id: string; criterion_id: string; value: number | null; unit: string; value_type: ValueType; confidence: number | null; source_id: string; notes: string }
export interface EvidenceItem { statement: string; source_id: string; value_type: ValueType; confidence: number | null; citation: string }

export interface SiteDetail extends Omit<Site, "score"> {
  features: Record<string, FeatureValue>;
  evidence: Record<string, EvidenceItem[]>;
  published_rankings: { ref_id: string; objective: string; score: number | null; rank: number | null }[];
  score?: ScoreResult & Record<string, unknown>;
  reference_scores?: { ref_id: string; name: string; body: Body; score: number | null; rank: number | null; completeness: number; status: string; body_relevant: boolean }[];
  cannot_replicate_on_earth?: Partial<Record<Body, string[]>>;
}

export interface PlanetaryReference {
  ref_id: string;
  body: Body;
  name: string;
  region_type: string;
  lat: number;
  lon_east: number;
  lon_east_360: number | null;
  coordinate_system: string;
  body_radius_km: number;
  diameter_km: number | null;
  gazetteer_feature_id: string | null;
  description: string;
  traits: string[];
  analog_type_affinity: string[];
  citation: string;
  provenance: string;
}

export interface RankingRow extends ScoreResult {
  name: string;
  country: string;
  lat: number;
  lon: number;
  analog_types: string[];
  published: { score: number | null; rank: number | null } | null;
}

export interface RankingsResponse {
  ref_id: string;
  reference_name: string;
  body: Body;
  objective: string;
  user_weights: Record<string, number>;
  effective_weights: Record<string, number>;
  min_completeness: number;
  synthetic: boolean;
  rankings: RankingRow[];
}

export interface CompareResponse {
  ref_id: string;
  reference_name: string;
  objective: string;
  criteria: Criterion[];
  sites: (Site & { result: ScoreResult; evidence: Record<string, EvidenceItem[]> })[];
  matrix: Record<string, string | number | null>[];
  synthetic: boolean;
}

export interface RecommendResult {
  site_id: string; name: string; country: string; lat: number; lon: number; analog_types: string[];
  score: number; score_low: number; score_high: number; rank: number; completeness: number; confidence: number;
  why: string[]; caveats: string[]; site_limitations: string[]; breakdown: Breakdown[];
}

export interface RecommendResponse {
  query: string;
  interpretation: { body: Body; ref_id: string; reference_name: string; objective: string; objective_label: string; analog_types: string[]; matched_terms: string[]; method: string };
  results: RecommendResult[];
  excluded_insufficient_evidence: { site_id: string; completeness: number }[];
  cannot_replicate_on_earth: string[];
  notes: string[];
}

export interface SensitivityResponse {
  ref_id: string; objective: string; tracked_sites: string[]; multipliers: number[];
  sweeps: Record<string, Record<string, number | null>[]>;
  max_rank_shift_by_criterion: Record<string, number>;
}

export interface ClustersResponse {
  k: number;
  clusters: { cluster: number; members: string[]; centroid: Record<string, number>; defining_criteria: string[]; dominant_analog_types: string[]; label: string }[];
  assignments: Record<string, number>;
  method: string;
}

export interface DatasetEntry { source_id: string; name: string; provider: string; url: string; license: string; data_type: string; usage: string; status: string; provenance: string; notes: string }
