import AnimatedNumber from "./AnimatedNumber";

// A row of big mono counters that tick up to their values.
export default function Counters({ items, label = "Summary" }) {
  return (
    <dl className="counters" aria-label={label}>
      {items.map((item) => (
        <div key={item.label} className={`counter${item.tone ? ` counter--${item.tone}` : ""}`}>
          <dt className="label">{item.label}</dt>
          <dd>
            <AnimatedNumber value={item.value} className="counter-num" />
            {item.unit && <span className="counter-unit mono">{item.unit}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
