import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { Wordmark } from "@/components/Wordmark";
import { useAuth, homeFor } from "@/context/AuthContext";

const LINKS = [
  ["Story", "#story"],
  ["Challenges", "#tracks"],
  ["Timeline", "#timeline"],
  ["Prizes", "#prizes"],
  ["Team", "#team"],
  ["FAQ", "#faq"],
];

export default function Navbar() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close mobile menu on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    document.addEventListener("touchstart", handler);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("touchstart", handler);
    };
  }, [open]);

  // Close mobile menu when route changes (hash links)
  const close = () => setOpen(false);

  return (
    <header
      className="fixed inset-x-0 top-0 z-50 px-4 pt-4 sm:px-6"
      data-testid="main-navbar"
      ref={menuRef}
    >
      <nav
        className={`mx-auto flex max-w-7xl items-center justify-between rounded-full px-5 py-3 transition-[background-color,box-shadow] duration-500 sm:px-7 ${
          scrolled ? "glass-strong" : "bg-transparent"
        }`}
      >
        {/* Logo */}
        <Link to="/" onClick={close} data-testid="nav-logo-link">
          <Wordmark className="text-lg sm:text-xl" testid="nav-wordmark" />
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-7 lg:flex">
          {LINKS.map(([l, h]) => (
            <a
              key={l}
              href={h}
              data-testid={`nav-link-${l.toLowerCase()}`}
              className="font-mono text-[11px] uppercase tracking-[0.25em] text-white/60 transition-colors hover:text-white"
            >
              {l}
            </a>
          ))}
          <Link
            to="/arena"
            data-testid="nav-link-arena"
            className="rounded-full border border-neon/50 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.25em] text-neon shadow-[0_0_18px_-6px_#ff2d95] transition-colors hover:bg-neon/10"
          >
            Arena
          </Link>
          <Link
            to="/leaderboard"
            data-testid="nav-link-leaderboard"
            className="font-mono text-[11px] uppercase tracking-[0.25em] text-ice/80 transition-colors hover:text-ice"
          >
            Leaderboard
          </Link>
        </div>

        {/* Right-side CTAs */}
        <div className="flex items-center gap-2 sm:gap-3">
          {user ? (
            <Link
              to={homeFor(user.role)}
              data-testid="nav-dashboard-button"
              className="btn-ghost !px-4 !py-2 !text-xs sm:!px-5 sm:!py-2.5"
            >
              Dashboard <ArrowUpRight size={14} />
            </Link>
          ) : (
            <>
              <Link
                to="/auth?mode=login"
                data-testid="nav-login-button"
                className="hidden font-mono text-[11px] uppercase tracking-[0.25em] text-white/70 hover:text-white sm:inline"
              >
                Login
              </Link>
              <Link
                to="/auth?mode=register"
                data-testid="nav-register-button"
                className="btn-neon !px-4 !py-2 !text-[11px] sm:!px-5 sm:!py-2.5 sm:!text-xs"
              >
                Register
              </Link>
            </>
          )}

          {/* Hamburger */}
          <button
            className="flex h-9 w-9 items-center justify-center rounded-full text-white transition-colors hover:bg-white/10 lg:hidden"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            data-testid="nav-mobile-toggle"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>

      {/* Mobile drawer */}
      {open && (
        <div
          className="glass-strong mx-auto mt-2 max-w-7xl rounded-3xl p-5 lg:hidden"
          data-testid="nav-mobile-menu"
        >
          <nav className="flex flex-col">
            {LINKS.map(([l, h]) => (
              <a
                key={l}
                href={h}
                onClick={close}
                data-testid={`nav-mobile-link-${l.toLowerCase()}`}
                className="border-b border-white/[0.06] py-3.5 font-display text-base uppercase tracking-[0.2em] text-white/80 transition-colors hover:text-white active:text-neon"
              >
                {l}
              </a>
            ))}
            <a
              href="/arena"
              onClick={close}
              data-testid="nav-mobile-link-arena"
              className="border-b border-white/[0.06] py-3.5 font-display text-base uppercase tracking-[0.2em] text-neon/90"
            >
              Arena
            </a>
            <a
              href="/leaderboard"
              onClick={close}
              data-testid="nav-mobile-link-leaderboard"
              className="border-b border-white/[0.06] py-3.5 font-display text-base uppercase tracking-[0.2em] text-ice/80"
            >
              Leaderboard
            </a>

            {/* Auth CTAs in drawer */}
            <div className="mt-5 flex flex-col gap-3">
              {user ? (
                <Link
                  to={homeFor(user.role)}
                  onClick={close}
                  className="btn-ghost w-full text-center"
                >
                  Dashboard <ArrowUpRight size={14} />
                </Link>
              ) : (
                <>
                  <Link
                    to="/auth?mode=register"
                    onClick={close}
                    className="btn-neon w-full text-center"
                  >
                    Register team
                  </Link>
                  <Link
                    to="/auth?mode=login"
                    onClick={close}
                    className="btn-ghost w-full text-center"
                  >
                    Login
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
