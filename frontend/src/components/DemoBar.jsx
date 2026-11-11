// Thin full-width bar at the top of every page.
export default function DemoBar() {
  return (
    <p className="demo-bar mono" role="note">
      <span className="demo-bar-mark" aria-hidden="true" />
      <strong>Demo data</strong>
      <span className="demo-bar-text">
        — Roads, facilities and population are real (OpenStreetMap, WorldPop); damage values in the Indian scenarios are simulated, as are
        accounts, relief stock and SOS requests.
      </span>
    </p>
  );
}
