# Resume Optimizer

Tailors a Markdown resume to one or more job descriptions using OpenAI (`gpt-4o-mini`), then exports each version as Markdown, HTML and PDF.

## Files

| File | What it is |
|---|---|
| `tailor_resume.py` | The script (prompt → API call → Markdown → HTML → PDF) |
| `resume.md` | Your resume in Markdown. **Replace the sample with your own.** |
| `resume.css` | Styling for the HTML/PDF output |
| `jobs/*.txt` | One job description per file |
| `output/` | Generated resumes land here |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."   # get one at platform.openai.com/api-keys
```

**PDF engine:** `pdfkit` needs the `wkhtmltopdf` program installed. If it isn't, the script automatically falls back to headless Google Chrome, which needs nothing extra.

## Usage

```bash
# One job
python tailor_resume.py --job jobs/ml_engineer.txt

# Every .txt in a folder (this is where Python beats ChatGPT — it scales)
python tailor_resume.py --job jobs/

# Test the PDF export without spending API credits
python tailor_resume.py --job jobs/ --no-ai

# Options
python tailor_resume.py --resume my_resume.md --job jobs/ --out output/ --model gpt-4o-mini
```

## Ideas for next steps

- Experiment with the prompt in `PROMPT_TEMPLATE` (step 2 of the project).
- Add a cover-letter generator using the same pattern.
- Have the model return a list of keywords from the job description that your resume is missing.
- Always review the output — LLMs can exaggerate. The prompt tells it not to invent experience, but check anyway.
