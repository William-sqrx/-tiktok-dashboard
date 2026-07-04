import { useEffect, useMemo, useState } from "react";
import {
  PostingAccount,
  ScheduledPost,
  schedule,
} from "../api";

type View = "month" | "week" | "today";

const STATUS_COLOR: Record<string, string> = {
  pending: "#9a9aa8",
  generating: "#3b82f6",
  ready: "#a855f7",
  scheduled: "#14b8a6", // video rendered & queued on PostPeer's cloud
  posting: "#f59e0b",
  posted: "#22c55e",
  error: "#ef4444",
};

const DOT_COLORS = ["#ff0050", "#3b82f6", "#22c55e", "#f59e0b", "#a855f7"];

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}
function addDays(d: Date, n: number) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
}
function ymd(d: Date) {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}
// Monday-based weekday index (0 = Mon … 6 = Sun)
function mondayIdx(d: Date) {
  return (d.getDay() + 6) % 7;
}

export function Schedule() {
  const [view, setView] = useState<View>("month");
  const [anchor, setAnchor] = useState(() => startOfDay(new Date()));
  const [accounts, setAccounts] = useState<PostingAccount[]>([]);
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [composerFor, setComposerFor] = useState<Date | null>(null);
  const [showAccounts, setShowAccounts] = useState(false);

  // Visible date range for the current view.
  const range = useMemo(() => {
    if (view === "today") {
      return { start: startOfDay(anchor), end: addDays(startOfDay(anchor), 1) };
    }
    if (view === "week") {
      const s = addDays(anchor, -mondayIdx(anchor));
      return { start: s, end: addDays(s, 7) };
    }
    // month: pad to full weeks
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const gridStart = addDays(first, -mondayIdx(first));
    return { start: gridStart, end: addDays(gridStart, 42) };
  }, [view, anchor]);

  async function reload() {
    const [a, p] = await Promise.all([
      schedule.accounts(),
      schedule.posts(range.start.toISOString(), range.end.toISOString()),
    ]);
    setAccounts(a);
    setPosts(p);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.start.getTime(), range.end.getTime()]);

  const byDay = useMemo(() => {
    const m: Record<string, ScheduledPost[]> = {};
    for (const p of posts) {
      const d = new Date(p.scheduled_at);
      (m[ymd(d)] ||= []).push(p);
    }
    return m;
  }, [posts]);

  function shift(dir: number) {
    if (view === "month")
      setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() + dir, 1));
    else setAnchor(addDays(anchor, dir * (view === "week" ? 7 : 1)));
  }

  const heading =
    view === "month"
      ? anchor.toLocaleDateString(undefined, { month: "long", year: "numeric" })
      : view === "week"
      ? `Week of ${range.start.toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        })}`
      : anchor.toLocaleDateString(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
        });

  return (
    <div className="schedule">
      <div className="sched-toolbar">
        <div className="seg">
          {(["today", "week", "month"] as View[]).map((v) => (
            <button
              key={v}
              className={view === v ? "on" : ""}
              onClick={() => setView(v)}
            >
              {v[0].toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        <div className="nav">
          <button onClick={() => shift(-1)}>‹</button>
          <button onClick={() => setAnchor(startOfDay(new Date()))}>Today</button>
          <button onClick={() => shift(1)}>›</button>
        </div>
        <strong className="heading">{heading}</strong>
        <div className="spacer" />
        <button className="ghost" onClick={() => setShowAccounts(true)}>
          Accounts
        </button>
        <button
          className="primary"
          onClick={() => setComposerFor(startOfDay(new Date()))}
        >
          + New post
        </button>
      </div>

      {accounts.length === 0 && (
        <div className="banner warn">
          Add your TikTok accounts first (the "Accounts" button) so you can pick
          where each post goes.
        </div>
      )}

      {view === "month" ? (
        <MonthGrid
          range={range}
          anchorMonth={anchor.getMonth()}
          byDay={byDay}
          onAdd={(d) => setComposerFor(d)}
          onDelete={async (id) => {
            await schedule.delPost(id);
            reload();
          }}
        />
      ) : (
        <DayList
          range={range}
          byDay={byDay}
          onAdd={(d) => setComposerFor(d)}
          onDelete={async (id) => {
            await schedule.delPost(id);
            reload();
          }}
        />
      )}

      {composerFor && (
        <Composer
          day={composerFor}
          accounts={accounts}
          onClose={() => setComposerFor(null)}
          onCreated={() => {
            setComposerFor(null);
            reload();
          }}
        />
      )}
      {showAccounts && (
        <AccountManager
          accounts={accounts}
          onClose={() => setShowAccounts(false)}
          onChange={reload}
        />
      )}
    </div>
  );
}

function PostChip({
  p,
  onDelete,
}: {
  p: ScheduledPost;
  onDelete: (id: number) => void;
}) {
  const t = new Date(p.scheduled_at).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <div className="chip" title={`${p.status} — ${p.song_query}`}>
      <span
        className="chip-dot"
        style={{ background: p.account_color || "#ff0050" }}
      />
      <span className="chip-time">{t}</span>
      <span className="chip-title">{p.title || p.song_query}</span>
      <span
        className="chip-status"
        style={{ color: STATUS_COLOR[p.status] || "#9a9aa8" }}
      >
        {p.status}
      </span>
      <button className="chip-x" onClick={() => onDelete(p.id)}>
        ×
      </button>
    </div>
  );
}

function MonthGrid({
  range,
  anchorMonth,
  byDay,
  onAdd,
  onDelete,
}: {
  range: { start: Date; end: Date };
  anchorMonth: number;
  byDay: Record<string, ScheduledPost[]>;
  onAdd: (d: Date) => void;
  onDelete: (id: number) => void;
}) {
  const days: Date[] = [];
  for (let i = 0; i < 42; i++) days.push(addDays(range.start, i));
  const todayKey = ymd(startOfDay(new Date()));
  return (
    <div className="month">
      <div className="weekhead">
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>
      <div className="grid">
        {days.map((d) => {
          const key = ymd(d);
          const items = byDay[key] || [];
          return (
            <div
              key={key}
              className={
                "cell" +
                (d.getMonth() !== anchorMonth ? " dim" : "") +
                (key === todayKey ? " today" : "")
              }
            >
              <div className="cell-head">
                <span>{d.getDate()}</span>
                <button className="cell-add" onClick={() => onAdd(d)}>
                  +
                </button>
              </div>
              <div className="cell-body">
                {items.map((p) => (
                  <PostChip key={p.id} p={p} onDelete={onDelete} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DayList({
  range,
  byDay,
  onAdd,
  onDelete,
}: {
  range: { start: Date; end: Date };
  byDay: Record<string, ScheduledPost[]>;
  onAdd: (d: Date) => void;
  onDelete: (id: number) => void;
}) {
  const days: Date[] = [];
  const n = Math.round((range.end.getTime() - range.start.getTime()) / 86400000);
  for (let i = 0; i < n; i++) days.push(addDays(range.start, i));
  return (
    <div className="daylist">
      {days.map((d) => {
        const items = byDay[ymd(d)] || [];
        return (
          <div key={ymd(d)} className="dayrow">
            <div className="dayrow-head">
              <strong>
                {d.toLocaleDateString(undefined, {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                })}
              </strong>
              <button className="cell-add" onClick={() => onAdd(d)}>
                + add
              </button>
            </div>
            {items.length === 0 ? (
              <p className="hint">Nothing scheduled.</p>
            ) : (
              items.map((p) => <PostChip key={p.id} p={p} onDelete={onDelete} />)
            )}
          </div>
        );
      })}
    </div>
  );
}

function Composer({
  day,
  accounts,
  onClose,
  onCreated,
}: {
  day: Date;
  accounts: PostingAccount[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [song, setSong] = useState("");
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? 0);
  const [date, setDate] = useState(
    `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(
      day.getDate()
    ).padStart(2, "0")}`
  );
  const [time, setTime] = useState("10:00");
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    if (!song.trim() || !accountId) {
      setErr("Song name and account are required.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const scheduled_at = new Date(`${date}T${time}`).toISOString();
      await schedule.addPost({
        posting_account_id: accountId,
        song_query: song.trim(),
        caption: caption.trim() || undefined,
        scheduled_at,
      });
      onCreated();
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Schedule a post</h2>
        <label>Song name (or YouTube URL)</label>
        <input
          autoFocus
          value={song}
          onChange={(e) => setSong(e.target.value)}
          placeholder="e.g. 年少有为 李荣浩"
        />
        <label>Account</label>
        <select
          value={accountId}
          onChange={(e) => setAccountId(Number(e.target.value))}
        >
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <div className="row2">
          <div>
            <label>Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div>
            <label>Time</label>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
            />
          </div>
        </div>
        <label>Caption (optional — defaults to the template)</label>
        <textarea
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          rows={2}
        />
        {err && <p className="err">{err}</p>}
        <div className="modal-actions">
          <button className="ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" onClick={submit} disabled={busy}>
            {busy ? "Scheduling…" : "Schedule"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AccountManager({
  accounts,
  onClose,
  onChange,
}: {
  accounts: PostingAccount[];
  onClose: () => void;
  onChange: () => void;
}) {
  const [name, setName] = useState("");
  const [user, setUser] = useState("");

  async function add() {
    if (!name.trim() || !user.trim()) return;
    await schedule.addAccount({
      name: name.trim(),
      upload_post_user: user.trim(),
      color: DOT_COLORS[accounts.length % DOT_COLORS.length],
    });
    setName("");
    setUser("");
    onChange();
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Posting accounts</h2>
        <p className="hint">
          One row per TikTok account. "Profile" is the upload-post.com user that
          account is connected to.
        </p>
        {accounts.map((a) => (
          <div key={a.id} className="acct-row">
            <span className="chip-dot" style={{ background: a.color || "#ff0050" }} />
            <strong>{a.name}</strong>
            <span className="hint">{a.upload_post_user}</span>
            <button
              className="chip-x"
              onClick={async () => {
                await schedule.delAccount(a.id);
                onChange();
              }}
            >
              ×
            </button>
          </div>
        ))}
        <div className="row2">
          <div>
            <label>Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="HSK Fish Main"
            />
          </div>
          <div>
            <label>upload-post.com profile</label>
            <input
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="profile_username"
            />
          </div>
        </div>
        <div className="modal-actions">
          <button className="primary" onClick={add}>
            Add account
          </button>
          <button className="ghost" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
