"use client";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { feature } from "topojson-client";
import land110 from "world-atlas/land-110m.json";
import { ANALOG_TYPE_COLORS } from "@/lib/constants";
import { scoreColor } from "@/lib/format";

export type Basemap = "vector" | "satellite" | "terrain";
export interface MapSite {
  site_id: string;
  name: string;
  lat: number;
  lon: number;
  analog_types: string[];
  score?: number | null;
  rank?: number | null;
}

// Verified (HTTP 200, 2026-11-15) NASA GIBS WMTS endpoints in Web Mercator (EPSG:3857).
const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
const SAT_TILES = `${GIBS}/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`;
const TERRAIN_TILES = `${GIBS}/ASTER_GDEM_Greyscale_Shaded_Relief/default/GoogleMapsCompatible_Level12/{z}/{y}/{x}.jpg`;

function graticule(step = 30) {
  const lines: GeoJSON.Feature[] = [];
  for (let lon = -180; lon <= 180; lon += step) lines.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: Array.from({ length: 37 }, (_, i) => [lon, -90 + i * 5]) } });
  for (let lat = -60; lat <= 60; lat += step) lines.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: Array.from({ length: 73 }, (_, i) => [-180 + i * 5, lat]) } });
  return { type: "FeatureCollection", features: lines } as GeoJSON.FeatureCollection;
}

export function buildStyle(): StyleSpecification {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const land = feature(land110 as any, (land110 as any).objects.land) as unknown as GeoJSON.FeatureCollection;
  return {
    version: 8,
    projection: { type: "globe" },
    sources: {
      land: { type: "geojson", data: land, attribution: "Land: Natural Earth (public domain)" },
      grat: { type: "geojson", data: graticule() },
      sat: { type: "raster", tiles: [SAT_TILES], tileSize: 256, maxzoom: 8, attribution: "Imagery: NASA GIBS Blue Marble" },
      terrain: { type: "raster", tiles: [TERRAIN_TILES], tileSize: 256, maxzoom: 12, attribution: "Relief: NASA GIBS / ASTER GDEM (NASA/METI)" },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#0b1a33" } },
      { id: "sat", type: "raster", source: "sat", layout: { visibility: "none" } },
      { id: "terrain", type: "raster", source: "terrain", layout: { visibility: "none" }, paint: { "raster-opacity": 0.9 } },
      { id: "land", type: "fill", source: "land", paint: { "fill-color": "#1c2740", "fill-opacity": 1 } },
      { id: "land-line", type: "line", source: "land", paint: { "line-color": "#46557a", "line-width": 0.6 } },
      { id: "grat", type: "line", source: "grat", paint: { "line-color": "#8b94a5", "line-opacity": 0.12, "line-width": 0.6 } },
    ],
  } as StyleSpecification;
}

function markerHTML(s: MapSite, selected: boolean, compared: boolean) {
  const type = s.analog_types[0] ?? "other";
  const fill = ANALOG_TYPE_COLORS[type] ?? "#aab2bf";
  const ring = scoreColor(s.score);
  const size = selected ? 34 : 26;
  const shapes: Record<string, string> = {
    polar_desert: `<path d="M10 3v14M4 6.5l12 7M16 6.5l-12 7" stroke="${fill}" stroke-width="2.2" stroke-linecap="round"/>`,
    permafrost_ice: `<polygon points="10,3 16,6.5 16,13.5 10,17 4,13.5 4,6.5" fill="none" stroke="${fill}" stroke-width="2"/><circle cx="10" cy="10" r="2.3" fill="${fill}"/>`,
    basaltic_volcanic: `<polygon points="10,4 16.5,15.5 3.5,15.5" fill="${fill}"/>`,
    impact_crater: `<circle cx="10" cy="10" r="5.6" fill="none" stroke="${fill}" stroke-width="2.4"/><circle cx="10" cy="10" r="1.7" fill="${fill}"/>`,
    lava_tube_cave: `<path d="M4 15.5V10a6 6 0 0 1 12 0v5.5h-3v-5a3 3 0 0 0-6 0v5z" fill="${fill}"/>`,
    hyperarid_desert: `<circle cx="10" cy="8" r="3" fill="${fill}"/><path d="M3.5 14.5c2.2-2.2 4.4-2.2 6.5 0s4.4 2.2 6.5 0" stroke="${fill}" stroke-width="1.8" fill="none"/>`,
    acidic_aqueous: `<path d="M10 3.5C10 3.5 5.5 9 5.5 12a4.5 4.5 0 0 0 9 0c0-3-4.5-8.5-4.5-8.5z" fill="${fill}"/>`,
    high_altitude: `<path d="M3 15.5l5-8.5 2.5 4 2.5-6 4.5 10.5z" fill="${fill}"/>`,
    evaporite_basin: `<polygon points="10,3.5 16.5,10 10,16.5 3.5,10" fill="none" stroke="${fill}" stroke-width="2"/><polygon points="10,7.3 12.7,10 10,12.7 7.3,10" fill="${fill}"/>`,
  };
  shapes.aqueous_alteration = shapes.acidic_aqueous;
  shapes.arid_desert = shapes.hyperarid_desert;
  return `<svg width="${size}" height="${size}" viewBox="0 0 20 20" aria-hidden="true">
    <circle cx="10" cy="10" r="9.2" fill="#0a1020" fill-opacity="0.92" stroke="${ring}" stroke-width="${selected ? 1.8 : 1.3}"/>
    ${compared ? `<circle cx="10" cy="10" r="9.6" fill="none" stroke="#67d4ee" stroke-width="0.9" stroke-dasharray="2 1.4"/>` : ""}
    ${shapes[type] ?? `<rect x="6" y="6" width="8" height="8" fill="${fill}"/>`}
  </svg>`;
}

