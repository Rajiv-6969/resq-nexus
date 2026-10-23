import { WEIGHT_FIELDS, isDefaultWeights } from "../constants";

// Priority weight sliders (w1..w4): scores and ranking update live as they move.
export default function WeightControls({ weights, onChange, onReset, settled, hasRun }) {
  const total = WEIGHT_FIELDS.reduce((sum, f) => sum + weights[f.key], 0);

  const change = (key, value) => {
    const others = total - weights[key];
    onChange(key, others === 0 && value === 0 ? 1 : value); // never let every weight reach zero
  };

  return (
    <section className="weights" aria-labelledby="weights-title">
      <header className="panel-head">
        <h3 id="weights-title" className="subhead">
          Priority weights
        </h3>
        <button type="button" className="btn btn--sm" onClick={onReset} disabled={isDefaultWeights(weights)}>
          Reset
        </button>
      </header>
      {WEIGHT_FIELDS.map((f) => {
        const share = total > 0 ? Math.round((weights[f.key] / total) * 100) : 0;
        return (
          <div className="weight-row" key={f.key}>
            <label htmlFor={`weight-${f.key}`}>
              <span className="weight-symbol">{f.symbol}</span>
              {f.label}
            </label>
            <output htmlFor={`weight-${f.key}`} className="weight-value">
              {share}%
            </output>
            <span className="range" style={{ "--fill": `${weights[f.key]}%` }}>
              <span className="range-fill" aria-hidden="true" />
              <input
                id={`weight-${f.key}`}
                type="range"
                min="0"
                max="100"
                step="1"
                value={weights[f.key]}
                onChange={(e) => change(f.key, Number(e.target.value))}
                aria-describedby="weights-help"
                aria-valuetext={`${share}% of the score`}
              />
            </span>
          </div>
        );
      })}
      <p id="weights-help" className="footnote">
        Weights are relative and rescaled to 100%. Scores update live{settled ? "" : " (updating…)"}
        {hasRun ? "; run the allocation again to update the plan." : "."}
      </p>
    </section>
  );
}
