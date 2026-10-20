#!/usr/bin/env python3
"""MarketCal scraper — 抓取美股财报日历与美国宏观事件，输出 data.json。仅依赖 Python 标准库。"""
import html, json, re, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, time, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).with_name("data.json")
CST = timezone(timedelta(hours=8))
ET  = ZoneInfo("America/New_York")
UA  = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
       "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
DAYS_AHEAD  = 14        # 财报往后看几天
KEEP_PAST   = 30        # 已过去的事件保留几天
MIN_MCAP    = 1e9       # 财报只存市值 ≥ 10 亿美元的公司（关注列表不受限），控制文件大小

# 关注列表：页面上高亮。增删直接改这里
WATCHLIST = {
    "AAPL": "Mag 7", "MSFT": "Mag 7", "NVDA": "Mag 7", "GOOGL": "Mag 7", "GOOG": "Mag 7",
    "AMZN": "Mag 7", "META": "Mag 7", "TSLA": "Mag 7",
    "TSM": "半导体", "AVGO": "半导体", "AMD": "半导体", "NFLX": "科技",
    "BABA": "中概", "PDD": "中概", "JD": "中概", "BIDU": "中概", "NIO": "中概",
    "FUTU": "券商", "TIGR": "券商", "HOOD": "券商", "COIN": "券商",
}

# 常见美国宏观指标的中文名（ForexFactory 英文标题 → 中文）
EVENT_ZH = {
    "CPI m/m": "CPI 月率", "CPI y/y": "CPI 年率", "Core CPI m/m": "核心 CPI 月率",
    "PPI m/m": "PPI 月率", "Core PPI m/m": "核心 PPI 月率",
    "Non-Farm Employment Change": "非农就业人数", "Unemployment Rate": "失业率",
    "Average Hourly Earnings m/m": "平均时薪月率", "Unemployment Claims": "初请失业金人数",
    "ADP Non-Farm Employment Change": "ADP 就业人数", "JOLTS Job Openings": "JOLTS 职位空缺",
    "Federal Funds Rate": "联邦基金利率决议", "FOMC Statement": "FOMC 声明",
    "FOMC Press Conference": "FOMC 新闻发布会", "FOMC Meeting Minutes": "FOMC 会议纪要",
    "Advance GDP q/q": "GDP 初值（季率）", "Prelim GDP q/q": "GDP 修正值（季率）", "Final GDP q/q": "GDP 终值（季率）",
    "Core PCE Price Index m/m": "核心 PCE 物价指数月率", "Retail Sales m/m": "零售销售月率",
    "Core Retail Sales m/m": "核心零售销售月率", "ISM Manufacturing PMI": "ISM 制造业 PMI",
    "ISM Services PMI": "ISM 服务业 PMI", "Flash Manufacturing PMI": "制造业 PMI 初值",
    "Flash Services PMI": "服务业 PMI 初值", "Prelim UoM Consumer Sentiment": "密歇根消费者信心初值",
    "Revised UoM Consumer Sentiment": "密歇根消费者信心终值", "Prelim UoM Inflation Expectations": "密歇根通胀预期初值",
    "Revised UoM Inflation Expectations": "密歇根通胀预期终值", "Empire State Manufacturing Index": "纽约联储制造业指数",
    "Philly Fed Manufacturing Index": "费城联储制造业指数", "Pending Home Sales m/m": "成屋签约销售月率",
    "Industrial Production m/m": "工业产出月率", "Trade Balance": "贸易差额", "Treasury Currency Report": "财政部汇率报告",
    "CB Consumer Confidence": "谘商会消费者信心", "Building Permits": "营建许可",
    "Existing Home Sales": "成屋销售", "New Home Sales": "新屋销售", "Durable Goods Orders m/m": "耐用品订单月率",
    "Fed Chair Powell Speaks": "鲍威尔讲话", "Crude Oil Inventories": "EIA 原油库存",
}
COUNTRY_ZH = {"USD": "美国", "CNY": "中国", "EUR": "欧元区", "GBP": "英国", "JPY": "日本",
              "CAD": "加拿大", "AUD": "澳大利亚", "NZD": "新西兰", "CHF": "瑞士", "All": "全球"}

# ── 工具 ──────────────────────────────────────────────────────────────────────

def fetch(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()

def money(s):
    try:
        return float(re.sub(r"[^\d.\-]", "", s or "") or "nan")
    except ValueError:
        return float("nan")

def et_iso(d, hh=0, mm=0):
    return datetime.combine(d, time(hh, mm), ET).astimezone(CST).isoformat(timespec="minutes")

def run(label, fn):
    try:
        res = fn()
        print(f"  ✓ {label:<18} {len(res):>4}")
        return res, ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:200]
        print(f"  ✗ {label:<18}    0 {err}")
        return None, err

# ── 财报（Nasdaq） ────────────────────────────────────────────────────────────

