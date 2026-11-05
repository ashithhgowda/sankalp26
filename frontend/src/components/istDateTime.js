export const getISTParts = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date).map((item) => [item.type, item.value]));
};

export const buildISTValue = (date, time, includeTime = true) => {
  if (!date || Number.isNaN(date.getTime())) return null;
  if (includeTime && !/^([01]\d|2[0-3]):[0-5]\d$/.test(time || "")) return null;
  const day = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const value = includeTime ? `${day}T${time}:00+05:30` : day;
  return Number.isNaN(new Date(value).getTime()) ? null : value;
};