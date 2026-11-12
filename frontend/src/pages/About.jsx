import { Link } from "react-router";
import Figure from "../components/Figure";
import { Reveal, Wipe } from "../components/Reveal";
import { SHOW_ANALYTICS } from "../config";
import { PIPELINE_STEPS } from "../constants";
import { PHOTOS, PHOTO_LIST } from "../lib/photos";

const pad2 = (n) => String(n).padStart(2, "0");

// Base paper and datasets (see docs/PROJECT_CONTEXT.md). Nothing here is loaded yet: the
// Data notice below says what is simulated.
const SOURCES = [
  {
    name: "DisasterReliefGPT",
    role: "Base paper",
    cite: "Reghunath, L.C.; Abhishek, A.S.; Changat, A.; Unnikrishnan, A.; Rai, A.K.; Napoli, C.; Randieri, C. Technologies 2026, 14(3), 179",
    url: "https://doi.org/10.3390/technologies14030179",
    license: "doi:10.3390/technologies14030179",
  },
  {
    name: "xBD",
    role: "Building damage from satellite imagery",
    cite: "Gupta, R. et al. CVPR Workshops, 2019",
    url: "https://arxiv.org/abs/1911.09296",
    license: "CC BY-NC-SA 4.0",
  },
  {
    name: "Sen1Floods11",
    role: "Flood extent, Sentinel-1",
    cite: "Bonafilia, D.; Tellman, B.; Anderson, T.; Issenberg, E. CVPR Workshops, 2020",
    url: "https://github.com/cloudtostreet/Sen1Floods11",
    license: "Open access",
  },
  {
    name: "OpenStreetMap",
    role: "Map data, places and tiles",
    cite: "© OpenStreetMap contributors",
    url: "https://www.openstreetmap.org/copyright",
    license: "ODbL",
  },
  {
    name: "WorldPop",
    role: "Population data",
    cite: "www.worldpop.org",
    url: "https://www.worldpop.org/",
    license: "CC BY 4.0",
  },
];

const STEP_COPY = {
  assess: "Each scenario lists zones with damage severity (0–3), population, a vulnerability index and road accessibility, plus the stock available for the whole response.",
  prioritise: "Every factor is normalised to 0–1 and weighted with adjustable weights into a priority score, with a small equity boost for damaged zones that are hard to reach.",
  allocate: `The Allocation Engine turns the scores into a plan: units of each resource per zone, a relief depot, a route and a travel time${SHOW_ANALYTICS ? ", compared against a greedy baseline" : ""}.`,
  explain: "Google Gemini writes a short, plain-language reason for each zone's share. Without a key the app uses template explanations, so the demo always works.",
};

const ALGORITHMS = [
  {
    name: "K-Means Clustering",
    library: "scikit-learn",
    text: "Partitions points into k clusters by repeatedly moving each centroid to the (optionally weighted) mean of its members.",
  },
  {
    name: "Dijkstra's Shortest Path",
    library: "NetworkX",
    text: "Finds the lowest-cost path from a source node to every other node of a graph with non-negative edge weights.",
  },
  {
    name: "Genetic Algorithm",
    library: "DEAP",
    text: "Evolves a population of candidate solutions through selection, crossover and mutation, guided by a fitness function.",
  },
];

const STACK = [
  { group: "Frontend", items: ["React 19", "Vite", "React Router", "React-Leaflet + OpenStreetMap", "Framer Motion"] },
  { group: "Backend", items: ["Python 3.13", "FastAPI", "Pydantic", "NumPy", "scikit-learn", "NetworkX", "DEAP"] },
  { group: "Geography", items: ["OSMnx road graphs (NetworkX GraphML)", "SciPy Dijkstra", "H3 hexagons", "OpenStreetMap", "WorldPop"] },
  { group: "AI", items: ["Google Gemini API (google-genai)", "Template fallback"] },
  { group: "Quality", items: ["pytest", "oxlint", "GitHub Actions CI"] },
];

const TEAM = [
  { name: "Rajiv Siddharth", id: "2411021061420" },
  { name: "Akash", id: "2411021061441" },
  { name: "Abhi Rathod", id: "2411021061436" },
  { name: "Sameer Basha Mulla", id: "2411021061446" },
];

