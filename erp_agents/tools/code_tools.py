"""
ERP Agents — Ferramentas de Código
Leitura, escrita e execução de código pelos agentes
"""
import os
import subprocess
from pathlib import Path
from typing import Any


def read_file(path: str) -> dict[str, Any]:
    """Lê um arquivo do repositório."""
    try:
        content = Path(path).read_text(encoding="utf-8")
        return {"success": True, "content": content, "path": path}
    except FileNotFoundError:
        return {"success": False, "error": f"Arquivo não encontrado: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str, create_dirs: bool = True) -> dict[str, Any]:
    """
    Escreve conteúdo em um arquivo.
    Cria os diretórios necessários automaticamente.
    """
    try:
        file_path = Path(path)
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return {"success": True, "path": path, "bytes_written": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(directory: str, pattern: str = "**/*") -> dict[str, Any]:
    """Lista arquivos em um diretório com padrão glob."""
    try:
        files = [str(f) for f in Path(directory).glob(pattern) if f.is_file()]
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_command(
    command: str,
    cwd: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """
    Executa um comando shell com verificações de segurança.
    Bloqueia comandos proibidos da configuração.
    """
    from config import SAFETY_LIMITS

    # Verificação de segurança
    for forbidden in SAFETY_LIMITS["forbidden_commands"]:
        if forbidden.lower() in command.lower():
            return {
                "success": False,
                "error": f"BLOQUEADO: Comando proibido detectado: '{forbidden}'",
                "command": command,
            }

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout após {timeout}s", "command": command}
    except Exception as e:
        return {"success": False, "error": str(e), "command": command}


def run_tests(
    test_path: str = "tests/",
    module: str | None = None,
) -> dict[str, Any]:
    """Executa os testes com pytest e retorna resultado."""
    cmd = f"python -m pytest {test_path}"
    if module:
        cmd += f" -k {module}"
    cmd += " --tb=short --json-report --json-report-file=test_results.json -q"

    result = run_command(cmd)

    # Tenta ler o relatório JSON
    coverage_info = {}
    try:
        import json
        with open("test_results.json") as f:
            report = json.load(f)
        coverage_info = {
            "passed": report.get("summary", {}).get("passed", 0),
            "failed": report.get("summary", {}).get("failed", 0),
            "total":  report.get("summary", {}).get("total", 0),
        }
    except Exception:
        pass

    return {**result, "test_summary": coverage_info}


def check_code_style(path: str) -> dict[str, Any]:
    """Verifica estilo de código com ruff (Python) ou eslint (TypeScript)."""
    if path.endswith(".py") or Path(path).is_dir():
        return run_command(f"python -m ruff check {path} --output-format=json")
    elif path.endswith((".ts", ".tsx", ".js", ".jsx")):
        return run_command(f"npx eslint {path} --format json")
    return {"success": True, "message": "Nenhum linter configurado para este tipo de arquivo"}


def scan_security(path: str) -> dict[str, Any]:
    """Escaneia vulnerabilidades de segurança com bandit (Python)."""
    if path.endswith(".py") or Path(path).is_dir():
        result = run_command(f"python -m bandit -r {path} -f json -q")
        # bandit retorna 1 se encontrar issues, não é erro de execução
        result["success"] = True
        return result
    return {"success": True, "message": "Scanner não configurado para este tipo"}
