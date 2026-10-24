// Resource availability in words, e.g. "12 of 40 beds available".
export const formatCount = (value) => new Intl.NumberFormat("en-IN").format(value);

export const availabilityText = (r) =>
  r.status === "CLOSED"
    ? `Closed / ${formatCount(r.capacity_total)} ${r.unit} when open`
    : `${formatCount(r.capacity_available)} of ${formatCount(r.capacity_total)} ${r.unit} available`;
