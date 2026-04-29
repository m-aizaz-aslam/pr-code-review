import os
import requests

# =========================
# CONFIG
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_REF = os.getenv("GITHUB_REF")

MAX_DIFF_LENGTH = 12000  # prevent token overflow


# =========================
# READ DIFF FILE
# =========================
def get_diff():
    try:
        with open("diff.txt", "r", encoding="utf-8") as f:
            diff = f.read()
            if not diff.strip():
                print("No diff content found.")
                return None

            # Truncate if too large
            if len(diff) > MAX_DIFF_LENGTH:
                print("Diff too large, truncating...")
                diff = diff[:MAX_DIFF_LENGTH]

            return diff
    except Exception as e:
        print(f"Error reading diff.txt: {e}")
        return None


# =========================
# RULE-BASED CHECKS
# =========================
def basic_checks(diff):
    issues = []

    lower_diff = diff.lower()

    if ".collect(" in diff:
        issues.append("[HIGH] Avoid using collect() on large datasets (can cause driver OOM)")

    if "select *" in lower_diff:
        issues.append("[MEDIUM] Avoid SELECT * in SQL queries")

    if "repartition(" in diff and "partitionby" not in lower_diff:
        issues.append("[MEDIUM] Check repartition usage; may cause unnecessary shuffle")

    if ".cache(" in diff and "unpersist" not in lower_diff:
        issues.append("[LOW] cache() used without unpersist()")

    if "cross join" in lower_diff:
        issues.append("[HIGH] Cross join detected — verify it's intentional")

    return issues


# =========================
# GEMINI API CALL
# =========================
def review_with_gemini(diff):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

        prompt = f"""
You are a senior data engineer reviewing a pull request.

Context:
- PySpark pipelines
- SQL transformations
- YAML configurations
- Large-scale healthcare data (MAO-004 style pipelines)

Analyze ONLY the code changes below:

{diff}

Focus on:
- Performance issues (Spark transformations, joins, shuffles)
- Bad practices (collect, select *, etc.)
- Schema evolution risks
- Null handling issues
- YAML misconfigurations

Return:
- Bullet points
- Each point should include severity: HIGH / MEDIUM / LOW
- Be concise and actionable
"""

        response = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}]
            },
            timeout=60
        )

        if response.status_code != 200:
            print(f"Gemini API error: {response.status_code}, {response.text}")
            return "⚠️ Gemini API failed."

        data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "⚠️ AI review failed."


# =========================
# POST COMMENT TO PR
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

        if response.status_code not in [200, 201]:
            print(f"Failed to post comment: {response.status_code}, {response.text}")
        else:
            print("Comment posted successfully.")

    except Exception as e:
        print(f"Error posting comment: {e}")


# =========================
# MAIN EXECUTION
# =========================
def main():
    print("Starting AI Code Review...")

    diff = get_diff()

    if not diff:
        print("No diff to analyze. Exiting.")
        return

    # Rule-based checks
    rule_issues = basic_checks(diff)

    # AI Review
    ai_review = review_with_gemini(diff)

    # Build final comment
    comment = "## 🤖 AI Code Review\n\n"

    if rule_issues:
        comment += "### ⚠️ Rule-Based Issues\n"
        for issue in rule_issues:
            comment += f"- {issue}\n"
    else:
        comment += "### ⚠️ Rule-Based Issues\nNo major issues detected.\n"

    comment += "\n### 🧠 Gemini Review\n"
    comment += ai_review

    # Post to PR
    post_comment(comment)

    print("Review completed.")


if __name__ == "__main__":
    main()
