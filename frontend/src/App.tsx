import { useState } from "react";
import { Analytics } from "./components/Analytics";
import { Schedule } from "./components/Schedule";

type Tab = "schedule" | "analytics";

export default function App() {
  const [tab, setTab] = useState<Tab>("schedule");

  return (
    <div className="app">
      <header>
        <h1>TikTok Studio</h1>
        <nav className="tabs">
          <button
            className={tab === "schedule" ? "on" : ""}
            onClick={() => setTab("schedule")}
          >
            Schedule
          </button>
          <button
            className={tab === "analytics" ? "on" : ""}
            onClick={() => setTab("analytics")}
          >
            Analytics
          </button>
        </nav>
        <div className="spacer" />
      </header>

      {tab === "schedule" ? <Schedule /> : <Analytics />}
    </div>
  );
}
