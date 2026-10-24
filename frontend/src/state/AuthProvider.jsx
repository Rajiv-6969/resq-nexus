import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { fetchMe, postLogin, postRegister, postRegisterProvider, setAuthToken, setUnauthorizedHandler } from "../api";
import { AuthContext } from "./contexts";

const STORAGE_KEY = "resq.session";

// { token, user, expiresAt } from localStorage, or null when missing, broken or expired.
function readSession() {
  try {
    const session = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "null");
    if (!session?.token || !session?.user) return null;
    if (session.expiresAt && session.expiresAt <= Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

function writeSession(session) {
  try {
    if (session) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // private mode: the session lasts until the tab closes
  }
}

export default function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [session, setSession] = useState(() => {
    const stored = readSession();
    setAuthToken(stored?.token ?? null);
    return stored;
  });
  // "checking" while a stored session is confirmed with the API (the account may have been deactivated).
  const [status, setStatus] = useState(() => (session ? "checking" : "ready"));
  const sessionRef = useRef(session);

  const save = useCallback((next) => {
    sessionRef.current = next;
    setAuthToken(next?.token ?? null);
    writeSession(next);
    setSession(next);
  }, []);

  const logout = useCallback(
    (message) => {
      save(null);
      navigate("/login", { replace: true, state: message ? { message } : undefined });
    },
    [save, navigate],
  );

  // An API call that comes back 401 (expired or revoked session) logs the user out with the reason.
  useEffect(() => {
    setUnauthorizedHandler((message) => logout(message || "Your session has ended. Log in again."));
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  useEffect(() => {
    if (status !== "checking") return undefined;
    const controller = new AbortController();
    // A stored session that no longer works is dropped quietly; protected pages then ask for a login.
    fetchMe({ signal: controller.signal, notifyUnauthorized: false })
      .then((user) => {
        if (sessionRef.current) save({ ...sessionRef.current, user });
        setStatus("ready");
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        if (err.status === 401) save(null);
        setStatus("ready"); // offline: keep the stored session; requests will say the API is unreachable
      });
    return () => controller.abort();
  }, [status, save]);

  const start = useCallback(
    (data) => {
      save({ token: data.access_token, user: data.user, expiresAt: Date.now() + data.expires_in * 1000 });
      setStatus("ready");
      return data.user;
    },
    [save],
  );

  const login = useCallback(async (email, password) => start(await postLogin(email, password)), [start]);
  const register = useCallback(async (body) => start(await postRegister(body)), [start]);
  const registerProvider = useCallback(
    async (body) => {
      const data = await postRegisterProvider(body);
      start(data);
      return data;
    },
    [start],
  );
  const refreshUser = useCallback(async () => {
    const user = await fetchMe();
    if (sessionRef.current) save({ ...sessionRef.current, user });
    return user;
  }, [save]);

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      ready: status === "ready",
      login,
      register,
      registerProvider,
      logout,
      refreshUser,
    }),
    [session, status, login, register, registerProvider, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