TIME_MAP = {"time-pre-market": "bmo", "time-after-hours": "amc"}

def nasdaq_day(d):
    data = json.loads(fetch(f"https://api.nasdaq.com/api/calendar/earnings?date={d.isoformat()}"))
    rows = ((data.get("data") or {}).get("rows")) or []
    out = []
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        mcap = money(r.get("marketCap"))
        if sym not in WATCHLIST and not (mcap >= MIN_MCAP):
            continue
        out.append({
            "date":   d.isoformat(),
            "symbol": sym,
            "name":   (r.get("name") or "").strip(),
            "time":   TIME_MAP.get(r.get("time"), "tbd"),
            "mcap":   None if mcap != mcap else mcap,   # NaN → None
            "eps_fc": (r.get("epsForecast") or "").strip(),
            "eps_ly": (r.get("lastYearEPS") or "").strip(),
            "ests":   (r.get("noOfEsts") or "").strip(),
            "fq":     (r.get("fiscalQuarterEnding") or "").strip(),
            "watch":  WATCHLIST.get(sym, ""),
        })
    return out

def earnings(today):
    days = [today + timedelta(days=i) for i in range(DAYS_AHEAD + 1)]
    days = [d for d in days if d.weekday() < 5]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(nasdaq_day, days))
    return [r for day in results for r in day]

# ── 宏观：FOMC（美联储官网） ──────────────────────────────────────────────────

MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                      "August", "September", "October", "November", "December"], 1)}

def fomc():
    page = fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm").decode("utf-8", "ignore")
    out = []
    for y in re.findall(r"(\d{4}) FOMC Meetings", page):
        seg = page[page.find(f"{y} FOMC Meetings"):]
        nxt = re.search(r"\d{4} FOMC Meetings", seg[20:])
        seg = seg[: nxt.start() + 20] if nxt else seg
        for mon, days in re.findall(r"fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<", seg, re.S):
            mon, days = mon.strip(), days.strip()
            sep = "*" in days
            # "Apr/May 30-1"、"January 27-28"：取最后一天作为决议日
            mons = [m for m in re.split(r"[/-]", mon) if m]
            nums = re.findall(r"\d+", days)
            if not nums:
                continue
            m_name = mons[-1]
            m = next((v for k, v in MONTHS.items() if k.startswith(m_name[:3])), None)
            if not m:
                continue
            d = date(int(y), m, int(nums[-1]))
            out.append({"kind": "fomc", "country": "USD", "impact": "High",
                        "title": "FOMC 利率决议" + ("（含经济预测与点阵图）" if sep else ""),
                        "title_en": "FOMC Rate Decision" + (" + SEP" if sep else ""),
                        "time": et_iso(d, 14, 0), "date": d.isoformat(),
                        "url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"})
    return out

# ── 宏观：BEA 发布日（GDP、PCE 等） ──────────────────────────────────────────

BEA_ZH = [("GDP", "GDP"), ("Personal Income and Outlays", "个人收支（含 PCE 物价指数）"),
          ("International Trade in Goods and Services", "国际贸易收支")]
GDP_STAGE = {"Advance": "初值", "Second": "修正值", "Third": "终值"}
ORD = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}

def bea_title(title, zh):
    """'GDP (Advance Estimate), 3rd Quarter 2026' → 'GDP 初值（2026Q3）'"""
    stage = next((v for k, v in GDP_STAGE.items() if f"({k}" in title), "") if zh == "GDP" else ""
    period = title.rsplit(",", 1)[-1].strip() if "," in title else ""
    q = re.match(r"(1st|2nd|3rd|4th) Quarter (\d{4})", period)
    mth = re.match(r"([A-Z][a-z]+) (\d{4})", period)
    if q:
        period = f"{q.group(2)}Q{ORD[q.group(1)]}"
    elif mth and mth.group(1) in MONTHS:
        period = f"{mth.group(2)} 年 {MONTHS[mth.group(1)]} 月"
    return f"{zh}{' ' + stage if stage else ''}" + (f"（{period}）" if period else "")

def bea(today):
    page = fetch("https://www.bea.gov/news/schedule").decode("utf-8", "ignore")
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        m = re.match(r"([A-Z][a-z]+) (\d{1,2})\s*(\d{1,2}:\d{2}\s*[AP]M)?", cells[0])
        if not m or m.group(1) not in MONTHS:
            continue
        title = cells[-1]
        zh = next((z for k, z in BEA_ZH if k in title), None)
        # 只保留影响市场的几项；"GDP by County / by State" 这类地区统计不算
        if not zh or re.search(r"\bby (County|State|Industry|Metropolitan)", title):
            continue
        mon, day = MONTHS[m.group(1)], int(m.group(2))
        # 页面不写年份：比今天早两个月以上的视为明年
        y = today.year + (1 if mon < today.month - 2 else 0)
        d = date(y, mon, day)
        hh, mm = 8, 30
        if m.group(3):
            t = datetime.strptime(m.group(3).replace(" ", ""), "%I:%M%p")
            hh, mm = t.hour, t.minute
        out.append({"kind": "bea", "country": "USD", "impact": "High" if "GDP" in title or "Personal Income" in title else "Medium",
                    "title": bea_title(title, zh), "title_en": title,
                    "time": et_iso(d, hh, mm), "date": d.isoformat(), "url": "https://www.bea.gov/news/schedule"})
    return out

