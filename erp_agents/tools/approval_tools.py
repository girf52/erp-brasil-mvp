"""
ERP Agents — Ferramentas de Aprovação Humana
Mecanismo de pausa e checkpoint para o Raphael
"""
import json
import time
from datetime import datetime
from typing import Any


def request_human_approval(
    checkpoint_type: str,
    agent_name: str,
    description: str,
    details: dict[str, Any],
    options: list[str] | None = None,
) -> dict[str, Any]:
    """
    Pausa o fluxo e solicita aprovação do Raphael no terminal.
    Retorna a decisão tomada.
    """
    border = "═" * 70
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    print(f"\n{border}")
    print(f"  🔔 CHECKPOINT — APROVAÇÃO NECESSÁRIA")
    print(f"  Horário: {timestamp}")
    print(f"  Agente:  {agent_name}")
    print(f"  Tipo:    {checkpoint_type}")
    print(border)
    print(f"\n  📋 {description}\n")

    if details:
        print("  Detalhes:")
        for key, value in details.items():
            if isinstance(value, (dict, list)):
                print(f"    • {key}:")
                print(f"      {json.dumps(value, ensure_ascii=False, indent=6)}")
            else:
                print(f"    • {key}: {value}")
        print()

    if options:
        print("  Opções disponíveis:")
        for i, opt in enumerate(options, 1):
            print(f"    [{i}] {opt}")
        print()

    print(f"{border}")
    print("  ⚠️  O sistema está pausado aguardando sua decisão.")
    print(f"{border}\n")

    # Loop até receber resposta válida
    while True:
        if options:
            prompt = f"  Digite sua escolha (1-{len(options)}) ou 'rejeitar' para bloquear: "
        else:
            prompt = "  Aprovar? (sim/não) ou adicione um comentário: "

        response = input(prompt).strip().lower()

        if not response:
            print("  ⚠️  Resposta vazia. Digite sua decisão.\n")
            continue

        if options:
            try:
                choice = int(response) - 1
                if 0 <= choice < len(options):
                    decision = {
                        "approved": True,
                        "choice": options[choice],
                        "choice_index": choice,
                        "comment": "",
                        "timestamp": timestamp,
                        "checkpoint_type": checkpoint_type,
                        "agent": agent_name,
                    }
                    print(f"\n  ✅ Decisão registrada: {options[choice]}\n")
                    _log_decision(decision)
                    return decision
                else:
                    print(f"  ⚠️  Opção inválida. Escolha entre 1 e {len(options)}.\n")
            except ValueError:
                if response == "rejeitar":
                    comment = input("  Motivo da rejeição: ").strip()
                    decision = {
                        "approved": False,
                        "choice": "rejeitar",
                        "comment": comment,
                        "timestamp": timestamp,
                        "checkpoint_type": checkpoint_type,
                        "agent": agent_name,
                    }
                    print(f"\n  ❌ Ação rejeitada. Agentes notificados.\n")
                    _log_decision(decision)
                    return decision
                else:
                    print(f"  ⚠️  Digite um número entre 1 e {len(options)} ou 'rejeitar'.\n")
        else:
            if response in ("sim", "s", "yes", "y", "aprovar", "ok"):
                comment = input("  Comentário adicional (Enter para pular): ").strip()
                decision = {
                    "approved": True,
                    "comment": comment,
                    "timestamp": timestamp,
                    "checkpoint_type": checkpoint_type,
                    "agent": agent_name,
                }
                print(f"\n  ✅ Aprovado! Agentes retomando o trabalho.\n")
                _log_decision(decision)
                return decision
            elif response in ("não", "nao", "n", "no", "rejeitar", "bloquear"):
                comment = input("  Motivo da rejeição (obrigatório): ").strip()
                if not comment:
                    print("  ⚠️  Por favor, informe o motivo.\n")
                    continue
                decision = {
                    "approved": False,
                    "comment": comment,
                    "timestamp": timestamp,
                    "checkpoint_type": checkpoint_type,
                    "agent": agent_name,
                }
                print(f"\n  ❌ Rejeitado: {comment}\n")
                _log_decision(decision)
                return decision
            else:
                # Tratar como comentário + aprovação
                decision = {
                    "approved": True,
                    "comment": response,
                    "timestamp": timestamp,
                    "checkpoint_type": checkpoint_type,
                    "agent": agent_name,
                }
                print(f"\n  ✅ Aprovado com comentário: {response}\n")
                _log_decision(decision)
                return decision


def _log_decision(decision: dict[str, Any]) -> None:
    """Registra a decisão em arquivo de log para auditoria."""
    log_file = "sprint_decisions.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(decision, ensure_ascii=False) + "\n")


def notify_sprint_summary(
    sprint_number: int,
    completed_tasks: list[str],
    pending_tasks: list[str],
    metrics: dict[str, Any],
) -> None:
    """Exibe o resumo do sprint para o Raphael."""
    border = "═" * 70
    print(f"\n{border}")
    print(f"  📊 RESUMO DO SPRINT {sprint_number}")
    print(border)
    print(f"\n  ✅ Tarefas concluídas ({len(completed_tasks)}):")
    for task in completed_tasks:
        print(f"     • {task}")
    if pending_tasks:
        print(f"\n  ⏳ Pendentes ({len(pending_tasks)}):")
        for task in pending_tasks:
            print(f"     • {task}")
    if metrics:
        print(f"\n  📈 Métricas:")
        for key, value in metrics.items():
            print(f"     • {key}: {value}")
    print(f"\n{border}\n")
