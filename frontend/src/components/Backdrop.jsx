// Fixed background layers: drifting glows and a slowly moving tactical grid.
export default function Backdrop() {
  return (
    <div className="backdrop" aria-hidden="true">
      <div className="backdrop-glow backdrop-glow--violet" />
      <div className="backdrop-glow backdrop-glow--teal" />
      <div className="backdrop-glow backdrop-glow--crimson" />
      <div className="backdrop-grid" />
      <div className="backdrop-vignette" />
    </div>
  );
}
