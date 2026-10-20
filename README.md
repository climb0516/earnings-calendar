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

## 数据来源

| 来源 | 内容 |
|---|---|
| Nasdaq 财报日历 API | 美股每日财报公司、盘前盘后、市值、EPS 预期 |
| [美联储官网](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | FOMC 议息全年日程 |
| [BEA 官网](https://www.bea.gov/news/schedule) | GDP、个人收支（PCE）、国际贸易发布日 |
| ForexFactory 周历 | 本周全球宏观事件（CPI、非农、PMI 等），带影响程度、预期值、前值 |

**限制**：
- 只有美股财报，港股暂无免费稳定的数据源
- BLS（CPI、非农的官方日程）拒绝程序访问，这些指标只能在当周通过 ForexFactory 拿到；爬虫每次运行都会把本周事件累积保存，过去的事件会保留
- 财报只保存市值 ≥ 10 亿美元的公司（关注列表不受限），控制文件大小

---

## 技术架构

```
GitHub Actions（每天北京时间 07:00 / 手动 / 修改爬虫后 push）
  ↓ python scraper.py（只用标准库，无需安装依赖）
  ↓ 并发抓取 4 个来源 → 与上一份 data.json 合并（已过去的事件保留 30 天）
  ↓ 写入 data.json 并 commit
       ↓
GitHub Pages（index.html）
  ↓ 前端读取同目录 data.json 渲染，倒计时在浏览器里实时计算
```

- 某个来源本次抓取失败时沿用上一次的数据，页面上标注「旧数据」
- 每次运行都会产生提交，仓库保持活跃，定时任务不会因 60 天无活动被 GitHub 停用

本地预览：

```
python3 scraper.py
python3 -m http.server
```
