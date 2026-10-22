import { levelClass } from "../constants";

export default function LevelBadge({ level }) {
  return <span className={`badge ${levelClass(level)}`}>{level}</span>;
}
