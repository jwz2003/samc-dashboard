#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAM C 情报仪表盘构建器：抓行情 + 解析 PDB 简报 + 渲染 index.html"""
import json, os, re, subprocess, glob, datetime, html as H

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

# ───────────── 1. 行情 ─────────────
US_GROUPS = [
    ("存储 · 美股/韩股", [("%5ESOX", "SOX", "费城半导体"), ("MU", "MU", "美光"), ("WDC", "WDC", "西部数据"),
        ("NVDA", "NVDA", "英伟达"), ("AMD", "AMD", "AMD"),
        ("000660.KS", "Hynix", "SK海力士"), ("005930.KS", "Samsung", "三星")]),
    ("宏观", [("SPY", "SPY", "标普500"), ("QQQ", "QQQ", "纳指100"), ("^VIX", "VIX", "恐慌指数"),
        ("^TNX", "TNX", "美债10Y"), ("DX-Y.NYB", "DXY", "美元指数")]),
]
CN_SYMS = [("1.603986", "兆易创新"), ("0.301308", "江波龙"), ("1.688525", "佰维存储"),
           ("0.001309", "德明利"), ("1.688008", "澜起科技"), ("0.000021", "深科技")]

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

def sparkline(closes):
    vals = [c for c in closes if c is not None]
    if len(vals) < 2:
        return ""
    w, h, pad = 70, 22, 2
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1
    pts = []
    for i, v in enumerate(vals):
        x = pad + i * (w - 2 * pad) / (len(vals) - 1)
        y = h - pad - (v - mn) / rng * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    cls = "up" if vals[-1] >= vals[0] else "down"
    return f'<svg class="spark {cls}" viewBox="0 0 {w} {h}"><path d="M{" L".join(pts)}"/></svg>'

