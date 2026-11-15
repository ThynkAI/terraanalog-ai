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
  return out;
}
