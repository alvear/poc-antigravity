"""
Jira Helper - cria epics/historias e lista issues no Jira Software.
"""
import json
import sys

import requests
from requests.auth import HTTPBasicAuth

import grafana_logger as log
from agents.exceptions import JiraError
from config import settings

JIRA_URL = settings.jira_url
JIRA_EMAIL = settings.jira_email
JIRA_TOKEN = settings.jira_token.get_secret_value()
PROJECT = settings.jira_project

auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}
base = f"{JIRA_URL}/rest/api/3"


def create_issue(summary, description, issue_type, parent_key=None):
    log.info("pm-agent", f"Criando {issue_type}: {summary}",
             {"parent_key": parent_key, "project": PROJECT})
    body = {
        "fields": {
            "project": {"key": PROJECT},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": description}]}
                ],
            },
            "issuetype": {"name": issue_type},
        }
    }
    if parent_key:
        body["fields"]["parent"] = {"key": parent_key}

    r = requests.post(f"{base}/issue", auth=auth, headers=headers, json=body)
    if not r.ok:
        raise JiraError(
            f"Failed to create {issue_type} '{summary}': {r.text[:200]}",
            status_code=r.status_code,
            context={"endpoint": "/issue", "project": PROJECT, "issue_type": issue_type, "parent": parent_key},
        )
    key = r.json()["key"]
    log.info("pm-agent", f"Issue criada: {key}", {"type": issue_type})
    print(f"[JIRA] {key}: {summary}")
    return key


def list_issues():
    log.info("pm-agent", f"Listando issues do projeto {PROJECT}")
    jql = f"project = {PROJECT} ORDER BY created DESC"
    r = requests.get(
        f"{base}/search",
        auth=auth,
        headers=headers,
        params={"jql": jql, "maxResults": 50,
                "fields": "summary,issuetype,status"},
    )
    if not r.ok:
        raise JiraError(
            f"Failed to list issues: {r.text[:200]}",
            status_code=r.status_code,
            context={"endpoint": "/search", "jql": jql},
        )
    issues = r.json()["issues"]
    log.info("pm-agent", f"{len(issues)} issues encontradas")
    summary_list = [
        {
            "key": i["key"],
            "summary": i["fields"]["summary"],
            "type": i["fields"]["issuetype"]["name"],
            "status": i["fields"]["status"]["name"],
        }
        for i in issues
    ]
    print(json.dumps(summary_list, indent=2, ensure_ascii=False))
    return summary_list


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create":
        data = json.loads(sys.argv[2])
        create_issue(
            data["summary"], data["description"],
            data["issue_type"], data.get("parent_key"),
        )
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        list_issues()
    else:
        print("Uso: python jira_helper.py [create|list] [json]")
