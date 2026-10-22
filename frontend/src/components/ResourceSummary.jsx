import { RESOURCE_ICONS } from "./iconMaps";
import { RESOURCES, formatNumber } from "../constants";

export default function ResourceSummary({ resources }) {
  return (
    <section className="card">
      <h2 className="card-title">Available resources</h2>
      <ul className="resource-grid">
        {RESOURCES.map(({ key, label, hint }) => {
          const Icon = RESOURCE_ICONS[key];
          return (
            <li key={key} className="resource">
              <span className="resource-icon">
                <Icon size={18} />
              </span>
              <span className="resource-text">
                <span className="resource-value">{formatNumber(resources[key] ?? 0)}</span>
                <span className="resource-label">{label}</span>
                <span className="resource-hint">{hint}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
