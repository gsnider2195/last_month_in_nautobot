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
    (r"(?i)nautobot-app-BGP-models", "nautobot-app-bgp-models"),
    (r"\r", ""),
    (r"\n\n*", r"\n"),
)


def get_releases(github_org, num_days=30):
    releases = []
    date_cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=num_days)
    for repo in github_org.get_repos():
        if repo.private:
            continue
        try:
            for release in repo.get_releases():
                if release.published_at < date_cutoff or release.draft:
                    break
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
    jinja2_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath="./templates"),
    )
    jinja2_environment.filters["date"] = lambda value, fmt: value.strftime(fmt)
    jinja2_environment.filters["release_title"] = filter_release_title
    jinja2_environment.tests["startswith"] = test_startswith
    template = jinja2_environment.get_template("last_month_in_nautobot.j2")
    print(template.render(releases=releases, month_year=datetime.date.today().strftime("%B %Y")))


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
