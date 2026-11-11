#!/usr/bin/env python3
"""Earnest demo video v4 — the v3 cut (same chapters, same narration) plus the
creative layer: 1200x860 canvas (photo-like footprint, a bit longer), scrolling
zoom-pans, an animated cursor with click ripples and press bounce, SEALED /
VERIFIED stamps, confetti bursts and floating reaction emojis.
Audio is built with the same graph as v3 but pinned to 48 kHz stereo AAC."""
import json, math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = "/home/hatch/workspace/earnest"
W, H = 1200, 860
PW, PH, PX, PY = 370, 804, 64, 26
GOLD = (238, 194, 94); PAPER = (242, 244, 250); DIM = (168, 175, 196)
VIOLET = (150, 128, 255); TEAL = (45, 212, 191); GREEN = (64, 220, 160)
FPS = 25
RAW = subprocess.run(["bash", "-c", f"ls -t {ROOT}/assets/video-raw/*.webm | head -1"],
                     capture_output=True, text=True).stdout.strip()

def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])

def font(size, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p, size)

CH = [
    (4.8, 9.3,   ["Earnest"], "Get paid. Get proof.\nGig work in NIM, sealed into\nproof you own."),
    (9.3, 13.8,  ["Signed by both sides,", "chained receipt", "by receipt"], "One tap re-verifies the\nwhole history, in seconds."),
    (13.8, 23.3, ["Post a job.", "Claim a job."], "Paid wallet to wallet in NIM.\nThe receipt seals when the\nworker countersigns."),
    (23.3, 27.8, ["The Earn Passport"], "Earnings nobody can dispute.\nYour jobs, your clients,\nyour signatures."),
    (30.5, 38.0, ["Share one link"], "Anyone can verify it.\nLandlords, banks, clients.\nNo account needed."),
    (41.5, 47.9, ["Grow what you earned"], "Staked in the same app.\n\nearnest-app2.netlify.app"),
]
# (z0, z1, focus_x, focus_y0, focus_y1) — the y pan is the scroll effect
ZOOM = [
    (1.00, 1.08, 0.5, 0.30, 0.38),
    (1.08, 1.00, 0.5, 0.58, 0.44),
    (1.00, 1.09, 0.5, 0.42, 0.56),
    (1.09, 1.02, 0.5, 0.28, 0.36),
    (1.00, 1.08, 0.5, 0.36, 0.50),
    (1.08, 1.00, 0.5, 0.42, 0.50),
]
narr = [probe_dur(f"{ROOT}/assets/audio/n{i}.mp3") for i in range(1, 7)]
targets, starts, t = [], [], 0.0
for d in narr:
    starts.append(round(t, 2)); targets.append(round(d + 0.5, 2)); t += d + 0.5
TOTAL = round(t, 2)
print("starts:", starts, "total:", TOTAL, flush=True)

# ————— stage 1: phone-only video with zoom + scrolling pan + chapter fades —————
fc = []
for i, (s0, s1, _, _) in enumerate(CH):
    src = s1 - s0; ratio = targets[i] / src; tg = targets[i]
    z0, z1, fx, fy0, fy1 = ZOOM[i]
    fc.append(
        f"[0:v]trim=start={s0}:end={s1},setpts={ratio:.4f}*(PTS-STARTPTS),fps={FPS},scale={PW}:{PH},setsar=1,"
        f"scale=w='{PW}*({z0:.3f}+({z1:.3f}-{z0:.3f})*t/{tg:.2f})':h='{PH}*({z0:.3f}+({z1:.3f}-{z0:.3f})*t/{tg:.2f})':eval=frame,"
        f"crop={PW}:{PH}:x='(iw-{PW})*{fx}':y='(ih-{PH})*({fy0:.3f}+({fy1:.3f}-{fy0:.3f})*t/{tg:.2f})',setsar=1,"
        f"fade=in:st=0:d=0.3,fade=out:st={tg-0.3:.2f}:d=0.3[ch{i}]")
fc.append("".join(f"[ch{i}]" for i in range(6)) + f"concat=n=6:v=1:a=0,format=yuv420p[v]")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", RAW, "-filter_complex", ";".join(fc),
                "-map", "[v]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "/tmp/phone4.mp4"], check=True)
print("phone rendered", flush=True)

