import os
import requests
from google import genai

# =========================
# CONFIG
# =========================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_REF = os.getenv("GITHUB_REF")

# IMPORTANT: SDK reads GEMINI_API_KEY automatically from env
client = genai.Client()


# =========================
# READ DIFF
# =========================
def get_diff():
    with open("diff.txt", "r", encoding="utf-8") as f:
        diff = f.read()

    return diff[:12000] if diff else None


# =========================
# RULE-BASED CHECKS
# =========================
def rule_checks(diff):
    issues = []
    lower = diff.lower()

    if ".collect(" in diff:
        issues.append("[HIGH] Avoid collect() in PySpark (driver overload risk)")

    if "select *" in lower:
        issues.append("[MEDIUM] Avoid SELECT * usage")

    if "cross join" in lower:
        issues.append("[HIGH] Cross join detected")

    if ".cache(" in diff and "unpersist" not in lower:
        issues.append("[LOW] cache() used without unpersist")

    return issues


# =========================
# GEMINI REVIEW (OFFICIAL SDK)
# =========================
def gemini_review(diff):
    prompt = f"""
You are a senior data engineer reviewing a pull request.

Focus on:
- PySpark performance issues
- SQL optimization
- schema design issues
- YAML mistakes

Return concise bullet points with severity.

CODE DIFF:
{diff}
"""

    # 🔥 THIS IS THE CORRECT CALL (from your snippet style)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    return response.text


# =========================
# POST COMMENT TO GITHUB
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

    # Rule-based checks
    rules = rule_checks(diff)

    # AI review (SDK)
    ai_review = gemini_review(diff)

    # Build comment
    comment = "## 🤖 AI Code Review\n\n"

    comment += "### ⚠️ Rule-Based Issues\n"
    comment += "\n".join(rules) if rules else "No rule issues found."

    comment += "\n\n### 🧠 Gemini Review\n"
    comment += ai_review

    post_comment(comment)

    print("Review completed.")


if __name__ == "__main__":
    main()
