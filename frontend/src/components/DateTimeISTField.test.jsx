jest.mock("@/components/ui/calendar", () => {
  const React = require("react");
  return {
    Calendar: ({ onSelect }) => React.createElement(
      "button",
      {
        type: "button",
        "data-testid": "calendar-day",
        onClick: (event) => onSelect(new Date(2026, 10, 6), new Date(2026, 10, 6), {}, event),
      },
      "6",
    ),
  };
});

import React, { act, useState } from "react";
import { createRoot } from "react-dom/client";
import { DateTimeISTField } from "./DateTimeISTField";
import { buildISTValue, getISTParts } from "./istDateTime";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("DateTimeISTField date conversion", () => {
  test("invalid and empty values do not throw during formatting", () => {
    expect(getISTParts("")).toBeNull();
    expect(getISTParts("not-a-date")).toBeNull();
  });

  test("formats valid timestamps in Asia/Kolkata", () => {
    expect(getISTParts("2026-11-04T09:15:00+05:30")).toMatchObject({
      year: "2026",
      month: "11",
      day: "04",
      hour: "09",
      minute: "15",
    });
  });

  test("does not serialize a blank time as an invalid timestamp", () => {
    const date = new Date(2026, 10, 4);
    expect(buildISTValue(date, "", true)).toBeNull();
    expect(buildISTValue(date, "09:15", true)).toBe("2026-11-04T09:15:00+05:30");
    expect(buildISTValue(date, "", false)).toBe("2026-11-04");
  });

  test("selects dates, changes times, clears, and restores controlled values", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    function ControlledField({ initialValue }) {
      const [value, setValue] = useState(initialValue);
      return (
        <>
          <DateTimeISTField value={value} onChange={setValue} testId="timeline-date" />
          <output data-testid="timeline-value">{value || ""}</output>
        </>
      );
    }

    try {
      await act(async () => root.render(<ControlledField key="first-load" initialValue="2026-11-04T09:15:00+05:30" />));
      const trigger = container.querySelector('[data-testid="timeline-date"]');
      await act(async () => trigger.click());

      const dateButton = document.querySelector('[data-testid="calendar-day"]');
      await act(async () => dateButton.click());
      expect(container.querySelector('[data-testid="timeline-value"]').textContent).toBe("2026-11-06T09:15:00+05:30");
      expect(trigger.textContent).toContain("06/11/2026");

      const timeInput = document.querySelector('[data-testid="timeline-date-time"]');
      await act(async () => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(timeInput, "14:25");
        timeInput.dispatchEvent(new Event("input", { bubbles: true }));
        timeInput.dispatchEvent(new Event("change", { bubbles: true }));
      });
      expect(container.querySelector('[data-testid="timeline-value"]').textContent).toBe("2026-11-06T14:25:00+05:30");

      await act(async () => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(timeInput, "");
        timeInput.dispatchEvent(new Event("input", { bubbles: true }));
        timeInput.dispatchEvent(new Event("change", { bubbles: true }));
      });
      expect(container.querySelector('[data-testid="timeline-value"]').textContent).toBe("");

      await act(async () => {
        root.render(
          <ControlledField key="reload" initialValue="2026-11-06T14:25:00+05:30" />
        );
      });
      expect(container.querySelector('[data-testid="timeline-date"]').textContent).toContain("06/11/2026 · 14:25 IST");
      await act(async () => container.querySelector('[data-testid="timeline-date-clear"]').click());
      expect(container.querySelector('[data-testid="timeline-value"]').textContent).toBe("");
    } finally {
      await act(async () => root.unmount());
      container.remove();
    }
  });
});