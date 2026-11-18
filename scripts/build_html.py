#!/usr/bin/env python3
"""把 data/*.json 渲染成单文件首页 index.html。

用法：
    python3 scripts/build_html.py

产物是自包含 HTML（内联 CSS/JS，无外部依赖），双击即可打开，也能直接托管。
"""

import datetime
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "index.html"

TIERS = ["主投", "冲刺", "备选", "排除"]
TIER_CLASS = {"主投": "t0", "冲刺": "t1", "备选": "t2", "排除": "t3"}
TIER_HINT = {
    "主投": "年限与技能双匹配，优先投、优先准备",
    "冲刺": "方向有吸引力，但存在明确缺口或不确定性",
    "备选": "年限偏低或规模偏小，用于练兵与兜底",
    "排除": "不符合当前条件，仅保留记录避免重复检索",
}

CSS = """
:root{
  --bg:#f6f7f9; --card:#ffffff; --ink:#14181f; --muted:#667085;
  --line:#e5e7eb; --soft:#f2f4f7;
  --brand:#2563eb; --t0:#047857; --t1:#b45309; --t2:#475569; --t3:#b91c1c;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.1);
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0d1017; --card:#151a23; --ink:#e8ecf3; --muted:#98a2b3;
    --line:#242b36; --soft:#1b212c; --shadow:0 1px 3px rgba(0,0,0,.5);
    --brand:#60a5fa; --t0:#34d399; --t1:#fbbf24; --t2:#94a3b8; --t3:#f87171;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}

/* hero */
.hero{padding:56px 0 28px;border-bottom:1px solid var(--line);background:var(--card)}
.eyebrow{font-size:11px;letter-spacing:.18em;color:var(--muted);font-weight:600;text-transform:uppercase}
h1{margin:12px 0 8px;font-size:34px;line-height:1.25;letter-spacing:-.02em}
.lede{margin:0;color:var(--muted);font-size:15px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.chip{font-size:12px;padding:4px 10px;border-radius:999px;background:var(--soft);color:var(--muted);border:1px solid var(--line)}
.chip b{color:var(--ink);font-weight:600}

/* stats */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin:26px 0 0}
.stat{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat .n{font-size:26px;font-weight:700;line-height:1.1;letter-spacing:-.02em}
.stat .l{font-size:12px;color:var(--muted);margin-top:2px}
.stat.t0 .n{color:var(--t0)} .stat.t1 .n{color:var(--t1)}
.stat.t2 .n{color:var(--t2)} .stat.t3 .n{color:var(--t3)}

/* tabs */
nav.tabs{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--line)}
.tabbar{display:flex;gap:4px;padding:0}
.tabbar button{
  appearance:none;background:none;border:0;border-bottom:2px solid transparent;
  padding:14px 18px;font:inherit;font-weight:600;color:var(--muted);cursor:pointer;
}
.tabbar button:hover{color:var(--ink)}
.tabbar button.active{color:var(--brand);border-bottom-color:var(--brand)}

main{padding:28px 0 80px}
section[hidden]{display:none}

/* toolbar */
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:18px}
input[type=search]{
  flex:1;min-width:220px;padding:9px 12px;border-radius:9px;border:1px solid var(--line);
  background:var(--card);color:var(--ink);font:inherit;
}
input[type=search]:focus{outline:2px solid var(--brand);outline-offset:-1px;border-color:transparent}
.fbtn{
  padding:7px 13px;border-radius:999px;border:1px solid var(--line);background:var(--card);
  color:var(--muted);font:inherit;font-size:13px;cursor:pointer;
}
.fbtn:hover{border-color:var(--muted)}
.fbtn.active{background:var(--ink);color:var(--card);border-color:var(--ink);font-weight:600}
.toggle{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
.count{font-size:13px;color:var(--muted);margin-left:auto}

/* job cards */
.job{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:10px;box-shadow:var(--shadow);overflow:hidden}
.job-head{display:flex;gap:14px;align-items:flex-start;padding:14px 16px}
.job-idx{font-variant-numeric:tabular-nums;font-size:12px;color:var(--muted);font-weight:600;padding-top:3px;min-width:22px}
.job-main{flex:1;min-width:0}
.job-title{font-weight:650;font-size:15.5px;line-height:1.4}
.job-title .co{color:var(--ink)}
.job-title .sep{color:var(--muted);margin:0 7px;font-weight:400}
.job-title .role{color:var(--muted);font-weight:500}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}
.tag{font-size:11.5px;padding:2px 8px;border-radius:6px;background:var(--soft);color:var(--muted);border:1px solid var(--line);white-space:nowrap}
.tag.t0{color:var(--t0);border-color:var(--t0)}
.tag.t1{color:var(--t1);border-color:var(--t1)}
.tag.t2{color:var(--t2);border-color:var(--t2)}
.tag.t3{color:var(--t3);border-color:var(--t3)}
.tag.go{font-weight:600}
.btn{
  flex:none;font-size:12.5px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);
  color:var(--brand);background:var(--bg);white-space:nowrap;
}
.btn:hover{text-decoration:none;border-color:var(--brand)}
details{border-top:1px solid var(--line);background:var(--bg)}
details summary{
  cursor:pointer;padding:9px 16px;font-size:12.5px;color:var(--muted);list-style:none;user-select:none;transition:color .15s;
}
details summary::-webkit-details-marker{display:none}
details summary::before{content:"▸ ";color:var(--muted)}
details[open] summary::before{content:"▾ "}
details .t-close{display:none}
details[open] .t-open{display:none}
details[open] .t-close{display:inline}
details summary:hover{color:var(--ink)}
.dbody{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:4px 16px 18px}
@media (max-width:800px){.dbody{grid-template-columns:1fr}}
.dbody h4{margin:12px 0 6px;font-size:12px;letter-spacing:.08em;color:var(--muted);text-transform:uppercase;font-weight:700}
.dbody h4:first-child{margin-top:0}
.dbody ol,.dbody ul{margin:0;padding-left:18px}
.dbody li{margin:3px 0}
.dbody p{margin:0}
.gap{color:var(--t1);font-size:14px}
.excluded{opacity:.85}
.excluded .reason{font-size:13.5px;color:var(--t3);margin-top:6px}

/* refine module */
h2.sec{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:38px 0 14px;font-weight:700}
h2.sec:first-child{margin-top:0}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;box-shadow:var(--shadow)}
.bars{display:grid;gap:9px}
.bar{display:grid;grid-template-columns:132px 1fr 42px;gap:12px;align-items:center;font-size:13.5px}
.bar .track{display:block;height:10px;border-radius:999px;background:var(--soft);overflow:hidden}
.bar .fill{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--brand),color-mix(in srgb,var(--brand) 55%,#a855f7))}
.bar .v{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.bar .lbl{color:var(--ink)}
.layers{display:grid;gap:10px}
.layer{display:grid;grid-template-columns:120px 1fr;gap:14px;padding:11px 0;border-bottom:1px dashed var(--line)}
.layer:last-child{border-bottom:0}
.layer .k{font-weight:650;font-size:13.5px;color:var(--brand)}
.layer .v{font-size:13.5px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.refine{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:var(--shadow)}
.refine h3{margin:0;font-size:15px;line-height:1.4}
.refine .meta{font-size:12.5px;color:var(--muted);margin:5px 0 12px}
.rblock{margin-top:11px}
.rblock .lbl{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:3px}
.rblock p{margin:0;font-size:13.5px;line-height:1.6}
.rblock.gap p{color:var(--t1)}
.notes{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.note-card{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--brand);border-radius:10px;padding:14px 16px}
.note-card h4{margin:0 0 6px;font-size:14px}
.note-card p{margin:0;font-size:13.5px;color:var(--muted)}
footer{border-top:1px solid var(--line);padding:26px 0 40px;color:var(--muted);font-size:12.5px;background:var(--card)}
.empty{padding:40px;text-align:center;color:var(--muted)}
"""

