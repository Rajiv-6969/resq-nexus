// Small inline SVG icons (stroke = currentColor) so the UI needs no icon library.

function Svg({ children, size = 18, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
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

export function LogoMark({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="8" fill="#163a52" />
      <path d="M16 4.5c-4.6 0-8.3 3.6-8.3 8 0 5.9 8.3 14.2 8.3 14.2s8.3-8.3 8.3-14.2c0-4.4-3.7-8-8.3-8z" fill="#e2483d" />
      <path d="M14.6 8.6h2.8v2.6H20V14h-2.6v2.6h-2.8V14H12v-2.8h2.6z" fill="#fff" />
    </svg>
  );
}

export const CheckIcon = (p) => (
  <Svg {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Svg>
);

export const ChevronIcon = (p) => (
  <Svg {...p}>
    <path d="M9 6l6 6-6 6" />
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
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" />
  </Svg>
);
