import { loadFont } from "@remotion/google-fonts/DMSans";
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const { fontFamily } = loadFont("normal", { weights: ["400", "500", "700"], subsets: ["latin"] });

export const FPS = 30;
const C = {
  ink: "#1d0c17", paper: "#fbf8fa", plum: "#5b1a63", pink: "#ec2d7a", softPink: "#f58db4",
  green: "#0e9f6e", mint: "#d7f2e3", muted: "#6e5f69", line: "#e6dde4", amber: "#d97706", red: "#dc2626",
};

const SCENES = { stakes: 270, maria: 540, islands: 450, grid: 780, close: 480, thanks: 300 };
export const filmDuration = Object.values(SCENES).reduce((a, b) => a + b, 0);
const OPENER = { stakes: 240, maria: 480, islands: 360, tag: 120 };
export const openerDuration = Object.values(OPENER).reduce((a, b) => a + b, 0);

export type FilmProps = { voiceover: boolean; music: boolean; demoFootage: boolean; opener: boolean };

// ------------------------------------------------------------------ helpers

const fade = (frame: number, start: number, dur: number, edge = 15) =>
  interpolate(frame, [start, start + edge, start + dur - edge, start + dur], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

const Caption: React.FC<{ text: string; from: number; dur: number; color?: string; size?: number; top?: number }> = ({
  text, from, dur, color = C.ink, size = 64, top = 760,
}) => {
  const frame = useCurrentFrame();
  const o = fade(frame, from, dur);
  const y = interpolate(frame, [from, from + 20], [16, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", top, left: 160, right: 160, textAlign: "center", opacity: o, transform: `translateY(${y}px)`,
      fontSize: size, fontWeight: 700, letterSpacing: -1.5, color, lineHeight: 1.15 }}>
      {text}
    </div>
  );
};

const Tag: React.FC<{ text: string; color?: string; bg?: string }> = ({ text, color = C.muted, bg = "rgba(0,0,0,0.05)" }) => (
  <div style={{ position: "absolute", top: 64, right: 80, fontSize: 26, fontWeight: 500, color, background: bg, padding: "8px 20px", borderRadius: 999 }}>
    {text}
  </div>
);

const Lock: React.FC<{ x: number; y: number; color?: string }> = ({ x, y, color = C.green }) => (
  <g transform={`translate(${x - 14}, ${y - 18})`}>
    <path d="M6 16 V11 a8 8 0 0 1 16 0 V16" fill="none" stroke={color} strokeWidth={3.5} />
    <rect x={2} y={16} width={24} height={18} rx={4} fill={color} />
  </g>
);

// ------------------------------------------------------------------ scenes

const Stakes: React.FC = () => {
  const frame = useCurrentFrame();
  const n = Math.round(interpolate(frame, [10, 90], [0, 95492], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }));
  return (
    <AbsoluteFill style={{ background: C.plum, color: C.paper, justifyContent: "center", alignItems: "center" }}>
      <div style={{ fontSize: 300, fontWeight: 700, letterSpacing: -12, opacity: fade(frame, 0, SCENES.stakes, 12) }}>{n.toLocaleString("en-US")}</div>
      <Caption text="people in the US are waiting for a kidney." from={40} dur={SCENES.stakes - 40} color="#f3d9f0" size={56} top={720} />
    </AbsoluteFill>
  );
};

const Maria: React.FC = () => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [150, 250], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const broken = frame > 300;
  const x = spring({ frame: frame - 300, fps: FPS, config: { damping: 12 } });
  const person = (cx: number, name: string, sub: string, accent: string) => (
    <g>
      <circle cx={cx} cy={380} r={150} fill="#fff" stroke={accent} strokeWidth={6} />
      <text x={cx} y={370} textAnchor="middle" fontSize={60} fontWeight={700} fill={C.ink} fontFamily={fontFamily}>{name}</text>
      {sub.split(" · ").map((line, i) => (
        <text key={line} x={cx} y={418 + i * 34} textAnchor="middle" fontSize={28} fill={C.muted} fontFamily={fontFamily}>{line}</text>
      ))}
    </g>
  );
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Tag text="Dramatization" />
      <svg width={1920} height={1080} style={{ position: "absolute", opacity: fade(frame, 0, SCENES.maria, 15) }}>
        <line x1={690} y1={380} x2={690 + 540 * draw} y2={380} stroke={broken ? C.red : C.pink} strokeWidth={8} strokeDasharray={broken ? "18 14" : "0"} />
        {person(540, "Tom", "husband · type A", C.line)}
        {person(1380, "Maria", "waiting 7 years · type O", C.pink)}
        {broken && (
          <text x={960} y={410} textAnchor="middle" fontSize={120 * x} fontWeight={700} fill={C.red} fontFamily={fontFamily}>✕</text>
        )}
      </svg>
      <Caption text="Maria has waited 7 years." from={10} dur={150} />
      <Caption text="Her husband Tom wants to give her his kidney." from={160} dur={140} />
      <Caption text="He can't. Wrong blood type." from={300} dur={130} color={C.red} />
      <Caption text="At least 1 in 3 willing donors is the wrong match." from={430} dur={110} size={52} color={C.muted} />
    </AbsoluteFill>
  );
};

