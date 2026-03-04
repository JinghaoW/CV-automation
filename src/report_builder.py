"""Generate an HTML report from ranked job data."""

import html
import json
import os
import sys
from datetime import datetime, timezone

JOBS_SCORED_PATH = os.path.join("data", "jobs_scored.json")
REPORT_PATH = os.path.join("output", "report.html")

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Job Search Report – {date}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; background: #f5f5f5; color: #333; }}
    h1 {{ color: #1a1a2e; }}
    h2 {{ color: #16213e; margin-top: 2rem; border-bottom: 2px solid #ddd; padding-bottom: 0.3rem; }}
    h3 {{ color: #0f3460; margin-top: 1.5rem; }}
    .job-card {{
      background: #fff; border: 1px solid #ddd; border-radius: 8px;
      padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .job-title {{ font-size: 1.1rem; font-weight: bold; }}
    .job-meta {{ color: #555; font-size: 0.9rem; margin: 0.3rem 0; }}
    .score-badge {{
      display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px;
      font-weight: bold; font-size: 0.85rem; color: #fff;
    }}
    .score-high {{ background: #28a745; }}
    .score-mid {{ background: #ffc107; color: #333; }}
    .score-low {{ background: #dc3545; }}
    .classification {{ font-style: italic; color: #666; font-size: 0.85rem; }}
    .reasoning {{ font-size: 0.9rem; color: #444; margin-top: 0.5rem; }}
    a {{ color: #0066cc; }}
    .toc a {{ display: block; margin: 0.2rem 0; }}
  </style>
</head>
<body>
  <h1>&#128188; Job Search Report</h1>
  <p>Generated on <strong>{date}</strong> &bull; {total} listings found</p>

  <div class="toc">
    <h2>Table of Contents</h2>
    {toc}
  </div>

  {sections}
</body>
</html>
"""

_SECTION_TEMPLATE = """\
<h2 id="{anchor}">{heading}</h2>
{subsections}
"""

_JOB_CARD_TEMPLATE = """\
<div class="job-card">
  <div class="job-title">
    {link_open}{title}{link_close}
    <span class="score-badge {score_class}">{score}/10</span>
    <span class="classification">[{classification}]</span>
  </div>
  <div class="job-meta">&#127970; {company} &bull; &#127757; {location}</div>
  <div class="reasoning">{reasoning}</div>
</div>
"""


def _score_class(score: int) -> str:
    if score >= 7:
        return "score-high"
    if score >= 4:
        return "score-mid"
    return "score-low"


def _render_job_card(job: dict) -> str:
    score = int(job.get("score", 0))
    url = job.get("url", "")
    title = html.escape(str(job.get("title", "N/A")))
    link_open = f'<a href="{html.escape(url)}" target="_blank">' if url else ""
    link_close = "</a>" if url else ""
    return _JOB_CARD_TEMPLATE.format(
        link_open=link_open,
        title=title,
        link_close=link_close,
        score=score,
        score_class=_score_class(score),
        classification=html.escape(str(job.get("classification", "unknown"))),
        company=html.escape(str(job.get("company", "N/A"))),
        location=html.escape(str(job.get("location", "N/A"))),
        reasoning=html.escape(str(job.get("reasoning", ""))),
    )


def build_report(
    jobs_scored_path: str = JOBS_SCORED_PATH,
    report_path: str = REPORT_PATH,
) -> str:
    """Load scored jobs, build an HTML report grouped by country and classification.

    Returns the HTML string.
    """
    if not os.path.exists(jobs_scored_path):
        raise FileNotFoundError(f"Scored jobs file not found: {jobs_scored_path}")

    with open(jobs_scored_path, encoding="utf-8") as fh:
        jobs = json.load(fh)

    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not jobs:
        html_out = _HTML_TEMPLATE.format(
            date=date_str,
            total=0,
            toc="<p>No jobs found.</p>",
            sections="<p>No jobs found.</p>",
        )
        _write_report(html_out, report_path)
        return html_out

    # Sort by score descending
    jobs_sorted = sorted(jobs, key=lambda j: int(j.get("score", 0)), reverse=True)

    # Group by country then by classification
    countries: dict[str, dict[str, list[dict]]] = {}
    for job in jobs_sorted:
        country = str(job.get("country", "Unknown"))
        classification = str(job.get("classification", "unknown"))
        countries.setdefault(country, {}).setdefault(classification, []).append(job)

    toc_lines = []
    section_parts = []

    for country in sorted(countries.keys()):
        anchor = country.lower().replace(" ", "-")
        toc_lines.append(f'<a href="#{anchor}">{html.escape(country)}</a>')

        subsection_parts = []
        for classification in sorted(countries[country].keys()):
            jobs_in_class = countries[country][classification]
            sub_anchor = f"{anchor}-{classification}"
            toc_lines.append(
                f'&nbsp;&nbsp;<a href="#{sub_anchor}">'
                f'{html.escape(classification.capitalize())} ({len(jobs_in_class)})</a>'
            )
            cards = "".join(_render_job_card(j) for j in jobs_in_class)
            subsection_parts.append(
                f'<h3 id="{sub_anchor}">'
                f'{html.escape(classification.capitalize())}</h3>\n{cards}'
            )

        section_parts.append(
            _SECTION_TEMPLATE.format(
                anchor=anchor,
                heading=html.escape(country),
                subsections="\n".join(subsection_parts),
            )
        )

    html_out = _HTML_TEMPLATE.format(
        date=date_str,
        total=len(jobs_sorted),
        toc="\n".join(toc_lines),
        sections="\n".join(section_parts),
    )

    _write_report(html_out, report_path)
    return html_out


def _write_report(html_content: str, report_path: str) -> None:
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)
    print(f"[report_builder] Report written to {report_path}")


if __name__ == "__main__":
    try:
        build_report()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
