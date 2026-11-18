"""Generate assets/pivot-overview.svg: a paper-style overview figure of the PiVoT pipeline.

    python tools/make_overview.py assets/pivot-overview.svg "<path to a Chrome binary>" /tmp/textwidths.json
    "<Chrome>" --headless=new --window-size=1600,832 --force-device-scale-factor=2 \\
        --screenshot=assets/pivot-overview.png "file://$PWD/assets/pivot-overview.svg"

Text is measured with headless Chrome (getComputedTextLength), so wrapping and chips fit exactly in the PNG
that is rasterised on the same machine. Two passes: the first collects the strings to measure.
"""
import json
import math
import pathlib
import subprocess
import sys
import tempfile

OUT, CHROME, CACHE = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
W, H = 1600, 832
SANS = "'Helvetica Neue',Helvetica,Arial,sans-serif"
MONO = "Menlo,Consolas,'DejaVu Sans Mono',monospace"
INK, GRAY, LIGHT, LINE, PANEL = "#1F2328", "#57606A", "#8C959F", "#D0D7DE", "#F6F8FA"
TEAL, TEAL_T = "#0E9F8A", "#E6F7F3"
ORANGE, ORANGE_T = "#D9661A", "#FFF1E3"
PURPLE, PURPLE_T = "#5B4BDB", "#EFEDFD"
GREEN, GREEN_T = "#1A7F37", "#DAFBE1"
RED, RED_T = "#CF222E", "#FFEBE9"
AMBER, AMBER_T = "#9A6700", "#FFF8C5"

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
misses = {}
out = []


def key(s, size, weight, family, style):
    return json.dumps([s, size, weight, family, style], ensure_ascii=False)


def tw(s, size=18, weight=400, family=SANS, style=""):
    k = key(s, size, weight, family, style)
    if k in cache:
        return cache[k]
    misses[k] = {"s": s, "size": size, "weight": weight, "family": family, "style": style}
    return len(s) * size * (0.6 if family == MONO else 0.5)


def measure_misses():
    reqs = list(misses.values())
    html = ("<html><body><svg id='s' xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg><pre id='out'></pre><script>"
            f"const reqs={json.dumps(reqs, ensure_ascii=False)};const svg=document.getElementById('s');const res=[];"
            "for(const r of reqs){const t=document.createElementNS('http://www.w3.org/2000/svg','text');"
            "t.setAttribute('font-family',r.family);t.setAttribute('font-size',r.size);t.setAttribute('font-weight',r.weight);"
            "if(r.style)t.setAttribute('font-style',r.style);t.setAttribute('xml:space','preserve');t.textContent=r.s;svg.appendChild(t);"
            "res.push(t.getComputedTextLength());}document.getElementById('out').textContent=JSON.stringify(res);</script></body></html>")
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "m.html"
        f.write_text(html, encoding="utf-8")
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={d}/p", "--dump-dom", f"file://{f}"],
                             capture_output=True, text=True, timeout=120).stdout
    res = json.loads(dom.split('<pre id="out">')[1].split("</pre>")[0])
    for k, w in zip(misses.keys(), res):
        cache[k] = w
    CACHE.write_text(json.dumps(cache, ensure_ascii=False))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def T(x, y, s, size=18, fill=INK, weight=400, family=SANS, anchor="start", style=""):
    extra = f' font-style="{style}"' if style else ""
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
               f'text-anchor="{anchor}" xml:space="preserve"{extra}>{esc(s)}</text>')


def wrap(s, maxw, size=18, weight=400, family=SANS, style=""):
    space = tw("x x", size, weight, family, style) - 2 * tw("x", size, weight, family, style)
    lines, cur, curw = [], [], 0.0
    for word in s.split(" "):
        w = tw(word, size, weight, family, style)
        if cur and curw + space + w > maxw:
            lines.append(" ".join(cur))
            cur, curw = [word], w
        else:
            curw = curw + space + w if cur else w
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines


