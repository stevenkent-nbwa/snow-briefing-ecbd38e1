# Daily Snow Briefing

Private podcast feeds for Steven's daily snow forecast summary.

- Audio feed: https://stevenkent-nbwa.github.io/snow-briefing-ecbd38e1/feed.xml
- Video feed: https://stevenkent-nbwa.github.io/snow-briefing-ecbd38e1/feed-video.xml

`tools/daily_video.py` builds each Snow Briefing MP4; `tools/avy_video.py` (with `tools/nwac_zones.json`) builds the weekly NWAC Avalanche Briefing (`episodes/YYYY-MM-DD-avalanche.mp4`); `tools/make_feed.py` rebuilds the feeds from `episodes/`.
Episodes are cleared every Tuesday.
