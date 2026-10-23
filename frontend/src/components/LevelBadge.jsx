import { levelClass } from "../constants";

export default function LevelBadge({ level, size }) {
  return <span className={`tag ${levelClass(level)}${size === "lg" ? " tag--lg" : ""}`}>{level}</span>;
}
