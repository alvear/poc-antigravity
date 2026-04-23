"""
Gate Logger - rastreia propostas dos agentes (approved/rejected) e calcula FPY.

Persiste sessoes em .gate_sessions.json (arquivo local, no .gitignore).
Usado por todos os agentes antes de executar uma acao relevante.
"""
import json
import os
import time
import uuid

import grafana_logger as log

SESSIONS_FILE = ".gate_sessions.json"


def _load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return []
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


def start_proposal(agent, proposal_type, summary):
    """Inicia sessao de proposta. Retorna session_id unico."""
    session_id = f"{agent}-{proposal_type.lower()}-{int(time.time())}"
    sessions = _load_sessions()
    sessions.append({
        "session_id": session_id,
        "agent": agent,
        "proposal_type": proposal_type,
        "summary": summary,
        "ts_start": time.time(),
        "decision": None,
        "iterations": 1,
    })
    _save_sessions(sessions)
    log.info(agent, f"Proposta iniciada: {proposal_type} - {summary}",
             {"session_id": session_id})
    print(f"[GATE] START {session_id} | {proposal_type} | {summary}")
    return session_id


def record_decision(session_id, decision, feedback=None, jira_key=None):
    """Registra decisao final (approved / rejected / adjusted)."""
    sessions = _load_sessions()
    for s in sessions:
        if s["session_id"] == session_id:
            s["decision"] = decision
            s["ts_end"] = time.time()
            s["duration_sec"] = round(s["ts_end"] - s["ts_start"], 2)
            if feedback:
                s["feedback"] = feedback
            if jira_key:
                s["jira_key"] = jira_key
            _save_sessions(sessions)
            agent = s["agent"]
            log.info(agent, f"Decisao: {decision}", {
                "session_id": session_id,
                "duration_sec": s["duration_sec"],
                "jira_key": jira_key,
            })
            print(f"[GATE] {decision.upper()} {session_id} "
                  f"({s['duration_sec']}s) jira={jira_key}")
            return s
    print(f"[GATE ERROR] sessao nao encontrada: {session_id}")
    return None


def compute_fpy():
    """First Pass Yield - percentual de propostas aprovadas sem iteracao."""
    sessions = _load_sessions()
    total = len([s for s in sessions if s.get("decision")])
    if total == 0:
        return {"fpy": 0.0, "total": 0, "approved": 0}
    approved_first_pass = len([
        s for s in sessions
        if s.get("decision") == "approved" and s.get("iterations", 1) == 1
    ])
    return {
        "fpy": round(approved_first_pass / total * 100, 1),
        "total": total,
        "approved": approved_first_pass,
    }


if __name__ == "__main__":
    print(json.dumps(compute_fpy(), indent=2))
