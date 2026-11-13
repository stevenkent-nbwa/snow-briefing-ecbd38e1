#!/usr/bin/env python3
"""Daily Snow Briefing: builds MP4 + MP3 from spec.json. Usage: python3 daily_video.py spec.json out_basename"""
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon, FancyBboxPatch, Rectangle
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as pe
from kokoro_onnx import Kokoro

for f in ["Inter-Regular.otf", "Inter-SemiBold.otf", "Inter-Bold.otf"]:
    p = f"/usr/share/fonts/opentype/inter/{f}"
    if os.path.exists(p): fm.fontManager.addfont(p); plt.rcParams["font.family"] = "Inter"
SPEC = json.load(open(sys.argv[1])); BASE = sys.argv[2]
W, H, PT, FPS = 1920, 1080, 0.72, 30
VOICE, SPEED = "am_echo", 1.25
FIX = {"Snoqualmie": "snoʊkwˈɔːlmi", "Alpental": "ˈælpəntˌɑːl", "Hoodoo": "hˈuːduː", "Schweitzer": "ʃwˈaɪtsɚ", "Yukon": "jˈuːkɑːn"}
BG, PANEL, OCEAN, LAND, FOCUS, EDGE = "#0e2238", "#16324f", "#0b1c2e", "#2a3f55", "#3e5b7a", "#6f8aa6"
TEXT, MUTED, ACCENT, INDY, BOYNE, DARK = "#ffffff", "#b4c6d8", "#7fd3ff", "#ffb547", "#6ee7a8", "#0e2238"
PC = {"indy": INDY, "boyne": BOYNE, "other": TEXT}
REG = {"WA": ("Washington", (-124.9, -116.6, 45.5, 49.15), [["indy"], ["boyne"], ["other"]]),
       "OR": ("Oregon", (-124.8, -116.3, 41.8, 46.35), [["indy"], ["other"]]),
       "ID": ("Idaho", (-121.5, -107.3, 41.7, 49.1), [["indy"], ["other"]]),
       "BC": ("British Columbia", (-127.8, -115.0, 48.35, 51.95), [["indy"], ["boyne"], ["other"]]),
       "MT": ("Montana", (-118.6, -103.6, 44.3, 49.1), [["indy"], ["boyne", "other"]])}
L, R_, UP, DN = (-1, 0, "right"), (1, 0, "left"), (0, 1.25, "center"), (0, -1.2, "center")
# name: (lat, lon, pass, label side). Positions are nudged apart for legibility. lat None = listed in a corner note.
RES = {"WA": {"Hurricane Ridge": (47.97, -123.5, "indy", UP), "White Pass": (46.64, -121.39, "indy", L), "Bluewood": (46.08, -117.85, "indy", L),
              "49 North": (48.3, -117.56, "indy", L), "Loup Loup": (48.39, -119.9, "indy", UP), "Snoqualmie": (47.27, -121.41, "boyne", R_),
              "Alpental": (47.6, -121.43, "boyne", R_), "Crystal": (46.94, -121.48, "other", L), "Mt. Baker": (48.86, -121.67, "other", R_),
              "Stevens Pass": (47.93, -120.95, "other", R_)},
       "OR": {"Mt. Hood Meadows": (45.3, -121.5, "indy", R_), "Cooper Spur": (45.72, -121.5, "indy", R_), "Hoodoo": (44.41, -121.87, "indy", R_),
              "Timberline": (45.3, -122.12, "other", L), "Mt. Bachelor": (43.98, -121.69, "other", R_), "Willamette Pass": (43.6, -122.03, "other", L),
              "Mt. Ashland": (42.08, -122.72, "other", R_), "Anthony Lakes": (44.96, -118.23, "other", L)},
       "ID": {"Brundage": (45.22, -116.16, "indy", L), "Tamarack": (44.56, -116.12, "indy", L), "Pomerelle": (42.32, -113.6, "indy", R_),
              "Silver Mtn": (47.45, -116.3, "indy", L), "Magic Mtn": (42.15, -114.75, "indy", L), "Pebble Creek": (42.77, -112.11, "indy", R_),
              "Soldier Mtn": (43.2, -115.1, "indy", DN), "Kelly Canyon": (43.64, -111.62, "indy", R_), "Sun Valley": (43.9, -114.15, "other", UP),
              "Bogus Basin": (43.85, -116.3, "other", L), "Schweitzer": (48.37, -116.62, "other", L), "Lookout Pass": (47.46, -115.05, "other", R_)},
       "BC": {"Mt. Cain": (50.23, -126.36, "indy", UP), "Mt. Washington": (49.74, -125.3, "indy", DN), "Sasquatch": (49.45, -121.93, "indy", UP),
              "Manning Park": (49.07, -120.95, "indy", DN), "Big White": (49.78, -118.93, "indy", R_), "Baldy": (49.15, -119.24, "indy", R_),
              "Apex": (49.42, -119.95, "indy", UP), "Shames": (None, None, "indy", R_), "Hudson Bay": (None, None, "indy", R_),
              "Cypress": (49.4, -123.2, "boyne", DN), "Whistler": (50.12, -122.95, "other", R_), "Revelstoke": (50.96, -118.16, "other", L),
              "Kicking Horse": (51.3, -117.05, "other", L)},
       "MT": {"Lost Trail": (45.69, -113.95, "indy", L), "Montana Snowbowl": (47.01, -114.0, "indy", L), "Red Lodge": (45.19, -109.34, "indy", R_),
              "Showdown": (46.86, -110.7, "indy", R_), "Big Sky": (45.29, -111.4, "boyne", DN), "Lookout Pass": (47.6, -115.7, "other", L),
              "Whitefish": (48.48, -114.36, "other", R_), "Bridger Bowl": (45.85, -110.9, "other", R_)}}
