#!/usr/bin/env python3
"""Local, raster-only screenshot guide renderer. Coordinates: EXIF-oriented pixels."""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import tempfile
import shutil
from PIL import Image, ImageOps, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

Image.MAX_IMAGE_PIXELS = 40_000_000
ROOT_KEYS = {'version','title','audience','status','notice','steps','font_size','language'}
STEP_KEYS = {'title','action','image','highlights','arrows','crop','redactions','check','evidence','uncertainty'}

def font_path():
    candidates = [os.environ.get('GUIDE_FONT',''), '/System/Library/Fonts/STHeiti Medium.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc']
    for p in candidates:
        if p and Path(p).is_file(): return p
    raise ValueError('Set GUIDE_FONT to a CJK font with Simplified/Traditional Chinese and English coverage')

def text(value, name, required=False):
    if not isinstance(value,str) or len(value)>4000 or (required and not value.strip()):
        raise ValueError(f'{name}: expected nonempty text <=4000 characters')
    if any(ord(c)<32 and c not in '\n\t' for c in value): raise ValueError(f'{name}: control character')
    return value

def rect(r, size):
    if not isinstance(r,list) or len(r)!=4 or any(type(n) not in (int,float) or not math.isfinite(n) for n in r): raise ValueError('rectangle must be [x,y,width,height]')
    x,y,w,h=r
    if min(x,y)<0 or min(w,h)<=0 or x+w>size[0] or y+h>size[1]: raise ValueError('rectangle outside oriented image')
    return tuple(round(v) for v in (x,y,x+w,y+h))

def load(spec_path):
    spec_path=Path(spec_path).resolve()
    if spec_path.stat().st_size>1_000_000: raise ValueError('spec too large')
    data=json.loads(spec_path.read_text('utf-8'))
    if not isinstance(data,dict) or set(data)-ROOT_KEYS: raise ValueError('unknown root fields')
    if type(data.get('version'))!=int or data.get('version')!=1: raise ValueError('version must be 1')
    text(data.get('title'),'title',True)
    if data.get('audience','beginner') not in ('beginner','parents','customer','expert'): raise ValueError('invalid audience')
    if data.get('status') not in ('complete','draft'): raise ValueError('explicit complete/draft status required')
    if data.get('language','zh-CN') not in ('zh-CN','zh-TW','en'): raise ValueError('invalid language')
    fs=data.get('font_size',44 if data.get('audience')=='parents' else 40 if data.get('audience','beginner')=='beginner' else 36)
    if type(fs)!=int or not 28<=fs<=56: raise ValueError('font_size must be integer 28..56')
    data['font_size']=fs
    for key in ('notice',): text(data.get(key,''),key)
    steps=data.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=40: raise ValueError('require 1..40 steps')
    loaded=[]; hashes=set(); warnings=[]; total_pixels=0
    for s in steps:
        if not isinstance(s,dict) or set(s)-STEP_KEYS: raise ValueError('unknown step fields')
        for k in ('title','action'): text(s.get(k),k,True)
        for k in ('check','evidence','uncertainty'): text(s.get(k,''),k)
        name=text(s.get('image'),'image',True)
        p=(spec_path.parent/name).resolve()
        if Path(name).is_absolute() or not p.is_relative_to(spec_path.parent): raise ValueError('image must stay within spec directory (including symlinks)')
        if not p.is_file(): raise ValueError(f'missing image: {name}')
        if p.stat().st_size>40_000_000: raise ValueError('image file too large')
        with Image.open(p) as raw:
            if raw.format not in ('PNG','JPEG','WEBP'): raise ValueError('use PNG/JPEG/WEBP')
            total_pixels+=raw.width*raw.height
            if raw.width*raw.height>40_000_000 or total_pixels>100_000_000: raise ValueError('pixel budget exceeded: 40M per image / 100M total')
            raw.load(); im=ImageOps.exif_transpose(raw).convert('RGB')
        digest=hashlib.sha256(im.tobytes()).hexdigest()
        if digest in hashes: warnings.append('Duplicate screenshot: check whether repetition is intentional')
        hashes.add(digest)
        for k in ('highlights','redactions'):
            rs=s.get(k,[])
            if not isinstance(rs,list) or len(rs)>50: raise ValueError('invalid region list')
            for r in rs: rect(r,im.size)
        if 'crop' in s: rect(s['crop'],im.size)
        arrows=s.get('arrows',[])
        if not isinstance(arrows,list) or len(arrows)>50: raise ValueError('invalid arrow list')
        for a in arrows:
            if not isinstance(a,list) or len(a)!=4: raise ValueError('arrow [x1,y1,x2,y2] required')
            for x,y in (a[:2],a[2:]): rect([x,y,1,1],im.size)
        # Erase pixels BEFORE any resize, crop, annotation, or PDF embedding.
        draw=ImageDraw.Draw(im)
        for r in s.get('redactions',[]): draw.rectangle(rect(r,im.size),fill='#303844')
        loaded.append((s,im))
    return data,loaded,warnings

def wrap(draw, content, f, width):
    lines=[]
    for paragraph in content.split('\n'):
        units=re.findall(r'「[^」\n]{1,20}」|“[^”\n]{1,20}”|[A-Za-z0-9]+(?:[-’][A-Za-z0-9]+)*[.,:;!?]?|.',paragraph)
        tokens=[]
        for unit in units:
            if unit in '。，、；：！？）」”' and tokens: tokens[-1]+=unit
            else: tokens.append(unit)
        line=''
        for token in tokens:
            parts=[token] if draw.textlength(token,font=f)<=width else list(token)
            for part in parts:
                if draw.textlength(line+part,font=f)>width:
                    if line.strip(): lines.append(line.rstrip())
                    line=part.lstrip()
                else: line+=part
        lines.append(line.rstrip())
    return lines

