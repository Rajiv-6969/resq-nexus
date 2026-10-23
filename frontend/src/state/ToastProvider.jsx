import { useCallback, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ToastContext } from "./contexts";
import { CloseIcon } from "../components/icons";

const HARD = [0.7, 0, 0.2, 1];

function Toaster({ toasts, onDismiss }) {
  return (
    <div className="toaster" role="region" aria-label="Notifications">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          return (
            <motion.div
              key={toast.id}
              layout
              className={`toast toast--${toast.type}`}
              role={toast.type === "error" ? "alert" : "status"}
              initial={{ opacity: 0, x: 64 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 64, transition: { duration: 0.12, ease: HARD } }}
              transition={{ duration: 0.22, ease: HARD }}
            >
              <span className="toast-mark" aria-hidden="true" />
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
