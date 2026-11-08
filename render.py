# -*- coding: utf-8 -*-
"""render.py — 把扫描结果渲染成可双击打开的单文件 HTML（无外部依赖）。"""

from __future__ import annotations

import html as H
from datetime import datetime

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0e14;color:#c9d1d9;font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:28px}
.wrap{max-width:1280px;margin:0 auto}
h1{font-size:22px;color:#e6edf3;font-weight:600;letter-spacing:.5px}
h1 span{color:#58a6ff}
.sub{color:#6e7681;font-size:13px;margin-top:6px}
.top{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid #21262d;padding-bottom:16px;margin-bottom:20px;flex-wrap:wrap;gap:12px}
.stats{display:flex;gap:22px;flex-wrap:wrap}
.stat b{display:block;font-size:19px;color:#e6edf3}
.stat i{font-style:normal;color:#6e7681;font-size:12px}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 22px;font-size:12px;color:#8b949e}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:middle}
table{width:100%;border-collapse:collapse;font-size:13.5px}
thead th{text-align:left;padding:10px 8px;color:#6e7681;font-weight:500;font-size:12px;
border-bottom:1px solid #21262d;white-space:nowrap;position:sticky;top:0;background:#0b0e14;z-index:2}
tbody tr{border-bottom:1px solid #161b22;transition:.15s}
tbody tr:hover{background:#11161f}
td{padding:11px 8px;vertical-align:middle}
.code{font-family:ui-monospace,Menlo,monospace;color:#6e7681;font-size:12.5px}
.name{color:#e6edf3;font-weight:600}
.name small{display:block;color:#484f58;font-weight:400;font-size:11px}
.up{color:#f85149}.down{color:#3fb950}.flat{color:#8b949e}
.bar{height:5px;border-radius:3px;background:#21262d;overflow:hidden;min-width:64px}
.bar>i{display:block;height:100%;border-radius:3px}
.score{font-family:ui-monospace,monospace;font-weight:700;font-size:15px}
.dims{display:flex;gap:3px;align-items:flex-end;height:22px}
.dim{width:7px;border-radius:2px 2px 0 0;background:#30363d}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11.5px;margin:1px 3px 1px 0;white-space:nowrap}
.t-good{background:rgba(63,185,80,.13);color:#3fb950;border:1px solid rgba(63,185,80,.25)}
.t-warn{background:rgba(210,153,34,.13);color:#d29922;border:1px solid rgba(210,153,34,.25)}
.t-bad{background:rgba(248,81,73,.13);color:#f85149;border:1px solid rgba(248,81,73,.25)}
.t-info{background:rgba(88,166,255,.12);color:#58a6ff;border:1px solid rgba(88,166,255,.25)}
.s-a{color:#f85149;border:1px solid rgba(248,81,73,.45);background:rgba(248,81,73,.1);padding:2px 9px;border-radius:4px;font-size:12px;white-space:nowrap}
.s-b{color:#d29922;border:1px solid rgba(210,153,34,.45);background:rgba(210,153,34,.1);padding:2px 9px;border-radius:4px;font-size:12px;white-space:nowrap}
.s-c{color:#58a6ff;border:1px solid rgba(88,166,255,.35);background:rgba(88,166,255,.08);padding:2px 9px;border-radius:4px;font-size:12px;white-space:nowrap}
.s-d{color:#6e7681;border:1px solid #30363d;padding:2px 9px;border-radius:4px;font-size:12px;white-space:nowrap}
.adv{color:#8b949e;font-size:12px;max-width:330px;line-height:1.5}
.foot{margin-top:26px;padding-top:14px;border-top:1px solid #21262d;color:#484f58;font-size:12px;line-height:1.9}
.foot b{color:#8b949e}
/* 卡片模式 */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px;margin-top:8px}
.card{background:#11161f;border:1px solid #21262d;border-radius:10px;padding:18px}
.card h3{font-size:17px;color:#e6edf3;display:flex;justify-content:space-between;align-items:center}
.card .px{font-family:ui-monospace,monospace;font-size:22px;margin:8px 0 2px}
.card .meta{color:#6e7681;font-size:12px;margin-bottom:10px}
.card .sec{border-top:1px solid #21262d;padding-top:10px;margin-top:10px}
.card .sec h4{font-size:11px;color:#6e7681;font-weight:500;letter-spacing:1px;margin-bottom:6px}
.card li{list-style:none;color:#a9b1ba;font-size:12.5px;margin:3px 0;padding-left:0}
.card li::before{content:"›";color:#30363d;margin-right:6px}
.card .a{color:#58a6ff;font-size:12.5px;margin-top:4px}
.ring{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-family:ui-monospace,monospace;font-size:15px;font-weight:700;flex-shrink:0}
"""


def _chg_cls(v):
    return "up" if v > 0 else ("down" if v < 0 else "flat")


def _score_color(s):
    if s >= 72:
        return "#f85149"
    if s >= 62:
        return "#d29922"
    if s >= 50:
        return "#58a6ff"
    return "#484f58"


def _tag_html(tags, limit=None):
    out = []
    for t, c in (tags if limit is None else tags[:limit]):
        out.append(f'<span class="tag t-{c}">{H.escape(t)}</span>')
    return "".join(out)


def _dims(r):
    bars = []
    for v, c in ((r["T"], "#58a6ff"), (r["M"], "#a371f7"), (r["V"], "#3fb950"), (r["F"], "#d29922")):
        h = max(3, int(v / 100 * 22))
        bars.append(f'<div class="dim" style="height:{h}px;background:{c};opacity:{0.35 + v/160:.2f}"></div>')
    return '<div class="dims">' + "".join(bars) + "</div>"


def render_scan_html(rows, uni, args) -> str:
    now = datetime.now()
    up = int((uni["changepercent"] > 0).sum()) if "changepercent" in uni else 0
    dn = int((uni["changepercent"] < 0).sum()) if "changepercent" in uni else 0
    n_a = sum(1 for r in rows if r["grade"] == "重点跟踪")
    n_b = sum(1 for r in rows if r["grade"] == "可关注")
    trs = []

    for i, r in enumerate(rows[:args.top], 1):
        col = _score_color(r["score"])
        trs.append(f"""
<tr>
  <td class="code">{i:02d}</td>
  <td><div class="name">{H.escape(r['name'])}<small>{r['code']} · {r['board']}</small></div></td>
  <td style="font-family:ui-monospace,monospace">{r['price']:.2f}</td>
  <td class="{_chg_cls(r['chg'])}" style="font-family:ui-monospace,monospace">{r['chg']:+.2f}%</td>
  <td><div style="display:flex;align-items:center;gap:8px">
      <span class="score" style="color:{col}">{r['score']:.1f}</span>
      <div class="bar"><i style="width:{r['score']}%;background:{col}"></i></div></div></td>
  <td><span class="{r['gcls']}">{r['grade']}</span>
      <div style="font-size:10.5px;margin-top:4px;color:#6e7681">买点 <b style="color:#3fb950">{r.get('buy_cnt',0)}</b>/7
      · 卖点 <b style="color:{'#f85149' if r.get('sell_cnt',0) else '#484f58'}">{r.get('sell_cnt',0)}</b></div></td>
  <td>{_dims(r)}
      <div style="color:#484f58;font-size:10.5px;margin-top:2px">{r['T']}/{r['M']}/{r['V']}/{r['F']}</div></td>
  <td>{_tag_html(r['tags'], 4)}</td>
  <td class="adv">{H.escape(r['advice'][0])}</td>
  <td style="font-family:ui-monospace,monospace;font-size:12px;color:#6e7681">{r['roe'] if r['roe'] is not None else '-'}</td>
  <td style="font-family:ui-monospace,monospace;font-size:12px;color:#6e7681">{r['pe'] if r['pe'] else '-'}</td>
  <td style="font-family:ui-monospace,monospace;font-size:12px;color:#6e7681">{r['vratio']}</td>
</tr>""")

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>选股扫描 {now:%Y-%m-%d %H:%M}</title><style>{CSS}</style></head><body><div class="wrap">
<div class="top">
  <div><h1>选股<span>扫描</span>报告</h1>
  <div class="sub">{now:%Y-%m-%d %H:%M} · 依据《半小时漫画股票实战》指标体系 + 《实操-风大》纪律 · 数据源：新浪财经</div></div>
  <div class="stats">
    <div class="stat"><b>{len(uni)}</b><i>全市场</i></div>
    <div class="stat"><b style="color:#f85149">{up}</b><i>上涨</i></div>
    <div class="stat"><b style="color:#3fb950">{dn}</b><i>下跌</i></div>
    <div class="stat"><b>{len(rows)}</b><i>有效样本</i></div>
    <div class="stat"><b style="color:#f85149">{n_a}</b><i>重点</i></div>
    <div class="stat"><b style="color:#d29922">{n_b}</b><i>可关注</i></div>
  </div>
</div>
<div class="legend">
  <span><i class="dot" style="background:#58a6ff"></i>趋势 32%</span>
  <span><i class="dot" style="background:#a371f7"></i>动能 30%</span>
  <span><i class="dot" style="background:#3fb950"></i>量能 23%</span>
  <span><i class="dot" style="background:#d29922"></i>基本面 15%</span>
  <span style="margin-left:12px">评分 = 四维加权 − 风险扣分（顶背离/量增价滞/破位）</span>
</div>
<table><thead><tr>
<th>#</th><th>标的</th><th>现价</th><th>涨跌</th><th>综合评分</th><th>档位</th>
<th>四维</th><th>命中信号</th><th>操作提示</th><th>ROE%</th><th>PE</th><th>量比</th>
</tr></thead><tbody>{''.join(trs)}</tbody></table>
<div class="foot">
<b>怎么读这张表</b>：先看档位 → 再看"命中信号"是否共振（书里说单一指标只用来验证想法，多指标共振才是时机）→
最后按"操作提示"执行，且必须带止损。<br>
<b>信号含义</b>：MACD零上金叉=多头新涨势；底背离=跌不动了；顶背离=涨不动了；量增价滞=出货嫌疑；无量拉升=虚涨；
龙回头=涨停后缩量回踩支撑。<br>
<b>基本面</b>：ROE 由 PB/PE 反推（≈净资产收益率），10–30% 为健康区间；PE 为负表示亏损。<br>
<b style="color:#d29922">风险提示</b>：本工具只做规则计算，不构成投资建议。指标是概率，止损是底线。
</div></div></body></html>"""


def render_watch_html(rows, interval=60, indices=None) -> str:
    now = datetime.now()
    idxs = indices or []

    idx_html = ""
    if idxs:
        items = []
        for i in idxs:
            cls = _chg_cls(i["chg"])
            items.append(
                f'<div class="idx"><span>{H.escape(i["name"])}</span>'
                f'<b class="{cls}">{i["price"]:.2f}</b>'
                f'<em class="{cls}">{i["chg"]:+.2f}%</em></div>')
        idx_html = '<div class="idxbar">' + "".join(items) + "</div>"

    risk = [r for r in rows if r.get("sell_cnt", 0) > 0]
    ok = [r for r in rows if r.get("sell_cnt", 0) == 0]
    risk_banner = ""
    if risk:
        names = "、".join(r["name"] for r in risk[:4])
        risk_banner = (f'<div class="alert">⚠ <b>{len(risk)} 只触发卖出信号</b>：{H.escape(names)}'
                       f'　— 按纪律先减仓，别等破位</div>')

    def card(r):
        col = _score_color(r["score"])
        ring = f"background:conic-gradient({col} {r['score']*3.6}deg,#21262d 0)"
        cls = "card risk" if r.get("sell_cnt", 0) > 0 else "card"
        adv = "".join(f'<li><span class="a">{H.escape(a)}</span></li>' for a in r["advice"])
        tags = _tag_html(r["tags"], 8)
        minx = ""
        if r.get("min"):
            m = r["min"]
            bits = []
            if m["top_div"]:
                bits.append('<span class="tag t-bad">分时顶背离·卖点</span>')
            if m["bottom_div"]:
                bits.append('<span class="tag t-good">分时底背离</span>')
            if m["gold"]:
                bits.append('<span class="tag t-good">分时金叉</span>')
            if bits:
                minx = (f'<div class="sec"><h4>分时（{m["last"][5:16]}）</h4>'
                        f'{"".join(bits)}</div>')
        ma = "/".join(f"{x:.2f}" for x in r["ma"])
        return f"""
<div class="{cls}">
  <h3><span>{H.escape(r['name'])} <span class="code">{r['code']}</span></span>
      <span class="ring" style="{ring}"><span class="ring-in">{r['score']:.0f}</span></span></h3>
  <div class="px {_chg_cls(r['chg'])}">{r['price']:.2f}
      <span style="font-size:15px">{r['chg']:+.2f}%</span></div>
  <div class="meta">MA5/10/20/60 {ma}<br>量比 {r['vratio']} · 乖离 {r['bias5']}% ·
     位置 {r['pos']:.0f}% · ROE {r['roe'] if r['roe'] is not None else '-'}%</div>
  <div>{tags}</div>
  {minx}
  <div class="sec"><h4>操作提示</h4><ul>{adv}</ul></div>
</div>"""

    body = "".join(card(r) for r in risk) + "".join(card(r) for r in ok)

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{interval}">
<title>盯盘 {now:%H:%M:%S}</title><style>{CSS}
.idxbar{{display:flex;gap:26px;flex-wrap:wrap;margin:16px 0 6px;padding:14px 16px;
background:#11161f;border:1px solid #21262d;border-radius:9px}}
.idx span{{display:block;color:#6e7681;font-size:11px;margin-bottom:3px}}
.idx b{{font-family:ui-monospace,monospace;font-size:16px;margin-right:8px}}
.idx em{{font-style:normal;font-size:12.5px}}
.alert{{margin:14px 0 18px;padding:11px 15px;border-radius:8px;font-size:13px;
background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.3);color:#f85149}}
.card.risk{{border-color:rgba(248,81,73,.4);box-shadow:0 0 0 1px rgba(248,81,73,.1) inset}}
.ring{{display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.ring-in{{width:42px;height:42px;border-radius:50%;background:#11161f;display:flex;
align-items:center;justify-content:center;font-family:ui-monospace,monospace;font-size:15px;font-weight:700}}
</style></head><body><div class="wrap">
<div class="top"><div><h1>自选股<span>盯盘</span></h1>
<div class="sub">{now:%Y-%m-%d %H:%M:%S} · 每 {interval}s 自动刷新 · 共 {len(rows)} 只 ·
按"卖出信号优先"排序</div></div></div>
{idx_html}
{risk_banner}
<div class="grid">{body}</div>
<div class="foot"><b>盯盘只看四件事（风大那份的原话）</b><br>
① 股价创新高但分时MACD不创新高 → 顶背离，减；<br>
② 在涨但没量 → 无量拉升，不追，回落5日线再接；<br>
③ 冲高回落跌破当日均价且量能萎缩 → 卖；<br>
④ 跌破10日线 → 先减仓避险，站回再谈。<br>
<b style="color:#d29922">风险提示</b>：本页面只做规则计算，信号是概率不是承诺，止损线必须自己设。
</div></div></body></html>"""


def render_index(**kw):
    return ""


M_CSS = """
*{box-sizing:border-box;margin:0;padding:0;-webkit-text-size-adjust:100%}
body{background:#0b0e14;color:#c9d1d9;font:15px/1.55 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
padding:14px 12px 40px;max-width:560px;margin:0 auto}
.hd{padding:4px 2px 14px}
.hd h1{font-size:20px;color:#e6edf3;font-weight:600}
.hd h1 span{color:#58a6ff}
.hd .s{color:#6e7681;font-size:12px;margin-top:5px;line-height:1.6}
.idx{display:flex;gap:10px;overflow-x:auto;padding:10px 12px;background:#11161f;
border:1px solid #21262d;border-radius:10px;margin-bottom:14px;-webkit-overflow-scrolling:touch}
.idx>div{flex:0 0 auto;min-width:78px}
.idx span{display:block;color:#6e7681;font-size:11px}
.idx b{font-family:ui-monospace,monospace;font-size:15px;display:block}
.idx em{font-style:normal;font-size:11.5px}
.alert{margin:0 0 14px;padding:10px 13px;border-radius:9px;font-size:13px;
background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.3);color:#f85149;line-height:1.6}
.c{background:#11161f;border:1px solid #21262d;border-radius:12px;padding:15px 15px 13px;margin-bottom:12px}
.c.risk{border-color:rgba(248,81,73,.45);background:linear-gradient(180deg,rgba(248,81,73,.06),#11161f 40%)}
.ch{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.ch .nm{font-size:17px;color:#e6edf3;font-weight:600;line-height:1.3}
.ch .cd{display:block;color:#484f58;font-size:11.5px;font-weight:400;margin-top:2px;font-family:ui-monospace,monospace}
.sc{width:50px;height:50px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.sc i{width:40px;height:40px;border-radius:50%;background:#11161f;display:flex;align-items:center;
justify-content:center;font-style:normal;font-family:ui-monospace,monospace;font-size:15px;font-weight:700}
.px{font-family:ui-monospace,monospace;font-size:25px;font-weight:600;margin:9px 0 3px;letter-spacing:-.5px}
.px em{font-style:normal;font-size:15px;margin-left:6px}
.gd{display:grid;grid-template-columns:repeat(4,1fr);gap:8px 4px;margin:11px 0 4px;
padding:10px 0;border-top:1px solid #1b2027;border-bottom:1px solid #1b2027}
.gd div{text-align:center}
.gd i{display:block;font-style:normal;color:#484f58;font-size:10.5px;margin-bottom:2px}
.gd b{font-family:ui-monospace,monospace;font-size:12.5px;color:#8b949e;font-weight:500}
.tg{margin-top:10px;line-height:1.9}
.tg span{display:inline-block;padding:2px 8px;border-radius:11px;font-size:11.5px;margin:0 4px 4px 0}
.t-g{background:rgba(63,185,80,.13);color:#3fb950}
.t-w{background:rgba(210,153,34,.13);color:#d29922}
.t-b{background:rgba(248,81,73,.13);color:#f85149}
.t-i{background:rgba(88,166,255,.12);color:#58a6ff}
.ad{margin-top:10px;padding-top:10px;border-top:1px dashed #21262d;font-size:13px;color:#58a6ff;line-height:1.65}
.ad div{margin-bottom:3px}
.ft{margin-top:20px;color:#484f58;font-size:11.5px;line-height:1.9;border-top:1px solid #21262d;padding-top:14px}
.ft b{color:#8b949e}
.up{color:#f85149}.dn{color:#3fb950}.fl{color:#8b949e}
"""


def render_mobile_html(rows, indices=None, data_time="", title="盯盘"):
    idxs = indices or []
    idx_html = ""
    if idxs:
        items = []
        for i in idxs:
            cls = _chg_cls(i["chg"])
            items.append(f'<div><span>{H.escape(i["name"])}</span>'
                         f'<b class="{cls}">{i["price"]:.2f}</b>'
                         f'<em class="{cls}">{i["chg"]:+.2f}%</em></div>')
        idx_html = '<div class="idx">' + "".join(items) + "</div>"

    risk = [r for r in rows if r.get("sell_cnt", 0) > 0]
    ok = [r for r in rows if r.get("sell_cnt", 0) == 0]
    banner = ""
    if risk:
        banner = (f'<div class="alert">⚠ <b>{len(risk)} 只触发卖出信号</b>　'
                  f'{"、".join(r["name"] for r in risk[:4])}<br>先减仓，别等破位</div>')

    def card(r):
        col = _score_color(r["score"])
        cls = "c risk" if r.get("sell_cnt", 0) > 0 else "c"
        ring = f"background:conic-gradient({col} {r['score']*3.6}deg,#21262d 0)"
        ma = "/".join(f"{x:.2f}" for x in r["ma"])
        tg = "".join(f'<span class="t-{c}">{H.escape(t)}</span>'
                     for t, c in r["tags"][:6])
        ad = "".join(f"<div>→ {H.escape(a)}</div>" for a in r["advice"])
        return f"""
<div class="{cls}">
 <div class="ch">
   <div><div class="nm">{H.escape(r['name'])}<span class="cd">{r['code']} · {r['board']}</span></div></div>
   <div class="sc" style="{ring}"><i style="color:{col}">{r['score']:.0f}</i></div>
 </div>
 <div class="px {_chg_cls(r['chg'])}">{r['price']:.2f}<em>{r['chg']:+.2f}%</em></div>
 <div class="gd">
   <div><i>距年内高点</i><b>{r.get('from_high','-')}%</b></div>
   <div><i>年内位置</i><b>{r['pos']:.0f}%</b></div>
   <div><i>量比</i><b>{r['vratio']}</b></div>
   <div><i>5日乖离</i><b>{r['bias5']}%</b></div>
   <div><i>ROE</i><b>{r['roe'] if r['roe'] is not None else '-'}%</b></div>
   <div><i>PE</i><b>{r['pe'] if r['pe'] else '-'}</b></div>
   <div><i>买点</i><b style="color:#3fb950">{r['buy_cnt']}/7</b></div>
   <div><i>卖点</i><b style="color:{'#f85149' if r['sell_cnt'] else '#8b949e'}">{r['sell_cnt']}</b></div>
 </div>
 <div style="font-size:11px;color:#484f58;margin-top:8px">MA5/10/20/60　{ma}</div>
 <div class="tg">{tg}</div>
 <div class="ad">{ad}</div>
</div>"""

    body = "".join(card(r) for r in risk) + "".join(card(r) for r in ok)
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>{title}</title><style>{M_CSS}</style></head><body>
<div class="hd"><h1>自选<span>盯盘</span></h1>
<div class="s">{data_time}　共 {len(rows)} 只　按"卖出信号优先"排序</div></div>
{idx_html}
{banner}
{body}
<div class="ft"><b>读法</b><br>
① 红框 = 触发卖出信号，先处理它；<br>
② 买点 ≥2 且卖点 0 才算"时机到了"；<br>
③ 跌破 10 日线先减仓，站回再谈；<br>
④ 无量拉升不追，回落 5 日线再接。<br><br>
<b style="color:#d29922">数据说明</b>：本页为收盘后快照，指标基于日K线计算。
盘中实时刷新需在电脑上运行 stock_scout.py。</div>
</body></html>"""


S_CSS = """
*{box-sizing:border-box;margin:0;padding:0;-webkit-text-size-adjust:100%}
body{background:#0f1115;color:#e8eaed;font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
padding:22px 16px 44px;max-width:680px;margin:0 auto}
.h{font-size:24px;font-weight:700;letter-spacing:.5px}
.h em{font-style:normal;color:#7c8798;font-size:13px;font-weight:400;display:block;margin-top:6px}
.sum{display:flex;gap:10px;margin:18px 0 22px;flex-wrap:wrap}
.sum>div{flex:1;min-width:100px;background:#171a21;border-radius:12px;padding:13px 14px;border:1px solid #232833}
.sum b{display:block;font-size:22px;font-family:ui-monospace,monospace;line-height:1.2}
.sum i{font-style:normal;font-size:11.5px;color:#7c8798}
.k-d{color:#ff5c5c}.k-g{color:#4ade80}.k-w{color:#fbbf24}
details{background:#171a21;border-radius:13px;margin-bottom:10px;border:1px solid #232833;
border-left:5px solid #2a303c;overflow:hidden}
details.danger{border-left-color:#ff5c5c;background:linear-gradient(90deg,rgba(255,92,92,.07),#171a21 60%)}
details.go{border-left-color:#4ade80}
details.wait{border-left-color:#3a4150}
summary{list-style:none;cursor:pointer;padding:14px 16px;-webkit-tap-highlight-color:transparent}
summary::-webkit-details-marker{display:none}
.l1{display:flex;justify-content:space-between;align-items:center;gap:10px}
.nm{font-size:16.5px;font-weight:600}
.nm span{display:block;font-size:11.5px;color:#5f6b7d;font-weight:400;font-family:ui-monospace,monospace;margin-top:1px}
.st{font-size:16px;font-weight:700;padding:5px 13px;border-radius:9px;white-space:nowrap;flex:0 0 auto}
.st.d{background:rgba(255,92,92,.16);color:#ff5c5c}
.st.g{background:rgba(74,222,128,.14);color:#4ade80}
.st.w{background:rgba(251,191,36,.13);color:#fbbf24}
.l2{display:flex;justify-content:space-between;align-items:baseline;margin-top:7px;font-size:13px;color:#7c8798}
.l2 b{font-family:ui-monospace,monospace;font-size:17px;font-weight:600;color:#e8eaed;margin-right:7px}
.up{color:#ff5c5c}.dn{color:#4ade80}.fl{color:#98a2b3}
.body{padding:2px 16px 16px;border-top:1px solid #232833;margin-top:12px}
.body h5{font-size:11px;color:#5f6b7d;letter-spacing:1.5px;margin:13px 0 7px;font-weight:600}
.body li{list-style:none;font-size:13.5px;color:#b8c0cc;padding:3px 0 3px 15px;position:relative;line-height:1.6}
.body li::before{content:"";position:absolute;left:2px;top:12px;width:5px;height:5px;border-radius:50%;background:#3a4150}
.why{font-size:14px;color:#e8eaed;background:#12161d;border-radius:9px;padding:11px 13px;line-height:1.65}
.lv{display:flex;gap:10px;margin-top:6px}
.lv>div{flex:1;background:#12161d;border-radius:9px;padding:9px 11px}
.lv i{font-style:normal;display:block;font-size:10.5px;color:#5f6b7d;margin-bottom:2px}
.lv b{font-family:ui-monospace,monospace;font-size:13.5px;font-weight:600}
.tip{margin-top:22px;font-size:12px;color:#4d5766;line-height:1.9;border-top:1px solid #232833;padding-top:15px}
.tip b{color:#7c8798}
"""

PLAIN = {
    "MACD零上金叉": "多头金叉，买点较硬",
    "MACD金叉(零下)": "金叉了，但还在弱势区",
    "MACD死叉": "动能转弱",
    "MACD底背离": "跌不动的信号",
    "MACD顶背离": "涨不动的信号",
    "分时MACD顶背离(卖点)": "盘中冲高失败",
    "均线多头排列 5>10>20": "短期趋势向上",
    "站上60日生命线": "中期趋势没坏",
    "5日上穿10日": "短线转强",
    "跌破10日线": "短线走坏",
    "60日线下方": "中期趋势偏弱",
    "KDJ低位金叉": "超卖后反弹",
    "KDJ高位死叉": "超买后回落",
    "量增价滞(出货嫌疑)": "放量却不涨，有人在卖",
    "无量拉升(虚涨)": "没量的假涨",
    "龙回头形态(涨停后缩量回踩)": "强势股回头到支撑",
    "回踩布林下轨收回": "跌到下轨被接住",
    "突破布林上轨": "短线偏热",
}


def _plain(t):
    if t in PLAIN:
        return PLAIN[t]
    if t.startswith("放量上涨"):
        return "放量上涨，资金真进来了"
    if t.startswith("5日乖离") and "超跌" in t:
        return "跌得太急，容易反弹"
    if t.startswith("5日乖离") and "超涨" in t:
        return "涨得太急，容易回头"
    if t.startswith("PSY"):
        return "情绪极冷" if "超卖" in t else "情绪过热"
    if "低位" in t:
        return "在低位区域"
    if "高位" in t:
        return "在高位区域"
    if t.startswith("ROE"):
        return "赚钱能力 " + t.replace("ROE ", "")
    if t.startswith("小市值"):
        return "盘子小，波动大"
    if "亏损" in t:
        return "公司在亏钱"
    if t.startswith("PE"):
        return "估值偏高"
    if "缩量回调" in t:
        return "缩量休息，健康"
    return t


def render_simple_html(rows, indices=None, data_time=""):
    def stat(r):
        if r["sell_cnt"] > 0:
            return "danger", "先减仓", "d"
        if r["buy_cnt"] >= 2:
            return "go", "可小试", "g"
        return "wait", "再等等", "w"

    danger = [r for r in rows if stat(r)[0] == "danger"]
    go = [r for r in rows if stat(r)[0] == "go"]
    wait = [r for r in rows if stat(r)[0] == "wait"]
    order = danger + go + wait

    def one(r):
        cls, label, sc = stat(r)
        chg_cls = _chg_cls(r["chg"])
        fh = r.get("from_high", 0)
        why = {
            "danger": "已经走坏了。按纪律先减，别等它跌透——跌透了也不会自己告诉你。",
            "go": "几个买点同时出现，是这几个里最像样子的。但只能小仓，错了就认。",
            "wait": "趋势没坏，但还没到能动手的时候。等它给信号，不要猜。",
        }[cls]
        pts = "".join(f"<li>{H.escape(_plain(t))}</li>" for t, c in r["tags"][:5])
        ma = r["ma"]
        return f"""
<details class="{cls}">
 <summary>
  <div class="l1">
    <div class="nm">{H.escape(r['name'])}<span>{r['code']}</span></div>
    <div class="st {sc}">{label}</div>
  </div>
  <div class="l2">
    <div><b class="{chg_cls}">{r['price']:.2f}</b><span class="{chg_cls}">{r['chg']:+.2f}%</span></div>
    <div>距年内高点 {fh}%</div>
  </div>
 </summary>
 <div class="body">
   <h5>为什么</h5>
   <div class="why">{why}</div>
   <h5>看到的信号</h5>
   <ul>{pts or '<li>没有明显信号</li>'}</ul>
   <h5>关键价位</h5>
   <div class="lv">
     <div><i>反弹到这减</i><b>{ma[0]:.2f}</b></div>
     <div><i>站上才算好</i><b>{ma[1]:.2f}</b></div>
     <div><i>中期生命线</i><b>{ma[3]:.2f}</b></div>
   </div>
 </div>
</details>"""

    idx = ""
    if indices:
        parts = []
        for i in indices[:3]:
            c = _chg_cls(i["chg"])
            parts.append(f'<span class="{c}">{H.escape(i["name"])} {i["price"]:.0f} {i["chg"]:+.2f}%</span>')
        idx = "　".join(parts)

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="今天怎么办">
<title>今天怎么办</title><style>{S_CSS}</style></head><body>

<div class="h">今天怎么办
  <em>{data_time}　{idx}</em>
</div>

<div class="sum">
  <div><b class="k-d">{len(danger)}</b><i>只要先处理</i></div>
  <div><b class="k-g">{len(go)}</b><i>只可以试试</i></div>
  <div><b class="k-w">{len(wait)}</b><i>只继续等</i></div>
</div>

{''.join(one(r) for r in order)}

<div class="tip">
<b>怎么看</b>　红色左条 = 先减仓（已经走坏）；绿色左条 = 可小试（买点共振，只能小仓）；
灰色 = 再等等（没到时机）。<b>点一下卡片</b>能展开原因和价位。<br><br>
<b>执行顺序</b>　先处理红色 → 再看绿色 → 灰色不用管。<br><br>
<b>数据</b>　{data_time}，收盘快照，盘中不会自己变。<br>
<b>风险</b>　信号是概率，不是承诺。止损必须自己设。
</div>
</body></html>"""
