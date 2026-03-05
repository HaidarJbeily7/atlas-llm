"""HTML report generator with embedded CSS and interactive dashboard."""
from __future__ import annotations

from pathlib import Path

from atlas.core.models import ScanResult
from atlas.plugins.registry import register


@register("reporters", name="html")
class HTMLReporter:
    """Generates HTML report with embedded CSS dashboard."""

    name = "html"
    format = "html"

    async def generate(self, result: ScanResult, output_path: str) -> str:
        """Write scan result as interactive HTML report."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        html = self._render(result)
        with open(path, "w") as f:
            f.write(html)

        return str(path)

    def _render(self, result: ScanResult) -> str:
        score = result.security_score
        ca = result.compliance_assessment

        # Score color
        if score.overall_score >= 80:
            score_color = "#28a745"
        elif score.overall_score >= 60:
            score_color = "#ffc107"
        elif score.overall_score >= 40:
            score_color = "#fd7e14"
        else:
            score_color = "#dc3545"

        # Build probe rows
        probe_rows = ""
        for name, pr in result.probe_results.items():
            rate_color = "#28a745" if pr.pass_rate >= 80 else "#ffc107" if pr.pass_rate >= 60 else "#dc3545"
            probe_rows += f"""
            <tr>
                <td>{name}</td>
                <td>{pr.total_attempts}</td>
                <td style="color:#28a745">{pr.passed}</td>
                <td style="color:#dc3545">{pr.failed}</td>
                <td style="color:{rate_color};font-weight:bold">{pr.pass_rate:.1f}%</td>
            </tr>"""

        # Category score bars
        category_bars = ""
        for cat, cat_score in sorted(score.category_scores.items()):
            bar_color = "#28a745" if cat_score >= 80 else "#ffc107" if cat_score >= 60 else "#dc3545"
            category_bars += f"""
            <div class="category-row">
                <span class="cat-name">{cat}</span>
                <div class="progress-bar">
                    <div class="progress-fill" style="width:{cat_score}%;background:{bar_color}"></div>
                </div>
                <span class="cat-score">{cat_score:.0f}</span>
            </div>"""

        # Compliance rows
        compliance_rows = ""
        for a in ca.article_details:
            status_class = "compliant" if a.status.value == "compliant" else "non-compliant" if a.status.value == "non-compliant" else "partial"
            compliance_rows += f"""
            <tr>
                <td>{a.article_id}</td>
                <td>{a.title}</td>
                <td><span class="badge badge-{status_class}">{a.status.value}</span></td>
                <td>{a.findings_count}</td>
                <td>{a.critical_findings}</td>
            </tr>"""

        # Recommendations
        rec_items = ""
        for rec in result.recommendations:
            priority = "critical" if "CRITICAL" in rec else "warning" if "WARNING" in rec else "info"
            rec_items += f'<div class="rec rec-{priority}">{rec}</div>\n'

        # Findings table (first 100)
        failed_findings = [f for f in result.findings if not f.passed]
        finding_rows = ""
        for f in failed_findings[:100]:
            sev_class = f.severity.value
            finding_rows += f"""
            <tr>
                <td><span class="badge badge-{sev_class}">{f.severity.value.upper()}</span></td>
                <td>{f.category.value}</td>
                <td>{f.attempt.probe_name}</td>
                <td class="truncate">{_html_escape(f.attempt.prompt[:150])}</td>
                <td>{', '.join(f.compliance_articles[:3])}</td>
            </tr>"""

        vuln = score.vulnerabilities_by_severity

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATLAS Security Report - {result.model_name}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f6fa; color:#2d3436; padding:2rem; }}
.container {{ max-width:1200px; margin:0 auto; }}
h1 {{ font-size:1.8rem; margin-bottom:0.5rem; }}
h2 {{ font-size:1.3rem; margin:2rem 0 1rem; padding-bottom:0.5rem; border-bottom:2px solid #dfe6e9; }}
.header {{ background:linear-gradient(135deg,#2d3436,#636e72); color:white; padding:2rem; border-radius:12px; margin-bottom:2rem; }}
.header p {{ opacity:0.8; margin-top:0.5rem; }}
.metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem; margin-bottom:2rem; }}
.metric-card {{ background:white; border-radius:8px; padding:1.5rem; box-shadow:0 2px 4px rgba(0,0,0,0.1); text-align:center; }}
.metric-value {{ font-size:2rem; font-weight:bold; }}
.metric-label {{ color:#636e72; font-size:0.85rem; margin-top:0.5rem; }}
.score-card {{ border-left:4px solid {score_color}; }}
.score-card .metric-value {{ color:{score_color}; }}
table {{ width:100%; border-collapse:collapse; background:white; border-radius:8px; overflow:hidden; box-shadow:0 2px 4px rgba(0,0,0,0.1); margin-bottom:1.5rem; }}
th {{ background:#2d3436; color:white; padding:0.75rem 1rem; text-align:left; font-size:0.85rem; }}
td {{ padding:0.75rem 1rem; border-bottom:1px solid #eee; font-size:0.9rem; }}
tr:hover {{ background:#f8f9fa; }}
.badge {{ padding:0.25rem 0.5rem; border-radius:4px; font-size:0.75rem; font-weight:bold; text-transform:uppercase; }}
.badge-compliant {{ background:#d4edda; color:#155724; }}
.badge-non-compliant {{ background:#f8d7da; color:#721c24; }}
.badge-partial {{ background:#fff3cd; color:#856404; }}
.badge-critical {{ background:#f8d7da; color:#721c24; }}
.badge-high {{ background:#ffe0cc; color:#993800; }}
.badge-medium {{ background:#fff3cd; color:#856404; }}
.badge-low {{ background:#d4edda; color:#155724; }}
.badge-info {{ background:#d1ecf1; color:#0c5460; }}
.category-row {{ display:flex; align-items:center; margin:0.5rem 0; }}
.cat-name {{ width:180px; font-size:0.9rem; }}
.progress-bar {{ flex:1; height:20px; background:#eee; border-radius:10px; overflow:hidden; margin:0 1rem; }}
.progress-fill {{ height:100%; border-radius:10px; transition:width 0.5s; }}
.cat-score {{ width:40px; text-align:right; font-weight:bold; }}
.rec {{ padding:0.75rem 1rem; border-radius:6px; margin:0.5rem 0; font-size:0.9rem; }}
.rec-critical {{ background:#f8d7da; border-left:4px solid #dc3545; }}
.rec-warning {{ background:#fff3cd; border-left:4px solid #ffc107; }}
.rec-info {{ background:#d1ecf1; border-left:4px solid #17a2b8; }}
.truncate {{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.section {{ background:white; border-radius:8px; padding:1.5rem; box-shadow:0 2px 4px rgba(0,0,0,0.1); margin-bottom:1.5rem; }}
footer {{ text-align:center; color:#636e72; margin-top:3rem; font-size:0.85rem; }}
@media (max-width:768px) {{ .metrics {{ grid-template-columns:1fr; }} .cat-name {{ width:120px; }} }}
</style>
</head>
<body>
<div class="container">

<div class="header">
    <h1>ATLAS Security Scan Report</h1>
    <p>Model: {result.model_name} | Profile: {result.profile} | ID: {result.scan_id[:8]}</p>
    <p>Date: {result.started_at} | Duration: {result.duration_ms/1000:.1f}s</p>
</div>

<div class="metrics">
    <div class="metric-card score-card">
        <div class="metric-value">{score.overall_score:.1f}</div>
        <div class="metric-label">Security Score (0-100)</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{score.risk_level.value.upper()}</div>
        <div class="metric-label">Risk Level</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{len(result.findings)}</div>
        <div class="metric-label">Total Findings</div>
    </div>
    <div class="metric-card">
        <div class="metric-value" style="color:#dc3545">{vuln.get('critical',0)}</div>
        <div class="metric-label">Critical Vulnerabilities</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{score.compliance_score:.0f}</div>
        <div class="metric-label">Compliance Score</div>
    </div>
</div>

<div class="section">
    <h2>Category Scores</h2>
    {category_bars}
</div>

<h2>Probe Results</h2>
<table>
    <thead><tr><th>Probe</th><th>Total</th><th>Passed</th><th>Failed</th><th>Pass Rate</th></tr></thead>
    <tbody>{probe_rows}</tbody>
</table>

{"<h2>EU AI Act Compliance</h2><table><thead><tr><th>Article</th><th>Title</th><th>Status</th><th>Findings</th><th>Critical</th></tr></thead><tbody>" + compliance_rows + "</tbody></table>" if compliance_rows else ""}

<div class="section">
    <h2>Recommendations</h2>
    {rec_items or '<p style="color:#636e72">No critical issues found.</p>'}
</div>

{"<h2>Vulnerability Findings</h2><table><thead><tr><th>Severity</th><th>Category</th><th>Probe</th><th>Prompt</th><th>Compliance</th></tr></thead><tbody>" + finding_rows + "</tbody></table>" if finding_rows else ""}

<footer>
    <p>Generated by ATLAS (Automated Testing for LLM Assurance &amp; Security) v0.1.0</p>
</footer>

</div>
</body>
</html>"""


def _html_escape(text: str) -> str:
    """Basic HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
