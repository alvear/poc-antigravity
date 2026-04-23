"""
GitHub Helper - interage com a API do GitHub para branches, commits, PRs, tags.
"""
import base64
import json

import requests

import grafana_logger as log
from agents.exceptions import GitHubError
from config import settings

GITHUB_TOKEN = settings.github_token.get_secret_value()
OWNER = settings.github_owner
REPO = settings.github_repo
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_branch_sha(branch="main"):
    r = requests.get(f"{BASE_URL}/git/ref/heads/{branch}", headers=headers)
    if not r.ok:
        raise GitHubError(
            f"Failed to get SHA for branch '{branch}': {r.text[:200]}",
            status_code=r.status_code,
            context={"branch": branch, "operation": "get_branch_sha"},
        )
    return r.json()["object"]["sha"]


def create_branch(branch_name, from_branch="main"):
    sha = get_branch_sha(from_branch)
    payload = {"ref": f"refs/heads/{branch_name}", "sha": sha}
    r = requests.post(f"{BASE_URL}/git/refs", headers=headers, json=payload)
    if r.status_code == 422:
        print(f"[GITHUB] Branch ja existe: {branch_name}")
        return branch_name
    if not r.ok:
        raise GitHubError(
            f"Failed to create branch '{branch_name}': {r.text[:200]}",
            status_code=r.status_code,
            context={"branch": branch_name, "from": from_branch},
        )
    log.info("dev-agent", f"Branch criada: {branch_name}", {"branch": branch_name})
    print(json.dumps({"branch": branch_name, "sha": sha[:7]}))
    return branch_name


def commit_file(branch, filepath, content, message):
    r = requests.get(
        f"{BASE_URL}/contents/{filepath}?ref={branch}", headers=headers
    )
    existing_sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    r = requests.put(
        f"{BASE_URL}/contents/{filepath}", headers=headers, json=payload
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to commit {filepath} to {branch}: {r.text[:200]}",
            status_code=r.status_code,
            context={"branch": branch, "filepath": filepath, "operation": "commit_file"},
        )
    commit_sha = r.json()["commit"]["sha"][:7]
    log.info("dev-agent", f"Commit: {filepath}",
             {"branch": branch, "sha": commit_sha})
    print(f"[GITHUB] {filepath} -> {commit_sha}")
    return commit_sha


def create_pr(from_branch, to_branch, title, body):
    payload = {"title": title, "head": from_branch, "base": to_branch, "body": body}
    r = requests.post(f"{BASE_URL}/pulls", headers=headers, json=payload)
    if not r.ok:
        raise GitHubError(
            f"Failed to create PR from {from_branch} to {to_branch}: {r.text[:200]}",
            status_code=r.status_code,
            context={"from": from_branch, "to": to_branch, "title": title},
        )
    pr = r.json()
    log.info("dev-agent", f"PR aberto: #{pr['number']}",
             {"pr_url": pr["html_url"]})
    print(f"[GITHUB] PR #{pr['number']}: {pr['html_url']}")
    return pr


def create_tag(tag_name, sha, message):
    """Cria tag anotada apontando pro SHA especificado."""
    tag_obj = {
        "tag": tag_name,
        "message": message,
        "object": sha,
        "type": "commit",
    }
    r = requests.post(f"{BASE_URL}/git/tags", headers=headers, json=tag_obj)
    if not r.ok:
        raise GitHubError(
            f"Failed to create tag object '{tag_name}': {r.text[:200]}",
            status_code=r.status_code,
            context={"tag_name": tag_name, "sha": sha[:7]},
        )
    tag_sha = r.json()["sha"]

    ref = {"ref": f"refs/tags/{tag_name}", "sha": tag_sha}
    r = requests.post(f"{BASE_URL}/git/refs", headers=headers, json=ref)
    if not r.ok:
        raise GitHubError(
            f"Failed to create tag ref for '{tag_name}': {r.text[:200]}",
            status_code=r.status_code,
            context={"tag_name": tag_name, "tag_sha": tag_sha[:7]},
        )

    log.info("release-agent", f"Tag criada: {tag_name}", {"sha": sha[:7]})
    print(f"[GITHUB] tag {tag_name} criada apontando para {sha[:7]}")
    return tag_name
