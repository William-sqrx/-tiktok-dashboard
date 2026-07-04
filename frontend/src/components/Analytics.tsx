import { useEffect, useState } from "react";
import {
  CreatorInfo,
  PPVideo,
  PostingAccount,
  fmt,
  pp,
  schedule,
} from "../api";

export function Analytics() {
  const [accounts, setAccounts] = useState<PostingAccount[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [info, setInfo] = useState<CreatorInfo | null>(null);
  const [videos, setVideos] = useState<PPVideo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    schedule.accounts().then((a) => {
      setAccounts(a);
      if (a.length > 0) setSelectedId(a[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedId === null) return;
    setLoading(true);
    setError("");
    setInfo(null);
    setVideos([]);
    Promise.all([pp.info(selectedId), pp.posts(selectedId)])
      .then(([i, v]) => {
        setInfo(i);
        setVideos(v);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [selectedId]);

  if (accounts.length === 0) {
    return (
      <div className="empty">
        <p>No accounts yet.</p>
        <p className="hint">
          Add your TikTok accounts in <strong>Schedule → Accounts</strong>{" "}
          (connected via PostPeer) and their analytics will appear here.
        </p>
      </div>
    );
  }

  const totals = videos.reduce(
    (t, v) => ({
      views: t.views + v.views,
      likes: t.likes + v.likes,
      comments: t.comments + v.comments,
      shares: t.shares + v.shares,
    }),
    { views: 0, likes: 0, comments: 0, shares: 0 }
  );

  return (
    <div className="layout">
      <aside>
        {accounts.map((a) => (
          <button
            key={a.id}
            className={
              "account-card" + (a.id === selectedId ? " selected" : "")
            }
            onClick={() => setSelectedId(a.id)}
          >
            <span
              className="chip-dot"
              style={{ background: a.color || "#ff0050" }}
            />
            <div className="account-meta">
              <strong>{a.name}</strong>
            </div>
          </button>
        ))}
      </aside>

      <main>
        {error && <div className="banner error">{error}</div>}
        {loading && <p className="hint">Loading from TikTok…</p>}

        {info && (
          <div className="creator-head">
            {info.creatorAvatarUrl && (
              <img className="avatar" src={info.creatorAvatarUrl} alt="" />
            )}
            <div>
              <strong>{info.creatorNickname || "TikTok creator"}</strong>
              <div className="hint">@{info.creatorUsername}</div>
            </div>
          </div>
        )}

        {!loading && (
          <>
            <div className="kpi-row">
              <Kpi label="Videos" value={String(videos.length)} />
              <Kpi label="Views" value={fmt(totals.views)} />
              <Kpi label="Likes" value={fmt(totals.likes)} />
              <Kpi label="Comments" value={fmt(totals.comments)} />
            </div>

            <section>
              <h2>Videos (live from TikTok, last 90 days)</h2>
              {videos.length === 0 ? (
                <p className="hint">
                  No videos found in the last 90 days for this account.
                </p>
              ) : (
                <div className="vid-table">
                  {videos.map((v, i) => (
                    <a
                      key={i}
                      className="vid-row"
                      href={v.url ?? "#"}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span className="vid-title">
                        {v.content || "Untitled"}
                      </span>
                      <span className="vid-date">
                        {v.published_at
                          ? new Date(v.published_at).toLocaleDateString()
                          : ""}
                      </span>
                      <span className="vid-stats">
                        ▶ {fmt(v.views)} · ♥ {fmt(v.likes)} · 💬{" "}
                        {fmt(v.comments)} · ↗ {fmt(v.shares)}
                      </span>
                    </a>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </main>
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
