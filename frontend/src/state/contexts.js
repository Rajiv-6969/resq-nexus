import { createContext, useContext } from "react";

// App-wide data: scenarios, priority weights, the latest allocation per scenario and the pipeline state.
export const AppDataContext = createContext(null);

export function useAppData() {
  const value = useContext(AppDataContext);
  if (!value) throw new Error("useAppData must be used inside <AppDataProvider>");
  return value;
}

// Toast notifications.
export const ToastContext = createContext(null);

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used inside <ToastProvider>");
  return value;
}
