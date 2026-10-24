// Client-side checks that mirror the API's validation, so mistakes show before a round trip.

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@.]{2,}$/;
const PHONE = /^\+?[0-9][0-9 ()-]*[0-9]$/;
const squash = (value) => value.trim().replace(/\s+/g, " ");

export const checkEmail = (value) =>
  !value.trim() ? "Enter your email." : EMAIL.test(value.trim()) ? null : "Enter a valid email address.";

export function checkPassword(value) {
  if (value.length < 8) return "Password must be at least 8 characters.";
  if (new TextEncoder().encode(value).length > 72) return "Password must be at most 72 bytes.";
  if (!/[A-Za-z]/.test(value) || !/[0-9]/.test(value)) return "Password must contain a letter and a number.";
  return null;
}

export function checkName(value) {
  const name = squash(value);
  if (name.length < 2) return "Enter your name (at least 2 characters).";
  return name.length > 80 ? "Name must be at most 80 characters." : null;
}

export function checkPhone(value, { required = false } = {}) {
  const phone = squash(value);
  if (!phone) return required ? "Enter a phone number." : null;
  const digits = phone.replace(/\D/g, "").length;
  return PHONE.test(phone) && digits >= 7 && digits <= 15 && phone.length <= 20 ? null : "Enter a valid phone number (7 to 15 digits).";
}

export function checkLength(value, { min = 0, max, label }) {
  const text = squash(value);
  if (text.length < min) return `Enter the ${label.toLowerCase()} (at least ${min} characters).`;
  return max && text.length > max ? `${label} must be at most ${max} characters.` : null;
}

// aria props for an input inside <Field>: links the hint or error and flags invalid values.
export const describe = (id, error, hint) => ({
  id,
  "aria-invalid": error ? true : undefined,
  "aria-describedby": error ? `${id}-error` : hint ? `${id}-hint` : undefined,
});

// { field: message | null } -> only the fields with a message.
export const onlyErrors = (errors) => Object.fromEntries(Object.entries(errors).filter(([, message]) => message));
export { squash };
