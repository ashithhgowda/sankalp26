import { motion } from "framer-motion";

export const Reveal = ({ children, delay = 0, y = 28, className = "" }) => (
  <motion.div
    className={className}
    initial={{ opacity: 0, y, filter: "blur(8px)" }}
    whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
    viewport={{ once: true, margin: "-80px" }}
    transition={{ duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] }}
  >
    {children}
  </motion.div>
);

export const SectionHead = ({ eyebrow, title, accent, sub, testid }) => (
  <Reveal className="mb-14 max-w-3xl">
    <p className="eyebrow mb-5">{eyebrow}</p>
    <h2 data-testid={testid} className="font-editorial text-3xl font-extrabold uppercase leading-[1.05] tracking-tight text-white sm:text-4xl lg:text-5xl">
      {title} <span className="text-grad">{accent}</span>
    </h2>
    {sub && <p className="mt-5 max-w-xl text-base text-white/60 md:text-lg">{sub}</p>}
  </Reveal>
);
