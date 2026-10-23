import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import AnimatedNumber from "./AnimatedNumber";
import { RESOURCES, clusterColor, formatNumber } from "../constants";

export const ENGINE_COLOR = "#2EC4B6";
export const GREEDY_COLOR = "#8E97C7";
const GRID = "rgba(148, 163, 209, 0.12)";
const TICK = { fill: "#9AA4C4", fontSize: 12, fontFamily: "Inter, sans-serif" };

function GlassTooltip({ active, payload, label, formatter, labelFormatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      {label != null && <p className="chart-tooltip-label">{labelFormatter ? labelFormatter(label, payload) : label}</p>}
      <ul>
        {payload.map((p) => (
          <li key={p.dataKey ?? p.name}>
            <span className="chart-swatch" style={{ background: p.color ?? p.fill }} />
            <span>{p.name}</span>
            <strong>{formatter ? formatter(p.value, p) : p.value}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

// One metric, engine vs greedy: values, a better/worse badge and a two-bar chart.
export function MetricCard({ title, icon: Icon, help, engine, greedy, format, lowerIsBetter, unit, deltaUnit = unit, index = 0 }) {
  const equal = Math.abs(engine - greedy) < 1e-9;
  const engineBetter = lowerIsBetter ? engine < greedy : engine > greedy;
  const delta = Math.abs(engine - greedy);
  const data = [
    { name: "Engine", value: engine, fill: ENGINE_COLOR },
    { name: "Greedy", value: greedy, fill: GREEDY_COLOR },
  ];
  return (
    <motion.article
      className="metric-card glass"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.06 }}
      whileHover={{ y: -4 }}
    >
      <header>
        <span className="metric-icon">
          <Icon size={17} />
        </span>
        <h3>{title}</h3>
        <span className={`delta ${equal ? "delta--equal" : engineBetter ? "delta--better" : "delta--worse"}`}>
          {equal ? "Equal" : `${engineBetter ? "Engine" : "Greedy"} ${lowerIsBetter ? "−" : "+"}${format(delta)}${deltaUnit ?? ""}`}
        </span>
      </header>
      <div className="metric-values">
        <div>
          <span className="metric-label">Engine</span>
          <span className="metric-engine">
            <AnimatedNumber value={engine} format={format} />
            {unit && <small>{unit}</small>}
          </span>
        </div>
        <div>
          <span className="metric-label">Greedy</span>
          <span className="metric-greedy">
            <AnimatedNumber value={greedy} format={format} />
            {unit && <small>{unit}</small>}
          </span>
        </div>
      </div>
      <BarChart responsive style={{ width: "100%", height: 92 }} data={data} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <XAxis type="number" hide domain={[0, (max) => (max > 0 ? max * 1.08 : 1)]} />
        <YAxis type="category" dataKey="name" tick={TICK} width={60} axisLine={false} tickLine={false} />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<GlassTooltip formatter={(v) => `${format(v)}${unit ?? ""}`} />} />
        <Bar dataKey="value" name={title} radius={[0, 6, 6, 0]} barSize={16} animationDuration={900}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.fill} />
          ))}
        </Bar>
      </BarChart>
      <p className="metric-help">{help}</p>
    </motion.article>
  );
}

// GA fitness per generation (best and population mean), one segment per pass.
export function FitnessChart({ history, passes, selectedPass }) {
  const data = useMemo(() => history.map((h, i) => ({ step: i + 1, ...h })), [history]);
  const boundaries = useMemo(() => {
    const out = [];
    let start = 1;
    passes.forEach((p) => {
      out.push({ pass: p.pass, start, end: start + p.generations - 1 });
      start += p.generations;
    });
    return out;
  }, [passes]);
  return (
    <LineChart responsive style={{ width: "100%", height: 300 }} data={data} margin={{ top: 16, right: 18, bottom: 8, left: 0 }}>
      <CartesianGrid stroke={GRID} vertical={false} />
      <XAxis dataKey="step" tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd" minTickGap={36}
        label={{ value: "Generation", position: "insideBottomRight", offset: -4, fill: "#6B7699", fontSize: 12 }} />
      <YAxis tick={TICK} tickLine={false} axisLine={false} width={52} domain={["auto", "auto"]} tickFormatter={(v) => v.toFixed(2)} />
      <Tooltip
        content={
          <GlassTooltip
            formatter={(v) => v.toFixed(4)}
            labelFormatter={(label, payload) => `Pass ${payload[0]?.payload.pass} · generation ${payload[0]?.payload.generation}`}
          />
        }
      />
      <Legend wrapperStyle={{ color: "#C9D1EA", fontSize: 12 }} />
      {boundaries.slice(1).map((b) => (
        <ReferenceLine key={b.pass} x={b.start} stroke="rgba(255, 209, 102, 0.45)" strokeDasharray="4 4" label={{ value: `Pass ${b.pass}`, fill: "#FFD166", fontSize: 11, position: "insideTopLeft" }} />
      ))}
      <Line type="monotone" dataKey="best" name="Best fitness" stroke="#FFD166" strokeWidth={2.4} dot={false} animationDuration={1400} />
      <Line type="monotone" dataKey="mean" name="Population mean" stroke="#B388FF" strokeWidth={1.6} dot={false} strokeDasharray="5 4" animationDuration={1600} />
      {selectedPass && boundaries.length > 1 && (
        <ReferenceArea
          x1={boundaries.find((b) => b.pass === selectedPass)?.start}
          x2={boundaries.find((b) => b.pass === selectedPass)?.end}
          fill={ENGINE_COLOR}
          fillOpacity={0.07}
          stroke="none"
          label={{ value: "Selected plan", fill: ENGINE_COLOR, fontSize: 11, position: "insideBottom" }}
        />
      )}
    </LineChart>
  );
}

