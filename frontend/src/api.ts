export interface Account {
  id: number;
  open_id: string;
  display_name: string | null;
  avatar_url: string | null;
  follower_count: number;
  following_count: number;
  likes_count: number;
  video_count: number;
  last_synced_at: string | null;
}

export interface Video {
  id: number;
  video_id: string;
  title: string | null;
  cover_image_url: string | null;
  share_url: string | null;
  embed_link: string | null;
  duration: number | null;
  create_time: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  share_count: number;
}

export interface Snapshot {
  captured_at: string;
  follower_count: number;
  likes_count: number;
  video_count: number;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  listAccounts: () => fetch("/api/accounts").then(json<Account[]>),
  videos: (id: number) =>
    fetch(`/api/accounts/${id}/videos`).then(json<Video[]>),
  history: (id: number) =>
    fetch(`/api/accounts/${id}/history`).then(json<Snapshot[]>),
  syncOne: (id: number) =>
    fetch(`/api/accounts/${id}/sync`, { method: "POST" }).then(json<Account>),
  syncAll: () => fetch("/api/sync", { method: "POST" }).then(json),
  remove: (id: number) =>
    fetch(`/api/accounts/${id}`, { method: "DELETE" }).then(json),
  connectUrl: () =>
    fetch("/api/auth/tiktok/login").then(json<{ authorize_url: string }>),
  health: () =>
    fetch("/api/health").then(
      json<{ status: string; tiktok_configured: boolean }>
    ),
};

export function fmt(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}
