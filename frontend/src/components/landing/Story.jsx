import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { STORY, WHY } from "@/data/content";
import { Reveal } from "@/components/Reveal";
import * as Icons from "lucide-react";
import heroGirlImage from "@/images/heroGirl.jpeg";
import eyeImage from "@/images/eye.jpeg";
import thirdImage from "@/images/thirdImage.png";

const STORY_IMAGES = [heroGirlImage, eyeImage, thirdImage];

// ─── Desktop: scroll-linked sticky chapter ───────────────────────────────────
const DesktopChapter = ({ c, i, progress }) => {
  const start = i / STORY.length;
  const fromLeft = i % 2 === 0;
  const opacity = useTransform(
    progress,
    [start - 0.1, start + 0.08, start + 0.28, start + 0.4],
    [0.15, 1, 1, i === STORY.length - 1 ? 1 : 0.15]
  );
  const x = useTransform(
    progress,
    [start - 0.1, start + 0.08, start + 0.28, start + 0.4],
    [fromLeft ? -40 : 40, 0, 0, fromLeft ? 40 : -40]
  );
  return (
    <motion.div
      style={{ opacity, x }}
      className="flex min-h-[70vh] flex-col justify-center"
      data-testid={`story-chapter-${c.n}`}
    >
      <p className="eyebrow mb-4">Chapter {c.n} // {c.tag}</p>
      <h3 className="font-editorial text-3xl font-extrabold uppercase leading-tight text-white sm:text-4xl lg:text-5xl">
        {c.title}
      </h3>
      <p className="mt-6 max-w-lg text-base leading-relaxed text-white/60 md:text-lg">
        {c.text}
      </p>
    </motion.div>
  );
};

const DesktopChapterImage = ({ src, i, progress, scale, hue }) => {
  const start = i / STORY_IMAGES.length;
  const end = (i + 1) / STORY_IMAGES.length;
  const fromLeft = i % 2 === 0;
  const opacity = useTransform(
    progress,
    [Math.max(0, start - 0.08), start + 0.08, end - 0.08, Math.min(1, end + 0.08)],
    [i === 0 ? 1 : 0, 1, 1, i === STORY_IMAGES.length - 1 ? 1 : 0]
  );
  const x = useTransform(
    progress,
    [Math.max(0, start - 0.08), start + 0.08, end - 0.08, Math.min(1, end + 0.08)],
    [i === 0 ? 0 : fromLeft ? -60 : 60, 0, 0, fromLeft ? 60 : -60]
  );

  return (
    <motion.img
      src={src}
      alt=""
      style={{ opacity, x, scale, filter: hue }}
      className="absolute inset-0 h-full w-full object-cover object-top"
    />
  );
};

