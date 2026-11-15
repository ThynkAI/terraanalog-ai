"use client";
import { useMemo, useState } from "react";
import { fmtLat, fmtLonEast } from "@/lib/format";
import type { Body, PlanetaryReference } from "@/lib/types";

/** NASA Trek WMTS layers (equirectangular / simple-cylindrical tile matrix, TopLeftCorner -180,90; level 0 = 2x1 tiles).
 *  Verified to return HTTP 200 on 2026-11-15 via their WMTSCapabilities.xml. Tile path = {z}/{row}/{col}.jpg */
const TREK: Record<Body, { url: string; credit: string }> = {
  moon: { url: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm", credit: "LRO WAC Global Mosaic — NASA/GSFC/Arizona State University via NASA Moon Trek" },
  mars: { url: "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm", credit: "Viking MDIM 2.1 colorized mosaic — NASA/JPL/USGS via NASA Mars Trek" },
};
const RADIUS: Record<Body, number> = { moon: 1737.4, mars: 3389.5 };
const W = 1440;
const H = 720;
const S = 4; // svg units per degree
const toX = (lonEast: number) => (lonEast + 180) * S;
const toY = (lat: number) => (90 - lat) * S;

interface VB { x: number; y: number; w: number; h: number }
const FULL: VB = { x: 0, y: 0, w: W, h: H };

function clampVB(v: VB): VB {
  const w = Math.min(W, Math.max(90, v.w));
  const h = w / 2;
  return { w, h, x: Math.min(W - w, Math.max(0, v.x)), y: Math.min(H - h, Math.max(0, v.y)) };
}

function tilesFor(vb: VB) {
  const zoom = W / vb.w;
  const z = zoom >= 6 ? 4 : zoom >= 3 ? 3 : 2;
  const cols = 2 ** (z + 1);
  const rows = 2 ** z;
  const tw = W / cols;
  const out: { z: number; r: number; c: number; x: number; y: number; s: number }[] = [];
  for (let r = 0; r < rows; r++)
    for (let c = 0; c < cols; c++) {
      const x = c * tw, y = r * tw;
      if (x + tw < vb.x || x > vb.x + vb.w || y + tw < vb.y || y > vb.y + vb.h) continue;
      out.push({ z, r, c, x, y, s: tw });
    }
  return out;
}

export function PlanetViewer({ body, refs, selected, onSelect }: { body: Body; refs: PlanetaryReference[]; selected: string | null; onSelect: (id: string) => void }) {
  const [vb, setVb] = useState<VB>(FULL);
  const [imgFail, setImgFail] = useState(0);
  const [hover, setHover] = useState<{ lat: number; lon: number } | null>(null);
  const tiles = useMemo(() => tilesFor(vb), [vb]);
  const accent = body === "moon" ? "#c9ced6" : "#f08a55";
  const sel = refs.find((r) => r.ref_id === selected);

  const zoom = (f: number, cx?: number, cy?: number) =>
    setVb((v) => {
      const w = v.w / f;
      const ccx = cx ?? v.x + v.w / 2;
      const ccy = cy ?? v.y + v.h / 2;
      return clampVB({ x: ccx - w / 2, y: ccy - w / 4, w, h: w / 2 });
    });
  const pan = (dx: number, dy: number) => setVb((v) => clampVB({ ...v, x: v.x + dx * v.w, y: v.y + dy * v.h }));
  const focusSel = () => sel && setVb(clampVB({ x: toX(sel.lon_east) - 180, y: toY(sel.lat) - 90, w: 360, h: 180 }));

  const onKey = (e: React.KeyboardEvent) => {
    const k = e.key;
    if (k === "+" || k === "=") zoom(1.5);
    else if (k === "-" || k === "_") zoom(1 / 1.5);
    else if (k === "ArrowLeft") pan(-0.15, 0);
    else if (k === "ArrowRight") pan(0.15, 0);
    else if (k === "ArrowUp") pan(0, -0.15);
    else if (k === "ArrowDown") pan(0, 0.15);
    else if (k === "0") setVb(FULL);
    else return;
    e.preventDefault();
  };

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = vb.x + ((e.clientX - rect.left) / rect.width) * vb.w;
    const py = vb.y + ((e.clientY - rect.top) / rect.height) * vb.h;
    setHover({ lon: px / S - 180, lat: 90 - py / S });
  };

  const polar = refs.filter((r) => r.lat <= -80);
  const markerR = 7 * (vb.w / W) + 2.2 * (vb.w / W);

  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black">
        <svg
          viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
          className="block h-auto w-full"
          role="application"
          aria-label={`${body === "moon" ? "Moon" : "Mars"} equirectangular reference map (planetocentric latitude, east-positive longitude). Arrow keys pan, plus and minus zoom, 0 resets. Reference markers are focusable.`}
          tabIndex={0}
          onKeyDown={onKey}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
          data-testid={`planet-viewer-${body}`}
        >
          <rect x={0} y={0} width={W} height={H} fill="#0b0f18" />
          {imgFail < 3 && tiles.map((t) => (
            <image
              key={`${t.z}-${t.r}-${t.c}`}
              href={`${TREK[body].url}/${t.z}/${t.r}/${t.c}.jpg`}
              x={t.x} y={t.y} width={t.s + 0.5} height={t.s + 0.5}
              preserveAspectRatio="none"
              onError={() => setImgFail((n) => n + 1)}
            />
          ))}
          {/* graticule every 30° */}
          {Array.from({ length: 13 }, (_, i) => -180 + i * 30).map((lon) => (
            <line key={`m${lon}`} x1={toX(lon)} x2={toX(lon)} y1={0} y2={H} stroke="#fff" strokeOpacity={0.12} strokeWidth={vb.w / W} />
          ))}
          {Array.from({ length: 7 }, (_, i) => -90 + i * 30).map((lat) => (
            <line key={`p${lat}`} y1={toY(lat)} y2={toY(lat)} x1={0} x2={W} stroke="#fff" strokeOpacity={lat === 0 ? 0.25 : 0.12} strokeWidth={vb.w / W} />
          ))}
          {Array.from({ length: 11 }, (_, i) => -150 + i * 30).map((lon) => (
            <text key={`tl${lon}`} x={toX(lon) + 2} y={toY(0) - 3} fontSize={10 * (vb.w / W) * 1.4} fill="#fff" fillOpacity={0.5}>{lon}°E</text>
          ))}
          {refs.map((r) => {
            const active = r.ref_id === selected;
            const x = toX(r.lon_east);
            const y = toY(r.lat);
            return (
              <g
                key={r.ref_id}
                role="button"
                tabIndex={0}
                aria-label={`${r.name}, ${fmtLat(r.lat)} ${fmtLonEast(r.lon_east)}${active ? ", selected" : ""}`}
                aria-pressed={active}
                onClick={() => onSelect(r.ref_id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(r.ref_id); } }}
                style={{ cursor: "pointer" }}
              >
                <circle cx={x} cy={y} r={markerR * (active ? 1.6 : 1)} fill={active ? accent : "#0a1020"} fillOpacity={active ? 0.9 : 0.75} stroke={accent} strokeWidth={markerR * 0.35} />
                <text x={x + markerR * 1.8} y={y + markerR * 0.6} fontSize={markerR * 1.9} fill="#fff" stroke="#000" strokeWidth={markerR * 0.25} paintOrder="stroke">{r.name.split(" (")[0]}</text>
              </g>
            );
          })}
        </svg>
        <div className="no-print absolute right-2 top-2 flex flex-col gap-1">
          <button className="btn px-2 py-1" onClick={() => zoom(1.5)} aria-label="Zoom in">＋</button>
          <button className="btn px-2 py-1" onClick={() => zoom(1 / 1.5)} aria-label="Zoom out">－</button>
          <button className="btn px-2 py-1 text-xs" onClick={() => setVb(FULL)} aria-label="Reset view">⟲</button>
          <button className="btn px-2 py-1 text-xs" onClick={focusSel} disabled={!sel} aria-label="Zoom to selected reference">◎</button>
        </div>
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 flex justify-between bg-gradient-to-t from-black/80 to-transparent px-3 pb-1.5 pt-4 text-[10px] text-lunar-300">
          <span>{imgFail >= 3 ? "Imagery unavailable — schematic graticule shown" : TREK[body].credit}</span>
          <span className="font-mono">{hover ? `${fmtLat(hover.lat)} ${fmtLonEast(hover.lon)}` : "planetocentric · +E"}</span>
        </div>
      </div>
      {polar.length > 0 && <PolarInset body={body} refs={polar} selected={selected} onSelect={onSelect} />}
    </div>
  );
}

