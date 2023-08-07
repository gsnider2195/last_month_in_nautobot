import os
import pprint

from github import Auth, Github

auth = Auth.Token(os.getenv("GITHUB_TOKEN"))

g = Github(auth=auth)

releases = []

org = g.get_organization("nautobot")

for repo in org.get_repos():
    if repo.private:
        continue
    try:
        release = repo.get_latest_release()
    except:
        continue
    releases.append(
        {
            "name": f"{repo.name} {release.tag_name}",
            "published_at": release.published_at,
            "tag_name": release.tag_name,
            "url": release.html_url,
        }
    )

sorted_releases = sorted(releases, key=lambda k: k["published_at"], reverse=True)
pprint.pprint(sorted_releases)
