#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stock_scout.py — A股选股盯盘小工具
=====================================
把《半小时漫画股票实战》的指标规则 + 《实操-风大》的买卖纪律，
做成一套可执行的扫描器。

用法：
  python3 stock_scout.py                      # 全市场扫描，选出今日候选
  python3 stock_scout.py --code 600000        # 单只股票体检（含分时卖点）
  python3 stock_scout.py --codes 600000,000001 --watch 60   # 盯盘，60秒刷新
  python3 stock_scout.py --full               # 不做粗筛，全量算技术面（慢）
  python3 stock_scout.py --top 40             # 报告里展示前40只

数据源：新浪财经公开行情接口（免费、免key、免登录）
风险提示：这是"规则执行器"，不是投资建议。指标只是概率，纪律才是命。
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import numpy as np
import pandas as pd
import requests

import indicators as ind

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn",
}

SINA_LIST = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
SINA_KLINE = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
SINA_MIN = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
WATCHLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.txt")

INDEXES = [("sh000001", "上证指数"), ("sz399001", "深证成指"),
           ("sz399006", "创业板指"), ("sh000688", "科创50")]


def load_watchlist():
    """
    读 watchlist.txt，支持分组：
        [持仓]                  → 持仓股
        [关注|AI算力|高]         → 关注股，题材=AI算力，优先级=高
    返回 [{'code','type','theme','priority'}, ...]
    """
    import re
    if not os.path.exists(WATCHLIST):
        return []
    out, cur = [], {"type": "关注", "theme": "未分类", "priority": "中"}
    for line in open(WATCHLIST, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            parts = [p.strip() for p in line[1:-1].split("|")]
            cur = {
                "type": parts[0] if parts and parts[0] else "关注",
                "theme": parts[1] if len(parts) > 1 and parts[1] else "未分类",
                "priority": parts[2] if len(parts) > 2 and parts[2] else "中",
            }
            continue
        parts = re.split(r"[\s,]+", line)
        c = re.sub(r"^(sh|sz|bj)", "", parts[0], flags=re.I)
        if not re.fullmatch(r"\d{6}", c):
            continue
        cost = shares = None
        try:
            if len(parts) > 1 and parts[1]:
                cost = float(parts[1])
            if len(parts) > 2 and parts[2]:
                shares = float(parts[2])
        except Exception:
            pass
        out.append({"code": c, "cost": cost, "shares": shares, **cur})
    # 去重（保留第一次出现）
    seen, uniq = set(), []
    for x in out:
        if x["code"] in seen:
            continue
        seen.add(x["code"])
        uniq.append(x)
    return uniq


def save_watchlist(codes):
    with open(WATCHLIST, "w", encoding="utf-8") as f:
        f.write("# 自选股盯盘清单：每行一个6位代码，用 python3 stock_scout.py --add 600000 添加\n")
        for c in codes:
            f.write(c + "\n")


def fetch_index():
    """大盘指数条：盯盘先看大盘，个股再强也拧不过大盘。"""
    out = []
    try:
        syms = ",".join(s for s, _ in INDEXES)
        r = requests.get("http://hq.sinajs.cn/list=" + syms, headers=HEADERS, timeout=8)
        r.encoding = "gbk"
        for line, (sym, label) in zip([x for x in r.text.split(";") if "hq_str" in x], INDEXES):
            vals = line.split("=", 1)[1].strip().strip('"').split(",")
            if len(vals) < 6:
                continue
            price, prev = float(vals[3] or 0), float(vals[2] or 0)
            out.append({"name": label, "price": price,
                        "chg": round((price / prev - 1) * 100, 2) if prev else 0})
    except Exception:
        pass
    return out


# ============================================================ 数据层

def _get(url, params=None, retry=2, timeout=12):
    last = None
    for i in range(retry):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                return r.text
        except Exception as e:  # noqa
            last = e
        time.sleep(0.3 * (i + 1))
    return None


def _json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        try:
            return json.loads(text.replace("'", '"'))
        except Exception:
            return None


def fetch_universe(include_bj=False) -> pd.DataFrame:
    """拉全市场快照：价格、涨跌幅、PE、PB、市值、换手、成交额。"""
    rows = []
    for page in range(1, 90):
        txt = _get(SINA_LIST, {"page": page, "num": 100, "sort": "symbol", "asc": 1,
                               "node": "hs_a", "symbol": ""})
        data = _json(txt)
        if not data:
            break
        rows.extend(data)
        if len(data) < 100:
            break
        time.sleep(0.05)

    if not rows:
        raise RuntimeError("行情列表拉取失败，请检查网络")

    df = pd.DataFrame(rows)
    for c in ["trade", "changepercent", "per", "pb", "mktcap", "nmc", "turnoverratio",
              "amount", "volume", "settlement", "open", "high", "low"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df[df["trade"] > 0].copy()                     # 去停牌
    if not include_bj:
        df = df[~df["symbol"].str.startswith("bj")]
    df["board"] = df["code"].map(board_of)
    return df.reset_index(drop=True)


def board_of(code: str) -> str:
    code = str(code)
    if code.startswith(("688", "689")):
        return "科创板"
    if code.startswith(("300", "301")):
        return "创业板"
    if code.startswith(("8", "4", "920")):
        return "北交所"
    return "主板"


def fetch_kline(symbol: str, datalen: int = 320) -> pd.DataFrame:
    txt = _get(SINA_KLINE, {"symbol": symbol, "scale": 240, "ma": "no", "datalen": datalen})
    data = _json(txt)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["day"] = pd.to_datetime(df["day"])
    return df.dropna(subset=["close"]).reset_index(drop=True)


def fetch_min(symbol: str, scale: int = 5, datalen: int = 240) -> pd.DataFrame:
    txt = _get(SINA_MIN, {"symbol": symbol, "scale": scale, "ma": "no", "datalen": datalen})
    data = _json(txt)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["day"] = pd.to_datetime(df["day"])
    return df.dropna(subset=["close"]).reset_index(drop=True)


def fetch_quote(codes) -> dict:
    """批量实时快照（盯盘用）。codes 形如 600000 / 000001"""
    out = {}
    codes = list(codes)
    for i in range(0, len(codes), 50):
        batch = codes[i:i + 50]
        symbols = ",".join(prefix_of(c) + c for c in batch)
        try:
            r = requests.get("http://hq.sinajs.cn/list=" + symbols, headers=HEADERS, timeout=10)
            r.encoding = "gbk"
            for line in r.text.split(";"):
                if "=" not in line:
                    continue
                left, right = line.split("=", 1)
                sym = left.split("_")[-1].strip()
                vals = right.strip().strip('"').split(",")
                if len(vals) < 32:
                    continue
                out[sym[2:]] = {
                    "name": vals[0], "open": float(vals[1] or 0), "prev": float(vals[2] or 0),
                    "price": float(vals[3] or 0), "high": float(vals[4] or 0), "low": float(vals[5] or 0),
                    "volume": float(vals[8] or 0), "amount": float(vals[9] or 0),
                    "date": vals[30], "time": vals[31],
                }
        except Exception:
            pass
        time.sleep(0.05)
    return out


def fetch_tencent_quote(codes) -> dict:
    """腾讯快照：补 PE / PB / 市值 / 换手（新浪批量接口没有这些）。"""
    out = {}
    codes = list(codes)
    for c in codes:
        sym = prefix_of(c) + c
        try:
            r = requests.get("https://qt.gtimg.cn/q=" + sym, headers=HEADERS, timeout=8)
            r.encoding = "gbk"
            if "=" not in r.text:
                continue
            vals = r.text.split("=", 1)[1].strip().strip(';').strip('"').split("~")
            if len(vals) < 47:
                continue

            def f(i):
                try:
                    return float(vals[i])
                except Exception:
                    return None

            out[c] = {
                "name": vals[1], "price": f(3), "prev": f(4),
                "chg": f(32), "turnoverratio": f(38), "per": f(39),
                "nmc": f(44), "mktcap": f(45), "pb": f(46), "mktcap_yi": f(45),
            }
        except Exception:
            pass
        time.sleep(0.04)
    return out


def fetch_fund(symbol: str, num: int = 12) -> list:
    """个股资金流：净流入、超大单净额（单位换算成亿元）。"""
    txt = _get("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
               "MoneyFlow.ssl_qsfx_zjlrqs",
               {"page": 1, "num": num, "sort": "opendate", "asc": 0, "daima": symbol})
    data = _json(txt)
    if not data:
        return []
    out = []
    for d in data:
        try:
            out.append({
                "date": str(d["opendate"])[5:],
                "net": round(float(d["netamount"]) / 1e8, 2),
                "main": round(float(d["r0_net"]) / 1e8, 2),
                "pct": round(float(d["changeratio"]) * 100, 2),
            })
        except Exception:
            continue
    return out


def build_payload(codes, days: int = 120, meta=None, with_company=True) -> list:
    """为详情页准备数据：K线+均线+MACD、资金流、基本面。"""
    out = []
    for c in codes:
        sym = prefix_of(c) + c
        df = fetch_kline(sym, 320)
        if df.empty or len(df) < 30:
            continue
        q = fetch_tencent_quote([c]).get(c, {})
        r = analyze(sym, c, q.get("name") or c, q, df)
        if not r.get("ok"):
            continue
        m = ind.macd(df["close"])
        mas = ind.ma_set(df["close"], (5, 10, 20, 60))
        seg = df.iloc[-days:].reset_index(drop=True)
        idx0 = len(df) - len(seg)
        k = []
        for i in range(len(seg)):
            j = idx0 + i
            k.append([
                str(df["day"].iloc[j])[:10],
                round(float(df["open"].iloc[j]), 2),
                round(float(df["close"].iloc[j]), 2),
                round(float(df["low"].iloc[j]), 2),
                round(float(df["high"].iloc[j]), 2),
                round(float(df["volume"].iloc[j]) / 1e6, 1),
                round(float(mas["MA5"].iloc[j]), 2),
                round(float(mas["MA10"].iloc[j]), 2),
                round(float(mas["MA20"].iloc[j]), 2),
                round(float(mas["MA60"].iloc[j]), 2),
                round(float(m["DIF"].iloc[j]), 3),
                round(float(m["DEA"].iloc[j]), 3),
                round(float(m["HIST"].iloc[j]), 3),
            ])
        m0 = (meta or {}).get(c, {})
        cost = _num(m0.get("cost"))
        shs = _num(m0.get("shares"))
        mv = round(r["price"] * shs, 2) if (shs and cost) else None
        pnl = round((r["price"] - cost) * shs, 2) if (shs and cost) else None
        pnl_pct = round((r["price"] / cost - 1) * 100, 2) if (shs and cost) else None
        out.append({
            "code": c, "name": r["name"], "board": r["board"],
            "type": m0.get("type", "关注"), "theme": m0.get("theme", "未分类"),
            "priority": m0.get("priority", "中"),
            "cost": cost, "shares": shs, "mv": mv, "pnl": pnl, "pnl_pct": pnl_pct,
            "day_pnl": (round((r["price"] - (r["price"] / (1 + r["chg"] / 100))) * shs, 2)
                        if (shs and r["chg"] != -100) else None),
            "price": r["price"], "chg": r["chg"],
            "status": ("danger" if r.get("sell_hard", r["sell_cnt"]) > 0 else
                       ("wait" if r.get("sell_soft", 0) > 0 else
                        ("go" if r["buy_cnt"] >= 2 else "wait"))),
            "status_text": ("先减仓" if r.get("sell_hard", r["sell_cnt"]) > 0 else
                            ("别追高" if r.get("sell_soft", 0) > 0 else
                             ("可小试" if r["buy_cnt"] >= 2 else "再等等"))),
            "sell_hard": r.get("sell_hard", r["sell_cnt"]), "sell_soft": r.get("sell_soft", 0),
            "score": r["score"], "tags": r["tags"], "advice": r["advice"],
            "grade": r["grade"], "gcls": r["gcls"],
            "T": r["T"], "M": r["M"], "V": r["V"], "F": r["F"],
            "ma": r["ma"], "pos": r["pos"], "from_high": r.get("from_high", 0),
            "vratio": r["vratio"], "bias5": r["bias5"],
            "basic": {
                "PE": r["pe"], "PB": r["pb"], "ROE": r["roe"],
                "总市值": r["mktcap"], "换手率": r["turnover"],
                "每股收益": (round(r["price"] / r["pe"], 2) if r["pe"] and r["pe"] > 0 else None),
                "每股净资产": (round(r["price"] / r["pb"], 2) if r["pb"] and r["pb"] > 0 else None),
                "年内位置": r["pos"], "距年内高点": r.get("from_high", 0),
            },
            "k": k,
            "fund": fetch_fund(sym, 12),
            "company": (_company(c) if with_company else {}),
            "buy_cnt": r["buy_cnt"], "sell_cnt": r["sell_cnt"],
        })
    return out


def _company(code):
    """公司资料（带当天缓存，失败不影响主流程）。"""
    try:
        from company import fetch_company
        return fetch_company(code)
    except Exception as e:
        print(f"  [公司资料] {code} 获取失败: {str(e)[:50]}")
        return {}


def prefix_of(code: str) -> str:
    code = str(code)
    if code.startswith(("92", "8", "4")):
        return "bj"
    if code.startswith(("5", "6", "9")):
        return "sh"
    return "sz"


# ============================================================ 单票分析

def _num(x):
    """把 None / NaN / 空串 统一成 None，避免分数被脏数据污染。"""
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except Exception:
        return None


def analyze(symbol: str, code: str, name: str, snap: dict, df: pd.DataFrame,
            min_df: pd.DataFrame | None = None) -> dict:
    """核心：把一只股票的日线 + 快照，翻译成一组信号和分数。"""
    if df is None or len(df) < 70:
        return {"ok": False, "code": code, "name": name, "reason": "K线数据不足"}

    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]
    last = -1
    price = float(close.iloc[last])
    prev = float(close.iloc[-2])
    chg = (price / prev - 1) * 100

    m = ind.macd(close)
    k = ind.kdj(high, low, close)
    b = ind.boll(close, 26, 2)
    p = ind.psy(close, 12)
    d = ind.dmi(high, low, close)
    bi = ind.bias(close, 5)
    mas = ind.ma_set(close, (5, 10, 20, 60))
    vf = ind.volume_features(vol)
    div = ind.detect_divergence(close, m["DIF"])

    dif, dea, hist = m["DIF"].iloc[last], m["DEA"].iloc[last], m["HIST"].iloc[last]
    K, D, J = k["K"].iloc[last], k["D"].iloc[last], k["J"].iloc[last]
    mid, up, low_band = b["MID"].iloc[last], b["UP"].iloc[last], b["LOW"].iloc[last]
    width = b["WIDTH"].iloc[last]
    psy_v = float(p.iloc[last])
    pdi, mdi, adx = d["PDI"].iloc[last], d["MDI"].iloc[last], d["ADX"].iloc[last]
    bias5 = float(bi.iloc[last])
    ma5, ma10, ma20, ma60 = [float(mas[f"MA{x}"].iloc[last]) for x in (5, 10, 20, 60)]
    vratio = float(vf["VOL_RATIO"].iloc[last]) if pd.notna(vf["VOL_RATIO"].iloc[last]) else 1.0

    gold = bool(ind.cross_up(m["DIF"], m["DEA"]).iloc[last])
    dead = bool(ind.cross_down(m["DIF"], m["DEA"]).iloc[last])
    kdj_gold = bool(ind.cross_up(k["K"], k["D"]).iloc[last])
    kdj_dead = bool(ind.cross_down(k["K"], k["D"]).iloc[last])
    gold_5d = bool(ind.cross_up(m["DIF"], m["DEA"]).iloc[-5:].any())
    above_zero = dif > 0

    # ---- 量价形态（书 + 风大的核心区分）
    vol_up_price_up = chg > 1.0 and vratio > 1.15
    vol_stall = vratio > 1.7 and chg < 1.0 and chg > -1.0          # 量增价滞 → 出货
    vol_no_price = vratio < 0.75 and chg > 2.0                      # 无量拉升 → 虚涨
    vol_shrink_pull = vratio < 0.9 and -3.0 < chg < 0.5             # 缩量回调 → 健康
    vol_mild = 1.0 <= vratio <= 3.0

    # ---- 均线
    ma_bull = ma5 > ma10 > ma20 and ma20 > float(mas["MA20"].iloc[-6])
    ma5_cross = bool(ind.cross_up(mas["MA5"], mas["MA10"]).iloc[-3:].any())
    above_ma5, above_ma20, above_ma60 = price > ma5, price > ma20, price > ma60
    break_ma10 = price < ma10 and ma5 < ma10

    # ---- BOLL
    boll_above_mid = price > mid
    boll_break_up = price > up
    boll_lower_touch = float(low.tail(3).min()) <= float(low_band) * 0.995 and price > low_band
    w_series = b["WIDTH"].dropna()
    boll_squeeze = len(w_series) > 60 and width <= float(np.percentile(w_series.tail(60), 20))

    # ---- 位置 / 龙回头
    pos = ind.price_position(close, 250)
    lp = ind.limit_pct(code)
    limit_days = df.index[(df["close"].pct_change() * 100) >= lp - 0.3].tolist()
    dragon = False
    if limit_days and (len(df) - 1 - limit_days[-1]) <= 25:
        li = limit_days[-1]
        post_high = df["high"].iloc[li:].max()
        drawdown = (post_high - price) / post_high * 100
        near_ma = min(abs(price / ma10 - 1), abs(price / ma20 - 1)) * 100
        if 6 <= drawdown <= 28 and near_ma <= 3.5 and vratio < 0.85:
            dragon = True

    # ---- 基本面（ROE 用 PB/PE 反推：PB/PE = E/B = ROE，恒等式近似）
    pe = _num(snap.get("per"))
    pb = _num(snap.get("pb"))
    mktcap = _num(snap.get("mktcap_yi"))
    if mktcap is None:
        mktcap = (_num(snap.get("mktcap")) or 0) / 10000.0     # 万元 → 亿
    turnover = _num(snap.get("turnoverratio")) or 0
    roe = (pb / pe * 100) if (pe and pe > 0 and pb and pb > 0) else None
    amount = (_num(snap.get("amount")) or 0) / 1e8

    # ================= 打分（50 为中性基线）
    T = 50.0   # 趋势
    M = 50.0   # 动能
    V = 50.0   # 量能
    F = 50.0   # 基本面
    risk = 0.0
    tags = []          # (文本, 类型) 类型: good / warn / bad / info

    # 趋势
    if ma_bull:
        T += 20; tags.append(("均线多头排列 5>10>20", "good"))
    elif ma5 > ma10:
        T += 8
    else:
        T -= 8
    if above_ma60:
        T += 14; tags.append(("站上60日生命线", "good"))
    else:
        T -= 10; tags.append(("60日线下方", "warn"))
    if ma5_cross:
        T += 14; tags.append(("5日上穿10日", "good"))
    if above_ma5:
        T += 6
    if break_ma10:
        T -= 12; risk += 6; tags.append(("跌破10日线", "bad"))

    # 动能
    if gold and above_zero:
        M += 26; tags.append(("MACD零上金叉", "good"))
    elif gold:
        M += 18; tags.append(("MACD金叉(零下)", "good"))
    elif gold_5d:
        M += 6
    if dead:
        M -= 14; tags.append(("MACD死叉", "bad"))
    if div.get("bottom"):
        M += 18; tags.append(("MACD底背离", "good"))
    if div.get("top"):
        M -= 20; risk += 14; tags.append(("MACD顶背离", "bad"))
    if kdj_gold and K < 30:
        M += 16; tags.append(("KDJ低位金叉", "good"))
    elif kdj_gold:
        M += 8
    if kdj_dead and K > 75:
        M -= 12; tags.append(("KDJ高位死叉", "bad"))
    if 20 < K < 80 and D < 80:
        M += 2
    if psy_v <= 25:
        M += 12; tags.append((f"PSY{psy_v:.0f} 超卖", "good"))
    elif psy_v >= 80:
        M -= 8; tags.append((f"PSY{psy_v:.0f} 超买", "warn"))
    if boll_above_mid:
        M += 6
    if boll_break_up:
        M -= 4; tags.append(("突破布林上轨", "warn"))
    if boll_lower_touch:
        M += 10; tags.append(("回踩布林下轨收回", "good"))
    if pdi < 8 and chg > 0:
        M += 8; tags.append(("DMI超跌反弹", "good"))
    if bias5 < -5:
        M += 8; tags.append((f"5日乖离{bias5:.1f}% 超跌", "good"))
    elif bias5 > 8:
        M -= 8; risk += 6; tags.append((f"5日乖离{bias5:.1f}% 超涨", "warn"))

    # 量能
    if vol_up_price_up:
        V += 24; tags.append((f"放量上涨(量比{vratio:.1f})", "good"))
    if vol_shrink_pull:
        V += 10; tags.append(("缩量回调(健康)", "good"))
    if vol_mild:
        V += 6
    if vol_stall:
        V -= 22; risk += 12; tags.append(("量增价滞(出货嫌疑)", "bad"))
    if vol_no_price:
        V -= 18; risk += 8; tags.append(("无量拉升(虚涨)", "bad"))

    # 基本面
    if roe is not None:
        if 10 <= roe <= 30:
            F += 22; tags.append((f"ROE {roe:.1f}%", "good"))
        elif 6 <= roe < 10:
            F += 8
        elif roe > 40:
            F += 6; tags.append((f"ROE {roe:.1f}% 偏高(查负债)", "warn"))
        elif roe < 4:
            F -= 12; tags.append((f"ROE {roe:.1f}% 偏低", "bad"))
    else:
        F -= 10
    if pe is not None:
        if 0 < pe <= 25:
            F += 14
        elif 25 < pe <= 45:
            F += 6
        elif 45 < pe <= 80:
            F -= 4
        elif pe > 80:
            F -= 10; tags.append((f"PE {pe:.0f} 偏高", "warn"))
        else:
            F -= 16; tags.append(("公司亏损(PE<0)", "bad"))
    if mktcap and mktcap >= 100:
        F += 6
    elif mktcap and mktcap < 30:
        F -= 8; tags.append(("小市值(<30亿)", "warn"))
    if 2 <= turnover <= 15:
        F += 4
    elif turnover > 25:
        F -= 4

    # 位置加成
    if pos < 25:
        T += 8; tags.append((f"处于年内低位({pos:.0f}%分位)", "good"))
    elif pos > 88:
        T -= 6; tags.append((f"处于年内高位({pos:.0f}%分位)", "warn"))

    if dragon:
        M += 16; tags.append(("龙回头形态(涨停后缩量回踩)", "good"))

    T, M, V, F = [max(0, min(100, x)) for x in (T, M, V, F)]
    score = T * 0.32 + M * 0.30 + V * 0.23 + F * 0.15 - risk
    score = round(max(0, min(100, score)), 1)

    # 买点共振计数（书：单一指标只是验证想法，共振才是时机）
    buy_hits = [
        ("MACD金叉", gold or gold_5d),
        ("底背离", bool(div.get("bottom"))),
        ("KDJ低位金叉", kdj_gold and K < 45),
        ("放量上涨", vol_up_price_up),
        ("龙回头", dragon),
        ("回踩下轨", boll_lower_touch),
        ("5日上穿10日", ma5_cross),
    ]
    buy_names = [k for k, v in buy_hits if v]
    buy_cnt = len(buy_names)
    # 卖点分级：hard=真的该减仓；soft=只是别追高，不等于要卖
    sell_hits = [
        ("顶背离", bool(div.get("top")), "hard"),
        ("量增价滞", vol_stall, "hard"),
        ("无量拉升", vol_no_price, "soft"),
        ("跌破10日线", break_ma10, "hard"),
        ("KDJ高位死叉", kdj_dead and K > 75, "hard"),
    ]
    sell_cnt = sum(1 for _, v, _ in sell_hits if v)
    sell_hard = sum(1 for _, v, lv in sell_hits if v and lv == "hard")
    sell_soft = sum(1 for _, v, lv in sell_hits if v and lv == "soft")
    buy_ready = buy_cnt >= 2 and sell_cnt == 0

    if score >= 76:
        grade, gcls = "重点跟踪", "s-a"
    elif score >= 66:
        grade, gcls = "可关注", "s-b"
    elif score >= 55:
        grade, gcls = "观察", "s-c"
    else:
        grade, gcls = "回避", "s-d"

    # 操作建议（严格对应两份材料的规则）
    adv = []
    if div.get("top") or vol_stall:
        adv.append("减仓信号：顶背离/量增价滞 → 越涨越卖，别等破位")
    if vol_no_price:
        adv.append("无量拉升不追；已持有则回落5日线再接回")
    if break_ma10:
        adv.append("已跌破10日线 → 按纪律先减仓，站回再谈")
    if dragon:
        adv.append("龙回头：涨停后缩量回踩支撑，可轻仓试，跌破支撑放弃")
    if sell_cnt == 0 and buy_cnt >= 3:
        adv.append(f"{buy_cnt}项买点共振（{'、'.join(buy_names)}）→ 地摊法首份建仓1/5，止损-5%")
    elif sell_cnt == 0 and buy_cnt == 2:
        adv.append(f"两项买点共振（{'、'.join(buy_names)}）→ 可小仓试，止损-5%")
    elif sell_cnt == 0 and buy_cnt == 1:
        adv.append(f"仅1项信号（{buy_names[0]}），单指标不算时机，等共振")
    if not adv:
        adv.append("信号未共振，等下一个买点，不猜底不追高")

    # ---- 分时（风大卖点）只在单票模式下传入
    min_info = None
    if min_df is not None and len(min_df) > 40:
        mm = ind.macd(min_df["close"])
        mdiv = ind.detect_divergence(min_df["close"], mm["DIF"], lookback=96, order=3, recent=10)
        mgold = bool(ind.cross_up(mm["DIF"], mm["DEA"]).iloc[-2:].any())
        min_info = {
            "top_div": mdiv.get("top", False),
            "bottom_div": mdiv.get("bottom", False),
            "gold": mgold,
            "last": str(min_df["day"].iloc[-1]),
        }
        if mdiv.get("top"):
            tags.append(("分时MACD顶背离(卖点)", "bad"))

    return {
        "ok": True, "code": code, "symbol": symbol, "name": name, "board": board_of(code),
        "price": price, "chg": round(chg, 2), "score": score, "grade": grade, "gcls": gcls,
        "T": round(T), "M": round(M), "V": round(V), "F": round(F),
        "pe": pe, "pb": pb, "roe": (round(roe, 1) if roe is not None else None),
        "mktcap": round(mktcap, 0), "turnover": round(float(turnover), 2), "amount": round(amount, 2),
        "pos": round(pos, 0), "vratio": round(vratio, 2), "bias5": round(bias5, 2),
        "from_high": round((price / float(close.tail(250).max()) - 1) * 100, 1),
        "macd": round(float(hist), 3), "kdj": (round(K, 0), round(D, 0), round(J, 0)),
        "psy": round(psy_v, 0), "pdi": round(float(pdi), 1),
        "ma": (round(ma5, 2), round(ma10, 2), round(ma20, 2), round(ma60, 2)),
        "tags": tags, "advice": adv, "min": min_info, "dragon": dragon,
        "buy_cnt": buy_cnt, "sell_cnt": sell_cnt, "buy_ready": buy_ready,
        "buy_hits": [k for k, v in buy_hits if v], "sell_hits": [k for k, v, _ in sell_hits if v],
        "sell_hard": sell_hard, "sell_soft": sell_soft,
        "last_day": str(df["day"].iloc[-1])[:10],
    }


# ============================================================ 粗筛

def preselect(df: pd.DataFrame, args) -> pd.DataFrame:
    d = df.copy()
    d = d[~d["name"].str.contains("ST|退", na=False)]
    d = d[d["changepercent"].between(args.min_chg, args.max_chg)]
    d = d[d["amount"] >= args.min_amount * 1e8]
    d = d[d["turnoverratio"].between(0.5, 30)]
    d = d[(d["mktcap"] / 10000) >= args.min_cap]
    if not args.allow_loss:
        d = d[d["per"] > 0]
    d = d[d["per"].fillna(999) < args.max_pe]
    if not args.star:
        d = d[~d["board"].isin(["科创板", "北交所"])]
    return d.reset_index(drop=True)


def run_scan(args):
    t0 = time.time()
    print("① 拉取全市场快照 ...", flush=True)
    uni = fetch_universe()
    print(f"   全市场 {len(uni)} 只 → "
          f"{'未粗筛(全量)' if args.full else '按条件粗筛'} ...", flush=True)

    pool = uni if args.full else preselect(uni, args)
    if args.limit:
        # 按成交额优先，保证流动性
        pool = pool.sort_values("amount", ascending=False).head(args.limit)
    print(f"   候选 {len(pool)} 只，开始算技术面 ...", flush=True)

    rows = []
    lock = 0

    def work(r):
        nonlocal lock
        try:
            kd = fetch_kline(r["symbol"], 320)
            lock += 1
            if lock % 50 == 0:
                print(f"   已分析 {lock}/{len(pool)}", flush=True)
            return analyze(r["symbol"], r["code"], r["name"], r.to_dict(), kd)
        except Exception:
            return {"ok": False, "code": r["code"], "name": r["name"], "reason": "抓取失败"}

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, r) for _, r in pool.iterrows()]
        for f in as_completed(futs):
            rows.append(f.result())

    ok = [r for r in rows if r.get("ok")]
    ok.sort(key=lambda x: -x["score"])
    print(f"② 完成：{len(ok)} 只有效，用时 {time.time()-t0:.1f}s", flush=True)
    return ok, uni


