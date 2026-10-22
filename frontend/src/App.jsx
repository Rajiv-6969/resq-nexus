import { useState } from "react";

function App() {
  const [topic, setTopic] = useState("");
  const [contentType, setContentType] = useState("youtube");
  const [tone, setTone] = useState("conversational");
  const [lengthMinutes, setLengthMinutes] = useState("");
  const [script, setScript] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setScript("");

    try {
      const res = await fetch("http://localhost:8000/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          content_type: contentType,
          tone,
          length_minutes: lengthMinutes ? Number(lengthMinutes) : null,
        }),
      });

      if (!res.ok) {
        throw new Error("Something went wrong on the server.");
      }

      const data = await res.json();
      setScript(data.script);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="title">Script Desk</h1>
      <p className="subtitle">Describe what you need. Get a script written for you.</p>

      <div className="card">
        <label className="field-label">Content type</label>
        <select
          className="select"
          value={contentType}
          onChange={(e) => setContentType(e.target.value)}
        >
          <option value="youtube">YouTube video</option>
          <option value="ad">Ad</option>
          <option value="reel">Reel</option>
          <option value="tiktok">TikTok</option>
          <option value="podcast">Podcast</option>
          <option value="short_film">Short Film</option>
        </select>

        <label className="field-label">Tone</label>
        <select
          className="select"
          value={tone}
          onChange={(e) => setTone(e.target.value)}
        >
          <option value="conversational">Conversational</option>
          <option value="energetic">Energetic</option>
          <option value="authoritative">Authoritative</option>
          <option value="witty">Witty</option>
          <option value="calm">Calm</option>
        </select>

        <label className="field-label">Target length (minutes, optional)</label>
        <input
          className="input"
          type="number"
          value={lengthMinutes}
          onChange={(e) => setLengthMinutes(e.target.value)}
          placeholder="e.g. 3"
        />

        <label className="field-label">Topic</label>
        <textarea
          className="textarea"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. why cats knock things off tables"
          rows={3}
        />

        <button
          className="generate-button"
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
        >
          {loading ? "Writing…" : "Generate Script"}
        </button>

        {error && <p className="error-text">{error}</p>}
      </div>

      {script && <div className="output-card">{script}</div>}
    </div>
  );
}

export default App;