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
import re
import sys

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
.flash{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;box-shadow:var(--shadow)}
.flash-top{display:flex;align-items:center;gap:12px;font-size:12.5px;color:var(--muted);margin-bottom:12px}
.fbar{flex:1;height:6px;background:var(--soft);border-radius:999px;overflow:hidden}
.fbar i{display:block;height:100%;background:var(--brand);width:0;transition:width .25s}
.flash-card{border:1px solid var(--line);border-radius:10px;padding:22px 24px;background:var(--bg);min-height:150px}
.f-cat{font-size:11px;letter-spacing:.06em;color:var(--muted);text-transform:none;margin-bottom:10px}
.f-q{font-size:16.5px;font-weight:650;line-height:1.55}
.f-a{margin-top:14px;padding-top:14px;border-top:1px dashed var(--line);font-size:14px;line-height:1.75;color:var(--ink)}
.flash-actions{display:flex;gap:10px;margin-top:14px}
.flash-actions button{padding:8px 16px;border-radius:9px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-size:13.5px;cursor:pointer}
.flash-actions .btn-primary{background:var(--brand);color:#fff;border-color:var(--brand);font-weight:600}
.flash-actions .btn-ok{color:var(--t0);border-color:var(--t0);font-weight:600}
.flash-actions .btn-ghost{color:var(--muted)}
.flash-opts{display:flex;justify-content:space-between;align-items:center;margin-top:12px}
.btn-link{background:none;border:0;color:var(--muted);font:inherit;font-size:12.5px;cursor:pointer;text-decoration:underline}
.ladder{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.lad-item{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow)}
.lad-top{display:flex;align-items:center;gap:8px;margin-bottom:5px}
.lad-id{font-size:11px;font-weight:700;color:#fff;background:var(--brand);border-radius:5px;padding:1px 7px}
.lad-nm{font-weight:650;font-size:14px}
.lad-item p{margin:0;font-size:12.5px;color:var(--muted);line-height:1.6}
.panel.topic{margin-bottom:10px}
.panel.topic h4{margin:0 0 8px;font-size:14px;color:var(--brand)}
.panel.topic ul{margin:0;padding-left:18px}
.panel.topic li{margin:4px 0;font-size:13.5px;line-height:1.65}
.arts{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.art{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
  text-decoration:none;color:inherit;box-shadow:var(--shadow);transition:border-color .15s}
.art:hover{border-color:var(--brand);text-decoration:none}
.art-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.art-lv{font-size:11px;font-weight:700;padding:1px 7px;border-radius:5px;background:var(--soft);color:var(--muted);border:1px solid var(--line)}
.art-lang{font-size:11px;color:var(--muted)}
.art-px{color:var(--t1)}
.art h5{margin:0 0 4px;font-size:14.5px;line-height:1.4}
.art-au{font-size:12px;color:var(--brand);margin-bottom:6px}
.art p{margin:0;font-size:12.5px;color:var(--muted);line-height:1.6}
ul.src{margin:0;padding-left:18px}
ul.src li{margin:4px 0;font-size:13px;line-height:1.6}
.checks{display:grid;gap:7px}
.chk{display:flex;gap:9px;align-items:flex-start;font-size:13.5px;line-height:1.55;cursor:pointer}
.chk input{margin-top:3px}
.chk-progress{margin-top:12px;font-size:12.5px;color:var(--muted)}
details.qa{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px 14px;margin-bottom:7px}
details.qa summary{cursor:pointer;font-size:13.5px;font-weight:600}
details.qa p{margin:8px 0 0;font-size:13px;color:var(--muted);line-height:1.65}
.roadmap{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.rm{background:var(--card);border:1px dashed var(--line);border-radius:10px;padding:12px 14px}
.rm-s{font-size:10.5px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:1px 7px}
.rm b{display:block;margin:6px 0 3px;font-size:13.5px}
.rm p{margin:0;font-size:12.5px;color:var(--muted);line-height:1.55}
.subsec{margin:26px 0 10px;font-size:15px;font-weight:650}
.subsec span{font-weight:400;font-size:12.5px;color:var(--muted);margin-left:8px}
table.algo{width:100%;border-collapse:collapse;font-size:13px}
table.algo th{text-align:left;font-size:11.5px;letter-spacing:.02em;color:var(--muted);
  font-weight:700;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
table.algo td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
table.algo tr:last-child td{border-bottom:0}
table.algo tbody tr:hover{background:var(--soft)}
table.algo .c{text-align:center}
table.algo .mono{font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}
table.algo .ttl{font-weight:600;min-width:150px}
table.algo .cat{color:var(--muted);white-space:nowrap;font-size:12.5px}
table.algo .pt{line-height:1.55}
table.algo .gh{color:var(--muted);font-size:12.5px;line-height:1.55;max-width:300px}
.fsel{padding:8px 10px;border-radius:9px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-size:13px}
.heat.mute{opacity:.45}
table.algo .gh{display:block;margin-top:3px;color:var(--muted);font-size:12px}
.heat{display:inline-block;min-width:26px;padding:1px 6px;border-radius:6px;background:var(--soft);
  color:var(--muted);font-size:11.5px;font-variant-numeric:tabular-nums}
.diff{display:inline-block;min-width:18px;padding:1px 6px;border-radius:5px;font-size:11.5px;font-weight:700;border:1px solid}
.d-e{color:#059669;border-color:#059669}
.d-m{color:#d97706;border-color:#d97706}
.d-h{color:#b91c1c;border-color:#b91c1c}
.d-x{color:var(--muted);border-color:var(--line)}
.hint{font-size:13px;color:var(--muted);margin:-4px 0 14px;line-height:1.6}
.hint b{color:var(--ink);font-weight:600}
.panel.tight{padding:6px 0;overflow-x:auto}
table.rank{width:100%;border-collapse:collapse;font-size:13.5px}
table.rank th{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
  font-weight:700;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
table.rank td{padding:9px 14px;border-bottom:1px solid var(--line);vertical-align:middle}
table.rank tr:last-child td{border-bottom:0}
table.rank tbody tr:hover{background:var(--soft)}
table.rank .c{text-align:center;color:var(--muted);font-variant-numeric:tabular-nums;width:44px}
table.rank .n{text-align:right;font-variant-numeric:tabular-nums;color:var(--muted);width:62px}
table.rank td.n{color:var(--ink)}
table.rank .sk{font-weight:650}
table.rank .cat{color:var(--muted);font-size:12.5px;white-space:nowrap}
table.rank .w{width:150px}
.mini{display:block;height:7px;border-radius:999px;background:var(--soft);overflow:hidden}
.mini i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--brand),color-mix(in srgb,var(--brand) 55%,#a855f7))}
table.rank td.dom{color:var(--muted);font-size:12.5px;line-height:1.5}
.lvl{display:inline-block;min-width:38px;text-align:center;font-size:11.5px;padding:2px 8px;border-radius:6px;border:1px solid var(--line);font-weight:600}
.lv3{color:#fff;background:var(--t0);border-color:var(--t0)}
.lv2{color:var(--ink);background:var(--soft)}
.lv1{color:var(--t1);border-color:var(--t1)}
.lv0{color:var(--t3);border-color:var(--t3);border-style:dashed}
.verdict{font-size:11.5px;padding:2px 9px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}
.v-must{color:var(--t0);border-color:var(--t0);font-weight:650}
.v-high{color:var(--brand);border-color:var(--brand)}
.v-mid{color:var(--muted)}
.v-low,.v-plus{color:var(--t2);border-style:dashed}
.cappool{display:flex;flex-wrap:wrap;gap:8px}
.cap{font-size:13px;padding:6px 12px;border-radius:8px;background:var(--soft);border:1px solid var(--line);font-weight:550}
.projs{display:grid;gap:14px}
.proj{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;box-shadow:var(--shadow)}
.proj-head{display:flex;align-items:baseline;gap:10px}
.proj-idx{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;font-weight:600}
.proj h3{margin:0;font-size:16.5px;letter-spacing:-.01em}
.proj-head{flex-wrap:wrap}
.prov{font-size:11px;padding:1px 8px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}
.prov-own{color:var(--t0);border-color:var(--t0)}
.prov-team{color:var(--t2);border-style:dashed}
.prov-core{color:var(--brand);border-color:var(--brand)}
.prov-bonus{color:var(--t1);border-color:var(--t1)}
.proj .tags{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0 4px}
.tag.tech{color:var(--brand);border-color:color-mix(in srgb,var(--brand) 40%,transparent)}
.pblock{margin-top:12px}
.pblock .lbl,.bullet .lbl{display:block;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:3px}
.pblock p{margin:0;font-size:14px;line-height:1.65}
.pblock ol{margin:0;padding-left:20px;font-size:14px;line-height:1.65}
.pblock ol li{margin:2px 0}
.pblock p.res{color:var(--t0);font-weight:550}
.bullet{margin-top:14px;padding:12px 14px;background:var(--bg);border:1px solid var(--line);border-left:3px solid var(--brand);border-radius:8px;position:relative}
.bullet p{margin:0;font-size:13.5px;line-height:1.7;padding-right:60px}
.bullet .copy{position:absolute;right:10px;top:10px;font-size:12px;padding:3px 10px;border-radius:6px;
  border:1px solid var(--line);background:var(--card);color:var(--brand);cursor:pointer}
.bullet .copy:hover{border-color:var(--brand)}
.empty{padding:40px;text-align:center;color:var(--muted)}
"""

JS = """
const tabs=[...document.querySelectorAll('.tabbar button')];
const secs={list:document.getElementById('tab-list'),req:document.getElementById('tab-req')};
const _rs=document.getElementById('tab-resume'); if(_rs) secs.resume=_rs;
const _al=document.getElementById('tab-algo'); if(_al) secs.algo=_al;
const _go=document.getElementById('tab-go'); if(_go) secs.go=_go;
function showTab(name,scroll){
  const b=tabs.find(x=>x.dataset.tab===name)||tabs[0];
  tabs.forEach(x=>x.classList.toggle('active',x===b));
  Object.entries(secs).forEach(([k,el])=>{ if(el) el.hidden=(k!==b.dataset.tab); });
  if(scroll) window.scrollTo({top:0,behavior:'instant'});
}
tabs.forEach(b=>b.addEventListener('click',()=>{
  showTab(b.dataset.tab,true);
  history.replaceState(null,'','#'+b.dataset.tab);
}));
const H=((location.hash||'').replace('#',''));
showTab(['list','req','algo','go','resume'].includes(H)?H:'list',false);

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

const aq=document.getElementById('aq');
const acat=document.getElementById('acat');
const ahot=document.getElementById('ahot');
const arows=[...document.querySelectorAll('.aprob')];
const acount=document.getElementById('acount');
function aapply(){
  const kw=(aq.value||'').trim().toLowerCase();
  const c=acat?acat.value:'全部';
  const onlyHot=ahot&&ahot.checked;
  let n=0;
  arows.forEach(el=>{
    const okC = c==='全部' || el.dataset.tier===c;
    const okK = !kw || (el.dataset.text||'').includes(kw);
    const okH = !onlyHot || el.dataset.hot==='1';
    const show = okC && okK && okH;
    el.style.display = show?'':'none';
    if(show) n++;
  });
  acount.textContent = `显示 ${n} / ${arows.length} 题`;
}
if(aq){ aq.addEventListener('input',aapply); }
if(acat){ acat.addEventListener('change',aapply); }
if(ahot){ ahot.addEventListener('change',aapply); }
aapply();

(function(){
  const el=document.getElementById('gmpCards');
  if(!el) return;
  const ALL=JSON.parse(el.textContent);
  const KEY='dsh.gmp.cards';
  const pos=document.getElementById('fPos'), fill=document.getElementById('fFill'),
        stat=document.getElementById('fStat'), cat=document.getElementById('fCat'),
        q=document.getElementById('fQ'), a=document.getElementById('fA'),
        card=document.getElementById('fCard');
  const onlyNew=document.getElementById('fOnlyNew');
  let known={};
  try{ known=JSON.parse(localStorage.getItem(KEY)||'{}'); }catch(e){ known={}; }
  let list=ALL.slice(), idx=0, shown=false;

  function rebuild(){
    list = onlyNew&&onlyNew.checked ? ALL.filter(c=>!known[c.id]) : ALL.slice();
    if(list.length===0){ list=ALL.slice(); if(onlyNew) onlyNew.checked=false; }
    idx=0; render();
  }
  function render(){
    if(list.length===0) return;
    const c=list[idx%list.length];
    cat.textContent=c.cat;
    q.textContent=c.q;
    a.textContent=c.a;
    a.hidden=true; shown=false;
    pos.textContent=`${(idx%list.length)+1} / ${list.length}`;
    const total=ALL.length, got=ALL.filter(x=>known[x.id]).length;
    fill.style.width=(got/total*100).toFixed(0)+'%';
    stat.textContent=`已掌握 ${got} / ${total}`;
    card.classList.remove('flip');
  }
  function next(){ idx++; render(); }
  document.getElementById('fShow').onclick=()=>{ a.hidden=false; shown=true; card.classList.add('flip'); };
  document.getElementById('fKnow').onclick=()=>{ const c=list[idx%list.length]; known[c.id]=1; save(); next(); };
  document.getElementById('fAgain').onclick=()=>{ const c=list[idx%list.length]; delete known[c.id]; save(); next(); };
  if(onlyNew) onlyNew.onchange=rebuild;
  const rs=document.getElementById('fReset');
  if(rs) rs.onclick=()=>{ known={}; save(); rebuild(); };
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(known)); }catch(e){} }
  render();
})();

(function(){
  const KEY='dsh.go.checklist';
  const boxes=[...document.querySelectorAll('#gocheck input[data-k]')];
  const prog=document.getElementById('goprog');
  let saved={};
  try{ saved=JSON.parse(localStorage.getItem(KEY)||'{}'); }catch(e){ saved={}; }
  boxes.forEach(b=>{ if(saved[b.dataset.k]) b.checked=true; });
  function upd(){
    const n=boxes.filter(b=>b.checked).length;
    if(prog) prog.textContent=`已完成 ${n} / ${boxes.length}`;
    const obj={}; boxes.forEach(b=>{ if(b.checked) obj[b.dataset.k]=1; });
    try{ localStorage.setItem(KEY,JSON.stringify(obj)); }catch(e){}
  }
  boxes.forEach(b=>b.addEventListener('change',upd));
  upd();
})();

document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{
  const t=b.dataset.text||'';
  (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{
    b.textContent='已复制';setTimeout(()=>b.textContent='复制',1500);
  }).catch(()=>{b.textContent='复制失败';setTimeout(()=>b.textContent='复制',1500);});
}));
"""


SKILL_DEFS = [
    ("Go", "语言", [r"\bgo\b", r"\bgolang\b"]),
    ("Java", "语言", [r"\bjava\b", r"\bjvm\b"]),
    ("C / C++", "语言", [r"\bc\+\+"]),
    ("Python", "语言", [r"\bpython\b"]),
    ("Node.js", "语言", [r"\bnode\.?js\b"]),
    ("TypeScript", "语言", [r"\btypescript\b"]),
    ("PHP", "语言", [r"\bphp\b"]),
    ("Linux", "基础", [r"\blinux\b"]),
    ("数据结构与算法", "基础", [r"数据结构"]),
    ("系统 / 网络 / 协议", "基础", [r"网络协议", r"计算机体系结构", r"操作系统", r"\bgrpc\b", r"\bsse\b", r"系统、网络"]),
    ("MySQL", "中间件", [r"\bmysql\b", r"\bsql\b"]),
    ("Redis", "中间件", [r"\bredis\b"]),
    ("消息队列", "中间件", [r"消息队列", r"\bmq\b", r"kafka", r"rocketmq"]),
    ("高并发", "架构", [r"高并发"]),
    ("分布式", "架构", [r"分布式"]),
    ("服务治理", "架构", [r"限流", r"熔断", r"降级", r"服务治理"]),
    ("可观测性 / 容灾", "架构", [r"可观测", r"\bslo\b", r"监控告警", r"容灾"]),
    ("性能调优", "架构", [r"性能调优", r"性能优化", r"压测"]),
    ("K8s / 云原生", "平台", [r"kubernetes", r"\bk8s\b", r"docker", r"云原生"]),
    ("LLM / Agent 工程化", "新变量", [r"大模型", r"\bllm\b", r"\bagent\b", r"\brag\b", r"prompt", r"\bmcp\b"]),
    ("AI 辅助研发", "新变量", [r"ai 辅助", r"ai 工具", r"与 ai 协作", r"ai 编程"]),
    ("领域：电商 / 交易", "领域", [r"电商", r"外卖", r"零售", r"团购", r"交易系统"]),
    ("领域：营销", "领域", [r"营销"]),
    ("领域：游戏服务端", "领域", [r"游戏服务端", r"游戏", r"\bmmo\b"]),
    ("领域：内容 / 社区", "领域", [r"内容安全", r"社区", r"短视频"]),
    ("领域：数据 / 数仓", "领域", [r"数仓", r"数据仓库", r"\bolap\b", r"大数据"]),
    ("领域：金融 / 支付", "领域", [r"支付", r"清结算", r"金融"]),
]

# 出现这些措辞说明是「多语言任选一」，语言类不计入硬性
PARALLEL = re.compile(r"至少一种|至少一门|任一|之中至少|包括但不限于|任选")


def _hit(patterns, text):
    text = (text or "").lower()
    return [p_ for p_ in patterns if re.search(p_, text)]


def extract_skills(job):
    """返回 {技能: 'must' | 'plus'}。语言类若处于「多语言任选」语境，降级为 plus。"""
    must_text = " ".join(job.get("must") or [])
    plus_text = " ".join(job.get("plus") or [])
    duty_text = " ".join(job.get("duties") or [])
    parallel = bool(PARALLEL.search(must_text))

    found = {}
    for name, cat, pats in SKILL_DEFS:
        in_must = bool(_hit(pats, must_text))
        in_duty = bool(_hit(pats, duty_text))
        in_plus = bool(_hit(pats, plus_text))
        if not (in_must or in_duty or in_plus):
            continue
        if in_must or in_duty:
            found[name] = "plus" if (cat == "语言" and parallel) else "must"
        else:
            found[name] = "plus"
    return found


def skill_ranking(jobs):
    """按出现广度排序：先总出现数，再硬性数。"""
    stats = {}
    for name, cat, _ in SKILL_DEFS:
        stats[name] = {"name": name, "cat": cat, "must": 0, "plus": 0, "jobs": []}
    for job in jobs:
        for name, kind in extract_skills(job).items():
            stats[name][kind] += 1
            stats[name]["jobs"].append(job.get("company"))
    rows = list(stats.values())
    for r in rows:
        r["total"] = r["must"] + r["plus"]
    rows.sort(key=lambda r: (r["total"], r["must"]), reverse=True)
    return [r for r in rows if r["total"] > 0]


def esc(value):
    return html.escape(str(value if value is not None else ""))


LV_LABEL = {3: "强", 2: "够用", 1: "薄弱", 0: "无"}


def lookup_level(levels, name):
    if not levels:
        return 2, ""
    item = levels.get(name)
    if isinstance(item, dict):
        return item.get("level", 2), item.get("note", "")
    if isinstance(item, int):
        return item, ""
    return 2, ""


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
    profile = load("profile.json")
    with_resume = "--with-resume" in sys.argv
    algo = load("algo.json")
    godoc = load("go.json")
    cards = load("gmp-cards.json")
    resume = load("resume.json") if (with_resume and (DATA / "resume.json").exists()) else {"projects": []}
    levels = profile.get("levels", {})
    meta = jobs_doc.get("meta", {})
    jobs = jobs_doc.get("jobs", [])
    apps = apps_doc.get("applications", [])

    prio = {a.get("job_id"): a.get("priority", 999) for a in apps}
    grouped = {t: sorted([j for j in jobs if j.get("tier") == t],
                         key=lambda x: (prio.get(x.get("id"), 999), x.get("id")))
               for t in TIERS}
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
    page.append('<span class="chip">基线 <b>%s</b></span>' % esc(profile.get("headline", "")))
    for t in profile.get("tags", []):
        page.append('<span class="chip">%s</span>' % esc(t))
    page.append("</div>")
    page.append('<div class="stats">')
    for t in TIERS:
        page.append('<div class="stat %s"><div class="n">%d</div><div class="l">%s</div></div>' % (TIER_CLASS[t], len(grouped[t]), t))
    page.append("</div></div></header>")

    # tabs
    page.append('<nav class="tabs"><div class="wrap"><div class="tabbar">')
    page.append('<button class="active" data-tab="list">① 职位列表</button>')
    page.append('<button data-tab="req">② 技能要求</button>')
    page.append('<button data-tab="algo">③ 算法专题</button>')
    page.append('<button data-tab="go">④ Go 深度</button>')
    if resume.get("projects"):
        page.append('<button data-tab="resume">⑤ 总简历能力池</button>')
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

    # module 2 —— 技能要求
    rank = skill_ranking(actionable)
    total_jobs = len(actionable)
    by_name = {r["name"]: r for r in rank}

    page.append('<section id="tab-req" hidden><div class="wrap">')
    tech = [r for r in rank if r["cat"] != "领域"]
    domain = [r for r in rank if r["cat"] == "领域"]

    def rank_table(rows, show_jobs=False, first_col="技能", strip_prefix="", levels=None):
        head = ('<div class="panel tight"><table class="rank"><thead><tr>'
                '<th class="c">#</th><th>' + first_col + '</th><th>类别</th>'
                '<th class="n">硬性</th><th class="n">加分</th><th class="n">覆盖</th>'
                '<th class="w">强度</th><th>判定</th><th>你的状态</th>')
        out = [head]
        if show_jobs:
            out.append('<th>涉及岗位</th>')
        out.append("</tr></thead><tbody>")
        for i, r in enumerate(rows, 1):
            ratio = r["total"] / total_jobs
            if ratio >= 0.75:
                verdict, vcls = "必备项", "v-must"
            elif ratio >= 0.5:
                verdict, vcls = "高频项", "v-high"
            elif ratio >= 0.25:
                verdict, vcls = "常见项", "v-mid"
            elif r["must"] > 0:
                verdict, vcls = "稀缺项", "v-low"
            else:
                verdict, vcls = "纯加分", "v-plus"
            out.append(
                '<tr><td class="c">%d</td><td class="sk">%s</td><td class="cat">%s</td>'
                '<td class="n">%d</td><td class="n">%d</td><td class="n">%d/%d</td>'
                '<td class="w"><span class="mini"><i style="width:%d%%"></i></span></td>'
                '<td><span class="verdict %s">%s</span></td>'
                % (i, esc(r["name"].replace(strip_prefix, "")), esc(r["cat"]), r["must"], r["plus"], r["total"], total_jobs,
                   round(ratio * 100), vcls, verdict)
            )
            lv, lnote = lookup_level(levels, r["name"])
            out.append('<td><span class="lvl lv%d" title="%s">%s</span></td>' % (lv, esc(lnote), LV_LABEL[lv]))
            if show_jobs:
                from collections import Counter as _C
                cnt = _C(r["jobs"])
                names = [c if n == 1 else "%s×%d" % (c, n) for c, n in cnt.items()]
                shown = "、".join(names[:4]) + ("…" if len(names) > 4 else "")
                out.append('<td class="dom">%s</td>' % esc(shown))
            out.append("</tr>")
        out.append("</tbody></table></div>")
        return "".join(out)

    page.append('<h2 class="sec">技能要求排行榜 · 技术技能（%d 个可投岗位）</h2>' % total_jobs)
    page.append('<p class="hint">你的基线：<b>%s</b> —— %s。最后一列是「你的状态」，可以直接对照差距。<br>' % (esc(profile.get("headline", "")), esc(profile.get("note", "").rstrip("。"))))
    page.append('<p class="hint">统计口径：技能出现在岗位「硬性要求」或「岗位职责」中记为<b>硬性</b>；仅出现在「加分项」中记为<b>加分</b>。'
                '同一岗位重复出现只计一次。多语言并列表述（如『Go/Java/Python 至少一种』）按<b>加分</b>计，避免把可选项算成必备。</p>')
    page.append(rank_table(tech, levels=levels))

    dom_jobs = set()
    for r in domain:
        dom_jobs.update(r["jobs"])
    page.append('<h2 class="sec">领域经验分布</h2>')
    page.append('<p class="hint">领域偏好单独统计：它在 JD 里多以「优先」「加分」表述，命中率天然低于技术技能；'
                '但对 4 年经验的社招，领域是否对口往往是简历第一道筛子（<b>推断</b>，非 JD 明示）。'
                '本池 %d/%d 个岗位写明了领域偏好。</p>' % (len(dom_jobs), total_jobs))
    page.append(rank_table(domain, show_jobs=True, first_col="领域", strip_prefix="领域：", levels=levels))

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

    go_r = by_name.get("Go", {"total": 0, "must": 0})
    k8s_r = by_name.get("K8s / 云原生", {"total": 0, "must": 0})
    llm_r = by_name.get("LLM / Agent 工程化", {"total": 0, "must": 0})
    page.append('<h2 class="sec">四条判断</h2>')
    notes = [
        ("Go 是底座，不是门槛",
         "Go 在 %d/%d 个岗位出现，其中 %d 个是硬性 —— 说明它已是基本盘。真正卡人的是领域深度，栈可以换，领域换不了。" % (go_r["total"], total_jobs, go_r["must"])),
        ("K8s 命中率低，但压在关键岗上",
         "K8s / 云原生只出现在 %d 个岗位（硬性 %d），覆盖率低；但其中包含主投第一顺位的腾讯 TIONE，属于『出现少、权重高』的稀缺项。" % (k8s_r["total"], k8s_r["must"])),
        ("LLM 工程化是 2026 年的新增变量",
         "LLM / Agent 相关要求出现在 %d 个岗位，是今年才普遍进 JD 的一项，也是把 4 年 Go 与其他人拉开差距的最短路径。" % llm_r["total"]),
        ("领域经验命中率最低，但决定性最强",
         "领域偏好只在 %d/%d 个岗位中被明写，且多为「优先」。但从技术技能榜看，各岗位的硬性要求高度同质（Go + 高并发 + MySQL + MQ）；"
         "真正能区分候选人的，恰恰是领域 —— 这也是为什么它值得单列一榜。" % (len(dom_jobs), total_jobs)),
    ]
    page.append('<div class="notes">')
    for h, p_ in notes:
        page.append('<div class="note-card"><h4>%s</h4><p>%s</p></div>' % (esc(h), esc(p_)))
    page.append("</div>")

    page.append("</div></section>")

    # module 4 —— 算法专题（公开可见）
    ameta = algo.get("meta", {})
    probs = algo.get("problems", [])
    backs = algo.get("back", [])
    cats = algo.get("cats", [])

    def heat_cell(h):
        return '<span class="heat">%s</span>' % (h if h else "—") if h else '<span class="heat mute">—</span>'

    page.append('<section id="tab-algo" hidden><div class="wrap">')
    page.append('<h2 class="sec">%s</h2>' % esc(ameta.get("title", "算法专题")))
    page.append('<p class="hint">%s<br><span style="opacity:.75">%s</span></p>'
                % (esc(ameta.get("subtitle", "")), esc(ameta.get("note", ""))))

    page.append('<div class="toolbar"><input id="aq" type="search" placeholder="搜索题目 / 考点…">')
    page.append('<select id="acat" class="fsel"><option value="全部">全部分类</option>')
    for c in cats:
        page.append('<option value="%s">%s</option>' % (esc(c), esc(c)))
    page.append('<option value="工程手撕">工程手撕</option></select>')
    page.append('<label class="toggle"><input id="ahot" type="checkbox"> 只看有面经热度</label>')
    page.append('<span class="count" id="acount"></span></div>')

    page.append('<div class="panel tight"><table class="algo"><thead><tr>'
                '<th>分类</th><th class="c">题号</th><th>题目</th><th class="c">难度</th>'
                '<th class="c">热度</th><th>考点</th></tr></thead><tbody>')
    ci = {c: i for i, c in enumerate(cats)}
    ordered = sorted(probs, key=lambda x: (ci.get(x.get("cat"), 99), -x.get("heat", 0), int(x["no"]) if x["no"].isdigit() else 0))
    for x in ordered:
        no = x.get("no", "")
        slug = x.get("slug")
        num = ('<a href="https://leetcode.cn/problems/%s/" target="_blank" rel="noopener">%s</a>' % (slug, no)) if slug else no
        d = x.get("diff", "")
        dcls = {"E": "d-e", "M": "d-m", "H": "d-h"}.get(d, "d-x")
        text = (str(no) + " " + x.get("title", "") + " " + x.get("point", "") + " " + x.get("cat", "")).lower()
        page.append('<tr class="aprob" data-tier="%s" data-hot="%d" data-text="%s">'
                    '<td class="cat">%s</td><td class="c mono">%s</td><td class="ttl">%s</td>'
                    '<td class="c"><span class="diff %s">%s</span></td><td class="c">%s</td><td class="pt">%s</td></tr>'
                    % (esc(x.get("cat")), 1 if x.get("heat") else 0, esc(text),
                       esc(x.get("cat")), num, esc(x.get("title")), dcls, esc(d), heat_cell(x.get("heat")), esc(x.get("point"))))
    for x in backs:
        d = x.get("diff", "—")
        text = (x.get("title", "") + " " + x.get("point", "")).lower()
        page.append('<tr class="aprob" data-tier="工程手撕" data-hot="1" data-text="%s">'
                    '<td class="cat">工程手撕</td><td class="c mono">—</td><td class="ttl">%s</td>'
                    '<td class="c"><span class="diff d-x">—</span></td><td class="c">%s</td><td class="pt">%s<br><span class="gh">Go：%s</span></td></tr>'
                    % (esc(text), esc(x.get("title")), heat_cell(x.get("heat")), esc(x.get("point")), esc(x.get("gohint"))))
    page.append("</tbody></table></div>")

    page.append('<h2 class="sec">Go 手撕的 6 个坑</h2>')
    page.append('<div class="panel"><div class="layers">')
    for f in algo.get("go_pitfalls", []):
        page.append('<div class="layer"><span class="k">%s</span><span class="v">%s</span></div>'
                    % (esc(f["k"]), esc(f["v"])))
    page.append("</div></div>")

    page.append('<h2 class="sec">17 天刷题计划</h2>')
    page.append('<div class="panel tight"><table class="algo"><thead><tr>'
                '<th class="c">阶段</th><th>主题</th><th>怎么刷</th></tr></thead><tbody>')
    for d in algo.get("plan", []):
        page.append('<tr><td class="c mono">%s</td><td class="ttl">%s</td><td class="pt">%s</td></tr>'
                    % (esc(d["d"]), esc(d["t"]), esc(d["v"])))
    page.append("</tbody></table></div>")
    page.append("</div></section>")

    # module 5 —— Go 深度（公开可见）
    gmeta = godoc.get("meta", {})
    topics = godoc.get("topics", [])
    page.append('<section id="tab-go" hidden><div class="wrap">')
    page.append('<h2 class="sec">%s</h2>' % esc(gmeta.get("title", "Go 深度")))
    page.append('<p class="hint">%s<br><span style="opacity:.75">%s</span></p>'
                % (esc(gmeta.get("subtitle", "")), esc(gmeta.get("note", ""))))

    if gmeta.get("demo"):
        page.append('<p class="hint">配套可运行 demo：<a href="%s" target="_blank" rel="noopener">demos/gmp</a> —— %s</p>'
                    % (esc(gmeta["demo"]), esc(gmeta.get("demo_note", ""))))

    page.append('<h2 class="sec">学习阶梯：到哪一步算学会了</h2>')
    page.append('<div class="ladder">')
    for i, lv in enumerate(godoc.get("levels", []), 1):
        page.append('<div class="lad-item"><div class="lad-top"><span class="lad-id">%s</span>'
                    '<span class="lad-nm">%s</span></div><p>%s</p></div>'
                    % (esc(lv["id"]), esc(lv["name"]), esc(lv["desc"])))
    page.append("</div>")

    for t in topics:
        page.append('<h2 class="sec">%s</h2>' % esc(t["name"]))
        page.append('<p class="hint">%s<br><b>目标：</b>%s</p>' % (esc(t.get("tagline", "")), esc(t.get("target", ""))))

        page.append('<h3 class="subsec">核心总结</h3>')
        for sec in t.get("sections", []):
            page.append('<div class="panel topic"><h4>%s</h4><ul>' % esc(sec["h"]))
            for pt in sec["points"]:
                page.append("<li>%s</li>" % esc(pt))
            page.append("</ul></div>")

        page.append('<h3 class="subsec">推荐阅读 <span>共 %d 篇，按「先建立直觉、再读源码」排序</span></h3>' % len(t.get("articles", [])))
        page.append('<div class="arts">')
        for a in t.get("articles", []):
            page.append('<a class="art" href="%s" target="_blank" rel="noopener">'
                        '<div class="art-h"><span class="art-lv">%s</span><span class="art-lang">%s%s</span></div>'
                        '<h5>%s</h5><div class="art-au">%s</div><p>%s</p></a>'
                        % (esc(a["url"]), esc(a["level"]), esc(a["lang"]),
                           (' · <span class="art-px">需代理</span>' if a.get("access") == "需代理" else ""),
                           esc(a["title"]), esc(a["author"]), esc(a["why"])))
        page.append("</div>")

        page.append('<h3 class="subsec">源码入口 <span>只看这几个，别一头扎进去</span></h3>')
        page.append('<div class="panel"><ul class="src">')
        for sp in t.get("source_paths", []):
            page.append("<li>%s</li>" % esc(sp))
        page.append("</ul></div>")

        page.append('<h3 class="subsec">自检清单 <span>能全部打勾，就算到 L3</span></h3>')
        page.append('<div class="panel"><div class="checks" id="gocheck">')
        for i, c in enumerate(t.get("checklist", [])):
            page.append('<label class="chk"><input type="checkbox" data-k="go-%s-%d"><span>%s</span></label>'
                        % (esc(t["id"]), i, esc(c)))
        page.append('</div><div class="chk-progress" id="goprog"></div></div>')

        page.append('<h3 class="subsec">高频追问 <span>点开看答题要点</span></h3>')
        for qa in t.get("followups", []):
            page.append('<details class="qa"><summary>%s</summary><p>%s</p></details>' % (esc(qa["q"]), esc(qa["a"])))

    # 记忆卡（Anki 式）
    clist = cards.get("cards", [])
    page.append('<h2 class="sec">记忆卡 <span style="font-weight:400;font-size:13px;color:var(--muted)">'
                '共 %d 张 · 点「会了」自动标记，进度存在本地</span></h2>' % len(clist))
    page.append('<div class="flash">')
    page.append('<div class="flash-top"><span id="fPos"></span>'
                '<span class="fbar"><i id="fFill"></i></span><span id="fStat"></span></div>')
    page.append('<div class="flash-card" id="fCard">'
                '<div class="f-cat" id="fCat"></div>'
                '<div class="f-q" id="fQ"></div>'
                '<div class="f-a" id="fA"></div>'
                '</div>')
    page.append('<div class="flash-actions">'
                '<button id="fShow" class="btn-primary">显示答案</button>'
                '<button id="fAgain" class="btn-ghost">还没掌握</button>'
                '<button id="fKnow" class="btn-ok">会了</button>'
                '</div>')
    page.append('<div class="flash-opts"><label class="toggle"><input id="fOnlyNew" type="checkbox"> 只看未掌握</label>'
                '<button id="fReset" class="btn-link">重置进度</button></div>')
    page.append('</div>')
    page.append('<script id="gmpCards" type="application/json">%s</script>'
                % json.dumps(clist, ensure_ascii=False).replace("</", "<\\/"))

    page.append('<h2 class="sec">后续主题路线</h2>')
    page.append('<div class="roadmap">')
    for r in godoc.get("roadmap", []):
        page.append('<div class="rm"><span class="rm-s">%s</span><b>%s</b><p>%s</p></div>'
                    % (esc(r["status"]), esc(r["name"]), esc(r["why"])))
    page.append("</div>")
    page.append("</div></section>")

    # module 3 —— 总简历能力池（仅本地构建，不进公开页）
    projs = resume.get("projects", [])
    if projs:
        rmeta = resume.get("meta", {})
        page.append('<section id="tab-resume" hidden><div class="wrap">')
        from collections import Counter as _Cnt
        prov_counts = _Cnt(x.get("provenance", "其他") for x in projs)
        prov_line = " · ".join("%s %d" % (k, v) for k, v in prov_counts.most_common())
        page.append('<h2 class="sec">%s（%d 条 · %s）</h2>'
                    % (esc(rmeta.get("title", "总简历能力池")), len(projs), esc(prov_line)))
        page.append('<p class="hint">%s<br><span style="opacity:.75">%s · %s</span></p>'
                    % (esc(rmeta.get("subtitle", "")), esc(rmeta.get("source", "")), esc(rmeta.get("note", ""))))

        page.append('<div class="panel"><div class="cappool">')
        for t in resume.get("capability_tags", []):
            page.append('<span class="cap">%s</span>' % esc(t))
        page.append("</div></div>")

        groups = {}
        for pr in projs:
            groups.setdefault(pr.get("group", "其他"), []).append(pr)
        order = ["风控", "行情", "投组", "账户体系（CeFi / DeFi）", "Agent 与 AI 平台", "内部平台", "平台与工程效能", "架构与技术设计", "产品与设计"]
        ordered = [g for g in order if g in groups] + [g for g in groups if g not in order]
        n = 0
        for g in ordered:
            page.append('<h2 class="sec">%s（%d 条）</h2>' % (esc(g), len(groups[g])))
            page.append('<div class="projs">')
            for pr in groups[g]:
                n += 1
                page.append('<article class="proj">')
                prov = pr.get("provenance", "")
                pcls = {"本人提交": "prov-own", "核心模块": "prov-core", "加分项": "prov-bonus", "团队项目": "prov-team"}.get(prov, "prov-team")
                page.append('<div class="proj-head"><span class="proj-idx">%02d</span><h3>%s</h3>'
                            '<span class="prov %s">%s</span></div>'
                            % (n, esc(pr.get("title")), pcls, esc(prov)))
                page.append('<div class="tags">%s</div>' % "".join('<span class="tag">%s</span>' % esc(t) for t in pr.get("tags", [])))
                page.append('<div class="pblock"><span class="lbl">背景</span><p>%s</p></div>' % esc(pr.get("context")))
                acts = pr.get("actions") or []
                if acts:
                    page.append('<div class="pblock"><span class="lbl">我的动作</span><ol>%s</ol></div>'
                                % "".join("<li>%s</li>" % esc(a) for a in acts))
                techs = pr.get("tech") or []
                if techs:
                    page.append('<div class="pblock"><span class="lbl">技术方案</span><div class="tags">%s</div></div>'
                                % "".join('<span class="tag tech">%s</span>' % esc(t) for t in techs))
                page.append('<div class="pblock"><span class="lbl">难点与权衡</span><p>%s</p></div>' % esc(pr.get("tradeoff")))
                page.append('<div class="pblock"><span class="lbl">结果</span><p class="res">%s</p></div>' % esc(pr.get("result")))
                bullet = pr.get("bullet", "")
                page.append('<div class="bullet"><span class="lbl">简历句式</span><p>%s</p>'
                            '<button class="copy" data-text="%s">复制</button></div>' % (esc(bullet), esc(bullet)))
                page.append("</article>")
            page.append("</div>")
        page.append("</div></section>")
    page.append("</main>")

    # footer
    page.append('<footer><div class="wrap">')
    page.append("%d 个岗位 · %d 条投递记录 · 生成于 %s<br>" % (len(jobs), len(apps), esc(now)))
    page.append("数据源 <code>data/jobs.json</code> · 由 <code>scripts/build_html.py</code> 生成，请勿手改本文件")
    page.append("</div></footer>")
    page.append("<script>%s</script></body></html>" % JS)

    target = (ROOT / "index.local.html") if projs else OUT
    target.write_text("".join(page), encoding="utf-8")
    print("wrote %s (%d jobs, %d actionable, %d projects)" % (target, len(jobs), len(actionable), len(projs)))


if __name__ == "__main__":
    main()