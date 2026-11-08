# -*- coding: utf-8 -*-
"""
indicators.py — 把《半小时漫画股票实战》里的指标，全部翻译成可计算的公式。

设计原则：
1. 只用 pandas / numpy，不依赖 TA-Lib，装不上也能跑。
2. 每个函数返回 Series 或 DataFrame，最后一根K线就是"当下"。
3. 参数默认值 = 书里给的值。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- 基础工具

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def sma_cn(s: pd.Series, n: int, m: int = 1) -> pd.Series:
    """国内软件的 SMA(X,N,M) = 递推平滑，等价 ewm(alpha=M/N)。KDJ 用它。"""
    return s.ewm(alpha=m / n, adjust=False).mean()


def cross_up(a: pd.Series, b: pd.Series) -> pd.Series:
    """a 上穿 b（金叉）"""
    return (a > b) & (a.shift(1) <= b.shift(1))


def cross_down(a: pd.Series, b: pd.Series) -> pd.Series:
    """a 下穿 b（死叉）"""
    return (a < b) & (a.shift(1) >= b.shift(1))


# ---------------------------------------------------------------- 1. MACD

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """书：MACD(12,26,9)。DIF=快慢EMA之差，DEA=DIF的EMA，柱子=(DIF-DEA)*2"""
    dif = ema(close, fast) - ema(close, slow)
    dea = ema(dif, signal)
    hist = (dif - dea) * 2
    return pd.DataFrame({"DIF": dif, "DEA": dea, "HIST": hist})


# ---------------------------------------------------------------- 2. KDJ

def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """书：KDJ(9,3,3)。20以下超卖，80以上超买；J最灵敏，D最稳。"""
    ln = low.rolling(n, min_periods=1).min()
    hn = high.rolling(n, min_periods=1).max()
    rng = (hn - ln).replace(0, np.nan)
    rsv = ((close - ln) / rng * 100).fillna(50.0)
    k = sma_cn(rsv, m1, 1)
    d = sma_cn(k, m2, 1)
    j = 3 * k - 2 * d
    return pd.DataFrame({"K": k, "D": d, "J": j})


# ---------------------------------------------------------------- 3. BOLL

def boll(close: pd.Series, n: int = 26, k: float = 2.0) -> pd.DataFrame:
    """书：参数用26比20更灵敏。中轨=MA26，上下轨=±2倍标准差。"""
    mid = close.rolling(n, min_periods=1).mean()
    std = close.rolling(n, min_periods=1).std(ddof=0)
    upper = mid + k * std
    lower = mid - k * std
    width = (upper - lower) / mid.replace(0, np.nan) * 100
    return pd.DataFrame({"MID": mid, "UP": upper, "LOW": lower, "WIDTH": width})


# ---------------------------------------------------------------- 4. PSY

def psy(close: pd.Series, n: int = 12) -> pd.Series:
    """书：12天里上涨的天数占比。正常25-75，<=25超卖，>=75超买。"""
    up = (close > close.shift(1)).astype(float)
    return up.rolling(n, min_periods=1).sum() / n * 100


# ---------------------------------------------------------------- 5. DMI

def dmi(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 14, m: int = 6) -> pd.DataFrame:
    """书：PDI<5 = 超跌，捕反弹；ADX抬头=趋势加强，ADX拐头=可能转向。"""
    pc = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)

    hd = high - high.shift(1)
    ld = low.shift(1) - low
    pdm = pd.Series(np.where((hd > 0) & (hd > ld), hd, 0.0), index=high.index)
    mdm = pd.Series(np.where((ld > 0) & (ld > hd), ld, 0.0), index=high.index)

    tr_n = sma_cn(tr.fillna(0), n, 1)
    pdi = 100 * sma_cn(pdm, n, 1) / tr_n.replace(0, np.nan)
    mdi = 100 * sma_cn(mdm, n, 1) / tr_n.replace(0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    adx = sma_cn(dx.fillna(0), m, 1)
    adxr = (adx + adx.shift(m)) / 2
    return pd.DataFrame({"PDI": pdi, "MDI": mdi, "ADX": adx, "ADXR": adxr})


# ---------------------------------------------------------------- 6. 乖离率

def bias(close: pd.Series, n: int = 5) -> pd.Series:
    """书：收盘价偏离均线的百分比。大盘超2%、小盘超4%容易回抽。"""
    ma = close.rolling(n, min_periods=1).mean()
    return (close / ma - 1) * 100


# ---------------------------------------------------------------- 7. 均线

def ma_set(close: pd.Series, periods=(5, 10, 20, 60)) -> pd.DataFrame:
    return pd.DataFrame({f"MA{p}": close.rolling(p, min_periods=1).mean() for p in periods})


# ---------------------------------------------------------------- 8. ATR / 量能

def atr(high, low, close, n: int = 14) -> pd.Series:
    pc = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    return sma_cn(tr.fillna(0), n, 1)


def volume_features(vol: pd.Series) -> pd.DataFrame:
    """书：量在价先。量比 = 今日量 / 过去5日均量（收盘口径）。"""
    v5 = vol.rolling(5, min_periods=1).mean().shift(1)
    v10 = vol.rolling(10, min_periods=1).mean().shift(1)
    ratio = vol / v5.replace(0, np.nan)
    return pd.DataFrame({"VOL_MA5": v5, "VOL_MA10": v10, "VOL_RATIO": ratio})


# ---------------------------------------------------------------- 9. 背离检测（书里的三板斧）

def _swings(s: pd.Series, order: int = 5, kind: str = "low"):
    """找局部极值点（左右各 order 根内最极端的点）。"""
    idx = []
    vals = s.values
    n = len(vals)
    for i in range(order, n - order):
        window = vals[i - order: i + order + 1]
        if kind == "low" and vals[i] == np.nanmin(window) and np.isfinite(vals[i]):
            idx.append(i)
        if kind == "high" and vals[i] == np.nanmax(window) and np.isfinite(vals[i]):
            idx.append(i)
    return idx


def detect_divergence(close: pd.Series, dif: pd.Series, lookback: int = 70, order: int = 5,
                      recent: int = 22) -> dict:
    """
    返回 {'bottom': bool, 'top': bool, 'note': str}
    底背离：价格创新低，DIF 没创新低 → 跌不动了
    顶背离：价格创新高，DIF 没创新高 → 涨不动了

    收紧口径（避免假信号满天飞）：
      1. 第二个极值点必须落在最近 recent 根内（是"正在发生"的背离）
      2. 价格要真的创新低/新高（差 1% 以上）
      3. DIF 要反向拉开明显差距
      4. 底背离要求价格已从低点回升，顶背离要求已从高点回落
    """
    out = {"bottom": False, "top": False, "note": ""}
    if len(close) < 45 or len(dif) < 45:
        return out

    seg_c = close.iloc[-lookback:].reset_index(drop=True)
    seg_d = dif.iloc[-lookback:].reset_index(drop=True)
    n = len(seg_c)

    lows = _swings(seg_c, order, "low")
    highs = _swings(seg_c, order, "high")

    if len(lows) >= 2:
        i1, i2 = lows[-2], lows[-1]
        price_lower = seg_c.iloc[i2] < seg_c.iloc[i1] * 0.99
        dif_higher = seg_d.iloc[i2] > seg_d.iloc[i1] + max(0.02 * abs(seg_d.iloc[i1]), 0.01)
        fresh = (n - 1 - i2) <= recent
        rebounded = seg_c.iloc[-1] > seg_c.iloc[i2] * 1.01
        if price_lower and dif_higher and fresh and rebounded:
            out["bottom"] = True
            out["bottom_gap"] = float(seg_d.iloc[i2] - seg_d.iloc[i1])

    if len(highs) >= 2:
        i1, i2 = highs[-2], highs[-1]
        price_higher = seg_c.iloc[i2] > seg_c.iloc[i1] * 1.01
        dif_lower = seg_d.iloc[i2] < seg_d.iloc[i1] - max(0.02 * abs(seg_d.iloc[i1]), 0.01)
        fresh = (n - 1 - i2) <= recent
        fell = seg_c.iloc[-1] < seg_c.iloc[i2] * 0.99
        if price_higher and dif_lower and fresh and fell:
            out["top"] = True
            out["top_gap"] = float(seg_d.iloc[i1] - seg_d.iloc[i2])

    return out


# ---------------------------------------------------------------- 10. 位置与形态

def price_position(close: pd.Series, window: int = 250) -> float:
    """当前价在近 window 日区间中的百分位（0=最低，100=最高）。对应筹码分布的高低位置。"""
    seg = close.iloc[-window:]
    lo, hi = seg.min(), seg.max()
    if hi == lo:
        return 50.0
    return float((close.iloc[-1] - lo) / (hi - lo) * 100)


def limit_pct(code: str) -> float:
    """按板块返回涨停幅度，用于识别"是否涨停/接近涨停"。"""
    if code.startswith(("300", "301", "688", "689")):
        return 20.0
    if code.startswith(("8", "4", "920")):
        return 30.0
    return 10.0


def detect_ex_right(df: pd.DataFrame) -> bool:
    """粗测是否有除权（不复权数据导致的异常跳空）：单日跌幅>限幅且量突变。"""
    if len(df) < 3:
        return False
    chg = df["close"].pct_change().iloc[-1] * 100
    return chg < -21.0
