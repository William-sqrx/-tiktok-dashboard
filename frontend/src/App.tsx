import { useEffect, useState } from "react";
import { Account, Snapshot, Video, api, fmt } from "./api";
import { AccountCard } from "./components/AccountCard";
import { FollowerChart } from "./components/FollowerChart";
import { VideoGrid } from "./components/VideoGrid";
import { Schedule } from "./components/Schedule";

type Tab = "dashboard" | "schedule";

export default function App() {
  const [tab, setTab] = useState<Tab>("schedule");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [busy, setBusy] = useState(false);
  const [configured, setConfigured] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadAccounts() {
    const list = await api.listAccounts();
    setAccounts(list);
    if (selectedId === null && list.length > 0) setSelectedId(list[0].id);
  }

  useEffect(() => {
    loadAccounts();
    api.health().then((h) => setConfigured(h.tiktok_configured));
    // Surface the result of the OAuth redirect (?connected=1 / ?error=...).
    const params = new URLSearchParams(window.location.search);
    if (params.get("error")) setError(params.get("error"));
    if (params.get("connected") || params.get("error")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (selectedId === null) return;
    api.videos(selectedId).then(setVideos);
    api.history(selectedId).then(setHistory);
  }, [selectedId]);

  async function connect() {
    try {
      const { authorize_url } = await api.connectUrl();
      window.location.href = authorize_url;
    } catch (e) {
      setError(String(e));
    }
  }

  async function syncAll() {
    setBusy(true);
    try {
      await api.syncAll();
      await loadAccounts();
      if (selectedId !== null) {
        setVideos(await api.videos(selectedId));
        setHistory(await api.history(selectedId));
      }
    } finally {
      setBusy(false);
    }
  }

  const selected = accounts.find((a) => a.id === selectedId) ?? null;

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
            className={tab === "dashboard" ? "on" : ""}
            onClick={() => setTab("dashboard")}
          >
            Analytics
          </button>
        </nav>
        <div className="spacer" />
        {tab === "dashboard" && (
          <div className="actions">
            <button onClick={connect}>+ Connect account</button>
            <button onClick={syncAll} disabled={busy}>
              {busy ? "Syncing…" : "Sync all"}
            </button>
          </div>
        )}
      </header>

      {tab === "schedule" && <Schedule />}

      {tab === "dashboard" && !configured && (
        <div className="banner warn">
          ⚠️ TikTok app credentials aren't set on the server yet. Add your{" "}
          <code>TIKTOK_CLIENT_KEY</code> and <code>TIKTOK_CLIENT_SECRET</code>{" "}
          (see the README), then reload. Connecting won't work until then.
        </div>
      )}
      {tab === "dashboard" && error && (
        <div className="banner error" onClick={() => setError(null)}>
          Something went wrong: {error} (click to dismiss)
        </div>
      )}

      {tab === "dashboard" &&
        (accounts.length === 0 ? (
        <div className="empty">
          <p>No accounts connected yet.</p>
          <p className="hint">
            Click <strong>Connect account</strong> and log in with TikTok.
            Repeat for each of your 5 accounts.
          </p>
        </div>
      ) : (
        <div className="layout">
          <aside>
            {accounts.map((a) => (
              <AccountCard
                key={a.id}
                account={a}
                selected={a.id === selectedId}
                onSelect={() => setSelectedId(a.id)}
              />
            ))}
          </aside>

          <main>
            {selected && (
              <>
                <div className="kpi-row">
                  <Kpi label="Followers" value={fmt(selected.follower_count)} />
                  <Kpi label="Total likes" value={fmt(selected.likes_count)} />
                  <Kpi label="Videos" value={fmt(selected.video_count)} />
                  <Kpi
                    label="Following"
                    value={fmt(selected.following_count)}
                  />
                </div>

                <section>
                  <h2>Follower trend</h2>
                  <FollowerChart data={history} />
                </section>

                <section>
                  <h2>Videos</h2>
                  <VideoGrid videos={videos} />
                </section>
              </>
            )}
          </main>
        </div>
        ))}
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
