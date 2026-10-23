import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "leaflet/dist/leaflet.css";
// Self-hosted Google Fonts: blackletter logo/headings, display subheadings, readable body + numbers.
import "@fontsource/pirata-one/400.css";
import "@fontsource/cinzel/600.css";
import "@fontsource/cinzel/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/rajdhani/500.css";
import "@fontsource/rajdhani/600.css";
import "@fontsource/rajdhani/700.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/landing.css";
import "./styles/command.css";
import "./styles/map.css";
import "./styles/analytics.css";
import "./styles/pages.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