def fetch_us():
    out = []  # [(group, row...)]
    for group, syms in US_GROUPS:
        rows = []
        for sym, short, name in syms:
            try:
                d = json.loads(curl(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"))
                r = d["chart"]["result"][0]
                m = r["meta"]
                closes = [c for c in r["indicators"]["quote"][0].get("close", []) if c is not None]
                price = m.get("regularMarketPrice")
                prev = closes[-2] if len(closes) >= 2 else None
                if price is None or prev in (None, 0):
                    rows.append((short, name, "—", "—", "flat", "", "—"))
                    continue
                chg = (price / prev - 1) * 100
                cls = "up" if chg > 0.05 else ("down" if chg < -0.05 else "flat")
                vol = fmt_vol(m.get("regularMarketVolume"))
                rows.append((short, name, f"{price:,.2f}", f"{chg:+.2f}%", cls, sparkline(closes), vol))
            except Exception:
                rows.append((short, name, "—", "—", "flat", "", "—"))
        out.append((group, rows))
    return out

def fetch_cn():
    rows = []
    d = json.loads(curl("https://push2.eastmoney.com/api/qt/ulist.np/get?secids=" +
                        ",".join(s for s, _ in CN_SYMS) +
                        "&fields=f2,f3,f12,f14"))
    diff = {x["f12"]: x for x in d.get("data", {}).get("diff", [])}
    for secid, name in CN_SYMS:
        code = secid.split(".")[1]
        x = diff.get(code)
        if not x or x.get("f2") in (None, "-"):
            rows.append((code, name, "—", "—", "flat", ""))
            continue
        price, chg = x["f2"] / 100, x["f3"] / 100
        cls = "up" if chg > 0.05 else ("down" if chg < -0.05 else "flat")
        # 5日K线 → sparkline
        sp = ""
        try:
            k = json.loads(curl(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&klt=101&fqt=1&lmt=5&end=20500101&fields1=f1,f2,f3&fields2=f51,f53"))
            klines = k.get("data", {}).get("klines", [])
            closes = [float(ln.split(",")[2]) for ln in klines if ln]
            sp = sparkline(closes)
        except Exception:
            pass
        rows.append((code, name, f"{price:,.2f}", f"{chg:+.2f}%", cls, sp))
    return rows

def market_rows_html():
    out = []
    for group, rows in fetch_us():
        out.append(f'<tr class="group"><td colspan="6">{group}</td></tr>')
        for sym, name, price, chg, cls, sp, vol in rows:
            out.append(f'<tr><td>{sym}</td><td>{name}</td><td>{price}</td><td><span class="chg {cls}">{chg}</span></td><td class="vol">{vol}</td><td>{sp}</td></tr>')
    out.append('<tr class="group"><td colspan="6">A股存储链 · 前一交易日收盘</td></tr>')
    for sym, name, price, chg, cls, sp in fetch_cn():
        out.append(f'<tr><td>{sym}</td><td>{name}</td><td>{price}</td><td><span class="chg {cls}">{chg}</span></td><td class="vol">—</td><td>{sp}</td></tr>')
    return "\n".join(out)

def hero_quotes_html():
    def q(sym, name):
        try:
            d = json.loads(curl(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1y"))
            r = d["chart"]["result"][0]
            m = r["meta"]
            closes = [c for c in r["indicators"]["quote"][0].get("close", []) if c is not None]
            price = m.get("regularMarketPrice")
            prev = closes[-2] if len(closes) >= 2 else None
            hi, lo = max(closes), min(closes)
            vol = fmt_vol(m.get("regularMarketVolume"))
            chg = (price / prev - 1) * 100 if price and prev else 0
            cls = "up" if chg > 0.05 else ("down" if chg < -0.05 else "flat")
            hi_s = f"{hi:,.0f}" if hi > 100 else f"{hi:,.2f}"
            lo_s = f"{lo:,.0f}" if lo > 100 else f"{lo:,.2f}"
            return (f'<div class="q"><div class="q-top"><span class="q-sym">{sym}</span><span class="q-name">{name}</span></div>'
                    f'<div class="q-price">{price:,.2f}</div><div class="q-chg {cls}">{chg:+.2f}%</div>'
                    f'<div class="q-meta"><span>52周高 <b>{hi_s}</b></span><span>52周低 <b>{lo_s}</b></span><span>量 <b>{vol}</b></span></div></div>')
        except Exception:
            return f'<div class="q"><div class="q-sym">{sym}</div><div class="empty">行情未披露</div></div>'
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

# ───────────── 2. PDB 简报解析 ─────────────
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
    # 只按 "## 罗马数字" 节标题切分；##(?!#) 避免误切 "### N." 条目
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
    # 按 **N. [等级] 分条
    heads = list(re.finditer(r"(?:###?\s*|\*\*)(\d+)\.\s*(\[[^\]]+\])\s*", sec))
    cards = []
    for i, m in enumerate(heads):
        body = sec[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(sec)]
        title = re.sub(r"^(?:###?\s*|\*\*)\s*\d+\.\s*", "", m.group(0)).strip()
        lvch = m.group(2)[1] if len(m.group(2)) > 1 else "🟡"
        cls = lv.get(lvch, "lv-yellow")
        # 事实 = 标题后到意味着
        fact = re.split(r"(?:\*|＊)?对你意味着|意味着[：:]", body)[0].strip()
        fact_lines = fact.split("\n")
        fact = "\n".join(fact_lines[1:]).strip() if len(fact_lines) > 1 else ""
        fact = re.sub(r"\*$", "", fact).strip()
        # 意味着
        means = ""
        mm = re.search(r"(?:对你意味着|意味着)[：:]\s*(.*?)(?=\n\s*🎯|\n\s*\*\*?[0-9]|\Z)", body, re.S)
        if mm:
            means = re.sub(r"[\*＊]", "", mm.group(1)).strip()
        # 决策
        dec = ""
        dm = re.search(r"🎯[^\n]*?[：:]\s*(.*?)(?=\n\s*###?\s*\d|\n##|\Z)", body, re.S)
        if dm:
            dec = dm.group(1).strip()
        stance = "watch"
        stance_cn = "观望"
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
                    rows.append(f'<div class="row"><b>立场</b> <span class="stance {stance}">{stance_cn}</span> {H.escape(line.split("：",1)[-1] if "：" in line else "")}</div>')
                else:
                    rows.append(f'<div class="row"><b>{k}</b> {H.escape(line.split("：",1)[-1] if "：" in line else line)}</div>')
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

# ───────────── 3. DXI / 台厂 ─────────────
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
    w, h, pad = 600, 100, 8
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1
    pts, labels = [], []
    for i, (d, v) in enumerate(rows):
        x = pad + i * (w - 2 * pad) / (len(rows) - 1)
        y = h - pad - (v - mn) / rng * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    last_x = pad + (len(rows) - 1) * (w - 2 * pad) / (len(rows) - 1)
    svg = (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="#4cc2ff" stop-opacity=".28"/><stop offset="1" stop-color="#4cc2ff" stop-opacity="0"/>'
           f'</linearGradient></defs>'
           f'<path d="M{" L".join(pts)} L {last_x},{h-pad} L {pad},{h-pad} Z" fill="url(#g)"/>'
           f'<path d="M{" L".join(pts)}" fill="none" stroke="#4cc2ff" stroke-width="2"/>'
           f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="3.5" fill="#4cc2ff"/>'
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

# ───────────── 4. 渲染 ─────────────
def main():
    now = datetime.datetime.now()
    week = "一二三四五六日"[now.weekday()]
    date_en = now.strftime("%b %d, %Y").upper() + " · " + now.strftime("%A").upper()
    date_cn = f"{now.year}年{now.month}月{now.day}日 星期{week}"
    dxi_svg, dxi_val, dxi_sub = dxi_block()
    repl = {
        "{{date_en}}": date_en, "{{date_cn}}": date_cn,
        "{{brief_cards}}": brief_cards_html(),
        "{{decision_list}}": decision_list_html(),
        "{{timeline}}": timeline_html(),
        "{{hero_quotes}}": hero_quotes_html(),
        "{{market_rows}}": market_rows_html(),
        "{{news_items}}": news_items_html(),
        "{{dxi_chart}}": dxi_svg, "{{dxi_value}}": dxi_val, "{{dxi_sub}}": dxi_sub,
        "{{revenue_table}}": revenue_table_html(),
        "{{updated_at}}": now.strftime("%Y-%m-%d %H:%M"),
    }
    tpl = open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    out = os.path.join(BASE, "index.html")
    open(out, "w", encoding="utf-8").write(tpl)
    print(f"✅ 仪表盘已更新 {now.strftime('%Y-%m-%d %H:%M')} · {out}")

if __name__ == "__main__":
    main()
