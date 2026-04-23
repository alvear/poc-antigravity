"""
Release Agent - POC Antigravity

Fluxo completo:
  1. Cria tag no GitHub
  2. Acompanha bake + DEV + UAT
  3. Cria GMUD no JSM (Standard ou Normal conforme risco)
  4. Auto-transiciona a GMUD
     - Standard (risk=LOW) -> TRIAGE -> IMPLEMENTING (pre-aprovado)
     - Normal   (risk>LOW) -> TRIAGE -> PLANEJAMENTO -> REVISAR (espera CAB)
  5. Aguarda o pipeline de PRD completar
     - Standard: bridge destrava PRD automaticamente
     - Normal: humano aprova em REVISAR -> IMPLEMENTING, bridge destrava
  6. Apos PRD verde -> marca GMUD como CONCLUIDA
  7. Publica Release Notes no Confluence
"""
import os
import sys
import time

import grafana_logger as log
import gate_logger
import github_helper
import jsm_helper
import confluence_helper
from config import settings

AGENT = "release-agent"
POLL_SEC = 10
MAX_WAIT_STAGE_MIN = 15
MAX_WAIT_PRD_MIN = 120  # ate 2h pra Normal Change (tempo para CAB aprovar)


def wait_stage(run_id, stage_substr, timeout_min=MAX_WAIT_STAGE_MIN):
    deadline = time.time() + (timeout_min * 60)
    last = None
    while time.time() < deadline:
        jobs = github_helper.get_run_jobs(run_id)
        target = next((j for j in jobs if stage_substr.lower() in j["name"].lower()), None)
        if target:
            status = target.get("status")
            conclusion = target.get("conclusion")
            key = f"{status}/{conclusion}"
            if key != last:
                print(f"[PIPELINE] {stage_substr}: status={status} conclusion={conclusion}")
                log.info(AGENT, f"stage '{stage_substr}': {key}")
                last = key
            if status == "completed":
                return conclusion == "success"
        time.sleep(POLL_SEC)
    raise TimeoutError(f"timeout esperando stage '{stage_substr}'")


def find_run_for_tag(tag, timeout_min=3):
    deadline = time.time() + (timeout_min * 60)
    while time.time() < deadline:
        run = github_helper.latest_run_for_workflow("deploy.yml")
        if run and (run.get("head_branch") == tag or tag in run.get("display_title", "")):
            return run
        time.sleep(5)
    return github_helper.latest_run_for_workflow("deploy.yml")


def publish_release_notes(release_tag, summary, risk, change_type, gmud_key, gmud_url,
                          run_id, run_url, jira_story_key, affected_envs, final_status):
    """Publica Release Notes no Confluence."""
    flow_desc = "Standard Change auto-aprovado (risk=LOW)" if change_type == "Standard" \
                else f"Normal Change (risk={risk.upper()}) aprovado manualmente no CAB"

    body = f"""<h1>Release Notes {release_tag}</h1>
<p><strong>Resumo:</strong> {summary}</p>
<p><strong>Tipo:</strong> {change_type} ({flow_desc})</p>
<p><strong>Ambientes:</strong> {affected_envs}</p>
<p><strong>Pipeline tool:</strong> GitHub Actions</p>
<p><strong>Status final:</strong> {final_status}</p>

<h2>Rastreabilidade</h2>
<ul>
  <li>Historia Jira: {jira_story_key or '-'}</li>
  <li>GMUD: <a href="{gmud_url}">{gmud_key}</a></li>
  <li>Pipeline: <a href="{run_url}">GitHub Actions Run #{run_id}</a></li>
  <li>Tag: {release_tag}</li>
</ul>

<h2>Fluxo executado</h2>
<ol>
  <li>Release Agent disparado (risk={risk.upper()}) -> classificado como {change_type} Change</li>
  <li>Tag {release_tag} criada no GitHub</li>
  <li>Pipeline bake + DEV + UAT concluidos</li>
  <li>GMUD {gmud_key} criada no JSM como {change_type}</li>
  {'<li>Auto-transicionada TRIAGE -> IMPLEMENTING (pre-aprovada ITIL)</li>' if change_type == 'Standard' else '<li>Auto-transicionada TRIAGE -> PLANEJAMENTO -> REVISAR (aguardando CAB)</li><li>CAB aprovou: REVISAR -> IMPLEMENTING</li>'}
  <li>Jira Automation disparou webhook para gmud-bridge (Cloud Run)</li>
  <li>gmud-bridge chamou GitHub API pending_deployments approved</li>
  <li>Deploy em PRD executado automaticamente</li>
  <li>Release Agent marcou GMUD como Concluida</li>
</ol>

<h2>URLs dos ambientes</h2>
<ul>
  <li>DEV: https://poc-oauth-dev-wppuojuy2a-uc.a.run.app/health</li>
  <li>UAT: https://poc-oauth-uat-wppuojuy2a-uc.a.run.app/health</li>
  <li>PRD: https://poc-oauth-prd-wppuojuy2a-uc.a.run.app/health</li>
</ul>
"""
    try:
        confluence_helper.create_page(
            title=f"Release Notes - {release_tag}",
            content=body,
            parent_title="POC-Antigravity"
        )
        print(f"[CONFLUENCE] Release Notes {release_tag} publicadas")
    except Exception as e:
        log.error(AGENT, f"Falha ao publicar Release Notes: {e}")
        print(f"[CONFLUENCE] AVISO: falha ao publicar: {e}")


