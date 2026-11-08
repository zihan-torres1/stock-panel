# -*- coding: utf-8 -*-
"""
render_app.py — 一个文件、两个页面
  ① 今天怎么办：持仓 / 关注 两块，点进详情
  ② 盯盘面板：持仓表 / 关注表，可排序、可按范围筛选
详情页：结论和标签置顶 → K线 → 基本面 → 资金流
"""

import json

TIPS = {
    "60日线下方": "股价在60日均线之下。60日线俗称「生命线」，跌破说明中期趋势偏弱，反弹容易夭折。",
    "站上60日生命线": "股价在60日均线之上，中期趋势还没坏。这是判断「能不能拿」的第一道关。",
    "跌破10日线": "股价跌穿10日均线。10日线是短线强弱的分界，跌破通常意味着短线走坏——先减仓，站回再谈。",
    "5日上穿10日": "5日均线从下往上穿过10日均线，俗称「短线金叉」，说明最近几天的买盘开始强过前十几天。",
    "均线多头排列 5>10>20": "短期均线在长期均线之上，且层层向上（5日>10日>20日）。越近的买盘越强，趋势健康向上。",
    "PSY超卖": "PSY叫心理线，统计12天里有几天在上涨。低于25说明只有3天在涨，市场情绪极冷，容易出现反弹。",
    "PSY超买": "PSY高于75，说明12天里有9天以上在涨，情绪过热。这时候不是不能涨，是容易回头，别追。",
    "5日乖离超跌": "乖离率=股价离5日均线有多远。负得太多说明跌得太急，像橡皮筋被拉太长，容易往回弹。",
    "5日乖离超涨": "股价比5日均线高出太多，短期涨得太急。追高容易被套。",
    "MACD零上金叉": "MACD快线从下往上穿过慢线，且两线都在零轴上方。零轴上方的金叉，是强势中的新一波上涨，比零下金叉可靠。",
    "MACD金叉(零下)": "MACD金叉了，但两线还在零轴下方。属于弱势反弹，力度不如零上金叉，只能小仓试。",
    "MACD死叉": "快线从上往下穿过慢线，上涨动能衰竭。零下死叉往往是一段新下跌的开始。",
    "MACD底背离": "股价创新低，但MACD的低点没跟着创新低。价格还在跌，但力气跟不上了。这是抄底的核心信号。",
    "MACD顶背离": "股价创新高，但MACD的高点没跟着创新高。价格还在涨，力气用完了。这是逃顶信号。",
    "分时MACD顶背离(卖点)": "盘中5分钟K线出现顶背离：股价还在冲高，分时MACD不跟了，成交量也跟不上。这是最核心的卖点。",
    "KDJ低位金叉": "KDJ在20以下的超卖区金叉，说明短期跌过头、开始有人接，反弹概率较高。",
    "KDJ高位死叉": "KDJ在80以上的超买区死叉，短期回调概率高。",
    "放量上涨": "成交量明显比平时大，同时股价在涨。有真金白银进场，最健康的量价配合。",
    "缩量回调(健康)": "价格小幅回落，但成交量明显萎缩。没人恐慌抛售，只是上涨途中的正常休息。",
    "量增价滞(出货嫌疑)": "成交量放大了，但股价不涨。有人借着热闹偷偷卖，见到就要减。",
    "无量拉升(虚涨)": "股价在涨，但几乎没有成交量。用少量单子把价格顶上去的空拉，千万别追。",
    "龙回头形态(涨停后缩量回踩)": "前期有过涨停的强势股，回调时成交量极度萎缩，正好踩到支撑位。书里的龙回头战法，等第二波。",
    "回踩布林下轨收回": "股价跌到布林线下轨位置，然后被买盘接住了。短线超跌反弹信号。",
    "突破布林上轨": "股价冲出布林线上轨。短线偏热，容易回调，不是买点。",
    "DMI超跌反弹": "DMI里的PDI跌到极低，说明跌到极端位置，可能出现反弹。",
    "小市值(<30亿)": "总市值不到30亿。盘子小、波动大，容易被资金拉抬或砸盘。",
    "公司亏损(PE<0)": "市盈率为负，公司在亏钱。这时候看估值没意义，只能看图。",
    "PE偏高": "市盈率高于市场平均或历史水平。买贵的公司，需要未来增长来消化估值。",
    "年内低位": "当前价在过去一年价格区间里处于很低的位置。上方套牢盘多，但也意味着已经跌透了。",
    "年内高位": "当前价接近过去一年最高区域。获利盘多，一有风吹草动容易踩踏。",
    "超涨": "短期涨得太快，离均线太远，容易回头。",
}

HEAD_TIPS = {
    "评分": "综合分（0-100）。趋势32% + 动能30% + 量能23% + 基本面15%，再减去风险扣分。50分是中性。",
    "档位": "≥76 重点跟踪 / ≥66 可关注 / ≥55 观察 / 低于55 回避。",
    "四维": "从左到右：趋势、动能、量能、基本面。每项满分100，50为中性，柱子越高越强。",
    "买点": "命中了几个买入信号（共7项）。书里说：单一指标不算时机，≥2项共振才算。点这里看详细清单。",
    "卖点": "命中了几个卖出信号（共5项）。≥1就该处理。点这里看详细清单。",
    "ROE": "净资产收益率。公司用股东的钱赚钱的效率。长期10%-30%算健康，这里用 PB÷PE 反推。",
    "PE": "市盈率。你花多少钱买1块钱的年利润。负数表示公司亏损。",
    "量比": "今天的成交量 ÷ 过去5天平均。>1.2放量，<0.8缩量。",
    "位置": "当前价在过去一年价格区间里的分位。0%是年内最低，100%是最高。",
    "距高点": "离过去一年最高价还差多少。负数，越小说明跌得越多。",
}

# 买点/卖点清单（用于界面说明）
BUY_LIST = [
    ("MACD金叉", "快线从下向上穿越慢线，下跌动能转成上涨动能"),
    ("底背离", "股价创新低但MACD没创新低，跌不动了"),
    ("KDJ低位金叉", "KDJ在超卖区金叉，短期跌过头了开始有人接"),
    ("放量上涨", "成交量放大且股价上涨，有真金白银进场"),
    ("龙回头", "涨停后缩量回踩支撑，强势股的第二波机会"),
    ("回踩布林下轨", "跌到布林下轨被接住，短线超跌反弹"),
    ("5日上穿10日", "5日均线上穿10日均线，短线转强"),
]
SELL_LIST = [
    ("顶背离", "股价创新高但MACD没创新高，涨不动了"),
    ("量增价滞", "成交量放大但价格不涨，有人在借机出货"),
    ("无量拉升", "股价在涨但没成交量，虚涨，容易跌回去"),
    ("跌破10日线", "跌穿短线强弱分界，趋势走坏"),
    ("KDJ高位死叉", "超买区死叉，短期回调概率高"),
]


def tip_of(t: str) -> str:
    if t in TIPS:
        return TIPS[t]
    if t.startswith("PSY"):
        return TIPS["PSY超卖"] if "超卖" in t else TIPS["PSY超买"]
    if t.startswith("5日乖离"):
        return TIPS["5日乖离超跌"] if "超跌" in t else TIPS["5日乖离超涨"]
    if t.startswith("ROE"):
        return ("净资产收益率。公司用股东的钱赚钱的效率，这里约 " + t.replace("ROE", "").strip()
                + "。长期10%-30%算健康，太低说明不赚钱，太高要查是不是靠高负债撑的。")
    if "低位" in t:
        return TIPS["年内低位"]
    if "高位" in t:
        return TIPS["年内高位"]
    if t.startswith("放量上涨"):
        return TIPS["放量上涨"]
    if t.startswith("PE"):
        return TIPS["PE偏高"]
    return ""


