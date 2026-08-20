import type { FlavorProfile } from '@/lib/api/types';

/**
 * Canonical Malt Radar 7-axis flavor model (source of truth: backend
 * DbReadService._map_canonical_to_app_axes). The public API returns
 * getFlavorProfile() as a JSON string with these keys.
 * Maritime is intentionally excluded to keep the heptagon geometry.
 */
export interface FlavorAxes {
  fruity: number;
  sweet: number;
  spicy: number;
  smoky_peaty: number;
  oak_cask: number;
  malty_cereal: number;
  floral_herbal: number;
}

const AXES: { key: keyof FlavorAxes; label: string; anchor: 'middle' | 'start' | 'end' }[] = [
  { key: 'fruity', label: 'Fruity', anchor: 'middle' },
  { key: 'sweet', label: 'Sweet', anchor: 'start' },
  { key: 'spicy', label: 'Spicy', anchor: 'start' },
  { key: 'smoky_peaty', label: 'Smoky / Peaty', anchor: 'middle' },
  { key: 'oak_cask', label: 'Oak / Cask', anchor: 'middle' },
  { key: 'malty_cereal', label: 'Malty', anchor: 'end' },
  { key: 'floral_herbal', label: 'Floral', anchor: 'end' },
];

const SIZE = 320;
const CENTER = SIZE / 2;
const MAX_R = 108;
const START_ANGLE = -Math.PI / 2;
const STEP = (2 * Math.PI) / AXES.length;

function point(i: number, r: number) {
  const angle = START_ANGLE + i * STEP;
  return { x: CENTER + r * Math.cos(angle), y: CENTER + r * Math.sin(angle) };
}

function polygonPath(radii: number[]) {
  return (
    radii
      .map((r, i) => {
        const { x, y } = point(i, r);
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ') + ' Z'
  );
}

/** Parse the backend's normalized 7-axis JSON string into a numeric map. */
function parseProfile(profile: FlavorProfile | null): FlavorAxes | null {
  const raw = profile?.flavor_profile;
  if (!raw || typeof raw !== 'string') return null;
  try {
    const obj = JSON.parse(raw) as Record<string, number>;
    const out: FlavorAxes = {
      fruity: Number(obj.fruity) || 0,
      sweet: Number(obj.sweet) || 0,
      spicy: Number(obj.spicy) || 0,
      smoky_peaty: Number(obj.smoky_peaty) || 0,
      oak_cask: Number(obj.oak_cask) || 0,
      malty_cereal: Number(obj.malty_cereal) || 0,
      floral_herbal: Number(obj.floral_herbal) || 0,
    };
    // Reject all-zero (no signal) — treat as missing data.
    if (Object.values(out).every((v) => v === 0)) return null;
    return out;
  } catch {
    return null;
  }
}

interface Props {
  profile: FlavorProfile | null;
  size?: number;
}

export function FlavorProfileChart({ profile }: Props) {
  const axes = parseProfile(profile);
  if (!axes) {
    return (
      <div className="text-textMuted text-sm">Flavor profile coming soon.</div>
    );
  }

  // Normalize each axis to 0–100 (backend values are unbounded floats).
  const maxVal = Math.max(1, ...AXES.map((a) => axes[a.key]));
  const dataRadii = AXES.map((a) => ((axes[a.key] / maxVal) * MAX_R));
  const rings = [0.2, 0.4, 0.6, 0.8, 1];

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="h-full w-full overflow-visible"
      role="img"
      aria-label="Seven-dimension Malt Radar flavor profile"
    >
      <defs>
        <radialGradient id="flavor-fill" cx="50%" cy="50%" r="65%">
          <stop offset="0%" stopColor="oklch(0.92 0.16 92)" stopOpacity="0.9" />
          <stop offset="45%" stopColor="#A6672C" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#6B1E23" stopOpacity="0.22" />
        </radialGradient>
        <radialGradient id="flavor-ring" cx="50%" cy="50%" r="50%">
          <stop offset="80%" stopColor="#A6672C" stopOpacity="0" />
          <stop offset="100%" stopColor="#A6672C" stopOpacity="0.1" />
        </radialGradient>
        <filter id="flavor-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <circle cx={CENTER} cy={CENTER} r={MAX_R + 20} fill="url(#flavor-ring)" />

      {rings.map((f, ri) => (
        <path
          key={f}
          d={polygonPath(AXES.map(() => f * MAX_R))}
          fill="none"
          stroke="#A6672C"
          strokeOpacity={ri === rings.length - 1 ? 0.5 : 0.16}
          strokeWidth={ri === rings.length - 1 ? 1.25 : 0.75}
        />
      ))}

      {AXES.map((a, i) => {
        const { x, y } = point(i, MAX_R);
        return (
          <line
            key={a.key}
            x1={CENTER}
            y1={CENTER}
            x2={x}
            y2={y}
            stroke="#A6672C"
            strokeOpacity="0.2"
            strokeWidth="0.75"
          />
        );
      })}

      <path
        d={polygonPath(dataRadii)}
        fill="url(#flavor-fill)"
        stroke="#EDE1C8"
        strokeWidth="2.5"
        strokeLinejoin="round"
        filter="url(#flavor-glow)"
        style={{ transition: 'all 0.7s ease-out' }}
      />

      {dataRadii.map((r, i) => {
        const { x, y } = point(i, r);
        return (
          <circle
            key={AXES[i].key}
            cx={x}
            cy={y}
            r="3"
            fill="#F5ECD8"
            style={{ transition: 'all 0.7s ease-out' }}
          />
        );
      })}

      {AXES.map((a, i) => {
        const { x, y } = point(i, MAX_R + 24);
        const dy = i === 0 ? -2 : i === 3 || i === 4 ? 12 : 4;
        return (
          <text
            key={a.key}
            x={x}
            y={y + dy}
            textAnchor={a.anchor}
            fontSize="14"
            fontWeight="600"
            letterSpacing="0.02em"
            fill="#BDB2A0"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}