TOT = SPEC["totals"]
FEATS = [f for f in json.load(open("states.geojson"))["features"] if f["properties"].get("iso_a2") in ("US", "CA")]

def sc(v): return "#ffffff" if v >= 10 else "#7fd3ff" if v >= 5 else "#4a90c8" if v >= 1 else "#6b7c8f"
def fig_(): f = plt.figure(figsize=(W / 100, H / 100), dpi=100); f.patch.set_facecolor(BG); return f
def px(f, x, y, w, h): return f.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
def T(f, x, y, s, size, color=TEXT, weight="regular", ha="left", va="top", **kw):
    return f.text(x / W, 1 - y / H, s, fontsize=size * PT, color=color, fontweight=weight, ha=ha, va=va, **kw)
def box(f, x, y, w, h, color, a=1.0, r=0.012):
    f.patches.append(FancyBboxPatch((x / W, 1 - (y + h) / H), w / W, h / H, boxstyle=f"round,pad=0,rounding_size={r}", transform=f.transFigure, facecolor=color, edgecolor="none", alpha=a))
def bar(f, x, y, w, h, color, a=1.0): f.patches.append(Rectangle((x / W, 1 - (y + h) / H), w / W, h / H, transform=f.transFigure, facecolor=color, alpha=a))
def header(f, kicker, headline):
    T(f, 60, 30, kicker.upper(), 40, ACCENT, "bold"); T(f, W - 60, 32, SPEC["date_short"], 36, MUTED, ha="right"); T(f, 60, 82, headline, 66, TEXT, "bold")
def footer(f, src, cur):
    if src: T(f, 60, H - 20, src, 27, MUTED, va="bottom")
    x = W - 60 - 5 * 96
    for r in REG:
        if r == cur: box(f, x, H - 62, 84, 46, ACCENT, r=0.008)
        T(f, x + 42, H - 22, r, 30, DARK if r == cur else MUTED, "bold", ha="center", va="bottom"); x += 96
def save(f, path): f.savefig(path, facecolor=f.get_facecolor()); plt.close(f)

def s_title(s, step, path):
    f = fig_(); ax = px(f, 0, 0, W, H); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), extent=[0, W, H, 0], aspect="auto", cmap=matplotlib.colors.LinearSegmentedColormap.from_list("g", ["#0e2238", "#3c6e9e"]))
    ax.add_patch(Polygon([(0, 820), (260, 600), (470, 720), (720, 480), (980, 690), (1220, 540), (1500, 700), (1920, 520), (1920, 1080), (0, 1080)], closed=True, facecolor="#7aa2c8"))
    ax.add_patch(Polygon([(0, 930), (360, 640), (620, 830), (920, 590), (1240, 860), (1520, 700), (1920, 840), (1920, 1080), (0, 1080)], closed=True, facecolor="#eaf1f9"))
    T(f, W / 2, 120, "DAILY SNOW BRIEFING", 54, ACCENT, "bold", ha="center"); T(f, W / 2, 205, SPEC["date_long"], 104, TEXT, "bold", ha="center")
    T(f, W / 2, 920, "WA · OR · ID · BC · MT", 64, "#1d3a5c", "bold", ha="center"); save(f, path)

