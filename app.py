"""
Streamlit Web Interface for Agentic Research Paper Evaluator
"""

import os
import sys
import io
from pathlib import Path
from datetime import datetime
import json

# Fix Windows charmap crash from emoji in CrewAI verbose output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from evaluator import ArxivEvaluator
from core.arxiv_client import ArxivClient

st.set_page_config(
    page_title="arXiv Paper Evaluator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .score-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        height: 100%;
    }
    .recommendation-accept {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 1.5rem;
        color: #155724;
    }
    .recommendation-reject {
        background: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 1.5rem;
        color: #721c24;
    }
    .recommendation-revision {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1.5rem;
        color: #856404;
    }
    .paper-info-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e3a5f;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def score_color(score: int) -> str:
    if score >= 70:
        return "#28a745"
    elif score >= 40:
        return "#e6a817"
    return "#dc3545"


def grammar_color(rating: str) -> str:
    return {"HIGH": "#28a745", "MEDIUM": "#e6a817", "LOW": "#dc3545"}.get(rating, "#6c757d")


def novelty_color(index: str) -> str:
    return {"Novel": "#28a745", "Incremental": "#e6a817", "Derivative": "#dc3545"}.get(index, "#6c757d")


def score_card(label: str, value: str, color: str, note: str = ""):
    st.markdown(f"""
    <div class="score-card">
        <p style="color:#777;font-size:0.8rem;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em">{label}</p>
        <p style="color:{color};font-size:1.9rem;font-weight:700;margin:0">{value}</p>
        {f'<p style="color:#999;font-size:0.75rem;margin-top:0.3rem">{note}</p>' if note else ""}
    </div>
    """, unsafe_allow_html=True)


