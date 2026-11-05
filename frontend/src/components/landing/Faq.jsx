import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { FAQS } from "@/data/content";
import { SectionHead, Reveal } from "@/components/Reveal";

export default function Faq() {
  return (
    <section id="faq" className="relative py-28" data-testid="faq-section">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-10 px-6 sm:px-10 lg:grid-cols-[1fr_1.4fr]">
        <SectionHead eyebrow="Questions" title="Everything you" accent="need to know." testid="faq-heading"
          sub="Still curious? Write to hackathon@ajiet.edu.in" />
        <Reveal>
          <Accordion type="single" collapsible className="space-y-3">
            {FAQS.map(([q, a], i) => (
              <AccordionItem key={q} value={`f${i}`} className="glass rounded-2xl border-0 px-6" data-testid={`faq-item-${i}`}>
                <AccordionTrigger data-testid={`faq-trigger-${i}`} className="py-5 text-left font-display text-lg font-bold uppercase tracking-wide text-white hover:no-underline">{q}</AccordionTrigger>
                <AccordionContent className="pb-5 text-sm leading-relaxed text-white/60">{a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </Reveal>
      </div>
    </section>
  );
}
