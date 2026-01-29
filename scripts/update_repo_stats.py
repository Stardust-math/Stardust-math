import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GH_USERNAME", "Stardust-math")

INCLUDE_FORKED_REPOS = os.environ.get("INCLUDE_FORKED_REPOS", "false").lower() == "true"
INCLUDE_ARCHIVED_REPOS = os.environ.get("INCLUDE_ARCHIVED_REPOS", "true").lower() == "true"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = os.environ.get("OUT_PATH", "badges/repo_stats.json")


def http_get_json(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_all_public_repos(username: str):
    repos = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page={per_page}&page={page}&sort=updated"
        data = http_get_json(url)
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response: {data}")
        if not data:
            break
        repos.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return repos


def parse_iso8601(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main():
    repos = list_all_public_repos(USERNAME)

    filtered = []
    for r in repos:
        if (not INCLUDE_FORKED_REPOS) and r.get("fork", False):
            continue
        if (not INCLUDE_ARCHIVED_REPOS) and r.get("archived", False):
            continue
        filtered.append(r)

    forks_total = 0
    last_push = None
    last_push_repo = ""

    for r in filtered:
        forks_total += int(r.get("forks_count", 0) or 0)
        pushed_at = r.get("pushed_at")
        if pushed_at:
            dt = parse_iso8601(pushed_at)
            if (last_push is None) or (dt > last_push):
                last_push = dt
                last_push_repo = r.get("name", "")

    if last_push is None:
        last_push = datetime.now(timezone.utc)

    payload = {
        "username": USERNAME,
        "repos_count": len(filtered),
        "forks_total": forks_total,
        "last_push_utc": last_push.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_push_date": last_push.strftime("%Y-%m-%d"),
        "last_push_repo": last_push_repo,
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    tmp_path = OUT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, OUT_PATH)

    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
