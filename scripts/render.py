#!/usr/bin/env python3
"""把 data/jobs.json + data/applications.json 渲染成 README.md。

用法：
    python3 scripts/render.py

只依赖标准库。改完数据跑一次，README 就同步了。
"""

import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
README = ROOT / "README.md"

TIER_ORDER = ["主投", "冲刺", "备选", "排除"]
TIER_DESC = {
    "主投": "年限与技能双匹配，优先投、优先准备",
    "冲刺": "方向有吸引力但存在明确缺口或不确定性",
    "备选": "年限偏低或公司规模偏小，用于练兵与兜底",
    "排除": "不符合当前条件，保留记录避免重复检索",
}


def load(name):
    with open(DATA / name, encoding="utf-8") as fh:
        return json.load(fh)


def cell(value):
    """空值统一显示为 —，并转义竖线避免破坏表格。"""
    if value in (None, "", []):
        return "—"
    return str(value).replace("|", "\\|")


def link(url, label="打开"):
    if not url:
        return "—"
    return "[%s](%s)" % (label, url)


def tier_table(jobs, numbered=True):
    head = "| # | 公司 | 岗位 | 年限 | 语言 | Go 对口 | 薪资 | 来源 | 链接 |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    rows = [head, sep]
    for i, job in enumerate(jobs, 1):
        rows.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                i if numbered else "",
                cell(job.get("company")),
                cell(job.get("title")),
                cell(job.get("band")),
                cell(job.get("languages")),
                cell(job.get("go_fit")),
                cell(job.get("salary")),
                cell(job.get("source_name")),
                link(job.get("source_url"), "JD"),
            )
        )
    return "\n".join(rows)


def exclude_table(jobs):
    rows = ["| 公司 | 岗位 | 年限 | 语言 | 排除原因 |", "|---|---|---|---|---|"]
    for job in jobs:
        rows.append(
            "| %s | %s | %s | %s | %s |"
            % (
                cell(job.get("company")),
                cell(job.get("title")),
                cell(job.get("band")),
                cell(job.get("languages")),
                cell(job.get("exclude_reason")),
            )
        )
    return "\n".join(rows)


def detail_section(jobs):
    out = []
    for i, job in enumerate(jobs, 1):
        out.append("### %d. %s · %s" % (i, job.get("company", ""), job.get("title", "")))
        out.append("")
        meta = []
        if job.get("band"):
            meta.append("**年限** %s" % job["band"])
        if job.get("languages"):
            meta.append("**语言** %s" % job["languages"])
        if job.get("go_fit"):
            meta.append("**Go 对口** %s" % job["go_fit"])
        if job.get("salary"):
            meta.append("**薪资** %s" % job["salary"])
        if job.get("source_level"):
            meta.append(
                "**来源** %s 级 · %s"
                % (job["source_level"], job.get("source_name") or "—")
            )
        if job.get("jd_verified"):
            meta.append("**JD 完整度** %s" % {"full": "完整", "partial": "部分", "none": "未获取"}.get(job["jd_verified"], job["jd_verified"]))
        out.append(" · ".join(meta) if meta else "")
        out.append("")

        must = job.get("must") or []
        if must:
            out.append("**硬性要求**")
            out.append("")
            for item in must:
                out.append("- %s" % item)
            out.append("")

        plus = job.get("plus") or []
        if plus:
            out.append("**加分项**")
            out.append("")
            for item in plus:
                out.append("- %s" % item)
            out.append("")

        if job.get("note"):
            out.append("> %s" % job["note"])
            out.append("")

        if job.get("source_url"):
            out.append("链接：%s" % link(job["source_url"], job["source_url"]))
            out.append("")

    return "\n".join(out).rstrip()


def pipeline_table(apps, by_id):
    header = "| 优先级 | 公司 | 岗位 | 阶段 | 投递日 | 最后更新 | 下一步 |"
    sep = "|---|---|---|---|---|---|---|"
    rows = [header, sep]
    for app in sorted(apps, key=lambda a: a.get("priority", 99)):
        job = by_id.get(app.get("job_id"), {})
        rows.append(
            "| %s | %s | %s | %s | %s | %s | %s |"
            % (
                cell(app.get("priority")),
                cell(job.get("company")),
                cell(job.get("title")),
                cell(app.get("stage")),
                cell(app.get("applied_at")),
                cell(app.get("last_update")),
                cell(app.get("next_step")),
            )
        )
    return "\n".join(rows)


def main():
    jobs_doc = load("jobs.json")
    apps_doc = load("applications.json")

    meta = jobs_doc.get("meta", {})
    jobs = jobs_doc.get("jobs", [])
    apps = apps_doc.get("applications", [])
    by_id = {job.get("id"): job for job in jobs}

    grouped = {tier: [j for j in jobs if j.get("tier") == tier] for tier in TIER_ORDER}
    actionable = grouped["主投"] + grouped["冲刺"] + grouped["备选"]

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    stage_counts = {}
    for app in apps:
        stage_counts[app.get("stage")] = stage_counts.get(app.get("stage"), 0) + 1

    lines = []
    lines.append("# %s" % meta.get("title", "岗位池"))
    lines.append("")
    lines.append("> %s" % meta.get("owner_note", ""))
    lines.append(">")
    lines.append(
        "> 数据核验：%s · 城市：%s · 本文件由 `scripts/render.py` 生成，请勿手改"
        % (meta.get("verified_at", "—"), meta.get("city", "—"))
    )
    lines.append("")
    lines.append("## 概览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append("| 岗位总数 | %d |" % len(jobs))
    for tier in TIER_ORDER:
        lines.append("| %s | %d |" % (tier, len(grouped[tier])))
    lines.append("| 投递看板条目 | %d |" % len(apps))
    if stage_counts:
        lines.append(
            "| 阶段分布 | %s |"
            % " · ".join("%s %d" % (k, v) for k, v in sorted(stage_counts.items()))
        )
    lines.append("")

    for tier in TIER_ORDER:
        items = grouped[tier]
        if not items:
            continue
        lines.append("## %s（%d）" % (tier, len(items)))
        lines.append("")
        lines.append("_%s_" % TIER_DESC[tier])
        lines.append("")
        lines.append(exclude_table(items) if tier == "排除" else tier_table(items))
        lines.append("")

    if actionable:
        lines.append("## 岗位要求明细")
        lines.append("")
        lines.append(detail_section(actionable))
        lines.append("")

    if apps:
        lines.append("## 投递看板")
        lines.append("")
        lines.append(pipeline_table(apps, by_id))
        lines.append("")

    lines.append("## 维护方式")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 scripts/render.py   # 改完 data/*.json 后重渲染 README")
    lines.append("```")
    lines.append("")
    lines.append("- `data/jobs.json`：岗位池，唯一事实来源")
    lines.append("- `data/applications.json`：投递看板")
    lines.append("- 阶段枚举：%s" % " / ".join(apps_doc.get("meta", {}).get("stages", [])))
    lines.append("- 来源等级：S 官方直读 · A 官方 ATS/猎头 · B 线索")
    lines.append("- JD 完整度：完整 / 部分 / 未获取（官方站多为 JS 渲染，抓不到正文时如实标注）")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("<sub>最后生成：%s</sub>" % now)
    lines.append("")

    README.write_text("\n".join(lines), encoding="utf-8")
    print("wrote %s (%d jobs, %d apps)" % (README, len(jobs), len(apps)))


if __name__ == "__main__":
    main()