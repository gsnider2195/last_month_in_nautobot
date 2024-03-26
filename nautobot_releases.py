import datetime
import jinja2
import json
import os

from github import Auth, Github, UnknownObjectException

RELEASE_KEYS = [
    "published_at",
    "tag_name",
    "html_url",
    "body",
    "title",
]


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

    def sort_releases(key):
        if key["repo_name"] == "nautobot":
            return key["published_at"] + datetime.timedelta(weeks=100)
        return key["published_at"]

    sorted_releases = sorted(releases, key=sort_releases, reverse=True)
    return sorted_releases


def render_releases(releases):
    jinja2_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath="./templates"),
    )
    jinja2_environment.filters["date"] = lambda value, fmt: value.strftime(fmt)
    jinja2_environment.filters["release_title"] = lambda value: " ".join(
        value.split("-")
    ).title()
    template = jinja2_environment.get_template("last_month_in_nautobot.j2")
    print(template.render(releases=releases))


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

    render_releases(releases)


if __name__ == "__main__":
    main()
