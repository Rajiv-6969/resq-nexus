import { InfoIcon, SparkIcon } from "./icons";

// Placeholder for the next stages (Allocate -> Explain). The button is wired to
// a notice only; the allocation engine and Gemini explanations come next.
export default function AllocationPanel({ requested, onAllocate }) {
  return (
    <>
      <div className="allocate-wrap">
        <button type="button" className="btn-primary" onClick={onAllocate}>
          <SparkIcon size={18} />
          Allocate Resources
        </button>
        <p className="allocate-hint">Next stage: distributes the resources above across zones by priority.</p>
      </div>

      <section className="card" aria-labelledby="allocation-title">
        <h2 className="card-title" id="allocation-title">
          Allocation &amp; Explanation <span className="stage-pill">Next stage</span>
        </h2>
        <div className="empty-state" aria-live="polite">
          {requested ? (
            <>
              <InfoIcon size={20} />
              <p>
                <strong>The allocation engine is not connected yet.</strong> In the next stage this section will
                show how many rescue teams, medical kits, food packets, shelters and vehicles go to each zone,
                with a plain-language explanation of every decision (generated with Google Gemini).
              </p>
            </>
          ) : (
            <p>No allocation yet. Recommended allocations and their explanations will appear here.</p>
          )}
        </div>
      </section>
    </>
  );
}