export default function About() {
  return (
    <div className="about">
      <section className="sec page-hero page-hero--paper" aria-labelledby="about-title">
        <p className="sec-bar mono">
          <span>(03) About</span>
          <span>Project notes</span>
        </p>
        <div className="page-hero-row">
          <Wipe as="h1" id="about-title" className="page-title">
            About
          </Wipe>
          <p className="page-sub">
            ResQ Nexus is an intelligent disaster response and resource allocation system: a web-based decision-support tool that
            helps a response team decide where scarce relief should go, and explains why.
          </p>
        </div>
      </section>

      <Figure photo={PHOTOS["about-concrete-pillars"]} index="01" className="page-figure" eager />

      <section className="sec sec--black about-block" aria-labelledby="pipeline-title">
        <p className="sec-bar mono">
          <span>01</span>
          <span>How it works</span>
        </p>
        <Wipe id="pipeline-title" className="about-h2">
          Four stages, one decision.
        </Wipe>
        <ol className="about-steps">
          {PIPELINE_STEPS.map((step, i) => (
            <Reveal as="li" key={step.key} className="about-step" delay={i * 0.05}>
              <span className="about-step-num">{pad2(i + 1)}</span>
              <h3>{step.name}</h3>
              <p>{STEP_COPY[step.key]}</p>
            </Reveal>
          ))}
        </ol>
      </section>

      <section className="sec sec--red about-block" aria-labelledby="algorithms-title">
        <p className="sec-bar mono">
          <span>02</span>
          <span>Algorithms</span>
        </p>
        <Wipe id="algorithms-title" className="about-h2">
          Algorithms Used
        </Wipe>
        <ul className="algo-grid">
          {ALGORITHMS.map(({ name, library, text }, i) => (
            <Reveal as="li" key={name} className="algo-card" delay={i * 0.05}>
              <span className="algo-num">{pad2(i + 1)}</span>
              <h3>{name}</h3>
              <span className="algo-lib">{library}</span>
              <p>{text}</p>
            </Reveal>
          ))}
        </ul>
      </section>

      <section className="sec about-split" aria-label="Priority score and data">
        <Reveal className="about-card">
          <p className="sec-no">03 / Priority score</p>
          <p className="formula">priority = w1·severity + w2·population + w3·vulnerability + w4·(1 − accessibility) + equity</p>
          <p>
            Default weights 0.40 / 0.25 / 0.20 / 0.15, adjustable live from the Command Centre. Levels: Critical ≥ 0.70, High ≥ 0.50,
            Medium ≥ 0.30, otherwise Low.
          </p>
        </Reveal>
        <Reveal className="about-card" delay={0.05}>
          <p className="sec-no">04 / Data</p>
          <p className="about-card-lead">Real geography, simulated damage.</p>
          <p>
            Roads, facilities and population are real: the road network, hospitals, clinics, fire and police stations and shelters come from
            OpenStreetMap, and zone population from WorldPop (or OSM building counts where the raster is absent). Damage values in the four
            South Indian scenarios (Aluva flood, Bengaluru flood, Coimbatore earthquake, Visakhapatnam cyclone) are simulated by <code>backend/scripts/build_scenario.py</code>
            and every zone is marked <code>source: simulated</code>; relief stock, accounts and SOS requests are also synthetic.
          </p>
        </Reveal>
      </section>

      <section className="sec sec--black about-block" aria-labelledby="stack-title">
        <p className="sec-bar mono">
          <span>05</span>
          <span>Tech stack</span>
        </p>
        <h2 id="stack-title" className="visually-hidden">
          Tech stack
        </h2>
        <div className="stack-grid">
          {STACK.map(({ group, items }) => (
            <div key={group} className="stack-group">
              <h3>{group}</h3>
              <ul>
                {items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="sec about-notice" aria-labelledby="notice-title">
        <p className="sec-bar mono">
          <span>06</span>
          <span>Data notice</span>
        </p>
        <div className="about-notice-body">
          <h2 id="notice-title" className="about-notice-title">
            Data notice
          </h2>
          <div className="about-notice-text">
            <p>
              All data in this prototype is simulated for demonstration: the disaster scenarios, user accounts, service providers,
              resources, SOS requests and their locations. Places are real, but every figure attached to them is made up.
            </p>
            <p>
              Real datasets will be integrated once they are finalised, for example satellite damage imagery, government resource
              registries and live disaster feeds.
            </p>
          </div>
        </div>
      </section>

      <section className="sec about-credits" aria-labelledby="sources-title">
        <p className="sec-bar mono">
          <span>07</span>
          <span id="sources-title">Base paper and datasets</span>
        </p>
        <ol className="credits-list">
          {SOURCES.map((s, i) => (
            <li key={s.name}>
              <span className="credits-no">{pad2(i + 1)}</span>
              <span className="credits-caption">{s.name}</span>
              <span>{s.role}</span>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.cite}
              </a>
              <span>{s.license}</span>
            </li>
          ))}
        </ol>
        <p className="credits-note">
          Map data © OpenStreetMap contributors (ODbL). xBD is for non-commercial use; this is an academic prototype.
        </p>
      </section>

      <section className="sec about-credits" aria-labelledby="credits-title">
        <p className="sec-bar mono">
          <span>08</span>
          <span id="credits-title">Photo credits</span>
        </p>
        <ol className="credits-list">
          {PHOTO_LIST.map((p, i) => (
            <li key={p.slug}>
              <span className="credits-no">{pad2(i + 1)}</span>
              <span className="credits-caption">{p.caption}</span>
              <span>{p.author}</span>
              <a href={p.page} target="_blank" rel="noreferrer">
                {p.source}
              </a>
              {p.license_url ? (
                <a href={p.license_url} target="_blank" rel="noreferrer">
                  {p.license}
                </a>
              ) : (
                <span>{p.license}</span>
              )}
            </li>
          ))}
        </ol>
        <p className="credits-note">Every photograph was converted to high-contrast grayscale and cropped for this site.</p>
      </section>

      <section className="sec sec--red about-cta" aria-label="Log in to the demo">
        <p className="about-cta-title">Try the demo</p>
        <Link to="/login" className="btn btn--on-red btn--lg">
          Log in with a demo account <span className="arrow">&rarr;</span>
        </Link>
      </section>

      <footer className="team" aria-labelledby="team-title">
        <p id="team-title" className="team-title">
          Project Team
        </p>
        <ul className="team-list">
          {TEAM.map((m) => (
            <li key={m.id}>
              {m.name} — {m.id}
            </li>
          ))}
        </ul>
      </footer>
    </div>
  );
}
