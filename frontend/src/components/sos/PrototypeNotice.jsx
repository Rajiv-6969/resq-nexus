// Fixed at the bottom of the SOS screens.
export default function PrototypeNotice() {
  return (
    <aside className="prototype-notice" role="note" aria-label="Prototype notice">
      <span className="prototype-mark" aria-hidden="true" />
      <p>
        <strong>PROTOTYPE</strong> — This system is not connected to emergency services. In a real emergency, call{" "}
        <a href="tel:112">112</a>.
      </p>
    </aside>
  );
}
