#!/usr/bin/env python3
"""Render the GitHub Stats and Top Languages cards as static SVGs.

Reads the GitHub GraphQL API (token from GITHUB_TOKEN) and writes
stats.svg and top-langs.svg into the output directory. Standard library only.

usage: profile_cards.py <login> <out_dir>
"""
import json
import os
import sys
import urllib.request
from html import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
  }
}
"""

BG, TITLE, TEXT, MUTED, ACCENT = "#1a1b27", "#818cf8", "#c0caf5", "#7a88b8", "#22d3ee"
FONT = "font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif"


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors") or not data.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {data.get('errors') or 'user not found'}")
    return data["data"]["user"]


def card(width, height, title, inner):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f'<rect width="{width}" height="{height}" rx="8" fill="{BG}"/>'
        f'<text x="25" y="35" style="{FONT};font-size:18px;font-weight:600" fill="{TITLE}">{escape(title)}</text>'
        f"{inner}</svg>"
    )


def stats_svg(user):
    repos = user["repositories"]["nodes"]
    c = user["contributionsCollection"]
    rows = [
        ("Total Stars Earned", sum(r["stargazerCount"] for r in repos)),
        ("Commits (last year)", c["totalCommitContributions"]),
        ("Total PRs", c["totalPullRequestContributions"]),
        ("Total Issues", c["totalIssueContributions"]),
        ("Public Repos", user["repositories"]["totalCount"]),
    ]
    out = []
    for i, (label, value) in enumerate(rows):
        y = 70 + i * 28
        out.append(
            f'<circle cx="32" cy="{y - 5}" r="4" fill="{ACCENT}"/>'
            f'<text x="46" y="{y}" style="{FONT};font-size:14px" fill="{TEXT}">{escape(label)}:</text>'
            f'<text x="290" y="{y}" text-anchor="end" style="{FONT};font-size:14px;font-weight:700" fill="{TEXT}">{value:,}</text>'
        )
    name = user.get("name") or ""
    title = f"{name}'s GitHub Stats" if name else "GitHub Stats"
    return card(320, 215, title, "".join(out))


def langs_svg(user):
    totals, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            n = edge["node"]["name"]
            totals[n] = totals.get(n, 0) + edge["size"]
            colors[n] = edge["node"]["color"] or MUTED
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:8]
    grand = sum(totals.values()) or 1
    out = []
    for i, (name, size) in enumerate(top):
        y = 70 + i * 28
        pct = size / grand * 100
        out.append(
            f'<text x="25" y="{y}" style="{FONT};font-size:13px" fill="{TEXT}">{escape(name)}</text>'
            f'<rect x="125" y="{y - 11}" width="130" height="8" rx="4" fill="#2a2c3f"/>'
            f'<rect x="125" y="{y - 11}" width="{max(130 * pct / 100, 3):.1f}" height="8" rx="4" fill="{colors[name]}"/>'
            f'<text x="295" y="{y}" text-anchor="end" style="{FONT};font-size:12px" fill="{MUTED}">{pct:.1f}%</text>'
        )
    if not top:
        out.append(f'<text x="25" y="75" style="{FONT};font-size:13px" fill="{MUTED}">No language data yet</text>')
    return card(320, 70 + max(len(top), 1) * 28 + 4, "Top Languages", "".join(out))


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    login, out_dir = sys.argv[1], sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")
    user = fetch(login, token)
    os.makedirs(out_dir, exist_ok=True)
    for fname, svg in (("stats.svg", stats_svg(user)), ("top-langs.svg", langs_svg(user))):
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {fname} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