# ============================================================ 输出

def print_table(rows, top=30):
    head = f"{'代码':<8}{'名称':<10}{'现价':>8}{'涨幅':>8}{'评分':>7}  {'趋势/动能/量能/基本':<20}{'信号'}"
    print("\n" + "=" * 108)
    print(head)
    print("-" * 108)
    for r in rows[:top]:
        nm = r["name"][:8]
        sig = "、".join(t[0] for t in r["tags"][:4])
        print(f"{r['code']:<8}{nm:<10}{r['price']:>8.2f}{r['chg']:>7.2f}%{r['score']:>7.1f}  "
              f"{r['T']:>3}/{r['M']:>3}/{r['V']:>3}/{r['F']:>3}          {sig}")
    print("=" * 108 + "\n")


def print_card(r):
    print(f"\n{'='*66}\n  {r['name']}  {r['code']}   现价 {r['price']:.2f}  {r['chg']:+.2f}%")
    print(f"  评分 {r['score']}  [{r['grade']}]   趋势{r['T']} 动能{r['M']} 量能{r['V']} 基本面{r['F']}")
    print(f"{'-'*66}")
    print(f"  PE {r['pe']}  PB {r['pb']}  ROE≈{r['roe']}%  市值{r['mktcap']:.0f}亿  换手{r['turnover']}%")
    print(f"  均线 5/10/20/60: {'/'.join(str(x) for x in r['ma'])}")
    print(f"  量比{r['vratio']}  5日乖离{r['bias5']}%  年内位置{r['pos']}%  KDJ {r['kdj']}  PSY{r['psy']}")
    print(f"{'-'*66}")
    for t, cls in r["tags"]:
        mark = {"good": "✔", "warn": "!", "bad": "✘", "info": "·"}.get(cls, "·")
        print(f"  {mark} {t}")
    print(f"{'-'*66}")
    for a in r["advice"]:
        print(f"  → {a}")
    print("=" * 66 + "\n")


