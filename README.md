# 📅 MarketCal · 财报与宏观日历

> 一个页面看清未来两周美股重要公司的财报时间，以及美联储议息、GDP、PCE、CPI、非农等宏观事件，带倒计时

**🌐 在线访问：[https://climb0516.github.io/earnings-calendar/](https://climb0516.github.io/earnings-calendar/)**

---

## 功能

- **本周概览**：顶部是「下一个高影响事件」「下次 FOMC」「下一家关注公司财报」倒计时；下面是未来 7 天日历，每天列出宏观事件（北京时间）和财报公司（按盘前 / 盘后分组）
- **财报日历**：未来 14 天按日期分组，显示代码、公司、盘前 / 盘后、市值、EPS 预期、去年同期 EPS、分析师数、财季；关注列表里的公司置顶高亮
- **宏观日历**：FOMC 全年日程（标注带经济预测和点阵图的会议）、BEA 发布日（GDP、PCE、贸易）、ForexFactory 本周事件（带预期值和前值），按月分组，显示倒计时
- **筛选**：财报按市值门槛（只看关注 / ≥ 1000 亿 / ≥ 100 亿 / ≥ 10 亿美元），宏观按地区（美国 / 全球）；全文搜索（`⌘K` / `Ctrl K`）
- **右侧挂件**：关注公司财报、接下来几次 FOMC、来源状态
- 右上角：↻ 重新读取数据，⚡ 跳转 GitHub Actions 手动触发抓取，☾ 切换深浅色；手机适配

日期按**美东时间**分组（与美股交易日一致），宏观事件的具体时间显示为**北京时间**。

---

## 关注列表

`scraper.py` 开头的 `WATCHLIST`，增删直接改：

```
Mag 7：AAPL MSFT NVDA GOOGL AMZN META TSLA
半导体 / 科技：TSM AVGO AMD NFLX
中概：BABA PDD JD BIDU NIO
券商：FUTU TIGR HOOD COIN
```

---

## 技术架构

```
GitHub Actions（触发：每天北京时间 07:00 定时 / 手动 dispatch / push 修改 scraper.py 或 workflow）
  ↓ python scraper.py（Python 3.12，只用标准库，无需安装依赖）
  ↓ 线程池并发抓取 4 个来源：Nasdaq 财报 API / 美联储 FOMC 页 / BEA 发布日程页 / ForexFactory 周历 JSON
  ↓ 与上一份 data.json 合并（财报按天替换、宏观按 (类型, 日期, 英文标题) 去重，已过去的保留 30 天）
  ↓ 写入 data.json，git commit + push
       ↓
GitHub Pages（index.html）
  ↓ 前端 fetch 同目录 data.json（每 10 分钟自动重读），倒计时在浏览器里计算
  ↓ 三个视图：本周概览 / 财报日历 / 宏观日历 + 右侧挂件
  ↓ kit 详情抽屉（#/item/co/<代码>、#/item/ev/<id>）+ 当天财报列表页（#/list/day/<美东日期>）
```

- 某个来源本次抓取失败时沿用上一次的数据，`sources[].ok=false`，页面上标注「旧数据」

---

## 数据来源

| 来源 | 方式 | 每次条数 / 范围 | 备注 |
|---|---|---|---|
| Nasdaq 财报日历 | 接口 `api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD` | 今天（美东）及往后 14 天（共 15 天）中的每个工作日各请求一次（周末跳过），4 线程并发 | 只保留市值 ≥ 10 亿美元或在关注列表里的公司；函数 `nasdaq_day()` / `earnings()` |
| [美联储官网](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | 网页解析（正则） | 页面上列出的所有年份 FOMC 会议 | 带 `*` 的会议标为「含经济预测与点阵图」；决议时间固定记为美东 14:00；函数 `fomc()` |
| [BEA 官网](https://www.bea.gov/news/schedule) | 网页解析（正则匹配表格行） | 页面上的全部发布日，只保留 GDP、个人收支（PCE）、国际贸易 3 类 | 函数 `bea()`；页面无时间时默认美东 08:30 |
| ForexFactory 周历 | 接口 `nfs.faireconomy.media/ff_calendar_thisweek.json` | 仅本周；只保留影响程度 High / Medium、且国家在 `COUNTRY_ZH` 内（USD CNY EUR GBP JPY CAD AUD NZD CHF All） | 带预期值、前值；函数 `week_events()` |

**配置位置**：
- 关注列表：`scraper.py` 的 `WATCHLIST`（代码 → 分组），见上文「关注列表」
- 抓取范围常量：`DAYS_AHEAD = 14`（财报往后看几天）、`KEEP_PAST = 30`（已过去事件保留天数）、`MIN_MCAP = 1e9`（财报市值门槛）
- 新增 / 删除来源：在 `scraper.py` 写一个返回事件列表的函数，然后在 `main()` 的线程池里 `pool.submit(run, "名称", fn)`，并加进宏观合并循环 `(("fomc", …), ("bea", …), ("week", …))`；删除来源则去掉对应 submit 与循环项
- BEA 关注的报告：`BEA_ZH` 列表（英文标题关键词 → 中文名）

**限制**：
- 只有美股财报，港股暂无免费稳定的数据源
- BLS（CPI、非农的官方日程）拒绝程序访问，这些指标只能在当周通过 ForexFactory 拿到；爬虫每次运行都会把本周事件累积保存，过去的事件会保留
- 财报只保存市值 ≥ 10 亿美元的公司（关注列表不受限），控制文件大小

---

## 数据处理规则

- **财报过滤**（`nasdaq_day()`）：`symbol` 在 `WATCHLIST` 里，或 `marketCap` 解析后 ≥ `MIN_MCAP`（10 亿美元）才保留；`money()` 去掉 `$`、逗号等非数字字符，解析失败记为 `None`
- **盘前 / 盘后识别**（`TIME_MAP`）：`time-pre-market` → `bmo`（盘前），`time-after-hours` → `amc`（盘后），其他 → `tbd`（时间未定）
- **财报合并**（`main()`）：本次抓到的日期（以及抓取成功时今天起 15 天内的所有日期）整天替换，其余日期沿用上一份；只保留美东日期 ≥ 今天 − 30 天；排序：日期升序、同日按市值降序
- **FOMC 解析**（`fomc()`）：按 `(\d{4}) FOMC Meetings` 切分年份段，正则取 `fomc-meeting__month` / `fomc-meeting__date`；跨月会议（如 `Apr/May 30-1`）取最后一个月、最后一天作为决议日；日期中带 `*` 表示含 SEP（点阵图）
- **BEA 过滤与命名**（`bea()` / `bea_title()`）：
  - 只认标题含 `GDP`、`Personal Income and Outlays`、`International Trade in Goods and Services` 的行
  - 排除地区 / 行业统计：正则 `\bby (County|State|Industry|Metropolitan)`
  - 页面不写年份：月份比当前月早 2 个月以上的视为明年
  - 重要度：标题含 GDP 或 Personal Income → `High`，其他 → `Medium`
  - 标题转中文：`GDP (Advance Estimate), 3rd Quarter 2026` → `GDP 初值（2026Q3）`（Advance/Second/Third → 初值/修正值/终值；月份周期转为「2026 年 9 月」）
- **ForexFactory 过滤与翻译**（`week_events()`）：`impact` 只保留 High / Medium；`country` 必须在 `COUNTRY_ZH`；美国指标按 `EVENT_ZH` 翻译成中文（如 `Non-Farm Employment Change` → 非农就业人数、`Core PCE Price Index m/m` → 核心 PCE 物价指数月率），非美国或未收录的保留英文
- **时区**：所有 `date` 统一为美东日期（与美股交易日一致，用于分组）；`time` 存北京时间 ISO（`et_iso()` 把美东时间转 +08:00）
- **宏观去重与改期处理**（`main()`）：按 `(kind, date, title_en)` 作 key，新数据覆盖旧数据；FOMC、BEA 抓取成功时，先删掉该类型中今天及以后的旧事件再写入（避免改期后残留旧日期），已过去的保留；ForexFactory 周历只增不删，靠每周累积留存历史；最终只保留 ≥ 今天 − 30 天，按 `time` 排序
- **失败兜底**（`run()` / `source()`）：单个来源异常时记录错误（截断 200 字），`count` 和 `updated` 沿用上次成功值

---

## 数据结构

`data.json` 顶层：

```
{
  "updated":   "2026-10-22T09:19:41+08:00",  // 北京时间，每次运行都变（心跳）
  "today_et":  "2026-10-21",                 // 运行时的美东日期
  "watchlist": { "AAPL": "Mag 7", ... },     // 即 WATCHLIST
  "sources":   [ ... ],                      // 4 个来源状态
  "earnings":  [ ... ],                      // 财报
  "macro":     [ ... ]                       // 宏观事件
}
```

`sources` 单条：

```
{ "id": "nasdaq", "name": "Nasdaq 财报日历", "ok": true, "error": "", "count": 1458, "updated": "2026-10-22T09:19:41+08:00" }
```

id 取值：`nasdaq` / `fomc` / `bea` / `week`。

`earnings` 单条：

```
{
  "date":   "2026-10-20",      // 美东财报日
  "symbol": "GE",
  "name":   "GE Aerospace",
  "time":   "bmo",             // bmo 盘前 / amc 盘后 / tbd 未定
  "mcap":   322972451000.0,    // 市值（美元），缺失为 null
  "eps_fc": "$2.02",           // EPS 预期
  "eps_ly": "$1.66",           // 去年同期 EPS
  "ests":   "7",               // 分析师数
  "fq":     "Sep/2026",        // 财季
  "watch":  ""                 // 关注分组名，不在关注列表为空
}
```

`macro` 单条：

```
{
  "kind":     "week",                         // fomc / bea / week
  "country":  "CAD",
  "impact":   "High",                         // High / Medium
  "title":    "CPI m/m",                      // 中文名（无翻译时为英文）
  "title_en": "CPI m/m",
  "time":     "2026-10-19T20:30+08:00",       // 北京时间
  "date":     "2026-10-19",                   // 美东日期
  "forecast": "0.2%",                         // 仅 week 类有
  "previous": "-0.1%",                        // 仅 week 类有
  "url":      "https://www.forexfactory.com/calendar"
}
```

本项目只有 `data.json` 一个数据文件，无其他 json / ics / 快照 / 历史文件。

---

## 前端

**详情抽屉 + 列表页（通用组件 kit）**：电脑上从右侧滑出，手机上从底部升起；地址写在 hash 里（`#/item/<类型>/<id>`、`#/list/<key>`），分享链接可直接打开对应详情；条目已不在当前数据里（已过期、被清理或旧链接）时弹出「这条内容已不在当前数据里」提示，并提供「回到首页」。

列表页是新开的一层：从右侧滑入盖在首页上，返回时滑走；首页一直在底下不动，滚动位置不变。在列表里点开的详情盖在这一层之上；直接打开列表链接时不播进场动画；安卓手机可从左边缘右滑返回（iOS 用系统自带手势）。

| 地址 | 内容 |
|---|---|
| `#/item/co/<股票代码>` | 公司财报详情：EPS 预期 / 去年同期 / 预期同比、市值、分析师数、财季；同一天同时段发布的大公司、该公司其它财报日；跳 Nasdaq 财报页。同代码多条时取最近一次未发布的 |
| `#/item/ev/<id>` | 宏观事件详情：北京时间、倒计时或「已发布」、预期值 / 前值、同一天其它事件、同一指标的其它日期（FOMC 显示其它 FOMC 日程）。id 由前端 `prepare()` 生成：`<美东日期>-<hash(kind+country+title_en)>` |
| `#/list/day/<美东日期>` | 当天全部财报列表页，支持 `?time=bmo\|amc\|tbd`、`cap=watch\|1e11\|1e10`、`sort=cap\|ests\|eps\|sym`，附前后几天快速切换，每页 30 条「加载更多」 |

**项目特有功能**：
- 三个视图 `#week` / `#earnings` / `#macro`，选择记在 localStorage（前缀 `mc.`）
- 本周概览每天最多列 12 家财报（`DAY_TOP`），财报日历每天先列 15 家（`ER_TOP`），其余点「查看当天全部」进列表页
- 市值门槛筛选：只看关注 / ≥ 1000 亿 / ≥ 100 亿 / ≥ 10 亿美元（关注公司始终显示）；宏观按地区：美国 / 全球
- 公司 logo 取自 financialmodelingprep 图片地址，加载失败显示首字母
- 每 10 分钟自动重新读取 data.json；深浅色主题切换

---

## 本地运行

```
python3 scraper.py          # 只用标准库（需 Python 3.9+，用到 zoneinfo；CI 用 3.12）
python3 -m http.server      # 打开 http://localhost:8000
```

- 依赖：无第三方依赖
- 环境变量：无（不需要任何密钥）

---

## 自动更新机制

| 触发方式 | 时机 |
|---|---|
| GitHub Actions 定时任务（cron `0 23 * * *` UTC） | 每天 07:00 北京时间（美股收盘后） |
| push 到 main 且修改了 `scraper.py` 或 `.github/workflows/scrape.yml` | 推送后立即运行 |
| GitHub Actions 手动 dispatch（页面右上角 ⚡ 可跳转） | 按需触发 |

- 运行流程：`actions/checkout@v4` → `setup-python@v5`（3.12）→ `python scraper.py` → 提交 `data.json`（提交信息 `data: update <北京时间>`）→ push；`concurrency: scrape` 保证不会并发运行
- **心跳**：`data.json` 的 `updated` 字段每次运行都会变，因此每次都有提交，仓库保持活跃
- GitHub 规定仓库 60 天无提交会自动停用定时任务；有上面的心跳提交一般不会触发，万一被停用，需到 Actions 页面手动重新启用
