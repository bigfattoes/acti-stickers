"""Instagram story: festival tickets 20% off, with Acti.

    python3 tools/make_story.py

Writes marketing/story-tickets-20-off.png (1080x1920). A dark poster layout: huge gradient '20%',
Acti lit by a soft glow, small tracked labels and one clear call to action. Nothing important sits
in the top 220 px or bottom 260 px, where Instagram draws its own bars.

Needs the Inter / Inter Display fonts (fonts-inter on Debian/Ubuntu).
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_stickers import MAGENTA, ORANGE, PINK, PURPLE, ROOT, SRC, character  # noqa: E402

W, H = 1080, 1920
M = 76  # side margin
OUT = ROOT / 'marketing' / 'story-tickets-20-off.png'
DATES = '16–17 JAN 2027'
SITE = 'activatemefest.com'

INTER = Path('/usr/share/fonts/opentype/inter')
BG = (13, 8, 32)
WHITE = (255, 255, 255)


def f(name, size):
    return ImageFont.truetype(str(INTER / f'{name}.otf'), size)


def tracked(s, font, tracking=0.0, fill=WHITE, alpha=1.0):
    """Text with letter-spacing (tracking is a fraction of the font size; negative tightens)."""
    gap = font.size * tracking
    xs, x = [], 0.0
    for ch in s:
        xs.append(x)
        x += font.getlength(ch) + gap
    asc, desc = font.getmetrics()
    mask = Image.new('L', (int(x - gap) + 8, asc + desc), 0)
    md = ImageDraw.Draw(mask)
    for ch, cx in zip(s, xs):
        md.text((cx, 0), ch, font=font, fill=round(255 * alpha))
    img = Image.new('RGBA', mask.size, fill + (0,))
    img.putalpha(mask)
    return img.crop(img.getbbox())


def fill_gradient(img, stops, angle_mix=0.35):
    """Recolour an alpha mask with the brand gradient, running left to right and slightly down."""
    w, h = img.size
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    t = np.clip(x * (1 - angle_mix) + y * angle_mix, 0, 1)[..., None]
    seg = len(stops) - 1
    out = np.zeros((h, w, 3))
    for i in range(seg):
        lo, hi = i / seg, (i + 1) / seg
        k = np.clip((t - lo) / (hi - lo), 0, 1)
        col = np.array(stops[i]) + (np.array(stops[i + 1]) - np.array(stops[i])) * k
        out = np.where((t >= lo) & (t <= hi), col, out)
    g = Image.fromarray(out.astype('uint8')).convert('RGBA')
    g.putalpha(img.getchannel('A'))
    return g


def radial(centre, radius, colour, strength):
    y, x = np.ogrid[:H, :W]
    d = np.sqrt((x - centre[0]) ** 2 + (y - centre[1]) ** 2) / radius
    layer = np.zeros((H, W, 4), dtype='uint8')
    layer[..., :3] = colour
    layer[..., 3] = (np.clip(1 - d, 0, 1) ** 2.2 * strength * 255).astype('uint8')
    return Image.fromarray(layer)


def grain(img, amount=6, seed=3):
    a = np.array(img).astype(np.int16)
    a[..., :3] += np.random.default_rng(seed).normal(0, amount, (img.height, img.width, 1)).astype(np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'))


def soft_shadow(img, blur, alpha):
    pad = blur * 3
    sh = Image.new('RGBA', (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    a = Image.new('L', sh.size, 0)
    a.paste(img.getchannel('A'), (pad, pad))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha)))
    return sh, pad


def main():
    c = Image.new('RGBA', (W, H), BG + (255,))

    # Light: a warm glow behind Acti, a cool one top-left, both fading into the dark.
    c.alpha_composite(radial((780, 1230), 720, MAGENTA, 0.55))
    c.alpha_composite(radial((820, 1360), 480, ORANGE, 0.45))
    c.alpha_composite(radial((80, 260), 700, PURPLE, 0.55))

    # Header: logo + name on the left, dates on the right, hairline under both.
    logo = Image.open(SRC / 'logo.png').convert('RGBA')
    logo.thumbnail((54, 54), Image.LANCZOS)
    c.alpha_composite(logo, (M, 236))
    name = tracked('ACTIVATEME FEST', f('Inter-SemiBold', 26), 0.16)
    c.alpha_composite(name, (M + logo.width + 18, 236 + (logo.height - name.height) // 2))
    dates = tracked(DATES, f('Inter-SemiBold', 26), 0.12)
    c.alpha_composite(dates, (W - M - dates.width, 236 + (logo.height - dates.height) // 2))
    ImageDraw.Draw(c).line((M, 322, W - M, 322), fill=(255, 255, 255, 60), width=2)

    # Kicker, then the number set big and tight.
    c.alpha_composite(tracked('TICKET OFFER', f('Inter-SemiBold', 28), 0.24, fill=(255, 190, 120)), (M, 380))
    big = tracked('20%', f('InterDisplay-Black', 440), -0.055)
    big = big.resize((W - 2 * M, round(big.height * (W - 2 * M) / big.width)), Image.LANCZOS)
    c.alpha_composite(fill_gradient(big, [PURPLE, MAGENTA, PINK, ORANGE]), (M - 6, 440))
    y = 440 + big.height + 34
    off = tracked('OFF', f('InterDisplay-Black', 230), -0.03)
    c.alpha_composite(off, (M - 4, y))
    y += off.height + 44
    line1 = tracked('Festival tickets.', f('InterDisplay-SemiBold', 54), -0.01)
    c.alpha_composite(line1, (M, y))
    c.alpha_composite(tracked('Get yours now.', f('InterDisplay-SemiBold', 54), -0.01, alpha=0.6),
                      (M, y + line1.height + 18))

    # Acti, pointing at the viewer, in front of the type, with a grounded shadow and a warm rim light.
    acti = character('pose_point', 760)
    a = acti.getchannel('A').point(lambda v: 0 if v < 24 else v)  # drop the cut-out's faint haze
    acti.putalpha(a)
    padded = Image.new('RGBA', (acti.width + 80, acti.height + 80), (0, 0, 0, 0))
    padded.alpha_composite(acti, (40, 40))  # room for the rim light, so it isn't clipped into a box
    acti = padded
    ax, ay = W - M - acti.width + 70, 1595 - acti.height  # head clears the '20%'
    floor = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(floor).ellipse((ax + 80, 1525, ax + acti.width - 80, 1585), fill=(0, 0, 0, 150))
    c.alpha_composite(floor.filter(ImageFilter.GaussianBlur(18)))
    sh, pad = soft_shadow(acti, 30, 0.45)
    c.alpha_composite(sh, (ax - pad - 24, ay - pad + 18))
    rim = Image.new('RGBA', acti.size, (255, 150, 90, 0))
    rim.putalpha(acti.getchannel('A').filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10))
                 .point(lambda v: int(v * 0.35)))
    c.alpha_composite(rim, (ax, ay))
    c.alpha_composite(acti, (ax, ay))

    # Call to action: put Instagram's link sticker over this button.
    bw, bh, by = W - 2 * M, 128, 1600
    btn = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(btn).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=bh // 2, fill=WHITE + (255,))
    label = tracked('Get your tickets', f('InterDisplay-ExtraBold', 50), -0.01, fill=BG)
    arrow = tracked('→', f('Inter-SemiBold', 54), 0, fill=BG)
    lx = (bw - (label.width + 22 + arrow.width)) // 2
    btn.alpha_composite(label, (lx, (bh - label.height) // 2))
    btn.alpha_composite(arrow, (lx + label.width + 22, (bh - arrow.height) // 2 + 2))
    sh, pad = soft_shadow(btn, 24, 0.5)
    c.alpha_composite(sh, (M - pad, by - pad + 14))
    c.alpha_composite(btn, (M, by))
    site = tracked(SITE.upper(), f('Inter-SemiBold', 24), 0.2, alpha=0.6)
    c.alpha_composite(site, ((W - site.width) // 2, by + bh + 40))

    OUT.parent.mkdir(exist_ok=True)
    grain(c).convert('RGB').save(OUT, optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