JS = """
const tabs=[...document.querySelectorAll('.tabbar button')];
const secs={list:document.getElementById('tab-list'),req:document.getElementById('tab-req')};
function showTab(name,scroll){
  const b=tabs.find(x=>x.dataset.tab===name)||tabs[0];
  tabs.forEach(x=>x.classList.toggle('active',x===b));
  Object.entries(secs).forEach(([k,el])=>el.hidden=(k!==b.dataset.tab));
  if(scroll) window.scrollTo({top:0,behavior:'instant'});
}
tabs.forEach(b=>b.addEventListener('click',()=>{
  showTab(b.dataset.tab,true);
  history.replaceState(null,'','#'+b.dataset.tab);
}));
showTab((location.hash||'').replace('#','')==='req'?'req':'list',false);

const q=document.getElementById('q');
const goOnly=document.getElementById('goOnly');
const fbtns=[...document.querySelectorAll('.fbtn')];
const jobs=[...document.querySelectorAll('.job')];
const count=document.getElementById('count');
let tier='全部';
function apply(){
  const kw=(q.value||'').trim().toLowerCase();
  let n=0;
  jobs.forEach(el=>{
    const okTier = tier==='全部' || el.dataset.tier===tier;
    const okGo = !goOnly.checked || Number(el.dataset.go)>=3;
    const okKw = !kw || (el.dataset.search||'').includes(kw);
    const show = okTier && okGo && okKw;
    el.style.display = show?'':'none';
    if(show) n++;
  });
  count.textContent = `显示 ${n} / ${jobs.length} 个岗位`;
}
fbtns.forEach(b=>b.addEventListener('click',()=>{
  fbtns.forEach(x=>x.classList.toggle('active',x===b));
  tier=b.dataset.tier; apply();
}));
q.addEventListener('input',apply);
goOnly.addEventListener('change',apply);
apply();
"""