CSS = """
*{box-sizing:border-box;margin:0;padding:0;-webkit-text-size-adjust:100%}
body{background:#0f1115;color:#e8eaed;font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
padding:18px 14px 50px;max-width:1000px;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.title{font-size:21px;font-weight:700}
.title em{font-style:normal;display:block;color:#7c8798;font-size:12px;font-weight:400;margin-top:4px}
.tabs{display:flex;gap:5px;background:#171a21;border:1px solid #232833;border-radius:11px;padding:4px}
.tabs button{background:none;border:none;color:#7c8798;font-size:13.5px;font-weight:600;
padding:8px 13px;border-radius:8px;cursor:pointer;font-family:inherit;transition:.15s}
.tabs button.on{background:#232833;color:#e8eaed}
.savebtn{background:#1d4ed8;border:none;color:#fff;padding:8px 14px;border-radius:9px;
font-size:13px;cursor:pointer;font-family:inherit;font-weight:600}
.savebtn:hover{background:#2563eb}
.sum{display:flex;gap:10px;margin:14px 0 16px}
.sum>div{flex:1;background:#171a21;border-radius:12px;padding:12px 14px;border:1px solid #232833}
.sum b{display:block;font-size:21px;font-family:ui-monospace,monospace;line-height:1.2}
.sum i{font-style:normal;font-size:11.5px;color:#7c8798}
.k-d{color:#ff5c5c}.k-g{color:#4ade80}.k-w{color:#fbbf24}

/* 统计卡 */
.stat2{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:9px;margin:12px 0 4px}
.s2{background:#171a21;border:1px solid #232833;border-radius:11px;padding:11px 13px}
.s2 i{font-style:normal;display:block;font-size:10.5px;color:#5f6b7d;margin-bottom:4px}
.s2 b{font-family:ui-monospace,monospace;font-size:17px;font-weight:700;color:#e8eaed;letter-spacing:-.5px}
/* 分组 */
.gtitle{display:flex;align-items:center;gap:9px;margin:20px 0 10px;font-size:14px;font-weight:600;color:#c8d0da}
.gtitle::after{content:"";flex:1;height:1px;background:#232833}
.gtitle b{font-family:ui-monospace,monospace;color:#58a6ff;font-size:13px}
.gtitle.pos b{color:#4ade80}

/* 卡片 */
.card{background:#171a21;border-radius:13px;margin-bottom:10px;border:1px solid #232833;
border-left:5px solid #2a303c;padding:13px 15px;cursor:pointer;transition:.15s}
.card:hover{background:#1b1f28;transform:translateY(-1px)}
.card.danger{border-left-color:#ff5c5c;background:linear-gradient(90deg,rgba(255,92,92,.07),#171a21 60%)}
.card.go{border-left-color:#4ade80}
.card.wait{border-left-color:#3a4150}
.card.is-pos{border-left-color:#58a6ff!important;background:linear-gradient(90deg,rgba(88,166,255,.08),#171a21 55%)}
.l1{display:flex;justify-content:space-between;align-items:center;gap:10px}
.nm{font-size:16.5px;font-weight:600;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.nm .c{font-size:11.5px;color:#5f6b7d;font-weight:400;font-family:ui-monospace,monospace}
.st{font-size:14.5px;font-weight:700;padding:5px 12px;border-radius:9px;white-space:nowrap;flex:0 0 auto}
.st.d{background:rgba(255,92,92,.16);color:#ff5c5c}
.st.g{background:rgba(74,222,128,.14);color:#4ade80}
.st.w{background:rgba(251,191,36,.13);color:#fbbf24}
.l2{display:flex;justify-content:space-between;align-items:baseline;margin-top:7px;font-size:13px;color:#7c8798}
.l2 b{font-family:ui-monospace,monospace;font-size:17px;font-weight:600;color:#e8eaed;margin-right:7px}
.up{color:#ff5c5c}.dn{color:#4ade80}.fl{color:#98a2b3}
.chk{width:17px;height:17px;accent-color:#58a6ff;cursor:pointer;flex:0 0 auto}
.grp{display:inline-block;font-size:10px;padding:1px 6px;border-radius:4px;font-weight:500}
.grp-pos{background:rgba(88,166,255,.16);color:#58a6ff}
.grp-watch{background:rgba(124,135,152,.14);color:#8b98ab}
.pri-h{background:rgba(255,92,92,.15);color:#ff5c5c}
.pri-m{background:rgba(251,191,36,.13);color:#fbbf24}
.pri-l{background:rgba(124,135,152,.13);color:#8b98ab}

/* 筛选 */
.filters{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0 14px;align-items:center}
.filters button{background:#171a21;border:1px solid #232833;color:#7c8798;padding:6px 12px;
border-radius:8px;font-size:12.5px;cursor:pointer;font-family:inherit;transition:.15s}
.filters button:hover{border-color:#3a4150;color:#b8c0cc}
.filters button.on{background:#232833;color:#e8eaed;border-color:#4a5568}

/* 表格 */
.tw{background:#171a21;border:1px solid #232833;border-radius:13px;overflow-x:auto;margin-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}
thead th{text-align:left;padding:10px;color:#7c8798;font-weight:600;font-size:11.5px;
border-bottom:1px solid #232833;background:#171a21;position:sticky;top:0;z-index:2}
thead th[data-tip]{cursor:help;border-bottom:1px dotted #3a4150}
thead th.sortable{cursor:pointer;user-select:none}
thead th.sortable:hover{color:#c8d0da}
thead th .ar{color:#58a6ff;margin-left:3px;font-size:10px}
tbody tr{border-bottom:1px solid #1b2027;cursor:pointer}
tbody tr[data-fitem]:hover{background:#1b1f28}
tbody tr.is-pos td{background:rgba(88,166,255,.045)}
tbody tr.is-pos .tname::after{content:"持仓";font-size:9.5px;color:#58a6ff;background:rgba(88,166,255,.15);
padding:1px 5px;border-radius:3px;margin-left:6px;vertical-align:middle}
td{padding:10px}
.tcode{font-family:ui-monospace,monospace;color:#5f6b7d;font-size:11.5px}
.tname{color:#e8eaed;font-weight:600}
.scorec{font-family:ui-monospace,monospace;font-weight:700;font-size:14px}
.dims{display:flex;gap:3px;align-items:flex-end;height:20px}
.dims i{width:6px;border-radius:2px 2px 0 0;display:block}
.tag{display:inline-block;padding:2px 8px;border-radius:11px;font-size:11.5px;margin:0 4px 4px 0;cursor:help}
.tag:hover{filter:brightness(1.35)}
.t-good{background:rgba(74,222,128,.13);color:#4ade80}
.t-warn{background:rgba(251,191,36,.13);color:#fbbf24}
.t-bad{background:rgba(255,92,92,.13);color:#ff5c5c}
.t-info{background:rgba(88,166,255,.12);color:#58a6ff}
.badge{font-size:11.5px;padding:2px 9px;border-radius:5px;white-space:nowrap}
.bg-a{color:#ff5c5c;background:rgba(255,92,92,.1);border:1px solid rgba(255,92,92,.3)}
.bg-b{color:#fbbf24;background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3)}
.bg-c{color:#58a6ff;background:rgba(88,166,255,.08);border:1px solid rgba(88,166,255,.25)}
.bg-d{color:#7c8798;border:1px solid #2a303c}
tr.grow td{background:#12161d;color:#7c8798;font-size:11.5px;font-weight:600;
letter-spacing:.5px;padding:7px 10px}
tr.grow b{color:#58a6ff;font-family:ui-monospace,monospace}
tr.grow.pos b{color:#4ade80}

/* 说明卡 */
details.explain{background:#171a21;border:1px solid #232833;border-radius:12px;margin:12px 0;overflow:hidden}
details.explain summary{padding:11px 15px;cursor:pointer;font-size:13px;color:#58a6ff;list-style:none}
details.explain summary::-webkit-details-marker{display:none}
details.explain summary::before{content:"▸ ";color:#4a5568}
details.explain[open] summary::before{content:"▾ "}
.ex-body{padding:0 15px 14px;display:grid;grid-template-columns:1fr 1fr;gap:18px}
.ex-body h5{font-size:11.5px;color:#7c8798;margin-bottom:8px;letter-spacing:.5px}
.ex-body ol{list-style:none;counter-reset:i}
.ex-body li{counter-increment:i;font-size:12.5px;color:#a9b1ba;padding:3px 0 3px 20px;position:relative;line-height:1.55}
.ex-body li::before{content:counter(i);position:absolute;left:0;top:4px;width:14px;height:14px;
background:#232833;border-radius:50%;font-size:9px;color:#7c8798;text-align:center;line-height:14px}
.ex-body b{color:#c8d0da}
.rule{margin-top:12px;padding:9px 12px;background:#12161d;border-radius:8px;
font-size:12.5px;color:#a9b1ba;line-height:1.7}
.rule em{font-style:normal;color:#fbbf24}

/* 详情 */
#detail{display:none}
.bar{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.back{background:#1b1f28;border:1px solid #2a303c;color:#b8c0cc;border-radius:9px;
padding:7px 13px;font-size:13.5px;cursor:pointer;font-family:inherit}
.back:hover{background:#232833;color:#e8eaed}
.dh{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.dh .t{font-size:21px;font-weight:700}
.dh .t span{display:block;font-size:12px;color:#5f6b7d;font-weight:400;font-family:ui-monospace,monospace;margin-top:2px}
.dp{font-family:ui-monospace,monospace;font-size:31px;font-weight:700;letter-spacing:-1px;margin:5px 0 0}
.dp em{font-style:normal;font-size:16px;margin-left:8px}
.box{background:#171a21;border:1px solid #232833;border-radius:13px;padding:14px 16px;margin-top:12px}
.box h4{font-size:11px;color:#5f6b7d;letter-spacing:1.5px;font-weight:600;margin-bottom:10px}
#chart{width:100%;height:350px;display:block;border-radius:9px;background:#12161d}
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
.adv{font-size:13.5px;color:#58a6ff;line-height:1.75;padding:2px 0}
.adv div{margin-bottom:3px}
.vhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.vscore{font-family:ui-monospace,monospace;font-size:30px;font-weight:700;line-height:1}
.vdims{display:flex;gap:5px;align-items:flex-end;height:26px}
.vdims i{width:9px;border-radius:2px 2px 0 0;display:block}
.vtxt{flex:1;min-width:180px;font-size:12.5px;color:#7c8798;line-height:1.6}

.cobtn{background:rgba(88,166,255,.12);border:1px solid rgba(88,166,255,.35);color:#58a6ff;
border-radius:9px;padding:7px 14px;font-size:13.5px;cursor:pointer;font-family:inherit;margin-left:auto}
.cobtn:hover{background:rgba(88,166,255,.2)}
#company{display:none}
.co-h{font-size:22px;font-weight:700;margin-bottom:2px}
.co-h span{display:block;font-size:12px;color:#5f6b7d;font-weight:400;font-family:ui-monospace,monospace;margin-top:3px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.kv>div{background:#12161d;border-radius:9px;padding:10px 12px}
.kv i{font-style:normal;display:block;font-size:10.5px;color:#5f6b7d;margin-bottom:3px}
.kv b{font-size:13px;font-weight:500;color:#c8d0da;word-break:break-all}
.biz{font-size:13.5px;color:#b8c0cc;line-height:1.85;margin-top:6px}
.biz b{color:#e8eaed}
.fin-t{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}
.fin-t th,.fin-t td{padding:8px 9px;border-bottom:1px solid #1b2027;text-align:right;white-space:nowrap}
.fin-t th:first-child,.fin-t td:first-child{text-align:left;color:#8b98ab}
.fin-t thead th{color:#5f6b7d;font-weight:500;font-size:11px;border-bottom:1px solid #2a303c}
.fin-t td{font-family:ui-monospace,monospace;color:#e8eaed}
.fin-t tr:hover td{background:#151a22}
.news a{display:block;padding:9px 0;border-bottom:1px solid #1b2027;color:#b8c0cc;
text-decoration:none;font-size:13.5px;line-height:1.6}
.news a:hover{color:#58a6ff}
.news a span{display:block;font-size:11px;color:#5f6b7d;font-family:ui-monospace,monospace;margin-top:2px}
#tip{position:fixed;z-index:9999;max-width:300px;background:#1e232c;border:1px solid #384150;
border-radius:9px;padding:10px 13px;font-size:12.5px;line-height:1.65;color:#c8d0da;
box-shadow:0 8px 26px rgba(0,0,0,.55);display:none;pointer-events:none}
#tip b{display:block;color:#e8eaed;font-size:12.5px;margin-bottom:4px}
"""