/** South-polar stereographic inset on a SPHERE of the body's IAU mean radius (no Earth ellipsoid). */
function PolarInset({ body, refs, selected, onSelect }: { body: Body; refs: PlanetaryReference[]; selected: string | null; onSelect: (id: string) => void }) {
  const R = RADIUS[body];
  const maxColat = Math.max(6, Math.ceil(Math.max(...refs.map((r) => 90 + r.lat)) + 1.5));
  const rho = (colatDeg: number) => 2 * R * Math.tan((colatDeg * Math.PI) / 180 / 2);
  const rMax = rho(maxColat);
  const size = 300;
  const k = (size / 2 - 16) / rMax;
  const pt = (lat: number, lon: number) => {
    const p = rho(90 + lat) * k;
    const l = (lon * Math.PI) / 180;
    return { x: size / 2 + p * Math.sin(l), y: size / 2 + p * Math.cos(l) }; // 0°E at bottom (Earth-facing for the Moon)
  };
  const rings = Array.from({ length: Math.floor(maxColat / 2) }, (_, i) => (i + 1) * 2);
  const scaleKm = body === "moon" ? 50 : 200;
  const accent = body === "moon" ? "#c9ced6" : "#f08a55";
  return (
    <figure className="panel p-3">
      <figcaption className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <span className="panel-title">South-polar stereographic inset</span>
        <span className="text-[11px] text-lunar-400">Sphere R = {R} km (IAU mean radius) · rings every 2° latitude · 0°E at bottom</span>
      </figcaption>
      <svg viewBox={`0 0 ${size} ${size}`} className="mx-auto block w-full max-w-[340px]" role="group" aria-label="South polar stereographic schematic">
        <circle cx={size / 2} cy={size / 2} r={rMax * k} fill="#0b0f18" stroke="#ffffff22" />
        {rings.map((c) => (
          <g key={c}>
            <circle cx={size / 2} cy={size / 2} r={rho(c) * k} fill="none" stroke="#ffffff1f" />
            <text x={size / 2 + 3} y={size / 2 - rho(c) * k + 10} fontSize={8} fill="#8b94a5">{-90 + c}°</text>
          </g>
        ))}
        {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((lon) => {
          const e = pt(-90 + maxColat, lon);
          return (
            <g key={lon}>
              <line x1={size / 2} y1={size / 2} x2={e.x} y2={e.y} stroke="#ffffff14" />
              {lon % 90 === 0 && <text x={e.x} y={e.y} fontSize={8} fill="#8b94a5" textAnchor="middle" dy={lon === 180 ? -3 : 9}>{lon > 180 ? lon - 360 : lon}°E</text>}
            </g>
          );
        })}
        {refs.map((r, i) => {
          const p = pt(r.lat, r.lon_east);
          const left = i % 2 === 1;
          const dy = 3 + (i % 3 === 2 ? 11 : 0);
          const active = r.ref_id === selected;
          return (
            <g key={r.ref_id} role="button" tabIndex={0} aria-label={`${r.name} (polar inset), ${((90 + r.lat) * Math.PI / 180 * R).toFixed(0)} km from the pole`}
              onClick={() => onSelect(r.ref_id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(r.ref_id); } }} style={{ cursor: "pointer" }}>
              <circle cx={p.x} cy={p.y} r={active ? 6 : 4} fill={active ? accent : "#0a1020"} stroke={accent} strokeWidth={1.5} />
              <text x={left ? p.x - 7 : p.x + 7} y={p.y + dy} fontSize={9} fill="#fff" textAnchor={left ? "end" : "start"} stroke="#000" strokeWidth={2} paintOrder="stroke">{r.name.split(" (")[0].replace(" vicinity", "").replace(" crater & massif", "").replace(" crater rim", "")}</text>
            </g>
          );
        })}
        <g transform={`translate(12 ${size - 14})`}>
          <line x1={0} x2={scaleKm * k} y1={0} y2={0} stroke="#fff" strokeWidth={2} />
          <text x={0} y={-4} fontSize={8} fill="#c9ced6">{scaleKm} km</text>
        </g>
      </svg>
    </figure>
  );
}