const HOSPITALS = ["Bay General", "Mission Medical", "Valley Health", "Peninsula Medical", "Capitol Hospital"];
const CITIES = ["San Francisco", "Oakland", "San Jose", "Palo Alto", "Sacramento"];

const Islands: React.FC<{ dur: number }> = ({ dur }) => {
  const frame = useCurrentFrame();
  const spread = interpolate(frame, [0, 120], [120, 330], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ background: "#f2ecf0" }}>
      <svg width={1920} height={1080} style={{ position: "absolute", opacity: fade(frame, 0, dur, 15) }}>
        {HOSPITALS.map((h, i) => {
          const a = (-90 + i * 72) * (Math.PI / 180);
          const cx = 960 + spread * 1.5 * Math.cos(a), cy = 430 + spread * 0.85 * Math.sin(a);
          return (
            <g key={h}>
              <circle cx={cx} cy={cy} r={92} fill="#fff" stroke={C.line} strokeWidth={4} />
              <text x={cx} y={cy + 14} textAnchor="middle" fontSize={22} fontWeight={700} fill={C.ink} fontFamily={fontFamily}>{h}</text>
              <text x={cx} y={cy + 42} textAnchor="middle" fontSize={20} fill={C.muted} fontFamily={fontFamily}>{CITIES[i]}</text>
              <Lock x={cx} y={cy - 40} />
            </g>
          );
        })}
      </svg>
      <Caption text="The right match exists, at another hospital." from={20} dur={dur / 2} top={800} />
      <Caption text="But hospitals can't share patient data." from={dur / 2 + 10} dur={dur / 2 - 10} top={800} color={C.plum} />
    </AbsoluteFill>
  );
};