JS = r"""
const DATA = __DATA__;
let curTab = 0, curStock = -1, _sY = 0, sortKey = '', sortAsc = false, curTheme = '__all__';
const $=id=>document.getElementById(id);
const fmt=(v,n=2)=>v==null?'-':Number(v).toFixed(n);

/* ---------- 持仓勾选 ---------- */
function getPicks(){try{return JSON.parse(localStorage.getItem('st_picks')||'[]')}catch(e){return[]}}
function setPicks(a){localStorage.setItem('st_picks', JSON.stringify(a))}

/* ---------- 持仓成本：存本机，改完立即生效，不用下载 ---------- */
function getHold(){try{return JSON.parse(localStorage.getItem('st_hold')||'{}')}catch(e){return{}}}
function setHold(o){localStorage.setItem('st_hold', JSON.stringify(o))}
function effHold(d){
  const h = getHold()[d.code];
  if(h && h.shares>0) return h;
  if(d.cost && d.shares) return {cost:d.cost, shares:d.shares};
  return null;
}
function prevOf(d){ return d.chg ? d.price/(1+d.chg/100) : d.price; }

function toast(msg){
  let t = document.getElementById('__toast');
  if(!t){
    t = document.createElement('div'); t.id='__toast';
    t.style.cssText='position:fixed;left:50%;bottom:34px;transform:translateX(-50%);background:#1e232c;border:1px solid #384150;color:#e8eaed;padding:10px 18px;border-radius:10px;font-size:13px;z-index:10000;box-shadow:0 8px 26px rgba(0,0,0,.55);opacity:0;transition:opacity .2s;pointer-events:none';
    document.body.appendChild(t);
  }
  t.textContent = msg; t.style.opacity = 1;
  clearTimeout(t._h); t._h = setTimeout(()=>{ t.style.opacity = 0; }, 2400);
}

function editHold(code){
  const d = DATA.find(x=>x.code===code); if(!d) return;
  const h = effHold(d) || {};
  const s = prompt(d.name+' '+code+'\n\n输入成本价（元）。留空并确定 = 清空该股成本', h.cost!=null?h.cost:'');
  if(s===null) return;
  if(String(s).trim()===''){ const o=getHold(); delete o[code]; setHold(o); applyHold(); toast('已清空 '+d.name+' 的成本'); return; }
  const cost = parseFloat(s);
  if(!(cost>0)){ alert('成本价要大于 0'); return; }
  const sh = prompt('持有多少股？', h.shares||1000);
  if(sh===null) return;
  const shares = parseInt(sh,10);
  if(!(shares>0)){ alert('股数要大于 0'); return; }
  const o = getHold(); o[code] = {cost:cost, shares:shares}; setHold(o);
  applyHold();
  toast(d.name+' 已更新：成本 '+cost.toFixed(2)+' × '+shares+' 股');
}

function applyHold(){
  document.querySelectorAll('tr[data-fitem]').forEach(tr=>{
    const d = DATA.find(x=>x.code===tr.dataset.code); if(!d) return;
    const h = effHold(d);
    const cl = tr.querySelector('.costline');
    if(cl) cl.textContent = h ? (' · 成本'+h.cost.toFixed(2)+'×'+h.shares+'股') : ' · 点此处填成本';
    const td = tr.querySelector('.pnlcell');
    if(td){
      if(!h){ td.innerHTML = '<span style="color:#3d4450">—</span>'; tr.dataset.pnl = -999999; }
      else{
        const pnl = (d.price-h.cost)*h.shares;
        const pct = (d.price/h.cost-1)*100;
        const c = pnl>0?'#ff5c5c':(pnl<0?'#4ade80':'#7c8798');
        td.innerHTML = '<b style="color:'+c+';font-family:ui-monospace,monospace">'+(pnl>0?'+':'')+pnl.toFixed(0)+'</b>'
          +'<div style="font-size:10.5px;color:'+c+'">'+(pct>0?'+':'')+pct.toFixed(2)+'%</div>';
        tr.dataset.pnl = pnl;
      }
    }
  });
  refreshStats(new Set(getPicks()));
  refreshSum();
}

function togglePick(el){
  const code = el.dataset.code;
  let p = getPicks();
  if(el.checked){ if(p.indexOf(code)<0) p.push(code); }
  else { p = p.filter(x=>x!==code); }
  setPicks(p);
  applyPicks();
}

function applyPicks(){
  const p = new Set(getPicks());
  document.querySelectorAll('.chk').forEach(cb=>{ cb.checked = p.has(cb.dataset.code); });
  document.querySelectorAll('[data-fitem]').forEach(el=>{
    el.classList.toggle('is-pos', p.has(el.dataset.code));
  });
  layout();
  applyHold();
}

/* ---------- 分组重排（持仓区 / 关注区） ---------- */
function layout(){
  const p = new Set(getPicks());
  // 卡片
  const posC = $('posCards'), watC = $('watchCards');
  if(posC && watC){
    const cards = [...document.querySelectorAll('.card')];
    cards.sort((a,b)=>parseFloat(b.dataset.score)-parseFloat(a.dataset.score));
    cards.forEach(el=>{ (p.has(el.dataset.code)?posC:watC).appendChild(el); });
    const nP = cards.filter(el=>p.has(el.dataset.code)).length;
    $('posCnt').textContent = nP;
    $('watchCnt').textContent = cards.length - nP;
    $('posGroup').style.display = nP ? 'block' : 'none';
  }
  // 表格行
  const pb = $('posBody'), wb = $('watchBody');
  if(pb && wb){
    const rows = [...document.querySelectorAll('tr[data-fitem]')];
    const pos = rows.filter(r=>p.has(r.dataset.code));
    const wat = rows.filter(r=>!p.has(r.dataset.code));
    pos.forEach(r=>pb.appendChild(r));
    wat.forEach(r=>wb.appendChild(r));
    $('posCnt2').textContent = pos.length;
    $('watchCnt2').textContent = wat.length;
    $('posWrap').style.display = pos.length ? 'block' : 'none';
  }
  refreshStats(p);
  refreshSum();
}

function refreshStats(p){
  let mv=0, cost=0, pnl=0, day=0, n=0, hasCost=0;
  DATA.forEach(d=>{
    if(!p.has(d.code)) return;
    n++;
    const h = effHold(d);
    if(h){
      const prev = prevOf(d);
      mv += d.price*h.shares;
      cost += h.cost*h.shares;
      pnl += (d.price-h.cost)*h.shares;
      day += (d.price-prev)*h.shares;
      hasCost++;
    }
  });
  const el = $('stMv'); if(!el) return;
  el.textContent = hasCost ? (mv/10000).toFixed(2)+'万' : '—';
  $('stN').textContent = n;
  const pv = $('stPnl'), dv = $('stDay');
  if(hasCost){
    pv.textContent = (pnl>0?'+':'')+pnl.toFixed(0);
    pv.style.color = pnl>0?'#ff5c5c':(pnl<0?'#4ade80':'#8b98ab');
    dv.textContent = (day>0?'+':'')+day.toFixed(0);
    dv.style.color = day>0?'#ff5c5c':(day<0?'#4ade80':'#8b98ab');
  } else {
    pv.textContent='—'; dv.textContent='—'; pv.style.color=dv.style.color='#7c8798';
  }
  buildStruct(p);
  buildCheck(p);
}

function buildStruct(p){
  const box = $('structBox'), wrap = $('structBars');
  if(!box) return;
  const arr = DATA.filter(d=>p.has(d.code));
  const withMv = arr.filter(d=>d.mv!=null);
  if(!withMv.length){ box.style.display='none'; return; }
  box.style.display='block';
  const total = withMv.reduce((a,d)=>a+d.mv,0) || 1;
  const byTheme = {};
  withMv.forEach(d=>{ byTheme[d.theme||'未分类'] = (byTheme[d.theme||'未分类']||0) + d.mv; });
  const cols = ['#58a6ff','#a371f7','#4ade80','#fbbf24','#ff5c5c','#38bdf8','#fb7185'];
  wrap.innerHTML = Object.entries(byTheme).sort((a,b)=>b[1]-a[1]).map((x,i)=>{
    const pct = x[1]/total*100;
    return '<div style="margin-bottom:9px">'+
      '<div style="display:flex;justify-content:space-between;font-size:12px;color:#8b98ab;margin-bottom:4px">'+
      '<span>'+x[0]+'</span><span style="font-family:ui-monospace,monospace">'+pct.toFixed(1)+'%　'+(x[1]/10000).toFixed(1)+'万</span></div>'+
      '<div style="height:9px;background:#12161d;border-radius:5px;overflow:hidden">'+
      '<i style="display:block;height:100%;width:'+pct+'%;background:'+cols[i%cols.length]+';border-radius:5px"></i></div></div>';
  }).join('');
}

function buildCheck(p){
  const box = $('checkBox'), list = $('checkList');
  if(!box) return;
  const arr = DATA.filter(d=>p.has(d.code));
  if(!arr.length){ box.style.display='none'; return; }
  box.style.display='block';
  const items = [];

  // 集中度
  const withMv = arr.filter(d=>d.mv!=null);
  if(withMv.length){
    const total = withMv.reduce((a,d)=>a+d.mv,0)||1;
    const top = withMv.slice().sort((a,b)=>b.mv-a.mv)[0];
    const pct = top.mv/total*100;
    if(pct>40) items.push(['warn','集中度偏高', top.name+' 占了 '+pct.toFixed(0)+'%，单一持仓过重，一次判断失误会很痛']);
    else if(pct>25) items.push(['info','集中度', '最大单只 '+top.name+' '+pct.toFixed(0)+'%，尚可接受']);
    else items.push(['good','分散度','最大单只 '+top.name+' '+pct.toFixed(0)+'%，仓位比较分散']);
  }
  // 卖出信号
  const sell = arr.filter(d=>d.sell_cnt>0);
  if(sell.length) items.push(['bad','风控', sell.length+' 只触发卖出信号：'+sell.map(d=>d.name).join('、')+'，按纪律先减']);
  // 深亏
  const deep = arr.filter(d=>d.pnl_pct!=null && d.pnl_pct<-10);
  if(deep.length) items.push(['warn','亏损扩大', deep.length+' 只浮亏超 10%：'+deep.map(d=>d.name+' '+d.pnl_pct.toFixed(0)+'%').join('、')+'，检查是否已破位']);
  // 盈利回撤
  const win = arr.filter(d=>d.pnl_pct!=null && d.pnl_pct>20);
  if(win.length) items.push(['good','浮盈较厚', win.map(d=>d.name+' '+d.pnl_pct.toFixed(0)+'%').join('、')+'，可考虑分批锁定']);
  // 无成本
  const noCost = arr.filter(d=>d.cost==null);
  if(noCost.length) items.push(['info','待补充', noCost.length+' 只没填成本价，盈亏算不出来：'+noCost.map(d=>d.name).join('、')]);
  // 位置
  const lowPos = arr.filter(d=>d.pos<20).length;
  if(lowPos>=2) items.push(['info','位置', lowPos+' 只处于年内低位区，跌透了但没走出趋势，别急着补']);

  const icon = {good:'✓',warn:'!',bad:'✕',info:'·'};
  const color = {good:'#4ade80',warn:'#fbbf24',bad:'#ff5c5c',info:'#7c8798'};
  list.innerHTML = items.map(x=>
    '<div style="display:flex;gap:8px;padding:5px 0;font-size:13px;line-height:1.65">'+
    '<span style="color:'+color[x[0]]+';font-weight:700;flex:0 0 14px">'+icon[x[0]]+'</span>'+
    '<span><b style="color:#c8d0da">'+x[1]+'</b>　<span style="color:#8b98ab">'+x[2]+'</span></span></div>').join('');
}

function refreshSum(){
  const p = new Set(getPicks());
  let sell=0, go=0, n=0;
  document.querySelectorAll('#cardsPool .card').forEach(el=>{
    if(p.size && !p.has(el.dataset.code)) return;
    n++;
    if(el.classList.contains('danger')) sell++;
    if(el.classList.contains('go')) go++;
  });
  const s = document.querySelectorAll('#page0 .sum b');
  if(s.length===3){ s[0].textContent=sell; s[1].textContent=go; s[2].textContent=n-sell-go; }
  $('sumScope').textContent = p.size ? '（仅持仓）' : '（全部，未勾选持仓）';
}

/* ---------- 排序 ---------- */
function sortBy(key){
  if(sortKey===key){ sortAsc = !sortAsc; } else { sortKey = key; sortAsc = false; }
  const kk = key.toLowerCase();
  ['posBody','watchBody'].forEach(id=>{
    const tb = $(id); if(!tb) return;
    const rows = [...tb.querySelectorAll('tr')];
    rows.sort((a,b)=>{
      let x = parseFloat(a.dataset[kk]), y = parseFloat(b.dataset[kk]);
      if(isNaN(x)) x = sortAsc ? 1e18 : -1e18;
      if(isNaN(y)) y = sortAsc ? 1e18 : -1e18;
      return sortAsc ? x-y : y-x;
    });
    rows.forEach(r=>tb.appendChild(r));
  });
  document.querySelectorAll('thead th.sortable').forEach(th=>{
    const ar = th.querySelector('.ar'); if(ar) ar.remove();
    th.style.color='';
  });
  document.querySelectorAll('thead th[data-key="'+key+'"]').forEach(th=>{
    th.style.color='#58a6ff';
    th.insertAdjacentHTML('beforeend','<span class="ar">'+(sortAsc?'▲':'▼')+'</span>');
  });
}

/* ---------- 范围筛选 ---------- */
function num(id){ const v=$(id).value; return v===''?null:parseFloat(v); }
function applyFilter(){
  const fs=num('fScore'), fb=num('fBuy'), fsl=num('fSell'), pm=num('fPeMin'),
        px=num('fPeMax'), fr=num('fRoe'), fv=num('fVr');
  document.querySelectorAll('tr[data-fitem]').forEach(tr=>{
    const d = tr.dataset;
    let ok = true;
    if(fs!==null && parseFloat(d.score)<fs) ok=false;
    if(fb!==null && parseFloat(d.buy)<fb) ok=false;
    if(fsl!==null && parseFloat(d.sell)>fsl) ok=false;
    if(pm!==null && (parseFloat(d.pe)||-1e9)<pm) ok=false;
    if(px!==null && (parseFloat(d.pe)||1e9)>px) ok=false;
    if(fr!==null && (parseFloat(d.roe)||-1e9)<fr) ok=false;
    if(fv!==null && parseFloat(d.vr)<fv) ok=false;
    if(curTheme!=='__all__' && d.theme!==curTheme) ok=false;
    tr.style.display = ok?'':'none';
  });
  document.querySelectorAll('.card').forEach(c=>{
    let ok = true;
    if(fs!==null && parseFloat(c.dataset.score)<fs) ok=false;
    if(curTheme!=='__all__' && c.dataset.theme!==curTheme) ok=false;
    c.style.display = ok?'':'none';
  });
}
function resetFilter(){
  ['fScore','fBuy','fSell','fPeMin','fPeMax','fRoe','fVr'].forEach(id=>$(id).value='');
  curTheme='__all__';
  document.querySelectorAll('.filters button').forEach(b=>b.classList.remove('on'));
  document.querySelector('.filters button').classList.add('on');
  applyFilter();
}
function setTheme(btn,val){
  document.querySelectorAll('.filters button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on'); curTheme = val; applyFilter();
}

/* ---------- Tab / 详情 ---------- */
function switchTab(i){
  curTab = i;
  $('page0').style.display = i===0?'block':'none';
  $('page1').style.display = i===1?'block':'none';
  $('detail').style.display = 'none';
  document.querySelectorAll('.tabs button').forEach((b,k)=>b.className = k===i?'on':'');
  window.scrollTo(0,0);
}

function openDetail(i){
  curStock = i;
  $('company').style.display='none';
  const d = DATA[i];
  _sY = window.scrollY;
  $('page0').style.display='none'; $('page1').style.display='none';
  $('detail').style.display='block';
  window.scrollTo(0,0);

  const cls = d.chg>0?'up':(d.chg<0?'dn':'fl');
  const stc = d.status==='danger'?'d':(d.status==='go'?'g':'w');
  $('dh').innerHTML = '<div class="t">'+d.name+'<span>'+d.code+' · '+d.board+' · '+(d.theme||'')+'</span></div>'+
    '<div class="st '+stc+'">'+d.status_text+'</div>';
  $('dp').innerHTML = fmt(d.price)+'<em class="'+cls+'">'+(d.chg>0?'+':'')+fmt(d.chg)+'%</em>';

  // 综合判断（置顶）
  const col = d.score>=76?'#ff5c5c':(d.score>=66?'#fbbf24':(d.score>=55?'#58a6ff':'#5f6b7d'));
  const dims = [[d.T,'#58a6ff','趋势'],[d.M,'#a371f7','动能'],[d.V,'#4ade80','量能'],[d.F,'#fbbf24','基本面']]
    .map(x=>'<i style="height:'+Math.max(3,x[0]/100*26)+'px;background:'+x[1]+'" title="'+x[2]+' '+x[0]+'"></i>').join('');
  $('vhead').innerHTML =
    '<div class="vscore" style="color:'+col+'">'+d.score.toFixed(1)+'</div>'+
    '<div><div class="vdims">'+dims+'</div>'+
    '<div style="font-size:10px;color:#4d5766;margin-top:3px">趋势/动能/量能/基本面</div></div>'+
    '<div class="vtxt">买点 <b style="color:#4ade80">'+d.buy_cnt+'</b>/7　卖点 <b style="color:'+(d.sell_cnt?'#ff5c5c':'#5f6b7d')+'">'+d.sell_cnt+'</b><br>'+
    '距年内高点 '+d.from_high+'%　年内位置 '+d.pos+'%</div>';

  $('adv').innerHTML = (d.advice||[]).map(a=>'<div>→ '+a+'</div>').join('');
  $('sig').innerHTML = (d.tags||[]).map(t=>'<span class="tag t-'+(t[1]==='good'?'good':t[1]==='bad'?'bad':t[1]==='warn'?'warn':'info')+
    '" data-tip="'+(t[2]||'').replace(/"/g,'&quot;')+'">'+t[0]+'</span>').join('');
  $('levels').innerHTML = [
    ['MA5 短线',d.ma[0],'5日平均成本。跌破它说明最近一周买的人都在亏。'],
    ['MA10',d.ma[1],'10日平均成本，短线强弱分界。'],
    ['MA20',d.ma[2],'20日平均成本，一个月的趋势中枢。'],
    ['MA60 生命线',d.ma[3],'60日平均成本，中期趋势的分水岭。']
  ].map(x=>'<div data-tip="'+x[2]+'"><i>'+x[0]+'</i><b>'+fmt(x[1])+'</b></div>').join('');

  const b=d.basic;
  $('basic').innerHTML = [
    ['市盈率 PE', b.PE, '你花多少钱买1块钱年利润。负数=亏损。'],
    ['市净率 PB', b.PB, '股价÷每股净资产。低于1叫破净。'],
    ['ROE', b.ROE==null?'-':b.ROE+'%', '净资产收益率。10%-30%算健康。'],
    ['总市值', b['总市值']?b['总市值']+'亿':'-', '公司总价值。小于30亿算小盘。'],
    ['每股收益', b['每股收益'], '每一股对应的年利润。'],
    ['每股净资产', b['每股净资产'], '每一股对应的账面净资产。'],
    ['换手率', b['换手率']+'%', '当天有多少比例的流通股换了主人。'],
    ['年内位置', b['年内位置']+'%', '现价在过去一年区间里的分位。']
  ].map(x=>'<div data-tip="'+x[2]+'"><i>'+x[0]+'</i><b>'+fmt(x[1])+'</b></div>').join('');

  const f = d.fund||[];
  if(f.length){
    const mx = Math.max(...f.map(x=>Math.abs(x.net)),0.01);
    $('fund').innerHTML = f.slice(0,10).map(x=>{
      const w = Math.abs(x.net)/mx*48, c2 = x.net>=0?'#ff5c5c':'#4ade80';
      const left = x.net>=0?50:50-w;
      return '<div class="frow"><span class="dt">'+x.date+'</span>'+
        '<span class="fbar"><i style="left:'+left+'%;width:'+w+'%;background:'+c2+'"></i><b></b></span>'+
        '<span class="fval" style="color:'+c2+'">'+(x.net>0?'+':'')+x.net.toFixed(2)+'亿</span></div>';
    }).join('');
    const s5 = f.slice(0,5).reduce((a,x)=>a+x.net,0);
    $('fundsum').innerHTML = '近5日累计 <b style="color:'+(s5>=0?'#ff5c5c':'#4ade80')+'">'+
      (s5>0?'+':'')+s5.toFixed(2)+' 亿</b>';
  } else {
    $('fund').innerHTML='<div style="color:#5f6b7d;font-size:13px">暂无资金流数据</div>';
    $('fundsum').innerHTML='';
  }
  requestAnimationFrame(()=>draw(d));
}

function openCompany(i){
  if(i<0) return;
  const d = DATA[i], co = d.company || {};
  const pr = co.profile || {}, fin = co.finance || {}, news = co.news || [];
  $('detail').style.display='none';
  $('page0').style.display='none'; $('page1').style.display='none';
  $('company').style.display='block';
  window.scrollTo(0,0);

  $('coHead').innerHTML = d.name + '<span>' + d.code + ' · ' + (pr['公司名称']||d.name) + '</span>';

  let h = '';

  // 概况
  const fields = [['所属行业','所属行业'],['上市日期','上市日期'],['注册资本','注册资本'],
                  ['注册地址','注册地址'],['公司网址','公司网址']];
  const kv = fields.map(f=>{
    const v = pr[f[1]];
    return v ? '<div><i>'+f[0]+'</i><b>'+v+'</b></div>' : '';
  }).join('');
  h += '<div class="box"><h4>公司基本情况</h4><div class="kv">'+kv+'</div>';
  if(pr['主营业务']) h += '<div class="biz" style="margin-top:12px"><b>主营业务：</b>'+pr['主营业务']+'</div>';
  if(pr['公司简介']) h += '<div class="biz"><b>公司简介：</b>'+pr['公司简介']+'</div>';
  h += '</div>';

  // 财务
  const periods = fin.periods || [];
  const rows = fin.rows || {};
  const order = ['营业总收入(亿)','净利润(亿)','每股收益','每股净资产','净资产收益率','资产负债率','销售毛利率'];
  const keys = order.filter(k=>rows[k]).concat(Object.keys(rows).filter(k=>order.indexOf(k)<0));
  if(keys.length && periods.length){
    let th = '<tr><th>指标</th>' + periods.map(p=>'<th>'+p+'</th>').join('') + '</tr>';
    let tb = keys.map(k=>'<tr><td>'+k+'</td>' + periods.map((_,j)=>{
      const v = (rows[k]||[])[j];
      return '<td>'+(v==null?'-':(Math.abs(v)>=1000? v.toFixed(0): v.toFixed(2)))+'</td>';
    }).join('') + '</tr>').join('');
    h += '<div class="box"><h4>财务 & 盈利情况</h4><table class="fin-t"><thead>'+th+'</thead><tbody>'+tb+'</tbody></table>'+
         '<div style="font-size:11px;color:#4d5766;margin-top:8px">数据来源：新浪财经季报，单位见指标名；标「亿」的已换算为亿元。</div></div>';
  } else {
    h += '<div class="box"><h4>财务 & 盈利情况</h4><div style="color:#5f6b7d;font-size:13px">暂无财务数据</div></div>';
  }

  // 新闻
  if(news.length){
    h += '<div class="box"><h4>重要新闻</h4><div class="news">' + news.map(n=>
      '<a href="'+n.url+'" target="_blank" rel="noopener">'+n.title+
      '<span>'+n.date+' '+n.time+'</span></a>').join('') + '</div></div>';
  } else {
    h += '<div class="box"><h4>重要新闻</h4><div style="color:#5f6b7d;font-size:13px">暂无新闻</div></div>';
  }

  h += '<div style="font-size:11.5px;color:#4d5766;margin-top:14px;line-height:1.8">'+
       '资料来自新浪财经公开数据，仅供参考，不构成投资建议。新闻标题可点击查看原文。</div>';

  $('coBody').innerHTML = h;
}

function backToDetail(){
  $('company').style.display='none';
  $('detail').style.display='block';
  window.scrollTo(0,0);
}

function back(){
  $('company').style.display='none';
  $('detail').style.display='none';
  switchTab(curTab);
  setTimeout(()=>window.scrollTo(0,_sY),0);
}

/* ---------- 保存清单 ---------- */
function download(name, text){
  const blob = new Blob(['\ufeff'+text], {type:'text/plain;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(a.href), 4000);
}
function buildWatchlist(){
  const p = new Set(getPicks());
  const pos = DATA.filter(d=>p.has(d.code));
  const watch = DATA.filter(d=>!p.has(d.code));
  let s = '# 自选股清单（由面板生成）\n# 勾选=持仓，未勾选=关注\n\n';
  const group = (list, type)=>{
    const themes = [...new Set(list.map(d=>d.theme||'未分类'))];
    themes.forEach(t=>{
      const arr = list.filter(d=>(d.theme||'未分类')===t);
      s += '['+type+'|'+t+'|'+(arr[0].priority||'中')+']\n';
      arr.forEach(d=>{
        const h = type==='持仓' ? effHold(d) : null;
        s += h ? (d.code+' '+h.cost.toFixed(2)+' '+h.shares) : d.code;
        s += '\n';
      });
      s += '\n';
    });
  };
  if(pos.length) group(pos,'持仓');
  if(watch.length) group(watch,'关注');
  return s;
}
function saveList(){
  const p = getPicks();
  applyHold();
  toast('已保存到本机：持仓 '+p.length+' 只 / 关注 '+(DATA.length-p.length)+' 只，刷新不会丢');
}
function exportList(){
  download('watchlist.txt', buildWatchlist());
  toast('已导出 watchlist.txt（换电脑时用它）');
}

/* ---------- K线绘制 ---------- */
function draw(d){
  const cv=$('chart'); if(!cv) return;
  const dpr=window.devicePixelRatio||1;
  const W=cv.clientWidth, H=350;
  cv.width=W*dpr; cv.height=H*dpr;
  const g=cv.getContext('2d'); g.setTransform(dpr,0,0,dpr,0,0); g.clearRect(0,0,W,H);
  const k=d.k; if(!k||!k.length) return;
  const n=k.length, padR=44, padT=8;
  const hK=170, hV=54, hM=74, gap=11;
  const topK=padT, topV=padT+hK+gap, topM=topV+hV+gap;
  const plotW=W-padR, w=plotW/n;
  let pmin=1e18,pmax=-1e18;
  k.forEach(r=>{pmin=Math.min(pmin,r[3]);pmax=Math.max(pmax,r[4]);});
  for(let c=6;c<=9;c++) k.forEach(r=>{if(r[c]>0){pmin=Math.min(pmin,r[c]);pmax=Math.max(pmax,r[c]);}});
  const pd=(pmax-pmin)*0.06; pmin-=pd; pmax+=pd;
  const yP=v=>topK+(pmax-v)/(pmax-pmin)*hK;
  g.strokeStyle='#1b2027'; g.lineWidth=1; g.fillStyle='#4d5766';
  g.font='10px ui-monospace,monospace'; g.textAlign='left';
  for(let i=0;i<=4;i++){
    const y=topK+hK*i/4;
    g.beginPath(); g.moveTo(0,y); g.lineTo(plotW,y); g.stroke();
    g.fillText((pmax-(pmax-pmin)*i/4).toFixed(2), plotW+6, y+3);
  }
  const bw=Math.max(1,w*0.62);
  k.forEach((r,i)=>{
    const o=r[1],c=r[2],l=r[3],h=r[4], x=i*w+w/2, up=c>=o;
    const col=up?'#ff5c5c':'#4ade80';
    g.strokeStyle=col; g.fillStyle=col; g.lineWidth=1;
    g.beginPath(); g.moveTo(x,yP(h)); g.lineTo(x,yP(l)); g.stroke();
    const y1=yP(Math.max(o,c)), y2=yP(Math.min(o,c));
    g.fillRect(x-bw/2, y1, bw, Math.max(1,y2-y1));
  });
  const mc=['#f0b90b','#58a6ff','#a371f7','#3fb950'];
  [6,7,8,9].forEach((ci,ii)=>{
    g.strokeStyle=mc[ii]; g.lineWidth=1.2; g.beginPath();
    let st=false;
    k.forEach((r,i)=>{const v=r[ci]; if(!v||v<=0)return; const x=i*w+w/2,y=yP(v);
      if(!st){g.moveTo(x,y);st=true;}else g.lineTo(x,y);});
    g.stroke();
  });
  let vmax=0.01; k.forEach(r=>vmax=Math.max(vmax,r[5]));
  k.forEach((r,i)=>{
    const x=i*w+w/2, hh=r[5]/vmax*hV;
    g.fillStyle=r[2]>=r[1]?'rgba(255,92,92,.55)':'rgba(74,222,128,.55)';
    g.fillRect(x-bw/2, topV+hV-hh, bw, hh);
  });
  g.fillStyle='#4d5766'; g.fillText('成交量',2,topV+10);
  let mmax=0.01; k.forEach(r=>{mmax=Math.max(mmax,Math.abs(r[10]),Math.abs(r[11]),Math.abs(r[12]));});
  const y0=topM+hM/2;
  g.strokeStyle='#1b2027'; g.beginPath(); g.moveTo(0,y0); g.lineTo(plotW,y0); g.stroke();
  k.forEach((r,i)=>{
    const v=r[12], hh=Math.abs(v)/mmax*(hM/2-2);
    g.fillStyle=v>=0?'rgba(255,92,92,.7)':'rgba(74,222,128,.7)';
    g.fillRect(i*w+w*0.2, v>=0?y0-hh:y0, Math.max(1,w*0.6), hh);
  });
  [[10,'#f0b90b'],[11,'#58a6ff']].forEach(([ci,cc])=>{
    g.strokeStyle=cc; g.lineWidth=1.2; g.beginPath();
    let st=false;
    k.forEach((r,i)=>{const v=r[ci], y=y0-(v/mmax)*(hM/2-2), x=i*w+w/2;
      if(!st){g.moveTo(x,y);st=true;}else g.lineTo(x,y);});
    g.stroke();
  });
  g.fillStyle='#4d5766'; g.fillText('MACD',2,topM+10);
  g.fillText(k[0][0].slice(5),1,H-3);
  g.textAlign='right'; g.fillText(k[n-1][0].slice(5),plotW,H-3);

  const tt=$('tip');
  cv.onmousemove=e=>{
    const rc=cv.getBoundingClientRect();
    let i=Math.floor((e.clientX-rc.left)/w); i=Math.max(0,Math.min(n-1,i));
    const r=k[i];
    tt.style.display='block';
    tt.style.left=Math.min(e.clientX+16,window.innerWidth-290)+'px';
    tt.style.top=(e.clientY+16)+'px';
    tt.innerHTML='<b>'+r[0]+'</b>开 '+fmt(r[1])+'　收 '+fmt(r[2])+'<br>高 '+fmt(r[4])+'　低 '+fmt(r[3])+
      '<br>量 '+fmt(r[5],1)+'万手<br>MA5 '+fmt(r[6])+'　MA10 '+fmt(r[7]);
  };
  cv.onmouseleave=()=>{tt.style.display='none';};
}

/* ---------- tooltip ---------- */
(function(){
  const el=$('tip');
  function show(t,x,y){
    if(!t) return;
    el.innerHTML='<b>'+t.split('|')[0]+'</b>'+(t.split('|')[1]||t);
    el.style.display='block';
    let L=x+14,T=y+14;
    if(L+el.offsetWidth>window.innerWidth-10) L=x-el.offsetWidth-14;
    if(T+el.offsetHeight>window.innerHeight-10) T=y-el.offsetHeight-14;
    el.style.left=Math.max(8,L)+'px'; el.style.top=Math.max(8,T)+'px';
  }
  function hide(){el.style.display='none';}
  document.addEventListener('mouseover',e=>{
    const t=e.target.closest?e.target.closest('[data-tip]'):null;
    if(t&&t.dataset.tip) show(t.dataset.tip,e.clientX,e.clientY);
  });
  document.addEventListener('mousemove',e=>{
    if(el.style.display==='block'){
      const t=e.target.closest?e.target.closest('[data-tip]'):null;
      if(t&&t.dataset.tip){
        const L=Math.min(e.clientX+14,window.innerWidth-el.offsetWidth-14);
        el.style.left=Math.max(8,L)+'px'; el.style.top=Math.max(8,e.clientY+14)+'px';
      }
    }
  });
  document.addEventListener('mouseout',e=>{
    const t=e.target.closest?e.target.closest('[data-tip]'):null;
    if(t) hide();
  });
  document.addEventListener('touchstart',e=>{
    const t=e.target.closest?e.target.closest('[data-tip]'):null;
    if(t&&t.dataset.tip){
      const b=e.touches[0]; show(t.dataset.tip,b.clientX,b.clientY);
      setTimeout(hide,3200);
    }
  },{passive:true});
})();

/* 立即执行一次（脚本在 body 末尾，此时 DOM 已就绪）；再挂 DOMContentLoaded 兜底 */
try { applyPicks(); } catch(e) { console.warn('init failed', e); }
if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded', ()=>{
    try { applyPicks(); } catch(e) { console.warn('init failed', e); }
  });
}
"""