def para(x, y, s, maxw, size=18, lh=None, **kw):
    lines = wrap(s, maxw, size, kw.get("weight", 400), kw.get("family", SANS), kw.get("style", ""))
    for i, line in enumerate(lines):
        T(x, y + i * (lh or size * 1.36), line, size=size, **kw)
    return len(lines)


def R(x, y, w, h, fill="#FFFFFF", stroke="none", sw=1.5, rx=10, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(x1, y1, x2, y2, color=GRAY, sw=2.5, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"{d} marker-end="url(#a{color[1:]})"/>')


def gear(cx, cy, r, color):
    out.append(f'<g fill="{color}">')
    for k in range(8):
        out.append(f'<rect x="{cx - r * 0.17:.2f}" y="{cy - r:.2f}" width="{r * 0.34:.2f}" height="{r * 0.5:.2f}" rx="{r * 0.08:.2f}" transform="rotate({k * 45} {cx} {cy})"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r * 0.7:.2f}"/></g><circle cx="{cx}" cy="{cy}" r="{r * 0.3:.2f}" fill="#FFFFFF"/>')


def sparkle(cx, cy, r, color):
    out.append(f'<path d="M{cx} {cy - r} Q{cx} {cy} {cx + r} {cy} Q{cx} {cy} {cx} {cy + r} Q{cx} {cy} {cx - r} {cy} Q{cx} {cy} {cx} {cy - r}Z" fill="{color}"/>')


def bulb(cx, cy, r, color):
    out.append(f'<circle cx="{cx}" cy="{cy - r * 0.18:.2f}" r="{r * 0.62:.2f}" fill="{color}"/>'
               f'<rect x="{cx - r * 0.3:.2f}" y="{cy + r * 0.5:.2f}" width="{r * 0.6:.2f}" height="{r * 0.2:.2f}" rx="1.5" fill="{color}"/>'
               f'<rect x="{cx - r * 0.2:.2f}" y="{cy + r * 0.78:.2f}" width="{r * 0.4:.2f}" height="{r * 0.16:.2f}" rx="1.5" fill="{color}"/>')


def doc(x, y, s, color=GRAY):
    out.append(f'<path d="M{x} {y} h{s * 0.5} l{s * 0.28} {s * 0.28} v{s * 0.72} h-{s * 0.78}z" fill="#FFFFFF" stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>'
               f'<path d="M{x + s * 0.5} {y} v{s * 0.28} h{s * 0.28}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>'
               f'<path d="M{x + s * 0.16} {y + s * 0.52} h{s * 0.46} M{x + s * 0.16} {y + s * 0.74} h{s * 0.46}" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>')


def block_arrow(x, y, color=GRAY):
    out.append(f'<path d="M{x} {y - 4.5} h11 v-7 l15 11.5 l-15 11.5 v-7 h-11z" fill="{color}"/>')


def cursor(cx, cy, s, color):
    """Arrow pointer, tip at the top left."""
    k = s / 20
    pts = [(0, 0), (0, 15.5), (4.2, 11.8), (7.2, 18.2), (9.8, 17.0), (6.9, 10.8), (12.2, 10.8)]
    x0, y0 = cx - 6 * k, cy - 9 * k
    d = "M" + " L".join(f"{x0 + px * k:.1f} {y0 + py * k:.1f}" for px, py in pts) + "Z"
    out.append(f'<path d="{d}" fill="{color}" stroke="{color}" stroke-width="1.2" stroke-linejoin="round"/>')


def scissors(cx, cy, s, color):
    k = s / 24
    out.append(f'<g fill="none" stroke="{color}" stroke-width="{2.1 * k:.2f}" stroke-linecap="round">'
               f'<circle cx="{cx - 7 * k:.1f}" cy="{cy - 5.2 * k:.1f}" r="{3.4 * k:.1f}"/><circle cx="{cx - 7 * k:.1f}" cy="{cy + 5.2 * k:.1f}" r="{3.4 * k:.1f}"/>'
               f'<path d="M{cx - 4.2 * k:.1f} {cy - 3.4 * k:.1f} L{cx + 9.5 * k:.1f} {cy + 5 * k:.1f} M{cx - 4.2 * k:.1f} {cy + 3.4 * k:.1f} L{cx + 9.5 * k:.1f} {cy - 5 * k:.1f}"/></g>')


def funnel(cx, cy, s, color):
    k = s / 24
    out.append(f'<path d="M{cx - 10 * k:.1f} {cy - 8 * k:.1f} H{cx + 10 * k:.1f} L{cx + 2.6 * k:.1f} {cy + 0.8 * k:.1f} V{cy + 9 * k:.1f} '
               f'L{cx - 2.6 * k:.1f} {cy + 6.6 * k:.1f} V{cy + 0.8 * k:.1f} Z" fill="{color}" stroke="{color}" stroke-width="1.2" stroke-linejoin="round"/>')


def flag(cx, cy, s, color):
    k = s / 24
    out.append(f'<line x1="{cx - 7 * k:.1f}" y1="{cy - 10 * k:.1f}" x2="{cx - 7 * k:.1f}" y2="{cy + 10 * k:.1f}" stroke="{color}" stroke-width="{2.2 * k:.2f}" stroke-linecap="round"/>'
               f'<path d="M{cx - 7 * k:.1f} {cy - 9.5 * k:.1f} H{cx + 9 * k:.1f} L{cx + 4.5 * k:.1f} {cy - 4.8 * k:.1f} L{cx + 9 * k:.1f} {cy:.1f} H{cx - 7 * k:.1f} Z" fill="{color}"/>')


def balance(cx, cy, s, color):
    k = s / 24
    pan = lambda x: (f'M{x - 4.2 * k:.1f} {cy + 1.5 * k:.1f} Q{x:.1f} {cy + 6.5 * k:.1f} {x + 4.2 * k:.1f} {cy + 1.5 * k:.1f} Z '
                     f'M{x:.1f} {cy - 6.5 * k:.1f} L{x - 4.2 * k:.1f} {cy + 1.5 * k:.1f} M{x:.1f} {cy - 6.5 * k:.1f} L{x + 4.2 * k:.1f} {cy + 1.5 * k:.1f}')
    out.append(f'<g stroke="{color}" stroke-width="{1.8 * k:.2f}" stroke-linecap="round" stroke-linejoin="round" fill="none">'
               f'<path d="M{cx:.1f} {cy - 9 * k:.1f} V{cy + 9 * k:.1f} M{cx - 5 * k:.1f} {cy + 9 * k:.1f} H{cx + 5 * k:.1f} M{cx - 8 * k:.1f} {cy - 6.5 * k:.1f} H{cx + 8 * k:.1f}"/>'
               f'<path d="{pan(cx - 8 * k)}" fill="{color}"/><path d="{pan(cx + 8 * k)}" fill="{color}"/></g>')


def calculator(cx, cy, s, color):
    k = s / 24
    keys = "".join(f'<circle cx="{cx + dx * k:.1f}" cy="{cy + dy * k:.1f}" r="{1.25 * k:.2f}"/>' for dx in (-4.2, 0, 4.2) for dy in (1.2, 4.6, 8))
    out.append(f'<rect x="{cx - 8 * k:.1f}" y="{cy - 10.5 * k:.1f}" width="{16 * k:.1f}" height="{21 * k:.1f}" rx="{2.6 * k:.1f}" fill="#FFFFFF" stroke="{color}" stroke-width="{1.8 * k:.2f}"/>'
               f'<rect x="{cx - 5.2 * k:.1f}" y="{cy - 7.6 * k:.1f}" width="{10.4 * k:.1f}" height="{4.6 * k:.1f}" rx="{1 * k:.1f}" fill="{color}"/><g fill="{color}">{keys}</g>')


def chat(cx, cy, s, color, inner=None):
    """Speech bubble with an LLM sparkle inside."""
    k = s / 24
    x0, x1, y0, y1, r = cx - 10.5 * k, cx + 10.5 * k, cy - 9 * k, cy + 5.5 * k, 4 * k
    d = (f"M{x0 + r:.1f} {y0:.1f} H{x1 - r:.1f} Q{x1:.1f} {y0:.1f} {x1:.1f} {y0 + r:.1f} V{y1 - r:.1f} Q{x1:.1f} {y1:.1f} {x1 - r:.1f} {y1:.1f} "
         f"H{cx - 2 * k:.1f} L{cx - 7 * k:.1f} {cy + 10.5 * k:.1f} L{cx - 6 * k:.1f} {y1:.1f} H{x0 + r:.1f} Q{x0:.1f} {y1:.1f} {x0:.1f} {y1 - r:.1f} "
         f"V{y0 + r:.1f} Q{x0:.1f} {y0:.1f} {x0 + r:.1f} {y0:.1f}Z")
    out.append(f'<path d="{d}" fill="#FFFFFF" stroke="{color}" stroke-width="{1.7 * k:.2f}" stroke-linejoin="round"/>')
    sparkle(cx, cy - 1.8 * k, 5.2 * k, inner or TEAL)


def docs(x, y, s, color=GRAY):
    """Two stacked pages."""
    doc(x + s * 0.22, y - s * 0.16, s, color)
    doc(x, y, s, color)


def bolt(cx, cy, s, color):
    k = s / 24
    pts = [(2, -11), (-7, 2), (-0.5, 2), (-2, 11), (7, -2), (0.5, -2)]
    out.append('<path d="M' + " L".join(f"{cx + px * k:.1f} {cy + py * k:.1f}" for px, py in pts) + f'Z" fill="{color}" stroke="{color}" stroke-width="1" stroke-linejoin="round"/>')


def target(cx, cy, s, color):
    k = s / 24
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{10.5 * k:.1f}" fill="none" stroke="{color}" stroke-width="{2 * k:.2f}"/>'
               f'<circle cx="{cx}" cy="{cy}" r="{6.3 * k:.1f}" fill="none" stroke="{color}" stroke-width="{2 * k:.2f}"/>'
               f'<circle cx="{cx}" cy="{cy}" r="{2.4 * k:.1f}" fill="{color}"/>')


def braces(cx, cy, s, color):
    k = s / 24
    out.append(f'<rect x="{cx - 12 * k:.1f}" y="{cy - 9.5 * k:.1f}" width="{24 * k:.1f}" height="{19 * k:.1f}" rx="{4 * k:.1f}" fill="#FFFFFF" stroke="{color}" stroke-width="1.5"/>')
    T(cx, cy + 5 * k, "{}", size=15 * k, fill=color, weight=700, family=MONO, anchor="middle")


def mark(cx, cy, kind, color, r=8, fg="#FFFFFF", disc=True):
    """Small status mark: check, cross or question, on a coloured disc (or bare, for use inside a pill)."""
    if disc:
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" stroke="#FFFFFF" stroke-width="1.6"/>')
    k = r / 8
    if kind == "check":
        out.append(f'<path d="M{cx - 3.6 * k:.1f} {cy + 0.2 * k:.1f} L{cx - 1 * k:.1f} {cy + 2.8 * k:.1f} L{cx + 3.8 * k:.1f} {cy - 2.6 * k:.1f}" fill="none" stroke="{fg}" stroke-width="{2 * k:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')
    elif kind == "cross":
        out.append(f'<path d="M{cx - 3 * k:.1f} {cy - 3 * k:.1f} L{cx + 3 * k:.1f} {cy + 3 * k:.1f} M{cx + 3 * k:.1f} {cy - 3 * k:.1f} L{cx - 3 * k:.1f} {cy + 3 * k:.1f}" fill="none" stroke="{fg}" stroke-width="{2 * k:.2f}" stroke-linecap="round"/>')
    else:
        T(cx, cy + 4.3 * k, "?", size=12.5 * k, fill=fg, weight=800, anchor="middle")


def glyph_tile(cx, cy, ch, color, tint, s=19):
    R(cx - s / 2, cy - s / 2, s, s, fill=tint, stroke=color, sw=1.2, rx=4.5)
    T(cx, cy + 4.6, ch, size=13, fill=color, weight=800, family=MONO if ch in "#" else SANS, anchor="middle")


ICONS = {"gear": gear, "sparkle": sparkle, "bulb": bulb}


def chip(x, y, label, color, tint, icon=None, size=16, h=30, bold=600):
    w = tw(label, size, bold) + 26 + (22 if icon else 0)
    R(x, y, w, h, fill=tint, stroke=color, sw=1.4, rx=h / 2)
    tx = x + 13
    if icon:
        ICONS[icon](x + 20, y + h / 2, 8.5, color)
        tx = x + 35
    T(tx, y + h / 2 + size * 0.35, label, size=size, fill=color, weight=bold)
    return w


def sid_tag(x, y, sid, w=74, h=28):
    R(x, y, w, h, fill=TEAL_T, stroke=TEAL, sw=1.4, rx=7)
    T(x + w / 2, y + h / 2 + 5.5, sid, size=15.5, fill=TEAL, weight=700, family=MONO, anchor="middle")


def claim_dot(cx, cy, label, r=17):
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#FFFFFF" stroke="{INK}" stroke-width="1.6"/>')
    T(cx, cy + 5.5, label, size=15.5, weight=700, anchor="middle")


def panel(x, w, num, title, color, tint, y=24, h=600):
    R(x, y, w, h, fill=tint, stroke=color, sw=1.6, rx=18, dash="7 6" if num else "")
    if num:
        out.append(f'<circle cx="{x + 36}" cy="{y + 38}" r="17" fill="{color}"/>')
        T(x + 36, y + 45, str(num), size=20, fill="#FFFFFF", weight=700, anchor="middle")
        T(x + 64, y + 46.5, title, size=24, weight=700)
    else:
        T(x + 20, y + 46.5, title, size=24, weight=700)


def build():
    del out[:]
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
               f'aria-label="Overview of PiVoT: the model points at sentence IDs; code flags hard claims for thinking, then derives verdicts and slices verbatim quotes.">')
    out.append("<defs>" + "".join(
        f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
        f'<path d="M0 0.6 L10 5 L0 9.4 z" fill="{c}"/></marker>' for c in (GRAY, LIGHT, GREEN, RED, ORANGE)) + "</defs>")
    R(0, 0, W, H, fill="#FFFFFF", rx=0)
    PY = 24

    # ------------------------------------------------------------ A: input
    ax, aw = 24, 348
    panel(ax, aw, 0, "Input", LINE, PANEL)
    passages = [("P0.S0", "WAL mode writes changes to a separate log file."), ("P0.S1", "The default page size is 4096 bytes."),
                ("P1.S0", "Checkpoints run every 1000 pages.")]
    tx, twid = ax + 112, aw - 14 - 112 - 14
    wrapped = [wrap(text, twid, 18) for _, text in passages]
    h1 = 58 + sum(max(len(ls) * 23, 30) + 18 for ls in wrapped) + 26
    R(ax + 14, PY + 66, aw - 28, h1, stroke=LINE)
    docs(ax + 26, PY + 86, 20)
    T(ax + 58, PY + 100, "Context passages", size=19, weight=700)
    y = PY + 124
    for (sid, _), ls in zip(passages, wrapped):
        sid_tag(ax + 28, y, sid)
        for j, line in enumerate(ls):
            T(tx, y + 14 + j * 23, line, size=18)
        y += max(len(ls) * 23, 30) + 18
    T(ax + aw - 28, y + 10, "sentence IDs added by code", size=15, fill=PURPLE, anchor="end", style="italic")
    y2 = PY + 66 + h1 + 16
    R(ax + 14, y2, aw - 28, PY + 584 - y2, stroke=LINE)
    chat(ax + 38, y2 + 28, 25, GRAY)
    T(ax + 58, y2 + 34, "Generated answer", size=19, weight=700)
    para(ax + 30, y2 + 72, "The default page size is 8192 bytes, and checkpoints run every 1000 pages. WAL is always faster than a rollback journal.",
         aw - 60, size=19, lh=28)

    # ------------------------------------------------------------ B: point
    bx, bw = 408, 392
    panel(bx, bw, 1, "Point", TEAL, TEAL_T)
    chip(bx + 16, PY + 68, "LLM · thinking off", TEAL, "#FFFFFF", icon="sparkle")
    cursor(bx + 25, PY + 118, 19, TEAL)
    T(bx + 40, PY + 124, "Split into claims; point at sentence IDs.", size=17, fill=GRAY)
    rows = [("c1", "The default page size is 8192 bytes.", "refutes", RED, "P0.S1"),
            ("c2", "Checkpoints run every 1000 pages.", "entails", GREEN, "P1.S0"),
            ("c3", "WAL is always faster than a rollback journal.", "no edge", LIGHT, None)]
    cw = 198
    for i, (cid, text, rel, color, sid) in enumerate(rows):
        y = PY + 144 + i * 112
        R(bx + 16, y, cw, 98, stroke=LINE)
        claim_dot(bx + 40, y + 26, cid, r=15)
        lines = wrap(text, cw - 78, 17)
        first = lines[0]
        rest = wrap(" ".join(lines[1:]), cw - 28, 17) if len(lines) > 1 else []
        T(bx + 64, y + 32, first, size=17)
        for j, line in enumerate(rest):
            T(bx + 30, y + 58 + j * 22, line, size=17)
        x1, x2, ym = bx + 16 + cw + 8, bx + bw - 16 - 74 - 8, y + 49
        if sid:
            arrow(x1, ym, x2, ym, color=color, sw=2.6)
            T((x1 + x2) / 2, ym - 10, rel, size=16, fill=color, weight=700, anchor="middle")
            sid_tag(bx + bw - 16 - 74, ym - 14, sid)
            mark(bx + bw - 16 - 2, ym - 14, "cross" if rel == "refutes" else "check", color, r=8.5)
        else:
            out.append(f'<line x1="{x1}" y1="{ym}" x2="{x2 + 18}" y2="{ym}" stroke="{LIGHT}" stroke-width="2.2" stroke-dasharray="5 6" stroke-linecap="round"/>')
            T((x1 + x2) / 2 + 6, ym - 10, rel, size=16, fill=GRAY, weight=700, anchor="middle")
            out.append(f'<circle cx="{bx + bw - 16 - 37}" cy="{ym}" r="15" fill="#FFFFFF" stroke="{LIGHT}" stroke-width="1.8"/>')
            T(bx + bw - 16 - 37, ym + 6.5, "∅", size=19, fill=GRAY, anchor="middle")
    R(bx + 16, PY + 486, bw - 32, 98, stroke=LINE)
    braces(bx + 42, PY + 507, 21, GRAY)
    T(bx + 60, PY + 512, "Model output: IDs only, no quotes", size=15.5, fill=GRAY, weight=600)
    T(bx + 30, PY + 541, '{"sid": "P0.S1", "rel": "refutes"}', size=15.5, family=MONO)
    T(bx + 30, PY + 567, '{"sid": "P1.S0", "rel": "entails"}', size=15.5, family=MONO)

    # ------------------------------------------------------------ C: think only where needed
    cx0, cw0 = 836, 344
    panel(cx0, cw0, 2, "Think where needed", ORANGE, ORANGE_T)
    w1 = chip(cx0 + 16, PY + 68, "code rules", PURPLE, "#FFFFFF", icon="gear")
    arrow(cx0 + 16 + w1 + 7, PY + 83, cx0 + 16 + w1 + 27, PY + 83, color=GRAY, sw=2.2)
    chip(cx0 + 16 + w1 + 35, PY + 68, "thinking on", ORANGE, "#FFFFFF", icon="bulb")
    R(cx0 + 16, PY + 112, cw0 - 32, 170, stroke=LINE)
    flag(cx0 + 38, PY + 134, 20, PURPLE)
    T(cx0 + 56, PY + 140, "A claim is flagged if", size=17.5, weight=700)
    for j, (g, line) in enumerate([("#", "its number is not in the evidence"), ("!", "it says only, must or always"),
                                   ("±", "evidence both supports and refutes"), ("?", "the model marked it unsure")]):
        glyph_tile(cx0 + 35, PY + 163 + j * 28, g, PURPLE, PURPLE_T)
        T(cx0 + 50, PY + 169 + j * 28, line, size=17)
    y1 = PY + 328
    claim_dot(cx0 + 38, y1, "c1")
    arrow(cx0 + 60, y1, cx0 + 108, y1, color=ORANGE, sw=2.8)
    R(cx0 + 114, y1 - 32, cw0 - 130, 64, fill="#FFFFFF", stroke=ORANGE, sw=2, rx=12)
    bulb(cx0 + 140, y1, 13, ORANGE)
    T(cx0 + 162, y1 - 5, "judged again", size=17.5, weight=700)
    T(cx0 + 162, y1 + 17, "with thinking", size=17.5, weight=700)
    T(cx0 + 30, y1 + 62, "flagged: 8192 is not in “… is 4096 bytes.”", size=15.5, fill=ORANGE, style="italic")
    for j, cid in enumerate(["c2", "c3"]):
        yy = PY + 444 + j * 52
        claim_dot(cx0 + 38, yy, cid)
        arrow(cx0 + 60, yy, cx0 + 108, yy, color=LIGHT, sw=2.2, dash="5 6")
        T(cx0 + 118, yy + 6, "first-pass result kept", size=17, fill=GRAY)
    note = "≈ ¼–⅓ of claims get thinking"
    nw = tw(note, 18, 700)
    nx = cx0 + (cw0 - nw - 28) / 2
    funnel(nx + 9, PY + 568, 19, ORANGE)
    T(nx + 28, PY + 574, note, size=18, fill=ORANGE, weight=700)

    # ------------------------------------------------------------ D: derive
    dx, dw = 1216, 360
    panel(dx, dw, 3, "Derive", PURPLE, PURPLE_T)
    chip(dx + 16, PY + 68, "deterministic code", PURPLE, "#FFFFFF", icon="gear")
    R(dx + 16, PY + 112, dw - 32, 106, stroke=LINE)
    for j, (icon, lhs, rhs, mono) in enumerate([(balance, "verdict", "entails / refutes edges", False), (scissors, "quote", "passage[start:end]", True),
                                                (calculator, "numbers", "computed by code", False)]):
        yy = PY + 142 + j * 29
        icon(dx + 38, yy - 6, 19, PURPLE)
        T(dx + 56, yy, lhs, size=17, weight=700)
        T(dx + 135, yy, "←", size=17, fill=GRAY)
        T(dx + 160, yy, rhs, size=15.5 if mono else 17, family=MONO if mono else SANS)
        rw = tw(rhs, 15.5 if mono else 17, 400, MONO if mono else SANS)
        assert misses or dx + 160 + rw < dx + dw - 22, (rhs, rw)
    res = [("CONTRADICTED", RED, RED_T, "c1", "“The default page size is 4096 bytes.”", "passage 0 · chars 48–84"),
           ("SUPPORTED", GREEN, GREEN_T, "c2", "“Checkpoints run every 1000 pages.”", "passage 1 · chars 0–33"),
           ("UNSUPPORTED", AMBER, AMBER_T, "c3", None, "no citation: the passages do not say this")]
    for j, (verdict, color, tint, cid, quote, meta) in enumerate(res):
        yy = PY + 234 + j * 120
        hh = 108 if quote else 110
        R(dx + 16, yy, dw - 32, hh, stroke=color, sw=1.6)
        bw_ = tw(verdict, 14.5, 700) + 40
        R(dx + 28, yy + 12, bw_, 26, fill=color, rx=13)
        mark(dx + 44, yy + 25, {"CONTRADICTED": "cross", "SUPPORTED": "check"}.get(verdict, "q"), color, r=8, disc=False)
        T(dx + 56, yy + 30, verdict, size=14.5, fill="#FFFFFF", weight=700)
        claim_dot(dx + dw - 44, yy + 25, cid, r=14)
        if quote:
            out.append(f'<line x1="{dx + 30}" y1="{yy + 50}" x2="{dx + 30}" y2="{yy + 96}" stroke="{TEAL}" stroke-width="3" stroke-linecap="round"/>')
            n = para(dx + 42, yy + 64, quote, dw - 32 - 40, size=16.5, lh=21, style="italic")
            T(dx + 42, yy + 64 + n * 21 + 2, meta, size=14.5, fill=GRAY, family=MONO)
        else:
            para(dx + 28, yy + 66, meta, dw - 60, size=16.5, lh=22, fill=GRAY, style="italic")

    # ------------------------------------------------------------ arrows between panels
    for xa, xb in ((ax + aw, bx), (bx + bw, cx0), (cx0 + cw0, dx)):
        block_arrow(xa + (xb - xa - 26) / 2, PY + 300)

    # ------------------------------------------------------------ bottom: legend + three takeaways
    BY, BH = 648, 160
    R(ax, BY, aw, BH, fill="#FFFFFF", stroke=LINE)
    for j, (icon, color, label) in enumerate([("sparkle", TEAL, "LLM call, thinking off"), ("bulb", ORANGE, "LLM call, thinking on"), ("gear", PURPLE, "deterministic code")]):
        ICONS[icon](ax + 36, BY + 38 + j * 42, 11, color)
        T(ax + 62, BY + 44 + j * 42, label, size=18)
    for x, w, color, tint, big, small in ((bx, bw, TEAL, TEAL_T, "Verbatim by construction", "Quotes are sliced from the passage by ID. The model never writes one."),
                                          (cx0, cw0, ORANGE, ORANGE_T, "31–40% of the tokens", "of the same model thinking on every claim (PiVoT v3)."),
                                          (dx, dw, PURPLE, PURPLE_T, "0.953 · 0.979 accuracy", "on two frozen test sets (v3). Thinking on every claim: 0.959 · 0.952.")):
        R(x, BY, w, BH, fill=tint, stroke=color, sw=1.6)
        T(x + 20, BY + 46, big, size=25, weight=700, fill=color)
        icon = {TEAL: scissors, ORANGE: bolt, PURPLE: target}[color]
        bw2 = tw(big, 25, 700)
        assert misses or x + 20 + bw2 < x + w - 58, (big, bw2)
        out.append(f'<circle cx="{x + w - 36}" cy="{BY + 38}" r="21" fill="#FFFFFF" stroke="{color}" stroke-width="1.4"/>')
        icon(x + w - 36, BY + 38, 25, color)
        para(x + 20, BY + 82, small, w - 40, size=18, lh=25, fill=INK)
    out.append("</svg>")
    return "\n".join(out) + "\n"


svg = build()
if misses:
    measure_misses()
    misses.clear()
    svg = build()
    assert not misses, "unmeasured strings remain"
pathlib.Path(OUT).write_text(svg, encoding="utf-8")
print("wrote", pathlib.Path(OUT).name, len(svg), "bytes")
