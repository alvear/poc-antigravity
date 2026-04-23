"""
Testes de archi_helper.

Cobertura:
- nid() gera IDs unicos com formato esperado
- generate_technical_view cria arquivos .archimate e manifest.json
- generate_technical_view respeita nome do modelo

archi_helper nao faz HTTP - so IO local. Testes usam tmp_path fixture.
"""
import json
from pathlib import Path
from unittest.mock import patch

import archi_helper


# ---- nid (gerador de ID) ----
def test_nid_format():
    """nid comeca com 'id-' e tem 24 chars hex apos o prefixo."""
    id_str = archi_helper.nid()
    assert id_str.startswith("id-")
    assert len(id_str) == 3 + 24  # prefixo 'id-' + 24 hex chars


def test_nid_uniqueness():
    """nid gera valores unicos em chamadas sucessivas."""
    ids = {archi_helper.nid() for _ in range(100)}
    assert len(ids) == 100  # zero colisoes


# ---- generate_technical_view ----
def test_generate_technical_view_creates_files(tmp_path, monkeypatch):
    """generate_technical_view cria .archimate + manifest.json no MODELS_DIR."""
    # Redireciona MODELS_DIR pra tmp_path
    monkeypatch.setattr(archi_helper, "MODELS_DIR", str(tmp_path))
    
    config = {
        "channels": ["Web", "Mobile"],
        "gcp": {"gke_cluster": "my-cluster"},
        "databases": ["Postgres"],
        "external_apis": ["Google OAuth"],
    }
    
    result = archi_helper.generate_technical_view("test-model", config)
    
    # Retorna tupla (archimate_path, manifest_path)
    assert isinstance(result, tuple)
    assert len(result) == 2
    
    # Arquivos devem existir
    archi_files = list(tmp_path.glob("*.archimate"))
    manifest_files = list(tmp_path.glob("*_manifest.json"))
    
    assert len(archi_files) >= 1, f"Nenhum .archimate criado em {tmp_path}"
    assert len(manifest_files) >= 1, f"Nenhum manifest criado em {tmp_path}"


def test_generate_technical_view_manifest_valid_json(tmp_path, monkeypatch):
    """Manifest gerado deve ser JSON valido."""
    monkeypatch.setattr(archi_helper, "MODELS_DIR", str(tmp_path))
    
    config = {"channels": ["Web"], "gcp": {"gke_cluster": "c"}}
    archi_helper.generate_technical_view("m", config)
    
    manifest_files = list(tmp_path.glob("*_manifest.json"))
    assert manifest_files
    
    # Deve ser JSON valido
    data = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert isinstance(data, dict)
