import { motion } from "framer-motion";
import { PIPELINE_STEPS } from "../constants";
import { AlertIcon, CheckIcon } from "./icons";
import { PIPELINE_ICONS } from "./iconMaps";

const STATE_TEXT = { done: "Complete", active: "Running…", stale: "Out of date", error: "Failed" };

// Assess -> Prioritise -> Allocate -> Explain; lights up step by step while the pipeline runs.
export default function PipelineStepper({ states }) {
  return (
    <ol className="stepper" aria-label="Pipeline progress">
      {PIPELINE_STEPS.map((step, i) => {
        const Icon = PIPELINE_ICONS[step.key];
        const state = states[i];
        return (
          <li key={step.key} className={`step step--${state}`} aria-current={state === "active" ? "step" : undefined}>
            <span className="step-node">
              {state === "done" ? <CheckIcon size={16} /> : state === "error" ? <AlertIcon size={16} /> : <Icon size={16} />}
              {state === "active" && <span className="step-spin" aria-hidden="true" />}
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
                  transition={{ duration: 0.45, ease: [0.2, 0.7, 0.2, 1] }}
                />
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
