"""
ERP Agents — Ferramentas GitHub
Integração com a API do GitHub para os agentes
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Any


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")
REPO_NAME    = os.getenv("GITHUB_REPO", "erp-sistema")
BASE_BRANCH  = "main"


def _run_git(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Executa um comando git e retorna (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True, text=True, cwd=cwd or os.getcwd()
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def create_feature_branch(branch_name: str, from_branch: str = BASE_BRANCH) -> dict[str, Any]:
    """Cria uma nova branch de feature a partir da branch base."""
    # Garante que estamos na branch base atualizada
    _run_git(["fetch", "origin"])
    _run_git(["checkout", from_branch])
    _run_git(["pull", "origin", from_branch])

    # Cria e faz checkout da nova branch
    code, out, err = _run_git(["checkout", "-b", branch_name])
    if code != 0:
        # Branch já existe, apenas faz checkout
        _run_git(["checkout", branch_name])

    return {
        "success": code == 0 or "already exists" in err,
        "branch": branch_name,
        "from": from_branch,
        "message": out or err,
    }


def commit_files(
    files: list[str],
    message: str,
    agent_name: str,
) -> dict[str, Any]:
    """
    Faz commit dos arquivos especificados.
    Usa Conventional Commits: feat:, fix:, docs:, test:, chore:
    """
    from config import SAFETY_LIMITS

    # Verificação de segurança: limite de arquivos por commit
    if len(files) > SAFETY_LIMITS["max_files_per_commit"]:
        return {
            "success": False,
            "error": f"Limite de {SAFETY_LIMITS['max_files_per_commit']} arquivos por commit excedido.",
        }

    # Verifica branch atual (nunca commita diretamente em main/production)
    _, current_branch, _ = _run_git(["branch", "--show-current"])
    if current_branch in SAFETY_LIMITS["protected_branches"]:
        return {
            "success": False,
            "error": f"BLOQUEADO: Tentativa de commit direto em branch protegida '{current_branch}'.",
        }

    # Adiciona os arquivos
    for file in files:
        _run_git(["add", file])

    # Commit com referência ao agente
    full_message = f"{message}\n\nCo-authored-by: {agent_name} <agent@erp-sistema>"
    code, out, err = _run_git(["commit", "-m", full_message])

    return {
        "success": code == 0,
        "branch": current_branch,
        "files_committed": files,
        "message": out or err,
    }


def push_branch(branch_name: str) -> dict[str, Any]:
    """Faz push da branch para o repositório remoto."""
    code, out, err = _run_git(["push", "-u", "origin", branch_name])
    return {
        "success": code == 0,
        "branch": branch_name,
        "output": out or err,
    }


def create_pull_request(
    title: str,
    body: str,
    branch: str,
    base: str = BASE_BRANCH,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Cria um Pull Request no GitHub via CLI (requer gh instalado)."""
    cmd = [
        "gh", "pr", "create",
        "--title", title,
        "--body", body,
        "--head", branch,
        "--base", base,
    ]
    if labels:
        for label in labels:
            cmd += ["--label", label]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "output": result.stdout.strip(),
        "error": result.stderr.strip() if result.returncode != 0 else None,
    }


def create_issue(
    title: str,
    body: str,
    labels: list[str] | None = None,
    assignee: str | None = None,
) -> dict[str, Any]:
    """Cria uma Issue no GitHub (usado pelo QA para reportar bugs)."""
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    if labels:
        for label in labels:
            cmd += ["--label", label]
    if assignee:
        cmd += ["--assignee", assignee]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "success": result.returncode == 0,
        "output": result.stdout.strip(),
        "error": result.stderr.strip() if result.returncode != 0 else None,
    }


def get_current_branch() -> str:
    _, branch, _ = _run_git(["branch", "--show-current"])
    return branch


def get_recent_commits(n: int = 5) -> list[str]:
    _, out, _ = _run_git(["log", f"-{n}", "--oneline"])
    return out.splitlines()