const GridScene: React.FC = () => {
  const frame = useCurrentFrame();
  const HUB = { x: 960, y: 470 };
  const R = 250;
  const pos = HOSPITALS.map((_, i) => {
    const a = (-90 + i * 72) * (Math.PI / 180);
    return { x: HUB.x + R * 1.35 * Math.cos(a), y: HUB.y + R * Math.sin(a) };
  });
  // Optimal loops from the verified 5-couple scenario: Bay->Mission->Valley->Bay and Peninsula<->Capitol.
  const loops = [[0, 1], [1, 2], [2, 0], [3, 4], [4, 3]];
  const packetPhase = (start: number) => ((frame - start) % 60) / 60;
  const counters = [
    { label: "Each hospital alone", value: 0, at: 300, color: C.muted },
    { label: "First-come matching", value: 3, at: 380, color: C.amber },
    { label: "KidneyGrid", value: 5, at: 480, color: C.green },
  ];
  const curve = (a: { x: number; y: number }, b: { x: number; y: number }) => {
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const cx = mx + (HUB.x - mx) * 0.3, cy = my + (HUB.y - my) * 0.3;
    return `M${a.x},${a.y} Q${cx},${cy} ${b.x},${b.y}`;
  };
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <svg width={1920} height={1080} style={{ position: "absolute", opacity: fade(frame, 0, SCENES.grid, 15) }}>
        {pos.map((p, i) => <line key={i} x1={HUB.x} y1={HUB.y} x2={p.x} y2={p.y} stroke={C.line} strokeWidth={3} />)}
        {frame > 40 && frame < 300 && pos.map((p, i) => {
          const t = packetPhase(40 + i * 8);
          const out = Math.floor((frame - 40) / 60) % 2 === 0;
          const [f, to] = out ? [HUB, p] : [p, HUB];
          return <circle key={i} cx={f.x + (to.x - f.x) * t} cy={f.y + (to.y - f.y) * t} r={10} fill={out ? C.plum : C.green} />;
        })}
        {loops.map(([a, b], i) => {
          const start = 500 + i * 20;
          const len = 900;
          const off = interpolate(frame, [start, start + 40], [len, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return <path key={i} d={curve(pos[a], pos[b])} fill="none" stroke={C.green} strokeWidth={10} strokeLinecap="round" strokeDasharray={len} strokeDashoffset={off} />;
        })}
        {pos.map((p, i) => (
          <g key={HOSPITALS[i]}>
            <circle cx={p.x} cy={p.y} r={84} fill="#fff" stroke={frame > 520 ? C.green : C.line} strokeWidth={5} />
            {HOSPITALS[i].split(" ").map((w, j) => (
              <text key={w} x={p.x} y={p.y - 14 + j * 26} textAnchor="middle" fontSize={22} fontWeight={700} fill={C.ink} fontFamily={fontFamily}>{w}</text>
            ))}
            <text x={p.x} y={p.y + 44} textAnchor="middle" fontSize={19} fill={C.muted} fontFamily={fontFamily}>{CITIES[i]}</text>
          </g>
        ))}
        <circle cx={HUB.x} cy={HUB.y} r={80} fill={C.plum} />
        <text x={HUB.x} y={HUB.y + 8} textAnchor="middle" fontSize={24} fontWeight={700} fill="#fff" fontFamily={fontFamily}>Coordinator</text>
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 820, display: "flex", justifyContent: "center", gap: 28 }}>
        {counters.map((c) => {
          const s = spring({ frame: frame - c.at, fps: FPS, config: { damping: 14 } });
          return (
            <div key={c.label} style={{ width: 360, background: c.value === 5 ? C.mint : "#f2ecf0", borderRadius: 28, padding: "18px 0", textAlign: "center",
              opacity: Math.min(1, s * 1.5), transform: `scale(${0.8 + 0.2 * s})` }}>
              <div style={{ fontSize: 84, fontWeight: 700, color: c.color, lineHeight: 1 }}>{c.value}</div>
              <div style={{ fontSize: 26, color: C.muted, marginTop: 6 }}>{c.label}</div>
            </div>
          );
        })}
      </div>
      <Caption text="An agent in every hospital. Only anonymous yes/no answers leave." from={20} dur={270} size={48} top={36} />
      <Caption text="Zero matches alone. Five together." from={560} dur={220} size={58} top={36} color={C.green} />
    </AbsoluteFill>
  );
};

