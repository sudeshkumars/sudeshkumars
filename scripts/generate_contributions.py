#!/usr/bin/env python3
"""Build Sudesh's daily contribution-city SVG from GitHub's public GraphQL data."""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request
from collections import Counter
from xml.sax.saxutils import escape

USER = "sudeshkumars"
WIDTH, HEIGHT = 1200, 650
BLUE_LEVEL = {
    "NONE": "#102d42",
    "FIRST_QUARTILE": "#16516e",
    "SECOND_QUARTILE": "#217fa4",
    "THIRD_QUARTILE": "#30b4d4",
    "FOURTH_QUARTILE": "#50e7f2",
}
LANGUAGE_COLORS = ["#50e7f2", "#398cff", "#2186ae", "#9deaff", "#56788b"]


def fetch_profile(start: dt.datetime, end: dt.datetime) -> dict:
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from,to:$to){
          totalCommitContributions totalIssueContributions
          totalPullRequestContributions totalPullRequestReviewContributions
          totalRepositoryContributions
          contributionCalendar{totalContributions weeks{contributionDays{contributionCount contributionLevel date}}}
        }
        repositories(first:100,privacy:PUBLIC,isFork:false){
          totalCount nodes{stargazerCount forkCount primaryLanguage{name}}
        }
      }
    }"""
    payload = json.dumps({
        "query": query,
        "variables": {
            "login": USER,
            "from": start.isoformat(),
            "to": end.isoformat(),
        },
    }).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "profile-contribution-city",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"][0].get("message", "GraphQL query failed"))
    return result["data"]["user"]


def polygon(points: list[tuple[float, float]], fill: str, stroke: str = "none", extra: str = "") -> str:
    coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{coordinates}" fill="{fill}" stroke="{stroke}" {extra}/>'


def build_city(profile: dict | None, start: dt.datetime, end: dt.datetime) -> str:
    weeks: list[dict] = []
    total = commits = issues = pulls = reviews = repos = stars = forks = 0
    language_counts: Counter[str] = Counter()
    if profile:
        activity = profile["contributionsCollection"]
        weeks = activity["contributionCalendar"]["weeks"]
        total = activity["contributionCalendar"]["totalContributions"]
        commits = activity["totalCommitContributions"]
        issues = activity["totalIssueContributions"]
        pulls = activity["totalPullRequestContributions"]
        reviews = activity["totalPullRequestReviewContributions"]
        repos = profile["repositories"]["totalCount"]
        nodes = profile["repositories"]["nodes"]
        stars = sum(repo["stargazerCount"] for repo in nodes)
        forks = sum(repo["forkCount"] for repo in nodes)
        for repo in nodes:
            language = repo.get("primaryLanguage")
            if language:
                language_counts[language["name"]] += 1

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Sudesh Kumar contribution city</title>',
        f'<desc id="desc">{total} contributions from {start:%Y-%m-%d} through {end:%Y-%m-%d}, shown as a blue isometric city.</desc>',
        '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#030817"/><stop offset=".55" stop-color="#07182b"/><stop offset="1" stop-color="#081d32"/></linearGradient><linearGradient id="cyan"><stop stop-color="#50e7f2"/><stop offset="1" stop-color="#398cff"/></linearGradient><linearGradient id="gold"><stop stop-color="#ffe08a"/><stop offset="1" stop-color="#f5ad48"/></linearGradient><filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><style>@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}.tile{animation:rise .35s ease both}</style></defs>',
        '<rect x="1" y="1" width="1198" height="648" rx="24" fill="url(#bg)" stroke="#36bddc" stroke-opacity=".5"/>',
        '<path d="M34 28h38" stroke="url(#cyan)" stroke-width="3" stroke-linecap="round"/>',
        '<text x="34" y="59" fill="#ecfaff" font-family="Arial,sans-serif" font-size="24" font-weight="700">MY CONTRIBUTION CITY</text>',
        '<text x="34" y="87" fill="#b9d9e7" font-family="Arial,sans-serif" font-size="13" font-style="italic">Every commit builds another tower — rebuilt automatically every day.</text>',
        f'<text x="1165" y="48" text-anchor="end" fill="#a8cadd" font-family="Arial,sans-serif" font-size="11">{start:%Y-%m-%d} / {end:%Y-%m-%d}</text>',
        '<path d="M32 103h1136" stroke="#8ed8ed" stroke-opacity=".16"/>',
    ]

    # Isometric calendar: every tile represents one day; busier days rise higher.
    weeks = weeks[-53:]
    x_origin, y_origin = 395, 125
    half_w, half_h = 10.2, 5.2
    heights = [0, 6, 14, 23, 34]
    side_colors = ["#102d42", "#10445e", "#176589", "#208eb1", "#2db6d3"]
    top_colors = ["#102d42", "#2781a2", "#36b4d1", "#50d8e8", "#62eff6"]
    for column, week in enumerate(weeks):
        for item in week["contributionDays"]:
            date = dt.date.fromisoformat(item["date"])
            day = date.weekday()
            x = x_origin + (column - day) * half_w
            y = y_origin + (column + day) * half_h
            level = {
                "NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
                "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4,
            }.get(item.get("contributionLevel"), 1 if item["contributionCount"] else 0)
            height = heights[level]
            top = [(x, y - half_h), (x + half_w, y), (x, y + half_h), (x - half_w, y)]
            chunks.append(f'<g class="tile" style="animation-delay:{min(column * .006, .3):.3f}s"><title>{date:%Y-%m-%d}: {item["contributionCount"]} contributions</title>')
            if height:
                raised = [(px, py - height) for px, py in top]
                chunks.append(polygon([raised[1], raised[2], top[2], top[1]], side_colors[level], "#061424"))
                chunks.append(polygon([raised[2], raised[3], top[3], top[2]], side_colors[max(0, level - 1)], "#061424"))
                chunks.append(polygon(raised, top_colors[level], "#a8f5ff", 'stroke-width=".7" filter="url(#glow)"' if level == 4 else 'stroke-width=".55"'))
            else:
                chunks.append(polygon(top, BLUE_LEVEL["NONE"], "#1a4a63", 'stroke-width=".45"'))
            chunks.append("</g>")

    # Compact language donut from the user's public repository primary languages.
    chunks.extend([
        '<text x="41" y="481" fill="#91e9f5" font-family="Arial,sans-serif" font-size="10" font-weight="700" letter-spacing="2">LANGUAGE MIX • PUBLIC REPOS</text>',
        '<circle cx="132" cy="548" r="48" fill="none" stroke="#102d42" stroke-width="19"/>',
    ])
    languages = language_counts.most_common(4)
    if languages:
        other = sum(language_counts.values()) - sum(count for _, count in languages)
        if other:
            languages.append(("Other", other))
    else:
        languages = [("JavaScript", 1), ("Other", 1)]
    total_langs = sum(count for _, count in languages)
    circumference = 2 * math.pi * 48
    offset = 0.0
    for index, (language, count) in enumerate(languages):
        length = circumference * count / total_langs
        color = LANGUAGE_COLORS[min(index, len(LANGUAGE_COLORS) - 1)]
        chunks.append(f'<circle cx="132" cy="548" r="48" fill="none" stroke="{color}" stroke-width="19" stroke-dasharray="{length:.2f} {circumference-length:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 132 548)"><title>{escape(language)}: {count} repositories</title></circle>')
        offset += length
    chunks.append(f'<text x="132" y="546" text-anchor="middle" fill="#effaff" font-family="Arial,sans-serif" font-size="19" font-weight="700">{repos}</text><text x="132" y="564" text-anchor="middle" fill="#9abccc" font-family="Arial,sans-serif" font-size="8" letter-spacing="1">REPOS</text>')
    for index, (language, count) in enumerate(languages):
        y = 520 + index * 21
        color = LANGUAGE_COLORS[min(index, len(LANGUAGE_COLORS) - 1)]
        chunks.append(f'<circle cx="215" cy="{y}" r="4" fill="{color}"/><text x="228" y="{y+4}" fill="#d9eff7" font-family="Arial,sans-serif" font-size="12">{escape(language)}</text><text x="410" y="{y+4}" text-anchor="end" fill="#a9c7d6" font-family="Arial,sans-serif" font-size="11">{count}</text>')

    # Activity radar panel.
    center_x, center_y, radius = 970, 285, 84
    labels = ["Commits", "Issues", "Pull req.", "Reviews", "Repos"]
    values = [commits, issues, pulls, reviews, repos]
    max_value = max(values + [1])
    angles = [-math.pi / 2 + i * (2 * math.pi / 5) for i in range(5)]
    chunks.extend([
        '<text x="808" y="145" fill="#91e9f5" font-family="Arial,sans-serif" font-size="10" font-weight="700" letter-spacing="2">ACTIVITY RADAR</text>',
    ])
    for fraction in (.25, .5, .75, 1):
        ring = [(center_x + radius * fraction * math.cos(a), center_y + radius * fraction * math.sin(a)) for a in angles]
        chunks.append(polygon(ring, "none", "#7294ad", 'stroke-dasharray="2 4" stroke-opacity=".52"'))
    for i, angle in enumerate(angles):
        ex, ey = center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)
        chunks.append(f'<path d="M{center_x:.1f},{center_y:.1f} L{ex:.1f},{ey:.1f}" stroke="#7395ae" stroke-opacity=".4" stroke-dasharray="2 4"/>')
        lx, ly = center_x + (radius + 19) * math.cos(angle), center_y + (radius + 19) * math.sin(angle)
        anchor = "middle" if i in (0, 2) else ("start" if math.cos(angle) > 0 else "end")
        chunks.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="{anchor}" fill="#c0d8e5" font-family="Arial,sans-serif" font-size="10">{labels[i]}</text>')
    radar = [(center_x + radius * max(.08, value / max_value) * math.cos(angle), center_y + radius * max(.08, value / max_value) * math.sin(angle)) for value, angle in zip(values, angles)]
    chunks.append(polygon(radar, "#36c7e5", "#7ceeff", 'fill-opacity=".35" stroke-width="2" filter="url(#glow)"'))
    for x, y in radar:
        chunks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#d6fbff"/>')

    chunks.extend([
        '<rect x="790" y="423" width="351" height="145" rx="17" fill="#0c2238" stroke="#2d7394" stroke-opacity=".65"/>',
        '<text x="812" y="453" fill="#91e9f5" font-family="Arial,sans-serif" font-size="10" font-weight="700" letter-spacing="2">BUILT FROM REAL ACTIVITY</text>',
        f'<text x="812" y="500" fill="#f1fbff" font-family="Arial,sans-serif" font-size="33" font-weight="700">{total:,}</text>',
        '<text x="813" y="523" fill="#a9c7d6" font-family="Arial,sans-serif" font-size="10" letter-spacing="1.2">CONTRIBUTIONS THIS YEAR</text>',
        f'<text x="1005" y="486" fill="#52e7f2" font-family="Arial,sans-serif" font-size="16" font-weight="700">{stars}</text>',
        '<text x="1028" y="486" fill="#b3cfdd" font-family="Arial,sans-serif" font-size="11">stars</text>',
        f'<text x="1005" y="516" fill="#52e7f2" font-family="Arial,sans-serif" font-size="16" font-weight="700">{forks}</text>',
        '<text x="1028" y="516" fill="#b3cfdd" font-family="Arial,sans-serif" font-size="11">forks</text>',
        '<path d="M32 596h1136" stroke="#8ed8ed" stroke-opacity=".14"/>',
        '<text x="34" y="623" fill="#8daabd" font-family="Arial,sans-serif" font-size="10">UPDATED DAILY FROM THE GITHUB CONTRIBUTION CALENDAR</text>',
        '<text x="1165" y="623" text-anchor="end" fill="#8daabd" font-family="Arial,sans-serif" font-size="10">SUDESHKUMARS • BUILD / LEARN / REPEAT</text>',
        '</svg>',
    ])
    return "".join(chunks)


def main() -> None:
    end = dt.datetime.now(dt.timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
    start = end - dt.timedelta(days=365)
    try:
        profile = fetch_profile(start, end)
    except Exception as error:
        print(f"GitHub data refresh failed: {error}")
        profile = None
    os.makedirs("dist", exist_ok=True)
    with open("dist/city.svg", "w", encoding="utf-8") as output:
        output.write(build_city(profile, start, end))


if __name__ == "__main__":
    main()
