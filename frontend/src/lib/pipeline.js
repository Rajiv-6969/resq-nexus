import { PIPELINE_STEPS } from "../constants";

// State of each pipeline step (pending | active | done | stale | error) for the stepper.
export function stepperStates(pipeline, { ready, run, stale }) {
  const steps = PIPELINE_STEPS.map((_, i) => i);
  if (pipeline.status === "running") return steps.map((i) => (i < pipeline.step ? "done" : i === pipeline.step ? "active" : "pending"));
  if (pipeline.status === "error") return steps.map((i) => (i < pipeline.step ? "done" : i === pipeline.step ? "error" : "pending"));
  const base = ready ? "done" : "pending";
  if (!run) return [base, base, "pending", "pending"];
  const planned = stale ? "stale" : "done";
  const explained = run.explanations ? planned : run.explainError ? "error" : "pending";
  return [base, base, planned, explained];
}
