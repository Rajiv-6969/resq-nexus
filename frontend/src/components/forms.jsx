// Form building blocks in the site's style: labelled fields, chip choices and an error block.

export function Field({ id, label, optional, hint, error, children, className = "" }) {
  return (
    <div className={`field ${className}`.trim()}>
      <label htmlFor={id} className="field-label">
        <span>{label}</span>
        {optional && <span className="field-optional">Optional</span>}
      </label>
      {children}
      {error ? (
        <p className="field-error" id={`${id}-error`}>
          {error}
        </p>
      ) : (
        hint && (
          <p className="field-hint" id={`${id}-hint`}>
            {hint}
          </p>
        )
      )}
    </div>
  );
}

// A group of chips: single choice (radio buttons) or multiple choice (toggle buttons).
export function ChoiceChips({ label, options, value, onChange, multiple = false, error, id, size }) {
  const toggle = (option) => {
    if (!multiple) return onChange(option);
    return onChange(value.includes(option) ? value.filter((v) => v !== option) : [...value, option]);
  };
  return (
    <fieldset className="field field--group" aria-describedby={error ? `${id}-error` : undefined}>
      <legend className="field-label">
        <span>{label}</span>
        {multiple && <span className="field-optional">Choose any</span>}
      </legend>
      <div className={`chips${size === "lg" ? " chips--lg" : ""}`} role={multiple ? "group" : "radiogroup"} aria-label={label}>
        {options.map((option) => {
          const on = multiple ? value.includes(option.value) : value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              className={`chip${on ? " is-on" : ""}`}
              {...(multiple ? { "aria-pressed": on } : { role: "radio", "aria-checked": on })}
              onClick={() => toggle(option.value)}
            >
              {option.icon}
              {option.label}
            </button>
          );
        })}
      </div>
      {error && (
        <p className="field-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </fieldset>
  );
}

export function FormError({ message }) {
  if (!message) return null;
  return (
    <p className="form-error" role="alert">
      <span className="form-error-mark" aria-hidden="true" />
      {message}
    </p>
  );
}