def generate_pdf_report(report: dict) -> bytes:
    """Generate a styled PDF report using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    NAVY   = colors.HexColor("#1e3a5f")
    GREEN  = colors.HexColor("#28a745")
    RED    = colors.HexColor("#dc3545")
    AMBER  = colors.HexColor("#e6a817")
    LGRAY  = colors.HexColor("#f4f6f9")
    DGRAY  = colors.HexColor("#555555")

    title_style = ParagraphStyle("Title2", parent=styles["Title"],
        textColor=NAVY, fontSize=18, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"],
        textColor=NAVY, fontSize=13, spaceBefore=14, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"],
        textColor=NAVY, fontSize=11, spaceBefore=10, spaceAfter=3)
    body = ParagraphStyle("Body2", parent=styles["Normal"],
        fontSize=9, leading=13, textColor=DGRAY)
    small = ParagraphStyle("Small", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey)
    center = ParagraphStyle("Center", parent=styles["Normal"],
        alignment=TA_CENTER, fontSize=9, textColor=DGRAY)

    meta   = report["metadata"]
    sc     = report["scores"]
    fi     = report.get("findings", {})
    rec    = report.get("recommendation", "NEEDS_REVISION")
    overall = report["overall_score"]

    rec_color = {"ACCEPT": GREEN, "REJECT": RED, "NEEDS_REVISION": AMBER}.get(rec, AMBER)
    rec_label = {"ACCEPT": "✅  ACCEPT", "REJECT": "❌  REJECT",
                 "NEEDS_REVISION": "⚠️  NEEDS REVISION"}.get(rec, rec)

    grammar_num = {"HIGH": 100, "MEDIUM": 60, "LOW": 20}.get(sc["grammar"], 60)
    novelty_num = {"Novel": 100, "Incremental": 60, "Derivative": 20}.get(sc["novelty"], 60)

    def score_col(v):
        if isinstance(v, int):
            return GREEN if v >= 70 else (AMBER if v >= 40 else RED)
        return DGRAY

    story = []

    # ── Header ────────────────────────────────────────────────────────────
    story.append(Paragraph("🔬 Research Paper Evaluation Report", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=8))

    # Paper info table
    authors = meta.get("authors", [])
    auth_str = ", ".join(authors[:4]) + (f" +{len(authors)-4} more" if len(authors) > 4 else "")
    info_data = [
        ["Title", meta.get("title", "N/A")],
        ["arXiv ID", meta.get("arxiv_id", "N/A")],
        ["Authors", auth_str or "N/A"],
        ["Published", str(meta.get("published", "N/A"))[:10]],
        ["Categories", ", ".join(meta.get("categories", [])) or "N/A"],
        ["Evaluation Date", str(meta.get("evaluation_date", ""))[:10]],
    ]
    info_table = Table(info_data, colWidths=[3.5*cm, 13*cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), NAVY),
        ("TEXTCOLOR", (1,0), (1,-1), DGRAY),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LGRAY, colors.white]),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    # ── Executive Summary ─────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    rec_cell = Paragraph(rec_label, ParagraphStyle(
        "Rec", parent=styles["Normal"], fontSize=13,
        textColor=rec_color, fontName="Helvetica-Bold"))
    score_cell = Paragraph(
        f"Overall Score: <b>{overall}/100</b>",
        ParagraphStyle("OS", parent=styles["Normal"], fontSize=11,
                       textColor=score_col(overall)))
    rec_table = Table([[rec_cell, score_cell]], colWidths=[9*cm, 7.5*cm])
    rec_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LGRAY),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [5,5,5,5]),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 10))

    # ── Score Table ───────────────────────────────────────────────────────
    story.append(Paragraph("Detailed Scores", h1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    score_rows = [
        [Paragraph("<b>Metric</b>", body), Paragraph("<b>Score</b>", body),
         Paragraph("<b>Weight</b>", body), Paragraph("<b>Interpretation</b>", body)],
        ["Consistency",     f"{sc['consistency']}/100",  "30%", "Methodology ↔ Results alignment"],
        ["Grammar",         sc['grammar'],                "20%", "HIGH / MEDIUM / LOW"],
        ["Novelty",         sc['novelty'],                "20%", "Novel / Incremental / Derivative"],
        ["Fabrication Risk",f"{sc['authenticity']}%",    "30%", "Lower is better (authenticity)"],
        ["Overall Score",   f"{overall}/100",             "—",   "Weighted composite"],
    ]
    st_obj = Table(score_rows, colWidths=[3.5*cm, 3*cm, 2*cm, 8*cm])
    st_obj.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        # Colour last row bold
        ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (1,-1), (1,-1),  score_col(overall)),
    ]))
    story.append(st_obj)
    story.append(Spacer(1, 10))

    # ── Agent Findings ────────────────────────────────────────────────────
    sections = [
        ("Consistency Analysis",      fi.get("consistency_analysis", "")),
        ("Grammar & Language Quality", fi.get("grammar_analysis", "")),
        ("Novelty Assessment",         fi.get("novelty_analysis", "")),
        ("Fact-Check Log",             fi.get("factcheck_log", "")),
        ("Authenticity Audit",         fi.get("authenticity_analysis", "")),
    ]

    story.append(Paragraph("Agent Findings", h1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    for sec_title, content in sections:
        if not content:
            continue
        block = []
        block.append(Paragraph(sec_title, h2))
        # Split into lines, render each as a paragraph to preserve formatting
        for line in (content or "N/A").split("\n"):
            line = line.strip()
            if not line:
                block.append(Spacer(1, 3))
            else:
                # Escape XML special chars
                line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                block.append(Paragraph(line, body))
        block.append(Spacer(1, 6))
        story.append(KeepTogether(block[:6]))  # keep heading + first lines together
        for item in block[6:]:
            story.append(item)

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4))
    story.append(Paragraph(
        "Generated by Agentic Research Paper Evaluator v1.0.0  ·  CrewAI  ·  OpenAI GPT-4o-mini",
        center
    ))
    story.append(Paragraph(
        "Done by <b>Dinakar S</b>  ·  ⚠️ AI-generated — validate with human experts",
        center
    ))

    doc.build(story)
    return buf.getvalue()


def generate_markdown_report(report: dict) -> str:
    meta = report["metadata"]
    sc = report["scores"]
    fi = report.get("findings", {})
    rec = report.get("recommendation", "NEEDS_REVISION")
    overall = report["overall_score"]

    return f"""# Research Paper Evaluation Report

## Paper Information
- **Title**: {meta.get("title", "N/A")}
- **arXiv ID**: {meta.get("arxiv_id", "N/A")}
- **Authors**: {", ".join(meta.get("authors", [])[:5])}
- **Published**: {str(meta.get("published", "N/A"))[:10]}
- **Categories**: {", ".join(meta.get("categories", []))}
- **Evaluation Date**: {str(meta.get("evaluation_date", "N/A"))[:10]}

---

## Executive Summary

**Recommendation**: {rec}
**Overall Score**: {overall}/100

---

## Scores

| Metric | Score |
|--------|-------|
| Consistency | {sc["consistency"]}/100 |
| Grammar Rating | {sc["grammar"]} |
| Novelty Index | {sc["novelty"]} |
| Fabrication Risk | {sc["authenticity"]}% |

