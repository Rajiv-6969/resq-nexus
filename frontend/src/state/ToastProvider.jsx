import { useCallback, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ToastContext } from "./contexts";
import { AlertIcon, CheckIcon, CloseIcon, InfoIcon } from "../components/icons";

const ICONS = { success: CheckIcon, info: InfoIcon, warning: AlertIcon, error: AlertIcon };

function Toaster({ toasts, onDismiss }) {
  return (
    <div className="toaster" role="region" aria-label="Notifications">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const Icon = ICONS[toast.type] ?? InfoIcon;
          return (
            <motion.div
              key={toast.id}
              layout
              className={`toast toast--${toast.type}`}
              role={toast.type === "error" ? "alert" : "status"}
              initial={{ opacity: 0, x: 48, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 48, transition: { duration: 0.2 } }}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            >
              <span className="toast-icon">
                <Icon size={18} />
              </span>
              <div className="toast-body">
                <strong>{toast.title}</strong>
                {toast.message && <p>{toast.message}</p>}
              </div>
              <button type="button" className="toast-close" onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification">
                <CloseIcon size={14} />
              </button>
              <span className="toast-timer" style={{ animationDuration: `${toast.timeout}ms` }} aria-hidden="true" />
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const push = useCallback(
    (type, title, message, timeout = 5200) => {
      nextId.current += 1;
      const id = nextId.current;
      setToasts((list) => [...list.slice(-3), { id, type, title, message, timeout }]);
      window.setTimeout(() => dismiss(id), timeout);
      return id;
    },
    [dismiss],
  );

  const api = useMemo(
    () => ({
      success: (title, message, timeout) => push("success", title, message, timeout),
      info: (title, message, timeout) => push("info", title, message, timeout),
      warning: (title, message, timeout) => push("warning", title, message, timeout),
      error: (title, message, timeout) => push("error", title, message, timeout ?? 8000),
      dismiss,
    }),
    [push, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <Toaster toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}
