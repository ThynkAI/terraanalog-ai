import type { PlanetaryReference, ScoreResult, Site } from "./types";
export interface StrictEvidence {
  method: string; scope: string; references: string[]; spearman_strict_vs_base: number; max_rank_shift: number;
  top5_base: string[]; top5_strict: string[]; top5_base_names: string[]; top5_strict_names: string[];
}
export interface CaseStudy {
  id: string; site_id: string; ref_id: string; objective: string; title: string; question: string;
  novelty_status: string; novelty_finding: string; interpretation: string; limits: string[];
  stress_label: string; stress_reason: string; stress_weights: Record<string, number>; field_plan: string[];
  sources: { title: string; url: string; supports: string }[];
  site: Site; reference: PlanetaryReference; objective_label: string; exploratory_reference: boolean;
  advantage_vs_best_benchmark: number | null; strict_evidence: StrictEvidence | null;
  comparisons: { site_id: string; name: string; candidate: boolean; result: ScoreResult; stress_result: ScoreResult }[];
  measurements: {
    source_files: string[]; sampling_note: string; earth_native_dem_m: number; planet_dem_product: string;
    comparison_grid_m: number; radius_m: number; earth_valid_fraction: number | null;
    earth_precipitation_mm_yr: number | null; earth_permafrost_probability: number | null; earth_permafrost_source: string;
    metrics: { label: string; unit: string; earth: number | null; planet: number | null; provenance: string }[];
  };
}
export interface CaseStudiesResponse { available: boolean; reason?: string; reviewed_on: string; review_scope: string; scoring_note: string; cases: CaseStudy[] }
