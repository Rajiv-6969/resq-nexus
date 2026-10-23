import { motion } from "framer-motion";
import { PIPELINE_STEPS } from "../constants";
import { AlertIcon, AsteriskMark, CheckIcon } from "./icons";

const STATE_TEXT = { done: "Complete", active: "Running", stale: "Out of date", error: "Failed" };
const HARD = [0.7, 0, 0.2, 1];

// Assess -> Prioritise -> Allocate -> Explain; each step switches state as the pipeline runs.
export default function PipelineStepper({ states }) {
  return (
    <ol className="stepper" aria-label="Pipeline progress">
      {PIPELINE_STEPS.map((step, i) => {
        const state = states[i];
        return (
          <li key={step.key} className={`step step--${state}`} aria-current={state === "active" ? "step" : undefined}>
            <span className="step-node" aria-hidden="true">
              {state === "done" ? (
                <CheckIcon size={14} />
              ) : state === "error" ? (
                <AlertIcon size={14} />
              ) : state === "active" ? (
                <AsteriskMark size={13} className="asterisk loader" />
              ) : (
                String(i + 1).padStart(2, "0")
              )}
            </span>
            <span className="step-text">
              <strong>{step.name}</strong>
              <small>{STATE_TEXT[state] ?? step.detail}</small>
            </span>
            {i < PIPELINE_STEPS.length - 1 && (
              <span className="step-link" aria-hidden="true">
                <motion.span
                  className="step-link-fill"
                  initial={false}
                  animate={{ scaleX: state === "done" || state === "stale" ? 1 : 0 }}
                  transition={{ duration: 0.3, ease: HARD }}
                />
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