# ————— sprites —————
def make_bg():
    small = Image.new("RGB", (300, 215), (6, 9, 19))
    d = ImageDraw.Draw(small)
    d.ellipse([140, -70, 310, 90], fill=(58, 40, 120))     # violet glow top right
    d.ellipse([-70, 110, 90, 250], fill=(10, 70, 66))      # teal glow bottom left
    d.ellipse([190, 130, 320, 240], fill=(74, 56, 16))     # gold warmth bottom right
    bg = small.resize((W, H)).filter(ImageFilter.GaussianBlur(60))
    return bg
BG = make_bg()

def make_caption(i):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # header
    d.rounded_rectangle([500, 58, 556, 114], 14, fill=GOLD + (255,))
    d.text((528, 86), "★", font=font(30), fill=(10, 12, 20, 255), anchor="mm")
    d.text((572, 86), "EARNEST", font=font(34), fill=GOLD + (255,), anchor="lm")
    d.text((1150, 86), "nimiq mini apps · cycle iii · earn", font=font(19, False), fill=DIM + (255,), anchor="rm")
    _, _, title, sub = CH[i]
    y = 238
    for line in title:
        d.text((500, y), line, font=font(52), fill=PAPER + (255,), anchor="la"); y += 62
    y += 14
    for line in sub.split("\n"):
        d.text((500, y), line, font=font(25, False), fill=DIM + (255,), anchor="la"); y += 34
    for j in range(6):
        d.ellipse([500 + j * 26, 786, 514 + j * 26, 800], fill=(GOLD if j == i else (70, 76, 96)) + (255,))
    return img
CAPS = [make_caption(i) for i in range(6)]

def make_cursor():
    img = Image.new("RGBA", (52, 52), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(6, 2), (6, 40), (16, 31), (22, 46), (28, 43), (22, 29), (34, 29)]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(10, 12, 20, 255), width=3)
    return img
CURSOR = make_cursor()

def make_stamp(text, color):
    f = font(44)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = tmp.textlength(text, font=f)
    img = Image.new("RGBA", (int(tw) + 56, 92), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, img.width - 5, img.height - 5], 16, outline=color + (255,), width=5)
    d.text((img.width / 2, img.height / 2), text, font=f, fill=color + (255,), anchor="mm")
    return img
STAMP_SEALED = make_stamp("✓ SEALED", GOLD)
STAMP_VERIFIED = make_stamp("✓ VERIFIED", GREEN)

EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
def make_emoji(ch, px=46):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    img = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((65, 65), ch, font=f, anchor="mm", embedded_color=True)
    return img.resize((px, px))
EMO = {c: make_emoji(c) for c in ["💸", "✨", "🎉", "💰", "🔥"]}

# ————— interaction script —————
TAPS = [  # (time, canvas_x, canvas_y)
    (15.6, 220, 498), (18.6, 220, 588), (20.1, 330, 588),
    (21.2, 220, 668), (32.4, 210, 498), (44.6, 255, 548),
]
PATH = [  # cursor keyframes (t, x, y)
    (14.80, 430, 770), (15.35, 220, 498), (16.30, 255, 645), (18.35, 220, 588),
    (19.20, 305, 520), (19.90, 330, 588), (20.70, 262, 705), (21.00, 220, 668),
    (21.70, 405, 790),
    (31.70, 405, 745), (32.20, 210, 498), (33.00, 385, 725),
    (43.90, 405, 745), (44.40, 255, 548), (45.20, 365, 705),
]
FADE_WINDOWS = [(14.8, 15.1, 21.9, 22.3), (31.7, 32.0, 33.2, 33.6), (43.9, 44.2, 45.4, 45.9)]

def smooth(a, b, x):
    x = max(0.0, min(1.0, (x - a) / (b - a)))
    return x * x * (3 - 2 * x)

def cursor_state(t):
    alpha = 0.0
    for f0, f1, o0, o1 in FADE_WINDOWS:
        if f0 <= t <= o1:
            alpha = min(smooth(f0, f1, t), 1 - smooth(o0, o1, t))
    if alpha <= 0:
        return None
    seg = None
    for k in range(len(PATH) - 1):
        if PATH[k][0] <= t <= PATH[k + 1][0]:
            seg = k; break
    if seg is None:
        return None
    t0, x0, y0 = PATH[seg]; t1, x1, y1 = PATH[seg + 1]
    p = smooth(t0, t1, t)
    return (x0 + (x1 - x0) * p, y0 + (y1 - y0) * p, alpha)

