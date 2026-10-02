"""Cuts the background off the generated Acti poses.

    pip install rembg onnxruntime
    python3 tools/cut_poses.py

For each pose it uses the full-size file in poses/ (e.g. poses/lol.png or .jpg) when there is
one, otherwise the small Canva preview in poses/preview/. Writes source/pose_<name>.png.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parent.parent
POSES = ['lol', 'hmm', 'wave', 'run', 'jump']
MIN_HEIGHT = 1200  # small previews are upscaled to this before cutting, for a smoother edge


def find(name):
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        p = ROOT / 'poses' / f'{name}.{ext}'
        if p.exists():
            return p, False
    return ROOT / 'poses' / 'preview' / f'{name}.jpg', True


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
        m = a[..., 3] > 30
        lab, n = nd.label(m)
        if n:
            sizes = nd.sum(m, lab, range(1, n + 1))
            keep = nd.binary_dilation(lab == (np.argmax(sizes) + 1), iterations=2)
            a[..., 3] = np.where(keep, a[..., 3], 0)
        out = Image.fromarray(a)
        out = out.crop(out.getbbox())
        out.save(ROOT / 'source' / f'pose_{name}.png')
        print(f'{name:6s} from {"preview" if is_preview else "full-size"} {path.name} -> {out.size}')


if __name__ == '__main__':
    main()
