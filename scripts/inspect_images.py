#!/usr/bin/env python3
"""Create PRIVATE oriented previews. Never deliver these unredacted copies."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageOps
p=argparse.ArgumentParser(description=__doc__); p.add_argument('images',nargs='+'); p.add_argument('--out',required=True); a=p.parse_args()
out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
for i,path in enumerate(a.images,1):
    with Image.open(path) as raw:
        im=ImageOps.exif_transpose(raw).convert('RGB'); dest=out/f'{i:02d}.png'; im.save(dest)
        print(json.dumps({'preview':str(dest.resolve()),'oriented_size':im.size},ensure_ascii=False))
