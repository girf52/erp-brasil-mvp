"""
ERP Agents — Maestro ERP
Orquestrador central da equipe de agentes autônomos

Uso:
  python maestro.py --sprint 1 --goal "Implementar módulo Financeiro" --modules financeiro

O Maestro recebe o objetivo do sprint, decompõe em tasks, delega para os agentes
especializados e gerencia os checkpoints de aprovação humana.
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import Any

import anthropic

from config import ALL_AGENTS, MAESTRO_MODEL, TECH_STACK, ERP_MODULES, HUMAN_CHECKPOINTS
from agents.agent_factory import create_agent  # fábrica unificada v2
from tools.approval_tools import request_human_approval, notify_sprint_summary
from tools.github_tools import create_pull_request, get_recent_commits

# Alias para compatibilidade com código legado neste arquivo
AGENTS = ALL_AGENTS


# ─── System Prompt do Maestro ERP ─────────────────────────────────────────
MAESTRO_SYSTEM_PROMPT = f"""Você é o Maestro ERP — orquestrador central de uma equipe de agentes autônomos
que estão construindo um sistema ERP completo do zero.

AGENTES DA SUA EQUIPE:
{chr(10).join(f'- {cfg.name}: {key}' for key, cfg in AGENTS.items() if key != 'maestro_erp')}

STACK TECNOLÓGICA:
{chr(10).join(f'- {k}: {v}' for k, v in TECH_STACK.items())}

MÓDULOS DO ERP:
{chr(10).join(f'- {m}' for m in ERP_MODULES)}

SEUS PODERES E RESPONSABILIDADES:
1. Receber o objetivo do sprint do Raphael (Product Owner)
2. Decompor em tasks específicas e atribuir a agentes
3. Coordenar execução em paralelo quando possível
4. Identificar dependências entre tasks (ex: DBA antes do Dev Backend)
5. Pausar nos checkpoints críticos para aprovação humana
6. Consolidar resultados e gerar relatório do sprint

COMO DECOMPOR UM OBJETIVO EM TASKS:
- Cada task deve ter: ID, título, agente responsável, critérios de aceite, dependências
- Tasks de banco (DBA) sempre precedem tasks de código (Backend)
- Tasks de código (Backend) sempre precedem tasks de interface (Frontend)
- QA trabalha em paralelo com Frontend depois que o Backend está pronto
- Segurança revisa código antes do PR ser aberto
- DevOps é acionado ao final para deploy em staging

CHECKPOINTS QUE EXIGEM APROVAÇÃO HUMANA:
{chr(10).join(f'- {c}' for c in HUMAN_CHECKPOINTS)}

