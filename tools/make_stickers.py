"""Builds the Acti sticker pack.

    python3 tools/make_stickers.py

Reads the character cut-outs in source/ and writes:
  stickers/whatsapp/*.webp   512x512, transparent, under 100 KB (WhatsApp's rules)
  stickers/png/*.png         same stickers as PNG, for Telegram, iMessage, Instagram, print
  stickers/whatsapp/tray.png 96x96 pack icon
  stickers/whatsapp/contents.json  pack description in the format WhatsApp's sample apps use
  preview.png                contact sheet of the whole pack

Needs Pillow built with libraqm (for Arabic), numpy and scipy.
"""

import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'source'
OUT = ROOT / 'stickers'
SIZE = 512
MARGIN = 18  # WhatsApp asks for a small margin around each sticker

PURPLE = (74, 1, 224)
MAGENTA = (176, 26, 184)
PINK = (248, 56, 64)
ORANGE = (252, 135, 0)
INK = (27, 11, 70)
WHITE = (255, 255, 255)

EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------

def font(size, arabic=False, weight='ExtraBold'):
    f = ImageFont.truetype(str(ROOT / 'fonts' / ('BalooBhaijaan2.ttf' if arabic else 'Baloo2.ttf')), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def gradient(w, h, stops=(PURPLE, MAGENTA, PINK, ORANGE)):
    x = np.linspace(0, 1, w)[None, :, None]
    seg = len(stops) - 1
    out = np.zeros((1, w, 3))
    for i in range(seg):
        lo, hi = i / seg, (i + 1) / seg
        t = np.clip((x - lo) / (hi - lo), 0, 1)
        c = np.array(stops[i]) + (np.array(stops[i + 1]) - np.array(stops[i])) * t
        mask = (x >= lo) & (x <= hi)
        out = np.where(mask, c, out)
    return Image.fromarray(np.repeat(out, h, 0).astype('uint8')).convert('RGBA')


def text_layer(text, size, fill='gradient', stroke=WHITE, stroke_w=None, arabic=False, max_w=None):
    """Bold caption with a white outline. fill is 'gradient' or an RGB tuple."""
    f = font(size, arabic)
    if max_w:
        while size > 20 and f.getlength(text, direction='rtl' if arabic else None) > max_w:
            size -= 2
            f = font(size, arabic)
    stroke_w = stroke_w if stroke_w is not None else max(4, size // 9)
    kw = {'direction': 'rtl', 'language': 'ar'} if arabic else {}
    l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f, stroke_width=stroke_w, **kw)
    w, h = r - l, b - t
    mask_fill = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask_fill).text((-l, -t), text, font=f, fill=255, stroke_width=0, **kw)
    mask_all = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask_all).text((-l, -t), text, font=f, fill=255, stroke_width=stroke_w, stroke_fill=255, **kw)
    layer = Image.new('RGBA', (w, h), stroke + (0,))
    layer.putalpha(mask_all)
    face = gradient(w, h) if fill == 'gradient' else Image.new('RGBA', (w, h), fill + (255,))
    layer.paste(face, (0, 0), mask_fill)
    return layer


def emoji(ch, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)  # Noto Color Emoji only ships this size
    img = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10, 10), ch, font=f, embedded_color=True)
    img = img.crop(img.getbbox())
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def character(name, height, flip=False, rotate=0):
    img = Image.open(SRC / f'{name}.png').convert('RGBA')
    img = img.crop(img.getbbox())
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img = img.resize((round(img.width * height / img.height), height), Image.LANCZOS)
    if rotate:
        img = img.rotate(rotate, resample=Image.BICUBIC, expand=True)
    return img


def face_badge(diameter):
    """Acti's close-up face cropped into a circle."""
    img = Image.open(SRC / 'face.png').convert('RGBA')
    w, h = img.size
    side = min(w, h - 22)
    img = img.crop(((w - side) // 2, 0, (w + side) // 2, side)).resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new('L', (diameter * 4, diameter * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter * 4 - 1, diameter * 4 - 1), fill=255)
    img.putalpha(mask.resize((diameter, diameter), Image.LANCZOS))
    return img


def label(text, size, bg=PURPLE, fg=WHITE, arabic=False):
    """Text on a rounded pill."""
    f = font(size, arabic)
    kw = {'direction': 'rtl', 'language': 'ar'} if arabic else {}
    l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f, **kw)
    pad_x, pad_y = size * 0.55, size * 0.18
    w, h = int(r - l + pad_x * 2), int(b - t + pad_y * 2)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg + (255,))
    d.text((pad_x - l, pad_y - t), text, font=f, fill=fg, **kw)
    return img