def esc(value):
    return html.escape(str(value if value is not None else ""))


def load(name):
    with open(DATA / name, encoding="utf-8") as fh:
        return json.load(fh)


def badge(text, cls=""):
    return '<span class="tag %s">%s</span>' % (cls, esc(text))


def job_card(idx, job):
    tier = job.get("tier", "")
    jd = job.get("source_url") or ""
    go_stars = job.get("go_fit") or ""
    go_num = go_stars.count("★")
    search_blob = " ".join(
        str(job.get(k, "")) for k in ("company", "title", "band", "languages", "source_name")
    ).lower()

    parts = ['<article class="job" data-tier="%s" data-go="%d" data-search="%s">' % (esc(tier), go_num, esc(search_blob))]
    parts.append('<div class="job-head">')
    parts.append('<div class="job-idx">%02d</div>' % idx)
    parts.append('<div class="job-main">')
    parts.append(
        '<div class="job-title"><span class="co">%s</span><span class="sep">/</span><span class="role">%s</span></div>'
        % (esc(job.get("company")), esc(job.get("title")))
    )
    badges = [badge(tier, TIER_CLASS.get(tier, ""))]
    if job.get("band"):
        badges.append(badge(job["band"]))
    if job.get("languages"):
        badges.append(badge(job["languages"]))
    if go_stars:
        badges.append(badge("Go " + go_stars, "go"))
    if job.get("salary"):
        badges.append(badge(job["salary"]))
    if job.get("source_level"):
        badges.append(badge("%s 级来源" % job["source_level"]))
    if job.get("jd_verified") and job["jd_verified"] != "full":
        badges.append(badge("JD %s" % {"partial": "部分", "none": "未获取"}.get(job["jd_verified"], job["jd_verified"])))
    parts.append('<div class="badges">%s</div>' % "".join(badges))
    parts.append("</div>")
    if jd:
        parts.append('<a class="btn" href="%s" target="_blank" rel="noopener">JD ↗</a>' % esc(jd))
    parts.append("</div>")

    if tier == "排除":
        parts.append('<div class="job-head excluded"><div class="job-idx"></div><div class="job-main"><div class="reason">排除原因：%s</div></div></div>' % esc(job.get("exclude_reason")))
        parts.append("</article>")
        return "".join(parts)

    duties = job.get("duties") or []
    must = job.get("must") or []
    plus = job.get("plus") or []
    if duties or must or plus:
        parts.append("<details><summary><span class='t-open'>展开岗位职责与要求</span><span class='t-close'>收起</span></summary><div class='dbody'>")
        left = ["<h4>岗位职责</h4><ol>"]
        for item in duties:
            left.append("<li>%s</li>" % esc(item))
        left.append("</ol>")
        parts.append('<div class="dcol">%s</div>' % "".join(left))

        right = []
        if must:
            right.append("<h4>硬性要求</h4><ul>")
            for item in must:
                right.append("<li>%s</li>" % esc(item))
            right.append("</ul>")
        if plus:
            right.append("<h4>加分项</h4><ul>")
            for item in plus:
                right.append("<li>%s</li>" % esc(item))
            right.append("</ul>")
        if job.get("gap"):
            right.append('<h4>你的差距</h4><p class="gap">%s</p>' % esc(job["gap"]))
        parts.append('<div class="dcol">%s</div>' % "".join(right))
        parts.append("</div></details>")
    parts.append("</article>")
    return "".join(parts)


