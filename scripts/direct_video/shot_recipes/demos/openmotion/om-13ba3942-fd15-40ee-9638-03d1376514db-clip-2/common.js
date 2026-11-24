// Adapted from OpenMotion: keep the single-clip drawing helpers and select the local font.
'use strict';
const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
const W=1000,H=600,TAU=Math.PI*2;
let P={title:CONFIG.demoTitle,accent:CONFIG.accent||CONFIG.palette[2]||'#888',strength:1},time=0;
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)),mix=(a,b,u)=>a+(b-a)*u,ease=x=>1-Math.pow(1-clamp(x),3),phase=(t,a,b)=>ease((t-a)/(b-a)),sin=Math.sin,cos=Math.cos;
const frac=x=>x-Math.floor(x),rand=i=>frac(Math.sin(i*127.1+311.7)*43758.5453);
const ink=()=>CONFIG.palette[0]==='#ffffff'||CONFIG.palette[0]==='#fafafa'?'#19191e':CONFIG.palette[1];
function rect(x,y,w,h,c,r=0){ctx.fillStyle=c;ctx.beginPath();ctx.roundRect(x,y,Math.max(0,w),Math.max(0,h),Math.max(0,Math.min(r,w/2,h/2)));ctx.fill();}
function line(x1,y1,x2,y2,c='#999',width=1){ctx.strokeStyle=c;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();}
function poly(points,fill,stroke){ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.stroke()}}
function ellipse(x,y,rx,ry,c,stroke){ctx.beginPath();ctx.ellipse(x,y,Math.max(.01,rx),Math.max(.01,ry),0,0,TAU);if(c){ctx.fillStyle=c;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.stroke()}}
function text(str,x,y,size=32,color='#fff',align='center',font='Arial',weight=400,maxWidth){ctx.fillStyle=color;ctx.font=`${weight} ${size}px PCPinned0, ${font}`;ctx.textAlign=align;ctx.textBaseline='middle';if(maxWidth)ctx.fillText(String(str),x,y,maxWidth);else ctx.fillText(String(str),x,y);}
function label(str,x,y,c='#888'){text(str,x,y,12,c,'left','monospace')}
function fittedText(str,x,y,size,c,max=850,font='Arial',weight=400){ctx.font=`${weight} ${size}px PCPinned0, ${font}`;text(str,x,y,Math.min(size,size*max/Math.max(1,ctx.measureText(str).width)),c,'center',font,weight)}
function wrap(str,max=32){const words=String(str).split(' ');let out=[''];for(const w of words){let n=out.length-1;if((out[n]+w).length>max&&out[n])out.push(w);else out[n]+=(out[n]?' ':'')+w;}return out;}
function multiline(str,x,y,size,c,width=32){const rows=wrap(str,width);rows.forEach((r,i)=>fittedText(r,x,y+(i-(rows.length-1)/2)*size*1.15,size,c,850));}
function saved(fn){ctx.save();fn();ctx.restore()}
function at(x,y,s=1,a=0,fn){saved(()=>{ctx.translate(x,y);ctx.rotate(a);ctx.scale(s,s);fn()})}
function alpha(a,fn){saved(()=>{ctx.globalAlpha*=clamp(a);fn()})}
function bg(c=CONFIG.palette[0]){rect(0,0,W,H,c)}
function grid(c='#9992',step=50){for(let x=0;x<W;x+=step)line(x,0,x,H,c);for(let y=0;y<H;y+=step)line(0,y,W,y,c)}
function glow(x,y,r,color){const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,color);g.addColorStop(1,color.slice(0,7)+'00');rect(x-r,y-r,r*2,r*2,g)}
function gradient(c1,c2,x=0,y=0,w=W,h=H){const g=ctx.createLinearGradient(x,y,x+w,y+h);g.addColorStop(0,c1);g.addColorStop(1,c2);rect(x,y,w,h,g)}
function star(x,y,r,c,n=6,rot=0){poly(Array.from({length:n*2},(_,i)=>[x+cos(i*Math.PI/n+rot)*r*(i%2?.36:1),y+sin(i*Math.PI/n+rot)*r*(i%2?.36:1)]),c)}
function flower(x,y,r,c,rot=0){at(x,y,1,rot,()=>{for(let j=0;j<6;j++)at(0,0,1,j*TAU/6,()=>ellipse(0,-r*.52,r*.27,r*.55,c));ellipse(0,0,r*.18,r*.18,'#efcb77')})}
function figma(x,y,s,collapse=1,t=0){const colors=['#f24e1e','#a259ff','#ff7262','#1abcfe','#0acf83'];at(x,y,s,0,()=>{[[0,0],[1,0],[0,1],[1,1],[0,2]].forEach(([a,b],i)=>{let dx=(a-.5)*35+(1-collapse)*(rand(i+3)-.5)*600,dy=(b-1)*35+(1-collapse)*(rand(i+9)-.5)*400;at(dx,dy,1,(1-collapse)*sin(t+i),()=>rect(-17,-17,34,34,colors[i],i===1?12:18))})})}
function simpleMark(x,y,s,c=P.accent){at(x,y,s,0,()=>{rect(-24,-24,22,48,c,8);rect(2,-24,22,48,c,8);ellipse(-10,0,3,8,'#fff');ellipse(10,0,3,8,'#fff')})}
function cursor(x,y,c='#fff'){poly([[x,y],[x+4,y+28],[x+12,y+18],[x+22,y+18]],c,'#333')}
function ui(x,y,w,h,c=P.accent,title=P.title,progress=1){saved(()=>{ctx.shadowColor='#0002';ctx.shadowBlur=18;rect(x,y,w,h,'#fafafa',8)});rect(x,y,w,26,'#e9e9e7',8);[0,1,2].forEach(i=>ellipse(x+12+i*12,y+13,3,3,['#e9766b','#edc160','#78b393'][i]));label(title,x+50,y+14,'#666');rect(x+10,y+36,w*.19,h-48,'#ececea',3);for(let i=0;i<5;i++)rect(x+18,y+48+i*21,w*.13,5,'#c7c7c5');const ww=w*.67;rect(x+w*.25,y+42,ww,10,'#333');for(let i=0;i<6;i++)if(progress>i/7){let xx=x+w*.25+(i%3)*(ww/3),yy=y+68+Math.floor(i/3)*(h*.28);rect(xx,yy,ww/3-8,h*.24,i===0?c:'#e5e6e3',4);rect(xx+5,yy+h*.24-14,ww/4,4,'#999')}}
function face(x,y,r,c,t=0,shape=0){at(x,y,1,sin(t)*.15,()=>{if(shape===1){for(let i=0;i<4;i++)ellipse(cos(i*TAU/4+Math.PI/4)*r*.3,sin(i*TAU/4+Math.PI/4)*r*.3,r*.7,r*.7,c)}else ellipse(0,0,r,r,c);rect(-r*.35,-r*.24,r*.16,r*.35,'#fff',r*.08);rect(r*.12,-r*.24,r*.16,r*.35,'#fff',r*.08)})}
function person(x,y,s,c='#222'){at(x,y,s,0,()=>{ellipse(0,-42,16,20,c);poly([[-18,-20],[18,-20],[26,35],[-24,35]],c);line(-10,30,-18,78,c,12);line(10,30,21,78,c,12);line(-18,-10,-40,30,c,10);line(18,-10,40,25,c,10)})}
function portrait(x,y,w,h,i,t=0){saved(()=>{rect(x,y,w,h,['#dfddd8','#c8d6db','#ebd5ca'][i%3]);ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();person(x+w*.5,y+h*.53,h/155,['#202226','#4f454b','#273e3f'][i%3]);rect(x+8,y+h-18,w*.4,3,'#fff8')})}
const maskCache=new Map();function wordPoints(value,size=84){let key=value+'|'+size;if(maskCache.has(key))return maskCache.get(key);const c=document.createElement('canvas');c.width=800;c.height=220;const q=c.getContext('2d');q.fillStyle='#fff';q.font=`700 ${size}px PCPinned0, Arial`;q.textAlign='center';q.textBaseline='middle';q.fillText(value,400,110,750);let a=q.getImageData(0,0,800,220).data,pts=[];for(let y=0;y<220;y+=5)for(let x=0;x<800;x+=5)if(a[(y*800+x)*4+3]>100)pts.push([x-400,y-110]);maskCache.set(key,pts);return pts;}
function progressText(value,u){return value.slice(0,Math.floor(clamp(u)*value.length))}
function useTitle(fallback){return P.title===CONFIG.demoTitle?fallback:P.title}
function stageAt(t){let n=0;CONFIG.stages.forEach((s,i)=>{if(t>=s.start)n=i});return n}
function stageProgress(t){let n=stageAt(t),a=CONFIG.stages[n].start,b=CONFIG.stages[n+1]?.start||CONFIG.duration;return clamp((t-a)/(b-a))}
