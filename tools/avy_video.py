#!/usr/bin/env python3
"""Avalanche Briefing (NWAC, Snoqualmie Pass focus): builds an MP4 from spec.json.
Usage: python3 avy_video.py spec.json out_basename
Needs in the working folder: kokoro.onnx, voices.bin, states.geojson, nwac_zones.json.
Same look, voice and audio pipeline as daily_video.py (the Snow Briefing).

Spec keys: date_long, date_short, zones {zone: {"today": [above, near, below] or null,
"tomorrow": [...] or null}}, scenes [...]. Danger numbers: 1 Low .. 5 Extreme, null = no rating.
Scene types: title, overview, danger, problems, cards, zones, bottom (see the task prompt)."""
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon, FancyBboxPatch, Rectangle, Wedge, Circle
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as pe
from kokoro_onnx import Kokoro

for f in ["Inter-Regular.otf", "Inter-SemiBold.otf", "Inter-Bold.otf"]:
    p = f"/usr/share/fonts/opentype/inter/{f}"
    if os.path.exists(p): fm.fontManager.addfont(p); plt.rcParams["font.family"] = "Inter"
SPEC = json.load(open(sys.argv[1])); BASE = sys.argv[2]
W, H, PT, FPS = 1920, 1080, 0.72, 30
VOICE, SPEED = "am_echo", 1.25
FIX = {"Snoqualmie": "snoʊkwˈɔːlmi", "Alpental": "ˈælpəntˌɑːl", "Chelan": "ʃəlˈæn", "Tieton": "tˈaɪətən",
       "Teanaway": "tiːˈænəweɪ", "Leavenworth": "lˈɛvənwɜːθ", "Wenatchee": "wənˈæʧi"}
BG, PANEL, OCEAN, LAND, EDGE = "#0e2238", "#16324f", "#0b1c2e", "#2a3f55", "#6f8aa6"
TEXT, MUTED, ACCENT, DARK, HI = "#ffffff", "#b4c6d8", "#7fd3ff", "#0e2238", "#1f4a73"
# North American Avalanche Danger Scale colors
DCOL = {None: "#5d6d7e", 1: "#50b848", 2: "#fff200", 3: "#f7941e", 4: "#ed1c24", 5: "#231f20"}
DNAME = {None: "No rating", 1: "Low", 2: "Moderate", 3: "Considerable", 4: "High", 5: "Extreme"}
def dtext(d): return DARK if d in (1, 2, 3) else TEXT
ORDER = ["Olympics", "West Slopes North", "West Slopes Central", "Stevens Pass", "Snoqualmie Pass",
         "West Slopes South", "East Slopes North", "East Slopes Central", "East Slopes South", "Mt Hood"]
FOCUS = "Snoqualmie Pass"
BADGE = {"Snoqualmie Pass": (-122.2, 47.22), "Stevens Pass": (-122.0, 47.8), "East Slopes Central": (-120.5, 47.45)}  # badges moved off small zones
ZONES = SPEC.get("zones", {})
ZPOLY = json.load(open("nwac_zones.json"))
FEATS = [f for f in json.load(open("states.geojson"))["features"] if f["properties"].get("iso_a2") in ("US", "CA")]

def zmax(z, day="today"):
    v = (ZONES.get(z) or {}).get(day)
    v = [x for x in (v or []) if x]
    return max(v) if v else None
def fig_(): f = plt.figure(figsize=(W / 100, H / 100), dpi=100); f.patch.set_facecolor(BG); return f
def px(f, x, y, w, h): return f.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
def T(f, x, y, s, size, color=TEXT, weight="regular", ha="left", va="top", **kw):
    return f.text(x / W, 1 - y / H, s, fontsize=size * PT, color=color, fontweight=weight, ha=ha, va=va, **kw)
def box(f, x, y, w, h, color, a=1.0, r=0.012, ec="none", lw=0):
    f.patches.append(FancyBboxPatch((x / W, 1 - (y + h) / H), w / W, h / H, boxstyle=f"round,pad=0,rounding_size={r}", transform=f.transFigure,
                                    facecolor=color, edgecolor=ec, linewidth=lw, alpha=a))
