"""Build assets/pivot-logo-banner.png from the original logo (assets/pivot-logo.png) without redrawing it.

    python tools/make_banner.py assets/pivot-logo.png assets/pivot-logo-banner.png "<path to a Chrome binary>"

The logo's pixels are copied unchanged. The script only crops the empty margin above and below the artwork and
extends the canvas left and right with the logo's own background colour (the background is flat: rgb(21,20,20),
s.d. < 1), so the banner is short and wide. Corners are rounded with transparency.
"""
import base64
import pathlib
import subprocess
import sys
import tempfile

SRC, OUT, CHROME = sys.argv[1], sys.argv[2], sys.argv[3]
BBOX = (433, 287, 1342, 635)      # artwork bounds in the 1774x887 original (wordmark + tagline)
PAD_Y, ASPECT, RADIUS = 40, 5.5, 26
BG = "rgb(21,20,20)"

y0, y1 = BBOX[1] - PAD_Y, BBOX[3] + PAD_Y
H = y1 - y0
W = round(H * ASPECT)
b64 = base64.b64encode(pathlib.Path(SRC).read_bytes()).decode()
html = f"""<html><body><pre id="o"></pre><script>
const im = new Image();
im.onload = () => {{
  const c = document.createElement('canvas'); c.width = {W}; c.height = {H};
  const g = c.getContext('2d');
  g.beginPath(); g.roundRect(0, 0, {W}, {H}, {RADIUS}); g.clip();
  g.fillStyle = "{BG}"; g.fillRect(0, 0, {W}, {H});
  const dx = Math.round(({W} - im.width) / 2);
  g.drawImage(im, 0, {y0}, im.width, {H}, dx, 0, im.width, {H});
  document.getElementById('o').textContent = c.toDataURL('image/png');
}};
im.src = "data:image/png;base64,{b64}";
</script></body></html>"""
with tempfile.TemporaryDirectory() as d:
    f = pathlib.Path(d) / "b.html"
    f.write_text(html)
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={d}/p", "--virtual-time-budget=20000",
                          "--dump-dom", f"file://{f}"], capture_output=True, text=True, timeout=120).stdout
data = dom.split('<pre id="o">data:image/png;base64,')[1].split("</pre>")[0]
pathlib.Path(OUT).write_bytes(base64.b64decode(data))
print(f"wrote {OUT}: {W}x{H}")
