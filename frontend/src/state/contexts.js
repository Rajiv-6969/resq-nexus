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

// The logged-in user and the login / logout actions.
export const AuthContext = createContext(null);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
