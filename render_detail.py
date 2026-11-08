# -*- coding: utf-8 -*-
"""
render_detail.py — 单文件「可点进去」的盯盘页
列表页三色卡片 → 点击进入详情：K线图(含均线/成交量/MACD) + 基本面 + 资金流
纯静态，无 CDN，无外部依赖，双击即用。
"""

import json

CSS = """
*{box-sizing:border-box;margin:0;padding:0;-webkit-text-size-adjust:100%}
body{background:#0f1115;color:#e8eaed;font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
padding:20px 16px 46px;max-width:760px;margin:0 auto}
.h{font-size:24px;font-weight:700}
.h em{font-style:normal;color:#7c8798;font-size:12.5px;font-weight:400;display:block;margin-top:6px}
.sum{display:flex;gap:10px;margin:18px 0 20px}
.sum>div{flex:1;background:#171a21;border-radius:12px;padding:13px 14px;border:1px solid #232833}
.sum b{display:block;font-size:22px;font-family:ui-monospace,monospace;line-height:1.2}
.sum i{font-style:normal;font-size:11.5px;color:#7c8798}
.k-d{color:#ff5c5c}.k-g{color:#4ade80}.k-w{color:#fbbf24}
.card{background:#171a21;border-radius:13px;margin-bottom:10px;border:1px solid #232833;
border-left:5px solid #2a303c;padding:14px 16px;cursor:pointer;transition:.15s;-webkit-tap-highlight-color:transparent}
.card:hover{background:#1b1f28;transform:translateY(-1px)}
.card.danger{border-left-color:#ff5c5c;background:linear-gradient(90deg,rgba(255,92,92,.07),#171a21 60%)}
.card.go{border-left-color:#4ade80}
.card.wait{border-left-color:#3a4150}
.l1{display:flex;justify-content:space-between;align-items:center;gap:10px}
.nm{font-size:16.5px;font-weight:600}
.nm span{display:block;font-size:11.5px;color:#5f6b7d;font-weight:400;font-family:ui-monospace,monospace;margin-top:1px}
.st{font-size:15px;font-weight:700;padding:5px 13px;border-radius:9px;white-space:nowrap}
.st.d{background:rgba(255,92,92,.16);color:#ff5c5c}
.st.g{background:rgba(74,222,128,.14);color:#4ade80}
.st.w{background:rgba(251,191,36,.13);color:#fbbf24}
.l2{display:flex;justify-content:space-between;align-items:baseline;margin-top:7px;font-size:13px;color:#7c8798}
.l2 b{font-family:ui-monospace,monospace;font-size:17px;font-weight:600;color:#e8eaed;margin-right:7px}
.up{color:#ff5c5c}.dn{color:#4ade80}.fl{color:#98a2b3}
.tip{margin-top:20px;font-size:12px;color:#4d5766;line-height:1.9;border-top:1px solid #232833;padding-top:14px}
.tip b{color:#7c8798}
/* ===== 详情页 ===== */
#detail{display:none}
.bar{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.back{background:#1b1f28;border:1px solid #2a303c;color:#b8c0cc;border-radius:9px;
padding:7px 13px;font-size:13.5px;cursor:pointer}
.back:hover{background:#232833;color:#e8eaed}
.dh{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:4px}
.dh .t{font-size:21px;font-weight:700}
.dh .t span{display:block;font-size:12px;color:#5f6b7d;font-weight:400;font-family:ui-monospace,monospace;margin-top:2px}
.dp{font-family:ui-monospace,monospace;font-size:32px;font-weight:700;letter-spacing:-1px;margin:6px 0 2px}
.dp em{font-style:normal;font-size:16px;margin-left:8px}
.box{background:#171a21;border:1px solid #232833;border-radius:13px;padding:14px 16px;margin-top:13px}
.box h4{font-size:11px;color:#5f6b7d;letter-spacing:1.5px;font-weight:600;margin-bottom:11px}
#chart{width:100%;height:360px;display:block;border-radius:9px;background:#12161d}
.legend{display:flex;gap:14px;margin-top:9px;font-size:11px;color:#7c8798;flex-wrap:wrap}
.legend i{display:inline-block;width:9px;height:2px;vertical-align:middle;margin-right:4px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}
.grid4>div{background:#12161d;border-radius:9px;padding:10px 11px}
.grid4 i{font-style:normal;display:block;font-size:10.5px;color:#5f6b7d;margin-bottom:3px}
.grid4 b{font-family:ui-monospace,monospace;font-size:14.5px;font-weight:600}
.frow{display:flex;align-items:center;gap:9px;font-size:12.5px;padding:4px 0}
.frow .dt{width:42px;color:#5f6b7d;font-family:ui-monospace,monospace;flex:0 0 auto}
.fbar{flex:1;height:15px;background:#12161d;border-radius:4px;position:relative;overflow:hidden}
.fbar i{position:absolute;top:0;bottom:0;border-radius:4px}
.fbar b{position:absolute;top:0;bottom:0;width:1px;background:#2a303c;left:50%}
.fval{width:62px;text-align:right;font-family:ui-monospace,monospace;flex:0 0 auto}
.tag{display:inline-block;padding:2px 8px;border-radius:11px;font-size:11.5px;margin:0 4px 5px 0}
.t-good{background:rgba(74,222,128,.13);color:#4ade80}
.t-warn{background:rgba(251,191,36,.13);color:#fbbf24}
.t-bad{background:rgba(255,92,92,.13);color:#ff5c5c}
.t-info{background:rgba(88,166,255,.12);color:#58a6ff}
.ad{font-size:13.5px;color:#58a6ff;line-height:1.7;padding:3px 0}
#tt{position:fixed;pointer-events:none;background:rgba(18,22,29,.96);border:1px solid #2a303c;
border-radius:8px;padding:7px 10px;font-size:11.5px;line-height:1.6;color:#b8c0cc;display:none;z-index:99;
font-family:ui-monospace,monospace;white-space:nowrap}
"""

