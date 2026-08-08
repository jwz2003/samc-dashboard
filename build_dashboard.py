#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAM C 情报终端构建器 v2：并发抓取全标的行情(1年)+新闻，生成 index.html / detail.html / data.js"""
import json, os, re, subprocess, glob, datetime, html as H, time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
INTEL_DIR = os.path.expanduser("~/storage-db-v1/P2_情报流")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

def curl(url, timeout=20):
    try:
        r = subprocess.run(["curl", "-s", "-L", "-m", str(timeout), "-A", UA, url],
                           capture_output=True, text=True, timeout=timeout + 10)
        return r.stdout
    except Exception:
        return ""

# ───────────── 标的定义 ─────────────
# (sym, short, name, group)
ALL_SYMS = [
    ("%5ESOX", "SOX", "费城半导体", "存储·美股/韩股"), ("MU", "MU", "美光", "存储·美股/韩股"),
    ("WDC", "WDC", "西部数据", "存储·美股/韩股"), ("NVDA", "NVDA", "英伟达", "存储·美股/韩股"),
    ("AMD", "AMD", "AMD", "存储·美股/韩股"), ("000660.KS", "Hynix", "SK海力士", "存储·美股/韩股"),
    ("005930.KS", "Samsung", "三星", "存储·美股/韩股"),
    ("SPY", "SPY", "标普500", "宏观"), ("QQQ", "QQQ", "纳指100", "宏观"),
    ("^VIX", "VIX", "恐慌指数", "宏观"), ("^TNX", "TNX", "美债10Y", "宏观"),
    ("DX-Y.NYB", "DXY", "美元指数", "宏观"),
    ("000001.SS", "SSE", "上证指数", "全球大盘"), ("%5EN225", "N225", "日经225", "全球大盘"),
    ("%5EKS11", "KOSPI", "韩国综合", "全球大盘"), ("%5EGSPC", "SPX", "标普500", "全球大盘"),
    ("%5ETWII", "TWII", "台湾加权", "全球大盘"), ("%5EHSI", "HSI", "恒生指数", "全球大盘"),
    ("399001.SZ", "SZSE", "深证成指", "全球大盘"), ("%5EDJI", "DJI", "道琼斯", "全球大盘"),
    ("000688.SS", "STAR", "科创50", "科技指数"), ("399006.SZ", "ChiNext", "创业板指", "科技指数"),
    ("%5ETELI", "TELI", "台湾电子", "科技指数"), ("%5ENDX", "NDX", "纳斯达克100", "科技指数"),
    ("%5EIXIC", "IXIC", "纳斯达克综指", "科技指数"), ("%5EKQ11", "KQ11", "KOSDAQ", "科技指数"),
    ("3033.HK", "HSTECH", "恒生科技", "科技指数"),
    ("CL=F", "WTI", "WTI原油", "能源"), ("BZ=F", "Brent", "布伦特原油", "能源"),
    ("NG=F", "NG", "天然气", "能源"),
    ("GC=F", "Gold", "黄金", "贵金属"), ("SI=F", "Silver", "白银", "贵金属"),
    ("PL=F", "Plat", "铂金", "贵金属"), ("PA=F", "Pall", "钯金", "贵金属"),
    ("HG=F", "Copper", "铜", "基本金属"), ("ALI=F", "Alu", "铝", "基本金属"),
    ("ZNC=F", "Zinc", "锌", "基本金属"), ("0NI=F", "Nickel", "镍", "基本金属"),
    ("TIO=F", "Iron", "铁矿石", "基本金属"),
]
CN_SYMS = [("1.603986", "603986", "兆易创新"), ("0.301308", "301308", "江波龙"),
           ("1.688525", "688525", "佰维存储"), ("0.001309", "001309", "德明利"),
           ("1.688008", "688008", "澜起科技"), ("0.000021", "000021", "深科技")]

NEWS_Q = {
    "%5ESOX": "Philadelphia semiconductor index", "MU": "Micron", "WDC": "Western Digital",
    "NVDA": "Nvidia", "AMD": "AMD", "000660.KS": "SK hynix", "005930.KS": "Samsung Electronics",
    "SPY": "S&P 500", "QQQ": "Nasdaq 100", "^VIX": "VIX", "^TNX": "10 year treasury yield",
    "DX-Y.NYB": "US dollar index", "CL=F": "WTI crude oil", "BZ=F": "Brent crude",
    "NG=F": "natural gas", "GC=F": "gold price", "SI=F": "silver price",
    "PL=F": "platinum", "PA=F": "palladium", "HG=F": "copper price", "ALI=F": "aluminum price",
    "ZNC=F": "zinc price", "0NI=F": "nickel price", "TIO=F": "iron ore price",
    "000001.SS": "上证指数 A股", "%5EN225": "Nikkei 225", "%5EKS11": "KOSPI index",
    "%5EGSPC": "S&P 500 index", "%5ETWII": "Taiwan stock index", "%5EHSI": "Hang Seng index",
    "399001.SZ": "深证成指", "%5EDJI": "Dow Jones", "000688.SS": "科创50",
    "399006.SZ": "创业板指", "%5ETELI": "Taiwan electronics index", "%5ENDX": "Nasdaq 100",
    "%5EIXIC": "Nasdaq composite", "%5EKQ11": "KOSDAQ index", "3033.HK": "恒生科技ETF",
}

def fmt_vol(v):
    if not v:
        return "—"
    if v >= 1e9:
        return f"{v/1e9:.1f}B"
    if v >= 1e6:
        return f"{v/1e6:.1f}M"
    if v >= 1e3:
        return f"{v/1e3:.0f}K"
    return str(v)

def rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains[:n]) / n; al = sum(losses[:n]) / n
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)

def ma(closes, n):
    return sum(closes[-n:]) / n if len(closes) >= n else None