def _tag_html(tags):
    out = []
    for t, c in tags:
        tip = tip_of(t).replace('"', "&quot;")
        out.append(f'<span class="tag t-{c}" data-tip="{tip}">{t.replace(chr(34), "&quot;")}</span>')
    return "".join(out)


def fmt_num(v):
    if v is None:
        return "-"
    try:
        return f"{float(v):.1f}"
    except Exception:
        return "-"


def _with_tips(stocks):
    out = []
    for s in stocks:
        s2 = dict(s)
        s2["tags"] = [[t, c, tip_of(t)] for t, c in s["tags"]]
        out.append(s2)
    return out


def render_app_html(stocks, data_time="", days=120) -> str:
    n_d = sum(1 for s in stocks if s["status"] == "danger")
    n_g = sum(1 for s in stocks if s["status"] == "go")
    n_w = sum(1 for s in stocks if s["status"] == "wait")

    # ---------- 卡片（按 type 预分组，JS 只做勾选后的重排）
    cards_pos, cards_watch = [], []
    cards = []
    for i, s in enumerate(stocks):
        cls = s["status"]
        sc = {"danger": "d", "go": "g", "wait": "w"}[cls]
        cc = "up" if s["chg"] > 0 else ("dn" if s["chg"] < 0 else "fl")
        tcls = "grp-pos" if s.get("type") == "持仓" else "grp-watch"
        pcls = {"高": "pri-h", "中": "pri-m"}.get(s.get("priority", "中"), "pri-l")
        cards.append(f"""<div class="card {cls}" data-fitem="1" data-code="{s['code']}"
  data-type="{s.get('type','关注')}" data-theme="{s.get('theme','未分类')}"
  data-pri="{s.get('priority','中')}" data-score="{s['score']}" onclick="openDetail({i})">
  <div class="l1">
    <input type="checkbox" class="chk" data-code="{s['code']}" onclick="event.stopPropagation()" onchange="togglePick(this)">
    <div class="nm">{s['name']}<span class="c">{s['code']}</span>
      <span class="grp {tcls}">{s.get('type','关注')}</span>
      <span class="grp {pcls}">{s.get('theme','未分类')}·{s.get('priority','中')}</span></div>
    <div class="st {sc}">{s['status_text']}</div>
  </div>
  <div class="l2"><div><b class="{cc}">{s['price']:.2f}</b>
    <span class="{cc}">{s['chg']:+.2f}%</span></div>
    <div data-tip="离过去一年最高价还差多少。">距年内高点 {s['from_high']}% ›</div></div>
</div>""")
        (cards_pos if s.get("type") == "持仓" else cards_watch).append(cards[-1])

    # ---------- 表格行
    rows, rows_pos, rows_watch = [], [], []
    for i, s in enumerate(stocks):
        cc = "up" if s["chg"] > 0 else ("dn" if s["chg"] < 0 else "fl")
        dims = "".join(
            f'<i style="height:{max(3,int(v/100*20))}px;background:{c}"></i>'
            for v, c in ((s["T"], "#58a6ff"), (s["M"], "#a371f7"),
                         (s["V"], "#4ade80"), (s["F"], "#fbbf24")))
        pc = "#ff5c5c" if s["score"] >= 76 else ("#fbbf24" if s["score"] >= 66 else
                                                 ("#58a6ff" if s["score"] >= 55 else "#5f6b7d"))
        roe = s["basic"]["ROE"]
        pe = s["basic"]["PE"]
        roe = s["basic"]["ROE"]
        pe = s["basic"]["PE"]
        pnl, pct = s.get("pnl"), s.get("pnl_pct")
        if pnl is None:
            pnl_html = '<span style="color:#3d4450">—</span>'
        else:
            pc2 = "#ff5c5c" if pnl > 0 else ("#4ade80" if pnl < 0 else "#7c8798")
            pnl_html = (f'<b style="color:{pc2};font-family:ui-monospace,monospace">{pnl:+,.0f}</b>'
                        f'<div style="font-size:10.5px;color:{pc2}">{pct:+.2f}%</div>')
        costline = ""
        if s.get("cost") and s.get("shares"):
            costline = f" · 成本{s['cost']:.2f}×{int(s['shares'])}股"
        rows.append(f"""<tr data-fitem="1" data-code="{s['code']}"
  data-theme="{s.get('theme','未分类')}" data-type="{s.get('type','关注')}"
  data-score="{s['score']}" data-buy="{s['buy_cnt']}" data-sell="{s['sell_cnt']}"
  data-roe="{roe if roe is not None else -999}" data-pe="{pe if pe else -999}"
  data-vr="{s['vratio']}" data-chg="{s['chg']}" data-price="{s['price']}"
  data-pnl="{pnl if pnl is not None else -999999}"
  onclick="openDetail({i})">
  <td onclick="event.stopPropagation()"><input type="checkbox" class="chk" data-code="{s['code']}" onchange="togglePick(this)"></td>
  <td><div class="tname">{s['name']}</div><div class="tcode">{s['code']} · {s.get('theme','')}<span class="costline" title="点击填写成本价和股数" onclick="event.stopPropagation();editHold('{s['code']}')">{costline}</span></div></td>
  <td style="font-family:ui-monospace,monospace">{s['price']:.2f}</td>
  <td class="{cc}" style="font-family:ui-monospace,monospace">{s['chg']:+.2f}%</td>
  <td class="pnlcell">{pnl_html}</td>
  <td><span class="scorec" style="color:{pc}">{s['score']:.1f}</span></td>
  <td><span class="badge bg-{'abcd'[['重点跟踪','可关注','观察','回避'].index(s['grade'])]}">{s['grade']}</span></td>
  <td><div class="dims" data-tip="四维|从左到右：趋势、动能、量能、基本面。每项满分100，50是中性。">{dims}</div></td>
  <td data-tip="买点|命中几个买入信号（共7项）。≥2项共振才算时机。">
    <b style="color:#4ade80">{s['buy_cnt']}</b>/7</td>
  <td data-tip="卖点|命中几个卖出信号（共5项）。≥1就该处理。">
    <b style="color:{'#ff5c5c' if s['sell_cnt'] else '#5f6b7d'}">{s['sell_cnt']}</b></td>
  <td style="max-width:250px;white-space:normal">{_tag_html(s['tags'][:4])}</td>
  <td style="font-family:ui-monospace,monospace;color:#7c8798">{roe if roe is not None else '-'}</td>
  <td style="font-family:ui-monospace,monospace;color:#7c8798">{fmt_num(pe)}</td>
  <td style="font-family:ui-monospace,monospace;color:#7c8798">{s['vratio']}</td>
</tr>""")
        (rows_pos if s.get("type") == "持仓" else rows_watch).append(rows[-1])

    # ---------- 表头（可排序）
    def th(label, key=None, tip=None):
        t = f' data-tip="{tip}"' if tip else ""
        if key:
            return f'<th class="sortable" data-key="{key}"{t} onclick="sortBy(\'{key}\')">{label}</th>'
        return f'<th{t}>{label}</th>'

    head = ('<th style="width:36px">持仓</th>' + th("标的")
            + th("现价", "Price") + th("涨跌", "Chg")
            + th("浮盈", "Pnl", "持仓浮盈 =（现价 − 成本）× 股数。没填成本就显示 —")
            + th("评分", "Score", HEAD_TIPS["评分"])
            + th("档位", None, HEAD_TIPS["档位"]) + th("四维", None, HEAD_TIPS["四维"])
            + th("买点", "Buy", HEAD_TIPS["买点"]) + th("卖点", "Sell", HEAD_TIPS["卖点"])
            + th("信号") + th("ROE", "Roe", HEAD_TIPS["ROE"])
            + th("PE", "Pe", HEAD_TIPS["PE"]) + th("量比", "Vr", HEAD_TIPS["量比"]))

    # ---------- 题材筛选
    from collections import Counter
    themes = Counter(s.get("theme", "未分类") for s in stocks)
    fparts = ['<button class="on" onclick="setTheme(this,\'__all__\')">全部题材</button>']
    for t, c in themes.most_common():
        fparts.append(f'<button onclick="setTheme(this,\'{t}\')">{t} {c}</button>')
    filters = '<div class="filters">' + "".join(fparts) + "</div>"

    # ---------- 买点/卖点说明
    buy_lis = "".join(f"<li><b>{n}</b> — {d}</li>" for n, d in BUY_LIST)
    sell_lis = "".join(f"<li><b>{n}</b> — {d}</li>" for n, d in SELL_LIST)
    explain = f"""<details class="explain">
  <summary>买点、卖点是什么意思？（点开看完整清单）</summary>
  <div class="ex-body">
    <div><h5>买点 · 7 项（命中几项就是「买点 n/7」）</h5><ol>{buy_lis}</ol></div>
    <div><h5>卖点 · 5 项（命中几项就是「卖点 n」）</h5><ol>{sell_lis}</ol></div>
  </div>
  <div class="rule">
    <b>怎么用：</b>书里那句话是关键——<em>单一指标只用来验证想法，多个指标同时出现（共振）才是真正的时机</em>。<br>
    所以：买点 <b>≥2 且卖点 =0</b> → 才算「时机到了」，可以小仓试；<br>
    　　　买点 0~1 → 只是「有点苗头」，继续等；<br>
    　　　卖点 <b>≥1</b> → 无论买点多少，先处理风险。
  </div>
</details>"""

    js = JS.replace("__DATA__", json.dumps(_with_tips(stocks), ensure_ascii=False))

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>今天怎么办</title><style>{CSS}</style></head><body>