JS = r"""
const DATA = __DATA__;
const fmt=(v,n=2)=>v==null?'-':Number(v).toFixed(n);

function byId(id){return document.getElementById(id);}

let _sY = 0;
function openDetail(i){
  const d = DATA[i];
  _sY = window.scrollY;
  byId('list').style.display='none';
  byId('detail').style.display='block';
  window.scrollTo(0,0);

  const cls = d.chg>0?'up':(d.chg<0?'dn':'fl');
  const stc = d.status==='danger'?'d':(d.status==='go'?'g':'w');

  byId('dh').innerHTML =
    '<div class="t">'+d.name+'<span>'+d.code+' · '+d.board+'</span></div>'+
    '<div class="st '+stc+'">'+d.status_text+'</div>';
  byId('dp').innerHTML = fmt(d.price)+'<em class="'+cls+'">'+
    (d.chg>0?'+':'')+fmt(d.chg)+'%</em>';

  const b=d.basic;
  byId('basic').innerHTML = [
    ['市盈率 PE', b.PE],['市净率 PB', b.PB],['ROE', b.ROE==null?'-':b.ROE+'%'],
    ['总市值', b['总市值']?b['总市值']+'亿':'-'],
    ['每股收益', b['每股收益']],['每股净资产', b['每股净资产']],
    ['换手率', b['换手率']+'%'],['年内位置', b['年内位置']+'%']
  ].map(x=>'<div><i>'+x[0]+'</i><b>'+fmt(x[1])+'</b></div>').join('');

  // 资金流
  const f = d.fund||[];
  if(f.length){
    const mx = Math.max(...f.map(x=>Math.abs(x.net)),0.01);
    byId('fund').innerHTML = f.slice(0,10).map(x=>{
      const w = Math.abs(x.net)/mx*48;
      const col = x.net>=0?'#ff5c5c':'#4ade80';
      const left = x.net>=0?50:50-w;
      const txt = (x.net>0?'+':'')+x.net.toFixed(2);
      return '<div class="frow"><span class="dt">'+x.date+'</span>'+
        '<span class="fbar"><i style="left:'+left+'%;width:'+w+'%;background:'+col+'"></i><b></b></span>'+
        '<span class="fval" style="color:'+col+'">'+txt+'亿</span></div>';
    }).join('');
    const sum5 = f.slice(0,5).reduce((a,x)=>a+x.net,0);
    byId('fundsum').innerHTML = '近5日累计 <b style="color:'+(sum5>=0?'#ff5c5c':'#4ade80')+'">'+
      (sum5>0?'+':'')+sum5.toFixed(2)+' 亿</b>';
  } else {
    byId('fund').innerHTML = '<div style="color:#5f6b7d;font-size:13px">暂无资金流数据</div>';
    byId('fundsum').innerHTML='';
  }

  // 信号
  byId('sig').innerHTML = (d.tags||[]).map(t=>'<span class="tag t-'+(t[1]==='good'?'good':t[1]==='bad'?'bad':t[1]==='warn'?'warn':'info')+'">'+t[0]+'</span>').join('');
  byId('adv').innerHTML = (d.advice||[]).map(a=>'<div>→ '+a+'</div>').join('');

  byId('levels').innerHTML = [
    ['MA5 短线',d.ma[0]],['MA10',d.ma[1]],['MA20',d.ma[2]],['MA60 生命线',d.ma[3]]
  ].map(x=>'<div><i>'+x[0]+'</i><b>'+fmt(x[1])+'</b></div>').join('');

  requestAnimationFrame(()=>draw(d));
}

function back(){
  byId('detail').style.display='none';
  byId('list').style.display='block';
  window.scrollTo(0,_sY);
}

function draw(d){
  const cv = byId('chart');
  const dpr = window.devicePixelRatio||1;
  const W = cv.clientWidth, H = 360;
  cv.width = W*dpr; cv.height = H*dpr;
  const g = cv.getContext('2d');
  g.setTransform(dpr,0,0,dpr,0,0);
  g.clearRect(0,0,W,H);

  const k = d.k;
  if(!k||!k.length) return;
  const n = k.length;
  const padR = 44, padT = 10;
  const hK = 176, hV = 58, hM = 78, gap = 12;
  const topK = padT, topV = padT+hK+gap, topM = topV+hV+gap;
  const plotW = W - padR;
  const w = plotW/n;

  // ---- 价格范围
  let pmin=1e18,pmax=-1e18;
  k.forEach(r=>{ pmin=Math.min(pmin,r[3]); pmax=Math.max(pmax,r[4]); });
  for(let c=6;c<=9;c++) k.forEach(r=>{ if(r[c]>0){pmin=Math.min(pmin,r[c]);pmax=Math.max(pmax,r[c]);} });
  const pad = (pmax-pmin)*0.06; pmin-=pad; pmax+=pad;
  const yP = v => topK + (pmax-v)/(pmax-pmin)*hK;

  // ---- 网格 + 价格标签
  g.strokeStyle='#1b2027'; g.lineWidth=1; g.fillStyle='#4d5766';
  g.font='10px ui-monospace,monospace'; g.textAlign='left';
  for(let i=0;i<=4;i++){
    const y = topK + hK*i/4;
    g.beginPath(); g.moveTo(0,y); g.lineTo(plotW,y); g.stroke();
    g.fillText((pmax-(pmax-pmin)*i/4).toFixed(2), plotW+6, y+3);
  }

  // ---- K线
  const bw = Math.max(1, w*0.62);
  k.forEach((r,i)=>{
    const [dt,o,c,l,h]=r;
    const x = i*w + w/2;
    const up = c>=o;
    const col = up?'#ff5c5c':'#4ade80';
    g.strokeStyle=col; g.fillStyle=col; g.lineWidth=1;
    g.beginPath(); g.moveTo(x, yP(h)); g.lineTo(x, yP(l)); g.stroke();
    const y1=yP(Math.max(o,c)), y2=yP(Math.min(o,c));
    const bh=Math.max(1,y2-y1);
    g.fillRect(x-bw/2, y1, bw, bh);
  });

  // ---- 均线
  const maCol=['#f0b90b','#58a6ff','#a371f7','#3fb950'];
  [6,7,8,9].forEach((ci,ii)=>{
    g.strokeStyle=maCol[ii]; g.lineWidth=1.2; g.beginPath();
    let started=false;
    k.forEach((r,i)=>{ const v=r[ci]; if(!v||v<=0) return;
      const x=i*w+w/2, y=yP(v);
      if(!started){g.moveTo(x,y);started=true;} else g.lineTo(x,y);
    });
    g.stroke();
  });

  // ---- 成交量
  let vmax=0.01; k.forEach(r=>vmax=Math.max(vmax,r[5]));
  k.forEach((r,i)=>{
    const x=i*w+w/2, hh=r[5]/vmax*hV;
    g.fillStyle = r[2]>=r[1]?'rgba(255,92,92,.55)':'rgba(74,222,128,.55)';
    g.fillRect(x-bw/2, topV+hV-hh, bw, hh);
  });
  g.fillStyle='#4d5766'; g.font='10px ui-monospace,monospace';
  g.fillText('成交量', 2, topV+10);

  // ---- MACD
  let mmax=0.01; k.forEach(r=>{mmax=Math.max(mmax,Math.abs(r[10]),Math.abs(r[11]),Math.abs(r[12]));});
  const yMzero = topM + hM/2;
  g.strokeStyle='#1b2027'; g.beginPath(); g.moveTo(0,yMzero); g.lineTo(plotW,yMzero); g.stroke();
  k.forEach((r,i)=>{
    const v=r[12], hh=Math.abs(v)/mmax*(hM/2-2);
    g.fillStyle = v>=0?'rgba(255,92,92,.7)':'rgba(74,222,128,.7)';
    g.fillRect(i*w+w*0.2, v>=0?yMzero-hh:yMzero, Math.max(1,w*0.6), hh);
  });
  [[10,'#f0b90b'],[11,'#58a6ff']].forEach(([ci,cc])=>{
    g.strokeStyle=cc; g.lineWidth=1.2; g.beginPath();
    let started=false;
    k.forEach((r,i)=>{ const v=r[ci]; const y=yMzero-(v/mmax)*(hM/2-2);
      const x=i*w+w/2;
      if(!started){g.moveTo(x,y);started=true;} else g.lineTo(x,y);
    });
    g.stroke();
  });
  g.fillStyle='#4d5766'; g.fillText('MACD', 2, topM+10);

  // ---- 日期轴
  g.fillText(k[0][0].slice(5), 1, H-3);
  g.textAlign='right'; g.fillText(k[n-1][0].slice(5), plotW, H-3);

  // ---- 交互
  const tt = byId('tt');
  cv.onmousemove = e=>{
    const rc = cv.getBoundingClientRect();
    let i = Math.floor((e.clientX-rc.left)/w);
    i = Math.max(0,Math.min(n-1,i));
    const r = k[i];
    tt.style.display='block';
    tt.style.left = Math.min(e.clientX+14, window.innerWidth-150)+'px';
    tt.style.top = (e.clientY-10)+'px';
    tt.innerHTML = r[0]+'<br>开 '+fmt(r[1])+'  收 '+fmt(r[2])+
      '<br>高 '+fmt(r[4])+'  低 '+fmt(r[3])+'<br>量 '+fmt(r[5],1)+'万手'+
      '<br>MA5 '+fmt(r[6])+'  MA10 '+fmt(r[7]);
  };
  cv.onmouseleave = ()=>{ tt.style.display='none'; };
}
"""

