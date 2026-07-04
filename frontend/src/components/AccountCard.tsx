import { Account, fmt } from "../api";

export function AccountCard({
  account,
  selected,
  onSelect,
}: {
  account: Account;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={"account-card" + (selected ? " selected" : "")}
      onClick={onSelect}
    >
      <img
        className="avatar"
        src={account.avatar_url ?? ""}
        alt=""
        onError={(e) => (e.currentTarget.style.visibility = "hidden")}
      />
      <div className="account-meta">
        <strong>{account.display_name ?? "TikTok user"}</strong>
        <div className="stat-row">
          <span>{fmt(account.follower_count)} followers</span>
          <span>{fmt(account.likes_count)} likes</span>
          <span>{fmt(account.video_count)} videos</span>
        </div>
      </div>
    </button>
  );
}
