"""Generate only fictional UI fixtures; never opens personal files."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from guide import font_path
BASE=Path(__file__).resolve().parents[1]/'examples'
FONT=font_path()
def screen(path,title,rows,size=(600,1000),secret=False,rotate=False):
    im=Image.new('RGB',size,'#eff3f7'); d=ImageDraw.Draw(im)
    f=ImageFont.truetype(FONT,27); big=ImageFont.truetype(FONT,34)
    d.rectangle((0,0,size[0],125),fill='white'); d.text((30,30),'示例应用 · 虚构界面',font=f,fill='#5b6674'); d.text((30,78),title,font=big,fill='#152536')
    for n,row in enumerate(rows):
        y=180+n*100; d.rounded_rectangle((25,y,size[0]-25,y+78),radius=10,fill='white'); 
        if '       ' in row:
            label,state=row.split('       '); d.text((45,y+20),label,font=f,fill='#152536'); d.text((430,y+20),state,font=f,fill='#152536')
        elif row=='⚙ 设置':
            # Fictional gear icon drawn geometrically; avoids missing symbol glyphs.
            import math
            cx,cy=64,y+38
            for k in range(8):
                angle=k*math.pi/4; d.line((cx+12*math.cos(angle),cy+12*math.sin(angle),cx+21*math.cos(angle),cy+21*math.sin(angle)),fill='#152536',width=6)
            d.ellipse((cx-15,cy-15,cx+15,cy+15),outline='#152536',width=5); d.text((100,y+20),'设置',font=f,fill='#152536')
        else: d.text((45,y+20),row,font=f,fill='#152536')
    if secret:
        d.text((35,700),'王小禾 · 13800001234',font=f,fill='black'); d.text((35,745),'SECRET-ADDRESS-729',font=f,fill='black'); d.text((35,790),'账户 6200 1234 5678',font=f,fill='black')
    if rotate:
        exif=Image.Exif(); exif[274]=6
        im.transpose(Image.Transpose.ROTATE_90).save(path,exif=exif)
    else: im.save(path)
def example(name,title,audience,definitions):
    root=BASE/name; root.mkdir(parents=True,exist_ok=True); steps=[]
    for i,(heading,rows,action,target,extra) in enumerate(definitions,1):
        filename=f'{i:02d}.jpg' if extra.get('rotate') else f'{i:02d}.png'
        screen(root/filename,heading,rows,size=extra.get('size',(600,1000)),secret=extra.get('secret',False),rotate=extra.get('rotate',False))
        x,y,w,h=target
        step={'title':heading,'action':action,'image':filename,'highlights':[target], 'arrows':[[x+min(w/2,150),y-40,x+min(w/2,150),y-4]],'redactions':[[25,690,550,150]] if extra.get('secret') else []}
        step['crop']=extra.get('crop',[15,max(0,y-45),570,h+90])
        if extra.get('check'): step['check']=extra['check']
        if extra.get('evidence'): step['evidence']=extra['evidence']
        steps.append(step)
    (root/'guide.json').write_text(json.dumps({'version':1,'title':title,'audience':audience,'status':'complete','notice':'虚构示例；分享前请复核个人信息。','steps':steps},ensure_ascii=False,indent=2),'utf-8')
example('parents','关闭「晴天聊」的消息通知','parents',[
('找到设置',['聊天','联系人','⚙ 设置'],'点击下方带齿轮图标的「设置」。齿轮旁边写着“设置”。',[25,380,550,78],{}),
('打开通知设置',['账号与安全','消息通知','通用'],'点击中间一行「消息通知」。',[25,280,550,78],{'rotate':True}),
('找到新消息开关',['新消息通知       开启','声音       开启','振动       开启'],'找到最上方的「新消息通知」，点击右侧写着「开启」的开关。',[380,180,190,78],{'crop':[20,140,570,160],'size':(600,1500)}),
('检查关闭状态',['新消息通知       关闭','声音       关闭','振动       关闭'],'查看「新消息通知」右侧是否显示「关闭」。',[380,180,190,78],{'evidence':'此示例截图显示「新消息通知」为「关闭」。'})])
example('customer','修改通讯地址','customer',[
('打开个人资料',['个人资料','安全设置','帮助中心'],'在账户页面选择「个人资料」。',[25,180,550,78],{'secret':True}),
('选择通讯地址',['姓名','通讯地址','联系偏好'],'选择「通讯地址」。',[25,280,550,78],{'secret':True}),
('填写新地址',['省 / 市 / 区','详细地址：示例路 18 号','邮政编码：000000'],'填写新的详细地址，并检查省、市、区和邮政编码。这里仅展示虚构地址。',[25,180,550,278],{'secret':True,'size':(1100,1000),'crop':[20,170,580,300]}),
('提交修改',['示例路 18 号','邮政编码：000000','保存'],'核对地址后选择「保存」。',[25,380,550,78],{'secret':True,'check':'如出现提示，请按实际提示处理。'}),
('核对保存结果',['通讯地址已更新','示例路 18 号','返回个人资料'],'查看是否出现「通讯地址已更新」，并核对显示的地址。',[25,180,550,78],{'secret':True,'evidence':'此示例截图显示「通讯地址已更新」。'})])
print(BASE)