def refine_card(job):
    tier = job.get("tier", "")
    duties = job.get("duties") or []
    must = job.get("must") or []
    core = "；".join(duties[:2]) if duties else "—"
    if len(core) > 180:
        core = core[:180] + "…"
    gate = " · ".join(must[:4]) if must else "JD 未获取"
    if len(gate) > 150:
        gate = gate[:150] + "…"
    return (
        '<div class="refine">'
        '<h3>%s · %s</h3>'
        '<div class="meta">%s · %s · Go %s%s</div>'
        '<div class="rblock"><span class="lbl">核心职责</span><p>%s</p></div>'
        '<div class="rblock"><span class="lbl">硬性门槛</span><p>%s</p></div>'
        '<div class="rblock gap"><span class="lbl">你的差距</span><p>%s</p></div>'
        "</div>"
    ) % (
        esc(job.get("company")),
        esc(job.get("title")),
        esc(tier),
        esc(job.get("band") or "—"),
        esc(job.get("go_fit") or "—"),
        (" · " + esc(job["salary"])) if job.get("salary") else "",
        esc(core),
        esc(gate),
        esc(job.get("gap") or "—"),
    )


def main():
    jobs_doc = load("jobs.json")
    apps_doc = load("applications.json")
    meta = jobs_doc.get("meta", {})
    jobs = jobs_doc.get("jobs", [])
    apps = apps_doc.get("applications", [])

    grouped = {t: [j for j in jobs if j.get("tier") == t] for t in TIERS}
    actionable = grouped["主投"] + grouped["冲刺"] + grouped["备选"]

    from collections import Counter

    sig = Counter()
    for job in actionable:
        for s in job.get("signals") or []:
            sig[s] += 1
    max_sig = max(sig.values()) if sig else 1

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    page = ['<!doctype html><html lang="zh-CN"><head>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            "<title>%s</title>" % esc(meta.get("title", "岗位池")),
            "<style>%s</style></head><body>" % CSS]

    # hero
    page.append('<header class="hero"><div class="wrap">')
    page.append('<div class="eyebrow">Career Search · Shanghai · Backend</div>')
    page.append("<h1>%s</h1>" % esc(meta.get("title")))
    page.append('<p class="lede">%s</p>' % esc(meta.get("owner_note")))
    page.append('<div class="chips">')
    page.append('<span class="chip">核验日期 <b>%s</b></span>' % esc(meta.get("verified_at")))
    page.append('<span class="chip">城市 <b>%s</b></span>' % esc(meta.get("city")))
    page.append('<span class="chip">可投 <b>%d</b> 个</span>' % len(actionable))
    page.append('<span class="chip">已排除 <b>%d</b> 个</span>' % len(grouped["排除"]))
    page.append("</div>")
    page.append('<div class="stats">')
    for t in TIERS:
        page.append('<div class="stat %s"><div class="n">%d</div><div class="l">%s</div></div>' % (TIER_CLASS[t], len(grouped[t]), t))
    page.append("</div></div></header>")

    # tabs
    page.append('<nav class="tabs"><div class="wrap"><div class="tabbar">')
    page.append('<button class="active" data-tab="list">① 职位列表</button>')
    page.append('<button data-tab="req">② 岗位要求提炼</button>')
    page.append("</div></div></nav><main>")

    # module 1
    page.append('<section id="tab-list"><div class="wrap">')
    page.append('<div class="toolbar">')
    page.append('<input id="q" type="search" placeholder="搜索公司 / 岗位 / 语言…">')
    page.append('<button class="fbtn active" data-tier="全部">全部</button>')
    for t in TIERS:
        page.append('<button class="fbtn" data-tier="%s">%s</button>' % (esc(t), esc(t)))
    page.append('<label class="toggle"><input id="goOnly" type="checkbox"> 只看 Go ★★★</label>')
    page.append('<span class="count" id="count"></span>')
    page.append("</div>")

    idx = 0
    for t in TIERS:
        if not grouped[t]:
            continue
        page.append('<h2 class="sec">%s · %d <span style="font-weight:400;text-transform:none;letter-spacing:0">— %s</span></h2>'
                    % (esc(t), len(grouped[t]), esc(TIER_HINT[t])))
        for job in grouped[t]:
            idx += 1
            page.append(job_card(idx, job))
    page.append("</div></section>")

    # module 2
    page.append('<section id="tab-req" hidden><div class="wrap">')

    page.append('<h2 class="sec">硬性要求出现频次（%d 个可投岗位样本）</h2>' % len(actionable))
    page.append('<div class="panel"><div class="bars">')
    for name, n in sig.most_common():
        width = round(n / max_sig * 100)
        page.append('<div class="bar"><span class="lbl">%s</span><span class="track"><span class="fill" style="width:%d%%"></span></span><span class="v">%d</span></div>' % (esc(name), width, n))
    page.append("</div></div>")

    page.append('<h2 class="sec">能力分层地图</h2>')
    layers = [
        ("基础层", "语言功底（Go 并发模型 / GC / 调度）、系统与网络、数据结构与算法、Linux 排障"),
        ("中间件层", "MySQL 索引与 SQL 调优、Redis 缓存设计、消息队列（Kafka / RocketMQ）、连接与线程模型"),
        ("架构层", "高并发与容量规划、分布式事务与一致性、服务治理（限流 / 熔断 / 降级）、可观测性"),
        ("领域层", "电商交易 / 支付 / 营销 / IM / 游戏服务端 —— 决定你能否过筛的第一权重"),
        ("新变量层", "K8s 与云原生编排、LLM 工程化（RAG / Agent / 工具调用）、AI 辅助研发"),
    ]
    page.append('<div class="panel"><div class="layers">')
    for k, v in layers:
        page.append('<div class="layer"><span class="k">%s</span><span class="v">%s</span></div>' % (esc(k), esc(v)))
    page.append("</div></div>")

    page.append('<h2 class="sec">三条判断</h2>')
    notes = [
        ("Go 不是门槛，是被当作加分", "12 个可投岗位里 9 个明写 Go；但真正卡人的是「有没有一个 3 年以上的深度领域」，栈可以换，领域换不了。"),
        ("最大缺口是 K8s 与 LLM 工程化", "K8s 只在 3 个岗位出现，但其中 2 个是主投；LLM 工程化出现 5 次，是 2026 年新增的通用加分项。"),
        ("3-5 年带是甜点区，5 年+ 是陷阱", "4 年投 5 年+ 岗会被压职级；投 2 年+ 岗会被判 overqualified。3 年+ / 3-5 年 才是最优区间。"),
    ]
    page.append('<div class="notes">')
    for h, p in notes:
        page.append('<div class="note-card"><h4>%s</h4><p>%s</p></div>' % (esc(h), esc(p)))
    page.append("</div>")

    page.append('<h2 class="sec">逐岗位要求提炼</h2>')
    page.append('<div class="grid2">')
    for job in actionable:
        page.append(refine_card(job))
    page.append("</div>")

    page.append("</div></section></main>")

    # footer
    page.append('<footer><div class="wrap">')
    page.append("%d 个岗位 · %d 条投递记录 · 生成于 %s<br>" % (len(jobs), len(apps), esc(now)))
    page.append("数据源 <code>data/jobs.json</code> · 由 <code>scripts/build_html.py</code> 生成，请勿手改本文件")
    page.append("</div></footer>")
    page.append("<script>%s</script></body></html>" % JS)

    OUT.write_text("".join(page), encoding="utf-8")
    print("wrote %s (%d jobs, %d actionable)" % (OUT, len(jobs), len(actionable)))


if __name__ == "__main__":
    main()