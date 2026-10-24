// A flat bar for how much of a resource is left (solid fill, 1px frame).
export default function CapacityBar({ available, total }) {
  const share = total > 0 ? Math.min(1, available / total) : 0;
  return (
    <span className="capacity" aria-hidden="true">
      <span className="capacity-fill" style={{ width: `${(share * 100).toFixed(1)}%` }} />
    </span>
  );
}