def main():
    ap = argparse.ArgumentParser(description="A股选股盯盘小工具")
    ap.add_argument("--code", help="单只股票体检，如 600000")
    ap.add_argument("--codes", help="盯盘股票池，逗号分隔")
    ap.add_argument("--watch", type=int, default=0, help="盯盘刷新秒数，如 60")
    ap.add_argument("--full", action="store_true", help="不做粗筛，全市场算技术面")
    ap.add_argument("--limit", type=int, default=0, help="只看成交额前N只")
    ap.add_argument("--top", type=int, default=30, help="报告展示前N只")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-cap", type=float, default=30, help="最小市值(亿)")
    ap.add_argument("--min-amount", type=float, default=0.8, help="最小成交额(亿)")
    ap.add_argument("--min-chg", type=float, default=-5.0)
    ap.add_argument("--max-chg", type=float, default=8.0)
    ap.add_argument("--max-pe", type=float, default=120)
    ap.add_argument("--allow-loss", action="store_true", help="允许亏损股入选")
    ap.add_argument("--star", action="store_true", help="包含科创板")
    ap.add_argument("--no-html", action="store_true")
    ap.add_argument("--watchlist", action="store_true", help="盯盘 watchlist.txt 里的自选股")
    ap.add_argument("--add", help="添加自选股，逗号分隔，如 --add 600000,000001")
    ap.add_argument("--remove", help="删除自选股，逗号分隔参与 --remove all 清空")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    # ---------- 自选股维护
    if args.add or args.remove:
        wl = load_watchlist()
        codes_now = [x["code"] for x in wl]
        if args.add:
            new_codes = [c.strip() for c in args.add.split(",") if c.strip()]
            codes_now = list(dict.fromkeys(codes_now + new_codes))
            print("已添加：" + " ".join(new_codes))
        if args.remove:
            if args.remove.strip().lower() == "all":
                codes_now = []
            else:
                rm = {c.strip() for c in args.remove.split(",")}
                codes_now = [c for c in codes_now if c not in rm]
                print("已删除：" + " ".join(rm))
        save_watchlist(codes_now)
        print(f"当前自选股 {len(codes_now)} 只：{' '.join(codes_now) if codes_now else '（空）'}")
        print(f"清单文件：{WATCHLIST}")
        return

    # ---------- 单票 / 盯盘
    if args.code or args.codes or args.watchlist:
        if args.watchlist:
            wl_meta = {x["code"]: x for x in load_watchlist()}
            codes = list(wl_meta.keys())
            if not codes:
                print("watchlist.txt 还是空的。先添加：" 
                      "\n  python3 stock_scout.py --add 600795,300059,000543")
                return
        else:
            codes = [c.strip() for c in (args.codes or args.code).split(",") if c.strip()]
        print(f"盯盘 {len(codes)} 只：{' '.join(codes)}")
        round_no = 0
        while True:
            round_no += 1
            quotes = fetch_quote(codes)
            tq = fetch_tencent_quote(codes)
            idxs = fetch_index()
            results = []

            def one(c):
                q = quotes.get(c)
                t = tq.get(c, {})
                sym = prefix_of(c) + c
                kd = fetch_kline(sym, 320)
                mn = fetch_min(sym, 5, 240)
                snap = dict(t) if t else {"per": None, "pb": None}
                name = (q or {}).get("name") or t.get("name") or c
                r = analyze(sym, c, name, snap, kd, mn)
                if r.get("ok") and q and q.get("price"):
                    # 用实时价覆盖（盘中日K最后一根可能滞后）
                    r["price"] = q["price"]
                    if q.get("prev"):
                        r["chg"] = round((q["price"] / q["prev"] - 1) * 100, 2)
                return r

            with ThreadPoolExecutor(max_workers=min(8, len(codes))) as ex:
                results = [f.result() for f in [ex.submit(one, c) for c in codes]]
            results = [r for r in results if r.get("ok")]
            # 盯盘排序：有卖出信号的排前面（保命优先），其次看评分
            results.sort(key=lambda x: (0 if x.get("sell_cnt", 0) > 0 else 1, -x["score"]))

            print(f"\n【盯盘 #{round_no}】{datetime.now():%Y-%m-%d %H:%M:%S}  {len(results)}只")
            if idxs:
                print("  大盘：" + "  ".join(f"{i['name']} {i['price']:.2f} {i['chg']:+.2f}%" for i in idxs))
            for r in results:
                print_card(r)
            if not args.no_html:
                p = os.path.join(OUT_DIR, "watch.html")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(render_watch_html(results, args.watch or 60, idxs))
                # 手机版：单列卡片，解决手机上表格挤的问题
                mp = os.path.join(OUT_DIR, "watch_m.html")
                dt = f"{results[0]['last_day']} 收盘" if results else ""
                with open(mp, "w", encoding="utf-8") as f:
                    f.write(render_mobile_html(results, idxs, data_time=dt))
                sp = os.path.join(OUT_DIR, "今天怎么办.html")
                payload = build_payload(codes, 120, meta=wl_meta if args.watchlist else None)
                with open(sp, "w", encoding="utf-8") as f:
                    f.write(render_app_html(payload, data_time=dt, days=120))
                print(f"已生成 {p}")
                print(f"手机版 {mp}")
                print(f"极简版 {sp}")
            if not args.watch:
                break
            time.sleep(args.watch)
        return

    # ---------- 全市场扫描
    rows, uni = run_scan(args)
    print_table(rows, args.top)
    if not args.no_html:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        p1 = os.path.join(OUT_DIR, f"scan_{stamp}.html")
        p2 = os.path.join(OUT_DIR, "latest.html")
        content = render_scan_html(rows, uni, args)
        for p in (p1, p2):
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        print(f"报告已生成：{p1}")
        print(f"最新副本：{p2}")


if __name__ == "__main__":
    from render import (render_scan_html, render_watch_html, render_mobile_html,
                        render_simple_html)
    from render_detail import render_detail_html
    from render_app import render_app_html
    main()
