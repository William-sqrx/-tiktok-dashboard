import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Snapshot } from "../api";

export function FollowerChart({ data }: { data: Snapshot[] }) {
  if (data.length < 2) {
    return (
      <p className="hint">
        Not enough history yet — sync a few times over the coming days and a
        follower trend will appear here.
      </p>
    );
  }
  const points = data.map((d) => ({
    date: new Date(d.captured_at).toLocaleDateString(),
    followers: d.follower_count,
    likes: d.likes_count,
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={points} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <XAxis dataKey="date" fontSize={12} />
        <YAxis fontSize={12} width={48} />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="followers"
          stroke="#ff0050"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
