import { loadFont } from "@remotion/google-fonts/Archivo";
import { AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame, Easing } from "remotion";
import boxes from "../public/shots/boxes.json";

const { fontFamily } = loadFont("normal", { weights: ["400", "600", "800"], subsets: ["latin"] });

export const FPS = 30;
export const DURATION = 19.5 * FPS;

const C = {
  buckram: "#17352b",
  buckramDeep: "#10261f",
  buckramInk: "#d9e4dc",
  gold: "#d4b04c",
  paper: "#f6f7f4",
};

type Box = { x: number; y: number; width: number; height: number };
type Point = [number, number];
const B = boxes as unknown as Record<string, Box> & Record<string, number>;
const center = (b: Box): Point => [b.x + b.width / 2, b.y + b.height / 2];
const ease = Easing.bezier(0.16, 1, 0.3, 1);

// Timeline, in frames.
const T = {
  titleEnd: 45,
  a: { start: 45, typeStart: 62, typeEnd: 100, click: 112, answer: 140, zoomAnswer: 165, zoomShelf: 225, end: 300 },
  b: { start: 300, typeStart: 318, typeEnd: 345, click: 355, answer: 383, zoom: 403, end: 495 },
};

/** Keyframed value: [[frame, value], ...] with eased interpolation between them. */
function track(frame: number, keys: Array<[number, number]>) {
  return interpolate(frame, keys.map((k) => k[0]), keys.map((k) => k[1]), {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

function Shot({ name }: { name: string }) {
  return <Img src={staticFile(`shots/${name}.png`)} style={{ width: 1440, height: 900, position: "absolute" }} />;
}

function Cursor({ at, clickAt }: { at: Point; clickAt: number[] }) {
  const frame = useCurrentFrame();
  // Scenes are not wrapped in a Sequence, so this is the absolute frame.
  const press = Math.max(0, ...clickAt.map((c) => 1 - Math.abs(frame - c) / 5));
  return (
    <svg
      width={28}
      height={28}
      viewBox="0 0 24 24"
      style={{ position: "absolute", left: at[0] - 4, top: at[1] - 2, transform: `scale(${1 - press * 0.18})`, transformOrigin: "4px 2px" }}
    >
      <path d="M4 2 L4 19 L8.5 14.8 L11.6 21.5 L14.4 20.3 L11.3 13.7 L17.5 13.7 Z" fill="#111" stroke="#fff" strokeWidth={1.4} strokeLinejoin="round" />
    </svg>
  );
}

/** Zooms the 1440×900 stage so `focus` (in screenshot coordinates) is centred at `scale`. */
function Camera({ scale, focus, children }: { scale: number; focus: Point; children: React.ReactNode }) {
  const tx = Math.min(0, Math.max(1440 - 1440 * scale, 720 - focus[0] * scale));
  const ty = Math.min(0, Math.max(900 - 900 * scale, 450 - focus[1] * scale));
  return (
    <AbsoluteFill style={{ transform: `translate(${tx}px, ${ty}px) scale(${scale})`, transformOrigin: "0 0" }}>
      {children}
    </AbsoluteFill>
  );
}

function Caption({ text, from, to, top = false }: { text: string; from: number; to: number; top?: boolean }) {
  const frame = useCurrentFrame();
  const opacity = track(frame, [[from, 0], [from + 10, 1], [to - 8, 1], [to, 0]]);
  const lift = track(frame, [[from, 16], [from + 14, 0]]);
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        ...(top ? { top: 48 } : { bottom: 48 }),
        transform: `translate(-50%, ${lift}px)`,
        opacity,
        background: C.buckramDeep,
        color: C.paper,
        fontFamily,
        fontSize: 34,
        fontWeight: 600,
        letterSpacing: "-0.01em",
        padding: "16px 28px",
        borderLeft: `6px solid ${C.gold}`,
        boxShadow: "0 18px 40px rgba(16,38,31,0.35)",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
}

function typeFrame(prefix: "a" | "b", frame: number, start: number, end: number) {
  const n = B[`${prefix}-typeFrames`];
  const i = Math.round(interpolate(frame, [start, end], [0, n - 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return `${prefix}-type-${String(i).padStart(2, "0")}`;
}

function SceneAda() {
  const frame = useCurrentFrame();
  const a = T.a;
  const textarea = center(B["a-textarea"]);
  const ask = center(B["a-ask"]);
  const shot =
    frame < a.typeStart ? "a-empty" : frame < a.click ? typeFrame("a", frame, a.typeStart, a.typeEnd) : frame < a.answer ? "a-loading" : "a-answer";

  const cursor: Point = [
    track(frame, [[a.start, 760], [a.typeStart - 2, textarea[0]], [a.typeEnd, textarea[0]], [a.click - 2, ask[0]]]),
    track(frame, [[a.start, 620], [a.typeStart - 2, textarea[1]], [a.typeEnd, textarea[1]], [a.click - 2, ask[1]]]),
  ];
  const answerFocus = center(B["a-answerText"]);
  const shelf = B["a-openSpine"];
  const shelfFocus: Point = [shelf.x + 300, shelf.y + 230];
  const scale = track(frame, [[a.zoomAnswer, 1], [a.zoomAnswer + 30, 1.85], [a.zoomShelf, 1.85], [a.zoomShelf + 30, 1.45]]);
  const fx = track(frame, [[a.zoomAnswer, 720], [a.zoomAnswer + 30, answerFocus[0]], [a.zoomShelf, answerFocus[0]], [a.zoomShelf + 30, shelfFocus[0]]]);
  const fy = track(frame, [[a.zoomAnswer, 450], [a.zoomAnswer + 30, answerFocus[1]], [a.zoomShelf, answerFocus[1]], [a.zoomShelf + 30, shelfFocus[1]]]);
  const cursorOpacity = track(frame, [[a.answer, 1], [a.answer + 10, 0]]);

  return (
    <AbsoluteFill>
      <Camera scale={scale} focus={[fx, fy]}>
        <Shot name={shot} />
        <div style={{ opacity: cursorOpacity }}>
          <Cursor at={cursor} clickAt={[a.click]} />
        </div>
      </Camera>
      <Caption text="Every answer cites the policy it comes from" from={a.zoomAnswer - 5} to={a.end} top />
    </AbsoluteFill>
  );
}

function SceneBasil() {
  const frame = useCurrentFrame();
  const b = T.b;
  const textarea = center(B["b-textarea"]);
  const ask = center(B["b-ask"]);
  const shot =
    frame < b.typeStart
      ? "b-empty"
      : frame < b.click
        ? typeFrame("b", frame, b.typeStart, b.typeEnd)
        : frame < b.answer
          ? "b-loading"
          : "b-answer";

  const cursor: Point = [
    track(frame, [[b.start, 900], [b.typeStart - 2, textarea[0]], [b.typeEnd, textarea[0]], [b.click - 2, ask[0]]]),
    track(frame, [[b.start, 500], [b.typeStart - 2, textarea[1]], [b.typeEnd, textarea[1]], [b.click - 2, ask[1]]]),
  ];
  const answer = center(B["b-answerText"]);
  const focus: Point = [answer[0] - 40, answer[1] + 20];
  const scale = track(frame, [[b.zoom, 1], [b.zoom + 30, 1.9]]);
  const fx = track(frame, [[b.zoom, 720], [b.zoom + 30, focus[0]]]);
  const fy = track(frame, [[b.zoom, 450], [b.zoom + 30, focus[1]]]);
  const cursorOpacity = track(frame, [[b.start, 0], [b.start + 6, 1], [b.answer, 1], [b.answer + 10, 0]]);

  return (
    <AbsoluteFill>
      <Camera scale={scale} focus={[fx, fy]}>
        <Shot name={shot} />
        <div style={{ opacity: cursorOpacity }}>
          <Cursor at={cursor} clickAt={[b.click]} />
        </div>
      </Camera>
      <Caption text="Orders are scoped to the signed-in customer" from={b.start + 10} to={b.end} />
    </AbsoluteFill>
  );
}

function Card({ children, length }: { children: React.ReactNode; length: number }) {
  const frame = useCurrentFrame();
  const opacity = track(frame, [[0, 0], [10, 1], [length - 8, 1], [length, 0]]);
  return (
    <AbsoluteFill style={{ background: C.buckram, color: C.buckramInk, fontFamily, justifyContent: "center", padding: "0 140px", opacity }}>
      {children}
    </AbsoluteFill>
  );
}

function Title() {
  return (
    <Card length={T.titleEnd}>
      <div style={{ color: C.gold, fontSize: 96, fontWeight: 800, letterSpacing: "-0.03em" }}>SupportPilot</div>
      <div style={{ fontSize: 40, marginTop: 12 }}>Grounded answers for Old Pages Books</div>
    </Card>
  );
}

function End() {
  const length = DURATION - T.b.end;
  return (
    <Card length={length}>
      <div style={{ color: C.gold, fontSize: 72, fontWeight: 800, letterSpacing: "-0.03em" }}>SupportPilot</div>
      <div style={{ fontSize: 40, marginTop: 16 }}>github.com/asdrubalivan/supportpilot</div>
      <div style={{ fontSize: 28, marginTop: 28, color: C.gold }}>Evals and metrics in the repo</div>
    </Card>
  );
}

export function Demo() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.buckram }}>
      <Sequence durationInFrames={T.titleEnd}>
        <Title />
      </Sequence>
      {frame >= T.a.start && frame < T.a.end && <SceneAda />}
      {frame >= T.b.start && frame < T.b.end && <SceneBasil />}
      <Sequence from={T.b.end}>
        <End />
      </Sequence>
    </AbsoluteFill>
  );
}