<div class="top">
  <div class="title">自选股 · 盯盘<em>{data_time}　共 {len(stocks)} 只</em></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <button class="savebtn" onclick="saveList()">保存持仓</button>
    <button class="savebtn" style="background:#21262d;border-color:#30363d;color:#8b949e" onclick="exportList()" title="换电脑时才需要用">导出</button>
    <div class="tabs">
      <button class="on" onclick="switchTab(0)">今天怎么办</button>
      <button onclick="switchTab(1)">盯盘面板</button>
    </div>
  </div>
</div>

<div id="page0">
  {filters}
  <div class="stat2" id="stat2">
    <div class="s2"><i>持仓市值</i><b id="stMv">—</b></div>
    <div class="s2"><i>浮动盈亏</i><b id="stPnl">—</b></div>
    <div class="s2"><i>今日盈亏</i><b id="stDay">—</b></div>
    <div class="s2"><i>持仓只数</i><b id="stN">0</b></div>
  </div>
  <div id="structBox" class="box" style="margin-top:10px;display:none">
    <h4>持仓结构（按题材 · 市值占比）</h4>
    <div id="structBars"></div>
  </div>
  <div id="checkBox" class="box" style="margin-top:10px;display:none">
    <h4>持仓体检</h4>
    <div id="checkList"></div>
  </div>
  <div class="sum">
    <div data-tip="有卖出信号：跌破关键均线或出现顶背离，按纪律该减。"><b class="k-d">{n_d}</b><i>只要先处理 <span id="sumScope" style="font-size:10px">（全部）</span></i></div>
    <div data-tip="买点共振≥2项且没有卖出信号，可以小仓试错。"><b class="k-g">{n_g}</b><i>只可以试试</i></div>
    <div data-tip="趋势没坏但没到买点，继续等信号。"><b class="k-w">{n_w}</b><i>只继续等</i></div>
  </div>

  <div id="posGroup">
    <div class="gtitle pos">我的持仓 <b id="posCnt">{len(cards_pos)}</b></div>
    <div id="posCards">{''.join(cards_pos)}</div>
  </div>
  <div class="gtitle">关注的股票 <b id="watchCnt">{len(cards_watch)}</b></div>
  <div id="watchCards">{''.join(cards_watch)}</div>

  <div style="margin-top:16px;padding:12px 14px;background:#171a21;border:1px dashed #2a303c;border-radius:11px;
  font-size:12.5px;color:#7c8798;line-height:1.8">
    勾选 = 持仓股，立即移到上面「我的持仓」，<b style="color:#58a6ff">不用点保存、不用下载</b>。<br>
    切到「盯盘面板」表格，点股票名下面的 <b style="color:#58a6ff">成本</b> 两个字，填买入价和股数，盈亏立刻算出来。<br>
    这些设置存在你这台浏览器里，刷新、关电脑再开都还在。换电脑时才点右上角「导出」。
  </div>
