import { API_BASE_URL } from "../api";
import { AlertIcon, RefreshIcon } from "./icons";

export default function ErrorBanner({ message, onRetry }) {
  return (
    <div className="error-banner" role="alert">
      <AlertIcon size={20} />
      <div>
        <strong>{message}</strong>
        <p>
          Is the backend running? In another terminal: <code>cd backend</code>, activate the virtual environment, then{" "}
          <code>uvicorn main:app --reload</code>. It should answer at <code>{API_BASE_URL}/health</code>.
        </p>
      </div>
      <button type="button" className="btn btn--sm btn--on-red" onClick={onRetry}>
        <RefreshIcon size={13} /> Retry
      </button>
    </div>
  );
}