FORMATO DO PLANO DE SPRINT (retorne SEMPRE neste formato JSON):
{{
  "sprint_number": int,
  "goal": string,
  "estimated_duration": string,
  "tasks": [
    {{
      "id": "T001",
      "title": string,
      "agent": string,
      "description": string,
      "acceptance_criteria": [string],
      "dependencies": ["T000"],
      "estimated_tokens": int,
      "requires_human_approval": bool,
      "approval_reason": string | null
    }}
  ],
  "parallel_groups": [[task_ids], [task_ids]],
  "checkpoints": [{{checkpoint_type, task_after, description}}]
}}"""


class MaestroERP:
    """Orquestrador principal da equipe de agentes ERP."""

    def __init__(self, sprint_number: int, approval_mode: str = "semi-auto"):
        self.sprint_number  = sprint_number
        self.approval_mode  = approval_mode  # "semi-auto" | "auto" | "manual"
        self.client         = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.sprint_log: list[dict] = []
        self.completed_tasks: list[str] = []
        self.failed_tasks:    list[str] = []

    def run_sprint(self, goal: str, modules: list[str]) -> dict[str, Any]:
        """
        Executa um sprint completo.
        1. Planeja → 2. Aprova com Raphael → 3. Executa → 4. PR → 5. Aprova merge
        """
        print(f"\n{'='*70}")
        print(f"  🎼 MAESTRO ERP — SPRINT {self.sprint_number}")
        print(f"  Objetivo: {goal}")
        print(f"  Módulos:  {', '.join(modules)}")
        print(f"  Modo:     {self.approval_mode}")
        print(f"{'='*70}\n")

        # ── PASSO 1: Gera o plano do sprint ───────────────────────────────
        print("  📋 Gerando plano do sprint...")
        sprint_plan = self._generate_sprint_plan(goal, modules)
        if not sprint_plan:
            return {"success": False, "error": "Falha ao gerar plano do sprint"}

        # ── PASSO 2: Aprovação do plano pelo Raphael ───────────────────────
        self._display_sprint_plan(sprint_plan)
        if self.approval_mode != "auto":
            approval = request_human_approval(
                checkpoint_type="sprint_plan_approval",
                agent_name="🎼 Maestro ERP",
                description=f"Plano do Sprint {self.sprint_number} está pronto. Revise e aprove.",
                details={
                    "total_tasks": len(sprint_plan.get("tasks", [])),
                    "estimated_duration": sprint_plan.get("estimated_duration", "N/A"),
                    "modules": modules,
                },
                options=["Aprovar e iniciar", "Aprovar com ajustes (comente)", "Rejeitar e replanejar"],
            )
            if not approval["approved"] or approval.get("choice_index") == 2:
                print("  ⏸️  Sprint rejeitado. Aguardando novo objetivo.\n")
                return {"success": False, "reason": "Sprint rejeitado pelo Raphael", "comment": approval.get("comment")}

        # ── PASSO 3: Execução das tasks ────────────────────────────────────
        print("\n  🚀 Iniciando execução das tasks...\n")
        execution_results = self._execute_sprint_tasks(sprint_plan)

        # ── PASSO 4: Relatório e PR ────────────────────────────────────────
        pr_body = self._generate_pr_body(sprint_plan, execution_results)
        sprint_branch = f"sprint/{self.sprint_number}-{goal[:30].lower().replace(' ', '-')}"

        if self.approval_mode != "auto":
            approval = request_human_approval(
                checkpoint_type="pull_request_to_main",
                agent_name="🎼 Maestro ERP",
                description=f"Sprint {self.sprint_number} concluído. Revisar e aprovar PR para merge em main.",
                details={
                    "tasks_completed": len(self.completed_tasks),
                    "tasks_failed": len(self.failed_tasks),
                    "branch": sprint_branch,
                    "commits": get_recent_commits(5),
                },
                options=["Aprovar merge", "Solicitar ajustes antes do merge", "Rejeitar sprint"],
            )
            if approval["approved"] and approval.get("choice_index") == 0:
                pr_result = create_pull_request(
                    title=f"Sprint {self.sprint_number}: {goal}",
                    body=pr_body,
                    branch=sprint_branch,
                    labels=[f"sprint-{self.sprint_number}", *modules],
                )
                print(f"  🔀 Pull Request criado: {pr_result.get('output', 'verificar GitHub')}\n")

        # ── PASSO 5: Resumo final ──────────────────────────────────────────
        notify_sprint_summary(
            sprint_number=self.sprint_number,
            completed_tasks=self.completed_tasks,
            pending_tasks=self.failed_tasks,
            metrics={
                "total_tasks": len(sprint_plan.get("tasks", [])),
                "success_rate": f"{len(self.completed_tasks) / max(len(sprint_plan.get('tasks', [])), 1):.0%}",
                "branch": sprint_branch,
            }
        )

        return {"success": True, "sprint_number": self.sprint_number, "results": execution_results}

    def _generate_sprint_plan(self, goal: str, modules: list[str]) -> dict | None:
        """Usa o Maestro (LLM) para gerar o plano de tasks do sprint."""
        prompt = f"""Crie um plano de sprint detalhado para o seguinte objetivo:

OBJETIVO: {goal}
MÓDULOS AFETADOS: {', '.join(modules)}
SPRINT: {self.sprint_number}