def s_board(s, step, path):
    rows = [(n, r, v, RES[r][n][2]) for r in TOT for n, v in TOT[r].items() if n in RES[r]]
    indy = sorted([x for x in rows if x[3] == "indy"], key=lambda x: -x[2])[:8]
    boyne = sorted([x for x in rows if x[3] == "boyne"], key=lambda x: -x[2])[:4]
    f = fig_(); header(f, "Your passes", "Snow in the next 5 days"); a2 = 1.0 if step >= 1 else 0.25
    box(f, 60, 200, 1130, 810, PANEL); box(f, 1230, 200, 630, 810, PANEL)
    T(f, 100, 222, "INDY PASS", 42, INDY, "bold"); T(f, 1270, 222, "BOYNE", 42, BOYNE, "bold", alpha=a2)
    mx = max([x[2] for x in indy] + [1]); y = 300
    for n, r, v, _ in indy:
        T(f, 100, y + 40, n, 42, TEXT, "bold", va="center"); T(f, 560, y + 40, r, 32, MUTED, "bold", va="center")
        bw = max(400 * v / mx, 4); bar(f, 640, y + 18, bw, 44, INDY); T(f, 640 + bw + 18, y + 40, f"{v}″", 46, TEXT, "bold", va="center"); y += 86
    y = 310
    for n, r, v, _ in boyne:
        T(f, 1270, y + 50, n, 46, TEXT, "bold", va="center", alpha=a2); T(f, 1630, y + 50, r, 32, MUTED, "bold", va="center", alpha=a2)
        T(f, 1820, y + 50, f"{v}″", 64, BOYNE, "bold", va="center", ha="right", alpha=a2); y += 160
    save(f, path)

