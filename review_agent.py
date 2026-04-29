import os
import re
import requests
from google import genai

# =========================
# CONFIG
# =========================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_REF = os.getenv("GITHUB_REF")

client = genai.Client()


# =========================
# READ FULL DIFF
# =========================
def get_diff():
    with open("diff.txt", "r", encoding="utf-8") as f:
        return f.read()


# =========================
# SPLIT DIFF BY FILE
# =========================
def split_diff_by_file(diff_text):
    """
    Returns:
    {
        "file1.py": "diff...",
        "file2.sql": "diff..."
    }
    """

    file_diffs = {}
    current_file = None
    buffer = []

    for line in diff_text.splitlines():
        # Detect file header
        match = re.match(r"^\+\+\+ b/(.*)", line)

        if match:
            # Save previous file
            if current_file and buffer:
                file_diffs[current_file] = "\n".join(buffer)

            current_file = match.group(1)
            buffer = []
            continue

        if current_file:
            buffer.append(line)

    # last file
    if current_file and buffer:
        file_diffs[current_file] = "\n".join(buffer)

    return file_diffs


# =========================
# GEMINI FILE REVIEW
# =========================
def review_file(file_name, diff):
    prompt = f"""
You are a senior data engineer reviewing ONE file in a PR.

File: {file_name}

Focus on:
- PySpark performance issues
- SQL mistakes
- schema risks
- YAML issues
- bad practices

Return:
- Bullet points
- Severity (HIGH / MEDIUM / LOW)

CODE DIFF:
{diff[:12000]}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    return response.text


# =========================
# POST COMMENT TO PR
# =========================
def post_comment(comment):
    pr_number = GITHUB_REF.split("/")[-2]

    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    requests.post(url, headers=headers, json={"body": comment})


# =========================
# MAIN
# =========================
def main():
    print("Starting AI Code Review (File-wise)...")

    diff = get_diff()

    if not diff:
        print("No diff found")
        return

    file_diffs = split_diff_by_file(diff)

    if not file_diffs:
        print("No files detected in diff")
        return

    final_comment = "## 🤖 AI Code Review (File-wise)\n"

    # Review each file separately
    for file_name, file_diff in file_diffs.items():
        print(f"Reviewing: {file_name}")

        try:
            review = review_file(file_name, file_diff)

            final_comment += f"\n---\n### 📄 {file_name}\n"
            final_comment += review + "\n"

        except Exception as e:
            final_comment += f"\n---\n### 📄 {file_name}\n⚠️ Review failed: {str(e)}\n"

    post_comment(final_comment)

    print("Review completed.")


if __name__ == "__main__":
    main()