</div>

<div id="page1" style="display:none">
  {filters}
  {explain}
  <details class="explain" style="margin-top:10px">
    <summary>按范围筛选（评分、买点、PE、ROE…）</summary>
    <div style="padding:0 15px 15px;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">
      <label style="font-size:12.5px;color:#7c8798">评分 ≥<br><input type="number" id="fScore" placeholder="如 60" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">买点 ≥<br><input type="number" id="fBuy" placeholder="如 2" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">卖点 ≤<br><input type="number" id="fSell" placeholder="如 0" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">PE 下限<br><input type="number" id="fPeMin" placeholder="如 10" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">PE 上限<br><input type="number" id="fPeMax" placeholder="如 50" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">ROE ≥<br><input type="number" id="fRoe" placeholder="如 10" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">量比 ≥<br><input type="number" id="fVr" placeholder="如 1" oninput="applyFilter()" style="width:100%;margin-top:4px;background:#12161d;border:1px solid #2a303c;color:#e8eaed;border-radius:7px;padding:6px 9px;font-family:inherit"></label>
      <label style="font-size:12.5px;color:#7c8798">&nbsp;<br><button onclick="resetFilter()" style="width:100%;margin-top:4px;background:#232833;border:1px solid #3a4150;color:#c8d0da;border-radius:7px;padding:7px;cursor:pointer;font-family:inherit">重置</button></label>
    </div>
  </details>
  <div class="gtitle pos">我的持仓 <b id="posCnt2">{len(rows_pos)}</b></div>
  <div class="tw" id="posWrap">
    <table><thead><tr>{head}</tr></thead><tbody id="posBody">{''.join(rows_pos)}</tbody></table>
  </div>
  <div class="gtitle">关注的股票 <b id="watchCnt2">{len(rows_watch)}</b></div>
  <div class="tw">
    <table><thead><tr>{head}</tr></thead><tbody id="watchBody">{''.join(rows_watch)}</tbody></table>
  </div>
  <div style="font-size:11.5px;color:#4d5766;margin-top:8px;padding:0 4px">
    点表头可以排序（评分/涨跌/买点/卖点/ROE/PE/量比）　·　点任意一行进入详情
  </div>
