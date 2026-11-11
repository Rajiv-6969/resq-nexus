// Disaster-type illustration whose intensity follows the damage severity (0-3).
export default function DamageGlyph({ type, severity, size = 72 }) {
  const water = [0, 14, 25, 37][severity];
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={`glyph glyph--${type} glyph--s${severity}`} aria-hidden="true" focusable="false">
      <rect x="0" y="0" width="64" height="64" className="glyph-bg" />
      {type === "flood" && (
        <>
          <path d="M18 34 32 22l14 12v16H18z" className="glyph-house" />
          <rect x="28" y="40" width="8" height="10" className="glyph-door" />
          {severity > 0 && (
            <path
              className="glyph-water"
              d={`M4 ${54 - water} q6 -4 12 0 t12 0 t12 0 t12 0 t12 0 V60 H4 Z`}
            />
          )}
          <path d="M4 54h56" className="glyph-ground" />
        </>
      )}
      {type === "earthquake" && (
        <>
          <g transform={severity === 3 ? "rotate(-9 32 52)" : undefined}>
            <rect x="20" y="16" width="24" height="36" className="glyph-house" />
            <path d="M25 22h4M35 22h4M25 30h4M35 30h4M25 38h4M35 38h4" className="glyph-window" />
            {severity >= 1 && <path d="M32 16l-3 8 4 5-3 7" className="glyph-crack" />}
            {severity >= 2 && <path d="M44 28l-6 4 3 4-5 5" className="glyph-crack" />}
            {severity >= 3 && <path d="M20 34l7 3-2 5 6 4" className="glyph-crack" />}
          </g>
          {severity >= 3 && <path d="M44 52l4-4 3 4 3-2 2 2" className="glyph-rubble" />}
          <path d="M4 52h56" className="glyph-ground" />
        </>
      )}
      {type === "cyclone" && (
        <>
          <g transform={severity >= 2 ? "skewX(-8)" : undefined}>
            <path d="M18 34 32 22l14 12v16H18z" className="glyph-house" />
            <rect x="28" y="40" width="8" height="10" className="glyph-door" />
          </g>
          {severity >= 3 && <path d="M44 24l10-6M46 30l12-2" className="glyph-crack" />}
          {[0, 1, 2].slice(0, severity).map((i) => (
            <path key={i} className="glyph-wind" style={{ animationDelay: `${i * 0.2}s` }} d={`M4 ${14 + i * 8}h${18 + i * 6}c4 0 4-5 0-5`} />
          ))}
          {severity > 0 && <path className="glyph-water" d={`M4 ${56 - severity * 2} q6 -3 12 0 t12 0 t12 0 t12 0 t12 0 V60 H4 Z`} />}
          <path d="M4 54h56" className="glyph-ground" />
        </>
      )}
      {type === "wildfire" && (
        <>
          <path d="M14 50V40M14 40l-6 0 6-12 6 12z" className="glyph-tree" />
          <path d="M32 50V36M32 36h-8l8-16 8 16z" className="glyph-tree" />
          <path d="M50 50V40M50 40h-6l6-12 6 12z" className="glyph-tree" />
          {[0, 1, 2].slice(0, severity).map((i) => (
            <path
              key={i}
              className="glyph-flame"
              style={{ animationDelay: `${i * 0.25}s` }}
              d={`M${[32, 14, 50][i]} ${[22, 30, 30][i]}c1.5 4 6 6 6 11a6 6 0 0 1-12 0c0-3 1.6-4.8 3.2-6.6.4 2 1.3 3.2 2.5 3.7.4-3.8-.6-6.4.3-8.1z`}
            />
          ))}
          <path d="M4 50h56" className="glyph-ground" />
        </>
      )}
    </svg>
  );
}
