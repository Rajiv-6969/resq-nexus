import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router";
import AnimatedNumber from "../components/AnimatedNumber";
import ParticleField from "../components/ParticleField";
import { ArrowRightIcon, PlayIcon } from "../components/icons";
import { DISASTER_ICONS, PIPELINE_ICONS } from "../components/iconMaps";
import { DISASTER_META, PIPELINE_STEPS, formatNumber } from "../constants";
import { useAppData } from "../state/contexts";

const STAGE_COPY = {
  assess:
    "Load a disaster scenario: damage severity, population, vulnerability and road access for every zone on the map.",
  prioritise:
    "Score each zone with transparent, adjustable weights, plus an equity boost so remote areas are not left behind.",
  allocate:
    "The Allocation Engine assigns rescue teams, medical kits, food, shelters and vehicles to every zone, with relief depots, routes and travel times.",
  explain:
    "Every zone gets a plain-language reason for its share, written by Google Gemini, with a built-in template fallback.",
};

const container = { hidden: {}, show: { transition: { staggerChildren: 0.09, delayChildren: 0.12 } } };
const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.2, 0.7, 0.2, 1] } },
};

export default function Landing() {
  const { scenarios, scenarioId, selectScenario, listState } = useAppData();
  const navigate = useNavigate();
  const ready = listState.status === "ready";
  const zones = scenarios.reduce((sum, s) => sum + s.zone_count, 0);
  const people = scenarios.reduce((sum, s) => sum + s.total_population, 0);
  const states = new Set(scenarios.map((s) => s.state)).size;
  const launchTo = `/command${scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : ""}`;

  const openScenario = (id) => {
    selectScenario(id);
    navigate(`/command?scenario=${encodeURIComponent(id)}`);
  };

  return (
    <div className="landing">
      <section className="hero" aria-labelledby="hero-title">
        <ParticleField className="hero-particles" />
        <div className="hero-rings" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <motion.div className="hero-inner" variants={container} initial="hidden" animate="show">
          <motion.p className="eyebrow" variants={item}>
            <span className="eyebrow-dot" aria-hidden="true" /> Disaster response decision support
          </motion.p>
          <motion.h1 id="hero-title" className="hero-logo" variants={item}>
            ResQ Nexus
          </motion.h1>
          <motion.p className="hero-tagline" variants={item}>
            Intelligent Disaster Response and Resource Allocation System
          </motion.p>
          <motion.ol className="hero-pipeline" variants={item} aria-label="Pipeline stages">
            {PIPELINE_STEPS.map((step, i) => (
              <li key={step.key}>
                <span>{step.name}</span>
                {i < PIPELINE_STEPS.length - 1 && <ArrowRightIcon size={14} />}
              </li>
            ))}
          </motion.ol>
          <motion.div className="hero-cta" variants={item}>
            <Link to={launchTo} className="btn btn-primary btn-xl">
              <PlayIcon size={16} /> Launch Command Centre
            </Link>
            <Link to="/about" className="btn btn-ghost btn-xl">
              How it works
            </Link>
          </motion.div>
          <motion.dl className="hero-stats" variants={item}>
            <div>
              <dt>Scenarios</dt>
              <dd>
                <AnimatedNumber value={ready ? scenarios.length : null} />
              </dd>
            </div>
            <div>
              <dt>Zones mapped</dt>
              <dd>
                <AnimatedNumber value={ready ? zones : null} />
              </dd>
            </div>
            <div>
              <dt>People in scope</dt>
              <dd>
                <AnimatedNumber value={ready ? people : null} />
              </dd>
            </div>
            <div>
              <dt>Indian states</dt>
              <dd>
                <AnimatedNumber value={ready ? states : null} />
              </dd>
            </div>
          </motion.dl>
          {listState.status === "error" && (
            <motion.p className="hero-offline" variants={item} role="status">
              The backend is offline, so live scenario figures are unavailable. Start the API and refresh.
            </motion.p>
          )}
        </motion.div>
        <div className="hero-fade" aria-hidden="true" />
      </section>

      <section className="stages" aria-labelledby="stages-title">
        <header className="section-head">
          <p className="kicker">The pipeline</p>
          <h2 id="stages-title" className="display-title">
            From damage to decisions
          </h2>
        </header>
        <motion.ol
          className="stage-grid"
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
        >
          {PIPELINE_STEPS.map((step, i) => {
            const Icon = PIPELINE_ICONS[step.key];
            return (
              <motion.li key={step.key} className={`stage-card stage-card--${step.key}`} variants={item}>
                <div className="stage-card-top">
                  <span className="stage-index">0{i + 1}</span>
                  <span className="stage-icon">
                    <Icon size={22} />
                  </span>
                </div>
                <h3>{step.name}</h3>
                <p>{STAGE_COPY[step.key]}</p>
                <span className="stage-signal" aria-hidden="true" />
              </motion.li>
            );
          })}
        </motion.ol>
      </section>

      <section className="teasers" aria-labelledby="teasers-title">
        <header className="section-head">
          <p className="kicker">Demo scenarios</p>
          <h2 id="teasers-title" className="display-title">
            Three disasters across India
          </h2>
        </header>
        <motion.div
          className="teaser-grid"
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
        >
          {scenarios.map((s) => {
            const Icon = DISASTER_ICONS[s.disaster_type];
            const meta = DISASTER_META[s.disaster_type];
            return (
              <motion.button
                type="button"
                key={s.id}
                className={`teaser teaser--${s.disaster_type}`}
                style={{ "--accent": meta?.color }}
                variants={item}
                whileHover={{ y: -6 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => openScenario(s.id)}
              >
                <span className="teaser-icon">{Icon && <Icon size={30} />}</span>
                <span className="teaser-type">{meta?.label ?? s.disaster_type}</span>
                <strong className="teaser-name">{s.name}</strong>
                <span className="teaser-region">
                  {s.region}, {s.state}
                </span>
                <span className="teaser-stats">
                  <span>{s.zone_count} zones</span>
                  <span>{formatNumber(s.total_population)} people</span>
                </span>
                <span className="teaser-open">
                  Open in Command Centre <ArrowRightIcon size={14} />
                </span>
              </motion.button>
            );
          })}
          {!scenarios.length &&
            [0, 1, 2].map((i) => <div key={i} className="teaser teaser--skeleton" aria-hidden="true" />)}
        </motion.div>
        <p className="landing-note">
          Synthetic demo data: zones are real OpenStreetMap places; damage, needs and stock are generated.
        </p>
      </section>
    </div>
  );
}
