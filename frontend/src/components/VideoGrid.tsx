import { Video, fmt } from "../api";

export function VideoGrid({ videos }: { videos: Video[] }) {
  if (videos.length === 0) {
    return <p className="hint">No videos synced yet for this account.</p>;
  }
  return (
    <div className="video-grid">
      {videos.map((v) => (
        <a
          key={v.id}
          className="video-card"
          href={v.share_url ?? "#"}
          target="_blank"
          rel="noreferrer"
        >
          <div className="thumb-wrap">
            {v.cover_image_url ? (
              <img src={v.cover_image_url} alt={v.title ?? ""} />
            ) : (
              <div className="thumb-placeholder" />
            )}
          </div>
          <div className="video-title">{v.title || "Untitled"}</div>
          <div className="video-stats">
            <span>▶ {fmt(v.view_count)}</span>
            <span>♥ {fmt(v.like_count)}</span>
            <span>💬 {fmt(v.comment_count)}</span>
            <span>↗ {fmt(v.share_count)}</span>
          </div>
        </a>
      ))}
    </div>
  );
}
