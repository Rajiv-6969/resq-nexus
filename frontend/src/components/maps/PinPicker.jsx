import { useMemo, useRef } from "react";
import { Marker, useMapEvents } from "react-leaflet";
import { roundCoord } from "../../lib/geolocation";
import { DEFAULT_LOCATION } from "../../lib/map";
import { pinIcon } from "../../lib/markers";
import BaseMap, { FlyTo } from "./BaseMap";

function ClickToPlace({ onPlace }) {
  useMapEvents({ click: (e) => onPlace({ latitude: roundCoord(e.latlng.lat), longitude: roundCoord(e.latlng.lng) }) });
  return null;
}

// Pick a point: tap the map (or drag the pin). Keyboard users can pan with the arrow keys
// and press "Pin the map centre". `focus` re-centres the map, e.g. after "use my location".
export default function PinPicker({ value, onChange, focus, start = DEFAULT_LOCATION, label = "Map for choosing a location", invalid }) {
  const mapRef = useRef(null);
  const handlers = useMemo(
    () => ({
      dragend: (e) => {
        const point = e.target.getLatLng();
        onChange({ latitude: roundCoord(point.lat), longitude: roundCoord(point.lng) });
      },
    }),
    [onChange],
  );

  const pinCentre = () => {
    const centre = mapRef.current?.getCenter();
    if (centre) onChange({ latitude: roundCoord(centre.lat), longitude: roundCoord(centre.lng) });
  };

  return (
    <div className={`pin-picker${invalid ? " is-invalid" : ""}`}>
      <div className="map-pane pin-map">
        <BaseMap center={value ?? start} zoom={value ? 15 : 12} label={label} mapRef={mapRef}>
          <ClickToPlace onPlace={onChange} />
          <FlyTo point={focus} zoom={15} />
          {value && <Marker position={[value.latitude, value.longitude]} icon={pinIcon()} draggable eventHandlers={handlers} keyboard={false} />}
        </BaseMap>
        <p className="map-corner map-corner--tl mono" aria-hidden="true">
          {value ? "Pin dropped / drag to adjust" : "Tap the map to drop a pin"}
        </p>
      </div>
      <div className="pin-bar">
        <p className="pin-readout mono" aria-live="polite">
          {value ? `${value.latitude.toFixed(5)}, ${value.longitude.toFixed(5)}` : "No location chosen"}
        </p>
        <button type="button" className="btn btn--sm" onClick={pinCentre}>
          Pin the map centre
        </button>
      </div>
    </div>
  );
}
