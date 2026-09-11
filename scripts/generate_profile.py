import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


USERNAME = "YUREKAN1"

START_MARKER = "<!-- AUTO-GENERATED:START -->"
END_MARKER = "<!-- AUTO-GENERATED:END -->"


def github_request(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "YUREKAN1-profile-generator",
    }

    github_token = os.environ.get("GITHUB_TOKEN")

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    request = urllib.request.Request(
        url,
        headers=headers,
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def get_github_data():
    print(f"Fetching GitHub data for {USERNAME}...")

    user = github_request(
        f"https://api.github.com/users/{USERNAME}"
    )

    repos = github_request(
        f"https://api.github.com/users/{USERNAME}/repos"
        "?per_page=100&sort=updated"
    )

    events = github_request(
        f"https://api.github.com/users/{USERNAME}/events/public"
        "?per_page=30"
    )

    return user, repos, events


def project_score(repo):
    """
    Calculate how suitable a repository is
    for displaying on the GitHub profile.
    """

    score = 0

    # -----------------------------------------
    # Project presentation
    # -----------------------------------------

    if repo.get("description"):
        score += 5

    if repo.get("language"):
        score += 3

    # -----------------------------------------
    # Community interest
    # -----------------------------------------

    stars = repo.get(
        "stargazers_count",
        0
    )

    score += stars * 4

    # -----------------------------------------
    # Recent activity
    # -----------------------------------------

    updated_at = repo.get(
        "updated_at"
    )

    if updated_at:

        updated_at = datetime.fromisoformat(
            updated_at.replace(
                "Z",
                "+00:00"
            )
        )

        days_old = (
            datetime.now(timezone.utc)
            - updated_at
        ).days

        if days_old <= 30:
            score += 6

        elif days_old <= 90:
            score += 4

        elif days_old <= 180:
            score += 2

    # -----------------------------------------
    # Repository substance
    # -----------------------------------------

    if repo.get("size", 0) > 0:
        score += 1

    return score


def select_projects(repos):
    """
    Select the strongest repositories to showcase
    on the GitHub profile.
    """

    excluded_repositories = {
        USERNAME.lower(),
        "github-activity-test",
        "dsa",
    }

    candidates = []

    for repo in repos:

        # Don't include forks.
        if repo.get("fork"):
            continue

        # Don't include excluded repositories.
        if repo["name"].lower() in excluded_repositories:
            continue

        candidates.append(repo)

    candidates.sort(
        key=project_score,
        reverse=True,
    )

    # Maximum of six featured projects.
    return candidates[:6]


def format_event(event):
    """
    Convert a GitHub event into a useful,
    human-readable activity description.
    """

    event_type = event.get(
        "type"
    )

    repo = event.get(
        "repo",
        {}
    )

    repo_name = repo.get(
        "name",
        "a repository"
    )

    short_name = repo_name.split(
        "/",
        1
    )[-1]

    # -----------------------------------------
    # Ignore activity from the profile repo.
    # -----------------------------------------

    if short_name.lower() == USERNAME.lower():
        return None

    # =========================================
    # Push event
    # =========================================

    if event_type == "PushEvent":

        payload = event.get(
            "payload",
            {}
        )

        commits = payload.get(
            "commits"
        )

        if commits:

            commit_count = len(
                commits
            )

            if commit_count == 1:

                return (
                    f"💻 Pushed a commit to "
                    f"`{short_name}`"
                )

            return (
                f"💻 Pushed {commit_count} "
                f"commits to `{short_name}`"
            )

        # GitHub sometimes doesn't include
        # commit details in the event.
        return (
            f"💻 Pushed changes to "
            f"`{short_name}`"
        )

    # =========================================
    # Create event
    # =========================================

    if event_type == "CreateEvent":

        payload = event.get(
            "payload",
            {}
        )

        ref_type = payload.get(
            "ref_type"
        )

        if ref_type == "repository":

            return (
                f"🆕 Created repository "
                f"`{short_name}`"
            )

        if ref_type == "branch":

            return (
                f"🌿 Created a branch in "
                f"`{short_name}`"
            )

        if ref_type == "tag":

            return (
                f"🏷️ Created a tag in "
                f"`{short_name}`"
            )

        return (
            f"🆕 Created new content in "
            f"`{short_name}`"
        )

    # =========================================
    # Pull request
    # =========================================

    if event_type == "PullRequestEvent":

        action = event.get(
            "payload",
            {}
        ).get(
            "action",
            "updated"
        )

        return (
            f"🔀 {action.capitalize()} a pull "
            f"request in `{short_name}`"
        )

    # =========================================
    # Issues
    # =========================================

    if event_type == "IssuesEvent":

        action = event.get(
            "payload",
            {}
        ).get(
            "action",
            "updated"
        )

        return (
            f"🐛 {action.capitalize()} an issue "
            f"in `{short_name}`"
        )

    # =========================================
    # Issue comments
    # =========================================

    if event_type == "IssueCommentEvent":

        return (
            f"💬 Commented on an issue "
            f"in `{short_name}`"
        )

    # =========================================
    # Star event
    # =========================================

    if event_type == "WatchEvent":

        # Don't show the user starring their
        # own repositories.
        if repo_name.lower().startswith(
            f"{USERNAME.lower()}/"
        ):
            return None

        return (
            f"⭐ Starred `{short_name}`"
        )

    # =========================================
    # Fork event
    # =========================================

    if event_type == "ForkEvent":

        return (
            f"🍴 Forked `{short_name}`"
        )

    # =========================================
    # Ignore unsupported events
    # =========================================

    return None


def get_recent_activity(events):
    """
    Convert GitHub events into readable activity.
    """

    activity = []
    seen = set()

    for event in events:

        formatted = format_event(
            event
        )

        if not formatted:
            continue

        if formatted in seen:
            continue

        seen.add(
            formatted
        )

        activity.append(
            formatted
        )

        # Keep the activity section compact.
        if len(activity) >= 8:
            break

    return activity


def build_dynamic_section(
    user,
    repos,
    events
):
    """
    Build the automatically generated section
    of the README.
    """

    public_repos = user[
        "public_repos"
    ]

    followers = user[
        "followers"
    ]

    following = user[
        "following"
    ]

    # =========================================
    # Total stars
    # =========================================

    total_stars = sum(
        repo.get(
            "stargazers_count",
            0
        )
        for repo in repos
    )

    # =========================================
    # Languages
    # =========================================

    languages = {}

    for repo in repos:

        if repo.get("fork"):
            continue

        language = repo.get(
            "language"
        )

        if language:

            languages[language] = (
                languages.get(
                    language,
                    0
                ) + 1
            )

    top_languages = sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    # =========================================
    # Featured projects
    # =========================================

    featured_projects = select_projects(
        repos
    )

    # =========================================
    # Recent activity
    # =========================================

    recent_activity = get_recent_activity(
        events
    )

    # =========================================
    # Build README content
    # =========================================

    lines = []

    # -----------------------------------------
    # GitHub statistics
    # -----------------------------------------

    lines.append(
        "### 📊 GitHub Statistics"
    )

    lines.append("")

    lines.append(
        "| Metric | Value |"
    )

    lines.append(
        "|---|---:|"
    )

    lines.append(
        f"| Public Repositories | "
        f"**{public_repos}** |"
    )

    lines.append(
        f"| Followers | "
        f"**{followers}** |"
    )

    lines.append(
        f"| Following | "
        f"**{following}** |"
    )

    lines.append(
        f"| Total Stars | "
        f"**{total_stars}** |"
    )

    lines.append("")

    # -----------------------------------------
    # Most used languages
    # -----------------------------------------

    lines.append(
        "### 🧠 Most Used Languages"
    )

    lines.append("")

    if top_languages:

        for language, count in top_languages[:8]:

            lines.append(
                f"- **{language}** — "
                f"{count} repositories"
            )

    else:

        lines.append(
            "- No language data available."
        )

    lines.append("")

    # -----------------------------------------
    # Featured projects
    # -----------------------------------------

    lines.append(
        "### 🚀 Featured Projects"
    )

    lines.append("")

    if featured_projects:

        for repo in featured_projects:

            name = repo[
                "name"
            ]

            url = repo[
                "html_url"
            ]

            description = (
                repo.get(
                    "description"
                )
                or
                "No description available."
            )

            language = (
                repo.get(
                    "language"
                )
                or
                "Various"
            )

            stars = repo.get(
                "stargazers_count",
                0
            )

            lines.append(
                f"#### [{name}]({url})"
            )

            lines.append("")

            lines.append(
                description
            )

            lines.append("")

            lines.append(
                f"`{language}` · "
                f"⭐ {stars}"
            )

            lines.append("")

    else:

        lines.append(
            "No public projects available yet."
        )

        lines.append("")

    # -----------------------------------------
    # Recent activity
    # -----------------------------------------

    lines.append(
        "### ⚡ Recent GitHub Activity"
    )

    lines.append("")

    if recent_activity:

        for activity in recent_activity:

            lines.append(
                f"- {activity}"
            )

    else:

        lines.append(
            "- No recent public activity available."
        )

    lines.append("")

    # -----------------------------------------
    # Footer
    # -----------------------------------------

    lines.append(
        "> 🔄 This section is automatically "
        "updated from GitHub."
    )

    return "\n".join(
        lines
    )


def update_readme(
    dynamic_content
):
    """
    Replace only the content between the
    AUTO-GENERATED markers.
    """

    readme_path = Path(
        "README.md"
    )

    if not readme_path.exists():

        raise FileNotFoundError(
            "README.md was not found."
        )

    readme = readme_path.read_text(
        encoding="utf-8"
    )

    start_index = readme.find(
        START_MARKER
    )

    end_index = readme.find(
        END_MARKER
    )

    # =========================================
    # Validate markers
    # =========================================

    if start_index == -1:

        raise ValueError(
            "AUTO-GENERATED:START marker "
            "not found."
        )

    if end_index == -1:

        raise ValueError(
            "AUTO-GENERATED:END marker "
            "not found."
        )

    if end_index < start_index:

        raise ValueError(
            "README markers are in the "
            "wrong order."
        )

    # =========================================
    # Replace generated section only
    # =========================================

    new_readme = (
        readme[
            :start_index
            + len(START_MARKER)
        ]
        + "\n\n"
        + dynamic_content
        + "\n\n"
        + readme[
            end_index:
        ]
    )

    readme_path.write_text(
        new_readme.rstrip() + "\n",
        encoding="utf-8"
    )


def main():

    # =========================================
    # Fetch GitHub data
    # =========================================

    user, repos, events = (
        get_github_data()
    )

    # =========================================
    # Select projects
    # =========================================

    featured_projects = (
        select_projects(
            repos
        )
    )

    # =========================================
    # Generate dynamic content
    # =========================================

    dynamic_content = (
        build_dynamic_section(
            user,
            repos,
            events
        )
    )

    # =========================================
    # Update README
    # =========================================

    update_readme(
        dynamic_content
    )

    # =========================================
    # Console output
    # =========================================

    print("")

    print(
        "README.md updated successfully."
    )

    print("")

    print(
        f"Repositories : "
        f"{user['public_repos']}"
    )

    print(
        f"Followers    : "
        f"{user['followers']}"
    )

    print(
        f"Following    : "
        f"{user['following']}"
    )

    print("")

    print(
        "Selected projects:"
    )

    for repo in featured_projects:

        print(
            f"- {repo['name']} "
            f"(score: "
            f"{project_score(repo)})"
        )


if __name__ == "__main__":
    main()