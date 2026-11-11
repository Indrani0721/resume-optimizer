"""
Resume Optimizer
----------------
Tailor a Markdown resume to a job description with OpenAI, then export it
as Markdown, HTML and PDF.

Usage:
    export OPENAI_API_KEY="sk-..."
    python tailor_resume.py --resume resume.md --job job_description.txt

    # Batch: tailor to every .txt file in a folder
    python tailor_resume.py --resume resume.md --job jobs/

    # Test the PDF step without calling the API
    python tailor_resume.py --resume resume.md --job job_description.txt --no-ai
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

# ---------------------------------------------------------------------------
# Step 2: the prompt template
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """\
I have a resume formatted in Markdown and a job description. \
Please adapt my resume to better align with the job requirements while \
maintaining a professional tone. Tailor my skills, experiences, and \
achievements to highlight the most relevant points for the position. \
Ensure that my resume still reflects my unique qualifications and strengths \
but emphasizes the skills and experiences that match the job description.

### Here is my resume in Markdown:
{md_resume}

### Here is the job description:
{job_description}

Please modify the resume to:
- Use keywords and phrases from the job description.
- Adjust the bullet points under each role to emphasize relevant skills and achievements.
- Make sure my experiences are presented in a way that matches the required qualifications.
- Maintain clarity, conciseness, and professionalism throughout.
- Do NOT invent jobs, degrees, certifications, or metrics that are not in the original resume.
- Keep the same Markdown structure (headings, bullet lists).

Return ONLY the updated resume in Markdown format, with no commentary and no code fences.
"""


# ---------------------------------------------------------------------------
# Step 3: call the OpenAI API
# ---------------------------------------------------------------------------
def tailor_resume(md_resume: str, job_description: str, model: str = "gpt-4o-mini") -> str:
    from openai import OpenAI  # imported here so --no-ai works without a key

    client = OpenAI()  # reads OPENAI_API_KEY from the environment
    prompt = PROMPT_TEMPLATE.format(md_resume=md_resume, job_description=job_description)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert resume writer and career coach."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
    )
    return strip_code_fences(response.choices[0].message.content)


def strip_code_fences(text: str) -> str:
    """Models sometimes wrap the answer in ```markdown ... ``` — remove that."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# Step 4: Markdown -> HTML -> PDF
# ---------------------------------------------------------------------------
def markdown_to_html(md_text: str, css_path: Path) -> str:
    body = markdown.markdown(md_text, extensions=["extra", "sane_lists"])
    css = css_path.read_text() if css_path.exists() else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Resume</title>
<style>{css}</style></head>
<body>{body}</body></html>"""


CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser",
]


def html_to_pdf(html: str, pdf_path: Path) -> str:
    """Try pdfkit (needs wkhtmltopdf); fall back to headless Chrome."""
    if shutil.which("wkhtmltopdf"):
        import pdfkit
        pdfkit.from_string(html, str(pdf_path), options={"encoding": "UTF-8", "quiet": ""})
        return "pdfkit"

    chrome = next((p for p in CHROME_PATHS if Path(p).exists() or shutil.which(p)), None)
    if not chrome:
        raise RuntimeError(
            "No PDF engine found. Install wkhtmltopdf (for pdfkit) or Google Chrome."
        )
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        tmp_html = f.name
    try:
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_path.resolve()}", f"file://{tmp_html}"],
            check=True, capture_output=True, timeout=60,
        )
    finally:
        os.unlink(tmp_html)
    return "headless Chrome"


# ---------------------------------------------------------------------------
# Glue
# ---------------------------------------------------------------------------
def process(resume_md: str, job_file: Path, out_dir: Path, css: Path, model: str, use_ai: bool):
    job_text = job_file.read_text()
    print(f"→ {job_file.name}")

    tailored = tailor_resume(resume_md, job_text, model) if use_ai else resume_md

    stem = f"resume_{job_file.stem}"
    md_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"
    pdf_path = out_dir / f"{stem}.pdf"

    md_path.write_text(tailored)
    html = markdown_to_html(tailored, css)
    html_path.write_text(html)
    engine = html_to_pdf(html, pdf_path)
    print(f"  saved {md_path}, {html_path.name}, {pdf_path.name} (PDF via {engine})")


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser(description="Tailor a Markdown resume to job descriptions.")
    ap.add_argument("--resume", default=here / "resume.md", type=Path)
    ap.add_argument("--job", required=True, type=Path,
                    help="A job description .txt file, or a folder of them")
    ap.add_argument("--out", default=here / "output", type=Path)
    ap.add_argument("--css", default=here / "resume.css", type=Path)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--no-ai", action="store_true", help="Skip the API call (test PDF export)")
    args = ap.parse_args()

    if not args.no_ai and not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first:  export OPENAI_API_KEY='sk-...'")

    resume_md = args.resume.read_text()
    jobs = sorted(args.job.glob("*.txt")) if args.job.is_dir() else [args.job]
    if not jobs:
        sys.exit(f"No .txt job descriptions found in {args.job}")

    args.out.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        process(resume_md, job, args.out, args.css, args.model, use_ai=not args.no_ai)


if __name__ == "__main__":
    main()
