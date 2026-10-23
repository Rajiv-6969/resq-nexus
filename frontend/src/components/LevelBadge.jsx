import { levelClass } from "../constants";

export default function LevelBadge({ level, size }) {
  return <span className={`badge ${levelClass(level)}${size ? ` badge--${size}` : ""}`}>{level}</span>;
}
