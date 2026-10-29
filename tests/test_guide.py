import copy,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import guide

class GuideTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        im=Image.new('RGB',(600,900),'white'); d=ImageDraw.Draw(im)
        d.rectangle((100,200,200,260),fill='#abcdef'); d.text((30,50),'SECRET-729',font=ImageFont.truetype(guide.font_path(),30),fill='black'); im.save(self.root/'in.png')
        self.spec={'version':1,'title':'操作 <script>alert(1)</script> & "测试"','audience':'parents','status':'draft','steps':[{'title':'點擊設定','action':'点击按钮，然后检查。','image':'in.png','highlights':[[98,198,104,64]],'arrows':[[150,150,150,196]],'crop':[50,150,250,180],'redactions':[[0,0,400,100]]}]}
    def tearDown(self): self.tmp.cleanup()
    def write(self,spec=None):
        p=self.root/'guide.json'; p.write_text(json.dumps(spec or self.spec,ensure_ascii=False)); return p
    def test_raster_privacy_and_consistency(self):
        p=self.write(); data,loaded,_=guide.load(p)
        self.assertEqual(set(loaded[0][1].crop((0,0,400,100)).tobytes()[j:j+3] for j in range(0,400*100*3,3)),{bytes((48,56,68))})
        before=(self.root/'in.png').read_bytes()
        guide.export(p,self.root/'out','both')
        self.assertEqual(before,(self.root/'in.png').read_bytes())
        pdf=PdfReader(self.root/'out/guide.pdf')
        self.assertEqual(len(pdf.pages),1); self.assertEqual(pdf.pages[0].extract_text(),'')
        self.assertFalse(pdf.pages[0].get('/Annots')); self.assertNotIn('/EmbeddedFiles',pdf.trailer['/Root'].get('/Names',{}))
        self.assertNotIn('/AcroForm',pdf.trailer['/Root'])
        png=Image.open(self.root/'out/guide-01.png').convert('RGB'); embedded=pdf.pages[0].images[0].image.convert('RGB')
        self.assertEqual(png.size,embedded.size); self.assertEqual(png.tobytes(),embedded.tobytes())
        self.assertNotIn(b'SECRET', (self.root/'out/guide.pdf').read_bytes())
        self.assertNotIn('SECRET',str(pdf.metadata))
        self.assertEqual(list((self.root/'out').glob('*.html')),[])
    def test_delivered_examples_privacy(self):
        base=Path(__file__).resolve().parents[1]/'examples'
        for name in ('parents','customer'):
            data,loaded,_=guide.load(base/name/'guide.json')
            expected=guide.cards(data,loaded); pdf=PdfReader(base/name/'final/guide.pdf')
            self.assertEqual(len(expected),len(pdf.pages))
            for index,(card,page) in enumerate(zip(expected,pdf.pages),1):
                self.assertEqual(page.extract_text(),''); self.assertFalse(page.get('/Annots'))
                self.assertEqual(len(page.images),1)
                self.assertEqual(page.images[0].image.convert('RGB').tobytes(),card.tobytes())
                with Image.open(base/name/'final'/f'guide-{index:02d}.png') as png:
                    self.assertEqual(png.convert('RGB').tobytes(),card.tobytes())
            self.assertNotIn('/Names',pdf.trailer['/Root']); self.assertNotIn('/Metadata',pdf.trailer['/Root'])
            for secret in ('SECRET-ADDRESS-729','13800001234','6200 1234 5678'):
                self.assertNotIn(secret,str(pdf.metadata))
            if name=='customer':
                for _,image in loaded:
                    region=image.crop((25,690,575,840))
                    self.assertEqual(region.getextrema(),((48,48),(56,56),(68,68)))

    def test_readable_word_wrap(self):
        draw=ImageDraw.Draw(Image.new('RGB',(1,1))); f=ImageFont.truetype(guide.font_path(),40)
        lines=guide.wrap(draw,'Check the Settings entry. 點擊「開啟」後，檢查畫面。',f,260)
        self.assertTrue(any('entry.' in line for line in lines))
        self.assertTrue(any('「開啟」' in line for line in lines))
        self.assertTrue(all(draw.textlength(line,font=f)<=260 for line in lines))
        self.assertTrue(all(not line.startswith(('。','，','.')) for line in lines))

    def test_coordinate_transform(self):
        _,loaded,_=guide.load(self.write()); s,im=loaded[0]
        cropped=guide.panel(s,im,s['crop'],400)
        scale=min(880/250,400/180)
        # Highlight top-left stays at (98-50,198-150) after crop/resize.
        x,y=round(48*scale),round(48*scale)
        pixels=[cropped.getpixel((x+dx,y+dy)) for dx in range(-2,3) for dy in range(-2,3)]
        self.assertTrue(any(r>120 and g<100 and b<50 for r,g,b in pixels))
        # Arrow tip remains just above target, after same transform.
        x,y=round(100*scale),round(45*scale)
        self.assertTrue(any(cropped.getpixel((x+dx,y+dy))[0]>120 and cropped.getpixel((x+dx,y+dy))[1]<100 for dx in range(-2,3) for dy in range(-2,3)))
    def test_exif_and_size(self):
        raw=Image.open(self.root/'in.png'); ex=Image.Exif(); ex[274]=6
        raw.transpose(Image.Transpose.ROTATE_90).save(self.root/'rot.jpg',exif=ex)
        self.spec['steps'][0]['image']='rot.jpg'; _,loaded,_=guide.load(self.write()); self.assertEqual(loaded[0][1].size,(600,900))
    def test_invalid_inputs(self):
        for field,value in [('image','../escape.png'),('image','/tmp/a.png'),('image','missing.png'),('highlights',[[590,0,30,10]]),('crop',[0,0,0,10]),('arrows',[[0,0,float('nan'),2]]),('redactions',[[0,-1,10,10]])]:
            with self.subTest(field=field,value=value):
                s=copy.deepcopy(self.spec); s['steps'][0][field]=value
                with self.assertRaises((ValueError,OSError)): guide.load(self.write(s))
        (self.root/'bad.png').write_text('broken'); self.spec['steps'][0]['image']='bad.png'
        with self.assertRaises(OSError): guide.load(self.write())
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as other:
            path=Path(other)/'outside.png'; Image.new('RGB',(100,100)).save(path)
            (self.root/'link.png').symlink_to(path); self.spec['steps'][0]['image']='link.png'
            with self.assertRaises(ValueError): guide.load(self.write())
    def test_duplicate_and_uncertainty(self):
        self.spec['steps']*=2; self.spec['steps'][1]['uncertainty']='文字模糊，待补全'
        data,_,warnings=guide.load(self.write()); self.assertEqual(len(warnings),1); self.assertEqual(data['status'],'draft')
    def test_no_overwrite_or_source_mutation(self):
        before=(self.root/'in.png').read_bytes(); p=self.write(); out=self.root/'out'; out.mkdir(); (out/'manual.txt').write_text('manual')
        with self.assertRaises(ValueError): guide.export(p,out,'both')
        self.assertEqual((out/'manual.txt').read_text(),'manual'); self.assertEqual(before,(self.root/'in.png').read_bytes())
    def test_overflow_and_segments(self):
        s=copy.deepcopy(self.spec); s['steps'][0]['action']='這是一段非常長的繁體中文操作說明。'*180
        with self.assertRaises(ValueError): guide.export(self.write(s),self.root/'overflow','both')
        self.assertFalse((self.root/'overflow').exists())
        self.spec['steps']*=4; guide.export(self.write(),self.root/'out','both')
        self.assertEqual(len(PdfReader(self.root/'out/guide.pdf').pages),4)
        images=list((self.root/'out').glob('*.png')); self.assertGreater(len(images),1)
        for path in images:
            with Image.open(path) as im: self.assertLessEqual(im.height,3000)
    def test_filename_literal_and_english(self):
        name='截图 $(touch PWNED) `echo` .png'; (self.root/'in.png').rename(self.root/name)
        self.spec['steps'][0]['image']=name; self.spec['language']='en'; self.spec['title']='How to change settings'; self.spec['steps'][0]['action']='Click Settings. Then check the label.'
        guide.export(self.write(),self.root/'out','png'); self.assertFalse((self.root/'PWNED').exists())
    def test_long_screenshot(self):
        Image.new('RGB',(400,5000),'white').save(self.root/'in.png'); self.spec['steps'][0]['crop']=[50,150,250,180]
        guide.export(self.write(),self.root/'out','both')
        with Image.open(self.root/'out/guide-01.png') as im: self.assertLessEqual(im.height,2330)

if __name__=='__main__': unittest.main(verbosity=2)
