import datetime
import json
import os
import re
import sqlite3
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "cockpit.db"
PUBLIC_SNAPSHOT = BASE_DIR / "public" / "data" / "snapshot.json"
DIST_SNAPSHOT = BASE_DIR / "dist" / "data" / "snapshot.json"
CAMPAIGNS_FILE = BASE_DIR / "backend" / "campaigns.json"
ELITE_HQ = Path(r"C:\Users\NITRO\.gemini\antigravity\scratch\elite-sniper-hq")
LOCK_FILE = ELITE_HQ / "task_registry_lock.json"
W2_FILE = ELITE_HQ / "worker2_ai_job_state.json"

USD_TO_VND = 25400

BOT_LOGINS = {
    "coderabbitai", "greptile-apps", "vercel", "github-actions", "codecov",
    "sonarqubecloud", "sonarcloud", "netlify", "changeset-bot", "dependabot",
    "renovate", "cla-bot", "easycla", "linux-foundation-easycla", "algora-pbc",
    "algora-bot", "cubic-dev-ai", "ellipsis-dev", "dosubot", "graphite-app",
    "linear", "deepsource-autofix", "copilot-pull-request-reviewer", "copilot",
    "gemini-code-assist", "claude", "cursor", "bugbot", "korbit-ai",
    "codeant-ai", "sourcery-ai", "pull-request-lint", "stale", "mergify",
    "kodiak-hq", "bors", "sentry-io", "supabase", "prisma-cloud",
    "cloudflare-workers-and-pages", "mintlify", "check-runs", "aikido-security",
    "socket-security", "gitguardian", "snyk-bot", "gitea-actions", "giteabot",
    "tscircuitbot", "claassistant", "melvin-bot",
}

FROZEN_OR_ZERO_REPOS = {
    "UseJunior/safe-docx": ("$0 Portfolio", "Repo $0 (không trả tiền mặt)"),
    "caley-io/marketing": ("$0 Portfolio", "Repo $0 (không có thưởng)"),
    "storytold/filmcraft": ("$0 Portfolio", "Repo $0 (không có thưởng)"),
    "medusajs/b2b-starter": ("$0 Portfolio", "PR cũ $0"),
    "TheSolaAI/sola-application": ("Frozen", "Repo đóng băng (0 merge gần đây)"),
    "PG-AGI/toingg-jarvis": ("Frozen", "Repo đóng băng (0 merge gần đây)"),
    "tryabby/abby": ("Frozen", "Repo đóng băng (0 merge tháng 10-11)"),
    "highlight/highlight": ("Frozen", "Repo đóng băng / chậm merge"),
    "flydelabs/flyde": ("Frozen", "Repo đóng băng (0 merge tháng 10-11)"),
}

