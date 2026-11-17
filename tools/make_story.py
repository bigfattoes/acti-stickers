"""Instagram story: tickets 20% off, with Acti pointing at the viewer.

    python3 tools/make_story.py

Writes marketing/story-tickets-20-off.png (1080x1920). Keeps the top 220 px and bottom 260 px
clear of important content, since Instagram draws its own bars there.
"""

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_stickers import (INK, MAGENTA, ORANGE, PINK, PURPLE, ROOT, SRC, WHITE, character, disk,  # noqa: E402
                           emoji, font, gradient)
from scipy import ndimage as nd  # noqa: E402

W, H = 1080, 1920
OUT = ROOT / 'marketing' / 'story-tickets-20-off.png'
DATES = '16–17 JAN 2027'
SITE = 'activatemefest.com'


def vertical_gradient(stops):
    y = np.linspace(0, 1, H)[:, None, None]
    out = np.zeros((H, 1, 3))
    seg = len(stops) - 1
    for i in range(seg):
        lo, hi = i / seg, (i + 1) / seg
        t = np.clip((y - lo) / (hi - lo), 0, 1)
        c = np.array(stops[i]) + (np.array(stops[i + 1]) - np.array(stops[i])) * t
        out = np.where((y >= lo) & (y <= hi), c, out)
    return Image.fromarray(np.repeat(out, W, 1).astype('uint8')).convert('RGBA')


def glow(img, xy, r, colour, alpha):
    layer = Image.new('RGBA', img.size, colour + (0,))
    m = Image.new('L', img.size, 0)
    x, y = xy
    ImageDraw.Draw(m).ellipse((x - r, y - r, x + r, y + r), fill=alpha)
    layer.putalpha(m.filter(ImageFilter.GaussianBlur(r * 0.6)))
    img.alpha_composite(layer)


def confetti(img, n=70, seed=7):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img)
    colours = [WHITE, ORANGE, (255, 200, 60), PINK, (140, 200, 255)]
    for _ in range(n):
        x, y = rnd.randrange(W), rnd.randrange(160, H - 120)
        c = rnd.choice(colours) + (rnd.randrange(120, 230),)
        s = rnd.randrange(6, 16)
        kind = rnd.random()
        if kind < 0.4:
            d.ellipse((x, y, x + s, y + s), fill=c)
        elif kind < 0.8:
            a = rnd.uniform(0, math.pi)
            dx, dy = math.cos(a) * s * 1.4, math.sin(a) * s * 1.4
            d.line((x - dx, y - dy, x + dx, y + dy), fill=c, width=max(4, s // 2))
        else:  # little four-point sparkle
            r = s * 1.6
            d.polygon([(x, y - r), (x + r * 0.28, y - r * 0.28), (x + r, y), (x + r * 0.28, y + r * 0.28),
                       (x, y + r), (x - r * 0.28, y + r * 0.28), (x - r, y), (x - r * 0.28, y - r * 0.28)], fill=c)


def text(s, size, fill=WHITE, weight='ExtraBold'):
    f = font(size, weight=weight)
    l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), s, font=f)
    img = Image.new('RGBA', (r - l, b - t), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((-l, -t), s, font=f, fill=fill)
    return img


def gradient_text(s, size, stops=(PURPLE, MAGENTA, PINK, ORANGE)):
    mask = text(s, size).getchannel('A')
    img = gradient(mask.width, mask.height, stops)
    img.putalpha(mask)
    return img


def shadow_of(img, blur=14, offset=(0, 12), alpha=0.35, colour=(25, 5, 60)):
    pad = blur * 3
    sh = Image.new('RGBA', (img.width + pad * 2, img.height + pad * 2), colour + (0,))
    a = Image.new('L', sh.size, 0)
    a.paste(img.getchannel('A'), (pad, pad))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha)))
    return sh, (pad - offset[0], pad - offset[1])


def put(canvas, img, cx, cy, rotate=0, shadow=None):
    if rotate:
        img = img.rotate(rotate, resample=Image.BICUBIC, expand=True)
    if shadow:
        sh, (ox, oy) = shadow_of(img, **shadow)
        canvas.alpha_composite(sh, (round(cx - img.width / 2 - ox), round(cy - img.height / 2 - oy)))
    canvas.alpha_composite(img, (round(cx - img.width / 2), round(cy - img.height / 2)))