---

## Detailed Findings

### Consistency Analysis
{fi.get("consistency_analysis", "N/A")}

### Grammar & Language Quality
{fi.get("grammar_analysis", "N/A")}

### Novelty Assessment
{fi.get("novelty_analysis", "N/A")}

### Fact-Check Log
{fi.get("factcheck_log", "N/A")}

### Authenticity Audit
{fi.get("authenticity_analysis", "N/A")}

---
*Generated by Agentic Research Paper Evaluator v1.0.0 · CrewAI · OpenAI GPT-4o-mini*
*Done by **Dinakar S***
"""


def display_results(report: dict, show_detailed: bool):
    scores = report["scores"]
    recommendation = report.get("recommendation", "NEEDS_REVISION")
    overall = report["overall_score"]

    st.subheader("📊 Evaluation Results")
    title = report["metadata"].get("title", "Research Paper")
    st.markdown(f"**Paper:** {title}")
    eval_time = report["metadata"].get("evaluation_time_seconds", 0)
    eval_date = str(report["metadata"].get("evaluation_date", ""))[:10]
    st.caption(f"Evaluated on {eval_date} · took {eval_time:.0f}s")
    st.divider()

    # ── Executive Summary ──────────────────────────────────────────────────
    st.subheader("📋 Executive Summary")

    rec_map = {
        "ACCEPT": (
            "✅ ACCEPT",
            "recommendation-accept",
            "Paper meets quality standards and is recommended for publication.",
        ),
        "REJECT": (
            "❌ REJECT",
            "recommendation-reject",
            "Significant issues detected. Major revisions or rejection recommended.",
        ),
        "NEEDS_REVISION": (
            "⚠️ NEEDS REVISION",
            "recommendation-revision",
            "Paper shows potential but requires substantial revisions before acceptance.",
        ),
    }
    rec_label, rec_class, rec_desc = rec_map.get(recommendation, rec_map["NEEDS_REVISION"])

    st.markdown(f"""
    <div class="{rec_class}">
        <h3 style="margin:0 0 0.5rem 0">{rec_label}</h3>
        <p style="margin:0">{rec_desc}</p>
        <p style="margin:0.6rem 0 0 0;font-weight:600">Overall Score: {overall}/100</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Score Cards ────────────────────────────────────────────────────────
    cols = st.columns(5)
    consistency = scores["consistency"]
    grammar = scores["grammar"]
    novelty = scores["novelty"]
    auth_risk = scores["authenticity"]
    auth_color = "#28a745" if auth_risk <= 30 else ("#e6a817" if auth_risk <= 60 else "#dc3545")

    with cols[0]:
        score_card("Overall Score", f"{overall}/100", score_color(overall), "Weighted avg")
    with cols[1]:
        score_card("Consistency", f"{consistency}/100", score_color(consistency), "Method↔Results")
    with cols[2]:
        score_card("Grammar", grammar, grammar_color(grammar), "Writing quality")
    with cols[3]:
        score_card("Novelty", novelty, novelty_color(novelty), "Originality")
    with cols[4]:
        score_card("Fabrication Risk", f"{auth_risk}%", auth_color, "Lower is better")

    # ── Detailed Findings ──────────────────────────────────────────────────
    if show_detailed:
        st.divider()
        st.subheader("📝 Detailed Agent Analysis")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            f"🔗 Consistency ({consistency}/100)",
            f"✍️ Grammar ({grammar})",
            f"💡 Novelty ({novelty})",
            "🔍 Fact Check",
            f"🛡️ Authenticity ({auth_risk}%)",
        ])
        findings = report.get("findings", {})

        with tab1:
            st.markdown("### Consistency Analysis")
            st.write(findings.get("consistency_analysis") or "No analysis available.")
        with tab2:
            st.markdown("### Grammar & Language Quality")
            st.write(findings.get("grammar_analysis") or "No analysis available.")
        with tab3:
            st.markdown("### Novelty Assessment")
            st.write(findings.get("novelty_analysis") or "No analysis available.")
        with tab4:
            st.markdown("### Fact-Check Log")
            st.write(findings.get("factcheck_log") or "No analysis available.")
        with tab5:
            st.markdown("### Authenticity Audit")
            st.write(findings.get("authenticity_analysis") or "No analysis available.")

    # ── Downloads ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("⬇️ Download Report")
    arxiv_id = report["metadata"].get("arxiv_id", "report")
    col1, col2 = st.columns(2)
    with col1:
        with st.spinner("Generating PDF…"):
            pdf_bytes = generate_pdf_report(report)
        st.download_button(
            "📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"evaluation_{arxiv_id}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "📝 Download Markdown",
            data=generate_markdown_report(report),
            file_name=f"evaluation_{arxiv_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.divider()
    if st.button("🔄 Evaluate Another Paper", use_container_width=True):
        st.session_state.report = None
        st.session_state.arxiv_input = ""
        st.rerun()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Session state init
    if "arxiv_input" not in st.session_state:
        st.session_state.arxiv_input = ""
    if "report" not in st.session_state:
        st.session_state.report = None

    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;font-size:2rem">🔬 Agentic Research Paper Evaluator</h1>
        <p style="margin:0.5rem 0 0 0;opacity:0.85;font-size:1rem">
            Multi-agent AI peer-review simulation · Consistency · Grammar · Novelty · Fact-Check · Authenticity
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("API Status")
        try:
            from core.llm_manager import get_llm_manager
            llm = get_llm_manager()
            any_connected = False
            if llm.openai_client:
                st.success(f"✓ OpenAI ({llm.primary_model})")
                any_connected = True
            if llm.openrouter_client:
                st.success("✓ OpenRouter Connected")
                any_connected = True
            if llm.google_key:
                st.success("✓ Google Gemini Connected")
                any_connected = True
            if not any_connected:
                st.error("✗ No LLM Provider")
                st.info("Add API keys to .env file")
        except Exception as e:
            st.error(f"✗ Error: {str(e)[:60]}")

        st.divider()
        st.subheader("Settings")
        show_detailed = st.checkbox("Show Detailed Analysis", value=True)

        st.divider()
        st.subheader("Scoring Weights")
        st.markdown("""
| Metric | Weight |
|--------|--------|
| Consistency | 30% |
| Authenticity | 30% |
| Grammar | 20% |
| Novelty | 20% |
        """)

        st.divider()
        st.subheader("Agents")
        for agent in ["Consistency Analyst", "Grammar Expert", "Novelty Scout", "Fact Checker", "Authenticity Auditor"]:
            st.markdown(f"• {agent}")

        st.divider()
        st.caption("v1.0.0 · CrewAI · GPT-4o-mini")
        st.caption("Done by **Dinakar S**")

    # ── Input ──────────────────────────────────────────────────────────────
    st.subheader("📥 Input Paper")
    tab_arxiv, tab_pdf = st.tabs(["🌐 arXiv Paper", "📄 Upload PDF"])

    with tab_arxiv:
        col_in, col_ex = st.columns([3, 1])

        with col_in:
            arxiv_input = st.text_input(
                "arXiv ID or URL",
                value=st.session_state.arxiv_input,
                placeholder="e.g., 2303.08774  or  https://arxiv.org/abs/2303.08774",
                help="Enter an arXiv paper ID (e.g. 2303.08774) or full arXiv URL",
            )
            evaluate_arxiv = st.button(
                "🚀 Evaluate Paper",
                type="primary",
                use_container_width=True,
                key="btn_arxiv",
                disabled=not arxiv_input.strip(),
            )

        with col_ex:
            st.markdown("**Quick Examples**")
            examples = {
                "GPT-4": "2303.08774",
                "Transformer": "1706.03762",
                "BERT": "1810.04805",
                "ResNet": "1512.03385",
            }
            for name, aid in examples.items():
                if st.button(name, key=f"ex_{aid}", use_container_width=True):
                    st.session_state.arxiv_input = aid
                    st.rerun()

    with tab_pdf:
        uploaded_file = st.file_uploader(
            "Upload a research paper PDF",
            type=["pdf"],
            help="Upload a local PDF of the paper you want to evaluate",
        )
        if uploaded_file:
            st.success(f"✅ **{uploaded_file.name}** ({uploaded_file.size // 1024} KB) ready")
        evaluate_pdf = st.button(
            "🚀 Evaluate PDF",
            type="primary",
            use_container_width=True,
            key="btn_pdf",
            disabled=uploaded_file is None,
        )

    # ── Run Evaluation ─────────────────────────────────────────────────────
    run_arxiv = evaluate_arxiv and arxiv_input.strip()
    run_pdf = evaluate_pdf and uploaded_file is not None

    if run_arxiv or run_pdf:
        st.divider()
        st.subheader("⏳ Running Evaluation")

        progress_bar = st.progress(0)
        status = st.empty()

        # Live agent step display
        agent_steps = [
            ("🔗 Consistency Agent",   "Checking methodology vs results alignment…"),
            ("✍️ Grammar Agent",        "Evaluating language quality and academic tone…"),
            ("💡 Novelty Agent",        "Comparing against existing literature…"),
            ("🔍 Fact-Check Agent",     "Verifying claims, formulas, and data…"),
            ("🛡️ Authenticity Agent",   "Calculating fabrication risk score…"),
        ]
        step_placeholders = []
        steps_container = st.container()
        with steps_container:
            for icon_name, _ in agent_steps:
                ph = st.empty()
                ph.markdown(
                    f"<div style='padding:0.5rem 1rem;border-left:3px solid #444;"
                    f"color:#888;margin:3px 0;border-radius:4px'>"
                    f"⬜ {icon_name}</div>", unsafe_allow_html=True
                )
                step_placeholders.append(ph)

        def mark_step(idx: int, done: bool = False):
            icon_name, desc = agent_steps[idx]
            if done:
                step_placeholders[idx].markdown(
                    f"<div style='padding:0.5rem 1rem;border-left:3px solid #28a745;"
                    f"background:#1a2e1a;color:#6fcf97;margin:3px 0;border-radius:4px'>"
                    f"✅ {icon_name} — done</div>", unsafe_allow_html=True
                )
            else:
                step_placeholders[idx].markdown(
                    f"<div style='padding:0.5rem 1rem;border-left:3px solid #2d6a9f;"
                    f"background:#1a2535;color:#7ec8e3;margin:3px 0;border-radius:4px'>"
                    f"⚙️ {icon_name} — {desc}</div>", unsafe_allow_html=True
                )

        try:
            evaluator = ArxivEvaluator()
        except Exception as e:
            st.error(f"Failed to initialize evaluator: {e}")
            st.exception(e)
            st.stop()

        try:
            if run_arxiv:
                status.info("📡 Fetching paper from arXiv…")
                progress_bar.progress(8)

                arxiv_client = ArxivClient()
                metadata = arxiv_client.get_paper_metadata(arxiv_input.strip())

                with st.expander("📄 Paper Details", expanded=True):
                    st.markdown(f"**Title:** {metadata['title']}")
                    authors = metadata["authors"]
                    auth_str = ", ".join(authors[:4]) + (f" +{len(authors)-4} more" if len(authors) > 4 else "")
                    st.markdown(f"**Authors:** {auth_str}")
                    st.markdown(f"**Published:** {metadata['published'].strftime('%B %d, %Y')}")
                    st.markdown(f"**Categories:** {', '.join(metadata['categories'])}")
                    with st.expander("Abstract"):
                        st.write(metadata["abstract"])

                progress_bar.progress(15)

            else:  # PDF
                status.info("📄 Parsing uploaded PDF…")
                progress_bar.progress(10)

                pdf_bytes = uploaded_file.read()
                with st.expander("📄 File Details", expanded=True):
                    st.markdown(f"**File:** {uploaded_file.name}")
                    st.markdown(f"**Size:** {len(pdf_bytes) // 1024} KB")

                progress_bar.progress(15)

            # Activate each step visually then run evaluation
            # (CrewAI runs sequentially so we light them up before kickoff
            #  and tick each one done as we parse the output after)
            for i in range(5):
                mark_step(i, done=False)

            status.info("🤖 Running 5 specialized agents — please wait (1–3 min)…")

            if run_arxiv:
                report = evaluator.evaluate_paper(arxiv_input.strip())
            else:
                report = evaluator.evaluate_from_pdf(pdf_bytes, uploaded_file.name)

            # Mark all steps done once complete
            for i in range(5):
                mark_step(i, done=True)
                progress_bar.progress(15 + (i + 1) * 16)

            progress_bar.progress(100)
            status.success("✅ All agents complete — report ready!")
            st.session_state.report = report

        except Exception as e:
            progress_bar.empty()
            st.error(f"❌ Evaluation failed: {e}")
            st.exception(e)
            st.stop()

    # ── Show Results ───────────────────────────────────────────────────────
    if st.session_state.report:
        st.divider()
        display_results(st.session_state.report, show_detailed)

    # Footer
    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#888;padding:1rem'>"
        "Built with CrewAI &nbsp;·&nbsp; Powered by OpenAI GPT-4o-mini"
        "<br><b style='color:#555'>Done by Dinakar S</b> &nbsp;·&nbsp; "
        "⚠️ AI-generated analysis — validate with human experts"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