def panel(s, im, box=None, maxh=650):
    # Draw in oriented source coordinates; crop and resize together afterwards.
    annotated=im.copy(); d=ImageDraw.Draw(annotated)
    line=max(3,round(im.width/160))
    for r in s.get('highlights',[]): d.rectangle(rect(r,im.size),outline='#b33900',width=line)
    for a in s.get('arrows',[]):
        x,y,u,v=a; d.line((x,y,u,v),fill='#b33900',width=line)
        angle=math.atan2(v-y,u-x); length=max(14,line*4)
        d.polygon([(u,v),(u-length*math.cos(angle-.5),v-length*math.sin(angle-.5)),(u-length*math.cos(angle+.5),v-length*math.sin(angle+.5))],fill='#b33900')
    if box: annotated=annotated.crop(rect(box,im.size))
    scale=min(880/annotated.width,maxh/annotated.height)
    return annotated.resize((max(1,round(annotated.width*scale)),max(1,round(annotated.height*scale))),Image.Resampling.LANCZOS)

def cards(data, loaded):
    fp=font_path(); fs=data['font_size']; f=ImageFont.truetype(fp,fs); bold=ImageFont.truetype(fp,42)
    en=data.get('language')=='en'; draft=data['status']=='draft'
    result=[]
    for i,(s,im) in enumerate(loaded,1):
        chunks=[(data['title'],bold),(('DRAFT · INCOMPLETE' if en else '待补全草稿') if draft else ('Step' if en else '操作步骤'),f),(f"{i:02d}  {s['title']}",bold),(s['action'],f)]
        for key, label in [('check','Check: ' if en else '点击后检查：'),('evidence','Shown: ' if en else '截图已证明：'),('uncertainty','Uncertain: ' if en else '不确定：')]:
            if s.get(key): chunks.append((label+s[key],f))
        if data.get('notice'): chunks.append((data['notice'],f))
        probe=ImageDraw.Draw(Image.new('RGB',(1,1))); lines=[]
        for content,font in chunks:
            for line in wrap(probe,content,font,880): lines.append((line,font))
            lines.append(('',f))
        text_h=sum(font.size+10 for _,font in lines)
        pics=[panel(s,im)]
        if s.get('crop'): pics.append(panel(s,im,s['crop'],400))
        h=50+text_h+sum(p.height+30 for p in pics)+70+(fs+10 if len(pics)>1 else 0)
        if h>2330: raise ValueError(f'step {i}: too much text; split into smaller actions (no automatic shrinking)')
        card=Image.new('RGB',(1000,h),'#ffffff'); d=ImageDraw.Draw(card); y=40
        for line,font in lines:
            d.text((60,y),line,font=font,fill='#152536'); y+=font.size+10
        for j,p in enumerate(pics):
            if j: d.text((60,y),'Detail' if en else '局部放大',font=f,fill='#152536'); y+=fs+10
            card.paste(p,((1000-p.width)//2,y)); y+=p.height+30
        # Account for the zoom label in the allocated card height.
        if y>h-25: raise ValueError('layout overflow')
        result.append(card)
    return result

def export(spec,out,fmt):
    data,loaded,warnings=load(spec); rendered=cards(data,loaded)
    out=Path(out).absolute()
    if out.exists(): raise ValueError('output already exists; choose a new revision directory')
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.guide-',dir=out.parent))
    try:
        if fmt in ('pdf','both'):
            c=canvas.Canvas(str(temp/'guide.pdf'),pagesize=(595.276,841.89),pageCompression=1)
            c.setTitle('Screenshot guide'); c.setAuthor(''); c.setCreator('screenshot-to-guide')
            for card in rendered:
                scale=min(555.276/card.width,801.89/card.height)
                c.drawImage(ImageReader(card), (595.276-card.width*scale)/2,841.89-20-card.height*scale,width=card.width*scale,height=card.height*scale)
                c.showPage()
            c.save()
        if fmt in ('png','both'):
            # Whole steps stay together; bounded height prevents tiny text in giant images.
            groups=[]; group=[]; height=0
            for card in rendered:
                if group and height+card.height>3000: groups.append(group); group=[]; height=0
                group.append(card); height+=card.height
            if group: groups.append(group)
            for n,group in enumerate(groups,1):
                image=Image.new('RGB',(1000,sum(x.height for x in group)),'white'); y=0
                for card in group: image.paste(card,(0,y)); y+=card.height
                image.save(temp/f'guide-{n:02d}.png')
        (temp/'review.txt').write_text('Review before sharing: automatic privacy detection is incomplete.\n'+'\n'.join(warnings),'utf-8')
        temp.rename(out)
    except Exception:
        shutil.rmtree(temp); raise
    return warnings

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('spec'); parser.add_argument('--out'); parser.add_argument('--format',choices=['pdf','png','both'],default='pdf'); parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    try:
        if args.validate:
            data,loaded,warnings=load(args.spec); print(json.dumps({'steps':len(loaded),'sizes':[im.size for _,im in loaded],'warnings':warnings},ensure_ascii=False))
        else:
            if not args.out: parser.error('--out is required')
            warnings=export(args.spec,args.out,args.format); print(json.dumps({'output':str(Path(args.out).absolute()),'warnings':warnings},ensure_ascii=False))
    except (ValueError,OSError,TypeError,KeyError,Image.DecompressionBombError) as exc: parser.exit(2,f'Error: {exc}\n')
if __name__=='__main__': main()
