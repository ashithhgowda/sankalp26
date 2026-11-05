import { useMemo } from "react";
import { CalendarDays, X } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { buildISTValue, getISTParts } from "./istDateTime";

export function DateTimeISTField({ value, onChange, testId, includeTime = true, placeholder = "Choose date" }) {
  const current = useMemo(() => getISTParts(value), [value]);
  const selected = current ? new Date(Number(current.year), Number(current.month) - 1, Number(current.day)) : undefined;
  const choose = (date, time = current ? `${current.hour}:${current.minute}` : "12:00") => {
    if (!date) return onChange("");
    if (includeTime && !time) return onChange("");
    const next = buildISTValue(date, time, includeTime);
    if (next) onChange(next);
  };
  const label = current ? `${current.day}/${current.month}/${current.year}${includeTime ? ` · ${current.hour}:${current.minute} IST` : ""}` : placeholder;
  return <div className="space-y-2"><Popover><PopoverTrigger asChild><button type="button" className="field flex items-center justify-between text-left" data-testid={testId}><span className={current ? "text-white" : "text-white/35"}>{label}</span><CalendarDays size={16} className="text-ice" /></button></PopoverTrigger><PopoverContent className="border-white/15 bg-[#101216] text-white" align="start"><Calendar mode="single" selected={selected} onSelect={(date) => choose(date)} initialFocus />{includeTime && <label className="mt-3 block"><span className="field-label">Time · IST</span><input type="time" className="field" value={current ? `${current.hour}:${current.minute}` : "12:00"} onChange={(event) => choose(selected || new Date(), event.target.value)} data-testid={`${testId}-time`} /></label>}</PopoverContent></Popover>{value && <button type="button" onClick={() => onChange("")} className="flex items-center gap-1 text-xs text-white/40 hover:text-neon" data-testid={`${testId}-clear`}><X size={12} /> Clear</button>}</div>;
}