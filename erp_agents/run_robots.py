"""
ERP Agents — Runner dos Robôs Autônomos
Executa os robôs do Setor de Automação IA de forma agendada ou sob demanda.

Uso:
  # Execução agendada (inicia o scheduler permanente)
  python run_robots.py --mode scheduled

  # Execução manual de um robô específico
  python run_robots.py --mode manual --robot robot_sefaz
  python run_robots.py --mode manual --robot robot_conciliacao
  python run_robots.py --mode manual --robot robot_audit_fiscal --scope full

  # Executar todos agora (para teste inicial)
  python run_robots.py --mode all
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.sectors.automacao_ia import get_automacao_agents, get_robot_schedule, ROBOT_SCHEDULE
from tools.approval_tools import request_human_approval
from config import SAFETY_LIMITS, ALL_AGENTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("robots.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("RobotRunner")


# ─── Executor central dos robôs ───────────────────────────────────────────

class RobotRunner:
    def __init__(self):
        self.agents = get_automacao_agents()
        self.execution_log: list[dict] = []

    def run_robot(self, robot_id: str, task_override: str | None = None, scope: str = "default") -> dict[str, Any]:
        """Executa um robô específico e registra o resultado."""
        agent = self.agents.get(robot_id)
        if not agent:
            log.error(f"Robô não encontrado: {robot_id}")
            return {"success": False, "error": f"Robô desconhecido: {robot_id}"}

        config = ALL_AGENTS.get(robot_id)
        log.info(f"▶ Iniciando {config.name if config else robot_id}...")

        task = task_override or self._build_task(robot_id, scope)

        try:
            result = agent.run(task=task, context={"scope": scope, "timestamp": datetime.now().isoformat()})

            # Verifica se precisa de aprovação humana
            if config and config.approval_required:
                self._handle_approval(robot_id, result, config.name)

            self._log_execution(robot_id, result)
            log.info(f"✅ {config.name if config else robot_id} concluído.")
            return result

        except Exception as e:
            log.error(f"❌ Erro no {robot_id}: {e}", exc_info=True)
            return {"success": False, "robot": robot_id, "error": str(e)}

    def _build_task(self, robot_id: str, scope: str) -> str:
        """Constrói a instrução de task para cada robô."""
        tasks = {
            "robot_sefaz": (
                "Execute o ciclo completo de busca de NF-es na SEFAZ: "
                "autentique com o certificado digital, consulte o endpoint de distribuição de DF-e, "
                "baixe e processe todos os XMLs novos, armazene no S3 e retorne o relatório JSON."
            ),
            "robot_cadastro": (
                "Processe todas as NF-es com status='pendente_cadastro' no banco de dados: "
                "cadastre/atualize fornecedores, produtos, movimente estoque e gere contas a pagar. "
                "Retorne JSON com resultado por NF-e processada."
            ),
            "robot_audit_fiscal": (
                f"Execute auditoria fiscal {'completa do catálogo' if scope == 'full' else 'dos produtos novos e alterados nos últimos 7 dias'}: "
                "verifique NCM na TIPI, CEST na tabela ICMS 142/2018, alíquotas de PIS/COFINS/ICMS/IPI. "
                "Gere relatório HTML e JSON com produtos por status (CORRETO/ATENÇÃO/ERRO). "
                f"Correções em lote > {SAFETY_LIMITS['max_product_corrections_auto']} produtos requerem aprovação humana."
            ),
            "robot_conciliacao": (
                "Execute conciliação bancária do dia anterior: "
                "busque extrato via Open Finance (Pluggy), execute matching automático em cascata, "
                "categorize não conciliados, gere relatório de posição e alertas de divergência. "
                f"Divergência > R$ {SAFETY_LIMITS['reconciliation_divergence_alert']:,.0f} requer alerta humano imediato."
            ),
            "robot_cobranca": (
                "Execute a régua de cobrança do dia: "
                "identifique clientes por faixa de atraso (D-3, D+1, D+5, D+15, D+30, D+60), "
                "envie notificações personalizadas via e-mail e WhatsApp Business, "
                "aplique juros/multa conforme contrato, escale para humano quando necessário. "
                f"Cobrança em lote > {SAFETY_LIMITS['max_collection_batch_auto']} clientes requer aprovação."
            ),
            "robot_credito": (
                "Execute reavaliação de crédito mensal: "
                "para cada cliente ativo, calcule score interno (histórico + volume + solidez), "
                "consulte Receita Federal e Serasa (se configurado), "
                "sugira novo limite de crédito com justificativa. "
                f"Limites > R$ {SAFETY_LIMITS['max_credit_limit_auto']:,.0f} sempre requerem aprovação humana."
            ),
        }
        return tasks.get(robot_id, f"Execute o ciclo padrão do {robot_id}.")

    def _handle_approval(self, robot_id: str, result: dict, agent_name: str) -> None:
        """Verifica se o resultado requer aprovação humana e solicita se necessário."""
        result_text = str(result.get("result", ""))

        # Analisa o resultado para detectar itens que requerem aprovação
        escalation_keywords = [
            "requer aprovação", "aguardando aprovação",
            "divergência > R$", "lote >", "bloqueio proposto",
            "limite >", "human_escalation"
        ]

        needs_approval = any(kw.lower() in result_text.lower() for kw in escalation_keywords)

        if needs_approval:
            approval = request_human_approval(
                checkpoint_type=f"robot_result_{robot_id}",
                agent_name=agent_name,
                description=f"O {agent_name} encontrou itens que requerem sua decisão.",
                details={"resultado_resumo": result_text[:800]},
                options=["Confirmar ações propostas", "Revisar manualmente", "Ignorar por agora"],
            )
            result["human_decision"] = approval

    def _log_execution(self, robot_id: str, result: dict) -> None:
        """Salva log de execução em arquivo JSON."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "robot_id": robot_id,
            "success": result.get("success", False),
            "tokens_used": result.get("tokens_used", 0),
        }
        self.execution_log.append(entry)

        log_file = "automation_log.json"
        existing = []
        try:
            if os.path.exists(log_file):
                with open(log_file, encoding="utf-8") as f:
                    existing = json.load(f)
        except Exception:
            pass
        existing.append(entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(existing[-500:], f, ensure_ascii=False, indent=2)  # mantém últimas 500 execuções

    # ── Modo agendado ──────────────────────────────────────────────────────
    def start_scheduled(self) -> None:
        """Inicia o scheduler APScheduler com todos os robôs configurados."""
        scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
        schedule = get_robot_schedule()

        for robot_id, config in schedule.items():
            if config["cron"] == "triggered":
                continue  # robôs acionados por outros (não têm cron próprio)

            cron_parts = config["cron"].split()
            trigger = CronTrigger(
                minute=cron_parts[0], hour=cron_parts[1],
                day=cron_parts[2],    month=cron_parts[3],
                day_of_week=cron_parts[4],
                timezone="America/Sao_Paulo"
            )
            scheduler.add_job(
                func=self.run_robot,
                trigger=trigger,
                args=[robot_id],
                id=robot_id,
                name=config["desc"],
                max_instances=1,  # nunca roda o mesmo robô em paralelo
                misfire_grace_time=3600,  # se perdeu o horário, tenta até 1h depois
            )
            log.info(f"📅 Agendado: {ALL_AGENTS[robot_id].name} — {config['desc']}")

        log.info("\n🤖 Scheduler iniciado. Robôs prontos.\n")
        print("\n  Pressione Ctrl+C para parar o scheduler.\n")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            log.info("Scheduler encerrado pelo usuário.")


# ─── Ponto de entrada ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ERP — Runner dos Robôs Autônomos")
    parser.add_argument("--mode",   choices=["scheduled", "manual", "all"], default="manual")
    parser.add_argument("--robot",  help="ID do robô (para --mode manual)")
    parser.add_argument("--scope",  default="default", help="Escopo: 'full' para auditoria completa")
    parser.add_argument("--task",   help="Task personalizada para o robô")
    args = parser.parse_args()

    # Verifica variáveis de ambiente
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n  ❌ ANTHROPIC_API_KEY não configurada. Execute: source .env\n")
        sys.exit(1)

    runner = RobotRunner()

    if args.mode == "scheduled":
        runner.start_scheduled()

    elif args.mode == "manual":
        if not args.robot:
            print("\n  ❌ Informe o robô com --robot. Opções disponíveis:")
            for robot_id, cfg in ROBOT_SCHEDULE.items():
                print(f"     {robot_id:25s} → {cfg['desc']}")
            print()
            sys.exit(1)
        result = runner.run_robot(args.robot, args.task, args.scope)
        print(f"\n  Resultado: {'✅ Sucesso' if result.get('success') else '❌ Falha'}")

    elif args.mode == "all":
        print("\n  🚀 Executando todos os robôs em sequência...\n")
        ordem = ["robot_sefaz", "robot_cadastro", "robot_audit_fiscal",
                 "robot_conciliacao", "robot_cobranca", "robot_credito"]
        for robot_id in ordem:
            result = runner.run_robot(robot_id, scope=args.scope)
            status = "✅" if result.get("success") else "❌"
            print(f"  {status} {robot_id}")


if __name__ == "__main__":
    main()
