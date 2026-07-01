import csv
import io
import json
import re
import urllib.request
from datetime import date

SHEET_ID = "1_6q_f57iR2xPBd0xPWuv3qG6GJ5l56E09CkWubWNvFA"


def fetch_csv(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        with urllib.request.urlopen(url) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        raise SystemExit(
            f"Could not fetch '{sheet_name}' tab.\n"
            f"Make sure the sheet is published to the web (File > Share > Publish to web).\n"
            f"Error: {e}"
        )


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader if any(v.strip() for v in row.values())]


def status_class(status):
    s = status.lower().strip()
    if s == "live":
        return "live"
    if s == "blocked":
        return "blocked"
    if "waiting" in s:
        return "waiting"
    if s in ("not started", "status tbc", "audit pending", "unconfirmed"):
        return "notstarted"
    if s in ("planned", "discovery") or "post-august" in s:
        return "planned"
    if s == "poc":
        return "poc"
    return "inbuild"


def js(value):
    return json.dumps(str(value).strip())


def build_partners_js(summary_rows, workstream_rows):
    ws_by_partner = {}
    for row in workstream_rows:
        p = row["Partner"].strip()
        ws_by_partner.setdefault(p, []).append(row)

    partner_blocks = []
    for row in summary_rows:
        name = row["Partner"].strip()
        risk = row["Renewal Risk"].strip()
        milestone_text = row["Key Milestone"].strip()
        milestone_due = row["Milestone Due Date"].strip()
        status = row["Overall Status"].strip()

        try:
            live = int(row["Agents Live"].strip())
        except ValueError:
            live = 0
        try:
            build = int(row["Agents In Build"].strip())
        except ValueError:
            build = 0

        milestone = f"{milestone_text} \u2014 due {milestone_due}"

        ws_items = []
        for w in ws_by_partner.get(name, []):
            ws_items.append(
                f"      {{ name: {js(w['Workstream'])}, lead: {js(w['CV Lead'])}, "
                f"status: {js(w['Status'])}, statusClass: {js(status_class(w['Status']))}, "
                f"deliverable: {js(w['Deliverable'])}, due: {js(w['Due Date'])}, "
                f"blocker: {js(w['Blocker'])}, cvAction: {js(w['CV Action Needed'])}, "
                f"partnerAction: {js(w['Partner Action Needed'])} }}"
            )

        ws_block = ",\n".join(ws_items)
        partner_blocks.append(
            f"  {{\n"
            f"    name: {js(name)}, risk: {js(risk)}, live: {live}, build: {build},\n"
            f"    milestone: {js(milestone)}, status: {js(status)},\n"
            f"    workstreams: [\n{ws_block},\n    ]\n"
            f"  }}"
        )

    return "const partners = [\n" + ",\n".join(partner_blocks) + "\n];"


def build_actions_js(action_rows):
    items = []
    for row in action_rows:
        items.append(
            f"  {{ partner: {js(row['Partner'])}, item: {js(row['Action Item'])}, "
            f"owner: {js(row['Owner'])}, due: {js(row['Due Date'])}, "
            f"priority: {js(row['Priority'])}, status: {js(row['Status'])}, "
            f"notes: {js(row['Notes'])} }}"
        )
    return "const actions = [\n" + ",\n".join(items) + "\n];"


def main():
    today = date.today()
    today_str = today.strftime("%B %-d, %Y")

    print("Fetching Partner_Summary...")
    summary = parse_csv(fetch_csv("Partner_Summary"))
    print("Fetching Workstreams...")
    workstreams = parse_csv(fetch_csv("Workstreams"))
    print("Fetching Action_Items...")
    actions = parse_csv(fetch_csv("Action_Items"))

    partners_js = build_partners_js(summary, workstreams)
    actions_js = build_actions_js(actions)

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    html = re.sub(r"const partners = \[.*?\];", partners_js, html, flags=re.DOTALL)
    html = re.sub(r"const actions = \[.*?\];", actions_js, html, flags=re.DOTALL)
    html = re.sub(
        r"Snapshot reflects the partner tracker as of [^.]+\.",
        f"Snapshot reflects the partner tracker as of {today_str}.",
        html,
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Done. index.html updated as of {today_str}.")


if __name__ == "__main__":
    main()
