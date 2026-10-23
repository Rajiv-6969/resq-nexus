import { Link, useNavigate } from "react-router";
import AnimatedNumber from "../components/AnimatedNumber";
import Figure from "../components/Figure";
import { AsteriskMark } from "../components/icons";
import { Reveal, Wipe } from "../components/Reveal";
import { DISASTER_META, formatNumber } from "../constants";
import { PHOTOS, SCENARIO_PHOTOS } from "../lib/photos";
import { useAppData } from "../state/contexts";

const pad2 = (n) => String(n).padStart(2, "0");

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
      {/* 01: hero */}
      <section className="hero" aria-labelledby="hero-title">
        <p className="hero-meta mono">
          <span>(01) Index</span>
          <span>Disaster response decision support</span>
          <span>India / {ready ? `${scenarios.length} demo scenarios` : "loading"}</span>
          <span>20.59&deg; N 78.96&deg; E</span>
        </p>

        <Wipe as="h1" id="hero-title" className="hero-title">
          ResQ Nexus
        </Wipe>

        <div className="hero-row">
          <Reveal className="hero-copy">
            <p className="hero-lede">
              Intelligent Disaster Response and Resource Allocation System. It ranks every affected zone, shares out
              scarce relief between them and explains each decision in plain language.
            </p>
            <Link to={launchTo} className="btn btn--solid btn--lg">
              Launch Command Centre <span className="arrow">&rarr;</span>
            </Link>
          </Reveal>

          <div className="hero-numeral">
            <span className="numeral" aria-hidden="true">
              {ready ? pad2(scenarios.length) : "—"}
            </span>
            <span className="label">
              Demo scenarios
              <br />
              Flood / Earthquake / Wildfire
            </span>
          </div>

          <dl className="hero-stats">
            <div>
              <dt className="label">Zones mapped</dt>
              <dd>
                <AnimatedNumber value={ready ? zones : null} />
              </dd>
            </div>
            <div>
              <dt className="label">People in scope</dt>
              <dd>
                <AnimatedNumber value={ready ? people : null} />
              </dd>
            </div>
            <div>
              <dt className="label">Indian states</dt>
              <dd>
                <AnimatedNumber value={ready ? states : null} />
              </dd>
            </div>
          </dl>

          <div className="hero-mark" aria-hidden="true">
            <AsteriskMark size={72} className="hero-asterisk" />
          </div>
        </div>

        {listState.status === "error" && (
          <p className="hero-offline mono" role="status">
            Backend offline: live scenario figures are unavailable. Start the API and refresh.
          </p>
        )}

        <Figure photo={PHOTOS["hero-chandigarh-assembly"]} index="01" className="hero-figure" eager />
      </section>

      {/* 02: statement */}
      <section className="sec sec--red statement" aria-labelledby="statement-title">
        <p className="sec-bar mono">
          <span>02</span>
          <span>The problem</span>
        </p>
        <Wipe id="statement-title" className="statement-title">
          Where should scarce relief go first?
        </Wipe>
        <Reveal className="statement-body">
          <p>
            After a disaster the stock is always smaller than the need. ResQ Nexus scores every zone on damage,
            population, vulnerability and road access, then shares out rescue teams, medical kits, food packets,
            shelters and vehicles, and says why each zone received what it did.
          </p>
        </Reveal>
      </section>

      {/* 03: the project (in place of the old pipeline diagram) */}
      <section className="sec sec--black project" aria-labelledby="project-title">
        <div className="project-text">
          <p className="sec-bar mono">
            <span>03</span>
            <span>The project</span>
          </p>
          <Wipe id="project-title" className="project-title">
            A command centre for relief decisions
          </Wipe>
          <Reveal className="project-body">
            <p className="project-desc">
              Pick a flood, earthquake or wildfire scenario, decide what matters most and run the Allocation Engine.
              Every affected zone gets its share of each resource, a relief depot, a road route and a travel time,
              with a plain-language explanation beside it.
            </p>
            <Link to={launchTo} className="btn btn--on-dark btn--lg">
              Launch Command Centre <span className="arrow">&rarr;</span>
            </Link>
          </Reveal>
        </div>
        <Reveal className="project-figure">
          <Figure photo={PHOTOS["relief-assam-floods"]} index="02" />
        </Reveal>
      </section>

      {/* 04: scenarios */}
      <section className="sec scenarios" aria-labelledby="scenarios-title">
        <header className="scenarios-head">
          <p className="sec-bar mono">
            <span>04</span>
            <span>Demo scenarios</span>
          </p>
          <Wipe id="scenarios-title" className="scenarios-title">
            Three disasters. Real places.
          </Wipe>
          <p className="label scenarios-note">
            Synthetic demo data. Zones are real OpenStreetMap places; damage, needs and stock are generated.
          </p>
        </header>

        <div className="scenario-grid">
          {scenarios.map((s, i) => {
            const photo = SCENARIO_PHOTOS[s.disaster_type];
            return (
              <Reveal as="article" key={s.id} className="scenario-card" delay={i * 0.06}>
                {photo && (
                  <div className="scenario-img">
                    <img src={photo.src} alt={photo.caption} loading="lazy" decoding="async" />
                  </div>
                )}
                <div className="scenario-body">
                  <p className="label">
                    {pad2(i + 1)} / {DISASTER_META[s.disaster_type]?.label ?? s.disaster_type}
                  </p>
                  <h3>{s.name}</h3>
                  <p className="scenario-region">
                    {s.region}, {s.state}
                  </p>
                  <dl className="scenario-stats">
                    <div>
                      <dt className="label">Zones</dt>
                      <dd className="num">{s.zone_count}</dd>
                    </div>
                    <div>
                      <dt className="label">People</dt>
                      <dd className="num">{formatNumber(s.total_population)}</dd>
                    </div>
                  </dl>
                </div>
                <button type="button" className="scenario-open" onClick={() => openScenario(s.id)}>
                  Open in Command Centre <span className="arrow">&rarr;</span>
                </button>
                {photo && (
                  <p className="scenario-credit mono">
                    <a href={photo.page} target="_blank" rel="noreferrer">
                      Photo: {photo.caption} / {photo.credit}
                    </a>
                  </p>
                )}
              </Reveal>
            );
          })}
          {!scenarios.length &&
            [0, 1, 2].map((i) => <div key={i} className="scenario-card scenario-card--empty" aria-hidden="true" />)}
        </div>
      </section>
    </div>
  );
}
