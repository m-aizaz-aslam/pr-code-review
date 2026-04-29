import os
import requests

# =========================
# CONFIG
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_REF = os.getenv("GITHUB_REF")

MAX_DIFF_LENGTH = 12000

# 🔥 Fallback model list (most important part)
GEMINI_MODELS = [
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash-latest",
]


# =========================
# READ DIFF
# =========================
def get_diff():
    try:
        with open("diff.txt", "r", encoding="utf-8") as f:
            diff = f.read()

        if not diff.strip():
            return None

        return diff[:MAX_DIFF_LENGTH]

    except Exception as e:
        print(f"Error reading diff: {e}")
        return None


# =========================
# RULE-BASED CHECKS
# =========================
def basic_checks(diff):
    issues = []
    lower = diff.lower()

    if ".collect(" in diff:
        issues.append("[HIGH] Avoid collect() on large datasets")

    if "select *" in lower:
        issues.append("[MEDIUM] Avoid SELECT * usage")

    if "cross join" in lower:
        issues.append("[HIGH] Cross join detected")

    if ".cache(" in diff and "unpersist" not in lower:
        issues.append("[LOW] cache() used without unpersist")

    return issues


# =========================
# GEMINI CALL WITH FALLBACK
# =========================
def review_with_gemini(diff):
    """
    Tries multiple Gemini models until one works.
    """

    prompt = f"""
You are a senior data engineer reviewing a PR.

Focus on:
- PySpark performance
- SQL optimization
- YAML correctness
- schema evolution issues

Return concise bullet points with severity.

Code diff:
{diff}
"""

    for model in GEMINI_MODELS:
        try:
            print(f"Trying model: {model}")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

            response = requests.post(
                url,
                json={
                    "contents": [
                        {"parts": [{"text": prompt}]}
                    ]
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

            else:
                print(f"Model {model} failed: {response.text}")

        except Exception as e:
            print(f"Error with model {model}: {e}")

    return "⚠️ AI review failed with all Gemini models."


# =========================
# POST COMMENT TO GITHUB
# =========================
def post_comment(comment):
    try:
        pr_number = GITHUB_REF.split("/")[-2]

        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments"

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.post(url, headers=headers, json={"body": comment})

        if response.status_code in [200, 201]:
            print("Comment posted successfully.")
        else:
            print(f"Failed to post comment: {response.status_code} {response.text}")

    except Exception as e:
        print(f"Error posting comment: {e}")


# =========================
# MAIN
# =========================
def main():
    print("Starting AI Code Review...")

    diff = get_diff()

    if not diff:
        print("No diff found.")
        return

    # Rule-based checks
    rule_issues = basic_checks(diff)

    # AI review (with fallback)
    ai_review = review_with_gemini(diff)

    # Build comment
    comment = "## 🤖 AI Code Review\n\n"

    # Rule-based section
    comment += "### ⚠️ Rule-Based Issues\n"
    if rule_issues:
        for i in rule_issues:
            comment += f"- {i}\n"
    else:
        comment += "No major rule-based issues detected.\n"

    # AI section
    comment += "\n### 🧠 Gemini Review\n"
    comment += ai_review

    # Post to PR
    post_comment(comment)

    print("Review completed.")


if __name__ == "__main__":
    main()
