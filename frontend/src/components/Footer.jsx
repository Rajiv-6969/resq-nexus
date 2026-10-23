import { Link } from "react-router";
import { AsteriskMark } from "./icons";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-top">
        <p className="footer-brand">
          <AsteriskMark size={30} />
          <span>
            ResQ
            <br />
            Nexus
          </span>
        </p>
        <p className="footer-col">
          <span className="label">01 / System</span>
          Decision support for disaster relief: who needs help first, what to send, and why.
        </p>
        <p className="footer-col">
          <span className="label">02 / Data</span>
          Synthetic demo scenarios placed at real OpenStreetMap locations in India.
        </p>
        <p className="footer-col">
          <span className="label">03 / Map</span>
          Map data and tiles &copy; OpenStreetMap contributors, shown in grayscale.
        </p>
        <p className="footer-col">
          <span className="label">04 / Photos</span>
          Wikimedia Commons and Unsplash, credited on the <Link to="/about">About</Link> page.
        </p>
      </div>
      <p className="footer-bottom mono">
        <span>&copy; {new Date().getFullYear()} ResQ Nexus</span>
        <span>Synthetic data. Not for operational use.</span>
      </p>
    </footer>
  );
}
