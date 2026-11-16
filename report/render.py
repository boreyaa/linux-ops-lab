import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def render_report(records, outdir="reports", tpl_dir="report"):
    env = Environment(
        loader=FileSystemLoader(tpl_dir),
        autoescape=select_autoescape(["html", "htm"]),
    )
    template = env.get_template("tpl.html")

    findings = []
    for record in records:
        for item in record.get("findings") or []:
            row = dict(item)
            row["ip"] = record.get("ip")
            findings.append(row)
    findings.sort(key=lambda x: ORDER.get(x.get("level"), 9))

    summary = {}
    for item in findings:
        summary[item["level"]] = summary.get(item["level"], 0) + 1

    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(outdir, "report_" + stamp + ".html")
    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        targets=[str(r.get("ip")) for r in records],
        findings=findings,
        summary=summary,
        levels=("high", "medium", "low", "info"),
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