def die_cut(img, border=14):
    """White outline around a cut-out, like the stickers."""
    pad = border + 4
    big = Image.new('RGBA', (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    big.alpha_composite(img, (pad, pad))
    a = np.array(big.getchannel('A')) > 40
    outline = nd.binary_fill_holes(nd.binary_dilation(a, structure=disk(border)))
    out = Image.new('RGBA', big.size, WHITE + (0,))
    out.putalpha(Image.fromarray((outline * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1)))
    out.alpha_composite(big)
    return out


def ticket(w=880, h=380):
    """A white festival ticket: '20% OFF' on the main part, a heart-logo stub on the right."""
    s = 2  # draw at 2x, then shrink, for smooth edges
    W2, H2, r, notch = w * s, h * s, 40 * s, 34 * s
    stub_x = int(W2 * 0.76)
    shape = Image.new('L', (W2, H2), 0)
    d = ImageDraw.Draw(shape)
    d.rounded_rectangle((0, 0, W2 - 1, H2 - 1), radius=r, fill=255)
    for x in (stub_x,):  # half-circle notches top and bottom at the tear line
        d.ellipse((x - notch, -notch, x + notch, notch), fill=0)
        d.ellipse((x - notch, H2 - notch, x + notch, H2 + notch), fill=0)
    shape = shape.resize((w, h), Image.LANCZOS)
    stub_x //= s

    t = Image.new('RGBA', (w, h), WHITE + (0,))
    t.putalpha(shape)
    stub = gradient(w - stub_x, h, (MAGENTA, PINK, ORANGE))
    stub.putalpha(shape.crop((stub_x, 0, w, h)))
    t.alpha_composite(stub, (stub_x, 0))
    d = ImageDraw.Draw(t)
    for y in range(40, h - 36, 26):  # perforation
        d.line((stub_x, y, stub_x, y + 12), fill=(210, 200, 230, 255), width=4)

    main_cx = stub_x // 2
    big = gradient_text('20%', 210)
    t.alpha_composite(big, (main_cx - big.width // 2 - 70, 58))
    off = gradient_text('OFF', 112, stops=(MAGENTA, PINK, ORANGE))
    t.alpha_composite(off.rotate(90, expand=True, resample=Image.BICUBIC),
                      (main_cx - big.width // 2 - 70 + big.width + 18, 66))
    sub = text('FESTIVAL TICKETS', 50, fill=INK)
    t.alpha_composite(sub, (main_cx - big.width // 2 - 62, h - sub.height - 58))  # under the '20%'

    logo = Image.open(SRC / 'logo.png').convert('RGBA')
    disc_d = 150
    disc = Image.new('RGBA', (disc_d, disc_d), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse((0, 0, disc_d - 1, disc_d - 1), fill=WHITE + (255,))
    logo.thumbnail((104, 104), Image.LANCZOS)
    disc.alpha_composite(logo, ((disc_d - logo.width) // 2, (disc_d - logo.height) // 2 + 4))
    stub_cx = stub_x + (w - stub_x) // 2
    t.alpha_composite(disc, (stub_cx - disc_d // 2, h // 2 - disc_d // 2 - 30))
    admit = text('ADMIT ONE', 30).rotate(0)
    t.alpha_composite(admit, (stub_cx - admit.width // 2, h // 2 + disc_d // 2 - 10))
    return t


def pill(s, size, bg, fg=WHITE, pad_x=0.6, pad_y=0.28):
    label = text(s, size, fill=fg)
    w, h = int(label.width + size * pad_x * 2), int(label.height + size * pad_y * 2)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if isinstance(bg, tuple):
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg + (255,))
    else:  # an image (gradient) clipped to the pill
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=255)
        bg = bg.resize((w, h))
        bg.putalpha(m)
        img = bg
    img.alpha_composite(label, ((w - label.width) // 2, (h - label.height) // 2))
    return img


def main():
    c = vertical_gradient([(36, 6, 120), PURPLE, MAGENTA, PINK, ORANGE])
    glow(c, (900, 420), 360, (120, 70, 255), 150)
    glow(c, (120, 1250), 380, (255, 90, 160), 120)
    glow(c, (540, 1500), 420, (255, 190, 80), 110)
    confetti(c)

    # Header: logo + festival name
    logo = Image.open(SRC / 'logo.png').convert('RGBA')
    logo.thumbnail((86, 86), Image.LANCZOS)
    disc = Image.new('RGBA', (118, 118), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse((0, 0, 117, 117), fill=WHITE + (255,))
    disc.alpha_composite(logo, ((118 - logo.width) // 2, (118 - logo.height) // 2 + 4))
    name = text('ACTIVATEME FEST', 58)
    row_w = disc.width + 22 + name.width
    x0 = (W - row_w) // 2
    c.alpha_composite(disc, (x0, 230))
    c.alpha_composite(name, (x0 + disc.width + 22, 230 + (disc.height - name.height) // 2))

    # Headline
    put(c, text('GRAB YOUR', 108), W / 2, 435, rotate=3, shadow={'blur': 10, 'offset': (0, 8)})
    put(c, text('TICKETS!', 172), W / 2, 570, rotate=3, shadow={'blur': 12, 'offset': (0, 10)})

    # Ticket
    put(c, ticket(), W / 2, 885, rotate=-4, shadow={'blur': 22, 'offset': (0, 18), 'alpha': 0.45})

    # Acti pointing at you
    acti = die_cut(character('pose_point', 570))
    put(c, acti, W / 2 + 195, 1262, shadow={'blur': 18, 'offset': (0, 16), 'alpha': 0.4})

    # Date tag and a nudge on the left
    put(c, pill(DATES, 50, ORANGE), 265, 1150, rotate=6, shadow={'blur': 10, 'offset': (0, 8)})
    put(c, text("DON'T", 78), 250, 1280, rotate=-5, shadow={'blur': 8, 'offset': (0, 6)})
    put(c, text('MISS', 78), 250, 1360, rotate=-5, shadow={'blur': 8, 'offset': (0, 6)})
    put(c, text('OUT!', 78), 250, 1440, rotate=-5, shadow={'blur': 8, 'offset': (0, 6)})
    put(c, emoji('🎉', 100), 985, 1135, rotate=12)

    # Call to action: put Instagram's link sticker on or just under this button
    btn = pill('BUY TICKETS NOW', 66, WHITE, fg=PURPLE, pad_x=0.75, pad_y=0.34)
    put(c, btn, W / 2, 1600, shadow={'blur': 16, 'offset': (0, 12), 'alpha': 0.4})
    put(c, text(SITE, 40, weight='Bold'), W / 2, 1690)

    OUT.parent.mkdir(exist_ok=True)
    c.convert('RGB').save(OUT, optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