# ── 宏观：本周全球事件（ForexFactory） ────────────────────────────────────────

def week_events():
    data = json.loads(fetch("https://nfs.faireconomy.media/ff_calendar_thisweek.json"))
    out = []
    for e in data:
        if e.get("impact") not in ("High", "Medium") or e.get("country") not in COUNTRY_ZH:
            continue
        try:
            t = datetime.fromisoformat(e["date"])
        except Exception:
            continue
        title = e.get("title", "")
        zh = EVENT_ZH.get(title, "") if e["country"] == "USD" else ""
        # date 统一用美东日期分组（与财报、FOMC 一致），time 存北京时间用于展示
        out.append({"kind": "week", "country": e["country"], "impact": e["impact"],
                    "title": zh or title, "title_en": title,
                    "time": t.astimezone(CST).isoformat(timespec="minutes"), "date": t.astimezone(ET).date().isoformat(),
                    "forecast": e.get("forecast", ""), "previous": e.get("previous", ""),
                    "url": "https://www.forexfactory.com/calendar"})
    return out

# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
        except Exception:
            pass
    prev_src = {s["id"]: s for s in prev.get("sources", [])}
    now = datetime.now(CST)
    today_et = datetime.now(ET).date()
    cutoff = (today_et - timedelta(days=KEEP_PAST)).isoformat()

    print("→ 抓取")
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_earn = pool.submit(run, "Nasdaq 财报", lambda: earnings(today_et))
        f_fomc = pool.submit(run, "FOMC 日程", fomc)
        f_bea  = pool.submit(run, "BEA 发布日", lambda: bea(today_et))
        f_week = pool.submit(run, "本周宏观事件", week_events)

    sources = []
    def source(sid, name, res, err):
        p = prev_src.get(sid, {})
        sources.append({"id": sid, "name": name, "ok": res is not None, "error": err,
                        "count": len(res) if res is not None else p.get("count", 0),
                        # 失败时保留上次成功时间，页面据此标注「旧数据」
                        "updated": now.isoformat(timespec="seconds") if res is not None else p.get("updated", "")})

    # 财报：新抓到的日期整天替换，其他日期沿用上次（含已过去的）
    earn, err = f_earn.result()
    source("nasdaq", "Nasdaq 财报日历", earn, err)
    fresh_days = {r["date"] for r in earn or []}
    if earn is not None:
        fresh_days |= {(today_et + timedelta(days=i)).isoformat() for i in range(DAYS_AHEAD + 1)}
    kept = [r for r in prev.get("earnings", []) if r["date"] not in fresh_days]
    earnings_all = sorted([r for r in kept + (earn or []) if r["date"] >= cutoff],
                          key=lambda r: (r["date"], -(r["mcap"] or 0)))

    # 宏观：按 (类型, 日期, 英文标题) 去重，新数据覆盖旧数据；本周事件靠每周累积保留历史
    macro = {}
    for e in prev.get("macro", []):
        macro[(e["kind"], e["date"], e["title_en"])] = e
    for sid, name, fut in (("fomc", "美联储 FOMC 日程", f_fomc), ("bea", "BEA 发布日", f_bea),
                           ("week", "ForexFactory 本周事件", f_week)):
        res, err = fut.result()
        source(sid, name, res, err)
        if res is not None and sid in ("fomc", "bea"):
            # 官方日程整体替换，避免改期后残留旧日期（已过去的保留）
            macro = {k: v for k, v in macro.items() if not (v["kind"] == sid and v["date"] >= today_et.isoformat())}
        for e in res or []:
            macro[(e["kind"], e["date"], e["title_en"])] = e
    macro_all = sorted((e for e in macro.values() if e["date"] >= cutoff), key=lambda e: e["time"])

    data = {
        "updated":   now.isoformat(timespec="seconds"),   # 每次都变，保证每次运行都有提交
        "today_et":  today_et.isoformat(),
        "watchlist": WATCHLIST,
        "sources":   sources,
        "earnings":  earnings_all,
        "macro":     macro_all,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    ok = sum(s["ok"] for s in sources)
    print(f"→ 完成：{ok}/{len(sources)} 个来源正常，财报 {len(earnings_all)} 条，宏观事件 {len(macro_all)} 条 → {OUT.name}")

if __name__ == "__main__":
    main()
