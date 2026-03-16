"""
ERP Agents — Agente Base
Classe base que todos os agentes especializados herdam
"""
import os
import json
from typing import Any
import anthropic

from config import AgentConfig, SAFETY_LIMITS


class BaseAgent:
    """
    Classe base para todos os agentes do ERP.
    Gerencia a comunicação com a API da Anthropic e o ciclo agentico.
    """

    def __init__(self, agent_id: str, config: AgentConfig, system_prompt: str):
        self.agent_id    = agent_id
        self.config      = config
        self.system_prompt = system_prompt
        self.client      = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.tools       = self._define_tools()
        self.message_log: list[dict] = []

    def _define_tools(self) -> list[dict]:
        """
        Define as ferramentas disponíveis para este agente.
        Subclasses podem sobrescrever para adicionar ferramentas específicas.
        """
        return [
            {
                "name": "read_file",
                "description": "Lê o conteúdo de um arquivo do repositório",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Caminho do arquivo"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Escreve conteúdo em um arquivo (cria se não existir)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path":    {"type": "string", "description": "Caminho do arquivo"},
                        "content": {"type": "string", "description": "Conteúdo a escrever"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "run_command",
                "description": "Executa um comando shell (com verificações de segurança)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Comando a executar"},
                        "cwd":     {"type": "string", "description": "Diretório de trabalho (opcional)"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "list_files",
                "description": "Lista arquivos em um diretório",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Diretório a listar"},
                        "pattern":   {"type": "string", "description": "Padrão glob (default: **/*)"}
                    },
                    "required": ["directory"]
                }
            },
        ]

    def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Executa uma ferramenta e retorna o resultado."""
        from tools.code_tools import read_file, write_file, run_command, list_files
        from tools.github_tools import (
            create_feature_branch, commit_files, push_branch,
            create_pull_request, create_issue
        )

        tool_map = {
            "read_file":            lambda i: read_file(i["path"]),
            "write_file":           lambda i: write_file(i["path"], i["content"]),
            "run_command":          lambda i: run_command(i["command"], i.get("cwd")),
            "list_files":           lambda i: list_files(i["directory"], i.get("pattern", "**/*")),
            "create_feature_branch":lambda i: create_feature_branch(i["branch_name"], i.get("from_branch", "main")),
            "commit_files":         lambda i: commit_files(i["files"], i["message"], self.config.name),
            "push_branch":          lambda i: push_branch(i["branch_name"]),
            "create_pull_request":  lambda i: create_pull_request(i["title"], i["body"], i["branch"], i.get("base", "main"), i.get("labels")),
            "create_issue":         lambda i: create_issue(i["title"], i["body"], i.get("labels"), i.get("assignee")),
        }

        if tool_name in tool_map:
            return tool_map[tool_name](tool_input)
        return {"error": f"Ferramenta desconhecida: {tool_name}"}

    def run(self, task: str, context: dict | None = None) -> dict[str, Any]:
        """
        Executa o agente em um loop agentico até concluir a task.
        Retorna o resultado final.
        """
        print(f"\n  {self.config.name} iniciando task...")

        messages = [{"role": "user", "content": self._format_task(task, context)}]
        total_tokens = 0

        while True:
            # Verificação de segurança: limite de tokens
            if total_tokens > SAFETY_LIMITS["max_tokens_per_task"]:
                return {
                    "success": False,
                    "agent": self.agent_id,
                    "error": f"Limite de tokens excedido ({total_tokens}). Task muito complexa — divida em subtasks.",
                }

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens

            # Se o modelo decidiu parar
            if response.stop_reason == "end_turn":
                final_text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                print(f"  {self.config.name} concluiu. ({total_tokens} tokens)")
                return {
                    "success": True,
                    "agent": self.agent_id,
                    "result": final_text,
                    "tokens_used": total_tokens,
                }

            # Se o modelo quer usar ferramentas
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        print(f"    🔧 {self.config.name} usando: {block.name}")
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                # Stop reason inesperado
                return {
                    "success": False,
                    "agent": self.agent_id,
                    "error": f"Stop reason inesperado: {response.stop_reason}",
                }

    def _format_task(self, task: str, context: dict | None) -> str:
        """Formata a task com contexto adicional."""
        formatted = task
        if context:
            formatted += f"\n\n---\nContexto adicional:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        return formatted
