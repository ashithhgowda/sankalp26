import { Link } from "react-router-dom";
import { ArrowRight, Mail, MapPin, Phone } from "lucide-react";
import { Wordmark, LogoBars } from "@/components/Wordmark";
import { IMAGES } from "@/data/content";
import { Reveal } from "@/components/Reveal";

export default function Footer() {
  return (
    <footer className="relative pt-10" data-testid="site-footer">
      <div className="mx-auto max-w-7xl px-6 sm:px-10">
        <Reveal>
          <div className="glass glow-border relative overflow-hidden rounded-[2rem] p-10 sm:p-14">
            <img src={IMAGES.eye} alt="" className="absolute inset-0 h-full w-full object-cover opacity-25" />
            <div className="absolute inset-0 bg-gradient-to-r from-jet via-jet/80 to-transparent" />
            <div className="relative max-w-xl">
              <p className="eyebrow mb-5">Ready to build?</p>
              <h2 className="font-editorial text-3xl font-extrabold uppercase leading-tight text-white sm:text-4xl lg:text-5xl">Turn ideas <span className="text-grad">into impact.</span></h2>
              <p className="mt-5 text-white/60">Choose a theme, prepare your one-page abstract, and take the first step toward something meaningful.</p>
              <Link to="/auth?mode=register" className="btn-neon mt-8" data-testid="footer-register-cta">Register now <ArrowRight size={16} /></Link>
            </div>
          </div>
        </Reveal>
        <div className="grid grid-cols-1 gap-10 py-16 md:grid-cols-3">
          <div>
            <Wordmark className="text-3xl" testid="footer-wordmark" />
            <LogoBars className="mt-4 max-w-[220px]" />
            <p className="mt-5 font-display text-sm uppercase text-white/50 spaced">Build. <span className="text-white">Breakthrough.</span> <span className="text-neon">Belong.</span></p>
          </div>
          <div className="space-y-3 text-sm text-white/60">
            <a href="mailto:hackathon@ajiet.edu.in" className="flex items-center gap-3 hover:text-white" data-testid="footer-email"><Mail size={16} className="text-ice" />hackathon@ajiet.edu.in</a>
            <a href="tel:+918197278959" className="flex items-center gap-3 hover:text-white"><Phone size={16} className="text-ice" />Prof. Manjukiran B · +91 8197278959</a>
            <p className="flex items-start gap-3"><MapPin size={16} className="mt-0.5 shrink-0 text-neon" />A.J. Institute of Engineering and Technology, NH-66, Kottara Chowki, Mangaluru</p>
          </div>
          <div className="flex flex-col gap-2 font-mono text-[11px] uppercase tracking-[0.25em] text-white/50 md:items-end">
            <Link to="/leaderboard" className="hover:text-white">Leaderboard</Link>
            <Link to="/auth?mode=login" className="hover:text-white">Team / Judge login</Link>
            <a href="#tracks" className="hover:text-white">Challenges</a>
          </div>
        </div>
        <div className="flex flex-col justify-between gap-2 border-t border-white/10 py-6 font-mono text-[10px] uppercase tracking-[0.25em] text-white/30 sm:flex-row">
          <span>© 2026 IEEE AJIET Student Branch</span><span>3rd edition · National level</span>
        </div>
      </div>
    </footer>
  );
}
