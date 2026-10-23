import AnimatedNumber from "./AnimatedNumber";

const CELLS = 20;

// Coverage (0-100 %) as a mono figure over a bar of 20 cells that switch on one by one.
export default function CoverageMeter({ value, label = "covered", muted = false }) {
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const filled = Math.round((pct / 100) * CELLS);
  return (
    <div className={`meter${muted ? " meter--muted" : ""}`}>
      <p className="meter-figure">
        <AnimatedNumber value={value} format={(v) => `${Math.round(v)}%`} duration={0.6} />
        <span className="label">{label}</span>
      </p>
      <ol className="meter-cells" aria-hidden="true">
        {Array.from({ length: CELLS }, (_, i) => (
          <li key={i} className={i < filled ? "on" : undefined} style={{ "--i": i }} />
        ))}
      </ol>
    </div>
  );
}
