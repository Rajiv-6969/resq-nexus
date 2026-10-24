import { glyphSvg, resourceSvg, sosSvg } from "../lib/markers";

// Inline SVG glyphs (static strings built in lib/markers.js, never user input).
export function ResourceGlyph({ type, status = "OPEN", size = 22, outline = false }) {
  return <span className="glyph" aria-hidden="true" dangerouslySetInnerHTML={{ __html: outline ? glyphSvg(type, size) : resourceSvg(type, status, size) }} />;
}

export function SosGlyph({ level, status, size = 18 }) {
  return <span className="glyph" aria-hidden="true" dangerouslySetInnerHTML={{ __html: sosSvg(level, status, size) }} />;
}
