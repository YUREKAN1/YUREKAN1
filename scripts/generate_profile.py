import json
import urllib.request
from pathlib import Path


USERNAME = "YUREKAN1"

START_MARKER = "<!-- AUTO-GENERATED:START -->"
END_MARKER = "<!-- AUTO-GENERATED:END -->"


def github_request(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "YUREKAN1-profile-generator",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_github_data():
    print(f"Fetching GitHub data for {USERNAME}...")

    user = github_request(
        f"https://api.github.com/users/{USERNAME}"
    )

    repos = github_request(
        f"https://api.github.com/users/{USERNAME}/repos"
        "?per_page=100&sort=updated"
    )

    return user, repos


def build_dynamic_section(user, repos):

    public_repos = user["public_repos"]
    followers = user["followers"]
    following = user["following"]

    total_stars = sum(
        repo["stargazers_count"]
        for repo in repos
    )

    # Count languages
    languages = {}

    for repo in repos:
        if repo.get("fork"):
            continue

        language = repo.get("language")

        if language:
            languages[language] = (
                languages.get(language, 0) + 1
            )

    top_languages = sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    # Recent repositories
    recent_repos = [
        repo
        for repo in repos
        if not repo.get("fork")
        and repo["name"] != USERNAME
        and repo["name"] != "github-activity-test"
    ][:6]

    lines = []

    lines.append("### 📊 GitHub Statistics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Public Repositories | **{public_repos}** |")
    lines.append(f"| Followers | **{followers}** |")
    lines.append(f"| Following | **{following}** |")
    lines.append(f"| Total Stars | **{total_stars}** |")
    lines.append("")

    lines.append("### 🧠 Most Used Languages")
    lines.append("")

    if top_languages:
        for language, count in top_languages[:8]:
            lines.append(
                f"- **{language}** — {count} repositories"
            )
    else:
        lines.append("- No language data available.")

    lines.append("")

    lines.append("### 🚀 Recent Projects")
    lines.append("")

    if recent_repos:

        for repo in recent_repos:

            name = repo["name"]
            url = repo["html_url"]

            description = (
                repo.get("description")
                or "No description available."
            )

            language = (
                repo.get("language")
                or "Various"
            )

            stars = repo["stargazers_count"]

            lines.append(
                f"#### [{name}]({url})"
            )
            lines.append("")
            lines.append(description)
            lines.append("")
            lines.append(
                f"`{language}` · ⭐ {stars}"
            )
            lines.append("")

    else:
        lines.append(
            "No public projects available yet."
        )
        lines.append("")

    lines.append(
        "> 🔄 This section is automatically updated "
        "from GitHub."
    )

    return "\n".join(lines)


def update_readme(dynamic_content):

    readme_path = Path("README.md")

    if not readme_path.exists():
        raise FileNotFoundError(
            "README.md was not found."
        )

    readme = readme_path.read_text(
        encoding="utf-8"
    )

    start_index = readme.find(START_MARKER)
    end_index = readme.find(END_MARKER)

    if start_index == -1:
        raise ValueError(
            "AUTO-GENERATED:START marker not found."
        )

    if end_index == -1:
        raise ValueError(
            "AUTO-GENERATED:END marker not found."
        )

    if end_index < start_index:
        raise ValueError(
            "README markers are in the wrong order."
        )

    new_readme = (
        readme[:start_index + len(START_MARKER)]
        + "\n\n"
        + dynamic_content
        + "\n\n"
        + readme[end_index:]
    )

    readme_path.write_text(
        new_readme,
        encoding="utf-8"
    )


def main():

    user, repos = get_github_data()

    dynamic_content = build_dynamic_section(
        user,
        repos
    )

    update_readme(dynamic_content)

    print("")
    print("README.md updated successfully.")
    print("")
    print(f"Repositories : {user['public_repos']}")
    print(f"Followers    : {user['followers']}")
    print(f"Following    : {user['following']}")
    print("")
    print("Recent projects:")

    for repo in repos:

        if (
            not repo.get("fork")
            and repo["name"] != USERNAME
            and repo["name"] != "github-activity-test"
        ):
            print(f"- {repo['name']}")


if __name__ == "__main__":
    main()