def bar(f, x, y, w, h, color, a=1.0): f.patches.append(Rectangle((x / W, 1 - (y + h) / H), w / W, h / H, transform=f.transFigure, facecolor=color, alpha=a))
def header(f, kicker, headline):
    T(f, 60, 30, kicker.upper(), 40, ACCENT, "bold"); T(f, W - 60, 32, SPEC["date_short"], 36, MUTED, ha="right"); T(f, 60, 82, headline, 66, TEXT, "bold")
def footer(f, src):
    if src: T(f, 60, H - 20, src, 27, MUTED, va="bottom")
    T(f, W - 60, H - 20, "Read the full forecast at nwac.us", 27, MUTED, "semibold", ha="right", va="bottom")
def chip(f, x, y, w, h, d, label=None, size=34, a=1.0):
    box(f, x, y, w, h, DCOL[d], a, 0.008, ec=("#ed1c24" if d == 5 else "none"), lw=(3 if d == 5 else 0))
    T(f, x + w / 2, y + h / 2, label if label is not None else DNAME[d], size, dtext(d), "bold", ha="center", va="center", alpha=a)
def save(f, path): f.savefig(path, facecolor=f.get_facecolor()); plt.close(f)

def s_title(s, step, path):
    f = fig_(); ax = px(f, 0, 0, W, H); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), extent=[0, W, H, 0], aspect="auto", cmap=matplotlib.colors.LinearSegmentedColormap.from_list("g", ["#0e2238", "#3c6e9e"]))
    ax.add_patch(Polygon([(0, 860), (300, 600), (560, 720), (960, 470), (1260, 680), (1500, 560), (1920, 760), (1920, 1080), (0, 1080)], closed=True, facecolor="#7aa2c8"))
    ax.add_patch(Polygon([(780, 620), (960, 470), (1140, 610), (1040, 590), (960, 560), (870, 620)], closed=True, facecolor="#eaf1f9"))
    ax.add_patch(Polygon([(0, 960), (420, 700), (700, 860), (1000, 640), (1300, 880), (1600, 760), (1920, 900), (1920, 1080), (0, 1080)], closed=True, facecolor="#dfe9f3"))
    T(f, W / 2, 110, "AVALANCHE BRIEFING", 54, ACCENT, "bold", ha="center"); T(f, W / 2, 195, SPEC["date_long"], 104, TEXT, "bold", ha="center")
    T(f, W / 2, 345, "Northwest Avalanche Center", 50, MUTED, "semibold", ha="center")
    T(f, W / 2, 950, "Snoqualmie Pass focus", 64, "#1d3a5c", "bold", ha="center"); save(f, path)

