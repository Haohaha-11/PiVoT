"""Generate assets/pivot-logo-banner.svg: a wide, short banner built from assets/pivot-logo.svg.

    python tools/make_banner.py assets/pivot-logo-banner.svg

The letterforms, pin, tips and fulcrum are copied from pivot-logo.svg unchanged; only the layout differs
(tagline to the right of the wordmark, full-width dark band with a faint dot grid).
"""
import sys

OUT = sys.argv[1]
BG, INK, TEAL, PURPLE, ORANGE, DOT = "#161616", "#DDD9D2", "#10B39A", "#6250E8", "#F07A2E", "#2C2C2C"
# wordmark bounding box in pivot-logo.svg coordinates: x 434..1340, y 287..549
X0, Y0, W, H = 290, 233, 2260, 370          # band in the logo's coordinate system (aspect ~6.1:1)
DIV_X = 1418                                   # divider between wordmark and tagline
TAG_X, TAG_Y = 1470, 438                       # tagline baseline, vertically centred on the wordmark

dots = []
for gx in range(X0 + 20, X0 + W, 28):
    for gy in range(Y0 + 18, Y0 + H, 28):
        dots.append(f'<circle cx="{gx}" cy="{gy}" r="2.2"/>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{X0} {Y0} {W} {H}" width="{W}" height="{H}" role="img" aria-label="PIVOT — Point, don’t paraphrase.">
  <!-- wide banner of pivot-logo.svg: same artwork, tagline set beside the wordmark -->
  <defs>
    <clipPath id="band"><rect x="{X0}" y="{Y0}" width="{W}" height="{H}" rx="28"/></clipPath>
    <radialGradient id="fade" cx="0.5" cy="0.5" r="0.62">
      <stop offset="0.35" stop-color="{BG}" stop-opacity="1"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <g clip-path="url(#band)">
  <rect x="{X0}" y="{Y0}" width="{W}" height="{H}" fill="{BG}"/>
  <g fill="{DOT}">{"".join(dots)}</g>
  <rect x="{X0}" y="{Y0}" width="{W}" height="{H}" fill="url(#fade)"/>
  <g fill="none" stroke="{INK}" stroke-width="52" stroke-linecap="round" stroke-linejoin="round">
    <path d="M460 520 V331 H545 A56 56 0 0 1 545 443 H460"/>
    <path d="M745 320 L822 520 L888 342"/>
    <ellipse cx="1033" cy="425" rx="94" ry="98"/>
    <path d="M1180 331 H1314"/>
    <path d="M1237 331 V505" stroke-linecap="butt"/>
  </g>
  <circle cx="672" cy="318" r="31" fill="{TEAL}"/>
  <line x1="672" y1="392" x2="672" y2="520" stroke="{TEAL}" stroke-width="52" stroke-linecap="round"/>
  <circle cx="744" cy="316" r="22" fill="{PURPLE}"/>
  <path d="M734 316 L742 324 L755 308" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="888" cy="336" r="22" fill="{ORANGE}"/>
  <text x="888" y="345" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="26" font-weight="700" fill="#fff">?</text>
  <path d="M1237 503 L1262 545 H1212 Z" fill="{PURPLE}" stroke="{PURPLE}" stroke-width="4" stroke-linejoin="round"/>
  <line x1="{DIV_X}" y1="318" x2="{DIV_X}" y2="532" stroke="#3A3A3A" stroke-width="3" stroke-linecap="round"/>
  <text x="{TAG_X}" y="{TAG_Y}" font-family="'Avenir Next', 'Helvetica Neue', Arial, sans-serif" font-size="58" font-weight="500" letter-spacing="3" fill="{INK}">Point, don’t paraphrase.</text>
  <text x="{TAG_X + 2}" y="{TAG_Y + 62}" font-family="'Avenir Next', 'Helvetica Neue', Arial, sans-serif" font-size="27" font-weight="500" letter-spacing="5" fill="#8A877F">CITATION GROUNDING · VERBATIM BY CONSTRUCTION</text>
  </g>
</svg>
'''
open(OUT, "w", encoding="utf-8").write(svg)
print("wrote", OUT, len(svg), "bytes")
