import { AsteriskMark } from "./icons";

export default function PageLoader({ label = "Loading" }) {
  return (
    <div className="page-loader" role="status">
      <AsteriskMark size={22} className="asterisk loader" />
      {label}
    </div>
  );
}
