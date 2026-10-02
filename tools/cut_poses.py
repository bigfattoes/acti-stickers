"""Cuts the background off the generated Acti poses.

    pip install rembg onnxruntime
    python3 tools/cut_poses.py

For each pose it uses the full-size Canva download in poses/ (e.g. poses/laugh.png) when there
is one, otherwise the 600 px copy in poses/canva600/. Writes source/pose_<name>.png.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parent.parent
POSES = [
    # emotions
    'laugh', 'think', 'wave', 'run', 'jump', 'thumbs', 'heart', 'yawn', 'thanks',
    'shocked', 'cry', 'point', 'flex', 'dance',
    # sports and activities
    'football', 'basketball', 'cricket', 'tennis', 'swimming', 'gymnastics',
    'boxing', 'skating', 'cycling', 'vr', 'chess', 'creativity',
]
MIN_HEIGHT = 1200  # smaller images are upscaled to this before cutting, for a smoother edge


def find(name):
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        p = ROOT / 'poses' / f'{name}.{ext}'
        if p.exists():
            return p, False
    return ROOT / 'poses' / 'canva600' / f'{name}.png', True


def main():
    session = new_session('isnet-general-use')
    for name in POSES:
        path, is_preview = find(name)
        img = Image.open(path).convert('RGB')
        if img.height < MIN_HEIGHT:
            k = MIN_HEIGHT / img.height
            img = img.resize((round(img.width * k), MIN_HEIGHT), Image.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        cut = remove(img, session=session)
        a = np.array(cut)
        # The images are on pure white: anything strongly coloured is part of the picture even
        # if the cut-out model missed it (e.g. a red cricket ball).
        rgb = np.array(img).astype(int)
        dist = np.sqrt(((255 - rgb) ** 2).sum(axis=2))
        colour = np.clip((dist - 90) * 4, 0, 255)
        a[..., 3] = np.maximum(a[..., 3], colour).astype('uint8')
        a[..., :3] = rgb.astype('uint8')  # true colours from the original, not the cut-out's
        m = a[..., 3] > 30
        lab, n = nd.label(m)
        if n:
            sizes = nd.sum(m, lab, range(1, n + 1))
            # Keep Acti plus any props floating free of him (a ball in mid-air), drop specks.
            big = [i + 1 for i, v in enumerate(sizes) if v >= 0.01 * sizes.max()]
            keep = nd.binary_dilation(np.isin(lab, big), iterations=2)
            a[..., 3] = np.where(keep, a[..., 3], 0)
        # Firm up half-transparent areas (motion-blurred balls come out see-through).
        alpha = a[..., 3].astype(float)
        a[..., 3] = np.clip((alpha - 25) * 1.6, 0, 255).astype('uint8')
        out = Image.fromarray(a)
        out = out.crop(out.getbbox())
        out.save(ROOT / 'source' / f'pose_{name}.png')
        print(f'{name:11s} from {"600px copy" if is_preview else "full-size"} {path.name} -> {out.size}')


if __name__ == '__main__':
    main()
