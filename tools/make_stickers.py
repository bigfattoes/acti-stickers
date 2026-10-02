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
    'lol': ['😂'], 'hmm': ['🤔'], 'hi': ['👋', '😊'], 'on_my_way': ['🏃', '🚗'], 'mabrook': ['🎉', '🥳'],
    'lets_go': ['👍', '🙌'], 'love_you': ['❤️', '😍'], 'good_morning': ['☀️', '😊'], 'shukran': ['🙏', '🧡'],
    'omg': ['😱', '😮'], 'nooo': ['😭', '😢'], 'habibi': ['🤗', '👉'], 'activated': ['💪', '⚡'],
    'yalla': ['💃', '🎉'], 'bye': ['👋'], 'psst': ['👀', '🤫'], 'see_you_there': ['📅', '🎉'],
    'activateme': ['🧡', '🎉'],
    'goal': ['⚽'], 'swish': ['🏀'], 'howzat': ['🏏'], 'ace': ['🎾'], 'splash': ['🏊'], 'flip': ['🤸'],
    'knockout': ['🥊'], 'wheee': ['⛸️'], 'ride_on': ['🚴'], 'game_on': ['🎮'], 'checkmate': ['♟️'],
    'get_creative': ['🎨'],
}



def pose_sticker(name, en, pose, ar=None, h=600, en_size=130, tilt=0, text_tilt=4, props=(), tag=None):
    """Caption on top, Acti below. `tag` is a small pill under the caption (e.g. the sport's name)."""
    b = Board()
    b.put(character(pose, h), 450, 540, rotate=tilt)
    for ch, size, x, y, rot in props:
        b.put(emoji(ch, size), x, y, rot)
    y = 135
    b.put(text_layer(en, en_size, max_w=840), 450, y, text_tilt)
    if ar:
        b.put(label(ar, 70, bg=ORANGE, arabic=True), 450, y + en_size * 0.82, -3)
    if tag:
        b.put(label(tag, 54, bg=PURPLE), 450, y + en_size * 0.8, -3)
    return name, finish(b.img), emojis_for(name)


def build_main():
    """Acti: everyday reactions. Every sticker has its own pose."""
    s = []
    s.append(pose_sticker('lol', 'LOL', 'pose_laugh', en_size=150, text_tilt=-4, props=[('😂', 110, 720, 300, -12)]))
    s.append(pose_sticker('hmm', 'HMM…', 'pose_think', en_size=140, props=[('🤔', 100, 720, 330, 8)]))
    s.append(pose_sticker('hi', 'HI!', 'pose_wave', ar='مرحبا', en_size=150))
    s.append(pose_sticker('on_my_way', 'ON MY WAY!', 'pose_run', en_size=120, text_tilt=3, props=[('💨', 130, 170, 640, 0)]))
    s.append(pose_sticker('mabrook', 'MABROOK!', 'pose_jump', ar='مبروك', en_size=120,
                          props=[('🎉', 110, 170, 420, -15), ('🎊', 100, 730, 430, 12)]))
    s.append(pose_sticker('lets_go', "LET'S GO!", 'pose_thumbs', en_size=130))
    s.append(pose_sticker('love_you', 'LOVE YOU!', 'pose_heart', en_size=130,
                          props=[('❤️', 90, 190, 360, -15), ('❤️', 70, 720, 330, 15)]))
    s.append(pose_sticker('good_morning', 'GOOD MORNING!', 'pose_yawn', ar='صباح الخير', en_size=100,
                          props=[('☀️', 110, 740, 360, 0)]))
    s.append(pose_sticker('shukran', 'SHUKRAN!', 'pose_thanks', ar='شكراً', en_size=120, props=[('🧡', 90, 700, 420, 10)]))
    s.append(pose_sticker('omg', 'OMG!', 'pose_shocked', en_size=160, text_tilt=-5))
    s.append(pose_sticker('nooo', 'NOOO!', 'pose_cry', en_size=150))
    s.append(pose_sticker('habibi', 'HABIBI, COME!', 'pose_point', ar='حبيبي تعال', en_size=105))
    s.append(pose_sticker('activated', 'ACTIVATED!', 'pose_flex', en_size=115, props=[('⚡', 110, 140, 420, 15), ('⚡', 110, 760, 420, -15)]))
    s.append(pose_sticker('yalla', 'YALLA!', 'pose_dance', ar='يلا!', en_size=150, props=[('🎶', 100, 740, 380, -10)]))

    b = Board()
    b.put(character('back', 560), 450, 520)
    b.put(emoji('👋', 120), 650, 340, -15)
    b.put(text_layer('BYE BYE!', 130), 450, 140, -3)
    s.append(('bye', finish(b.img), emojis_for('bye')))

    b = Board()
    b.put(face_badge(560), 450, 560)
    b.put(label('PSST…', 100, bg=PURPLE), 650, 220, 8)
    b.put(emoji('👀', 120), 230, 250, 10)
    s.append(('psst', finish(b.img), emojis_for('psst')))

    b = Board()
    b.put(character('threequarter', 520), 450, 560)
    b.put(text_layer('SEE YOU THERE!', 100, max_w=820), 450, 130, 3)
    b.put(label('16–17 JAN 2027', 62, bg=ORANGE), 450, 230, -3)
    b.put(emoji('📅', 110), 680, 440, -10)
    s.append(('see_you_there', finish(b.img), emojis_for('see_you_there')))

    s.append(brand_sticker())
    return s


