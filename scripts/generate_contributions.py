#!/usr/bin/env python3
"""Render a GitHub contribution heatmap as a self-contained SVG."""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

USER = "sudeshkumars"
WIDTH, HEIGHT = 1160, 252
LEFT, TOP, CELL, GAP = 40, 88, 12, 6
STEP = CELL + GAP
COLS = 53


def fetch_calendar() -> tuple[int, list[list[dict]]]:
    end = dt.datetime.now(dt.timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
    start = end - dt.timedelta(days=365)
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{contributionCount date color}}}}}}"""
    payload = json.dumps({"query": query, "variables": {"login": USER, "from": start.isoformat(), "to": end.isoformat()}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json", "User-Agent": "profile-readme-assets"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return calendar["totalContributions"], calendar["weeks"]


def main() -> None:
    try:
        total, weeks = fetch_calendar()
        note = f"{total:,} contributions in the last year"
    except Exception as error:  # Keep the snake publishable if GitHub limits GraphQL.
        print(f"Contribution query unavailable: {error}")
        weeks = []
        note = "Contribution calendar refreshes daily"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Sudesh Kumar contribution activity</title>',
        f'<desc id="desc">{escape(note)} shown as a GitHub contribution heatmap.</desc>',
        '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#111522"/><stop offset="1" stop-color="#17152a"/></linearGradient><linearGradient id="accent"><stop stop-color="#ff69bd"/><stop offset="1" stop-color="#aa72ff"/></linearGradient><style>@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}.day{animation:rise .35s ease both}</style></defs>',
        '<rect x="1" y="1" width="1158" height="222" rx="24" fill="url(#bg)" stroke="#a969d766"/>',
        '<text x="34" y="39" fill="#b4a7c9" font-family="Arial,sans-serif" font-size="12" letter-spacing="2">CONTRIBUTION ACTIVITY</text>',
        f'<text x="34" y="68" fill="#f2eaff" font-family="Arial,sans-serif" font-size="19" font-weight="700">{escape(note)}</text>',
    ]

    first_date = None
    for column, week in enumerate(weeks[-COLS:]):
        days = week.get("contributionDays", [])
        if days and first_date is None:
            first_date = dt.date.fromisoformat(days[0]["date"])
        if days:
            date = dt.date.fromisoformat(days[0]["date"])
            if date.day <= 7:
                parts.append(f'<text x="{LEFT + column * STEP}" y="82" fill="#9b8eae" font-family="Arial,sans-serif" font-size="10">{date.strftime("%b")}</text>')
        for day in days:
            date = dt.date.fromisoformat(day["date"])
            row = date.weekday()
            count = day["contributionCount"]
            fill = day["color"] if count else "#242437"
            x, y = LEFT + column * STEP, TOP + row * STEP
            parts.append(f'<rect class="day" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{fill}" style="animation-delay:{min(column * .008, .4):.3f}s"><title>{date.isoformat()}: {count} contributions</title></rect>')

    if not weeks:
        parts.append('<text x="42" y="135" fill="#aa9db8" font-family="Arial,sans-serif" font-size="14">Contribution activity will appear after the first successful scheduled refresh.</text>')

    parts.append('<text x="1000" y="241" fill="#a99bb7" font-family="Arial,sans-serif" font-size="10">LESS</text>')
    for index, color in enumerate(("#242437", "#541f59", "#8a3379", "#cc4f9e", "#ff81c4")):
        parts.append(f'<rect x="1034" y="229" width="13" height="13" rx="3" fill="{color}"/>')
    parts.append('<text x="1120" y="241" fill="#a99bb7" font-family="Arial,sans-serif" font-size="10">MORE</text></svg>')

    os.makedirs("dist", exist_ok=True)
    with open("dist/contributions.svg", "w", encoding="utf-8") as output:
        output.write("".join(parts))


if __name__ == "__main__":
    main()