def draw_map(f, x, y, w, h, hl):
    ax = px(f, x, y, w, h); lon0, lon1, lat0, lat1 = -124.3, -119.5, 45.05, 49.15; k = math.cos(math.radians(47.1))
    ax.set_facecolor(OCEAN); bg = []
    for ft in FEATS:
        g = ft["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            ring = poly[0]; xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
            if max(xs) < lon0 - 3 or min(xs) > lon1 + 3 or max(ys) < lat0 - 3 or min(ys) > lat1 + 3: continue
            bg.append(Polygon([(p[0] * k, p[1]) for p in ring], closed=True))
    ax.add_collection(PatchCollection(bg, facecolor=LAND, edgecolor=EDGE, linewidth=1))
    for i, z in enumerate(ORDER):
        ring = ZPOLY[z]; d = zmax(z); on = z in hl
        ax.add_patch(Polygon([(p[0] * k, p[1]) for p in ring], closed=True, facecolor=DCOL[d], edgecolor=("#ffffff" if z == FOCUS else "#0e2238"),
                             linewidth=(5 if z == FOCUS else 1.5), alpha=(1.0 if on else 0.35), zorder=(4 if z == FOCUS else 3)))
        cx = sum(p[0] for p in ring[:-1]) / (len(ring) - 1); cy = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
        if z in BADGE:
            bx, by = BADGE[z]; ax.plot([cx * k, bx * k], [cy, by], color="#ffffff", linewidth=2.5, zorder=5, alpha=(1.0 if on else 0.45)); cx, cy = bx, by
        ax.scatter([cx * k], [cy], s=1500, color="#0e2238", edgecolors="#ffffff", linewidths=2, zorder=6, alpha=(1.0 if on else 0.45))
        ax.annotate(str(i + 1), (cx * k, cy), ha="center", va="center", fontsize=28 * PT, fontweight="bold", color=TEXT, zorder=7, alpha=(1.0 if on else 0.45))
    for name, lo, la in [("Seattle", -122.33, 47.61), ("Portland", -122.68, 45.52)]:
        ax.scatter([lo * k], [la], s=90, color=MUTED, zorder=5)
        t = ax.annotate(name, (lo * k, la), xytext=(-12, 0), textcoords="offset points", ha="right", va="center", fontsize=28 * PT, color=MUTED, fontweight="semibold", zorder=5)
        t.set_path_effects([pe.withStroke(linewidth=5, foreground=OCEAN)])
    ax.set_xlim(lon0 * k, lon1 * k); ax.set_ylim(lat0, lat1); ax.set_aspect("equal"); ax.axis("off")

def s_overview(s, step, path):
    hl = s.get("groups", [ORDER])[min(step, len(s.get("groups", [ORDER])) - 1)]
    f = fig_(); header(f, "NWAC zones · today", s["headline"]); draw_map(f, 30, 190, 700, 820, hl)
    T(f, 790, 192, "Highest danger today", 34, MUTED, "semibold"); y = 245
    for i, z in enumerate(ORDER):
        on = z in hl; a = 1.0 if on else 0.3; d = zmax(z)
        if z == FOCUS: box(f, 772, y - 6, 1110, 76, HI, a)
        T(f, 800, y + 32, str(i + 1), 38, MUTED, "bold", va="center", alpha=a); T(f, 860, y + 32, z, 42, TEXT, "bold", va="center", alpha=a)
        chip(f, 1450, y + 4, 410, 56, d, size=34, a=a); y += 76
    footer(f, s.get("source", "")); save(f, path)

def triangle(f, x, y, w, h, bands, title, a):
    """Mountain triangle: bands = [above, near, below] treeline danger."""
    T(f, x + w / 2, y, title, 50, ACCENT, "bold", ha="center", alpha=a)
    ax = px(f, x, y + 70, w, h); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    bands = bands or [None, None, None]; cuts = [1.0, 0.64, 0.33, 0.0]
    for i, d in enumerate(bands):
        t, b = cuts[i], cuts[i + 1]; ht, hb = (1 - t) / 2, (1 - b) / 2
        ax.add_patch(Polygon([(0.5 - (0.5 - hb) * 1, b), (0.5 + (0.5 - hb), b), (0.5 + (0.5 - ht), t), (0.5 - (0.5 - ht), t)], closed=True,
                             facecolor=DCOL[d], edgecolor=("#ed1c24" if d == 5 else BG), linewidth=4, alpha=a))
    labels = ["Above treeline", "Near treeline", "Below treeline"]
    for i, d in enumerate(bands):
        yy = y + 70 + h * (1 - (cuts[i] + cuts[i + 1]) / 2)
        T(f, x + w + 30, yy - 22, labels[i], 32, MUTED, "semibold", va="center", alpha=a)
        T(f, x + w + 30, yy + 22, (f"{d} · " if d else "") + DNAME[d], 42, (DCOL[d] if d and d != 5 else TEXT), "bold", va="center", alpha=a)

def s_danger(s, step, path):
    z = ZONES.get(FOCUS, {}); f = fig_(); header(f, "Snoqualmie Pass", s["headline"])
    triangle(f, 110, 200, 430, 520, z.get("today"), s.get("today_label", "Today"), 1.0 if step == 0 else 0.35)
    triangle(f, 1010, 200, 430, 520, z.get("tomorrow"), s.get("tomorrow_label", "Tomorrow"), 1.0 if step >= 1 else 0.35)
    if s.get("note"):
        box(f, 60, 830, 1800, 170, PANEL); bar(f, 60, 830, 16, 170, ACCENT)
        T(f, 110, 850, s.get("note_title", "Travel advice"), 36, ACCENT, "bold"); T(f, 110, 905, s["note"], 44, TEXT, "bold", wrap=False)
    footer(f, s.get("source", "")); save(f, path)

ASP = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
LIKE = ["unlikely", "possible", "likely", "very likely", "almost certain"]
def rose(f, x, y, size, locs, a=1.0):
    ax = px(f, x, y, size, size); ax.set_zorder(3); ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.25, 1.25); ax.set_aspect("equal"); ax.axis("off")
    locs = {l.lower() for l in locs}; rings = [("upper", 0.0, 0.36), ("middle", 0.36, 0.68), ("lower", 0.68, 1.0)]
    for i, asp in enumerate(ASP):
        c = 90 - i * 45
        for el, r0, r1 in rings:
            on = f"{asp} {el}" in locs
            ax.add_patch(Wedge((0, 0), r1, c - 22.5, c + 22.5, width=r1 - r0, facecolor=(ACCENT if on else "#2a4664"), edgecolor=BG, linewidth=3, alpha=a))
    for i, lab in enumerate(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]):
        ang = math.radians(90 - i * 45); ax.text(1.14 * math.cos(ang), 1.14 * math.sin(ang), lab, ha="center", va="center", fontsize=30 * PT, color=MUTED, fontweight="bold", alpha=a)

