# -*- coding: utf-8 -*-
"""company.py — 抓公司资料 / 财务 / 新闻（新浪 F10），带当天缓存。"""

import os
import re
import json
import time
from datetime import datetime

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Referer": "https://finance.sina.com.cn"}

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "company_cache.json")


def _get(url, timeout=15):
    for _ in range(2):
        try:
            r = requests.get(url, headers=H, timeout=timeout)
            if r.status_code == 200:
                r.encoding = "gb2312"
                return r.text
        except Exception:
            time.sleep(0.3)
    return ""


def _txt(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("\u3000", " ")
    return re.sub(r"\s+", " ", s).strip()


def fetch_profile(symbol: str) -> dict:
    html = _get(f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpInfo/stockid/{symbol[2:]}.phtml")
    out = {}
    if not html:
        return out
    keys = ["公司名称", "公司简称", "上市日期", "注册资本", "员工人数", "所属行业",
            "主营业务", "公司简介", "注册地址", "办公地址", "公司网址", "法人代表"]
    m = re.search(r"所属行业[：:]?\s*</td>\s*<td[^>]*>.*?<a[^>]*>(.*?)</a>", html, re.S)
    if m:
        out["所属行业"] = _txt(m.group(1))
    for k in keys:
        m = re.search(re.escape(k) + r"[:：]?\s*</td>\s*<td[^>]*>(.*?)</td>", html, re.S)
        if m:
            v = _txt(m.group(1))
            if v:
                out[k] = v[:400]
    return out


# (显示名, 精确匹配规则——越靠前优先级越高)
FIN_KEYS = [
    ("每股收益", lambda n: n.startswith("每股收益") and "扣除" not in n),
    ("每股净资产", lambda n: n.startswith("每股净资产")),
    ("净资产收益率", lambda n: n.startswith("净资产收益率") and "扣除" not in n),
    ("营业收入", lambda n: ("营业收入" in n or "主营业务收入" in n) and "增长" not in n and "利润" not in n),
    ("净利润", lambda n: n.startswith("净利润") and "率" not in n and "增长" not in n),
    ("销售毛利率", lambda n: "毛利率" in n and "率" in n),
    ("资产负债率", lambda n: n.startswith("资产负债率")),
]


def fetch_finance(symbol: str) -> dict:
    """返回 {'periods': [...], 'rows': {指标: [值...]}}"""
    html = _get("https://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/"
                f"stockid/{symbol[2:]}/ctrl/{datetime.now().year}/displaytype/4.phtml")
    if not html:
        return {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    periods, data = [], {}
    for row in rows:
        cells = [_txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if not cells:
            continue
        if any("报表日期" in c for c in cells) and len(cells) >= 3:
            periods = [c for c in cells[1:] if re.match(r"\d{4}-\d{2}-\d{2}", c)]
            continue
        name = cells[0]
        if len(cells) < 3:
            continue
        for label, rule in FIN_KEYS:
            if rule(name) and label not in data:
                vals = []
                for c in cells[1:]:
                    try:
                        vals.append(float(c))
                    except Exception:
                        vals.append(None)
                if any(v is not None for v in vals):
                    data[label] = vals[:4]
                break
    if not periods:
        found = []
        for d in re.findall(r"\d{4}-\d{2}-\d{2}", html):
            if d >= "2020-01-01" and d not in found:
                found.append(d)
        found.sort(reverse=True)
        periods = found[:4] if found else [f"第{i+1}期" for i in range(4)]
    return {"periods": periods[:4], "rows": data}


def fetch_profit(symbol: str) -> dict:
    """利润表：营业总收入、净利润（万元→亿元）。"""
    html = _get("https://money.finance.sina.com.cn/corp/go.php/vFD_ProfitStatement/"
                f"stockid/{symbol[2:]}/ctrl/{datetime.now().year}/displaytype/4.phtml")
    if not html:
        return {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    out = {}
    for row in rows:
        cells = [_txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cells) < 3 or not cells[0]:
            continue
        name = cells[0]
        target = None
        if name.endswith("营业总收入") and "营业总收入" not in out:
            target = "营业总收入"
        elif name.endswith("净利润") and "归属" not in name and "扣除" not in name and "净利润" not in out:
            target = "净利润"
        if not target:
            continue
        vals = []
        for c in cells[1:4]:
            try:
                vals.append(round(float(c.replace(",", "")) / 1e4, 2))
            except Exception:
                vals.append(None)
        if any(v is not None for v in vals):
            out[target] = vals
    return out


def fetch_news(symbol: str, limit=8) -> list:
    html = _get(f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{symbol}.phtml")
    if not html:
        return []
    pat = re.compile(r"(\d{4}-\d{2}-\d{2})(?:&nbsp;|\s)*(\d{2}:\d{2})(?:&nbsp;|\s)*"
                     r"<a[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", re.S)
    out, seen = [], set()
    for d, t, url, title in pat.findall(html):
        title = _txt(title)
        if not title or title in seen:
            continue
        seen.add(title)
        out.append({"date": d, "time": t, "url": url, "title": title})
        if len(out) >= limit:
            break
    return out


def load_cache() -> dict:
    try:
        d = json.load(open(CACHE, encoding="utf-8"))
        return d if d.get("_date") == datetime.now().strftime("%Y-%m-%d") else {}
    except Exception:
        return {}


def save_cache(d: dict):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    json.dump(d, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)


def fetch_company(code: str, use_cache=True) -> dict:
    cache = load_cache() if use_cache else {}
    if code in cache:
        return cache[code]
    sym = ("sh" if code.startswith(("6", "9", "5")) else
           ("bj" if code.startswith(("8", "4", "92")) else "sz")) + code
    fin = fetch_finance(sym)
    prof = fetch_profit(sym)
    if prof and fin:
        fin.setdefault("rows", {})
        for k, v in prof.items():
            fin["rows"][k + "(亿)"] = v
    d = {"profile": fetch_profile(sym), "finance": fin, "news": fetch_news(sym)}
    cache[code] = d
    if use_cache:
        save_cache(cache)
    return d