KNOWN_PR_VALUES = {
    ("go-gitea/gitea", 40201): (200, "$200 USD (Rủi ro: #6898 từng gỡ bounty 12/2024)"),
    ("tari-project/tari-ootle", 3851): (8.82, "15,000 XTM Đã Duyệt (#676 · ~$8.82)"),
    ("tari-project/tari-ootle", 3886): (0, "Đã Merge 15:29 VN · Chờ xét retro-bounty XTM"),
    ("cognizant-ai-labs/agentic-web", 49): (0, "Đã Merge #49 · Open Agentic Web ($10k-$13k)"),
    ("go-gitea/gitea", 40228): (0, "PR kỹ thuật phụ (không gắn bounty)"),
    ("documenso/documenso", 3577): (0, "Rủi ro trùng (#3582 đã merge 11/11)"),
    ("PsymoNiko/mediamtx-dashboard", 134): (0, "$0 (Bounty #4 đã trao từ 05/2026)"),
    ("CapSoftware/Cap", 3706): (500, "$500 USD (Algora #73)"),
    ("CapSoftware/Cap", 4149): (150, "$150 USD (Algora #28)"),
    ("CapSoftware/Cap", 4152): (0, "$0 (Bug #2144 không gắn bounty)"),
    ("CapSoftware/Cap", 3916): (0, "$0 (Feature #2928 không gắn bounty)"),
    ("CapSoftware/Cap", 3892): (0, "$0 (Feature #3636 không gắn bounty)"),
    ("CapSoftware/Cap", 3769): (0, "SEO / Không gắn bounty"),
    ("ergoplatform/ergo", 2957): (200, "$200 SigUSD (#2157)"),
    ("ergoplatform/ergo", 2956): (100, "$100 SigUSD (#2095)"),
    ("ergoplatform/ergo", 2955): (0, "100 ERG (#2213)"),
    ("ergoplatform/ergo", 2954): (500, "$500 SigUSD (#1868)"),
    ("ergoplatform/ergo", 2953): (500, "$500 SigUSD (#1884)"),
    ("ergoplatform/ergo", 2952): (500, "$500 SigUSD (#1556)"),
    ("ergoplatform/ergo", 2951): (1000, "$1,000 SigUSD (#1392)"),
    ("ergoplatform/ergo", 2950): (1000, "$1,000 SigUSD (#1668)"),
    ("ergoplatform/ergo", 2949): (500, "$500 SigUSD (#1228)"),
    ("ergoplatform/ergo", 2948): (0, "Ergo Wallet Slice (#2281)"),
    ("ergoplatform/ergo", 2947): (0, "100 ERG (#1005)"),
    ("ergoplatform/ergo", 2946): (0, "200 ERG (#938)"),
    ("ergoplatform/ergo", 2945): (500, "$500 SigUSD (#2092)"),
    ("ergoplatform/ergo", 2944): (1000, "$1,000 SigUSD (#2034)"),
    ("ergoplatform/ergo", 2941): (500, "$500 SigUSD (#1551)"),
    ("ergoplatform/ergo", 2940): (0, "200 ERG (#1156)"),
    ("ergoplatform/ergo", 2930): (500, "$500 SigUSD (#1885)"),
    ("ergoplatform/ergo", 2921): (500, "$500 SigUSD (#1598)"),
    ("ergoplatform/ergo", 2920): (500, "$500 SigUSD (#1952)"),
}

def load_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("Missing GITHUB_TOKEN in environment or .env")

def is_bot(author: dict | None) -> bool:
    if not author:
        return True
    login = (author.get("login") or "").lower()
    typ = author.get("__typename", "")
    return typ == "Bot" or login.endswith("[bot]") or login.endswith("-bot") or login in BOT_LOGINS