def s_problems(s, step, path):
    probs = s["problems"]; p = probs[min(step, len(probs) - 1)]; f = fig_()
    header(f, f"Snoqualmie Pass · problem {min(step, len(probs) - 1) + 1} of {len(probs)}", p["name"])
    box(f, 60, 200, 760, 800, PANEL); rose(f, 100, 230, 680, p.get("location", []))
    T(f, 440, 935, "Center = above treeline · outer = below", 28, MUTED, "semibold", ha="center")
    box(f, 860, 200, 1000, 800, PANEL); T(f, 900, 225, "LIKELIHOOD", 36, MUTED, "bold")
    li = LIKE.index(p.get("likelihood", "possible").lower()) if p.get("likelihood", "possible").lower() in LIKE else 1
    for i, lab in enumerate(LIKE):
        on = i == li; bar(f, 900 + i * 188, 290, 176, 60, ACCENT if i <= li else "#2a4664")
        T(f, 900 + i * 188 + 88, 375, lab.title() if lab != "almost certain" else "Certain", 27, TEXT if on else MUTED, "bold" if on else "regular", ha="center")
    T(f, 900, 450, "SIZE", 36, MUTED, "bold"); sz = [float(v) for v in p.get("size", [1, 2])]; lo, hi = min(sz), max(sz)
    for i, (lab, a0, a1) in enumerate([("Small", 0, 1.5), ("Large", 1.5, 2.5), ("Very large", 2.5, 3.5), ("Historic", 3.5, 9)]):
        on = lo < a1 and hi >= a0; bar(f, 900 + i * 235, 515, 223, 60, ACCENT if on else "#2a4664")
        T(f, 900 + i * 235 + 111, 600, lab, 30, TEXT if on else MUTED, "bold" if on else "regular", ha="center")
    T(f, 900, 690, "WHAT TO DO", 36, MUTED, "bold")
    for j, line in enumerate(p.get("advice", [])[:3]): T(f, 900, 750 + j * 72, "• " + line, 40, TEXT, "bold")
    footer(f, s.get("source", "")); save(f, path)

def s_cards(s, step, path):
    f = fig_(); header(f, s.get("kicker", "Snoqualmie Pass"), s["headline"]); y = 215
    for i, (when, title, sub) in enumerate(s["rows"][:3]):
        on = (i == step); a = 1.0 if on else 0.3
        box(f, 60, y, 1800, 240, HI if on else PANEL); bar(f, 60, y, 16, 240, ACCENT, a)
        T(f, 120, y + 120, when, 52, ACCENT, "bold", va="center", alpha=a); T(f, 640, y + 40, title, 58, TEXT, "bold", alpha=a); T(f, 640, y + 138, sub, 46, TEXT, alpha=a); y += 262
    footer(f, s.get("source", "")); save(f, path)