</div>

<div id="detail">
  <div class="bar"><button class="back" onclick="back()">← 返回</button>
    <button class="cobtn" onclick="openCompany(curStock)">公司详情介绍 ›</button></div>
  <div class="dh" id="dh"></div>
  <div class="dp" id="dp"></div>

  <div class="box" style="margin-top:14px">
    <h4>综合判断</h4>
    <div class="vhead" id="vhead"></div>
    <div class="adv" id="adv"></div>
    <div id="sig" style="margin-top:8px"></div>
    <div style="margin-top:12px"><h4 style="margin-bottom:8px">关键价位</h4><div class="grid4" id="levels"></div></div>
  </div>

  <div class="box">
    <h4>股价走势（近 {days} 个交易日）</h4>
    <canvas id="chart"></canvas>
    <div class="legend">
      <span><i style="background:#f0b90b"></i>MA5</span>
      <span><i style="background:#58a6ff"></i>MA10</span>
      <span><i style="background:#a371f7"></i>MA20</span>
      <span><i style="background:#3fb950"></i>MA60</span>
      <span style="color:#4d5766">鼠标移到图上可看当天数据</span>
    </div>
  </div>

  <div class="box"><h4>基本面</h4><div class="grid4" id="basic"></div></div>
  <div class="box"><h4>资金流（近 10 日 · 红入绿出）</h4><div id="fund"></div>
    <div style="margin-top:9px;font-size:12.5px;color:#7c8798" id="fundsum"></div></div>
</div>

<div id="company">
  <div class="bar"><button class="back" onclick="backToDetail()">← 返回个股</button></div>
  <div class="co-h" id="coHead"></div>
  <div id="coBody"></div>
</div>

<div id="tip"></div>
<script>{js}</script>
</body></html>"""
