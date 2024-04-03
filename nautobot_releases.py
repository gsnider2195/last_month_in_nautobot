import calendar
import datetime
import jinja2
import json
import os
import re

from github import Auth, Github, UnknownObjectException


RELEASE_KEYS = [
    "published_at",
    "tag_name",
    "html_url",
    "body",
    "title",
]

STRING_REPLACEMENTS = (
    (r"(?i)\bssot\b", "SSoT"),
    (r"(?i)nautobot-app-SSoT", "nautobot-app-ssot"),
    (r"(?i)\bbgp\b", "BGP"),
    (r"(?i)chatops", "ChatOps"),
    (r"(?i)nautobot-app-ChatOps", "nautobot-app-chatops"),
    (r"(?i)nautobot-app-BGP-models", "nautobot-app-bgp-models"),
    (r"\r", ""),
    (r"\n\n*", r"\n"),
    (r"(?m)^\* ", "- "),
    (r"(?m)^##* ", "- "),
)


def get_releases(github_org):
    releases = []
    month = 0
    while month not in range(1, 13):
        try:
            month = int(input("Select month (1=January, 2=February, etc.): "))
        except ValueError:
            month = 0
    year = datetime.date.today().year
    if month == 12:
        year -= 1
    date_cutoff = datetime.datetime(year, month, 1)
    for repo in github_org.get_repos():
        if repo.private:
            continue
        try:
            for release in repo.get_releases():
                if release.published_at < date_cutoff:
                    break
                if release.draft:
                    continue
                if release.published_at.month != month:
                    continue
                release_dict = {key: getattr(release, key) for key in RELEASE_KEYS}
                release_dict["repo_name"] = repo.name
                releases.append(release_dict)
        except UnknownObjectException:
            continue

    sorted_releases = sorted(releases, key=lambda k: k["published_at"], reverse=True)
    return sorted_releases


def substitute_strings(releases):
    for release in releases:
        for pattern, replacement in STRING_REPLACEMENTS:
            release["repo_name"] = re.sub(pattern, replacement, release["repo_name"])
            release["body"] = re.sub(pattern, replacement, release["body"])


def filter_release_title(value):
    release_title = " ".join(value.split("-")).title()
    for pattern, replacement in STRING_REPLACEMENTS:
        release_title = re.sub(pattern, replacement, release_title)
    return release_title


def test_startswith(value, match):
    return value.startswith(match)


def render_releases(releases):
    if not releases:
        print("No releases for this date")
        return

    jinja2_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath="./templates"),
    )
    jinja2_environment.filters["date"] = lambda value, fmt: value.strftime(fmt)
    jinja2_environment.filters["release_title"] = filter_release_title
    jinja2_environment.tests["startswith"] = test_startswith
    template = jinja2_environment.get_template("last_month_in_nautobot.j2")
    print(template.render(releases=releases, month_year=releases[0]["published_at"].strftime("%B %Y")))


def main():
    if os.path.exists("releases.json"):
        releases = json.load(open("releases.json"))
        for release in releases:
            release["published_at"] = datetime.datetime.strptime(
                release["published_at"], "%Y-%m-%d %H:%M:%S"
            )
    else:
        auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
        g = Github(auth=auth)

        org = g.get_organization("nautobot")

        releases = get_releases(org)
        with open("releases.json", "w") as f:
            json.dump(releases, f, indent=4, default=str)

    substitute_strings(releases)
    render_releases(releases)


if __name__ == "__main__":
    main()
