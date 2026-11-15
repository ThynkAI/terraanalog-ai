"use client";
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, Legend, Line, LineChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { scoreColor } from "@/lib/format";
import type { Breakdown } from "@/lib/types";

export const SERIES = ["#e8743b", "#67d4ee", "#c9ced6", "#a78bfa", "#4ade80", "#fbbf24"];
const axis = { stroke: "#8b94a5", fontSize: 11 };
const tooltipStyle = { background: "#0d1426", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, fontSize: 12, color: "#e3e7ee" };

export function RadarCompare({ data, series, height = 340, domain = [0, 5] }: { data: Record<string, string | number | null>[]; series: { key: string; name: string }[]; height?: number; domain?: [number, number] }) {
  const completeRows = data.filter((row) => series.every((s) => row[s.key] != null));
  const omitted = data.length - completeRows.length;
  return (
    <div><p className="mb-2 text-xs text-lunar-300">{omitted ? `${omitted} incomplete criteria omitted from this radar for all sites; inspect the evidence table for missing values.` : "Radar uses criteria available for every selected site."} Missing values are never plotted as zero.</p>
    <div style={{ width: "100%", height }} role="img" aria-label={`Radar chart comparing ${series.map((s) => s.name).join(", ")} across criteria (${domain[0]}–${domain[1]}). Incomplete criteria are omitted for all sites.`}>
      <ResponsiveContainer>
        <RadarChart data={completeRows} outerRadius="72%">
          <PolarGrid stroke="rgba(255,255,255,0.12)" />
          <PolarAngleAxis dataKey="label" tick={{ fill: "#c9ced6", fontSize: 11 }} />
          <PolarRadiusAxis domain={domain} tickCount={6} tick={{ fill: "#8b94a5", fontSize: 10 }} angle={90} />
          {series.map((s, i) => (
            <Radar key={s.key} name={s.name} dataKey={s.key} stroke={SERIES[i % SERIES.length]} fill={SERIES[i % SERIES.length]} fillOpacity={0.14} strokeWidth={2} isAnimationActive={false} />
          ))}
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Tooltip contentStyle={tooltipStyle} />
        </RadarChart>
      </ResponsiveContainer>
    </div></div>
  );
}

export function RankingChart({ rows, height }: { rows: { name: string; score: number | null; low: number; high: number }[]; height?: number }) {
  const data = rows.filter((r) => r.score !== null).map((r) => ({ ...r, err: [r.score! - r.low, r.high - r.score!] }));
  const h = height ?? Math.max(180, data.length * 30 + 40);
  return (
    <div style={{ width: "100%", height: h }} className="overflow-hidden" role="img" aria-label={`Ranking bar chart: ${data.map((d) => `${d.name} ${d.score}`).join("; ")}`}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
          <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.06)" />
          <XAxis type="number" domain={[0, 100]} {...axis} />
          <YAxis type="category" dataKey="name" width={170} tick={{ fill: "#c9ced6", fontSize: 11 }} />
          <Tooltip contentStyle={{ ...tooltipStyle, whiteSpace: "normal", maxWidth: 220 }} formatter={(v: number) => [v, "score"]} />
          <Bar dataKey="score" isAnimationActive={false} radius={[0, 4, 4, 0]}>
            {data.map((d) => <Cell key={d.name} fill={scoreColor(d.score)} />)}
            <ErrorBar dataKey="err" width={4} stroke="#e3e7ee" strokeWidth={1} direction="x" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BreakdownBar({ breakdown }: { breakdown: Breakdown[] }) {
  const present = breakdown.filter((b) => b.contribution !== null && b.effective_weight > 0);
  const total = present.reduce((a, b) => a + (b.contribution ?? 0), 0);
  return (
    <div>
      <div className="flex h-4 w-full overflow-hidden rounded bg-white/5" role="img" aria-label={`Score composition: ${present.map((b) => `${b.label} ${b.contribution} points`).join(", ")}`}>
        {present.map((b, i) => (
          <div key={b.criterion_id} title={`${b.label}: ${b.contribution} pts`} style={{ width: `${(b.contribution ?? 0)}%`, background: SERIES[i % SERIES.length], opacity: 0.85 }} />
        ))}
      </div>
      <p className="mt-1 text-[11px] text-lunar-400">Bar length = points contributed (sum {total.toFixed(1)} / 100).</p>
    </div>
  );
}

export function DistributionChart({ data, height = 230 }: { data: Record<string, number | string>[]; height?: number }) {
  return (
    <div style={{ width: "100%", height }} role="img" aria-label="Histogram of criterion values by value type">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: -10, right: 8 }}>
          <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="bin" {...axis} />
          <YAxis allowDecimals={false} {...axis} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="provisional" stackId="a" fill="#fbbf24" isAnimationActive={false} />
          <Bar dataKey="synthetic" stackId="a" fill="#f472b6" isAnimationActive={false} />
          <Bar dataKey="measured" stackId="a" fill="#4ade80" isAnimationActive={false} />
          <Bar dataKey="modeled" stackId="a" fill="#67d4ee" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SensitivityChart({ data, sites, names, height = 300 }: { data: Record<string, number | null>[]; sites: string[]; names: Record<string, string>; height?: number }) {
  return (
    <div style={{ width: "100%", height }} role="img" aria-label="Line chart of site scores as the selected criterion weight multiplier varies from 0 to 2">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: -10, right: 16 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="multiplier" {...axis} label={{ value: "weight multiplier", position: "insideBottom", offset: -2, fill: "#8b94a5", fontSize: 11 }} />
          <YAxis domain={[0, 100]} {...axis} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {sites.map((s, i) => (
            <Line key={s} dataKey={s} name={names[s] ?? s} stroke={SERIES[i % SERIES.length]} strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} connectNulls={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ClusterScatter({ points, xLabel, yLabel, height = 320 }: { points: { x: number; y: number; cluster: number; name: string }[]; xLabel: string; yLabel: string; height?: number }) {
  const clusters = Array.from(new Set(points.map((p) => p.cluster))).sort();
  return (
    <div style={{ width: "100%", height }} role="img" aria-label={`Scatter plot of sites by ${xLabel} and ${yLabel}, coloured by cluster`}>
      <ResponsiveContainer>
        <ScatterChart margin={{ left: -10, right: 16, top: 8 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" />
          <XAxis type="number" dataKey="x" domain={[-0.3, 5.3]} ticks={[0, 1, 2, 3, 4, 5]} name={xLabel} {...axis} label={{ value: xLabel, position: "insideBottom", offset: -2, fill: "#8b94a5", fontSize: 11 }} />
          <YAxis type="number" dataKey="y" domain={[-0.3, 5.3]} ticks={[0, 1, 2, 3, 4, 5]} name={yLabel} {...axis} />
          <ZAxis range={[90, 90]} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number, n: string) => [v, n]} labelFormatter={() => ""}
            content={({ payload }) => payload && payload[0] ? <div style={tooltipStyle} className="px-2 py-1">{(payload[0].payload as { name: string }).name}</div> : null} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {clusters.map((c, i) => (
            <Scatter key={c} name={`Cluster ${c + 1}`} data={points.filter((p) => p.cluster === c)} fill={SERIES[i % SERIES.length]} isAnimationActive={false} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
