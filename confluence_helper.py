"""
Confluence Helper - cria paginas no space POCAntigra (ADRs, QA Evidence, Release Notes).

Confluence roda no mesmo tenant Atlassian do Jira, entao reusa a auth do Jira.
"""
import json

import requests
from requests.auth import HTTPBasicAuth

import grafana_logger as log
from agents.exceptions import ConfluenceError
from config import settings

CONFLUENCE_URL = settings.confluence_url
CONFLUENCE_EMAIL = settings.confluence_email
CONFLUENCE_TOKEN = settings.confluence_token.get_secret_value()
SPACE_KEY = settings.confluence_space

auth = HTTPBasicAuth(CONFLUENCE_EMAIL, CONFLUENCE_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}


def _api():
    return f"{CONFLUENCE_URL}/wiki/api/v2"


def _rest():
    return f"{CONFLUENCE_URL}/wiki/rest/api"


def _get_space_id():
    r = requests.get(
        f"{_api()}/spaces", auth=auth, headers=headers,
        params={"keys": SPACE_KEY},
    )
    if not r.ok:
        raise ConfluenceError(
            f"Failed to get space_id for '{SPACE_KEY}': {r.text[:200]}",
            status_code=r.status_code,
            context={"space": SPACE_KEY, "operation": "get_space_id"},
        )
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError(f"Space nao encontrado: {SPACE_KEY}")
    return results[0]["id"]


def _find_parent_id(parent_title):
    """Encontra ID da pagina pai pelo titulo."""
    r = requests.get(
        f"{_rest()}/content",
        auth=auth, headers=headers,
        params={"title": parent_title, "spaceKey": SPACE_KEY, "expand": "version"},
    )
    if not r.ok:
        raise ConfluenceError(
            f"Failed to find parent '{parent_title}': {r.text[:200]}",
            status_code=r.status_code,
            context={"space": SPACE_KEY, "parent_title": parent_title},
        )
    results = r.json().get("results", [])
    return results[0]["id"] if results else None


def create_page(title, content, parent_title=None):
    space_id = _get_space_id()
    body = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": content},
    }
    if parent_title:
        parent_id = _find_parent_id(parent_title)
        if parent_id:
            body["parentId"] = parent_id

    r = requests.post(
        f"{_api()}/pages", auth=auth, headers=headers, json=body,
    )
    if r.status_code == 400 and "already exists" in r.text.lower():
        print(f"[CONFLUENCE] Pagina ja existe: {title}")
        return None
    if not r.ok:
        raise ConfluenceError(
            f"Failed to create page '{title}': {r.text[:200]}",
            status_code=r.status_code,
            context={"title": title, "space": SPACE_KEY, "parent": parent_title},
        )
    page = r.json()
    log.info("architect-agent", f"Pagina criada: {title}",
             {"page_id": page.get("id")})
    print(f"[CONFLUENCE] {title} criada (id={page.get('id')})")
    return page


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python confluence_helper.py <titulo> <conteudo_html>")
        sys.exit(1)
    create_page(sys.argv[1], sys.argv[2])
