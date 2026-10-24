// Dates and times for the trackers and lists (Indian English, the user's own time zone).

const clock = new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
const dayClock = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

const toDate = (value) => (value instanceof Date ? value : new Date(value));
const sameDay = (a, b) => a.toDateString() === b.toDateString();

// "14:05" today, otherwise "23 Oct, 14:05".
export function formatTime(value) {
  if (!value) return "—";
  const date = toDate(value);
  return sameDay(date, new Date()) ? clock.format(date) : dayClock.format(date);
}

// "just now", "4 min ago", "2 hr ago", "yesterday", "3 days ago".
export function timeAgo(value, now = Date.now()) {
  if (!value) return "—";
  const seconds = Math.round((toDate(value).getTime() - now) / 1000);
  const abs = Math.abs(seconds);
  if (abs < 45) return "just now";
  if (abs < 3600) return relative.format(Math.round(seconds / 60), "minute").replace("minutes", "min").replace("minute", "min");
  if (abs < 86400) return relative.format(Math.round(seconds / 3600), "hour").replace("hours", "hr").replace("hour", "hr");
  return relative.format(Math.round(seconds / 86400), "day");
}
