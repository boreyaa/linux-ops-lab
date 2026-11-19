import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def render_report(records, outdir="reports", tpl_dir="report", scope_file="targets.yaml"):
    env = Environment(
        loader=FileSystemLoader(tpl_dir),
        autoescape=select_autoescape(["html", "htm"]),
    )
    template = env.get_template("tpl.html")

    rows = []
    for record in records:
        for port in record.get("ports") or []:
            if port.get("state") != "open":
                continue
            rows.append({
                "ip": record.get("ip"),
                "port": port.get("port"),
                "state": port.get("state"),
                "service": port.get("service") or "-",
                "version": port.get("version") or "-",
            })

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
        rows=rows,
        findings=findings,
        summary=summary,
        levels=("high", "medium", "low", "info"),
        scope_file=scope_file,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