BODY = """
<div id="list">
  <div class="h">今天怎么办
    <em>__TIME__</em>
  </div>
  <div class="sum">
    <div><b class="k-d">__ND__</b><i>只要先处理</i></div>
    <div><b class="k-g">__NG__</b><i>只可以试试</i></div>
    <div><b class="k-w">__NW__</b><i>只继续等</i></div>
  </div>
  __CARDS__
  <div class="tip">
  <b>怎么看</b>　红色 = 先减仓，绿色 = 可小试，灰色 = 再等等。<br>
  <b>点任意一只</b> → 看 K线图、基本面、资金流、买卖信号。<br><br>
  <b>数据</b>　__TIME__，收盘快照。<b>风险</b>　信号是概率，止损必须自己设。
  </div>
</div>

<div id="detail">
  <div class="bar"><button class="back" onclick="back()">← 返回列表</button></div>
  <div class="dh" id="dh"></div>
  <div class="dp" id="dp"></div>

  <div class="box">
    <h4>股价走势（近 __DAYS__ 个交易日）</h4>
    <canvas id="chart"></canvas>
    <div class="legend">
      <span><i style="background:#f0b90b"></i>MA5</span>
      <span><i style="background:#58a6ff"></i>MA10</span>
      <span><i style="background:#a371f7"></i>MA20</span>
      <span><i style="background:#3fb950"></i>MA60</span>
      <span style="color:#4d5766">鼠标移到图上可看当天数据</span>
    </div>
  </div>

  <div class="box">
    <h4>基本面</h4>
    <div class="grid4" id="basic"></div>
  </div>

  <div class="box">
    <h4>资金流（近 10 日 · 红入绿出）</h4>
    <div id="fund"></div>
    <div style="margin-top:9px;font-size:12.5px;color:#7c8798" id="fundsum"></div>
  </div>

  <div class="box">
    <h4>关键价位</h4>
    <div class="grid4" id="levels"></div>
  </div>

  <div class="box">
    <h4>看到了什么</h4>
    <div id="sig" style="margin-bottom:8px"></div>
    <div id="adv"></div>
  </div>
  <div style="height:10px"></div>
</div>
<div id="tt"></div>
"""