def fetch_yahoo(sym):
    """返回 dict 或 None"""
    d = json.loads(curl(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1y"))
    r = d["chart"]["result"][0]
    m = r["meta"]
    q = r["indicators"]["quote"][0]
    closes = [c for c in q.get("close", []) if c is not None]
    if not closes:
        return None
    ts = r.get("timestamp", [])[:len(closes)]
    dates = [datetime.datetime.fromtimestamp(t, datetime.UTC).strftime("%Y-%m-%d") for t in ts]
    price = m.get("regularMarketPrice") or closes[-1]
    prev = closes[-2] if len(closes) >= 2 else price
    chg = (price / prev - 1) * 100 if prev else 0
    ytd = None
    if len(closes) > 30:
        # 粗略 YTD：用 12 月 31 日前后最近的点
        y = [i for i, t in enumerate(ts) if datetime.datetime.fromtimestamp(t, datetime.UTC).year == datetime.datetime.now(datetime.UTC).year - 1]
        if y:
            ytd = (price / closes[max(y)] - 1) * 100
    return {
        "price": price, "prev": prev, "chg": chg, "cur": m.get("currency", "USD"),
        "vol": fmt_vol(m.get("regularMarketVolume")), "vol_raw": m.get("regularMarketVolume"),
        "hi52": max(closes), "lo52": min(closes), "ytd": ytd,
        "ma20": ma(closes, 20), "ma50": ma(closes, 50), "rsi14": rsi(closes),
        "closes": closes, "dates": dates,
    }

def fetch_cn_quote(secid, code):
    """A股：东方财富 1 年日线 → 同结构 dict"""
    raw = curl(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&klt=101&fqt=1&lmt=250&end=20500101&fields1=f1,f2,f3&fields2=f51,f53")
    d = json.loads(raw) if raw else {}
    if not isinstance(d, dict) or not d.get("data"):
        return None
    klines = d.get("data", {}).get("klines", [])
    if not klines:
        return None
    closes = [float(k.split(",")[-1]) for k in klines]
    dates = [k.split(",")[0] for k in klines]
    price, prev = closes[-1], closes[-2]
    return {
        "price": price, "prev": prev, "chg": (price / prev - 1) * 100, "cur": "CNY",
        "vol": "—", "vol_raw": None, "hi52": max(closes), "lo52": min(closes),
        "ytd": None, "ma20": ma(closes, 20), "ma50": ma(closes, 50), "rsi14": rsi(closes),
        "closes": closes, "dates": dates,
    }

def fetch_news(query, n=4, zh=False):
    try:
        hl = "zh-CN&gl=CN&ceid=CN:zh-Hans" if zh else "en-US&gl=US&ceid=US:en"
        x = curl(f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl={hl}", timeout=15)
        items = re.findall(r"<item>\s*<title>(.*?)</title>.*?<link>(.*?)</link>.*?<source[^>]*>(.*?)</source>", x, re.S)
        out = []
        for t, u, s in items[:n]:
            out.append({"t": H.unescape(t).replace("<![CDATA[", "").replace("]]>", ""), "u": u.strip(), "s": H.unescape(s)})
        return out
    except Exception:
        return []

def build_quote(item):
    sym, short, name, group = item
    if sym.startswith("cn:"):
        _, secid, code = sym.split(":")
        q = None
        for _ in range(3):  # 并发限流重试
            q = fetch_cn_quote(secid, code)
            if q:
                break
            time.sleep(0.6)
        short = code
    else:
        q = fetch_yahoo(sym)
    if not q:
        return None
    q.update({"sym": code if sym.startswith("cn:") else sym, "short": short, "name": name, "group": group,
              "news": fetch_news(NEWS_Q.get(sym, name), 4, zh=(sym.startswith("cn:")))})
    return q

# ───────────── 渲染：主页 ─────────────
def market_rows_html(quotes):
    groups = []
    for q in quotes:
        if q["group"] not in groups and q["group"] not in ("全球大盘", "科技指数"):
            groups.append(q["group"])
    out = []
    for g in groups:
        out.append(f'<tr class="group" data-g="{g}"><td colspan="6">{g}</td></tr>')
        for q in quotes:
            if q["group"] != g or q["group"] in ("全球大盘", "科技指数"):
                continue
            closes = q["closes"][-5:]
            sp = sparkline(closes)
            cls = "up" if q["chg"] > 0.05 else ("down" if q["chg"] < -0.05 else "flat")
            out.append(f'<tr data-sym="{H.escape(q["sym"])}"><td><a class="sym-link" href="detail.html?s={H.escape(q["sym"])}">{q["short"]}</a></td><td>{q["name"]}</td>'
                       f'<td>{q["price"]:,.2f}</td><td><span class="chg {cls}">{q["chg"]:+.2f}%</span></td>'
                       f'<td class="vol">{q["vol"]}</td><td>{sp}</td></tr>')
    return "\n".join(out)

def index_charts_html(quotes):
    idx = [q for q in quotes if q["group"] in ("全球大盘", "科技指数")]
    cards = []
    for q in idx:
        closes = q.get("closes") or []
        cls = "up" if q["chg"] > 0.05 else ("down" if q["chg"] < -0.05 else "flat")
        chg_s = f"{q['chg']:+.2f}%"
        chart = ""
        if len(closes) >= 10:
            w, h, pad = 300, 84, 6
            mn, mx = min(closes), max(closes)
            rg = (mx - mn) or 1
            pts = []
            for i, v in enumerate(closes):
                x = pad + i * (w - 2 * pad) / (len(closes) - 1)
                y = h - pad - (v - mn) / rg * (h - 2 * pad)
                pts.append(f"{x:.1f},{y:.1f}")
            lx = pad + (len(closes) - 1) * (w - 2 * pad) / (len(closes) - 1)
            col = "#2962ff"
            chart = (f'<svg class="idx-chart" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
                     f'<defs><linearGradient id="g{q["sym"]}" x1="0" y1="0" x2="0" y2="1">'
                     f'<stop offset="0" stop-color="{col}" stop-opacity=".22"/>'
                     f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient></defs>'
                     f'<path d="M{" L".join(pts)} L {lx},{h-pad} L {pad},{h-pad} Z" fill="url(#g{q["sym"]})"/>'
                     f'<path d="M{" L".join(pts)}" fill="none" stroke="{col}" stroke-width="1.8"/>'
                     f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="3" fill="{col}"/></svg>')
        cards.append(
            f'<div class="idx-card" onclick="location.href=\'detail.html?s={H.escape(q["sym"])}\'">'
            f'<div class="idx-top"><span class="idx-name">{q["name"]}</span><span class="idx-sym">{q["short"]}</span></div>'
            f'<div class="idx-nums"><span class="idx-price">{q["price"]:,.2f}</span>'
            f'<span class="idx-chg {cls}">{chg_s}</span></div>{chart}</div>'
        )
    return "\n".join(cards)

def sparkline(closes):
    vals = [c for c in closes if c is not None]
    if len(vals) < 2:
        return ""
    w, h, pad = 64, 20, 2
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1
    pts = []
    for i, v in enumerate(vals):
        x = pad + i * (w - 2 * pad) / (len(vals) - 1)
        y = h - pad - (v - mn) / rng * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    cls = "up" if vals[-1] >= vals[0] else "down"
    return f'<svg class="spark {cls}" viewBox="0 0 {w} {h}"><path d="M{" L".join(pts)}"/></svg>'

def hero_quotes_html(quotes):
    by = {q["sym"]: q for q in quotes}
    def q(sym, name):
        d = by.get(sym)
        if not d:
            return f'<div class="q"><div class="q-sym">{sym}</div><div class="empty">未披露</div></div>'
        cls = "up" if d["chg"] > 0.05 else ("down" if d["chg"] < -0.05 else "flat")
        hi_s = f"{d['hi52']:,.0f}" if d["hi52"] > 100 else f"{d['hi52']:,.2f}"
        lo_s = f"{d['lo52']:,.0f}" if d["lo52"] > 100 else f"{d['lo52']:,.2f}"
        return (f'<a href="detail.html?s={H.escape(sym)}" style="text-decoration:none;color:inherit">'
                f'<div class="q"><div class="q-top"><span class="q-sym">{d["short"]}</span><span class="q-name">{name}</span></div>'
                f'<div class="q-price">{d["price"]:,.2f}</div><div class="q-chg {cls}">{d["chg"]:+.2f}%</div>'
                f'<div class="q-meta"><span>52周高 <b>{hi_s}</b></span><span>52周低 <b>{lo_s}</b></span><span>量 <b>{d["vol"]}</b></span></div></div></a>')
    return q("%5ESOX", "费城半导体指数") + q("MU", "美光 Micron")

def news_items_html():
    items = []
    try:
        h = curl("https://www.chinaflashmarket.com/")
        for t in re.findall(r'<a[^>]*title="([^"]+)"', h):
            t = H.unescape(t).strip()
            if t and len(t) > 5 and "首页" not in t and "用户中心" not in t:
                items.append((t, "CFM", "https://www.chinaflashmarket.com/"))
    except Exception:
        pass
    try:
        h2 = curl("https://www.trendforce.com/presscenter/news")
        for href, t in re.findall(r'<a[^>]+href="([^"]*?/presscenter/news/\d+[^"]*)"[^>]*>(.*?)</a>', h2, re.S):
            t = re.sub(r"<[^>]+>", "", t).strip()
            if t and len(t) > 8:
                url = href if href.startswith("http") else "https://www.trendforce.com" + href
                items.append((t, "TrendForce", url))
    except Exception:
        pass
    seen, out = set(), []
    for t, src, url in items:
        if t in seen:
            continue
        seen.add(t)
        out.append(f'<a href="{H.escape(url)}" target="_blank">{H.escape(t)}<span class="src">{src}</span></a>')
    return "\n".join(out[:14]) or '<div class="empty">暂无要闻</div>'

# ───────────── PDB 简报解析（保持不变） ─────────────
def latest_brief():
    files = sorted(glob.glob(os.path.join(INTEL_DIR, "*.md")), key=os.path.getmtime, reverse=True)
    for f in files:
        if "价格快照" in f or "台厂" in f:
            continue
        try:
            return open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
    return ""

def section(text, *keys):
    for part in re.split(r"\n##(?!#)\s*", text):
        head = part.split("\n", 1)[0]
        if any(k in head for k in keys):
            body = part.split("\n", 1)[1] if "\n" in part else ""
            return body.strip()
    return ""

def brief_cards_html():
    text = latest_brief()
    if not text:
        return '<div class="empty">暂无简报（每日 07:00 生成）</div>'
    sec = section(text, "最高优先级")
    if not sec:
        return '<div class="empty">简报尚未生成情报条目</div>'
    lv = {"🔴": "lv-red", "🟡": "lv-yellow", "🟢": "lv-green"}
    tag = {"🔴": "CRITICAL", "🟡": "IMPORTANT", "🟢": "BACKGROUND"}
    heads = list(re.finditer(r"(?:###?\s*|\*\*)(\d+)\.\s*(\[[^\]]+\])\s*", sec))
    cards = []
    for i, m in enumerate(heads):
        body = sec[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(sec)]
        title = re.sub(r"^(?:###?\s*|\*\*)\s*\d+\.\s*", "", m.group(0)).strip()
        lvch = m.group(2)[1] if len(m.group(2)) > 1 else "🟡"
        cls = lv.get(lvch, "lv-yellow")
        fact = re.split(r"(?:\*|＊)?对你意味着|意味着[：:]", body)[0].strip()
        fact_lines = fact.split("\n")
        fact = "\n".join(fact_lines[1:]).strip() if len(fact_lines) > 1 else ""
        fact = re.sub(r"\*$", "", fact).strip()
        means = ""
        mm = re.search(r"(?:对你意味着|意味着)[：:]\s*(.*?)(?=\n\s*🎯|\n\s*\*\*?[0-9]|\Z)", body, re.S)
        if mm:
            means = re.sub(r"[\*＊]", "", mm.group(1)).strip()
        dec = ""
        dm = re.search(r"🎯[^\n]*?[：:]\s*(.*?)(?=\n\s*###?\s*\d|\n##|\Z)", body, re.S)
        if dm:
            dec = dm.group(1).strip()
        stance, stance_cn = "watch", "观望"
        sm = re.search(r"立场[=：:]\s*([^，。;\n]+)", dec)
        if sm:
            s = sm.group(1).strip()
            if re.match(r"^(减仓|减持|卖出|兑现|分批)", s):
                stance, stance_cn = "st-cut", "减仓"
            elif re.match(r"^(持有|继续持有|持股|维持)", s):
                stance, stance_cn = "st-hold", "持有"
            elif re.match(r"^(加仓|买入|增持|逢低)", s):
                stance, stance_cn = "st-add", "加仓"
            else:
                stance, stance_cn = "st-watch", "观望"
        dec_html = ""
        if dec:
            rows = []
            for line in dec.split("\n"):
                line = line.strip().lstrip("·-•")
                if not line:
                    continue
                key = {"立场": "立场", "具体动作": "动作", "关键信号": "信号", "触发": "触发", "风险": "风险"}
                k = next((v for k_, v in key.items() if k_ in line[:8]), "")
                if k == "立场":
                    rest = line.split("：", 1)[-1] if "：" in line else ""
                    rows.append(f'<div class="row"><b>立场</b> <span class="stance {stance}">{stance_cn}</span> {H.escape(rest)}</div>')
                else:
                    rows.append(f'<div class="row"><b>{k}</b> {H.escape(line.split("：", 1)[-1] if "：" in line else line)}</div>')
            dec_html = '<div class="dec"><div class="dh">🎯 决策方案 <span style="float:right;font-weight:400">模拟场景 · 假设持有</span></div>' + "\n".join(rows) + "</div>"
        means_html = f'<div class="means"><b>对你意味着</b>　{H.escape(means)}</div>' if means else ""
        cards.append(
            f'<div class="brief {cls}"><div class="bar"></div><div class="body">'
            f'<div class="t"><span class="lv-tag">{tag.get(lvch, "")}</span>{H.escape(title)}</div>'
            f'<div class="f">{H.escape(fact)}</div>{means_html}{dec_html}</div></div>'
        )
    return "\n".join(cards) if cards else '<div class="empty">无情报条目</div>'

def decision_list_html():
    sec = section(latest_brief(), "决策清单")
    if not sec:
        return '<li>暂无决策清单</li>'
    items = [l.strip().lstrip("-·•0123456789. ") for l in sec.split("\n") if l.strip().startswith(("-", "·", "•", "1", "2", "3", "4", "5", "6", "7"))]
    return "\n".join(f"<li>{H.escape(i)}</li>" for i in items[:8]) or "<li>暂无</li>"

def timeline_html():
    sec = section(latest_brief(), "时间线")
    if not sec:
        return '<li>无已知事件</li>'
    items = [l.strip().lstrip("-·•") for l in sec.split("\n") if l.strip() and not l.strip().startswith("Ⅳ")]
    return "\n".join(f"<li>{H.escape(i)}</li>" for i in items[:8]) or "<li>无已知事件</li>"

def dxi_block():
    path = os.path.join(INTEL_DIR, "价格快照.csv")
    if not os.path.exists(path):
        return '<div class="empty">等待首次周快照（每周日 20:30 生成）</div>', "—", "未披露"
    rows = []
    for ln in open(path, encoding="utf-8", errors="ignore"):
        p = ln.strip().split(",")
        if len(p) >= 2 and p[0] and p[0] != "日期":
            try:
                rows.append((p[0], float(p[1])))
            except ValueError:
                continue
    if not rows:
        return '<div class="empty">暂无 DXI 数据</div>', "—", "未披露"
    vals = [v for _, v in rows]
    last, prev = vals[-1], (vals[-2] if len(vals) > 1 else None)
    chg = f"{(last/prev-1)*100:+.2f}%" if prev else "—"
    w, h, pad = 600, 90, 8
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1
    pts = []
    for i, (d, v) in enumerate(rows):
        x = pad + i * (w - 2 * pad) / (len(rows) - 1)
        y = h - pad - (v - mn) / rng * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    last_x = pad + (len(rows) - 1) * (w - 2 * pad) / (len(rows) - 1)
    svg = (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="#2962ff" stop-opacity=".25"/><stop offset="1" stop-color="#2962ff" stop-opacity="0"/>'
           f'</linearGradient></defs>'
           f'<path d="M{" L".join(pts)} L {last_x},{h-pad} L {pad},{h-pad} Z" fill="url(#g)"/>'
           f'<path d="M{" L".join(pts)}" fill="none" stroke="#2962ff" stroke-width="2"/>'
           f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="3.5" fill="#2962ff"/>'
           f'</svg>')
    sub = f"最新 {rows[-1][0]} · 环比 {chg} · {len(rows)} 周记录"
    return svg, f"{last:,.0f}", sub

def revenue_table_html():
    path = os.path.join(INTEL_DIR, "台厂月营收.csv")
    if not os.path.exists(path):
        return '<div class="empty">等待首次月营收（每月 8 日生成）</div>'
    lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore") if l.strip()]
    if len(lines) < 2:
        return '<div class="empty">暂无数据</div>'
    header = lines[0].split(",")
    rows = [l.split(",") for l in lines[1:]]
    last_month = rows[-1][0] if rows else ""
    hdr = "".join(f"<th>{H.escape(h)}</th>" for h in header)
    trs = []
    for r in rows[-5:]:
        tds = []
        for j, v in enumerate(r):
            cls = ""
            if j in (2, 3, 4) and v not in ("", "未披露"):
                try:
                    cls = "up" if float(v.replace("%", "")) > 0 else ("down" if float(v.replace("%", "")) < 0 else "flat")
                except ValueError:
                    pass
            tds.append(f'<td class="num" style="text-align:left">{H.escape(v)}</td>' if j == 1 else
                       f'<td class="num"><span class="chg {cls}">{H.escape(v)}</span></td>' if cls else f'<td class="num">{H.escape(v)}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div style="font-size:11px;color:#4a5570;margin-bottom:6px">报告月：{H.escape(last_month)} · 最近 {len(rows[-5:])} 行</div><table><tr>{hdr}</tr>' + "".join(trs) + "</table>"

# ───────────── 渲染：详情页 ─────────────
DETAIL_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}} · SAM C 情报终端</title>
<style>
:root{--bg:#000000;--panel:#131722;--panel2:#1a1f2e;--hover:#232833;--line:#2a2e39;--txt:#d1d4dc;--dim:#787b86;--faint:#5d606b;--cyan:#2962ff;--gold:#d4a853;--up:#089981;--down:#f23645;--mono:"SF Mono",ui-monospace,Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:var(--sans);font-size:13px;line-height:1.6;-webkit-font-smoothing:antialiased;padding-bottom:36px}
.topbar{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:16px;padding:9px 18px;background:rgba(19,23,34,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.back{color:var(--dim);text-decoration:none;font-size:12px;padding:4px 10px;border:1px solid var(--line);border-radius:6px}
.back:hover{color:var(--txt);border-color:var(--line2)}
.sym-big{font-family:var(--mono);font-size:20px;font-weight:800;color:#7db3ff}
.name-line{font-size:11px;color:var(--dim)}
.live{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:10px;color:var(--dim);letter-spacing:1px}
.live i{width:6px;height:6px;border-radius:50%;background:var(--down);box-shadow:0 0 6px var(--down);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.wrap{max-width:1100px;margin:0 auto;padding:18px 20px}
.price-row{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:4px}
.price{font-family:var(--mono);font-size:44px;font-weight:800;letter-spacing:.5px}
.chg{font-family:var(--mono);font-size:20px;font-weight:700}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--dim)}
.cur{font-size:12px;color:var(--faint);margin-left:2px}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.m{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px}
.m .k{font-size:10px;letter-spacing:1px;color:var(--faint);text-transform:uppercase}
.m .v{font-family:var(--mono);font-size:17px;font-weight:700;margin-top:2px}
.m .s{font-size:10.5px;color:var(--dim)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;margin-bottom:14px;overflow:hidden}
.panel-h{padding:8px 14px;border-bottom:1px solid var(--line);font-size:11px;letter-spacing:0;color:var(--dim);font-weight:500;display:flex;align-items:center;justify-content:space-between}
.tf{display:flex;gap:2px}
.tf button{background:transparent;border:1px solid transparent;color:var(--dim);font-size:11px;padding:2px 9px;border-radius:4px;cursor:pointer;font-family:var(--sans)}
.tf button:hover{background:var(--hover);color:var(--txt)}
.tf button.on{background:var(--hover);color:var(--txt);border-color:var(--line2)}
.loading{color:var(--faint);padding:24px;text-align:center;font-size:12px}
.errbox{display:none;color:var(--down);background:var(--down-bg);border:1px solid var(--line);border-radius:6px;padding:14px;margin:14px;font-size:12px}
.chart-box{background:#000;padding:12px 8px 4px}
.chart-box svg{width:100%;height:320px;display:block}
.legend{display:flex;gap:18px;padding:8px 14px;font-size:10.5px;color:var(--dim)}
.legend i{display:inline-block;width:14px;height:2px;vertical-align:middle;margin-right:5px}
.news a{display:block;padding:8px 14px;color:#b8bdc9;text-decoration:none;font-size:12px;border-bottom:1px dashed rgba(42,46,57,.8)}
.news a:hover{color:#7db3ff;background:var(--hover)}
.news .src{color:var(--faint);font-size:9.5px;margin-left:6px}
.pos-bar{height:8px;border-radius:4px;background:#0e1119;border:1px solid var(--line);overflow:hidden;margin-top:6px}
.pos-bar i{display:block;height:100%;background:linear-gradient(90deg,#089981,var(--gold),#f23645)}
.empty{color:var(--faint);font-style:italic;font-size:11px;padding:8px 14px}
.statusbar{position:fixed;bottom:0;left:0;right:0;display:flex;justify-content:space-between;padding:5px 18px;background:rgba(19,23,34,.94);border-top:1px solid var(--line);font-size:10px;color:var(--faint);font-family:var(--mono)}
</style>
</head>
<body>
<div class="topbar">
  <a class="back" href="index.html">← 返回</a>
  <a class="back" id="deep-link" href="#" style="color:var(--gold)">深度分析 →</a>
  <div><span class="sym-big" id="sym">—</span> <span class="name-line" id="name"></span></div>
  <div class="live"><i></i>LIVE</div>
</div>
<div class="wrap">
  <div class="price-row">
    <span class="price" id="price">—</span><span class="chg" id="chg"></span><span class="cur" id="cur"></span>
  </div>
  <div class="metrics" id="metrics"></div>
  <div class="panel">
    <div class="panel-h"><span>价格走势 · 价格 / MA20 / MA50</span><span class="tf"><button data-r="30">1M</button><button data-r="90">3M</button><button data-r="180">6M</button><button data-r="252" class="on">1Y</button></span></div>
    <div class="chart-box"><div id="chart"><div class="loading">数据加载中…</div></div></div>
    <div class="legend"><span><i style="background:#7db3ff"></i>价格</span><span><i style="background:var(--gold)"></i>MA20</span><span><i style="background:#b066ff"></i>MA50</span></div>
  </div>
  <div class="panel">
    <div class="panel-h">相关新闻</div>
    <div class="news" id="news"></div>
  </div>
</div>
<div class="statusbar"><span id="src"></span><span>仅供个人研究 · 模拟决策不构成投资建议</span></div>
<script src="data.js"></script>
<script>
window.onerror = function(m){ var e=document.getElementById('errbox'); if(e){ e.style.display='block'; e.textContent='加载出错：'+m; } };
const s = new URLSearchParams(location.search).get('s');
const q = (window.QUOTES||{})[s];
document.getElementById('deep-link').href = 'deep.html?s=' + encodeURIComponent(s);
document.title = (q? q.short+' · ' : '') + 'SAM C';
if (!q) {
  document.getElementById('errbox').style.display = 'block';
  document.getElementById('errbox').textContent = '未找到标的「' + s + '」——数据尚未生成或代码有误';
  document.getElementById('price').textContent = '—';
} else {
  document.getElementById('sym').textContent = q.short;
  document.getElementById('name').textContent = q.name + ' · ' + q.group;
  document.getElementById('price').textContent = q.price.toLocaleString(undefined,{minimumFractionDigits:2});
  document.getElementById('cur').textContent = q.cur;
  const c = document.getElementById('chg');
  c.textContent = (q.chg>=0?'+':'') + q.chg.toFixed(2) + '%';
  c.className = 'chg ' + (q.chg>0.05?'up':q.chg<-0.05?'down':'flat');
  const pos = q.hi52>q.lo52 ? Math.round((q.price-q.lo52)/(q.hi52-q.lo52)*100) : 0;
  const m = [
    ['52周高', q.hi52.toLocaleString(), ''], ['52周低', q.lo52.toLocaleString(), ''],
    ['年初至今', q.ytd!=null?(q.ytd>=0?'+':'')+q.ytd.toFixed(1)+'%':'未披露', q.ytd!=null?(q.ytd>0?'up':'down'):''],
    ['MA20', q.ma20!=null?q.ma20.toLocaleString():'—', q.ma20!=null?(q.price>=q.ma20?'up':'down'):''],
    ['MA50', q.ma50!=null?q.ma50.toLocaleString():'—', q.ma50!=null?(q.price>=q.ma50?'up':'down'):''],
    ['RSI14', q.rsi14!=null?q.rsi14.toFixed(1):'—', q.rsi14!=null?(q.rsi14>=70?'up':q.rsi14<=30?'down':''):''],
    ['成交量', q.vol, ''], ['52周位置', pos+'%', '']
  ];
  document.getElementById('metrics').innerHTML = m.map(x =>
    `<div class="m"><div class="k">${x[0]}</div><div class="v ${x[2]}">${x[1]}</div>` +
    (x[0]==='RSI14'&&q.rsi14!=null?`<div class="s">${q.rsi14>=70?'超买':q.rsi14<=30?'超卖':'中性'}</div>`:'') +
    (x[0]==='52周位置'?`<div class="pos-bar"><i style="width:${pos}%"></i></div>`:'') +
    `</div>`).join('');
  // 图表（支持周期切换）
  const W=900,H=300,P=12;
  function drawChart(r){
    const cl=q.closes, ds=q.dates;
    const box=document.getElementById('chart');
    if (!cl || cl.length<10){ box.innerHTML='<div class="loading">数据点不足，无法绘图</div>'; return; }
    const sl=cl.slice(-r), sld=ds?ds.slice(-r):[];
    const mn=Math.min(...sl), mx=Math.max(...sl), rg=(mx-mn)||1;
    const X=i=>P+i*(W-2*P)/(sl.length-1), Y=v=>H-P-(v-mn)/rg*(H-2*P);
    const line=(arr,color,w)=>{let d='';arr.forEach((v,i)=>{if(v==null)return;d+=(d?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1)+' '});return `<path d="${d}" fill="none" stroke="${color}" stroke-width="${w}"/>`};
    const m20=sl.map((_,i)=>i>=19?sl.slice(i-19,i+1).reduce((a,b)=>a+b)/20:null);
    const m50=sl.map((_,i)=>i>=49?sl.slice(i-49,i+1).reduce((a,b)=>a+b)/50:null);
    let grid='';for(let g=0;g<5;g++){const y=Y(mn+rg*g/4);grid+=`<line x1="${P}" y1="${y}" x2="${W-P}" y2="${y}" stroke="#2a2e39" stroke-width="1"/>`;}
    const area=`<path d="M${X(0).toFixed(1)},${Y(sl[0]).toFixed(1)} ${sl.map((v,i)=>'L'+X(i).toFixed(1)+','+Y(v).toFixed(1)).join(' ')} L${X(sl.length-1).toFixed(1)},${H-P} L${X(0).toFixed(1)},${H-P} Z" fill="rgba(41,98,255,.10)"/>`;
    box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}${area}${line(sl,'#2962ff',2)}${line(m20,'#d4a853',1.2)}${line(m50,'#b066ff',1.2)}</svg>`;
  }
  drawChart(252);
  document.querySelectorAll('.tf button').forEach(b=>b.addEventListener('click',()=>{
    document.querySelectorAll('.tf button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); drawChart(+b.dataset.r);
  }));
  const nw = q.news||[];
  document.getElementById('news').innerHTML = nw.length ? nw.map(n=>`<a href="${n.u}" target="_blank">${n.t}<span class="src">${n.s}</span></a>`).join('') : '<div class="empty">暂无相关新闻</div>';
}
document.getElementById('src').textContent = 'Yahoo Finance · 东方财富 · Google News · 更新 ' + new Date().toLocaleString('zh-CN');
</script>
</body>
</html>
"""

# ───────────── 渲染：三级页（深度分析） ─────────────
DEEP_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}} · 深度分析 · SAM C</title>
<style>
:root{--bg:#000;--panel:#131722;--panel2:#1a1f2e;--hover:#232833;--line:#2a2e39;--txt:#d1d4dc;--dim:#787b86;--faint:#5d606b;--blue:#2962ff;--gold:#d4a853;--up:#089981;--down:#f23645;--mono:"SF Mono",ui-monospace,Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:var(--sans);font-size:12px;line-height:1.6;-webkit-font-smoothing:antialiased;padding-bottom:34px}
.topbar{position:sticky;top:0;z-index:100;display:flex;align-items:center;gap:14px;padding:8px 16px;background:#0a0a0c;border-bottom:1px solid var(--line)}
.back{color:var(--dim);text-decoration:none;font-size:12px;padding:4px 10px;border:1px solid var(--line);border-radius:4px}
.back:hover{color:var(--txt);border-color:var(--line2)}
.sym-big{font-family:var(--mono);font-size:19px;font-weight:800;color:#7db3ff}
.name-line{font-size:11px;color:var(--dim)}
.live{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:10px;color:var(--dim);letter-spacing:1px}
.live i{width:6px;height:6px;border-radius:50%;background:var(--up);box-shadow:0 0 6px var(--up);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.wrap{max-width:1100px;margin:0 auto;padding:16px 18px}
.price-row{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.price{font-family:var(--mono);font-size:40px;font-weight:800}
.chg{font-family:var(--mono);font-size:18px;font-weight:700}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--dim)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.m{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:9px 13px}
.m .k{font-size:10px;color:var(--faint)}
.m .v{font-family:var(--mono);font-size:16px;font-weight:700;margin-top:2px}
.m .s{font-size:10px;color:var(--dim)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:4px;margin-bottom:12px;overflow:hidden}
.panel-h{padding:7px 14px;border-bottom:1px solid var(--line);font-size:11px;color:var(--dim);font-weight:500;display:flex;justify-content:space-between;align-items:center}
.panel-h .tag{font-size:9.5px;color:var(--faint);font-family:var(--mono)}
.chart-box{background:#000;padding:10px 6px 4px}
.chart-box svg{width:100%;display:block}
table{width:100%;border-collapse:collapse}
th{font-size:10px;color:var(--dim);text-align:right;padding:5px 12px;border-bottom:1px solid var(--line);font-weight:500}
th:first-child{text-align:left}
td{padding:5px 12px;border-bottom:1px solid rgba(42,46,57,.6);font-size:11.5px;text-align:right;font-variant-numeric:tabular-nums}
td:first-child{text-align:left;color:var(--dim)}
tr:hover td{background:var(--hover)}
.loading{color:var(--faint);padding:20px;text-align:center}
.errbox{display:none;color:var(--down);background:rgba(242,54,69,.1);border:1px solid var(--line);border-radius:4px;padding:12px;margin:12px;font-size:12px}
.statusbar{position:fixed;bottom:0;left:0;right:0;display:flex;justify-content:space-between;padding:4px 16px;background:#0a0a0c;border-top:1px solid var(--line);font-size:10px;color:var(--faint);font-family:var(--mono)}
</style>
</head>
<body>
<div class="topbar">
  <a class="back" id="back" href="index.html">← 返回</a>
  <div><span class="sym-big" id="sym">—</span> <span class="name-line" id="name"></span></div>
  <div class="live"><i></i>LIVE</div>
</div>
<div class="wrap">
  <div class="errbox" id="errbox"></div>
  <div class="price-row">
    <span class="price" id="price">—</span><span class="chg" id="chg"></span><span id="cur" style="color:var(--faint);font-size:11px"></span>
  </div>
  <div class="stats" id="stats"></div>
  <div class="panel">
    <div class="panel-h"><span>MACD · 12 / 26 / 9</span><span class="tag">MACD · SIGNAL · HIST</span></div>
    <div class="chart-box"><div id="c-macd"><div class="loading">计算中…</div></div></div>
  </div>
  <div class="panel">
    <div class="panel-h"><span>布林带 · MA20 ± 2σ</span><span class="tag">BOLL</span></div>
    <div class="chart-box"><div id="c-boll"><div class="loading">计算中…</div></div></div>
  </div>
  <div class="panel">
    <div class="panel-h"><span>RSI · 14 日历史</span><span class="tag">30 / 70</span></div>
    <div class="chart-box"><div id="c-rsi"><div class="loading">计算中…</div></div></div>
  </div>
  <div class="panel">
    <div class="panel-h"><span>月度涨跌 · 近 12 个月</span><span class="tag">MONTHLY</span></div>
    <table><thead><tr><th>月份</th><th>收盘</th><th>月涨跌</th></tr></thead><tbody id="t-monthly"></tbody></table>
  </div>
</div>
<div class="statusbar"><span id="src"></span><span>仅供个人研究</span></div>
<script src="data.js"></script>
<script>
window.onerror = function(m){ var e=document.getElementById('errbox'); if(e){ e.style.display='block'; e.textContent='加载出错：'+m; } };
const s = new URLSearchParams(location.search).get('s');
const q = (window.QUOTES||{})[s];
document.getElementById('back').href = 'detail.html?s=' + encodeURIComponent(s);
if (!q) {
  const e=document.getElementById('errbox'); e.style.display='block';
  e.textContent='未找到标的「'+s+'」';
} else {
  document.title = q.short + ' · 深度分析 · SAM C';
  document.getElementById('sym').textContent = q.short;
  document.getElementById('name').textContent = q.name + ' · ' + q.group;
  document.getElementById('price').textContent = q.price.toLocaleString(undefined,{minimumFractionDigits:2});
  document.getElementById('cur').textContent = q.cur;
  const c=document.getElementById('chg');
  c.textContent=(q.chg>=0?'+':'')+q.chg.toFixed(2)+'%';
  c.className='chg '+(q.chg>0.05?'up':q.chg<-0.05?'down':'flat');
  const cl=q.closes, ds=q.dates;
  // 统计卡
  const rets=[]; for(let i=1;i<cl.length;i++) rets.push(cl[i]/cl[i-1]-1);
  const avg=rets.reduce((a,b)=>a+b,0)/rets.length;
  const sd=Math.sqrt(rets.reduce((a,b)=>a+(b-avg)**2,0)/rets.length);
  const volA=sd*Math.sqrt(252)*100;
  let peak=cl[0], maxDD=0;
  for(const v of cl){ if(v>peak)peak=v; const dd=(peak-v)/peak*100; if(dd>maxDD)maxDD=dd; }
  const pos=q.hi52>q.lo52?Math.round((q.price-q.lo52)/(q.hi52-q.lo52)*100):0;
  const trend=(q.ma20!=null&&q.ma50!=null)?(q.ma20>q.ma50?'多头排列':'空头排列'):'—';
  const tcol=q.ma20!=null&&q.ma50!=null?(q.ma20>q.ma50?'up':'down'):'';
  document.getElementById('stats').innerHTML=[
    ['年化波动率', volA.toFixed(1)+'%', ''],
    ['最大回撤(1Y)', '-'+maxDD.toFixed(1)+'%', 'down'],
    ['52周位置', pos+'%', ''],
    ['均线趋势', trend, tcol],
    ['RSI14', q.rsi14!=null?q.rsi14.toFixed(1):'—', q.rsi14!=null?(q.rsi14>=70?'up':q.rsi14<=30?'down':''):'']
  ].map(x=>`<div class="m"><div class="k">${x[0]}</div><div class="v ${x[2]}">${x[1]}</div></div>`).join('');
  // 通用画图
  const W=860,H=190,P=8;
  function fig(el, series){ // series: [{d, color, w, fill}]
    if(!cl||cl.length<20){document.getElementById(el).innerHTML='<div class="loading">数据不足</div>';return;}
    let mn=Infinity,mx=-Infinity;
    series.forEach(sr=>sr.d.forEach(v=>{if(v==null)return;if(v<mn)mn=v;if(v>mx)mx=v;}));
    const rg=(mx-mn)||1;
    const X=i=>P+i*(W-2*P)/(cl.length-1), Y=v=>H-P-(v-mn)/rg*(H-2*P);
    let grid='';for(let g=0;g<4;g++){const y=Y(mn+rg*g/3);grid+=`<line x1="${P}" y1="${y}" x2="${W-P}" y2="${y}" stroke="#1c1f2a" stroke-width="1"/>`;}
    let html=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}`;
    series.forEach(sr=>{
      if(sr.fill){
        let d=`M${X(0)},${Y(sr.d[0])}`;for(let i=1;i<sr.d.length;i++){if(sr.d[i]==null)continue;d+=` L${X(i)},${Y(sr.d[i])}`;}
        html+=`<path d="${d} L${X(sr.d.length-1)},${H-P} L${X(0)},${H-P} Z" fill="${sr.fill}"/>`;
      } else {
        let d='';sr.d.forEach((v,i)=>{if(v==null)return;d+=(d?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1)+' ';});
        html+=`<path d="${d}" fill="none" stroke="${sr.color}" stroke-width="${sr.w||1.5}"/>`;
      }
    });
    html+='</svg>';
    document.getElementById(el).innerHTML=html;
  }
  function ema(arr,n){const o=[arr[0]];for(let i=1;i<arr.length;i++)o.push(arr[i]*(2/(n+1))+o[i-1]*(1-2/(n+1)));return o;}
  // MACD
  const e12=ema(cl,12), e26=ema(cl,26);
  const macd=cl.map((_,i)=>e12[i]-e26[i]);
  const sig=ema(macd,9);
  const hist=macd.map((v,i)=>v-sig[i]);
  let hmax=Math.max(...hist.map(Math.abs),0.0001);
  const bars=hist.map((v,i)=>`<rect x="${P+i*(W-2*P)/(cl.length-1)-0.6}" y="${H/2}" width="1.2" height="${-v/hmax*(H/2-10)}" fill="${v>=0?'#2962ff':'#f23645'}" opacity="0.75"/>`);
  fig('c-macd',[{d:macd,color:'#2962ff',w:1.6},{d:sig,color:'#d4a853',w:1.2}]);
  document.querySelector('#c-macd svg').insertAdjacentHTML('beforeend', bars.join(''));
  // 布林带
  const m20=[],sd20=[],upb=[],lob=[];
  for(let i=0;i<cl.length;i++){
    if(i>=19){const w=cl.slice(i-19,i+1);const a=w.reduce((x,y)=>x+y)/20;const s=Math.sqrt(w.reduce((x,y)=>x+(y-a)**2,0)/20);
      m20.push(a);sd20.push(s);upb.push(a+2*s);lob.push(a-2*s);}
    else{m20.push(null);sd20.push(null);upb.push(null);lob.push(null);}
  }
  fig('c-boll',[{d:upb,color:'rgba(120,123,134,.5)',w:1},{d:lob,color:'rgba(120,123,134,.5)',w:1},{d:m20,color:'#d4a853',w:1.2},{d:cl,color:'#2962ff',w:2}]);
  // RSI 历史
  const rs=[null];
  for(let i=14;i<cl.length;i++){
    let g=0,l=0;
    for(let j=i-13;j<=i;j++){const d=cl[j]-cl[j-1];if(d>0)g+=d;else l-=d;}
    rs.push(l===0?100:100-100/(1+g/14));
  }
  while(rs.length<cl.length)rs.unshift(null);
  const rlen=rs.length;
  for(let i=0;i<cl.length-rlen;i++)rs.unshift(null);
  const rsiFull=new Array(cl.length-rlen).fill(null).concat(rs.slice(0,rlen));
  fig('c-rsi',[{d:rsiFull.map(v=>v==null?null:70),color:'rgba(242,54,69,.4)',w:1},{d:rsiFull.map(v=>v==null?null:30),color:'rgba(8,153,129,.4)',w:1},{d:rsiFull,color:'#b066ff',w:1.8}]);
  // 月度
  const months={};
  ds.forEach((d,i)=>{const mk=d.slice(0,7);months[mk]=[i,cl[i]];});
  const mkeys=Object.keys(months).slice(-12);
  const rows=[];
  for(let i=0;i<mkeys.length;i++){
    const mk=mkeys[i], [idx,val]=months[mk];
    let chg=null;
    if(i>0){const pv=months[mkeys[i-1]][1];chg=(val/pv-1)*100;}
    const cls=chg==null?'flat':(chg>0.05?'up':chg<-0.05?'down':'flat');
    rows.push(`<tr><td>${mk}</td><td>${val.toLocaleString(undefined,{minimumFractionDigits:2})}</td><td><span class="chg ${cls}" style="font-size:11px;padding:1px 6px;border-radius:3px">${chg==null?'—':(chg>=0?'+':'')+chg.toFixed(2)+'%'}</span></td></tr>`);
  }
  document.getElementById('t-monthly').innerHTML=rows.reverse().join('');
}
document.getElementById('src').textContent='Yahoo Finance · 东方财富 · 更新 '+new Date().toLocaleString('zh-CN');
</script>
</body>
</html>
"""

# ───────────── 主流程 ─────────────
def main():
    now = datetime.datetime.now()
    week = "一二三四五六日"[now.weekday()]
    date_en = now.strftime("%b %d, %Y").upper() + " · " + now.strftime("%A").upper()
    date_cn = f"{now.year}年{now.month}月{now.day}日 星期{week}"

    items = ALL_SYMS + [("cn:" + secid + ":" + code, code, name, "A股存储链") for secid, code, name in CN_SYMS]
    cn_items = [i for i in items if i[0].startswith("cn:")]
    other = [i for i in items if not i[0].startswith("cn:")]
    print("抓取中...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(build_quote, other))
    for it in cn_items:  # A股串行，避免并发限流
        results.append(build_quote(it))
    quotes = [q for q in results if q]
    print(f"成功 {len(quotes)}/{len(items)} 个标的")

    # data.js
    data = {q["sym"]: {k: q[k] for k in ("short","name","group","price","chg","cur","vol","hi52","lo52","ytd","ma20","ma50","rsi14","closes","dates","news")} for q in quotes}
    with open(os.path.join(BASE, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.QUOTES=" + json.dumps(data, ensure_ascii=False) + ";")

    # index.html
    dxi_svg, dxi_val, dxi_sub = dxi_block()
    repl = {
        "{{date_en}}": date_en, "{{date_cn}}": date_cn,
        "{{brief_cards}}": brief_cards_html(),
        "{{decision_list}}": decision_list_html(),
        "{{timeline}}": timeline_html(),
        "{{hero_quotes}}": hero_quotes_html(quotes),
        "{{idx_cards}}": index_charts_html(quotes),
        "{{market_rows}}": market_rows_html(quotes),
        "{{market_count}}": str(len(quotes) - sum(1 for q in quotes if q["group"] in ("全球大盘", "科技指数"))),
        "{{news_items}}": news_items_html(),
        "{{dxi_chart}}": dxi_svg, "{{dxi_value}}": dxi_val, "{{dxi_sub}}": dxi_sub,
        "{{revenue_table}}": revenue_table_html(),
        "{{updated_at}}": now.strftime("%Y-%m-%d %H:%M"),
    }
    tpl = open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    open(os.path.join(BASE, "index.html"), "w", encoding="utf-8").write(tpl)

    # detail.html
    open(os.path.join(BASE, "detail.html"), "w", encoding="utf-8").write(DETAIL_TEMPLATE)
    # deep.html
    open(os.path.join(BASE, "deep.html"), "w", encoding="utf-8").write(DEEP_TEMPLATE)

    print(f"✅ 终端已更新 {now.strftime('%Y-%m-%d %H:%M')} · {len(quotes)} 标的 · index/detail/data.js 已生成")

if __name__ == "__main__":
    main()