def gql(token: str, query: str, variables: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "bounty-cockpit-sync",
    }
    data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request("https://api.github.com/graphql", data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("data", {})

SEARCH_QUERY = """
query($q: String!, $after: String) {
  search(query: $q, type: ISSUE, first: 50, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        url
        state
        createdAt
        updatedAt
        mergedAt
        closedAt
        mergeable
        reviewDecision
        labels(first: 10) { nodes { name } }
        repository { nameWithOwner primaryLanguage { name } }
        comments(last: 10) {
          nodes {
            author { __typename login }
            createdAt
            body
          }
        }
        reviews(last: 10) {
          nodes {
            author { __typename login }
            state
            submittedAt
            body
          }
        }
      }
    }
  }
}
"""

def fetch_all(token: str, q: str) -> list[dict]:
    out = []
    after = None
    while True:
        d = gql(token, SEARCH_QUERY, {"q": q, "after": after})
        s = d.get("search") or {}
        nodes = [n for n in (s.get("nodes") or []) if n]
        out.extend(nodes)
        pi = s.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        after = pi.get("endCursor")
    return out

def parse_usd_and_tier(repo: str, num: int, title: str, labels: list[str]) -> tuple[float, str, str]:
    if (repo, num) in KNOWN_PR_VALUES:
        val, lbl = KNOWN_PR_VALUES[(repo, num)]
        tier = (
            "Crypto / Ergo"
            if repo.startswith("ergoplatform/")
            else ("Crypto / Tari XTM" if repo.startswith("tari-project/") else ("USD Cash" if val > 0 else "$0"))
        )
        return float(val), lbl, tier
    if repo.startswith("tari-project/"):
        return 0.0, "XTM Retro Bounty (Chưa định giá USD)", "Crypto / Tari XTM"
    if repo.startswith("ergoplatform/"):
        return 0.0, "Ergo (Cần đối chiếu bounty)", "Crypto / Ergo"
    if repo.startswith("tscircuit/"):
        return 0.0, "$0 (Chờ duyệt Sponsor / hay Stale)", "$0 / Backlog"
    if repo in FROZEN_OR_ZERO_REPOS:
        return 0.0, "$0", "$0 / Backlog"
    text = f"{title} {' '.join(labels)}"
    m = re.search(r"\$([\d,]+(?:\.\d+)?)\s*(k)?", text, re.I)
    if m:
        amt = float(m.group(1).replace(",", ""))
        if m.group(2):
            amt *= 1000
        return amt, f"${int(amt):,} USD", "USD Cash"
    return 0.0, "$0 / Chưa xác định", "$0 / Backlog"

def extract_human_feedback(pr: dict) -> tuple[list[dict], list[dict]]:
    humans = []
    bots = []
    for r in (pr.get("reviews") or {}).get("nodes") or []:
        a = r.get("author")
        login = a.get("login") if a else "ghost"
        if login == "cocvn157":
            continue
        body = (r.get("body") or "").strip()
        entry = {
            "author": login,
            "kind": f"Review ({r.get('state')})",
            "at": r.get("submittedAt"),
            "snippet": re.sub(r"\s+", " ", body)[:280] if body else f"Trạng thái: {r.get('state')}",
        }
        (bots if is_bot(a) else humans).append(entry)
    for c in (pr.get("comments") or {}).get("nodes") or []:
        a = c.get("author")
        login = a.get("login") if a else "ghost"
        if login == "cocvn157":
            continue
        body = (c.get("body") or "").strip()
        entry = {
            "author": login,
            "kind": "Comment",
            "at": c.get("createdAt"),
            "snippet": re.sub(r"\s+", " ", body)[:280],
        }
        (bots if is_bot(a) else humans).append(entry)
    humans.sort(key=lambda x: x["at"] or "", reverse=True)
    bots.sort(key=lambda x: x["at"] or "", reverse=True)
    return humans, bots

def classify_item(pr: dict, humans: list[dict], bots: list[dict], usd: float) -> dict:
    repo = pr["repository"]["nameWithOwner"]
    num = pr["number"]
    state = pr["state"]  # OPEN, MERGED, CLOSED
    mergeable = pr.get("mergeable")
    latest_human = humans[0] if humans else None
    latest_bot = bots[0] if bots else None

    if state == "MERGED":
        if (repo, num) == ("go-gitea/gitea", 40201):
            return {
                "drop_state": "MERGED_APPROVED",
                "drop_label": "Đã Merge · Chờ Xét Claim (Rủi Ro)",
                "drop_reason": "Đã merge 10/11 & có link Algora claim, nhưng @lunny từng gỡ #6898 khỏi bounty list 12/2024",
                "readiness": 45,
                "next_action": "Giữ im chờ admin xử lý claim; không trông chờ chắc chắn $200",
                "owner": "Commander",
            }
        return {
            "drop_state": "MERGED",
            "drop_label": "Đã Merge",
            "drop_reason": "PR đã được gộp vào nhánh chính",
            "readiness": 100 if usd == 0 else 90,
            "next_action": "Hoàn tất" if usd == 0 else "Kiểm tra giải ngân",
            "owner": "Commander",
        }

    if state == "CLOSED":
        reason = "Maintainer đóng chưa merge"
        if repo.startswith("tscircuit/") or (latest_bot and "stale" in (latest_bot.get("snippet") or "").lower()):
            reason = "Bot tự động đóng do quá hạn Stale"
        elif repo == "BasedHardware/omi":
            reason = "Repo đóng hàng loạt PR ngoài (09/11)"
        elif (repo, num) == ("CapSoftware/Cap", 3925):
            reason = "Maintainer đóng — nhánh main đã xử lý cách khác"
        elif (repo, num) == ("tari-project/tari-ootle", 3834):
            reason = "Đóng để thay bằng bản mới sạch hơn (ootle.ts#154)"
        elif latest_human and "would not approve" in (latest_human.get("snippet") or "").lower():
            reason = f"Review báo blocking bởi @{latest_human['author']}"
        return {
            "drop_state": "DROPPED",
            "drop_label": "Đã Rớt",
            "drop_reason": reason,
            "readiness": 0,
            "next_action": "Không xử lý nữa",
            "owner": "Archive",
        }

    # OPEN PR
    if repo == "tari-project/tari-ootle" and latest_human and "would approve" in (latest_human.get("snippet") or "").lower():
        return {
            "drop_state": "NEAR_WIN",
            "drop_label": "Chưa Rớt · Sắp Chốt",
            "drop_reason": f"@{latest_human['author']} đánh giá 'would approve (0 blocking)'",
            "readiness": 80,
            "next_action": "Chờ maintainer bấm Approve & Merge + xét retro XTM",
            "owner": "Commander",
        }

    if (repo, num) == ("CapSoftware/Cap", 3706):
        return {
            "drop_state": "NEAR_WIN",
            "drop_label": "Chưa Rớt · Sắp Chốt",
            "drop_reason": "Đã rebase sạch theo yêu cầu @richiemcilroy, chờ xem lại",
            "readiness": 75,
            "next_action": "Chờ @richiemcilroy review & merge",
            "owner": "Worker 1 / Commander",
        }

    if mergeable == "CONFLICTING":
        return {
            "drop_state": "NEEDS_FIX",
            "drop_label": "Chưa Rớt · Bị Conflict",
            "drop_reason": "Đang xung đột git (mergeable=CONFLICTING)",
            "readiness": 25 if usd > 0 else 5,
            "next_action": "Rebase nếu kèo $ > 0; bỏ nếu $0",
            "owner": "Worker 1" if usd > 0 else "Archive",
        }

    if (repo, num) == ("CapSoftware/Cap", 4149):
        return {
            "drop_state": "NEAR_WIN",
            "drop_label": "Chưa Rớt · Sắp Chốt",
            "drop_reason": "Đã đạt Greptile 5/5 trên commit cuối, không conflict, chờ @richiemcilroy duyệt",
            "readiness": 75,
            "next_action": "Chờ @richiemcilroy review & merge ($150 Algora #28)",
            "owner": "Commander / Worker 1",
        }

    if (repo, num) == ("CapSoftware/Cap", 4152):
        return {
            "drop_state": "FROZEN_ZERO",
            "drop_label": "Chưa Rớt · Đạt 5/5 (Kèo $0)",
            "drop_reason": "PR đã Greptile 5/5 & mergeable=True, nhưng Issue #2144 không có /bounty ($0)",
            "readiness": 60,
            "next_action": "Giữ mở, không tốn thêm công vì $0",
            "owner": "Archive",
        }

    if (repo, num) == ("documenso/documenso", 3577):
        return {
            "drop_state": "STALE_RISK",
            "drop_label": "Nguy Cơ Rớt (Trùng PR #3582)",
            "drop_reason": "Maintainer @catalinpit đã merge PR #3582 ngày 11/11 sửa convertToLocalSystemFormat",
            "readiness": 15,
            "next_action": "Không kỳ vọng $500; giữ theo dõi hoặc đóng nếu maintainer yêu cầu",
            "owner": "Archive",
        }

    if (repo, num) == ("PsymoNiko/mediamtx-dashboard", 134):
        return {
            "drop_state": "STALE_RISK",
            "drop_label": "Hết Hạn (Đã Trao 05/2026)",
            "drop_reason": "Issue #4 đã có PR được merge & Algora trao thưởng từ 11/05/2026",
            "readiness": 5,
            "next_action": "Bỏ qua, không tốn công chăm sóc",
            "owner": "Archive",
        }

    if repo == "ergoplatform/ergo" and latest_human and ("blocking" in (latest_human.get("snippet") or "").lower() or "likely bug" in (latest_human.get("snippet") or "").lower()):
        return {
            "drop_state": "ALIVE",
            "drop_label": "Chưa Rớt · Đã Đẩy Fix Chờ Chấm Lại",
            "drop_reason": f"Đã đẩy commit sửa sau review @{latest_human['author']}, chờ re-test CI",
            "readiness": 55,
            "next_action": "Theo dõi re-review từ @cafebedouin / maintainer",
            "owner": "Commander",
        }

    if repo in FROZEN_OR_ZERO_REPOS:
        kind, rsn = FROZEN_OR_ZERO_REPOS[repo]
        return {
            "drop_state": "FROZEN_ZERO",
            "drop_label": f"Tạm Dừng ({kind})",
            "drop_reason": rsn,
            "readiness": 5,
            "next_action": "Ngừng tốn công (vốn=0 cần ưu tiên kèo ra tiền)",
            "owner": "Archive",
        }

    if repo.startswith("tscircuit/"):
        is_stale = any("stale" in (b.get("snippet") or "").lower() for b in bots)
        return {
            "drop_state": "STALE_RISK" if is_stale else "FROZEN_ZERO",
            "drop_label": "Nguy Cơ Rớt (Stale)" if is_stale else "Backlog tscircuit",
            "drop_reason": "Bot đã gắn cảnh báo stale sắp đóng" if is_stale else "Chờ Discord/Sponsorship (phản hồi GitHub rất thấp)",
            "readiness": 10,
            "next_action": "Không cày thêm PR lạnh",
            "owner": "Archive",
        }

    if repo in {"tari-project/ootle.ts", "tari-project/ootle-py"}:
        return {
            "drop_state": "ALIVE",
            "drop_label": "Chưa Rớt · Vừa Nộp (CI Xanh)",
            "drop_reason": "PR sạch mới nộp sáng 18/11, chờ maintainer Tari review",
            "readiness": 65,
            "next_action": "Chờ maintainer review & xét retro XTM",
            "owner": "Commander / Worker 1",
        }

    return {
        "drop_state": "ALIVE",
        "drop_label": "Chưa Rớt · Đang Chạy",
        "drop_reason": "Đang mở, chưa có phản hồi người thật" if not latest_human else f"Có cmt từ @{latest_human['author']}",
        "readiness": 40 if usd > 0 else 15,
        "next_action": "Theo dõi phản hồi maintainer" if usd > 0 else "Ưu tiên thấp",
        "owner": "Commander" if repo.startswith("ergoplatform/") else "Worker 1",
    }

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            synced_at TEXT NOT NULL,
            open_count INTEGER NOT NULL,
            merged_count INTEGER NOT NULL,
            closed_count INTEGER NOT NULL,
            human_feedback_open INTEGER NOT NULL,
            summary_json TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            url TEXT
        )
    """)
    conn.commit()

def record_diff_events(conn: sqlite3.Connection, now_iso: str, items: list[dict]):
    cur = conn.execute("SELECT summary_json FROM snapshots ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        conn.execute(
            "INSERT INTO events (at, kind, title, detail, url) VALUES (?, ?, ?, ?, ?)",
            (now_iso, "sync", "Khởi tạo Cockpit Sync Engine", f"Đã quét {len(items)} bài PR từ GitHub API", None),
        )
        conn.commit()
        return

    prev = {it["id"]: it for it in json.loads(row[0]).get("items_index", [])}
    for it in items:
        old = prev.get(it["id"])
        if not old:
            conn.execute(
                "INSERT INTO events (at, kind, title, detail, url) VALUES (?, ?, ?, ?, ?)",
                (now_iso, "new", f"PR mới: {it['repo']}#{it['number']}", it["title"][:120], it["url"]),
            )
        else:
            if old.get("state") != it["state"]:
                conn.execute(
                    "INSERT INTO events (at, kind, title, detail, url) VALUES (?, ?, ?, ?, ?)",
                    (now_iso, "state", f"Đổi trạng thái {it['repo']}#{it['number']}: {old.get('state')} -> {it['state']}", it["drop_reason"], it["url"]),
                )
            elif (old.get("human_count", 0) < it.get("human_count", 0)):
                lh = it["latest_human"] or {}
                conn.execute(
                    "INSERT INTO events (at, kind, title, detail, url) VALUES (?, ?, ?, ?, ?)",
                    (now_iso, "human", f"Phản hồi mới từ @{lh.get('author')} trên {it['repo']}#{it['number']}", (lh.get("snippet") or "")[:160], it["url"]),
                )
    conn.commit()

def run_sync() -> dict:
    token = load_token()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_vn = now_utc + datetime.timedelta(hours=7)

    open_prs = fetch_all(token, "is:pr author:cocvn157 is:open")
    merged_prs = fetch_all(token, "is:pr author:cocvn157 is:merged")
    closed_prs = fetch_all(token, "is:pr author:cocvn157 is:closed is:unmerged sort:updated-desc")

    all_prs = open_prs + merged_prs + closed_prs
    items = []

    for pr in all_prs:
        repo = pr["repository"]["nameWithOwner"]
        num = pr["number"]
        labels = [l["name"] for l in (pr.get("labels") or {}).get("nodes") or []]
        usd, usd_label, tier = parse_usd_and_tier(repo, num, pr["title"], labels)
        humans, bots = extract_human_feedback(pr)
        cls = classify_item(pr, humans, bots, usd)

        created_dt = datetime.datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
        age_days = max(0, round((now_utc - created_dt).total_seconds() / 86400, 1))
        lang = ((pr["repository"].get("primaryLanguage") or {}).get("name")) or "Code"

        items.append({
            "id": f"{repo}#{num}",
            "repo": repo,
            "number": num,
            "title": pr["title"],
            "url": pr["url"],
            "state": pr["state"],
            "lang": lang,
            "usd": usd,
            "usd_label": usd_label,
            "tier": tier,
            "created_at": pr["createdAt"],
            "updated_at": pr["updatedAt"],
            "merged_at": pr.get("mergedAt"),
            "closed_at": pr.get("closedAt"),
            "age_days": age_days,
            "mergeable": pr.get("mergeable"),
            "human_count": len(humans),
            "bot_count": len(bots),
            "latest_human": humans[0] if humans else None,
            "human_history": humans[:5],
            "latest_bot": bots[0] if bots else None,
            **cls,
        })

    # Add Public-Safe Special Entries (Private Security Advisory + Job AI)
    items.insert(0, {
        "id": "tari-project/tari-ootle#GHSA-9xcg-c7qc-33hv",
        "repo": "tari-project/tari-ootle",
        "number": 0,
        "title": "Private Security Advisory GHSA-9xcg-c7qc-33hv (Consensus Bug Bounty)",
        "url": "https://github.com/tari-project/tari-ootle/security/advisories/GHSA-9xcg-c7qc-33hv",
        "state": "ADVISORY",
        "lang": "Rust",
        "usd": 0.0,
        "usd_label": "15k–150k XTM (Tari Bug Hunt)",
        "tier": "Crypto / Tari XTM",
        "created_at": "2026-11-18T03:16:58Z",
        "updated_at": "2026-11-18T03:16:58Z",
        "merged_at": None,
        "closed_at": None,
        "age_days": 0.0,
        "mergeable": "NA",
        "human_count": 0,
        "bot_count": 0,
        "latest_human": None,
        "human_history": [],
        "latest_bot": None,
        "drop_state": "ALIVE",
        "drop_label": "Đã Nộp · Đang Triage",
        "drop_reason": "Báo cáo bảo mật riêng đã gửi thành công (trạng thái triage)",
        "readiness": 70,
        "next_action": "Chờ Tari Security Team xác nhận mức độ & thưởng XTM",
        "owner": "Commander",
    })

    items.insert(1, {
        "id": "tari-project/tari-ootle#GHSA-9j8f-q3rm-7q3v",
        "repo": "tari-project/tari-ootle",
        "number": 0,
        "title": "Private Security Advisory GHSA-9j8f-q3rm-7q3v (tari_walletd Auth Bypass)",
        "url": "https://github.com/tari-project/tari-ootle/security/advisories/GHSA-9j8f-q3rm-7q3v",
        "state": "ADVISORY",
        "lang": "Rust",
        "usd": 0.0,
        "usd_label": "15k–150k XTM (Tari Bug Hunt)",
        "tier": "Crypto / Tari XTM",
        "created_at": "2026-11-18T04:21:18Z",
        "updated_at": "2026-11-18T04:21:18Z",
        "merged_at": None,
        "closed_at": None,
        "age_days": 0.0,
        "mergeable": "NA",
        "human_count": 0,
        "bot_count": 0,
        "latest_human": None,
        "human_history": [],
        "latest_bot": None,
        "drop_state": "ALIVE",
        "drop_label": "Đã Nộp · Đang Triage",
        "drop_reason": "Báo cáo phân quyền handle_publish_template đã gửi thành công",
        "readiness": 72,
        "next_action": "Chờ Tari Security Team xác nhận & xét thưởng XTM",
        "owner": "Commander",
    })

    items.insert(2, {
        "id": "tari-project/tari-ootle#GHSA-x844-q559-4vcj",
        "repo": "tari-project/tari-ootle",
        "number": 0,
        "title": "Private Security Advisory GHSA-x844-q559-4vcj (Consensus LocalAccept DoS)",
        "url": "https://github.com/tari-project/tari-ootle/security/advisories/GHSA-x844-q559-4vcj",
        "state": "ADVISORY",
        "lang": "Rust",
        "usd": 0.0,
        "usd_label": "15k–150k XTM (Tari Bug Hunt)",
        "tier": "Crypto / Tari XTM",
        "created_at": "2026-11-18T05:39:29Z",
        "updated_at": "2026-11-18T05:39:29Z",
        "merged_at": None,
        "closed_at": None,
        "age_days": 0.0,
        "mergeable": "NA",
        "human_count": 0,
        "bot_count": 0,
        "latest_human": None,
        "human_history": [],
        "latest_bot": None,
        "drop_state": "ALIVE",
        "drop_label": "Đã Nộp · Đang Triage (High/Crit)",
        "drop_reason": "Lỗ hổng cross-shard LocalAccept HotStuff DoS đã gửi thành công",
        "readiness": 75,
        "next_action": "Chờ Tari Security Team xác nhận & xét thưởng XTM",
        "owner": "Commander",
    })

    # Compute KPI metrics honestly
    paid_open_items = [i for i in items if i["state"] == "OPEN" and i["usd"] > 0 and i["drop_state"] not in {"FROZEN_ZERO", "DROPPED"}]
    paid_open_human = [i for i in paid_open_items if i["human_count"] > 0]
    all_open_items = [i for i in items if i["state"] == "OPEN"]
    all_open_human = [i for i in all_open_items if i["human_count"] > 0]
    near_win_items = [i for i in items if i["drop_state"] in {"NEAR_WIN", "MERGED_APPROVED"}]

    approved_usd = sum(i["usd"] for i in items if i["drop_state"] in {"MERGED_APPROVED"} or (i["state"] == "MERGED" and i["usd"] > 0))
    active_paid_usd = sum(i["usd"] for i in paid_open_items)
    near_win_usd = sum(i["usd"] for i in near_win_items if i["state"] == "OPEN")

    # Lock / cooldown status
    lock_data = {}
    if LOCK_FILE.exists():
        lock_data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    last_write_at = lock_data.get("last_github_write_at")
    cooldown_remaining_sec = 0
    if last_write_at:
        lw_dt = datetime.datetime.fromisoformat(last_write_at.replace("Z", "+00:00"))
        elapsed = (now_utc - lw_dt).total_seconds()
        cooldown_remaining_sec = max(0, int(900 - elapsed))

    w2_data = {}
    if W2_FILE.exists():
        try:
            w2_data = json.loads(W2_FILE.read_text(encoding="utf-8"))
        except Exception:
            w2_data = {}

    deadline_dt = datetime.datetime(2026, 11, 30, 23, 59, 59, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    deadline_left_hours = max(0, round((deadline_dt - now_vn).total_seconds() / 3600, 1))

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    record_diff_events(conn, now_vn.isoformat(), items)

    # Also build recent GitHub activity feed from latest PRs updated in last 48h
    recent_feed = []
    cur = conn.execute("SELECT at, kind, title, detail, url FROM events ORDER BY id DESC LIMIT 15")
    for r in cur.fetchall():
        recent_feed.append({"at": r[0], "kind": r[1], "title": r[2], "detail": r[3], "url": r[4]})

    if len(recent_feed) < 8:
        sorted_recent = sorted(items, key=lambda x: x["updated_at"], reverse=True)[:12]
        for x in sorted_recent:
            kind = "merged" if x["state"] == "MERGED" else ("dropped" if x["state"] == "CLOSED" else ("human" if x["latest_human"] else "open"))
            detail = x["latest_human"]["snippet"][:150] if x["latest_human"] else x["drop_reason"]
            recent_feed.append({
                "at": x["updated_at"],
                "kind": kind,
                "title": f"{x['repo']}#{x['number']} · {x['drop_label']}" if x["number"] else x["title"],
                "detail": detail,
                "url": x["url"],
            })

    # Repo breakdown for clear grouping
    repo_groups = {}
    for i in items:
        r = i["repo"]
        g = repo_groups.setdefault(r, {"repo": r, "open": 0, "merged": 0, "closed": 0, "human": 0, "usd": 0.0, "tier": i["tier"]})
        if i["state"] == "OPEN":
            g["open"] += 1
        elif i["state"] == "MERGED":
            g["merged"] += 1
        elif i["state"] == "CLOSED":
            g["closed"] += 1
        if i["human_count"] > 0:
            g["human"] += 1
        if i["state"] in {"OPEN", "MERGED"}:
            g["usd"] += i["usd"]

    payload = {
        "generated_at_vn": now_vn.strftime("%Y-%m-%d %H:%M:%S +07:00"),
        "generated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "usd_to_vnd": USD_TO_VND,
        "goal": {
            "target_usd": 1000,
            "earned_usd": 0,
            "approved_pending_usd": approved_usd,
            "near_win_usd": near_win_usd,
            "active_paid_usd": active_paid_usd,
            "deadline_iso": deadline_dt.isoformat(),
            "deadline_label": "30/11/2026",
            "hours_remaining": deadline_left_hours,
        },
        "kpis": {
            "total_all_prs": len(open_prs) + len(merged_prs) + len(closed_prs),
            "open_count": len(open_prs),
            "merged_count": len(merged_prs),
            "closed_count": len(closed_prs),
            "paid_open_count": len(paid_open_items),
            "near_win_count": len(near_win_items),
            "tscircuit_open_count": sum(1 for i in all_open_items if i["repo"].startswith("tscircuit/")),
            "human_response_rate_paid_pct": round((len(paid_open_human) / len(paid_open_items) * 100), 1) if paid_open_items else 0.0,
            "human_response_rate_all_pct": round((len(all_open_human) / len(all_open_items) * 100), 1) if all_open_items else 0.0,
            "paid_open_human_count": len(paid_open_human),
            "all_open_human_count": len(all_open_human),
        },
        "team": {
            "cooldown_remaining_sec": cooldown_remaining_sec,
            "last_github_write_at": last_write_at,
            "last_github_write_target": lock_data.get("last_github_write_target"),
            "last_github_write_by": lock_data.get("last_github_write_by"),
            "gmail_status": f"Kiểm tra theo yêu cầu (sync lúc {now_vn.strftime('%H:%M VN')})",
            "agents": [
                {"name": "Stellar Wave 11 (Hồ Sơ Sạch 56 PR)", "status": "Active", "focus": "Đậu Sumsub KYC; đã đóng 385/385 PR rác -> còn 56 PR; giữ 7 slot Dex-Chat pre-stage & đang quét bù 8 slot mới"},
                {"name": "Tari Bounty Team (33 PR + 10 GHSA)", "status": "Active", "focus": "Đã merge #3851 & #3886; vá conflict #3830 & #3869 -> 17/17 tari-ootle MERGEABLE; đã nộp đủ 10 GHSA"},
                {"name": "Hackathon & Kaggle (DeBERTa V2 Submitted)", "status": "Active", "focus": "NanoVault ($30k) ĐÃ NỘP; Santa V2 185,887; Squares 24.171; Name That LLM đã nộp DeBERTa V2 OOF 0.4201 (ref 58647073)"},
                {"name": "Fast Cash & Delphi Arena", "status": "Ready", "focus": "Xong tool delphi-evidence-miner (20/20 tests, 50 live markets) & 3 bộ kit Upwork/Mindrift/Superteam Wave 2"},
            ],
        },
        "campaigns": json.loads(CAMPAIGNS_FILE.read_text(encoding="utf-8")) if CAMPAIGNS_FILE.exists() else [],
        "repo_groups": sorted(repo_groups.values(), key=lambda x: (x["usd"], x["human"], x["open"]), reverse=True),
        "feed": recent_feed[:20],
        "items": items,
    }

    slim_summary = {
        "items_index": [
            {"id": x["id"], "state": x["state"], "human_count": x["human_count"]}
            for x in items
        ]
    }
    conn.execute(
        "INSERT INTO snapshots (synced_at, open_count, merged_count, closed_count, human_feedback_open, summary_json) VALUES (?, ?, ?, ?, ?, ?)",
        (now_vn.isoformat(), len(open_prs), len(merged_prs), len(closed_prs), len(all_open_human), json.dumps(slim_summary)),
    )
    conn.commit()
    conn.close()

    for target in (PUBLIC_SNAPSHOT, DIST_SNAPSHOT):
        if target.parent.parent.exists() or target == PUBLIC_SNAPSHOT:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return payload

if __name__ == "__main__":
    p = run_sync()
    print(f"Synced OK @ {p['generated_at_vn']} | Open={p['kpis']['open_count']} | PaidOpen={p['kpis']['paid_open_count']} (${p['goal']['active_paid_usd']:,.0f}) | Merged={p['kpis']['merged_count']} | Closed={p['kpis']['closed_count']}")