Retorne SOMENTE o JSON do plano, sem texto adicional."""

        try:
            response = self.client.messages.create(
                model=MAESTRO_MODEL,
                max_tokens=8000,
                system=MAESTRO_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            plan_text = response.content[0].text.strip()
            # Remove markdown code block se presente
            if plan_text.startswith("```"):
                plan_text = plan_text.split("```")[1]
                if plan_text.startswith("json"):
                    plan_text = plan_text[4:]
            return json.loads(plan_text)
        except Exception as e:
            print(f"  ❌ Erro ao gerar plano: {e}")
            return None

    def _execute_sprint_tasks(self, sprint_plan: dict) -> list[dict]:
        """Executa as tasks do sprint na ordem correta, respeitando dependências."""
        tasks = sprint_plan.get("tasks", [])
        results = []
        task_map = {t["id"]: t for t in tasks}
        completed_ids = set()

        # Executa em grupos paralelos (quando definidos) ou sequencialmente
        parallel_groups = sprint_plan.get("parallel_groups", [[t["id"] for t in tasks]])

        for group in parallel_groups:
            group_tasks = [task_map[tid] for tid in group if tid in task_map]
            print(f"\n  ▶ Executando grupo de {len(group_tasks)} task(s) em paralelo...\n")

            # Por simplicidade, executamos sequencialmente aqui
            # Em produção, use asyncio ou threading para paralelismo real
            for task in group_tasks:
                # Verifica dependências
                deps_ok = all(dep in completed_ids for dep in task.get("dependencies", []))
                if not deps_ok:
                    print(f"  ⏭️  Pulando {task['id']} — dependências não concluídas")
                    continue

                result = self._execute_single_task(task)
                results.append(result)

                if result["success"]:
                    completed_ids.add(task["id"])
                    self.completed_tasks.append(f"[{task['id']}] {task['title']}")
                else:
                    self.failed_tasks.append(f"[{task['id']}] {task['title']}: {result.get('error', 'falha')}")

                # Checkpoint humano se necessário
                if task.get("requires_human_approval") and self.approval_mode != "auto":
                    approval = request_human_approval(
                        checkpoint_type=task.get("approval_reason", "task_completion"),
                        agent_name="🎼 Maestro ERP",
                        description=f"Task {task['id']} concluída: {task['title']}. Revisar antes de continuar.",
                        details={"task_result": result.get("result", "")[:500]},
                        options=["Continuar para próxima task", "Revisar e ajustar", "Parar sprint"],
                    )
                    if not approval["approved"]:
                        print("  ⏸️  Sprint pausado por decisão do Raphael.\n")
                        return results

        return results

    def _execute_single_task(self, task: dict) -> dict:
        """Executa uma única task delegando para o agente especializado."""
        agent_id = task.get("agent", "dev_backend")
        print(f"  📌 [{task['id']}] {task['title']} → {AGENTS.get(agent_id, type('', (), {'name': agent_id})()).name if hasattr(AGENTS.get(agent_id, None), 'name') else agent_id}")

        try:
            agent = create_agent(agent_id)
            result = agent.run(
                task=task.get("description", task["title"]),
                context={
                    "task_id": task["id"],
                    "sprint": self.sprint_number,
                    "acceptance_criteria": task.get("acceptance_criteria", []),
                    "tech_stack": TECH_STACK,
                }
            )
            print(f"  {'✅' if result['success'] else '❌'} [{task['id']}] {task['title']}")
            return result
        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ [{task['id']}] Erro: {error_msg}")
            return {"success": False, "agent": agent_id, "error": error_msg}

    def _display_sprint_plan(self, plan: dict) -> None:
        """Exibe o plano de sprint de forma legível no terminal."""
        print(f"\n  📋 PLANO DO SPRINT {plan.get('sprint_number', self.sprint_number)}")
        print(f"  Duração estimada: {plan.get('estimated_duration', 'N/A')}")
        print(f"  Total de tasks: {len(plan.get('tasks', []))}\n")

        for task in plan.get("tasks", []):
            agent_name = AGENTS.get(task.get("agent", ""), type("", (), {"name": "?"})())
            approval_flag = " 🔔" if task.get("requires_human_approval") else ""
            print(f"  [{task['id']}]{approval_flag} {task['title']}")
            print(f"       Agente: {getattr(agent_name, 'name', task.get('agent', '?'))}")
            if task.get("dependencies"):
                print(f"       Depende: {', '.join(task['dependencies'])}")
        print()

    def _generate_pr_body(self, plan: dict, results: list[dict]) -> str:
        """Gera o corpo do Pull Request com resumo do sprint."""
        success_count = sum(1 for r in results if r.get("success"))
        return f"""## Sprint {self.sprint_number} — {plan.get('goal', 'N/A')}

### Resumo
- **Tasks concluídas:** {success_count}/{len(results)}
- **Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
- **Modo:** Semi-autônomo (checkpoints humanos)

### Tasks Completadas
{chr(10).join(f'- ✅ {t}' for t in self.completed_tasks)}

### Tasks com Falha
{chr(10).join(f'- ❌ {t}' for t in self.failed_tasks) or '- Nenhuma'}

### Agentes Envolvidos
{chr(10).join(f'- {AGENTS[r["agent"]].name}' for r in results if r.get("agent") in AGENTS)}

---
🤖 Gerado automaticamente pelo Maestro ERP (Claude Agent SDK)"""


# ─── PONTO DE ENTRADA ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Maestro ERP — Orquestrador de Agentes Autônomos")
    parser.add_argument("--sprint",         type=int,   required=True, help="Número do sprint")
    parser.add_argument("--goal",           type=str,   required=True, help="Objetivo do sprint")
    parser.add_argument("--modules",        type=str,   nargs="+",     default=["financeiro"], help="Módulos afetados")
    parser.add_argument("--approval-mode",  type=str,   default="semi-auto", choices=["auto", "semi-auto", "manual"])

    args = parser.parse_args()

    # Verifica variáveis de ambiente obrigatórias
    missing_vars = []
    for var in ["ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GITHUB_OWNER"]:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"\n  ❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("  Configure o arquivo .env e execute: source .env\n")
        sys.exit(1)

    maestro = MaestroERP(
        sprint_number=args.sprint,
        approval_mode=args.approval_mode,
    )

    result = maestro.run_sprint(
        goal=args.goal,
        modules=args.modules,
    )

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
