// Thin full-width bar at the top of every page.
export default function DemoBar() {
  return (
    <p className="demo-bar mono" role="note">
      <span className="demo-bar-mark" aria-hidden="true" />
      <strong>Demo data</strong>
      <span className="demo-bar-text">— All scenarios, users, resources and locations shown are simulated. Real datasets are yet to be finalised.</span>
    </p>
  );
}
