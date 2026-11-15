"use client";
import { createContext, useContext } from "react";
import { useApi } from "@/lib/api";
import type { Meta, PlanetaryReference } from "@/lib/types";

interface Ctx {
  meta: Meta | null;
  refs: PlanetaryReference[];
  error: string | null;
  loading: boolean;
}
const MetaCtx = createContext<Ctx>({ meta: null, refs: [], error: null, loading: true });

export function MetaProvider({ children }: { children: React.ReactNode }) {
  const m = useApi<Meta>("/meta");
  const r = useApi<{ references: PlanetaryReference[] }>("/planetary-references");
  return (
    <MetaCtx.Provider value={{ meta: m.data, refs: r.data?.references ?? [], error: m.error || r.error, loading: m.loading || r.loading }}>
      {children}
    </MetaCtx.Provider>
  );
}

export const useMeta = () => useContext(MetaCtx);

export function useCriteriaLabels() {
  const { meta } = useMeta();
  const out: Record<string, string> = {};
  meta?.criteria.forEach((c) => (out[c.id] = c.label));
  meta?.features?.forEach((f) => (out[f.id] = f.label));
  return out;
}

/** Feature groups that carry fidelity weight (11 for the research dataset; all criteria for the fixture shape). */
export function useFidelityFeatures() {
  const { meta } = useMeta();
  const feats = meta?.features?.length ? meta.features : (meta?.criteria ?? []).map((c) => ({ id: c.id, label: c.label, description: c.description, earth_proxy: c.earth_proxy, per_reference: false, in_fidelity_score: true }));
  return feats.filter((f) => f.in_fidelity_score);
}

/** Objectives usable with a body: shared ones (no body) plus that body's mission profiles. */
export function useObjectivesFor(body?: string | null) {
  const { meta } = useMeta();
  return (meta?.objectives ?? []).filter((o) => !body || !o.body || o.body.toLowerCase() === body);
}