def run_release(release_tag, summary, jira_story_key=None, affected_envs="DEV,UAT,PRD", risk="LOW"):
    session = gate_logger.start_proposal(AGENT, "release", f"Release {release_tag}: {summary}")
    log.info(AGENT, f"Iniciando release {release_tag}")

    # ETAPA 1 - Cria tag
    log.info(AGENT, f"Etapa 1/6: criando tag {release_tag}")
    github_helper.create_tag(release_tag, from_branch="main")
    time.sleep(5)

    # ETAPA 2 - Localiza run
    log.info(AGENT, "Etapa 2/6: localizando run do deploy.yml")
    run = find_run_for_tag(release_tag, timeout_min=3)
    if not run:
        log.error(AGENT, "run nao encontrado")
        gate_logger.record_decision(session, "rejected", feedback="no_run")
        sys.exit(1)
    run_id = run["id"]
    run_url = run["html_url"]
    print(f"[PIPELINE] Run ID: {run_id}\n[PIPELINE] URL: {run_url}")

    # ETAPA 3 - Aguarda bake + dev + uat
    log.info(AGENT, "Etapa 3/6: aguardando Bake + DEV + UAT")
    for stage in ["Bake", "DEV", "UAT"]:
        ok = wait_stage(run_id, stage)
        if not ok:
            log.error(AGENT, f"stage {stage} falhou")
            gate_logger.record_decision(session, "rejected", feedback=f"{stage}_failed", jira_key=jira_story_key)
            sys.exit(1)
        print(f"[PIPELINE] {stage} OK")

    # ETAPA 4 - Cria GMUD
    risk_upper = (risk or "LOW").upper()
    if risk_upper == "LOW":
        change_type = "Standard"
        flow_desc = "pre-aprovado (Standard Change)"
    else:
        change_type = "Normal"
        flow_desc = "requer aprovacao manual no CAB (Normal Change)"

    log.info(AGENT, f"Etapa 4/6: criando GMUD ({change_type}) no JSM - {flow_desc}")
    description = (
        f"Release automatica disparada pelo Release Agent.\n\n"
        f"Workflow run: {run_url}\n\n"
        f"Change type: {change_type}\n"
        f"Fluxo: {flow_desc}\n\n"
        f"--- METADATA (para o gmud-bridge) ---\n"
        f"RUN_ID={run_id}\n"
        f"TARGET_ENV=prd\n"
        f"TAG={release_tag}"
    )
    gmud_key = jsm_helper.create_change(
        summary=summary,
        description=description,
        release_tag=release_tag,
        affected_envs=affected_envs,
        risk=risk,
        change_type=change_type,
    )
    jsm_url = settings.jsm_url or settings.jira_url  # dual-site fallback
    gmud_url = f"{jsm_url}/browse/{gmud_key}"
    jsm_helper.add_comment(gmud_key, f"Workflow run: {run_url}")

    # ETAPA 5 - Auto-transiciona conforme o tipo
    time.sleep(8)  # JSM precisa indexar a issue recem-criada
    if change_type == "Standard":
        log.info(AGENT, f"Etapa 5/6: Standard Change -> auto-transicionando {gmud_key} ate IMPLEMENTING")
        try:
            jsm_helper.auto_transition_to_implementing(gmud_key)  # default path = ["Implementing"]
            jsm_helper.add_comment(gmud_key, "Standard Change auto-aprovado. Deploy em PRD sera liberado pelo bridge.")
        except Exception as e:
            log.error(AGENT, f"auto-transition Standard falhou: {e}")
            jsm_helper.add_comment(gmud_key, f"AVISO: auto-transition falhou ({e}). Transicione manualmente para IMPLEMENTING.")
    else:
        log.info(AGENT, f"Etapa 5/6: Normal Change -> auto-transicionando {gmud_key} ate REVISAR")
        try:
            # Normal vai de TRIAGE -> PLANEJAMENTO -> REVISAR e espera CAB
            jsm_helper.auto_transition_to_implementing(gmud_key, path=["Planejamento", "Revisar"])
            jsm_helper.add_comment(gmud_key, "Normal Change preparado pelo Release Agent. Aguardando aprovacao do CAB em REVISAR -> IMPLEMENTING.")
        except Exception as e:
            log.error(AGENT, f"auto-transition Normal falhou: {e}")
            jsm_helper.add_comment(gmud_key, f"AVISO: auto-transition falhou ({e}). Transicione manualmente.")

    # ETAPA 6 - Aguarda PRD concluir (bridge destrava automaticamente)
    log.info(AGENT, "Etapa 6/6: aguardando deploy em PRD concluir")
    if change_type == "Normal":
        print()
        print("=" * 60)
        print(f"  GMUD {gmud_key} em REVISAR - aguardando aprovacao do CAB")
        print(f"  Abra: {gmud_url}")
        print(f"  Transicao: Revisar -> Implementing")
        print("  O bridge detectara e destravara o deploy em PRD.")
        print("=" * 60)
        print()

    prd_ok = False
    try:
        prd_ok = wait_stage(run_id, "PRD", timeout_min=MAX_WAIT_PRD_MIN)
    except TimeoutError:
        log.error(AGENT, "timeout esperando deploy PRD")
        jsm_helper.add_comment(gmud_key, "Timeout aguardando deploy em PRD.")

    # ETAPA FINAL - Fecha GMUD e publica Release Notes
    if prd_ok:
        print(f"[PIPELINE] PRD OK - deploy concluido com sucesso")
        log.success(AGENT, f"Deploy em PRD concluido para {release_tag}")
        try:
            jsm_helper.mark_done(gmud_key)
            final_status = "Concluida"
        except Exception as e:
            log.error(AGENT, f"falha ao marcar GMUD concluida: {e}")
            final_status = "Implementing"
        jsm_helper.add_comment(gmud_key, f"Deploy em PRD concluido. Versao em producao: {release_tag}")
        gate_logger.record_decision(session, "approved", jira_key=jira_story_key)
    else:
        log.error(AGENT, f"Deploy em PRD nao concluiu com sucesso para {release_tag}")
        final_status = "Implementing (deploy falhou)"
        gate_logger.record_decision(session, "rejected", feedback="prd_failed", jira_key=jira_story_key)

    # Publica Release Notes (sempre, independente do sucesso)
    publish_release_notes(
        release_tag=release_tag,
        summary=summary,
        risk=risk_upper,
        change_type=change_type,
        gmud_key=gmud_key,
        gmud_url=gmud_url,
        run_id=run_id,
        run_url=run_url,
        jira_story_key=jira_story_key,
        affected_envs=affected_envs,
        final_status=final_status,
    )

    print()
    print("=" * 60)
    print(f"  RELEASE {release_tag} FINALIZADO")
    print(f"  Change type:  {change_type}")
    print(f"  Status final: {final_status}")
    print(f"  GMUD:         {gmud_url}")
    print(f"  Pipeline:     {run_url}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python release_agent.py <tag> <summary> [jira_story_key] [envs] [risk]")
        print('Ex:  python release_agent.py v1.2.0 "Feature X" POC-2 DEV,UAT,PRD LOW')
        sys.exit(1)
    tag = sys.argv[1]
    summary = sys.argv[2]
    story = sys.argv[3] if len(sys.argv) > 3 else None
    envs = sys.argv[4] if len(sys.argv) > 4 else "DEV,UAT,PRD"
    risk = sys.argv[5] if len(sys.argv) > 5 else "LOW"
    run_release(tag, summary, story, envs, risk)