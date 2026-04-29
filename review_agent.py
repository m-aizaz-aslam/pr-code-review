import os
import requests
from google import genai

# =========================
# CONFIG
# =========================
API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_REF = os.getenv("GITHUB_REF")

MAX_DIFF = 12000

# =========================
# INIT GEMINI CLIENT (OFFICIAL WAY)
# =========================
client = genai.Client(api_key=API_KEY)


# =========================
# GET DIFF
# =========================
def get_diff():
    with open("diff.txt", "r", encoding="utf-8") as f:
        diff = f.read()

    return diff[:MAX_DIFF] if diff else None


# =========================
# RULE CHECKS
# =========================
def rule_checks(diff):
    issues = []
    lower = diff.lower()

    if ".collect(" in diff:
        issues.append("[HIGH] Avoid collect() in PySpark")

    if "select *" in lower:
        issues.append("[MEDIUM] SELECT * detected")

    if "cross join" in lower:
        issues.append("[HIGH] Cross join detected")

    return issues


# =========================
# GEMINI REVIEW (OFFICIAL SDK)
# =========================
def gemini_review(diff):
    prompt = f"""
You are a senior data engineer.

Review this PR diff for:
- PySpark performance issues
- SQL anti-patterns
- YAML issues
- schema risks

Return concise bullet points with severity.

CODE:
{diff}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


# =========================
# POST COMMENT
# =========================
def post_comment(text):
    pr_number = GITHUB_REF.split("/")[-2]

    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    requests.post(url, headers=headers, json={"body": text})


# =========================
# MAIN
# =========================
def main():
    print("Starting AI Code Review...")

    diff = get_diff()

    if not diff:
        print("No diff found")
        return

    rules = rule_checks(diff)
    ai = gemini_review(diff)

    comment = "## 🤖 AI Code Review\n\n"

    comment += "### ⚠️ Rule-Based\n"
    comment += "\n".join(rules) if rules else "No issues found."

    comment += "\n\n### 🧠 Gemini Review\n"
    comment += ai

    post_comment(comment)

    print("Review completed.")


if __name__ == "__main__":
    main()
