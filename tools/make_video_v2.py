#!/usr/bin/env python3
"""Earnest demo video v2: landscape frame, narration, motion, sound effects."""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

A = os.path.expanduser("~/workspace/earnest/assets")
RAW = max((os.path.join(A, "video-raw", f) for f in os.listdir(os.path.join(A, "video-raw"))), key=os.path.getmtime)
WORK = "/tmp/earnest-v2"
os.makedirs(WORK, exist_ok=True)
W, H = 1280, 720
GOLD = (238, 194, 94); PAPER = (242, 244, 250); DIM = (168, 175, 196); VIOLET = (150, 128, 255)

def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])

def font(size, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p, size)

# ——— chapters: (raw_start, raw_end, title_lines, sub) ———
CH = [
    (4.8, 9.3,   ["Earnest"], "Get paid. Get proof.\nGig work in NIM, sealed into\nproof you own."),
    (9.3, 13.8,  ["Signed by both sides,", "chained receipt", "by receipt"], "One tap re-verifies the\nwhole history, in seconds."),
    (13.8, 23.3, ["Post a job.", "Claim a job."], "Paid wallet to wallet in NIM.\nThe receipt seals when the\nworker countersigns."),
    (23.3, 27.8, ["The Earn Passport"], "Earnings nobody can dispute.\nYour jobs, your clients,\nyour signatures."),
    (30.5, 38.0, ["Share one link"], "Anyone can verify it.\nLandlords, banks, clients.\nNo account needed."),
    (41.5, 47.9, ["Grow what you earned"], "Staked in the same app.\n\nearnest-app2.netlify.app"),
]
ZOOM = [
    (1.00, 1.08, 0.5, 0.32),
    (1.08, 1.00, 0.5, 0.55),
    (1.00, 1.09, 0.5, 0.45),
    (1.09, 1.02, 0.5, 0.30),
    (1.00, 1.08, 0.5, 0.40),
    (1.08, 1.00, 0.5, 0.45),
]
narr = [probe_dur(os.path.join(A, "audio", f"n{i+1}.mp3")) for i in range(6)]
GAP = 0.5
targets = [n + GAP for n in narr]
starts = []
t = 0.0
for tg in targets:
    starts.append(t)
    t += tg
TOTAL = t + 0.8
print("chapter starts:", [round(s, 2) for s in starts], "total:", round(TOTAL, 2))

# ——— background ———
bg = Image.new("RGB", (W, H), (6, 8, 18))
d = ImageDraw.Draw(bg)
for x in range(W):
    for yy in range(0, H, 4):
        pass
for i in range(H):
    tt = i / H
    d.line([(0, i), (W, i)], fill=(int(6 + 10 * tt), int(8 + 8 * tt), int(18 + 22 * tt)))
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(ov)
od.ellipse([760, -260, 1420, 260], fill=(124, 92, 255, 60))
od.ellipse([-220, 420, 320, 900], fill=(45, 212, 191, 36))
od.ellipse([820, 480, 1400, 900], fill=(238, 194, 94, 30))
bg = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
bg.save(f"{WORK}/bg.png")

# phone frame (slightly bigger than the 298x648 phone video at 110,36)
fr = Image.new("RGBA", (330, 680), (0, 0, 0, 0))
fd = ImageDraw.Draw(fr)
fd.rounded_rectangle([6, 6, 324, 674], radius=30, fill=(0, 0, 0, 130))
fd.rounded_rectangle([10, 10, 320, 670], radius=27, outline=(238, 194, 94, 200), width=3)
fd.rounded_rectangle([13, 13, 317, 667], radius=25, outline=(255, 255, 255, 40), width=1)
fr.save(f"{WORK}/frame.png")

