"""
JSM Helper — POC Antigravity
Cria GMUDs no Jira Service Management e acompanha o workflow
ate aprovacao (Implementing) ou reprovacao (Declined/Cancelado).

Workflow:
  Triage -> Planejamento -> Revisar -> Implementing (deploy) -> Concluida
                                   -> Declined (aborta)
                                   -> Cancelado (aborta)
"""
import time
import json
import requests

import grafana_logger as log
from config import settings

AGENT = "release-agent"
# JSM pode estar em tenant separado do Jira Software (dual-site).
# Se JSM_URL nao configurado, usa o mesmo tenant do Jira Software.
JIRA_URL    = settings.jsm_url or settings.jira_url
JIRA_EMAIL  = settings.jira_email
JIRA_TOKEN  = settings.jira_token.get_secret_value()
JSM_PROJECT = settings.jsm_project

auth = (JIRA_EMAIL, JIRA_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

# Status terminais
STATUS_APPROVED_FOR_DEPLOY = ["IMPLEMENTING", "EM EXECUCAO"]
STATUS_REJECTED = ["DECLINED", "CANCELADO", "CANCELLED"]
STATUS_COMPLETED = ["CONCLUIDA", "CONCLUIDO", "DONE", "COMPLETED"]

def _normalize(s):
    return s.upper().strip().replace("Ã", "A").replace("Á", "A").replace("Í", "I").replace("Ç", "C").replace("Ó", "O").replace("Õ", "O").replace("É", "E")


def create_change(summary, description, release_tag, affected_envs="PRD", risk="LOW", change_type="Normal"):
    """Cria uma Request a change no JSM. Retorna o issue key (ex: GMUD-2)."""
    # Mapeamento Change type -> ID do customfield_10084 no projeto GMUD
    CHANGE_TYPE_IDS = {
        "Normal":    "10090",
        "Standard":  "10091",
        "Emergency": "10092",
    }
    change_type_id = CHANGE_TYPE_IDS.get(change_type, "10090")

    payload = {
        "fields": {
            "project":     {"key": JSM_PROJECT},
            "issuetype":   {"name": "Request a change"},
            "summary":     f"[RELEASE {release_tag}] {summary}",
            "description": {
                "type":    "doc",
                "version": 1,
                "content": [
                    {
                        "type":    "paragraph",
                        "content": [{"type": "text", "text": description}]
                    },
                    {
                        "type":    "paragraph",
                        "content": [{
                            "type": "text",
                            "text": f"Release tag: {release_tag} | Ambientes afetados: {affected_envs} | Risco: {risk}"
                        }]
                    }
                ]
            },
            # Campo obrigatorio do template ITSM - Change type
            "customfield_10084": {"id": change_type_id},
        }
    }
    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        auth=auth, headers=headers, json=payload
    )
    if r.status_code not in (200, 201):
        log.error(AGENT, f"Falha ao criar GMUD: HTTP {r.status_code}", {"body": r.text[:500]})
        print(f"[JSM] HTTP {r.status_code} ao criar GMUD. Body: {r.text[:800]}")
        r.raise_for_status()
    key = r.json()["key"]
    url = f"{JIRA_URL}/browse/{key}"
    log.success(AGENT, f"GMUD criada: {key}", {
        "gmud_key": key, "gmud_url": url, "release_tag": release_tag,
        "affected_envs": affected_envs, "risk": risk
    })
    print(json.dumps({"gmud_key": key, "gmud_url": url, "release_tag": release_tag}))
    return key


def get_status(issue_key):
    """Retorna o status atual da GMUD em UPPERCASE normalizado."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}?fields=status",
        auth=auth, headers=headers
    )
    r.raise_for_status()
    status = r.json()["fields"]["status"]["name"]
    return _normalize(status)


def get_transitions(issue_key):
    """Lista transicoes disponiveis a partir do status atual."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        auth=auth, headers=headers
    )
    r.raise_for_status()
    return [
        {"id": t["id"], "name": t["name"], "to": t["to"]["name"]}
        for t in r.json()["transitions"]
    ]


def transition(issue_key, target_status):
    """Transiciona a GMUD para o status desejado (busca a transicao por nome de destino)."""
    target_norm = _normalize(target_status)
    trans = get_transitions(issue_key)
    match = [t for t in trans if _normalize(t["to"]) == target_norm]
    if not match:
        available = [f"{t['name']} -> {t['to']}" for t in trans]
        raise RuntimeError(f"Transicao para '{target_status}' nao disponivel. Disponiveis: {available}")
    t_id = match[0]["id"]
    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        auth=auth, headers=headers,
        json={"transition": {"id": t_id}}
    )
    r.raise_for_status()
    log.info(AGENT, f"GMUD {issue_key} transicionada para {target_status}")
    return True


