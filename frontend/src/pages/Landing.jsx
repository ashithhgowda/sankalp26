import { useCallback, useState } from "react";
import IntroReveal from "@/components/IntroReveal";
import Navbar from "@/components/Navbar";
import Hero from "@/components/landing/Hero";
import Story from "@/components/landing/Story";
import Tracks from "@/components/landing/Tracks";
import Timeline from "@/components/landing/Timeline";
import Prizes from "@/components/landing/Prizes";
import Organizers from "@/components/landing/Organizers";
import ArenaTeaser from "@/components/landing/ArenaTeaser";
import Faq from "@/components/landing/Faq";
import Footer from "@/components/landing/Footer";

export default function Landing() {
  const [intro, setIntro] = useState(() => !sessionStorage.getItem("sk_intro"));
  const done = useCallback(() => { sessionStorage.setItem("sk_intro", "1"); setIntro(false); }, []);

  return (
    <div className="grain relative bg-jet" data-testid="landing-page">
      {intro && <IntroReveal onDone={done} />}
      <Navbar />
      <Hero ready={!intro} />
      <Story />
      <Tracks />
      <Timeline />
      <Prizes />
      <ArenaTeaser />
      <Organizers />
      <Faq />
      <Footer />
    </div>
  );
}
