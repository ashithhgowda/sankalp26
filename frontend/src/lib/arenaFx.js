import confetti from "canvas-confetti";

let ctx;
export const isMuted = () => localStorage.getItem("sk_sound") !== "on";
export const setMuted = (m) => localStorage.setItem("sk_sound", m ? "off" : "on");

export function beep(kind = "tick") {
  if (isMuted()) return;
  ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
  const notes = { good: [660, 990], bad: [220, 160], tick: [880], win: [523, 659, 784, 1046] }[kind];
  notes.forEach((f, i) => {
    const t = ctx.currentTime + i * 0.1;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "triangle";
    o.frequency.value = f;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.12, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
    o.connect(g).connect(ctx.destination);
    o.start(t);
    o.stop(t + 0.22);
  });
}

const COLORS = ["#FF2D95", "#00C8FF", "#007BA7", "#ffffff"];
export const burst = (big = false) =>
  confetti({ particleCount: big ? 180 : 70, spread: big ? 110 : 65, startVelocity: big ? 55 : 38, origin: { y: 0.7 }, colors: COLORS, disableForReducedMotion: true });

export const sideCannons = () => {
  confetti({ particleCount: 120, angle: 60, spread: 70, origin: { x: 0, y: 0.8 }, colors: COLORS, disableForReducedMotion: true });
  confetti({ particleCount: 120, angle: 120, spread: 70, origin: { x: 1, y: 0.8 }, colors: COLORS, disableForReducedMotion: true });
};