// Each zone's share of every stock, scaled by 1/5 so a bar shows its share of all relief.
const zoneShareRows = (zones, method, stock) =>
  zones.map((z) => {
    const row = { name: z.name, units: {}, share: {} };
    RESOURCES.forEach((r) => {
      const units = z[method].allocated[r.key];
      const share = stock[r.key] ? (units / stock[r.key]) * 100 : 0;
      row.units[r.key] = units;
      row.share[r.key] = share;
      row[r.key] = share / RESOURCES.length;
    });
    return row;
  });

function ZoneShareTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const { units, share } = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      <ul>
        {payload.map((p) => (
          <li key={p.dataKey}>
            <span className="chart-swatch" style={{ background: p.color }} />
            <span>{p.name}</span>
            <strong>
              {formatNumber(units[p.dataKey])} ({share[p.dataKey].toFixed(1)}% of stock)
            </strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Resource mix sent to each zone in need (stacked), engine or greedy.
export function ZoneDistributionChart({ result }) {
  const [method, setMethod] = useState("engine");
  const zones = result.zones.filter((z) => z.damage_severity > 0);
  const data = zoneShareRows(zones, method, result.resources);
  return (
    <>
      <div className="segmented" role="radiogroup" aria-label="Plan shown">
        {["engine", "greedy"].map((m) => (
          <button key={m} type="button" role="radio" aria-checked={method === m} className={method === m ? "is-active" : ""} onClick={() => setMethod(m)}>
            {m === "engine" ? "Allocation Engine" : "Greedy baseline"}
          </button>
        ))}
      </div>
      <BarChart responsive style={{ width: "100%", height: 320 }} data={data} margin={{ top: 10, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="name" tick={{ ...TICK, fontSize: 11 }} interval={0} angle={-38} textAnchor="end" height={64} tickLine={false} axisLine={{ stroke: GRID }} />
        <YAxis tick={TICK} tickLine={false} axisLine={false} width={44} tickFormatter={(v) => `${v.toFixed(0)}%`} />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<ZoneShareTooltip />} />
        <Legend verticalAlign="top" wrapperStyle={{ color: "#C9D1EA", fontSize: 12, paddingBottom: 8 }} />
        {RESOURCES.map((r, i) => (
          <Bar key={r.key} dataKey={r.key} name={r.label} stackId="share" fill={r.color} radius={i === RESOURCES.length - 1 ? [5, 5, 0, 0] : 0} animationDuration={900} />
        ))}
      </BarChart>
    </>
  );
}

const RESERVE_COLOR = "rgba(148, 163, 209, 0.22)";

function DepotShareTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const { units } = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      <ul>
        {payload.map((p) => (
          <li key={p.dataKey}>
            <span className="chart-swatch" style={{ background: p.color }} />
            <span>{p.name}</span>
            <strong>
              {formatNumber(units[p.dataKey])} ({p.value.toFixed(0)}%)
            </strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

// How each resource's stock is split between relief depots (engine plan).
export function DepotDistributionChart({ result }) {
  const byId = Object.fromEntries(result.zones.map((z) => [z.id, z]));
  const data = RESOURCES.map((r) => {
    const stock = result.resources[r.key] || 0;
    const row = { name: r.label, units: {} };
    let sent = 0;
    result.depots.forEach((d) => {
      const units = d.zone_ids.reduce((s, id) => s + byId[id].engine.allocated[r.key], 0);
      sent += units;
      row.units[d.id] = units;
      row[d.id] = stock ? (units / stock) * 100 : 0;
    });
    row.units.reserve = Math.max(stock - sent, 0);
    row.reserve = stock ? (row.units.reserve / stock) * 100 : 0;
    return row;
  });
  return (
    <BarChart responsive style={{ width: "100%", height: 300 }} data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
      <CartesianGrid stroke={GRID} horizontal={false} />
      <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} tickFormatter={(v) => `${v}%`} />
      <YAxis type="category" dataKey="name" tick={{ ...TICK, fill: "#C9D1EA" }} width={104} tickLine={false} axisLine={false} />
      <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<DepotShareTooltip />} />
      <Legend wrapperStyle={{ color: "#C9D1EA", fontSize: 12 }} />
      {result.depots.map((d, i) => (
        <Bar key={d.id} dataKey={d.id} name={d.name} stackId="stock" fill={clusterColor(i)} barSize={22} animationDuration={900} />
      ))}
      <Bar dataKey="reserve" name="Not sent" stackId="stock" fill={RESERVE_COLOR} radius={[0, 5, 5, 0]} barSize={22} animationDuration={900} />
    </BarChart>
  );
}

// Lorenz curve of zone coverage: the closer to the diagonal, the fairer the plan.
export function FairnessChart({ result }) {
  const data = useMemo(() => {
    const needy = result.zones.filter((z) => z.engine.coverage_pct != null);
    const curve = (method) => {
      const values = needy.map((z) => z[method].coverage_pct).sort((a, b) => a - b);
      const total = values.reduce((s, v) => s + v, 0) || 1;
      let running = 0;
      return [0, ...values.map((v) => (running += v) / total)];
    };
    const engine = curve("engine");
    const greedy = curve("greedy");
    return engine.map((e, i) => ({
      zones: Math.round((i / (engine.length - 1)) * 100),
      equality: Math.round((i / (engine.length - 1)) * 100),
      engine: +(e * 100).toFixed(1),
      greedy: +(greedy[i] * 100).toFixed(1),
    }));
  }, [result]);
  return (
    <LineChart responsive style={{ width: "100%", height: 300 }} data={data} margin={{ top: 10, right: 18, bottom: 18, left: 0 }}>
      <CartesianGrid stroke={GRID} />
      <XAxis dataKey="zones" type="number" domain={[0, 100]} tick={TICK} tickLine={false} axisLine={{ stroke: GRID }} tickFormatter={(v) => `${v}%`}
        label={{ value: "Share of zones in need (least covered first)", position: "insideBottom", offset: -10, fill: "#6B7699", fontSize: 12 }} />
      <YAxis type="number" domain={[0, 100]} tick={TICK} tickLine={false} axisLine={false} width={44} tickFormatter={(v) => `${v}%`} />
      <Tooltip content={<GlassTooltip formatter={(v) => `${v}%`} labelFormatter={(l) => `${l}% of zones`} />} />
      <Legend verticalAlign="top" wrapperStyle={{ color: "#C9D1EA", fontSize: 12, paddingBottom: 6 }} />
      <Line type="linear" dataKey="equality" name="Perfect equality" stroke="rgba(255,255,255,0.35)" strokeDasharray="4 4" dot={false} animationDuration={600} />
      <Line type="monotone" dataKey="greedy" name={`Greedy (Gini ${result.greedy.metrics.gini?.toFixed(2)})`} stroke={GREEDY_COLOR} strokeWidth={2} dot={{ r: 2.5 }} animationDuration={1200} />
      <Line type="monotone" dataKey="engine" name={`Engine (Gini ${result.engine.metrics.gini?.toFixed(2)})`} stroke={ENGINE_COLOR} strokeWidth={2.6} dot={{ r: 2.5 }} animationDuration={1400} />
    </LineChart>
  );
}

// Coverage of each zone in need, engine vs greedy (zones in priority order).
export function ZoneCoverageChart({ result }) {
  const data = result.zones
    .filter((z) => z.engine.coverage_pct != null)
    .map((z) => ({ name: z.name, engine: z.engine.coverage_pct, greedy: z.greedy.coverage_pct, level: z.priority_level }));
  return (
    <BarChart responsive style={{ width: "100%", height: 300 }} data={data} margin={{ top: 10, right: 12, bottom: 64, left: 0 }}>
      <CartesianGrid stroke={GRID} vertical={false} />
      <XAxis dataKey="name" tick={{ ...TICK, fontSize: 11 }} interval={0} angle={-38} textAnchor="end" height={70} tickLine={false} axisLine={{ stroke: GRID }} />
      <YAxis tick={TICK} domain={[0, 100]} tickLine={false} axisLine={false} width={44} tickFormatter={(v) => `${v}%`} />
      <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={<GlassTooltip formatter={(v) => `${v.toFixed(0)}%`} labelFormatter={(l, p) => `${l} · ${p[0]?.payload.level}`} />} />
      <Legend verticalAlign="top" wrapperStyle={{ color: "#C9D1EA", fontSize: 12, paddingBottom: 8 }} />
      <Bar dataKey="engine" name="Allocation Engine" fill={ENGINE_COLOR} radius={[4, 4, 0, 0]} animationDuration={900} />
      <Bar dataKey="greedy" name="Greedy baseline" fill={GREEDY_COLOR} radius={[4, 4, 0, 0]} animationDuration={1100} />
    </BarChart>
  );
}
