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


# ============================================================
# PULL REQUESTS (usado pelo Reviewer Agent)
# ============================================================

def list_open_prs():
    """Lista PRs abertos. Retorna [{number, title, user, head_ref, base_ref, html_url}]."""
    r = requests.get(
        f"{BASE_URL}/pulls",
        headers=headers,
        params={"state": "open", "per_page": 50},
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to list open PRs: {r.text[:200]}",
            status_code=r.status_code,
            context={"operation": "list_open_prs"},
        )
    prs = r.json()
    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "user": pr["user"]["login"],
            "head_ref": pr["head"]["ref"],
            "base_ref": pr["base"]["ref"],
            "html_url": pr["html_url"],
        }
        for pr in prs
    ]


def get_pr_diff(pr_number):
    """Retorna o diff bruto do PR (formato unified diff)."""
    diff_headers = dict(headers)
    diff_headers["Accept"] = "application/vnd.github.v3.diff"
    r = requests.get(
        f"{BASE_URL}/pulls/{pr_number}",
        headers=diff_headers,
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to get diff for PR #{pr_number}: {r.text[:200]}",
            status_code=r.status_code,
            context={"pr_number": pr_number, "operation": "get_pr_diff"},
        )
    return r.text


def get_pr_files(pr_number):
    """Lista arquivos alterados no PR. Retorna [{filename, status, additions, deletions, patch}]."""
    r = requests.get(
        f"{BASE_URL}/pulls/{pr_number}/files",
        headers=headers,
        params={"per_page": 100},
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to get files for PR #{pr_number}: {r.text[:200]}",
            status_code=r.status_code,
            context={"pr_number": pr_number, "operation": "get_pr_files"},
        )
    files = r.json()
    return [
        {
            "filename": f["filename"],
            "status": f["status"],
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
            "patch": f.get("patch", ""),
        }
        for f in files
    ]


def close_pr(pr_number, reason):
    """Fecha um PR comentando o motivo. Usado pelo Reviewer em REJECT."""
    comment_payload = {"body": f"**Reviewer Agent - REJECT**\n\n{reason}"}
    r = requests.post(
        f"{BASE_URL}/issues/{pr_number}/comments",
        headers=headers,
        json=comment_payload,
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to comment on PR #{pr_number}: {r.text[:200]}",
            status_code=r.status_code,
            context={"pr_number": pr_number, "operation": "close_pr.comment"},
        )

    r = requests.patch(
        f"{BASE_URL}/pulls/{pr_number}",
        headers=headers,
        json={"state": "closed"},
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to close PR #{pr_number}: {r.text[:200]}",
            status_code=r.status_code,
            context={"pr_number": pr_number, "operation": "close_pr.patch"},
        )
    log.info("reviewer-agent", f"PR #{pr_number} fechado", {"pr_number": pr_number, "reason": reason[:100]})
    return True


def comment_pr_review(pr_number, event, body):
    """
    Cria uma review no PR.
    event: 'APPROVE' | 'REQUEST_CHANGES' | 'COMMENT'
    """
    valid_events = ("APPROVE", "REQUEST_CHANGES", "COMMENT")
    if event not in valid_events:
        raise GitHubError(
            f"Invalid review event '{event}'. Must be one of {valid_events}",
            context={"pr_number": pr_number, "event": event, "operation": "comment_pr_review"},
        )
    payload = {"event": event, "body": body}
    r = requests.post(
        f"{BASE_URL}/pulls/{pr_number}/reviews",
        headers=headers,
        json=payload,
    )
    if not r.ok:
        raise GitHubError(
            f"Failed to post review on PR #{pr_number}: {r.text[:200]}",
            status_code=r.status_code,
            context={"pr_number": pr_number, "event": event, "operation": "comment_pr_review"},
        )
    log.info("reviewer-agent", f"Review {event} em PR #{pr_number}", {"pr_number": pr_number, "event": event})
    return r.json().get("id")