const Close: React.FC<{ short?: boolean }> = ({ short }) => {
  const frame = useCurrentFrame();
  const card = spring({ frame: frame - 10, fps: FPS, config: { damping: 13 } });
  if (short) {
    return (
      <AbsoluteFill style={{ background: C.paper, justifyContent: "center", alignItems: "center" }}>
        <div style={{ fontSize: 180, fontWeight: 700, letterSpacing: -7, opacity: fade(frame, 0, OPENER.tag, 10) }}>
          Kidney<span style={{ color: C.pink }}>Grid</span>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <div style={{ position: "absolute", top: 220, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: fade(frame, 0, 200) }}>
        <div style={{ background: "#fff", border: `4px solid ${C.pink}`, borderRadius: 36, padding: "40px 64px", transform: `scale(${0.85 + 0.15 * card})`,
          boxShadow: "0 0 0 12px rgba(236,45,122,0.12)", textAlign: "center" }}>
          <div style={{ fontSize: 88, fontWeight: 700, letterSpacing: -3 }}>Sam → Maria</div>
          <div style={{ fontSize: 36, color: C.muted, marginTop: 8 }}>7 years waiting · Matched</div>
        </div>
      </div>
      <Caption text="No patient record left any hospital." from={200} dur={120} top={480} />
      <Caption text="Five families. Built on Flower." from={320} dur={160} top={400} color={C.plum} />
      <div style={{ position: "absolute", top: 560, left: 0, right: 0, textAlign: "center", fontSize: 150, fontWeight: 700, letterSpacing: -6, opacity: fade(frame, 330, 150) }}>
        Kidney<span style={{ color: C.pink }}>Grid</span>
      </div>
      <div style={{ position: "absolute", bottom: 48, left: 0, right: 0, textAlign: "center", fontSize: 22, color: C.muted, opacity: fade(frame, 330, 150) }}>
        People shown are fictional; data simulated. Sources: OPTN via organdonor.gov (July 2026); Segev et al., JAMA 2005.
      </div>
    </AbsoluteFill>
  );
};


const SPONSORS = [
  { name: "Flower Labs", what: "Flower Agent, SuperGrid, Flower Hub and Endeavor 1.0 power every agent." },
  { name: "Nebius", what: "Capitol Hospital's SuperNode runs on Nebius Serverless AI (NVIDIA L40S)." },
  { name: "Arm", what: "Five SuperNodes run on an Arm-based Apple M1 Pro laptop." },
  { name: "AMD", what: "Thank you for supporting the builders at this hackathon." },
];

const Thanks: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.paper, padding: "110px 160px", opacity: fade(frame, 0, SCENES.thanks, 15) }}>
      <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: 3, textTransform: "uppercase", color: C.pink }}>Thank you</div>
      <div style={{ fontSize: 76, fontWeight: 700, letterSpacing: -2.5, marginTop: 12 }}>Built with the help of our sponsors</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, marginTop: 56 }}>
        {SPONSORS.map((sp, i) => {
          const s = spring({ frame: frame - 20 - i * 12, fps: FPS, config: { damping: 15 } });
          return (
            <div key={sp.name} style={{ background: i === 0 ? "#efe4f2" : "#ffffff", border: `2px solid ${C.line}`, borderRadius: 28,
              padding: "30px 36px", opacity: Math.min(1, s * 1.4), transform: `translateY(${(1 - s) * 24}px)` }}>
              <div style={{ fontSize: 44, fontWeight: 700, color: C.plum }}>{sp.name}</div>
              <div style={{ fontSize: 28, color: C.muted, marginTop: 8, lineHeight: 1.35 }}>{sp.what}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 64, left: 160, fontSize: 24, color: C.muted, opacity: fade(frame, 60, SCENES.thanks - 60) }}>
        Flower Collaborative Agent Hackathon · Stanford · September 29, 2026
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ film

export const Film: React.FC<FilmProps> = ({ voiceover, music, demoFootage, opener }) => {
  const { durationInFrames } = useVideoConfig();
  let t = 0;
  const at = (d: number) => { const s = t; t += d; return s; };
  const seq = opener
    ? [
        <Sequence key="s" from={at(OPENER.stakes)} durationInFrames={OPENER.stakes}><Stakes /></Sequence>,
        <Sequence key="m" from={at(OPENER.maria)} durationInFrames={OPENER.maria}><Maria /></Sequence>,
        <Sequence key="i" from={at(OPENER.islands)} durationInFrames={OPENER.islands}><Islands dur={OPENER.islands} /></Sequence>,
        <Sequence key="t" from={at(OPENER.tag)} durationInFrames={OPENER.tag}><Close short /></Sequence>,
      ]
    : [
        <Sequence key="s" from={at(SCENES.stakes)} durationInFrames={SCENES.stakes}><Stakes /></Sequence>,
        <Sequence key="m" from={at(SCENES.maria)} durationInFrames={SCENES.maria}><Maria /></Sequence>,
        <Sequence key="i" from={at(SCENES.islands)} durationInFrames={SCENES.islands}><Islands dur={SCENES.islands} /></Sequence>,
        <Sequence key="g" from={at(SCENES.grid)} durationInFrames={SCENES.grid}>
          {demoFootage ? <OffthreadVideo src={staticFile("demo.mp4")} muted /> : <GridScene />}
        </Sequence>,
        <Sequence key="c" from={at(SCENES.close)} durationInFrames={SCENES.close}><Close /></Sequence>,
        <Sequence key="t" from={at(SCENES.thanks)} durationInFrames={SCENES.thanks}><Thanks /></Sequence>,
      ];
  return (
    <AbsoluteFill style={{ fontFamily, background: C.paper }}>
      {seq}
      {voiceover && <Audio src={staticFile("voiceover.mp3")} />}
      {music && (
        <Audio src={staticFile("music.mp3")} volume={(f) => interpolate(f, [0, 30, durationInFrames - 60, durationInFrames], [0, 0.22, 0.22, 0], { extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