export default function EarthMap({
  sites,
  selectedId,
  compareIds = [],
  onSelect,
  basemap = "vector",
  projection = "globe",
  focus,
  height = "100%",
  label = "Interactive globe of Earth analog sites",
}: {
  sites: MapSite[];
  selectedId?: string | null;
  compareIds?: string[];
  onSelect?: (id: string) => void;
  basemap?: Basemap;
  projection?: "globe" | "mercator";
  focus?: { lat: number; lon: number; zoom?: number } | null;
  height?: string;
  label?: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<Map<string, { m: maplibregl.Marker; node: HTMLButtonElement }>>(new Map());
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!el.current) return;
    let m: maplibregl.Map;
    try {
      m = new maplibregl.Map({
        container: el.current,
        style: buildStyle(),
        center: [-40, 25],
        zoom: 1.15,
        attributionControl: { compact: true },
        keyboard: true,
        dragRotate: true,
        renderWorldCopies: false,
      });
    } catch (e) {
      setFailed((e as Error).message || "WebGL unavailable");
      return;
    }
    m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    m.on("load", () => setReady(true));
    m.on("error", (ev) => {
      // tile errors are non-fatal; keep the vector base map
      if (process.env.NODE_ENV !== "production") console.warn("map error", ev?.error?.message);
    });
    map.current = m;
    const canvas = m.getCanvas();
    canvas.setAttribute("aria-label", `${label}. Use arrow keys to pan, plus and minus to zoom. Site markers are focusable buttons.`);
    canvas.setAttribute("role", "region");
    return () => {
      markers.current.forEach(({ m: mk }) => mk.remove());
      markers.current.clear();
      m.remove();
      map.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // basemap + projection
  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    m.setLayoutProperty("sat", "visibility", basemap === "satellite" ? "visible" : "none");
    m.setLayoutProperty("terrain", "visibility", basemap === "terrain" ? "visible" : "none");
    m.setPaintProperty("land", "fill-opacity", basemap === "vector" ? 1 : 0);
    m.setPaintProperty("land-line", "line-color", basemap === "vector" ? "#46557a" : "#ffffff");
    m.setPaintProperty("land-line", "line-opacity", basemap === "vector" ? 1 : 0.35);
    m.setProjection({ type: projection });
  }, [basemap, projection, ready]);

  // markers
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const keep = new Set(sites.map((s) => s.site_id));
    markers.current.forEach((v, k) => {
      if (!keep.has(k)) {
        v.m.remove();
        markers.current.delete(k);
      }
    });
    sites.forEach((s) => {
      const selected = s.site_id === selectedId;
      const compared = compareIds.includes(s.site_id);
      let entry = markers.current.get(s.site_id);
      if (!entry) {
        const node = document.createElement("button");
        node.type = "button";
        node.className = "site-marker";
        node.dataset.siteId = s.site_id;
        node.addEventListener("click", (e) => {
          e.stopPropagation();
          onSelectRef.current?.(s.site_id);
        });
        const mk = new maplibregl.Marker({ element: node }).setLngLat([s.lon, s.lat]).addTo(m);
        entry = { m: mk, node };
        markers.current.set(s.site_id, entry);
      }
      entry.m.setLngLat([s.lon, s.lat]);
      entry.node.innerHTML = markerHTML(s, selected, compared);
      entry.node.setAttribute(
        "aria-label",
        `${s.name}${s.rank ? `, rank ${s.rank}` : ""}${s.score !== undefined ? `, score ${s.score ?? "insufficient evidence"}` : ""}${compared ? ", in comparison" : ""}`,
      );
      entry.node.setAttribute("aria-pressed", selected ? "true" : "false");
      entry.node.style.zIndex = selected ? "5" : "1";
      entry.node.title = s.name;
    });
  }, [sites, selectedId, compareIds, ready]);

  // focus / fly
  useEffect(() => {
    const m = map.current;
    if (!m || !focus) return;
    const opts = { center: [focus.lon, focus.lat] as [number, number], zoom: focus.zoom ?? Math.max(m.getZoom(), 1.7) };
    if (reduced) m.jumpTo(opts);
    else m.flyTo({ ...opts, speed: 1.4, essential: false });
  }, [focus, reduced]);

  if (failed) {
    return (
      <div className="flex h-full min-h-[300px] items-center justify-center p-6 text-center text-sm text-lunar-300" role="alert">
        Interactive map unavailable ({failed}). The ranked list remains fully usable.
      </div>
    );
  }
  return (
    <div className="relative h-full w-full" style={{ height }}>
      <div ref={el} className="h-full w-full" style={{ position: "absolute", inset: 0 }} data-testid="earth-map" />
      {!ready && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-lunar-300" role="status">
          Initialising globe…
        </div>
      )}
    </div>
  );
}
