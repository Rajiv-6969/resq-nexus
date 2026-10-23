// Inline SVG icons (stroke = currentColor) so the UI needs no icon library.
import { useId } from "react";

function Svg({ children, size = 18, strokeWidth = 2, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export function LogoMark({ size = 34 }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" focusable="false" className="logo-mark">
      <defs>
        <linearGradient id={`${id}-ring`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2EC4B6" />
          <stop offset="1" stopColor="#9D4EDD" />
        </linearGradient>
        <radialGradient id={`${id}-core`} cx="50%" cy="40%" r="65%">
          <stop offset="0" stopColor="#ff7a84" />
          <stop offset="1" stopColor="#b3172b" />
        </radialGradient>
      </defs>
      <path d="M20 2.5 35.2 11.25v17.5L20 37.5 4.8 28.75v-17.5z" fill="#0f1730" stroke={`url(#${id}-ring)`} strokeWidth="2" />
      <path d="M20 8.6c-4.4 0-8 3.4-8 7.6 0 5.7 8 13.3 8 13.3s8-7.6 8-13.3c0-4.2-3.6-7.6-8-7.6z" fill={`url(#${id}-core)`} />
      <path d="M18.6 12.4h2.8V15H24v2.8h-2.6v2.6h-2.8v-2.6H16V15h2.6z" fill="#fff" />
    </svg>
  );
}

export const CheckIcon = (p) => (
  <Svg {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Svg>
);
export const ArrowRightIcon = (p) => (
  <Svg {...p}>
    <path d="M4 12h15M13 6l6 6-6 6" />
  </Svg>
);
export const CloseIcon = (p) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Svg>
);
export const AlertIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3l9.5 17h-19z" />
    <path d="M12 10v4.5M12 17.5v.01" />
  </Svg>
);
export const InfoIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8v.01" />
  </Svg>
);
export const PlayIcon = (p) => (
  <Svg {...p}>
    <path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none" />
  </Svg>
);
export const RefreshIcon = (p) => (
  <Svg {...p}>
    <path d="M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16M20 20v-4h-4" />
  </Svg>
);
export const LifebuoyIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="4" />
    <path d="M5.6 5.6l3.6 3.6M14.8 14.8l3.6 3.6M18.4 5.6l-3.6 3.6M9.2 14.8l-3.6 3.6" />
  </Svg>
);
export const MedkitIcon = (p) => (
  <Svg {...p}>
    <rect x="3" y="7" width="18" height="13" rx="2" />
    <path d="M9 7V5h6v2M12 10.5v6M9 13.5h6" />
  </Svg>
);
export const FoodIcon = (p) => (
  <Svg {...p}>
    <path d="M4 8l8-4 8 4v8l-8 4-8-4z" />
    <path d="M4 8l8 4 8-4M12 12v8" />
  </Svg>
);
export const ShelterIcon = (p) => (
  <Svg {...p}>
    <path d="M3 20L12 5l9 15z" />
    <path d="M12 5v15M9 20l3-5 3 5" />
  </Svg>
);
export const TruckIcon = (p) => (
  <Svg {...p}>
    <rect x="2" y="6" width="12" height="10" rx="1" />
    <path d="M14 9h4l3 3.5V16h-7" />
    <circle cx="6.5" cy="17.5" r="2" />
    <circle cx="17" cy="17.5" r="2" />
  </Svg>
);
export const WavesIcon = (p) => (
  <Svg {...p}>
    <path d="M2 8c2.5-2 4.5-2 7 0s4.5 2 7 0 4.5-2 6 0M2 13c2.5-2 4.5-2 7 0s4.5 2 7 0 4.5-2 6 0M2 18c2.5-2 4.5-2 7 0s4.5 2 7 0 4.5-2 6 0" />
  </Svg>
);
export const QuakeIcon = (p) => (
  <Svg {...p}>
    <path d="M2 12h4l2.5-6 4 13 3-9 2 2H22" />
  </Svg>
);
export const FlameIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3c1 3.5 5 5.5 5 10.5a5 5 0 0 1-10 0c0-2.5 1.2-4 2.5-5.5.3 1.6 1 2.6 2 3 .3-3-.5-5.5.5-8z" />
  </Svg>
);
export const SparkIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6z" />
    <path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />
  </Svg>
);
export const RadarIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <path d="M12 12l6.4-6.4M12 3v2M21 12h-2" />
  </Svg>
);
export const GaugeIcon = (p) => (
  <Svg {...p}>
    <path d="M4.5 18a9 9 0 1 1 15 0" />
    <path d="M12 13l4-5M12 13v.01" />
  </Svg>
);
export const RouteIcon = (p) => (
  <Svg {...p}>
    <circle cx="6" cy="18" r="2.5" />
    <circle cx="18" cy="6" r="2.5" />
    <path d="M8.5 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.5" />
  </Svg>
);
export const DepotIcon = (p) => (
  <Svg {...p}>
    <path d="M3 10l9-6 9 6v10H3z" />
    <path d="M7 20v-6h10v6M7 17h10" />
  </Svg>
);
export const MapIcon = (p) => (
  <Svg {...p}>
    <path d="M3 6.5l6-2.5 6 2.5 6-2.5v13.5l-6 2.5-6-2.5-6 2.5z" />
    <path d="M9 4v13.5M15 6.5V20" />
  </Svg>
);
export const ChartIcon = (p) => (
  <Svg {...p}>
    <path d="M4 20V4M4 20h16" />
    <path d="M8 16v-5M12 16V8M16 16v-8M20 16v-3" />
  </Svg>
);
export const LayersIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3l9 5-9 5-9-5z" />
    <path d="M3 13l9 5 9-5" />
  </Svg>
);
export const SlidersIcon = (p) => (
  <Svg {...p}>
    <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0" />
    <circle cx="16" cy="6" r="2" />
    <circle cx="10" cy="12" r="2" />
    <circle cx="18" cy="18" r="2" />
  </Svg>
);
export const ListIcon = (p) => (
  <Svg {...p}>
    <path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />
  </Svg>
);
export const ClockIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Svg>
);
export const ScaleIcon = (p) => (
  <Svg {...p}>
    <path d="M12 4v16M7 20h10M5 8h14M12 4l-1 .5M12 4l1 .5" />
    <path d="M5 8l-3 6a3 3 0 0 0 6 0zM19 8l-3 6a3 3 0 0 0 6 0z" />
  </Svg>
);
export const TargetIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <circle cx="12" cy="12" r="1" />
  </Svg>
);
export const CpuIcon = (p) => (
  <Svg {...p}>
    <rect x="6" y="6" width="12" height="12" rx="2" />
    <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
    <path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3" />
  </Svg>
);
export const BrainIcon = (p) => (
  <Svg {...p}>
    <path d="M9 4a3 3 0 0 0-3 3v.2A3 3 0 0 0 4 10a3 3 0 0 0 1 2.2A3 3 0 0 0 6 17a3 3 0 0 0 3 3V4z" />
    <path d="M15 4a3 3 0 0 1 3 3v.2a3 3 0 0 1 2 2.8 3 3 0 0 1-1 2.2A3 3 0 0 1 18 17a3 3 0 0 1-3 3V4z" />
    <path d="M9 9H7.5M9 14H7M15 9h1.5M15 14h2" />
  </Svg>
);
export const UsersIcon = (p) => (
  <Svg {...p}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M21.5 20a6.5 6.5 0 0 0-4-6" />
  </Svg>
);
export const ShieldIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z" />
    <path d="M9 12l2 2 4-4" />
  </Svg>
);
export const CodeIcon = (p) => (
  <Svg {...p}>
    <path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16" />
  </Svg>
);