def burst(t0, cx, cy, n, seed):
    rnd = random.Random(seed)
    parts = []
    for _ in range(n):
        parts.append((rnd.uniform(-170, 170), rnd.uniform(-330, -60),
                      rnd.uniform(4, 8), rnd.choice([GOLD, TEAL, VIOLET, PAPER]),
                      rnd.uniform(0, 6.28)))
    def draw(d, t):
        dt = t - t0
        if dt < 0 or dt > 1.5:
            return
        for vx, vy, sz, col, ph in parts:
            x = cx + vx * dt; y = cy + vy * dt + 265 * dt * dt
            a = max(0, int(255 * (1 - dt / 1.5)))
            wob = math.sin(ph + dt * 9) * sz * 0.5
            d.rectangle([x - sz / 2, y - (sz + wob) / 2, x + sz / 2, y + (sz + wob) / 2], fill=col + (a,))
    return draw
BURSTS = [burst(21.7, PX + PW // 2, 430, 80, 7), burst(44.6, 255, 548, 36, 11)]

STAMPS = [(21.75, 23.9, STAMP_SEALED, -12), (32.65, 34.8, STAMP_VERIFIED, -10)]
FLOATS = [  # (t0, t1, emoji, x, y, rise, sway_phase)
    (22.0, 28.6, "💸", 830, 320, 26, 0.0), (22.4, 28.6, "✨", 990, 215, 20, 1.7),
    (22.8, 28.6, "🎉", 1065, 395, 30, 3.1), (18.6, 20.6, "💸", 300, 520, 44, 0.6),
    (36.5, 42.8, "💰", 865, 300, 24, 0.9), (37.0, 42.8, "✨", 1015, 205, 18, 2.4),
    (37.4, 42.8, "🔥", 1080, 360, 22, 4.2),
]

def ease_out_back(x):
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ————— stage 2: composite —————
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "/tmp/phone4.mp4",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "/tmp/comp4.mp4"], stdin=subprocess.PIPE)
frame_bytes = PW * PH * 3
n_frames = int(TOTAL * FPS)
shadow = Image.new("RGBA", (PW + 60, PH + 60), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle([30, 26, PW + 30, PH + 34], 46, fill=(0, 0, 0, 190))
shadow = shadow.filter(ImageFilter.GaussianBlur(16))

for n in range(n_frames):
    t = n / FPS
    raw = dec.stdout.read(frame_bytes)
    if len(raw) < frame_bytes:
        break
    phone = Image.frombytes("RGB", (PW, PH), raw)
    canvas = BG.copy().convert("RGBA")
    canvas.alpha_composite(shadow, (PX - 30, PY - 22))
    # press bounce
    scale = 1.0
    for tt, _, _ in TAPS:
        if tt <= t <= tt + 0.22:
            scale = 1 - 0.018 * math.sin(math.pi * (t - tt) / 0.22)
    if scale != 1.0:
        nw, nh = int(PW * scale), int(PH * scale)
        ph = phone.resize((nw, nh))
        canvas.paste(ph, (PX + (PW - nw) // 2, PY + (PH - nh) // 2))
    else:
        canvas.paste(phone, (PX, PY))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([PX, PY, PX + PW, PY + PH], 34, outline=GOLD + (255,), width=3)
    # chapter caption with slide + fade
    ci = max(i for i, s in enumerate(starts) if t >= s)
    st = starts[ci]; en = starts[ci + 1] if ci < 5 else TOTAL
    a = min(smooth(st, st + 0.25, t), 1 - smooth(en - 0.3, en, t)) if ci < 5 else smooth(st, st + 0.25, t)
    if a > 0:
        cap = CAPS[ci].copy()
        cap.putalpha(cap.split()[3].point(lambda v: int(v * a)))
        canvas.alpha_composite(cap, (int(46 * math.exp(-3 * (t - st))), 0))
        d = ImageDraw.Draw(canvas)
    # floating emojis
    for t0, t1, ch, x, y, rise, ph in FLOATS:
        if t0 <= t <= t1:
            p = (t - t0) / (t1 - t0)
            ea = min(smooth(t0, t0 + 0.4, t), 1 - smooth(t1 - 0.4, t1, t))
            sp = EMO[ch].copy()
            sp.putalpha(sp.split()[3].point(lambda v: int(v * ea)))
            yy = y - rise * math.sin(p * math.pi) + 6 * math.sin(t * 2 + ph)
            canvas.alpha_composite(sp, (int(x + 8 * math.sin(t * 1.6 + ph)), int(yy)))
    # stamps
    for t0, t1, sprite, ang in STAMPS:
        if t0 <= t <= t1:
            p = min(1.0, (t - t0) / 0.28)
            s = max(0.05, ease_out_back(p))
            a = 1 - smooth(t1 - 0.3, t1, t)
            sp = sprite.resize((int(sprite.width * s), int(sprite.height * s))).rotate(ang, expand=True, resample=Image.BICUBIC)
            if a < 1:
                sp.putalpha(sp.split()[3].point(lambda v: int(v * a)))
            canvas.alpha_composite(sp, (PX + PW // 2 - sp.width // 2, PY + 285 - sp.height // 2))
    # confetti
    d = ImageDraw.Draw(canvas)
    for b in BURSTS:
        b(d, t)
    # cursor + ripples
    for tt, cx, cy in TAPS:
        dt = t - tt
        if 0 <= dt <= 0.5:
            for lag in (0.0, 0.13):
                p = (dt - lag) / 0.45
                if 0 <= p <= 1:
                    r = 8 + 58 * p
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD + (int(230 * (1 - p)),), width=3)
    cs = cursor_state(t)
    if cs:
        cx, cy, a = cs
        cur = CURSOR.copy()
        if a < 1:
            cur.putalpha(cur.split()[3].point(lambda v: int(v * a)))
        canvas.alpha_composite(cur, (int(cx - 6), int(cy - 2)))
    # progress bar
    d.rectangle([0, H - 8, int(W * t / TOTAL), H], fill=GOLD + (255,))
    enc.stdin.write(canvas.convert("RGB").tobytes())
dec.stdout.close(); dec.wait()
enc.stdin.close(); enc.wait()
print("composite done", flush=True)

# ————— stage 3: audio (v3 graph, pinned to 48 kHz) + mux —————
fc = [f"[0:a]atrim=0:{TOTAL},asetpts=PTS-STARTPTS[base]"]
for i in range(6):
    fc.append(f"[{i+1}:a]loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,adelay={int(starts[i]*1000)}|{int(starts[i]*1000)},apad[na{i}]")
fc.append("[base]" + "".join(f"[na{i}]" for i in range(6)) + "amix=inputs=7:normalize=0[narr]")
whoosh = []
for i in range(1, 6):
    fc.append(f"anoisesrc=d=0.55:c=pink:r=48000:a=0.5,bandpass=f=900:width_type=h:w=600,afade=t=in:st=0:d=0.08,afade=t=out:st=0.3:d=0.25,volume=0.22,adelay={int(starts[i]*1000)}|{int(starts[i]*1000)},apad[w{i}]")
    whoosh.append(f"[w{i}]")
fc.append(f"sine=f=1318.5:d=0.35:r=48000,volume=0.30,adelay={int(starts[3]*1000)}|{int(starts[3]*1000)},apad[c1]")
fc.append(f"sine=f=1760:d=0.5:r=48000,volume=0.22,adelay={int(starts[3]*1000)+110}|{int(starts[3]*1000)+110},apad[c2]")
fc.append(f"sine=f=1568:d=0.4:r=48000,volume=0.20,adelay={int(starts[4]*1000)}|{int(starts[4]*1000)},apad[dg]")
fc.append(f"sine=f=220:d={TOTAL}:r=48000[pd1]")
fc.append(f"sine=f=277.2:d={TOTAL}:r=48000[pd2]")
fc.append(f"[pd1][pd2]amix=inputs=2:normalize=0,volume=0.02,afade=t=out:st={TOTAL-1.2}:d=1.2,atrim=0:{TOTAL}[pad]")
fc.append("[narr]" + "".join(whoosh) + "[c1][c2][dg][pad]amix=inputs=10:normalize=0,alimiter=limit=0.95,aresample=48000[aout]")
cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
for i in range(1, 7):
    cmd += ["-i", f"{ROOT}/assets/audio/n{i}.mp3"]
cmd += ["-i", "/tmp/comp4.mp4", "-filter_complex", ";".join(fc),
        "-map", "7:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-shortest",
        f"{ROOT}/assets/earnest-demo.mp4"]
subprocess.run(cmd, check=True)
print("done: earnest-demo.mp4 (v4)")