def s_zones(s, step, path):
    groups = s["groups"]; hl = groups[min(step, len(groups) - 1)]; rows = [z for g in groups for z in g]
    f = fig_(); header(f, "Other NWAC zones · today", s["headline"]); rh = min(92, 720 // max(len(rows), 1)); y = 262
    T(f, 980, 205, "Above", 28, MUTED, "bold", ha="center"); T(f, 1110, 205, "Near", 28, MUTED, "bold", ha="center"); T(f, 1240, 205, "Below", 28, MUTED, "bold", ha="center"); T(f, 1330, 205, s.get("notes_title", ""), 28, MUTED, "bold")
    for z in rows:
        on = z in hl; a = 1.0 if on else 0.3; bands = (ZONES.get(z) or {}).get("today") or [None, None, None]
        if on and len(hl) < len(rows): box(f, 50, y - 8, 1820, rh - 6, HI, 1.0, 0.008)
        T(f, 80, y + rh / 2 - 6, z, 40, TEXT, "bold", va="center", alpha=a)
        for j, d in enumerate(bands): chip(f, 925 + j * 130, y + 6, 110, rh - 32, d, label=(str(d) if d else "–"), size=36, a=a)
        T(f, 1330, y + rh / 2 - 6, s.get("notes", {}).get(z, ""), 34, MUTED if not on else TEXT, "semibold", va="center", alpha=a); y += rh
    footer(f, s.get("source", "")); save(f, path)

def s_bottom(s, step, path):
    f = fig_(); T(f, W / 2, 50, "BOTTOM LINE", 60, ACCENT, "bold", ha="center"); y = 165; rows = s["rows"][:4]
    for i, (lab, text, kind) in enumerate(rows):
        allon = step >= len(rows); a = 1.0 if (allon or step == i) else 0.3
        col = DCOL.get(kind) if isinstance(kind, int) else {"focus": ACCENT, "muted": "#9fb3c8", "warn": "#f7941e"}.get(kind, TEXT)
        box(f, 60, y, 1800, 195, HI if (a == 1 and not allon) else PANEL); bar(f, 60, y, 16, 195, col, a)
        T(f, 120, y + 22, lab, 50, col, "bold", alpha=a); T(f, 120, y + 100, text, 54, TEXT, "bold", alpha=a); y += 220
    save(f, path)

DRAW = {"title": s_title, "overview": s_overview, "danger": s_danger, "problems": s_problems, "cards": s_cards, "zones": s_zones, "bottom": s_bottom}
if "--frames" in sys.argv:  # quick preview: one PNG per step, no audio
    os.makedirs("preview", exist_ok=True)
    for si, s in enumerate(SPEC["scenes"]):
        for i in range(len(s["say"])): DRAW[s["type"]](s, i, f"preview/s{si:02d}_{i}.png")
    print("frames written"); sys.exit()

os.makedirs("work", exist_ok=True)
K = Kokoro("kokoro.onnx", "voices.bin"); SR = 24000
def say(text):
    ph = K.tokenizer.phonemize(text, "en-us")
    for w, ipa in FIX.items():
        if w in text: ph = ph.replace(K.tokenizer.phonemize(w, "en-us").rstrip("."), ipa)
    return K.create(ph, voice=VOICE, speed=SPEED, is_phonemes=True)[0]
sil = lambda t: np.zeros(int(t * SR), dtype=np.float32)
t = np.arange(int(1.1 * SR)) / SR; t2 = np.clip(t - 0.16, 0, None)
chime = (0.10 * np.sin(2 * np.pi * 523.25 * t) * np.exp(-3.5 * t) + 0.08 * np.sin(2 * np.pi * 783.99 * t2) * np.exp(-3.5 * t2) * (t > 0.16)).astype(np.float32)
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
print("done")
