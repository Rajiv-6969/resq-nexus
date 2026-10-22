const STAGES = ["Assess", "Prioritise", "Allocate", "Explain"];

function App() {
  return (
    <div className="page">
      <h1 className="title">ResQ Nexus</h1>
      <p className="subtitle">Intelligent Disaster Response and Resource Allocation</p>
      <div className="card">
        <p className="pipeline">{STAGES.join(" → ")}</p>
        <p className="muted">The scenario dashboard is under construction.</p>
      </div>
    </div>
  );
}

export default App;
