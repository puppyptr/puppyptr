import os
import json
import urllib.request
from datetime import datetime, timezone

USERNAME = "puppyptr"
README = "README.md"


def github_api(path):
    url = f"https://api.github.com{path}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "puppyptr-profile-updater",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def get_all_repos():
    repos = []
    page = 1

    while True:
        data = github_api(
            f"/users/{USERNAME}/repos?per_page=100&page={page}&type=owner"
        )

        if not data:
            break

        repos.extend(data)
        page += 1

    return repos


def get_stats(repos):
    stars = sum(repo["stargazers_count"] for repo in repos)

    starred_repo = max(
        repos,
        key=lambda repo: repo["stargazers_count"],
        default=None,
    )

    return {
        "stars": stars,
        "repos": len(repos),
        "most_starred": (
            starred_repo["name"] if starred_repo else "none"
        ),
        "most_starred_count": (
            starred_repo["stargazers_count"] if starred_repo else 0
        ),
    }


def get_yearly_commit_count():
    year = datetime.now(timezone.utc).year

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
        }
      }
    }
    """

    start = f"{year}-01-01T00:00:00Z"
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = json.dumps({
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": start,
            "to": end,
        },
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "puppyptr-profile-updater",
        },
    )

    with urllib.request.urlopen(request) as response:
        result = json.load(response)

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]["user"]["contributionsCollection"][
        "totalCommitContributions"
    ]


def get_pull_requests():
    data = github_api(
        f"/search/issues?q=author:{USERNAME}+type:pr"
    )
    return data["total_count"]


def get_issues():
    data = github_api(
        f"/search/issues?q=author:{USERNAME}+type:issue"
    )
    return data["total_count"]


def get_language_percentages(repos):
    totals = {}

    for repo in repos:
        try:
            languages = github_api(
                f"/repos/{USERNAME}/{repo['name']}/languages"
            )
        except Exception as exc:
            print(
                f"Could not read languages for "
                f"{repo['name']}: {exc}"
            )
            continue

        for language, amount in languages.items():
            totals[language] = totals.get(language, 0) + amount

    total_bytes = sum(totals.values())

    if total_bytes == 0:
        return {}

    percentages = {
        language: (amount / total_bytes) * 100
        for language, amount in totals.items()
    }

    return dict(
        sorted(
            percentages.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def language_bar(percentage, width=10):
    filled = round((percentage / 100) * width)
    return "▓" * filled + "░" * (width - filled)


def format_languages(languages):
    lines = []

    for language, percentage in list(languages.items())[:8]:
        lines.append(
            f"{language:<15} "
            f"{language_bar(percentage)} "
            f"{percentage:.2f}%"
        )

    return "\n".join(lines)


def generate_readme(stats, languages, commits, prs, issues):
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    avg_commits = (
        commits / stats["repos"]
        if stats["repos"]
        else 0
    )

    language_text = format_languages(languages)

    return (
        "### haii, i’m elizabeth (puppyptr) 🐾\n"
        "\n"
        "> very queer demigirl hacker • software dev & music artist • makes random things ^w^\n"
        "\n"
        "**top languages**\n"
        "```\n"
        f"{language_text}\n"
        "```\n"
        "\n"
        "**my stats**\n"
        "```python\n"
        f"- {stats['stars']} stars across repos\n"
        f"- {commits} commits this year\n"
        f"- {prs} total pull requests\n"
        f"- {issues} total issues\n"
        "- 0 repos contributed to\n"
        f"- {stats['repos']} total owned repos\n"
        f"- Most Starred Repo: {stats['most_starred']} ({stats['most_starred_count']})\n"
        f"- Avg commits per repo: {avg_commits:.1f}\n"
        "```\n"
        f"_Last updated {now}_\n"
        "\n"
        "**fun fact:**  \n"
        "im attempting to learn rust... i kinda suck at it\n"
        "\n"
        '<p align="center">\n'
        '  <img src="https://avatars.githubusercontent.com/u/65957437?v=4&size=128" width="128" height="128" style="border-radius:50%;">\n'
        "  <br>\n"
        "  <sub>this is me btw</sub>\n"
        "</p>\n"
        "\n"
        "![Profile Views](https://komarev.com/ghpvc/?username=puppyptr&color=grey)\n"
        "\n"
        "[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/puppyptr)\n"
        "\n"
        "*Profile README inspired by [ptrpaws](https://github.com/ptrpaws) 🐾*\n"
    )


def main():
    print("Fetching repositories...")
    repos = get_all_repos()

    print("Calculating stats...")
    stats = get_stats(repos)

    print("Fetching languages...")
    languages = get_language_percentages(repos)

    print("Fetching yearly commits...")
    commits = get_yearly_commit_count()

    print("Fetching pull requests...")
    prs = get_pull_requests()

    print("Fetching issues...")
    issues = get_issues()

    readme = generate_readme(
        stats,
        languages,
        commits,
        prs,
        issues,
    )

    with open(README, "w", encoding="utf-8") as file:
        file.write(readme)

    print("README.md updated!")


if __name__ == "__main__":
    main()