def finish(canvas):
    """Die-cut look: white border around everything, soft shadow, fit inside the margin."""
    canvas = canvas.crop(canvas.getbbox())
    border = 10
    pad = border + 8
    big = Image.new('RGBA', (canvas.width + pad * 2, canvas.height + pad * 2), (0, 0, 0, 0))
    big.alpha_composite(canvas, (pad, pad))
    alpha = np.array(big.getchannel('A')) > 40
    outline = nd.binary_dilation(alpha, structure=disk(border))
    outline = nd.binary_fill_holes(outline)
    outline_img = Image.fromarray((outline * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.8))
    shadow = outline_img.filter(ImageFilter.GaussianBlur(5)).point(lambda v: v * 0.35)
    out = Image.new('RGBA', big.size, (0, 0, 0, 0))
    sh = Image.new('RGBA', big.size, (30, 10, 60, 0))
    sh.putalpha(shadow)
    out.alpha_composite(sh, (0, 3))
    white = Image.new('RGBA', big.size, WHITE + (0,))
    white.putalpha(outline_img)
    out.alpha_composite(white)
    out.alpha_composite(big)
    out = out.crop(out.getbbox())
    inner = SIZE - MARGIN * 2
    scale = min(inner / out.width, inner / out.height)
    out = out.resize((round(out.width * scale), round(out.height * scale)), Image.LANCZOS)
    final = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    final.alpha_composite(out, ((SIZE - out.width) // 2, (SIZE - out.height) // 2))
    return final


_disks = {}


def disk(r):
    if r not in _disks:
        y, x = np.ogrid[-r:r + 1, -r:r + 1]
        _disks[r] = x * x + y * y <= r * r
    return _disks[r]


class Board:
    """A big working canvas; elements are placed by their centre."""

    def __init__(self, w=900, h=900):
        self.img = Image.new('RGBA', (w, h), (0, 0, 0, 0))

    def put(self, layer, cx, cy, rotate=0):
        if rotate:
            layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
        self.img.alpha_composite(layer, (round(cx - layer.width / 2), round(cy - layer.height / 2)))
        return self


# --------------------------------------------------------------------------
# The stickers
# --------------------------------------------------------------------------

def caption_top(name, en, ar=None, pose='front', h=560, flip=False, tilt=0, props=(), en_size=130, text_tilt=4):
    b = Board()
    b.put(character(pose, h, flip=flip), 450, 520, rotate=tilt)
    for ch, size, x, y, rot in props:
        b.put(emoji(ch, size), x, y, rot)
    y = 140
    b.put(text_layer(en, en_size, max_w=820), 450, y, text_tilt)
    if ar:
        b.put(label(ar, 70, bg=ORANGE, arabic=True), 450, y + en_size * 0.82, -3)
    return name, finish(b.img), [e for e in emojis_for(name)]


def emojis_for(name):
    return EMOJI_TAGS.get(name, ['🧡'])


EMOJI_TAGS = {
    'yalla': ['🏃', '🔥'], 'lets_go': ['⚡', '🙌'], 'whos_in': ['🙋', '❓'], 'on_my_way': ['🏃', '🚗'],
    'bye': ['👋'], 'hi': ['👋', '😊'], 'shukran': ['🙏', '🧡'], 'mabrook': ['🎉', '🥳'],
    'good_morning': ['☀️', '😊'], 'game_on': ['⚽', '💪'], 'activated': ['⚡', '💪'],
    'save_the_date': ['📅', '🎉'], 'habibi': ['🤗', '🧡'], 'hmm': ['🤔'], 'love_it': ['❤️', '😍'],
    'lol': ['😂'], 'weekend': ['🤸', '❓'], 'activateme': ['🧡', '🎉'],
}


def build():
    """Each sticker uses a different pose. Stickers waiting on new poses are listed in poses/PROMPTS.md."""
    s = []
    s.append(caption_top('lol', 'LOL', pose='pose_lol', h=600, en_size=150, text_tilt=-4,
                         props=[('😂', 120, 700, 330, -12)]))
    s.append(caption_top('hmm', 'HMM…', pose='pose_hmm', h=600, en_size=140, props=[('🤔', 110, 700, 330, 8)]))
    s.append(caption_top('hi', 'HI!', 'مرحبا', pose='pose_wave', h=580, en_size=150))

    b = Board()
    b.put(character('pose_run', 590), 470, 530)
    b.put(emoji('💨', 150), 230, 640, 0)
    b.put(text_layer('ON MY WAY!', 120, max_w=820), 450, 140, 3)
    s.append(('on_my_way', finish(b.img), emojis_for('on_my_way')))

    s.append(caption_top('mabrook', 'MABROOK!', 'مبروك', pose='pose_jump', h=560, en_size=120,
                         props=[('🎉', 120, 200, 420, -15), ('🎊', 110, 700, 430, 12)]))

    b = Board()
    b.put(character('back', 560), 450, 520)
    b.put(emoji('👋', 120), 650, 340, -15)
    b.put(text_layer('BYE BYE!', 130), 450, 140, -3)
    s.append(('bye', finish(b.img), emojis_for('bye')))

    # Psst: face peeking with a speech bubble
    b = Board()
    b.put(face_badge(560), 450, 560)
    b.put(label('PSST…', 100, bg=PURPLE), 650, 220, 8)
    b.put(emoji('👀', 120), 230, 250, 10)
    s.append(('psst', finish(b.img), ['👀', '🤫']))

    b = Board()
    b.put(face_badge(520), 450, 520)
    for x, y, r, sz in [(170, 230, -15, 120), (740, 200, 15, 110), (780, 620, 10, 90)]:
        b.put(emoji('❤️', sz), x, y, r)
    b.put(text_layer('LOVE IT!', 125), 450, 820, -3)
    s.append(('love_it', finish(b.img), emojis_for('love_it')))

    # Acti's open arms read as a welcome
    s.append(caption_top('habibi', 'HABIBI, COME!', 'حبيبي تعال', pose='front', en_size=105,
                         props=[('🤗', 110, 680, 420, 0)]))

    b = Board()
    b.put(character('threequarter', 520), 450, 560)
    b.put(text_layer('SEE YOU THERE!', 100, max_w=820), 450, 130, 3)
    b.put(label('16–17 JAN 2027', 62, bg=ORANGE), 450, 230, -3)
    b.put(emoji('📅', 110), 680, 440, -10)
    s.append(('save_the_date', finish(b.img), emojis_for('save_the_date')))

    # Brand sticker: logo + name
    b = Board()
    logo = Image.open(SRC / 'logo.png').convert('RGBA')
    logo.thumbnail((380, 380), Image.LANCZOS)
    disc = Image.new('RGBA', (460, 460), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse((0, 0, 459, 459), fill=WHITE + (255,))
    disc.alpha_composite(logo, ((460 - logo.width) // 2, (460 - logo.height) // 2 + 10))
    b.put(disc, 450, 360)
    b.put(label('ACTIVATEME FEST', 80, bg=PURPLE), 450, 640, -3)
    s.append(('activateme', finish(b.img), emojis_for('activateme')))
    return s


def save_webp(img, path):
    for q in (90, 85, 80, 75, 70, 60, 50):
        buf = io.BytesIO()
        img.save(buf, 'WEBP', quality=q, method=6)
        if buf.tell() < 100 * 1024:
            path.write_bytes(buf.getvalue())
            return buf.tell()
    raise RuntimeError(f'{path.name} is over 100 KB')


def main():
    for sub in ('whatsapp', 'png'):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
        for old in (OUT / sub).glob('[0-9][0-9]_*'):
            old.unlink()
    stickers = build()
    entries = []
    for i, (name, img, tags) in enumerate(stickers, 1):
        fname = f'{i:02d}_{name}'
        size = save_webp(img, OUT / 'whatsapp' / f'{fname}.webp')
        img.save(OUT / 'png' / f'{fname}.png', optimize=True)
        entries.append({'image_file': f'{fname}.webp', 'emojis': tags})
        print(f'{fname:24s} {size / 1024:5.1f} KB')

    tray = face_badge(96)
    tray.save(OUT / 'whatsapp' / 'tray.png', optimize=True)

    contents = {
        'android_play_store_link': '',
        'ios_app_store_link': '',
        'sticker_packs': [{
            'identifier': 'acti_v1',
            'name': 'Acti · ActivateMe Fest',
            'publisher': 'ActivateMe Fest',
            'tray_image_file': 'tray.png',
            'publisher_website': 'https://www.activatemefest.com',
            'image_data_version': '1',
            'avoid_cache': False,
            'animated_sticker_pack': False,
            'stickers': entries,
        }],
    }
    (OUT / 'whatsapp' / 'contents.json').write_text(json.dumps(contents, indent=2, ensure_ascii=False))

    # Contact sheet on a chat-like background
    cols = 6
    rows = math.ceil(len(stickers) / cols)
    cell = 220
    sheet = Image.new('RGBA', (cols * cell + 40, rows * cell + 40), (236, 229, 221, 255))
    for i, (_, img, _) in enumerate(stickers):
        t = img.resize((200, 200), Image.LANCZOS)
        sheet.alpha_composite(t, (20 + (i % cols) * cell + 10, 20 + (i // cols) * cell + 10))
    sheet.convert('RGB').save(ROOT / 'preview.png')
    print(f'{len(stickers)} stickers written')


if __name__ == '__main__':
    main()