def s_map(s, step, path):
    reg = s["region"]; name, bbox, order = REG[reg]; hl = order[min(step, len(order) - 1)]
    f = fig_(); header(f, name, s["headline"]); cx = 60
    for key, lab in [("indy", "Indy Pass"), ("boyne", "Boyne"), ("other", "Other")]:
        a = 1.0 if key in hl else 0.35; box(f, cx, 186, 26, 26, PC[key], a, 0.004); T(f, cx + 38, 178, lab, 36, PC[key], "bold", alpha=a); cx += 78 + len(lab) * 20
    T(f, W - 60, 180, "Inches of snow, next 5 days", 34, MUTED, "semibold", ha="right")
    ax = px(f, 30, 236, W - 60, 770); lon0, lon1, lat0, lat1 = bbox; k = math.cos(math.radians((lat0 + lat1) / 2)); ax.set_facecolor(OCEAN)
    bg, fg = [], []
    for ft in FEATS:
        g = ft["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            ring = poly[0]; xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            if max(xs) < lon0 - 3 or min(xs) > lon1 + 3 or max(ys) < lat0 - 3 or min(ys) > lat1 + 3: continue
            (fg if ft["properties"]["name"] == name else bg).append(Polygon([(p[0] * k, p[1]) for p in ring], closed=True))
    ax.add_collection(PatchCollection(bg, facecolor=LAND, edgecolor=EDGE, linewidth=1)); ax.add_collection(PatchCollection(fg, facecolor=FOCUS, edgecolor="#c9dcef", linewidth=2.5))
    ax.set_xlim(lon0 * k, lon1 * k); ax.set_ylim(lat0, lat1); ax.set_aspect("equal"); ax.axis("off")
    pins = [(n, v) + RES[reg][n] for n, v in TOT.get(reg, {}).items() if n in RES[reg]]
    for n, v, lat, lon, ps, (dx, dy, ha) in sorted([p for p in pins if p[2] is not None], key=lambda p: p[4] in hl):
        on = ps in hl; a = 1.0 if on else 0.3; d = 42 + min(v, 24)
        ax.scatter([lon * k], [lat], s=d * d, color=sc(v), edgecolors=(PC[ps] if ps != "other" else "#dfe9f3"), linewidths=(4.5 if ps != "other" else 2), alpha=a, zorder=5 + on)
        ax.annotate(str(v), (lon * k, lat), ha="center", va="center", fontsize=30 * PT, fontweight="bold", color=(DARK if v >= 5 else TEXT), alpha=a, zorder=7 + on)
        t = ax.annotate(n, (lon * k, lat), xytext=(dx * (30 + d / 2) if dy == 0 else dx * 20, dy * 34), textcoords="offset points", fontsize=33 * PT,
                        color=PC[ps], fontweight="bold", ha=ha, va="center", alpha=a, zorder=8 + on)
        t.set_path_effects([pe.withStroke(linewidth=6, foreground=OCEAN, alpha=a)])
    far = [f"{n} {v}″" for n, v, lat, *_ in pins if lat is None]
    if far:
        a = 1.0 if "indy" in hl else 0.35; box(f, 50, 840, 560, 150, PANEL, r=0.01)
        T(f, 75, 852, "Farther north, Indy Pass", 30, MUTED, "semibold", alpha=a); T(f, 75, 900, " · ".join(far), 38, INDY, "bold", alpha=a)
    footer(f, s.get("source", ""), reg); save(f, path)

def s_cards(s, step, path):
    f = fig_(); header(f, REG[s["region"]][0], s["headline"]); y = 215
    for i, (when, title, sub) in enumerate(s["rows"][:3]):
        on = (i == step); a = 1.0 if on else 0.3
        box(f, 60, y, 1800, 240, "#1f4a73" if on else PANEL); bar(f, 60, y, 16, 240, ACCENT, a)
        T(f, 120, y + 120, when, 52, ACCENT, "bold", va="center", alpha=a); T(f, 640, y + 40, title, 58, TEXT, "bold", alpha=a); T(f, 640, y + 138, sub, 46, TEXT, alpha=a); y += 262
    footer(f, s.get("source", ""), s["region"]); save(f, path)

def s_bottom(s, step, path):
    f = fig_(); T(f, W / 2, 50, "BOTTOM LINE", 60, ACCENT, "bold", ha="center"); y = 165; rows = s["rows"][:4]
    for i, (lab, text, kind) in enumerate(rows):
        allon = step >= len(rows); a = 1.0 if (allon or step == i) else 0.3; col = {"indy": INDY, "boyne": BOYNE, "muted": "#9fb3c8"}.get(kind, TEXT)
        box(f, 60, y, 1800, 195, "#1f4a73" if (a == 1 and not allon) else PANEL); bar(f, 60, y, 16, 195, col, a)
        T(f, 120, y + 22, lab, 50, col, "bold", alpha=a); T(f, 120, y + 100, text, 54, TEXT, "bold", alpha=a); y += 220
    save(f, path)

DRAW = {"title": s_title, "board": s_board, "map": s_map, "cards": s_cards, "bottom": s_bottom}
os.makedirs("work", exist_ok=True)
K = Kokoro("kokoro.onnx", "voices.bin"); SR = 24000
def say(text):
    ph = K.tokenizer.phonemize(text, "en-us")
    for w, ipa in FIX.items():
        if w in text: ph = ph.replace(K.tokenizer.phonemize(w, "en-us").rstrip("."), ipa)
    return K.create(ph, voice=VOICE, speed=SPEED, is_phonemes=True)[0]
sil = lambda t: np.zeros(int(t * SR), dtype=np.float32)
t = np.arange(int(1.1 * SR)) / SR; t2 = np.clip(t - 0.16, 0, None)
chime = (0.10 * np.sin(2 * np.pi * 659.25 * t) * np.exp(-3.5 * t) + 0.08 * np.sin(2 * np.pi * 987.77 * t2) * np.exp(-3.5 * t2) * (t > 0.16)).astype(np.float32)
audio, lst = [], []
for si, s in enumerate(SPEC["scenes"]):
    parts, bounds = [], []
    for i, sents in enumerate(s["say"]):
        seg = [sil(0.85 if si == 0 else 0.35)] if i == 0 else []
        for x in sents: seg += [say(x), sil(0.22)]
        if i == len(s["say"]) - 1: seg.append(sil(0.45))
        parts.append(np.concatenate(seg)); bounds.append(sum(len(p) for p in parts))
    fb = [round(b / SR * FPS) for b in bounds]; fb[-1] = math.ceil(bounds[-1] / SR * FPS)
    a = np.concatenate(parts); a = np.concatenate([a, np.zeros(max(0, round(fb[-1] / FPS * SR) - len(a)), dtype=np.float32)])
    if si == 0: a[:len(chime)] += chime
    audio.append(a); prev = 0
    for i, fe in enumerate(fb):
        n = fe - prev; prev = fe
        if n <= 0: continue
        png = f"work/s{si:02d}_{i}.png"; DRAW[s["type"]](s, i, png)
        vf = f"format=yuv420p,loop=-1:1,trim=end_frame={n}"
        if i == 0: vf += ",fade=t=in:st=0:d=0.25:color=0x0e2238"
        if i == len(fb) - 1: vf += f",fade=t=out:st={n / FPS - 0.25:.3f}:d=0.25:color=0x0e2238"
        out = f"work/s{si:02d}_{i}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", png, "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-crf", "20",
                        "-preset", "veryfast", "-pix_fmt", "yuv420p", out + ".tmp.mp4"], check=True)
        os.replace(out + ".tmp.mp4", out); lst.append(f"file '{os.path.abspath(out)}'")
    print(si, s["type"], f"{fb[-1] / FPS:.1f}s", flush=True)
sf.write("work/nar.wav", np.concatenate(audio), SR); open("work/list.txt", "w").write("\n".join(lst) + "\n")
AF = "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=11"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "work/list.txt", "-c", "copy", "work/v.mp4"], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "work/v.mp4", "-i", "work/nar.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", AF, "-ar", "48000",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", BASE + ".tmp.mp4"], check=True)
os.replace(BASE + ".tmp.mp4", BASE + ".mp4")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "work/nar.wav", "-af", AF, "-ar", "44100", "-ac", "1", "-b:a", "64k", BASE + ".mp3"], check=True)
print("done")
