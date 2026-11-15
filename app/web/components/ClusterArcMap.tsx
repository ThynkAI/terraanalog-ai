"use client";
/**
 * Analog Discovery map — deck.gl layers over an offline MapLibre basemap.
 *
 * Why deck.gl here: the discovery question is "which Earth environments behave alike, and where are they?".
 * Feature-space clusters are global (an Antarctic and an Arctic site can share a cluster), which a scatter
 * plot cannot show geographically. ArcLayer links each cluster member to its cluster anchor (the member with
 * the highest score vs the selected planetary reference), ScatterplotLayer encodes cluster (colour) and score
 * (radius). All geometry is EARTH-only (WGS84); planetary reference coordinates are never projected onto Earth.
 */
import { MapboxOverlay } from "@deck.gl/mapbox";
import { ArcLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { buildStyle } from "@/components/EarthMap";
import { SERIES } from "@/components/Charts";

import { clusterArcs, type ClusterSite } from "@/lib/clusterArcs";

function hexToRgb(h: string): [number, number, number] {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export default function ClusterArcMap({ sites }: { sites: ClusterSite[] }) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const overlay = useRef<MapboxOverlay | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const { arcs, anchors } = useMemo(() => clusterArcs(sites), [sites]);

  useEffect(() => {
    if (!el.current) return;
    try {
      const style = buildStyle();
      style.projection = { type: "mercator" };
      const m = new maplibregl.Map({ container: el.current, style, center: [-20, 25], zoom: 0.55, renderWorldCopies: false, minZoom: 0, attributionControl: { compact: true }, dragRotate: false });
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      const ov = new MapboxOverlay({ interleaved: false, layers: [] });
      m.addControl(ov as unknown as maplibregl.IControl);
      map.current = m;
      overlay.current = ov;
      return () => { m.remove(); map.current = null; overlay.current = null; };
    } catch (e) {
      setFailed(String(e));
    }
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !sites.length) return;
    // Whole-world width (the container is 5:4 so a full Mercator world from ~80°S to ~80°N fits without wrapped copies).
    const lats = sites.map((s) => s.lat);
    const fit = () => m.fitBounds([[-180, Math.max(-80, Math.min(...lats) - 3)], [180, Math.min(80, Math.max(...lats) + 3)]], { padding: 0, animate: false });
    fit();
    m.once("idle", fit);
  }, [sites]);

  useEffect(() => {
    if (!overlay.current) return;
    const col = (c: number) => hexToRgb(SERIES[c % SERIES.length]);
    overlay.current.setProps({
      layers: [
        new ArcLayer({
          id: "cluster-arcs", data: arcs, greatCircle: false, getHeight: 0.35, getWidth: 1.6,
          getSourcePosition: (d: (typeof arcs)[number]) => [d.from.lon, d.from.lat],
          getTargetPosition: (d: (typeof arcs)[number]) => [d.to.lon, d.to.lat],
          getSourceColor: (d: (typeof arcs)[number]) => [...col(d.cluster), 200],
          getTargetColor: (d: (typeof arcs)[number]) => [...col(d.cluster), 90],
        }),
        new ScatterplotLayer<ClusterSite>({
          id: "cluster-sites", data: sites, pickable: true, stroked: true, radiusUnits: "pixels", lineWidthUnits: "pixels",
          getPosition: (d) => [d.lon, d.lat],
          getRadius: (d) => 4 + ((d.score ?? 0) / 100) * 9,
          getFillColor: (d) => [...col(d.cluster), d.score === null ? 70 : 220],
          getLineColor: (d) => (anchors[d.cluster] === d.site_id ? [255, 255, 255, 255] : [10, 16, 32, 255]),
          getLineWidth: (d) => (anchors[d.cluster] === d.site_id ? 2 : 1),
          onHover: (info) => setHover(info.object ? `${info.object.name} — cluster ${info.object.cluster + 1}, score ${info.object.score ?? "insufficient evidence"}` : null),
          updateTriggers: { getLineColor: [anchors], getLineWidth: [anchors] },
        }),
        new TextLayer<ClusterSite>({
          id: "cluster-labels", data: sites.filter((s) => anchors[s.cluster] === s.site_id), getPosition: (d) => [d.lon, d.lat],
          getText: (d) => `C${d.cluster + 1} ${d.site_id}`, getSize: 11, getColor: [235, 238, 245, 255], getPixelOffset: [0, -16],
          fontFamily: "ui-monospace, monospace", outlineWidth: 2, outlineColor: [10, 16, 32, 255], fontSettings: { sdf: true },
        }),
      ],
    });
  }, [arcs, anchors, sites]);

  const summary = Object.entries(anchors).map(([c, a]) => `cluster ${Number(c) + 1} anchored at ${a} with ${sites.filter((s) => s.cluster === Number(c)).length} site(s)`).join("; ");
  return (
    <figure className="m-0">
      <div className="relative overflow-hidden rounded-lg border border-white/10" style={{ aspectRatio: "5 / 4" }} data-testid="cluster-arc-map">
        <div ref={el} style={{ position: "absolute", inset: 0 }} role="img" aria-label={`deck.gl map of feature-space clusters on Earth: ${summary || "loading"}`} />
        {hover && <div className="pointer-events-none absolute left-2 top-2 rounded bg-black/70 px-2 py-1 text-xs text-white">{hover}</div>}
        {failed && <p className="absolute inset-0 grid place-items-center p-4 text-center text-sm text-lunar-300">WebGL unavailable — the cluster membership list beside this map has the same information. ({failed})</p>}
      </div>
      <figcaption className="mt-1 text-[11px] text-lunar-400">
        deck.gl ArcLayer + ScatterplotLayer. Colour = cluster, radius = score vs the selected reference, white ring = cluster anchor (highest-scoring member).
        Arcs connect sites that are similar in feature space — they are not travel routes, and Moon/Mars coordinates are never drawn on Earth.
      </figcaption>
    </figure>
  );
}