def build_sports():
    """Acti Sports: one sticker per festival activity."""
    sports = [
        ('goal', 'GOAL!', 'pose_football', 'FOOTBALL'),
        ('swish', 'SWISH!', 'pose_basketball', 'BASKETBALL'),
        ('howzat', 'HOWZAT!', 'pose_cricket', 'CRICKET'),
        ('ace', 'ACE!', 'pose_tennis', 'TENNIS'),
        ('splash', 'SPLASH!', 'pose_swimming', 'SWIMMING'),
        ('flip', 'FLIP MODE!', 'pose_gymnastics', 'GYMNASTICS'),
        ('knockout', 'KNOCKOUT!', 'pose_boxing', 'BOXING'),
        ('wheee', 'WHEEE!', 'pose_skating', 'SKATING'),
        ('ride_on', 'RIDE ON!', 'pose_cycling', 'CYCLING'),
        ('game_on', 'GAME ON!', 'pose_vr', 'VR & ESPORTS'),
        ('checkmate', 'CHECKMATE!', 'pose_chess', 'CHESS'),
        ('get_creative', 'GET CREATIVE!', 'pose_creativity', 'CREATIVITY'),
    ]
    s = [pose_sticker(name, en, pose, tag=tag, en_size=125, text_tilt=(4 if i % 2 else -4))
         for i, (name, en, pose, tag) in enumerate(sports)]
    s.append(brand_sticker())
    return s


def brand_sticker():
    b = Board()
    logo = Image.open(SRC / 'logo.png').convert('RGBA')
    logo.thumbnail((380, 380), Image.LANCZOS)
    disc = Image.new('RGBA', (460, 460), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse((0, 0, 459, 459), fill=WHITE + (255,))
    disc.alpha_composite(logo, ((460 - logo.width) // 2, (460 - logo.height) // 2 + 10))
    b.put(disc, 450, 360)
    b.put(label('ACTIVATEME FEST', 80, bg=PURPLE), 450, 640, -3)
    return ('activateme', finish(b.img), emojis_for('activateme'))


def tray_from(pose):
    """96x96 pack icon: the head of a pose cut-out."""
    img = Image.open(SRC / f'{pose}.png').convert('RGBA')
    img = img.crop(img.getbbox())
    side = min(img.width, int(img.height * 0.55))
    head = img.crop(((img.width - side) // 2, 0, (img.width + side) // 2, side))
    head.thumbnail((96, 96), Image.LANCZOS)
    tray = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
    tray.alpha_composite(head, ((96 - head.width) // 2, (96 - head.height) // 2))
    return tray


def save_webp(img, path):
    for q in (90, 85, 80, 75, 70, 60, 50):
        buf = io.BytesIO()
        img.save(buf, 'WEBP', quality=q, method=6)
        if buf.tell() < 100 * 1024:
            path.write_bytes(buf.getvalue())
            return buf.tell()
    raise RuntimeError(f'{path.name} is over 100 KB')


def contact_sheet(stickers, path, title):
    cols = 6
    rows = math.ceil(len(stickers) / cols)
    cell = 220
    top = 90
    sheet = Image.new('RGBA', (cols * cell + 40, rows * cell + 40 + top), (236, 229, 221, 255))
    d = ImageDraw.Draw(sheet)
    d.text((30, 28), title, font=font(46), fill=INK)
    for i, (_, img, _) in enumerate(stickers):
        t = img.resize((200, 200), Image.LANCZOS)
        sheet.alpha_composite(t, (20 + (i % cols) * cell + 10, top + 20 + (i // cols) * cell + 10))
    sheet.convert('RGB').save(path)


PACKS = [
    # id, name, builder, tray pose, preview file
    ('acti', 'Acti · ActivateMe Fest', build_main, 'pose_wave', 'preview.png'),
    ('acti_sports', 'Acti Sports · ActivateMe Fest', build_sports, 'pose_football', 'preview-sports.png'),
]


def main():
    import shutil
    if OUT.exists():
        shutil.rmtree(OUT)
    packs_json = []
    for pack_id, pack_name, builder, tray_pose, preview in PACKS:
        wa = OUT / 'whatsapp' / pack_id
        png = OUT / 'png' / pack_id
        wa.mkdir(parents=True)
        png.mkdir(parents=True)
        stickers = builder()
        assert 3 <= len(stickers) <= 30, f'{pack_id}: WhatsApp packs need 3–30 stickers'
        entries = []
        for i, (name, img, tags) in enumerate(stickers, 1):
            fname = f'{i:02d}_{name}'
            size = save_webp(img, wa / f'{fname}.webp')
            img.save(png / f'{fname}.png', optimize=True)
            entries.append({'image_file': f'{fname}.webp', 'emojis': tags})
            print(f'{pack_id:12s} {fname:22s} {size / 1024:5.1f} KB')
        tray_from(tray_pose).save(wa / 'tray.png', optimize=True)
        packs_json.append({
            'identifier': pack_id,
            'name': pack_name,
            'publisher': 'ActivateMe Fest',
            'tray_image_file': 'tray.png',
            'publisher_website': 'https://www.activatemefest.com',
            'image_data_version': '2',
            'avoid_cache': False,
            'animated_sticker_pack': False,
            'stickers': entries,
        })
        contact_sheet(stickers, ROOT / preview, pack_name)
    contents = {'android_play_store_link': '', 'ios_app_store_link': '', 'sticker_packs': packs_json}
    (OUT / 'whatsapp' / 'contents.json').write_text(json.dumps(contents, indent=2, ensure_ascii=False))
    print(f'{sum(len(p["stickers"]) for p in packs_json)} stickers in {len(packs_json)} packs')


if __name__ == '__main__':
    main()