def star(draw, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.46
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    draw.polygon(pts, fill=fill)

# captions: full-canvas transparent overlays, text on the right side
for i, (_, _, lines, sub) in enumerate(CH):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    dd.rounded_rectangle([478, 54, 542, 118], radius=16, fill=(238, 194, 94, 255))
    star(dd, 510, 86, 19, (25, 16, 3))
    dd.text((560, 86), "EARNEST", font=font(30), fill=GOLD, anchor="lm")
    dd.text((1222, 86), "nimiq mini apps · cycle iii · earn", font=font(19, False), fill=DIM, anchor="rm")
    y = 218
    for ln in lines:
        dd.text((482, y), ln, font=font(54), fill=PAPER)
        y += 66
    y += 16
    for ln in sub.split("\n"):
        dd.text((484, y), ln, font=font(27, False), fill=(196, 202, 220))
        y += 38
    for k in range(6):
        cx = 486 + k * 30
        dd.ellipse([cx, 600, cx + 14, 614], fill=GOLD if k == i else (90, 98, 120))
    img.save(f"{WORK}/cap{i}.png")
print("assets rendered")

# ——— ffmpeg assembly ———
inputs = ["-loop", "1", "-t", f"{TOTAL:.2f}", "-i", f"{WORK}/bg.png",
          "-i", RAW,
          "-loop", "1", "-t", f"{TOTAL:.2f}", "-i", f"{WORK}/frame.png"]
for i in range(6):
    inputs += ["-loop", "1", "-t", f"{TOTAL:.2f}", "-i", f"{WORK}/cap{i}.png"]
for i in range(6):
    inputs += ["-i", os.path.join(A, "audio", f"n{i+1}.mp3")]
# input indexes: 0 bg, 1 raw, 2 frame, 3..8 captions, 9..14 narration

fc = []
for i, (s0, s1, _, _) in enumerate(CH):
    src = s1 - s0
    ratio = targets[i] / src
    z0, z1, fx, fy = ZOOM[i]
    tg = targets[i]
    fc.append(
        f"[1:v]trim=start={s0}:end={s1},setpts={ratio:.4f}*(PTS-STARTPTS),fps=25,scale=298:648,setsar=1,"
        f"scale=w='298*({z0:.3f}+({z1:.3f}-{z0:.3f})*t/{tg:.2f})':h='648*({z0:.3f}+({z1:.3f}-{z0:.3f})*t/{tg:.2f})':eval=frame,"
        f"crop=298:648:x='(iw-298)*{fx}':y='(ih-648)*{fy}',setsar=1,"
        f"fade=in:st=0:d=0.3,fade=out:st={tg-0.3:.2f}:d=0.3[ch{i}]")
fc.append("".join(f"[ch{i}]" for i in range(6)) + "concat=n=6:v=1:a=0[cat]")
fc.append("[cat]scale=298:648,setsar=1[phone]")
fc.append("[0:v][2:v]overlay=94:20[bf]")
fc.append("[bf][phone]overlay=x='110+4*sin(t*0.55)':y='36+3*cos(t*0.42)'[comp]")
prev = "comp"
for i in range(6):
    st, en = starts[i], starts[i] + targets[i]
    fi = min(0.45, targets[i] / 3)
    fc.append(f"[{3+i}:v]format=rgba,fade=in:st={st:.2f}:d={fi:.2f}:alpha=1,fade=out:st={en-fi:.2f}:d={fi:.2f}:alpha=1[cap{i}f]")
    fc.append(f"[{prev}][cap{i}f]overlay=x='46*exp(-3.0*(t-{st:.2f}))':y=0:enable='between(t,{st:.2f},{en:.2f})'[c{i}]")
    prev = f"c{i}"
fc.append(f"[{prev}]drawbox=x=0:y=712:w='1280*t/{TOTAL:.2f}':h=8:color=0xEEC25E@0.85:t=fill,format=yuv420p[vout]")

# audio: narration delayed to chapter starts
for i in range(6):
    fc.append(f"[{9+i}:a]loudnorm=I=-15:TP=-1.5:LRA=11,adelay={int(starts[i]*1000)}|{int(starts[i]*1000)},apad[na{i}]")
fc.append("".join(f"[na{i}]" for i in range(6)) + "amix=inputs=6:normalize=0[narr]")
# ambient pad
fc.append(f"sine=frequency=110:d={TOTAL:.2f}[p1]")
fc.append(f"sine=frequency=164.81:d={TOTAL:.2f}[p2]")
fc.append("[p1][p2]amix=inputs=2:normalize=0,lowpass=f=280,volume=0.02,afade=out:st={:.2f}:d=1.2[pad]".format(TOTAL - 1.4))
# whooshes at chapter boundaries 1..5
whoosh_labels = []
for j, b in enumerate(starts[1:]):
    lbl = f"w{j}"
    fc.append(f"anoisesrc=d=0.5:color=pink,bandpass=f=750:width_type=h:width=500,afade=in:st=0:d=0.18,afade=out:st=0.28:d=0.22,volume=0.22,adelay={int(b*1000)}|{int(b*1000)},apad[{lbl}]")
    whoosh_labels.append(f"[{lbl}]")
# chime at chapter 4 start (passport grown), ding at chapter 5 start (public verify)
fc.append(f"sine=frequency=1318.5:d=0.5,afade=out:st=0.08:d=0.42,volume=0.30,adelay={int(starts[3]*1000)}|{int(starts[3]*1000)},apad[chm1]")
fc.append(f"sine=frequency=1760:d=0.5,afade=out:st=0.08:d=0.42,volume=0.22,adelay={int((starts[3]+0.14)*1000)}|{int((starts[3]+0.14)*1000)},apad[chm2]")
fc.append(f"sine=frequency=1568:d=0.45,afade=out:st=0.06:d=0.39,volume=0.22,adelay={int(starts[4]*1000)}|{int(starts[4]*1000)},apad[dng]")
sfx = "".join(whoosh_labels) + "[chm1][chm2][dng]"
fc.append(f"[narr][pad]{sfx}amix=inputs={2 + len(whoosh_labels) + 3}:normalize=0,alimiter=limit=0.95,atrim=0:{TOTAL:.2f}[aout]")

out = os.path.join(A, "earnest-demo.mp4")
cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + [
    "-filter_complex", ";".join(fc),
    "-map", "[vout]", "-map", "[aout]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "25",
    "-c:a", "aac", "-b:a", "160k", "-shortest", out]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:])
    sys.exit(1)
print("done:", out, os.path.getsize(out), "bytes, total", round(TOTAL, 1), "s")