def wait_for_approval(issue_key, timeout_minutes=60, poll_seconds=15):
    """
    Bloqueia ate a GMUD sair de TRIAGE/PLANEJAMENTO/REVISAR para um status terminal.
    Retorna:
      True  -> aprovada (IMPLEMENTING) — pode deployar
      False -> rejeitada (DECLINED / CANCELADO)
    """
    deadline = time.time() + (timeout_minutes * 60)
    last_status = None
    log.info(AGENT, f"Aguardando aprovacao da GMUD {issue_key} (timeout {timeout_minutes}min)")
    print(f"[JSM] Aguardando aprovacao de {issue_key} em {JIRA_URL}/browse/{issue_key}")

    while time.time() < deadline:
        status = get_status(issue_key)
        if status != last_status:
            print(f"[JSM] Status atual: {status}")
            log.info(AGENT, f"GMUD {issue_key} status: {status}")
            last_status = status

        if status in STATUS_APPROVED_FOR_DEPLOY:
            log.success(AGENT, f"GMUD {issue_key} APROVADA — liberando deploy", {
                "gmud_key": issue_key, "status": status
            })
            return True

        if status in STATUS_REJECTED:
            log.warn(AGENT, f"GMUD {issue_key} REJEITADA", {
                "gmud_key": issue_key, "status": status
            })
            return False

        time.sleep(poll_seconds)

    log.error(AGENT, f"GMUD {issue_key} timeout apos {timeout_minutes}min", {"gmud_key": issue_key})
    raise TimeoutError(f"GMUD {issue_key} nao foi aprovada em {timeout_minutes} minutos")


def mark_done(issue_key):
    """Apos deploy bem-sucedido, transiciona GMUD para CONCLUIDA."""
    trans = get_transitions(issue_key)
    done_target = None
    for t in trans:
        if _normalize(t["to"]) in STATUS_COMPLETED:
            done_target = t["to"]
            break
    if not done_target:
        log.warn(AGENT, f"Nao ha transicao para CONCLUIDA em {issue_key}", {
            "available": [t["to"] for t in trans]
        })
        return False
    transition(issue_key, done_target)
    log.success(AGENT, f"GMUD {issue_key} fechada como {done_target}")
    return True


def add_comment(issue_key, text):
    """Adiciona comentario na GMUD (ex: URL de deploy, metricas, logs)."""
    payload = {
        "body": {
            "type":    "doc",
            "version": 1,
            "content": [{
                "type":    "paragraph",
                "content": [{"type": "text", "text": text}]
            }]
        }
    }
    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment",
        auth=auth, headers=headers, json=payload
    )
    r.raise_for_status()
    return True




def auto_transition_to_implementing(issue_key, path=None):
    """
    Transiciona automaticamente a GMUD por um caminho pre-definido ate IMPLEMENTING.
    Usado para Standard Changes (pre-aprovados, sem CAB).

    Default path: TRIAGE -> PLANEJAMENTO -> IMPLEMENTING
    (pula REVISAR porque Standard Change nao precisa de review humano)
    """
    import time as _time
    if path is None:
        # Standard Change vai direto de TRIAGE -> IMPLEMENTING via transicao "Set as standard"
        # (pre-aprovado, nao precisa passar por Planejamento/Revisar)
        path = ["Implementing"]

    log.info(AGENT, f"Auto-transicao de {issue_key} por {' -> '.join(path)}")
    for target in path:
        current = get_status(issue_key)
        if _normalize(current) == _normalize(target):
            print(f"[JSM] {issue_key} ja esta em {target}, pulando")
            continue
        try:
            transition(issue_key, target)
            print(f"[JSM] {issue_key} -> {target}")
            _time.sleep(2)  # dar tempo do JSM processar
        except RuntimeError as e:
            # Se transicao direta nao existir, loga mas continua
            log.warn(AGENT, f"Transicao para {target} falhou: {e}")
            print(f"[JSM] AVISO: nao foi possivel transicionar para {target}: {e}")
    final = get_status(issue_key)
    log.info(AGENT, f"Auto-transicao concluida: {issue_key} esta em {final}")
    return final


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "create":
        key = create_change(
            summary="POC Smoke Test — verifica integracao JSM",
            description="GMUD gerada pelo jsm_helper para validar integracao end-to-end.",
            release_tag="v0.0.1-smoke",
            affected_envs="DEV,UAT,PRD",
            risk="LOW"
        )
        print(f"\nGMUD criada: {key}")
        print(f"Abra em: {JIRA_URL}/browse/{key}")

    elif cmd == "status":
        key = sys.argv[2]
        print(f"Status de {key}: {get_status(key)}")
        print("Transicoes disponiveis:")
        for t in get_transitions(key):
            print(f"  - {t['name']} -> {t['to']}")

    elif cmd == "wait":
        key = sys.argv[2]
        timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        ok = wait_for_approval(key, timeout_minutes=timeout)
        print("APROVADA" if ok else "REJEITADA")

    elif cmd == "done":
        key = sys.argv[2]
        mark_done(key)

    else:
        print("Uso:")
        print("  python jsm_helper.py create              # cria GMUD de smoke")
        print("  python jsm_helper.py status GMUD-N       # ve status e transicoes")
        print("  python jsm_helper.py wait GMUD-N [min]   # polling de aprovacao")
        print("  python jsm_helper.py done GMUD-N         # marca CONCLUIDA")