// ─── Mobile: alternating entrance animations, no sticky / scroll-link ────────
const MobileChapter = ({ c, i, image }) => {
  const fromLeft = i % 2 === 0;
  return (
    <motion.div
      className="mb-16 last:mb-0"
      data-testid={`story-chapter-mobile-${c.n}`}
      initial={{ opacity: 0, x: fromLeft ? -40 : 40 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Chapter image */}
      <div className="glass glow-border relative mb-5 overflow-hidden rounded-2xl">
        <img
          src={image}
          alt={`Chapter ${c.n} — ${c.tag}`}
          className="h-52 w-full object-cover object-top"
          style={{ filter: `hue-rotate(${i * -8}deg)` }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-jet/80 to-transparent" />
      </div>

      {/* Chapter text */}
      <p className="eyebrow mb-3">Chapter {c.n} // {c.tag}</p>
      <h3 className="font-editorial text-2xl font-extrabold uppercase leading-tight text-white">
        {c.title}
      </h3>
      <p className="mt-4 text-sm leading-relaxed text-white/60">{c.text}</p>
    </motion.div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────
export default function Story() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  const imageScale = useTransform(scrollYProgress, [0, 1], [1.15, 1]);
  const hue = useTransform(
    scrollYProgress,
    [0, 1],
    ["hue-rotate(0deg)", "hue-rotate(-25deg)"]
  );
  const barH = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <section id="story" className="relative" data-testid="story-section">
      {/* ── Desktop layout (lg+): sticky image + scroll-linked text ── */}
      <div
        ref={ref}
        className="relative mx-auto hidden max-w-7xl grid-cols-2 gap-10 px-6 sm:px-10 lg:grid"
      >
        {/* Sticky image panel */}
        <div className="sticky top-0 flex h-screen items-center">
          <div className="glass glow-border relative h-[78vh] w-full overflow-hidden rounded-[2rem]">
            {STORY_IMAGES.map((image, i) => (
              <DesktopChapterImage
                key={image}
                src={image}
                i={i}
                progress={scrollYProgress}
                scale={imageScale}
                hue={hue}
              />
            ))}
            <div className="absolute inset-0 bg-gradient-to-t from-jet via-transparent to-transparent" />
            <div className="scanline" />
            <div className="absolute bottom-6 left-6 right-6 flex items-end justify-between">
              <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/60">
                Muse // संकल्प
                <br />
                <span className="text-neon">Resolve.exe</span>
              </p>
              <div className="h-24 w-px bg-white/10">
                <motion.div
                  style={{ height: barH }}
                  className="w-px bg-gradient-to-b from-ice to-neon"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Scroll-driven chapters */}
        <div className="py-24">
          <Reveal>
            <p className="eyebrow mb-5">The story of the theme</p>
            <h2 className="font-editorial text-3xl font-extrabold uppercase leading-[1.05] text-white sm:text-4xl lg:text-5xl">
              Half human. Half signal.{" "}
              <span className="text-grad">All resolve.</span>
            </h2>
          </Reveal>
          {STORY.map((c, i) => (
            <DesktopChapter key={c.n} c={c} i={i} progress={scrollYProgress} />
          ))}
        </div>
      </div>

      {/* ── Mobile layout (<lg): alternating entrance, no sticky ── */}
      <div className="mx-auto max-w-2xl px-5 py-16 lg:hidden">
        <div className="mb-10">
          <p className="eyebrow mb-4">The story of the theme</p>
          <h2 className="font-editorial text-2xl font-extrabold uppercase leading-tight text-white">
            Half human. Half signal.{" "}
            <span className="text-grad">All resolve.</span>
          </h2>
        </div>
        {STORY.map((c, i) => (
          <MobileChapter key={c.n} c={c} i={i} image={STORY_IMAGES[i]} />
        ))}
      </div>

      {/* ── Stats + WHY cards (shared) ── */}
      <div className="mx-auto max-w-7xl px-6 pb-20 sm:px-10">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[
            ["24", "Hours"],
            ["₹75k", "Prize pool"],
            ["3", "Max members"],
            ["06", "Challenges"],
          ].map(([v, l], i) => (
            <Reveal key={l} delay={i * 0.08}>
              <div
                className="glass rounded-3xl p-5 sm:p-6"
                data-testid={`stat-${l.toLowerCase().replace(/\s/g, "-")}`}
              >
                <p className="font-wordmark text-2xl font-black text-white sm:text-3xl lg:text-4xl">
                  {v}
                </p>
                <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/50">
                  {l}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {WHY.map((w, i) => {
            const Icon = Icons[w.icon];
            return (
              <Reveal key={w.title} delay={i * 0.08}>
                <div className="glass glow-border card-scan h-full rounded-3xl p-6 sm:p-7 transition-transform duration-500 hover:-translate-y-1">
                  <Icon className="text-neon" size={22} />
                  <h3 className="mt-5 font-display text-lg font-bold uppercase tracking-wider text-white sm:mt-6 sm:text-xl">
                    {w.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-white/55">
                    {w.text}
                  </p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
