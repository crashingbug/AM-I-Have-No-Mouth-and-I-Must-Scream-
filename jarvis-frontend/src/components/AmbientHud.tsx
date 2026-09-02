import type { CSSProperties } from "react";

type AmbientHudProps = { active: boolean; level: number };

const signalBars = Array.from({ length: 28 }, (_, index) => {
  const normalized = (index - 13.5) / 13.5;
  const curve = Math.cos(normalized * (Math.PI / 2.2));
  const baseHeight = 18 + curve * (32 + ((index * 17) % 55));
  return {
    x: 24 + index * 20.5,
    height: Math.round(baseHeight),
    delay: `${(index % 7) * -0.14}s`,
    peakDelay: `${((index + 3) % 5) * -0.18}s`,
  };
});

const datumTicks = Array.from({ length: 15 }, (_, i) => 24 + i * 41);

export function AmbientHud({ active, level }: AmbientHudProps) {
  return (
    <div className={`ambient-hud ${active ? "is-active" : ""}`} style={{ "--audio-level": level } as CSSProperties} aria-hidden="true">
      <svg className="signal-field" viewBox="0 0 620 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="hudLineGrad" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#ff4d00" stopOpacity="0.4" />
            <stop offset="60%" stopColor="#ff8c2e" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#ffbe5c" stopOpacity="1" />
          </linearGradient>
          <linearGradient id="hudActiveGrad" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#ff2200" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#ff7a18" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#ffe6a3" stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* Decorative Circuit & Corner Telemetry */}
        <path className="hud-corner-bracket" d="M 12 140 L 12 186 L 58 186" fill="none" />
        <path className="hud-corner-bracket" d="M 608 140 L 608 186 L 562 186" fill="none" />

        {/* Baseline datum line & grid ticks */}
        <line className="hud-datum-line" x1="16" y1="186" x2="604" y2="186" />
        {datumTicks.map((tickX) => (
          <line className="hud-datum-tick" key={`tick-${tickX}`} x1={tickX} y1="186" x2={tickX} y2="191" />
        ))}

        {/* Audio Visualiser Spectrum Lines */}
        {signalBars.map((bar, index) => (
          <g key={`bar-${bar.x}`}>
            <line
              className="signal-line"
              style={{ "--line-delay": bar.delay } as CSSProperties}
              x1={bar.x}
              x2={bar.x}
              y1="184"
              y2={184 - bar.height}
            />
            <circle
              className="signal-node"
              style={{ "--line-delay": bar.peakDelay } as CSSProperties}
              cx={bar.x}
              cy={184 - bar.height - 4}
              r={index % 3 === 0 ? 1.8 : 1.2}
            />
          </g>
        ))}

        {/* Scan sweep line */}
        <line className="hud-scan-beam" x1="16" y1="186" x2="604" y2="186" />
      </svg>

      <div className="hud-telemetry">
        <p className="hud-caption">{active ? "AUDIO LINK // ACTIVE FEED" : "AUDIO LINK // STANDBY"}</p>
        <span className="hud-sub-caption">ACOUSTIC SPECTRUM • 24.8 kHz</span>
      </div>
    </div>
  );
}
