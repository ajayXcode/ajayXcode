#!/usr/bin/env python3
"""
Scrape real daily contribution counts from GitHub's public contributions endpoint
and write data/contributions.json with raw days and derived metrics.
"""
import datetime
import json
import os
import re
import sys
import requests

USERNAME = os.environ.get("GH_PROFILE_USER", "ajayXcode")
URL = f"https://github.com/users/{USERNAME}/contributions"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "data", "contributions.json")


def fetch_days():
    resp = requests.get(URL, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=30)
    resp.raise_for_status()
    html = resp.text

    matches = re.findall(r'<td[^>]*class="[^"]*ContributionCalendar-day[^"]*"[^>]*>', html)
    if not matches:
        print("No contribution calendar cells found, using fallback/existing data.", file=sys.stderr)
        if os.path.exists(OUT_PATH):
            return json.load(open(OUT_PATH))["days"]
        sys.exit(1)

    days = []
    for m in matches:
        d_m = re.search(r'data-date="([^"]+)"', m)
        l_m = re.search(r'data-level="([^"]+)"', m)
        id_m = re.search(r'id="([^"]+)"', m)
        if d_m:
            date = d_m.group(1)
            level = int(l_m.group(1)) if l_m else 0
            cell_id = id_m.group(1) if id_m else ""
            
            count = 0
            if cell_id:
                tip_m = re.search(r'<tool-tip[^>]*for="' + re.escape(cell_id) + r'"[^>]*>(.*?)</tool-tip>', html, re.DOTALL)
                if tip_m:
                    text = tip_m.group(1).strip()
                    if "no contribution" not in text.lower():
                        cnt_m = re.search(r'(\d+)', text)
                        if cnt_m:
                            count = int(cnt_m.group(1))
            days.append({"date": date, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def compute_streaks(days):
    idx = len(days) - 1
    if days and days[idx]["count"] == 0:
        idx -= 1
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    cur = {
        "length": streak,
        "start": days[start_idx]["date"] if streak and start_idx < len(days) else None,
        "end": days[end_idx]["date"] if streak and end_idx >= 0 else None
    }

    longest = run = 0
    l_start = l_end = None
    r_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                r_start_idx = i
            run += 1
            if run > longest:
                longest = run
                l_start = days[r_start_idx]["date"]
                l_end = days[i]["date"]
        else:
            run = 0
    long_s = {"length": longest, "start": l_start, "end": l_end}
    return cur, long_s


def build_data(days):
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"]) if days else {"date": "", "count": 0}
    cur_streak, long_streak = compute_streaks(days)

    monthly = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]} if days else {},
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": cur_streak,
        "longest_streak": long_streak,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "days": days,
    }


if __name__ == "__main__":
    days = fetch_days()
    data = build_data(days)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT_PATH}: {data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, "
          f"longest streak {data['longest_streak']['length']}")