def render_detail_html(stocks, data_time="", days=120) -> str:
    n_d = sum(1 for s in stocks if s["status"] == "danger")
    n_g = sum(1 for s in stocks if s["status"] == "go")
    n_w = sum(1 for s in stocks if s["status"] == "wait")

    cards = []
    for i, s in enumerate(stocks):
        cls = s["status"]
        sc = {"danger": "d", "go": "g", "wait": "w"}[cls]
        chg_cls = "up" if s["chg"] > 0 else ("dn" if s["chg"] < 0 else "fl")
        cards.append(f"""  <div class="card {cls}" onclick="openDetail({i})">
    <div class="l1"><div class="nm">{s['name']}<span>{s['code']}</span></div>
      <div class="st {sc}">{s['status_text']}</div></div>
    <div class="l2"><div><b class="{chg_cls}">{s['price']:.2f}</b>
      <span class="{chg_cls}">{s['chg']:+.2f}%</span></div>
      <div>距年内高点 {s['from_high']}% ›</div></div>
  </div>""")

    body = (BODY.replace("__CARDS__", "\n".join(cards))
                .replace("__TIME__", data_time)
                .replace("__ND__", str(n_d))
                .replace("__NG__", str(n_g))
                .replace("__NW__", str(n_w))
                .replace("__DAYS__", str(days)))

    js = JS.replace("__DATA__", json.dumps(stocks, ensure_ascii=False))

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>今天怎么办</title><style>{CSS}</style></head><body>
{body}
<script>{js}</script>
</body></html>"""
