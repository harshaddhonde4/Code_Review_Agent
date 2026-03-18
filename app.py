"""
Code Review Agent — Streamlit UI
Beautiful dashboard with Plotly visualizations & PDF download.
"""

import os
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

from Code_review_agent import run_review, SEVERITY_EMOJI

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Review Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.stApp { font-family: 'Inter', sans-serif; }

/* Hero header */
.hero { text-align: center; padding: 2rem 0 1rem; }
.hero h1 {
    font-size: 3rem; font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.hero p { font-size: 1.15rem; color: #888; margin-top: 0; }

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid rgba(102, 126, 234, 0.2); border-radius: 16px;
    padding: 1.5rem; text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
}
.metric-card .value {
    font-size: 2.5rem; font-weight: 800;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-card .label {
    font-size: 0.85rem; color: #aaa;
    text-transform: uppercase; letter-spacing: 1px; margin-top: 0.3rem;
}

/* Severity badges */
.badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.badge-high   { background: #C0392B22; color: #E74C3C; border: 1px solid #E74C3C44; }
.badge-medium { background: #E67E2222; color: #F39C12; border: 1px solid #F39C1244; }
.badge-low    { background: #F1C40F22; color: #F1C40F; border: 1px solid #F1C40F44; }
.badge-info   { background: #2980B922; color: #3498DB; border: 1px solid #3498DB44; }

/* Finding card */
.finding-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-left: 4px solid; border-radius: 8px;
    padding: 1rem 1.2rem; margin: 0.6rem 0;
}
.finding-card.sev-high   { border-left-color: #E74C3C; }
.finding-card.sev-medium { border-left-color: #F39C12; }
.finding-card.sev-low    { border-left-color: #F1C40F; }
.finding-card.sev-info   { border-left-color: #3498DB; }
.finding-card .file-loc {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem; color: #888; margin-bottom: 0.4rem;
}

/* Highlight / Rec cards */
.highlight-card {
    background: linear-gradient(135deg, rgba(39, 174, 96, 0.08), rgba(46, 204, 113, 0.04));
    border: 1px solid rgba(46, 204, 113, 0.2); border-radius: 12px;
    padding: 1rem 1.2rem; margin: 0.5rem 0;
}
.rec-card {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.04));
    border: 1px solid rgba(102, 126, 234, 0.2); border-radius: 12px;
    padding: 1rem 1.2rem; margin: 0.5rem 0;
}

/* Section header */
.section-header {
    font-size: 1.4rem; font-weight: 700;
    margin: 2rem 0 0.8rem; padding-bottom: 0.5rem;
    border-bottom: 2px solid rgba(102, 126, 234, 0.3);
}

/* Input styling */
div[data-testid="stTextInput"] input {
    border-radius: 12px !important;
    border: 2px solid rgba(102, 126, 234, 0.3) !important;
    padding: 0.8rem 1rem !important; font-size: 1.05rem !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 20px rgba(102, 126, 234, 0.15) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Plotly helpers ───────────────────────────────────────────────────────────

def score_gauge(score: int) -> go.Figure:
    """Radial gauge for the overall score."""
    color = "#27AE60" if score >= 8 else "#E67E22" if score >= 5 else "#C0392B"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/10", "font": {"size": 48, "color": "white"}},
        gauge={
            "axis": {"range": [0, 10], "tickwidth": 2, "tickcolor": "#444",
                     "dtick": 2, "tickfont": {"color": "#888"}},
            "bar": {"color": color, "thickness": 0.6},
            "bgcolor": "rgba(255,255,255,0.05)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 4], "color": "rgba(192,57,43,0.12)"},
                {"range": [4, 7], "color": "rgba(230,126,34,0.12)"},
                {"range": [7, 10], "color": "rgba(39,174,96,0.12)"},
            ],
        },
        title={"text": "Overall Score", "font": {"size": 16, "color": "#aaa"}},
    ))
    fig.update_layout(
        height=280, margin=dict(t=60, b=20, l=40, r=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
    )
    return fig


def severity_chart(data: dict) -> go.Figure:
    """Bar chart of findings grouped by severity."""
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for section in data.get("sections", []):
        for f in section.get("findings", []):
            sev = f.get("severity", "info").upper()
            if sev in counts:
                counts[sev] += 1

    colors = {"HIGH": "#E74C3C", "MEDIUM": "#F39C12", "LOW": "#F1C40F", "INFO": "#3498DB"}
    fig = go.Figure(go.Bar(
        x=list(counts.keys()), y=list(counts.values()),
        marker_color=[colors[k] for k in counts],
        marker_line_width=0,
        text=list(counts.values()), textposition="outside",
        textfont={"color": "white", "size": 14, "family": "Inter"},
    ))
    fig.update_layout(
        title={"text": "Issues by Severity", "font": {"size": 16, "color": "#aaa"}, "x": 0.5},
        xaxis={"color": "#888", "showgrid": False},
        yaxis={"color": "#888", "showgrid": True, "gridcolor": "rgba(255,255,255,0.05)"},
        height=300, margin=dict(t=60, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter"},
    )
    return fig


def language_pie(data: dict) -> go.Figure | None:
    """Donut chart of repository languages."""
    langs = data.get("language_breakdown", [])
    if not langs:
        return None
    names = [lang["language"] for lang in langs]
    vals  = [lang["percentage"] for lang in langs]
    fig = px.pie(names=names, values=vals,
                 color_discrete_sequence=px.colors.qualitative.Set2, hole=0.45)
    fig.update_layout(
        title={"text": "Language Breakdown", "font": {"size": 16, "color": "#aaa"}, "x": 0.5},
        height=300, margin=dict(t=60, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Inter"},
        legend={"font": {"color": "#ccc"}},
    )
    fig.update_traces(
        textfont_color="white",
        marker=dict(line=dict(color="rgba(0,0,0,0.3)", width=2)),
    )
    return fig


# ── PDF generation ───────────────────────────────────────────────────────────

def safe_text(text) -> str:
    """Sanitize text for fpdf2 Helvetica (Latin-1 only)."""
    s = str(text)
    replacements = {
        '\u2014': '-', '\u2013': '-',
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2026': '...', '\u2022': '*',
        '\u2713': '[x]', '\u2717': '[!]',
        '\u2192': '->', '\u00a0': ' ',
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode('latin-1', errors='replace').decode('latin-1')


class ReviewPDF(FPDF):
    """Custom FPDF subclass with branded header/footer."""
    def header(self):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(102, 126, 234)
        self.cell(0, 12, "Code Review Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


SEV_STYLES = {
    "high":   {"text": (231, 76, 60),  "bg": (253, 237, 236), "border": (245, 183, 177)},
    "medium": {"text": (243, 156, 18), "bg": (254, 245, 231), "border": (245, 203, 167)},
    "low":    {"text": (241, 196, 15), "bg": (254, 249, 231), "border": (249, 231, 159)},
    "info":   {"text": (52, 152, 219), "bg": (235, 245, 251), "border": (174, 214, 241)},
}


def generate_pdf(data: dict) -> bytes:
    """Generate a styled PDF report from the review data."""
    pdf = ReviewPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # ── Header Banner ────────────────────────────────────────────────────
    pdf.set_fill_color(102, 126, 234)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(w, 20, " Code Review Report", border=0, fill=True, align="L",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── Repository Info ──────────────────────────────────────────────────
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(w, 8, safe_text(f"Repository: {data.get('repo_name', 'Unknown')}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(w, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── Metrics Row ──────────────────────────────────────────────────────
    score = data.get("overall_score", 0)
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for section in data.get("sections", []):
        for f in section.get("findings", []):
            sev = f.get("severity", "info").upper()
            if sev in counts:
                counts[sev] += 1

    pdf.set_fill_color(245, 247, 255)
    pdf.set_draw_color(200, 210, 240)
    pdf.set_line_width(0.5)
    metrics_y = pdf.get_y()

    # Score Cell
    if score >= 8:
        pdf.set_text_color(39, 174, 96)
    elif score >= 5:
        pdf.set_text_color(230, 126, 34)
    else:
        pdf.set_text_color(192, 57, 43)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(w / 3, 16, f"Score: {score}/10", border=1, fill=True, align="C")

    # Issues Cell
    pdf.set_xy(pdf.get_x() + 5, metrics_y)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font("Helvetica", "B", 11)
    issues_text = f"Issues: {counts['HIGH']} High | {counts['MEDIUM']} Med | {counts['LOW']} Low"
    pdf.cell(w - (w / 3) - 5, 16, safe_text(issues_text), border=1, fill=True,
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # ── Section Header helper ────────────────────────────────────────────
    def _section_header(title: str):
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(50, 50, 60)
        pdf.cell(w, 10, safe_text(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(102, 126, 234)
        pdf.set_line_width(1)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + w, pdf.get_y())
        pdf.ln(4)

    # ── Summary ──────────────────────────────────────────────────────────
    _section_header("Executive Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(w, 6, safe_text(data.get("summary", "N/A")))
    pdf.ln(6)

    # ── Language Breakdown ───────────────────────────────────────────────
    langs = data.get("language_breakdown", [])
    if langs:
        _section_header("Language Breakdown")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(70, 70, 70)
        for lang in langs:
            pdf.set_fill_color(240, 240, 240)
            pdf.set_draw_color(220, 220, 220)
            text = safe_text(f" {lang['language']}: {lang['percentage']}% ")
            text_w = pdf.get_string_width(text) + 6
            if pdf.get_x() + text_w > w:
                pdf.ln(8)
            pdf.cell(text_w, 8, text, border=1, fill=True, align="C")
            pdf.set_x(pdf.get_x() + 4)
        pdf.ln(12)

    # ── Detailed Findings ────────────────────────────────────────────────
    _section_header("Detailed Findings")
    has_findings = False

    for section in data.get("sections", []):
        findings = section.get("findings", [])
        if not findings:
            continue

        has_findings = True
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(80, 80, 90)
        pdf.cell(w, 8, safe_text(section.get("title", "")), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for f in findings:
            sev = f.get("severity", "info").lower()
            style = SEV_STYLES.get(sev, SEV_STYLES["info"])

            pdf.set_fill_color(*style["bg"])
            pdf.set_draw_color(*style["border"])
            pdf.set_line_width(0.3)

            # Severity badge + file
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*style["text"])
            loc = safe_text(f.get("file", ""))
            if f.get("line"):
                loc += f" (L{f['line']})"
            pdf.cell(w, 7, f"  [{sev.upper()}]  {loc}", border="L T R", fill=True,
                     new_x="LMARGIN", new_y="NEXT")

            # Issue text
            pdf.set_text_color(50, 50, 50)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_x(pdf.get_x() + 2)
            pdf.multi_cell(w - 4, 5, safe_text(f"Issue: {f.get('issue', '')}"),
                           border=0, fill=True)

            # Fix text
            pdf.set_xy(pdf.l_margin, pdf.get_y())
            pdf.set_text_color(100, 100, 100)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_x(pdf.get_x() + 2)
            pdf.multi_cell(w - 4, 5, safe_text(f"Fix: {f.get('suggestion', '')}"),
                           border=0, fill=True)

            # Close the card
            pdf.set_xy(pdf.l_margin, pdf.get_y())
            pdf.cell(w, 2, "", border="L B R", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

    if not has_findings:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(w, 10, "No issues found in the analysis.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── Recommendations ──────────────────────────────────────────────────
    recs = data.get("top_recommendations", [])
    if recs:
        _section_header("Top Recommendations")
        pdf.set_fill_color(244, 246, 255)
        pdf.set_draw_color(200, 210, 240)
        pdf.set_text_color(60, 60, 80)
        pdf.set_font("Helvetica", "", 10)
        for i, r in enumerate(recs, 1):
            pdf.multi_cell(w, 8, safe_text(f" {i}. {r}"), border=1, fill=True)
            pdf.ln(2)
        pdf.ln(4)

    # ── Highlights ────────────────────────────────────────────────────────
    highs = data.get("positive_highlights", [])
    if highs:
        _section_header("Positive Highlights")
        pdf.set_fill_color(233, 247, 239)
        pdf.set_draw_color(171, 235, 198)
        pdf.set_text_color(30, 100, 50)
        pdf.set_font("Helvetica", "", 10)
        for h in highs:
            pdf.multi_cell(w, 8, safe_text(f" +  {h}"), border=1, fill=True)
            pdf.ln(2)

    return bytes(pdf.output())


# ── Main App ─────────────────────────────────────────────────────────────────

def main():
    # Hero
    st.markdown("""
    <div class="hero">
        <h1>🔍 Code Review Agent</h1>
        <p>AI-powered code analysis · Powered by Groq + Agno</p>
    </div>
    """, unsafe_allow_html=True)

    # Input
    col1, col2 = st.columns([4, 1])
    with col1:
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo",
            label_visibility="collapsed",
        )
    with col2:
        review_btn = st.button("🚀 Review", use_container_width=True, type="primary")

    st.markdown("---")

    # Run review
    if review_btn and repo_url:
        with st.spinner(""):
            status = st.empty()
            progress = st.progress(0)

            status.markdown("⏳ **Initializing agent...**")
            progress.progress(10)
            status.markdown("🔗 **Connecting to GitHub API...**")
            progress.progress(25)
            status.markdown("📂 **Reading repository structure...**")

            data = run_review(repo_url)

            progress.progress(80)
            status.markdown("📊 **Generating report...**")
            st.session_state["review_data"] = data
            progress.progress(100)
            status.empty()
            progress.empty()

    # Display review
    if "review_data" not in st.session_state:
        return

    data = st.session_state["review_data"]
    score = data.get("overall_score", 0)

    # ── Charts Row ───────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.plotly_chart(score_gauge(score), use_container_width=True)
    with c2:
        st.plotly_chart(severity_chart(data), use_container_width=True)
    with c3:
        pie = language_pie(data)
        if pie:
            st.plotly_chart(pie, use_container_width=True)
        else:
            total = sum(len(s.get("findings", [])) for s in data.get("sections", []))
            st.markdown(f"""
            <div class="metric-card">
                <div class="value">{total}</div>
                <div class="label">Total Findings</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Summary ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 Executive Summary</div>',
                unsafe_allow_html=True)
    st.info(data.get("summary", "No summary available."))

    # ── Findings ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔎 Detailed Findings</div>',
                unsafe_allow_html=True)
    sections = data.get("sections", [])
    if sections:
        tabs = st.tabs([s.get("title", "Section") for s in sections])
        for tab, section in zip(tabs, sections):
            with tab:
                findings = section.get("findings", [])
                if not findings:
                    st.markdown("_✅ No issues found in this category._")
                    continue
                for f in findings:
                    sev = f.get("severity", "info").lower()
                    emoji = SEVERITY_EMOJI.get(sev, "•")
                    loc = f.get("file", "")
                    if f.get("line"):
                        loc += f" : L{f['line']}"
                    st.markdown(f"""
                    <div class="finding-card sev-{sev}">
                        <span class="badge badge-{sev}">{emoji} {sev.upper()}</span>
                        <span class="file-loc" style="margin-left: 8px;">{loc}</span>
                        <p style="margin: 0.5rem 0 0.2rem; color: #ddd;">
                            <strong>Issue:</strong> {f.get('issue', '')}</p>
                        <p style="margin: 0; color: #aaa;">
                            <strong>Fix:</strong> {f.get('suggestion', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("_No detailed findings available._")

    # ── Recommendations ──────────────────────────────────────────────
    recs = data.get("top_recommendations", [])
    if recs:
        st.markdown('<div class="section-header">🎯 Top Recommendations</div>',
                    unsafe_allow_html=True)
        for i, r in enumerate(recs, 1):
            st.markdown(f"""
            <div class="rec-card">
                <strong style="color: #667eea;">{i}.</strong> {r}
            </div>
            """, unsafe_allow_html=True)

    # ── Highlights ───────────────────────────────────────────────────
    highs = data.get("positive_highlights", [])
    if highs:
        st.markdown('<div class="section-header">✅ Positive Highlights</div>',
                    unsafe_allow_html=True)
        for h in highs:
            st.markdown(f"""
            <div class="highlight-card">✅ {h}</div>
            """, unsafe_allow_html=True)

    # ── PDF Download ─────────────────────────────────────────────────
    st.markdown("---")
    try:
        pdf_bytes = generate_pdf(data)
        repo_name = data.get("repo_name", "repo").replace("/", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M")

        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"review_{repo_name}_{ts}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )

        # Save locally as well
        os.makedirs("reports", exist_ok=True)
        local_path = f"reports/review_{repo_name}_{ts}.pdf"
        with open(local_path, "wb") as fp:
            fp.write(pdf_bytes)
        st.success(f"PDF saved locally to `{local_path}`")
    except Exception as e:
        st.error(f"⚠️ PDF generation failed: {e}")


if __name__ == "__main__":
    main()
