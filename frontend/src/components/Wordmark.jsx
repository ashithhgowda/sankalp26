export const Wordmark = ({ className = "", testid = "wordmark" }) => (
  <span data-testid={testid} className={`font-wordmark font-black leading-none tracking-[-0.02em] ${className}`}>
    <span className="wm-sankalp">SANKALP</span>
    <span className="wm-26">'26</span>
  </span>
);

export const LogoBars = ({ className = "" }) => (
  <div className={`flex items-center gap-1.5 ${className}`}>
    <span className="h-[5px] w-10 -skew-x-[30deg] bg-ice shadow-[0_0_12px_#00c8ff]" />
    <span className="h-[5px] w-16 -skew-x-[30deg] bg-neon shadow-[0_0_12px_#ff2d95]" />
    <span className="ml-1 h-px flex-1 bg-gradient-to-r from-white/50 to-transparent" />
  </div>
);
