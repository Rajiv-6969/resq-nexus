import { motion } from "framer-motion";
import { Link } from "react-router";
import { ArrowRightIcon, CodeIcon, CpuIcon, InfoIcon, MapIcon, RouteIcon, SparkIcon } from "../components/icons";
import { PIPELINE_ICONS } from "../components/iconMaps";
import { SHOW_ANALYTICS } from "../config";
import { PIPELINE_STEPS } from "../constants";

const STEP_COPY = {
  assess: "Each scenario lists zones with damage severity (0–3), population, a vulnerability index and road accessibility, plus the stock available for the whole response.",
  prioritise: "Every factor is normalised to 0–1 and weighted with adjustable weights into a priority score, with a small equity boost for damaged zones that are hard to reach.",
  allocate: `The Allocation Engine turns the scores into a plan: units of each resource per zone, a relief depot, a route and a travel time${SHOW_ANALYTICS ? ", compared against a greedy baseline" : ""}.`,
  explain: "Google Gemini writes a short, plain-language reason for each zone's share. Without a key the app uses template explanations, so the demo always works.",
};

const ALGORITHMS = [
  {
    name: "K-Means clustering",
    library: "scikit-learn",
    icon: MapIcon,
    text: "Partitions points into k clusters by repeatedly moving each centroid to the (optionally weighted) mean of its members.",
  },
  {
    name: "Dijkstra's shortest path",
    library: "NetworkX",
    icon: RouteIcon,
    text: "Finds the lowest-cost path from a source node to every other node of a graph with non-negative edge weights.",
  },
  {
    name: "Genetic Algorithm",
    library: "DEAP",
    icon: CpuIcon,
    text: "Evolves a population of candidate solutions through selection, crossover and mutation, guided by a fitness function.",
  },
];

const STACK = [
  { group: "Frontend", items: ["React 19", "Vite", "React Router", "React-Leaflet + OpenStreetMap", "Framer Motion", "Recharts"] },
  { group: "Backend", items: ["Python 3.13", "FastAPI", "Pydantic", "NumPy", "scikit-learn", "NetworkX", "DEAP"] },
  { group: "AI", items: ["Google Gemini API (google-genai)", "Template fallback"] },
  { group: "Quality", items: ["pytest", "oxlint", "GitHub Actions CI"] },
];

const rise = { initial: { opacity: 0, y: 18 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, amount: 0.2 } };

export default function About() {
  return (
    <div className="about">
      <header className="page-head page-head--center">
        <p className="kicker">About the project</p>
        <h1 className="page-title">ResQ Nexus</h1>
        <p className="page-lead">
          An intelligent disaster response and resource allocation system: a web-based decision-support tool that helps a
          response team decide where scarce relief should go, and explains why.
        </p>
      </header>

      <motion.section className="about-section" {...rise}>
        <h2 className="display-title">The pipeline</h2>
        <ol className="about-pipeline">
          {PIPELINE_STEPS.map((step, i) => {
            const Icon = PIPELINE_ICONS[step.key];
            return (
              <li key={step.key} className={`about-step about-step--${step.key}`}>
                <span className="about-step-num">0{i + 1}</span>
                <span className="about-step-icon">
                  <Icon size={20} />
                </span>
                <div>
                  <h3>{step.name}</h3>
                  <p>{STEP_COPY[step.key]}</p>
                </div>
              </li>
            );
          })}
        </ol>
      </motion.section>

      <motion.section className="about-section" {...rise} aria-labelledby="algorithms-title">
        <h2 id="algorithms-title" className="display-title">
          Algorithms Used
        </h2>
        <ul className="algo-grid">
          {ALGORITHMS.map(({ name, library, icon: Icon, text }) => (
            <li key={name} className="algo-card glass">
              <span className="algo-icon">
                <Icon size={22} />
              </span>
              <h3>{name}</h3>
              <span className="algo-lib">{library}</span>
              <p>{text}</p>
            </li>
          ))}
        </ul>
      </motion.section>

      <motion.section className="about-section about-split" {...rise}>
        <div className="glass about-card">
          <h2 className="panel-title">Priority score</h2>
          <p className="formula">
            priority = w1·severity + w2·population + w3·vulnerability + w4·(1 − accessibility) + equity
          </p>
          <p>
            Default weights 0.40 / 0.25 / 0.20 / 0.15, adjustable live from the Command Centre. Levels: Critical ≥ 0.70, High ≥
            0.50, Medium ≥ 0.30, otherwise Low.
          </p>
        </div>
        <div className="glass about-card">
          <h2 className="panel-title">
            <InfoIcon size={16} /> Data
          </h2>
          <p>
            The three demo scenarios (Barpeta flood, Kachchh earthquake, Kumaon wildfire) are synthetic: zone names and coordinates
            are real OpenStreetMap places, populations are rounded approximations, and damage, vulnerability, access and stock are
            generated by <code>backend/generate_scenario.py</code>.
          </p>
        </div>
      </motion.section>

      <motion.section className="about-section" {...rise} aria-labelledby="stack-title">
        <h2 id="stack-title" className="display-title">
          Tech stack
        </h2>
        <div className="stack-grid">
          {STACK.map(({ group, items }) => (
            <div key={group} className="stack-group glass">
              <h3>
                {group === "AI" ? <SparkIcon size={15} /> : <CodeIcon size={15} />} {group}
              </h3>
              <ul>
                {items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </motion.section>

      <div className="about-cta">
        <Link to="/command" className="btn btn-primary btn-lg">
          Open the Command Centre <ArrowRightIcon size={15} />
        </Link>
      </div>
    </div>
  );
}
