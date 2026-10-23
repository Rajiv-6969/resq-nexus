// A photograph with a mono caption that carries its credit.
export default function Figure({ photo, index, className = "", eager = false }) {
  if (!photo) return null;
  return (
    <figure className={`figure ${className}`}>
      <div className="figure-img">
        <img src={photo.src} alt={photo.caption} loading={eager ? "eager" : "lazy"} decoding="async" />
      </div>
      <figcaption className="figcaption">
        <span>
          Fig. {index} / {photo.caption}
        </span>
        <a href={photo.page} target="_blank" rel="noreferrer">
          {photo.credit}
        </a>
      </figcaption>
    </figure>
  );
}
