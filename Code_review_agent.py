"""
Code Review Agent
Uses Agno + Groq to review GitHub repos and output structured JSON reports.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.github import GithubTools

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OUTPUT_DIR   = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Review prompt ────────────────────────────────────────────────────────────

REVIEW_SYSTEM_PROMPT = """
You are a senior software engineer conducting a thorough code review.
Analyse the provided GitHub repository and return a structured JSON report with EXACTLY this schema:

{
  "repo_name": "<owner/repo>",
  "summary": "<2-3 sentence executive summary>",
  "overall_score": <integer 1-10>,
  "language_breakdown": [{"language": "...", "percentage": ...}],
  "sections": [
    {
      "title": "Code Quality",
      "findings": [
        {"severity": "high|medium|low|info", "file": "...", "line": "...", "issue": "...", "suggestion": "..."}
      ]
    },
    {
      "title": "Security",
      "findings": [...]
    },
    {
      "title": "Performance",
      "findings": [...]
    },
    {
      "title": "Best Practices",
      "findings": [...]
    },
    {
      "title": "Documentation",
      "findings": [...]
    }
  ],
  "top_recommendations": ["...", "...", "..."],
  "positive_highlights": ["...", "...", "..."]
}

Rules:
- severity "high" = bugs / security holes
- severity "medium" = code smells / maintainability issues
- severity "low" = style / minor improvements
- severity "info" = observations / praise
- Be specific: mention actual filenames and approximate line numbers when possible
- Return ONLY valid JSON, no markdown fences, no preamble
""".strip()

SEVERITY_EMOJI = {"high": "\U0001f534", "medium": "\U0001f7e0", "low": "\U0001f7e1", "info": "\U0001f535"}

# ── Agent ────────────────────────────────────────────────────────────────────

def build_agent() -> Agent:
    """Build the Agno agent with Groq LLM and GitHub tools."""
    gh = GithubTools(
        access_token=GITHUB_TOKEN or None,
        include_tools=[
            "get_repository",
            "get_repository_languages",
            "get_directory_content",
            "get_file_content",
            "list_issues",
        ],
    )

    return Agent(
        model=Groq(id="llama-3.1-8b-instant", api_key=GROQ_API_KEY),
        tools=[gh],
        system_message=REVIEW_SYSTEM_PROMPT,
        markdown=False,
    )


def run_review(repo_url: str) -> dict:
    """Run the agent and parse the JSON report."""
    agent = build_agent()

    # Normalise URL → owner/repo
    repo_path = repo_url.rstrip("/").replace("https://github.com/", "")

    prompt = f"""
Review the GitHub repository: {repo_path}

Steps:
1. Use get_repository to get repo info
2. Use get_directory_content to list top-level files
3. Use get_file_content to read 2-3 key source files only (keep it brief)
4. Based on what you read, produce your JSON review

Return your full JSON report now.
""".strip()

    try:
        response = agent.run(prompt)
        raw = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return _fallback_report(repo_path, f"Agent failed: {str(e)[:300]}")

    # Strip accidental markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_report(repo_path, raw[:500])


def _fallback_report(repo_path: str, summary: str) -> dict:
    """Return an empty-structure report when the agent fails or returns invalid JSON."""
    return {
        "repo_name": repo_path,
        "summary": summary,
        "overall_score": 0,
        "language_breakdown": [],
        "sections": [],
        "top_recommendations": [],
        "positive_highlights": [],
    }


# ── Markdown report ──────────────────────────────────────────────────────────

def to_markdown(data: dict, output_path: Path) -> None:
    """Generate a Markdown report from the review data."""
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines += [
        f"# Code Review Report — `{data['repo_name']}`",
        f"_Generated {ts}_",
        "",
        "## Executive Summary",
        data.get("summary", ""),
        "",
        f"**Overall Score:** {'⭐' * data.get('overall_score', 0)} ({data.get('overall_score', '?')}/10)",
        "",
    ]

    # Language breakdown
    langs = data.get("language_breakdown", [])
    if langs:
        lines += ["## Language Breakdown", ""]
        for lang in langs:
            lines.append(f"- **{lang['language']}** — {lang['percentage']}%")
        lines.append("")

    # Sections
    for section in data.get("sections", []):
        lines += [f"## {section['title']}", ""]
        findings = section.get("findings", [])
        if not findings:
            lines += ["_No issues found._", ""]
            continue
        for f in findings:
            sev   = f.get("severity", "info")
            emoji = SEVERITY_EMOJI.get(sev, "•")
            loc   = f" `{f['file']}`" if f.get("file") else ""
            line  = f" (line {f['line']})" if f.get("line") else ""
            lines += [
                f"{emoji} **[{sev.upper()}]{loc}{line}**",
                f"- **Issue:** {f.get('issue', '')}",
                f"- **Fix:** {f.get('suggestion', '')}",
                "",
            ]

    # Recommendations
    recs = data.get("top_recommendations", [])
    if recs:
        lines += ["## Top Recommendations", ""]
        for i, r in enumerate(recs, 1):
            lines.append(f"{i}. {r}")
        lines.append("")

    # Highlights
    highs = data.get("positive_highlights", [])
    if highs:
        lines += ["## Positive Highlights", ""]
        for h in highs:
            lines.append(f"- {h}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown saved -> {output_path}")


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python Code_review_agent.py <github_repo_url>")
        print("  e.g. python Code_review_agent.py https://github.com/pallets/flask")
        sys.exit(1)

    repo_url = sys.argv[1]
    print(f"\nReviewing repository: {repo_url}\n{'─' * 60}")

    data = run_review(repo_url)

    slug = data.get("repo_name", repo_url.rstrip("/").split("/")[-1]).replace("/", "_")
    ts   = datetime.now().strftime("%Y%m%d_%H%M")

    md_path = OUTPUT_DIR / f"review_{slug}_{ts}.md"
    to_markdown(data, md_path)

    print(f"\n{'─' * 60}")
    print(f"Score: {data.get('overall_score', '?')}/10")
    print(f"Summary: {data.get('summary', '')[:120]}...")
    recs = data.get("top_recommendations", [])
    if recs:
        print("\nTop Recommendations:")
        for r in recs[:3]:
            print(f"   - {r}")


if __name__ == "__main__":
    main()