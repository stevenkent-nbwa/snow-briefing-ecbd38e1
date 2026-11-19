#!/usr/bin/env python3
"""Rebuild feed.xml for the Daily Snow Briefing podcast.

Usage: python3 make_feed.py <repo_dir> <base_url> [audio|video]
  repo_dir : local clone of the GitHub Pages repo
  base_url : e.g. https://OWNER.github.io/REPO   (no trailing slash)

Episodes are the MP3 (or MP4 with "video") files in <repo_dir>/episodes/, named
"YYYY-MM-DD.mp3" (Snow Briefing) or "YYYY-MM-DD-avalanche.mp4" (weekly NWAC Avalanche Briefing). An optional "YYYY-MM-DD.txt" next to each holds the
episode description (first line is used as the title suffix).
"""
import os, sys, subprocess, datetime, html
from email.utils import format_datetime
from zoneinfo import ZoneInfo

repo, base = sys.argv[1], sys.argv[2].rstrip("/")
KIND = sys.argv[3] if len(sys.argv) > 3 else "audio"
EXT, MIME, FEED, SUFFIX = (".mp4", "video/mp4", "feed-video.xml", " (Video)") if KIND == "video" else (".mp3", "audio/mpeg", "feed.xml", "")
ep_dir = os.path.join(repo, "episodes")
os.makedirs(ep_dir, exist_ok=True)
pt = ZoneInfo("America/Los_Angeles")

def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    s = int(float(out or 0))
    return f"{s//60}:{s%60:02d}"

items = []
for f in sorted(os.listdir(ep_dir), reverse=True):
    if not f.endswith(EXT):
        continue
    day = f[:-4]  # "YYYY-MM-DD" (Snow Briefing) or "YYYY-MM-DD-avalanche" (Avalanche Briefing)
    show = "avalanche" if day.endswith("-avalanche") else ""
    try:
        d = datetime.datetime.strptime(day[:10], "%Y-%m-%d").replace(hour=10 if show else 9, minute=30, tzinfo=pt)
    except ValueError:
        continue
    path = os.path.join(ep_dir, f)
    txt = os.path.join(ep_dir, day + ".txt")
    desc = open(txt).read().strip() if os.path.exists(txt) else "Daily snow forecast summary."
    headline = desc.splitlines()[0][:120] if desc else ""
    title = ("Avalanche · " if show else "") + d.strftime("%a %b %-d") + (f": {headline}" if headline else "")
    items.append(f"""    <item>
      <title>{html.escape(title)}</title>
      <description>{html.escape(desc)}</description>
      <guid isPermaLink="false">daily-snow-{KIND}-{day}</guid>
      <pubDate>{format_datetime(d)}</pubDate>
      <enclosure url="{base}/episodes/{f}" length="{os.path.getsize(path)}" type="{MIME}"/>
      <itunes:duration>{duration(path)}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

now = format_datetime(datetime.datetime.now(pt))
feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Daily Snow Briefing{SUFFIX}</title>
    <link>{base}/</link>
    <description>Private snow forecast briefings for the Pacific Northwest and northern Rockies, plus a weekly NWAC avalanche briefing.</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>Daily Snow Briefing</itunes:author>
    <itunes:image href="{base}/cover.jpg"/>
    <itunes:category text="Sports"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""
open(os.path.join(repo, FEED), "w").write(feed)
# keep crawlers out of the site
open(os.path.join(repo, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
print(f"{FEED} written with {len(items)} episode(s)")
