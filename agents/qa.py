"""
QA Agent (migrado para BaseAgent, Sprint 3).

Fluxo:
  1. Monta arquivo de testes pytest (scaffold + edge cases)
  2. Valida sintaticamente via AST
  3. Atualiza requirements.txt (append se faltar)
  4. Commita na branch do PR (shift-left testing)
  5. Publica evidencia no Confluence

Templates (TEST_SCAFFOLD, LLM_EDGE_CASES, CONFTEST) ficam em agents/qa_templates.py
para separar dados de logica. Isso facilita:
- Versionar prompts/templates independente
- Testar com mocks
- Evolucao futura para geracao LLM dinamica
"""
import ast
import json
import sys
from pathlib import Path

import confluence_helper
import github_helper
from agents.base import BaseAgent
from agents.exceptions import AntigravityError, ValidationError
from agents.qa_templates import CONFTEST, LLM_EDGE_CASES, TEST_SCAFFOLD


class QAAgent(BaseAgent):
    AGENT_NAME = "qa-agent"

    def run(
        self,
        branch: str = "feature/POC-2-autenticacao-google-oauth",
        story: str = "POC-2",
    ):
        with self.propose("test-suite", f"pytest suite for {story}") as session:
            session.set_jira_key(story)
            session.add_context(branch=branch)
            self.log_info(
                f"QA Agent iniciado para {story} na branch {branch}"
            )

            # ---- Etapa 1 - gera scaffold ----
            self.log_info("Etapa 1/5: gerando scaffold deterministico")
            full_test = TEST_SCAFFOLD.replace(
                "# LLM_EDGE_CASES_PLACEHOLDER",
                "# [IA] Edge cases abaixo foram gerados por LLM\n" + LLM_EDGE_CASES,
            )
            tests_dir = Path("tests")
            tests_dir.mkdir(exist_ok=True)
            (tests_dir / "__init__.py").write_text("", encoding="utf-8")
            (tests_dir / "conftest.py").write_text(CONFTEST, encoding="utf-8")
            test_file = tests_dir / "test_auth.py"
            test_file.write_text(full_test, encoding="utf-8")
            self.log_success(
                "Arquivos gerados: tests/test_auth.py, tests/conftest.py, tests/__init__.py"
            )

            # ---- Etapa 2 - validacao AST ----
            self.log_info("Etapa 2/5: validacao sintatica (AST)")
            tree = ast.parse(test_file.read_text(encoding="utf-8"))
            test_fns = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
            ]
            collected = len(test_fns)
            self.log_info(
                f"AST validou: {collected} funcoes de teste detectadas",
                {"test_names": [fn.name for fn in test_fns]},
            )
            if collected == 0:
                raise ValidationError("qa-agent", "Nenhum teste detectado no arquivo gerado")

            # ---- Etapa 3 - atualiza requirements.txt ----
            self.log_info("Etapa 3/5: atualizando requirements.txt")
            req_path = Path("requirements.txt")
            existing = req_path.read_text(encoding="utf-8") if req_path.exists() else ""
            needed = ["pytest", "pytest-asyncio", "httpx", "respx"]
            to_add = [p for p in needed if p not in existing]
            if to_add:
                new_req = existing.rstrip() + "\n" + "\n".join(to_add) + "\n"
                req_path.write_text(new_req, encoding="utf-8")
                self.log_info(
                    f"Adicionado ao requirements.txt: {to_add}"
                )

            # ---- Etapa 4 - commit na branch do PR ----
            self.log_info(f"Etapa 4/5: commitando na branch {branch}")
            github_helper.commit_file(
                branch=branch,
                filepath="tests/__init__.py",
                content="",
                message=f"test({story}): add tests package marker",
            )
            github_helper.commit_file(
                branch=branch,
                filepath="tests/conftest.py",
                content=CONFTEST,
                message=f"test({story}): add pytest conftest",
            )
            github_helper.commit_file(
                branch=branch,
                filepath="tests/test_auth.py",
                content=full_test,
                message=f"test({story}): add auth OAuth test suite (happy + errors + edge cases)",
            )
            if to_add:
                github_helper.commit_file(
                    branch=branch,
                    filepath="requirements.txt",
                    content=req_path.read_text(encoding="utf-8"),
                    message=f"chore({story}): add pytest/respx to requirements",
                )

            # ---- Etapa 5 - evidencia no Confluence ----
            self.log_info("Etapa 5/5: publicando evidencia no Confluence")
            deterministic_count = (
                full_test.count("def test_") - LLM_EDGE_CASES.count("def test_")
            )
            llm_count = LLM_EDGE_CASES.count("def test_")
            total = deterministic_count + llm_count

            confluence_body = self._render_confluence_body(
                story=story,
                branch=branch,
                total=total,
                det_count=deterministic_count,
                llm_count=llm_count,
            )
            confluence_helper.create_page(
                title=f"QA Evidence - {story} - Google OAuth",
                content=confluence_body,
                parent_title="POC-Antigravity",
            )

            self.log_success(
                f"QA completo: {total} testes, branch {branch}, "
                "evidencia publicada no Confluence"
            )
            result = {
                "agent": self.AGENT_NAME,
                "story": story,
                "branch": branch,
                "tests_total": total,
                "tests_deterministic": deterministic_count,
                "tests_llm": llm_count,
            }
            print(json.dumps(result, indent=2))
            session.add_context(
                tests_total=total,
                tests_deterministic=deterministic_count,
                tests_llm=llm_count,
            )
            return result

    # -----------------------------------------------------------
    # Helpers internos
    # -----------------------------------------------------------
    @staticmethod
    def _render_confluence_body(story, branch, total, det_count, llm_count):
        """Monta o HTML da pagina Confluence (sem f-string multilinha com aspas)."""
        parts = []
        parts.append(f"<h1>Evidencia de QA - {story}</h1>")
        parts.append(f"<p><strong>Agente:</strong> QA Agent (POC Antigravity)</p>")
        parts.append(f"<p><strong>Branch:</strong> <code>{branch}</code></p>")
        parts.append("<p><strong>Data:</strong> gerado automaticamente</p>")
        parts.append("")
        parts.append("<h2>Testes gerados</h2>")
        parts.append("<ul>")
        parts.append(f"  <li>Total: <strong>{total}</strong> casos</li>")
        parts.append(f"  <li>Deterministicos (template): <strong>{det_count}</strong></li>")
        parts.append(f"  <li>Edge cases (IA): <strong>{llm_count}</strong></li>")
        parts.append("</ul>")
        parts.append("")
        parts.append("<h2>Estrategia</h2>")
        parts.append(
            "<p>Shift-left testing - testes commitados na mesma branch "
            "do PR de desenvolvimento.</p>"
        )
        parts.append(
            "<p>Geracao hibrida: scaffold deterministico (fixtures, "
            "happy + error paths) + enriquecimento por LLM para edge "
            "cases especificos de OAuth (Google timeout, unverified email, "
            "malformed id_token, CSRF state abuse).</p>"
        )
        parts.append("")
        parts.append("<h2>Cobertura dos casos</h2>")
        parts.append("<h3>Happy path</h3>")
        parts.append("<ul>")
        parts.append("  <li>GET /health retorna 200</li>")
        parts.append("  <li>GET /v1/auth/login redireciona para Google</li>")
        parts.append("  <li>GET /v1/auth/callback com code valido autentica</li>")
        parts.append("</ul>")
        parts.append("<h3>Error paths</h3>")
        parts.append("<ul>")
        parts.append("  <li>Callback sem code retorna 400/422</li>")
        parts.append("  <li>Callback com code invalido retorna 400/401</li>")
        parts.append("  <li>State mismatch (CSRF) retorna 400/403</li>")
        parts.append("  <li>Acesso sem token retorna 401</li>")
        parts.append("</ul>")
        parts.append("<h3>Edge cases (IA)</h3>")
        parts.append("<ul>")
        parts.append("  <li>Email nao verificado</li>")
        parts.append("  <li>Timeout do Google</li>")
        parts.append("  <li>redirect_uri nao-HTTPS</li>")
        parts.append("  <li>id_token malformado</li>")
        parts.append("  <li>State param com tamanho abusivo (DoS)</li>")
        parts.append("</ul>")
        parts.append("")
        parts.append("<h2>Links</h2>")
        parts.append(
            '<p>Pull Request: <a href="https://github.com/alvear/poc-antigravity/pull/1">'
            "PR #1 - Autenticacao Google OAuth</a></p>"
        )
        parts.append(
            '<p>CI Pipeline: <a href="https://github.com/alvear/poc-antigravity/actions">'
            "GitHub Actions</a></p>"
        )
        return "\n".join(parts)


if __name__ == "__main__":
    branch = sys.argv[1] if len(sys.argv) > 1 else "feature/POC-2-autenticacao-google-oauth"
    story = sys.argv[2] if len(sys.argv) > 2 else "POC-2"
    try:
        QAAgent().run(branch=branch, story=story)
    except AntigravityError as exc:
        print(f"[QA] falhou: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"[QA] erro inesperado: {exc}")
        sys.exit(1)
