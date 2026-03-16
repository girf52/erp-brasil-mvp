"""
[Dev RH] Service — funcionários, eventos, cálculo de folha CLT.
Tabelas INSS/IRRF 2026 embutidas (sem API externa).
Todos os valores em centavos (inteiro).
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from models.rh import (
    Funcionario, EventoFolha, Folha,
    StatusFuncionario, StatusFolha, TipoEvento, RegimeContratacao,
)

# ── INSS 2026 — tabela progressiva ──
# (teto_centavos, faixa_centavos, aliquota)
TABELA_INSS = [
    (141200,  750, 0.075),
    (282400, 1060, 0.09),
    (400200,  900, 0.12),
    (750000,  500, 0.14),
]

# ── IRRF 2026 — base após dedução INSS + dependentes ──
# (teto_centavos, aliquota, deducao_centavos)
DEDUCAO_DEPENDENTE = 18959  # R$ 189,59
TABELA_IRRF = [
    (200096, 0.000,     0),
    (293504, 0.075, 15007),
    (387534, 0.150, 37011),
    (481521, 0.225, 66078),
    (float('inf'), 0.275, 90131),
]


def calcular_inss(salario_bruto: int) -> int:
    """Calcula INSS progressivo. Entrada e saída em centavos."""
    total = 0
    base_anterior = 0
    for teto, _, aliquota in TABELA_INSS:
        if salario_bruto <= base_anterior:
            break
        faixa = min(salario_bruto, teto) - base_anterior
        total += round(faixa * aliquota)
        base_anterior = teto
    return total


def calcular_irrf(salario_bruto: int, inss: int, dependentes: int = 0) -> int:
    """Calcula IRRF. Base = bruto - INSS - deduções por dependente."""
    base = salario_bruto - inss - (dependentes * DEDUCAO_DEPENDENTE)
    if base <= 0:
        return 0
    for teto, aliquota, deducao in TABELA_IRRF:
        if base <= teto:
            imposto = round(base * aliquota) - deducao
            return max(imposto, 0)
    return 0


def calcular_fgts(salario_bruto: int) -> int:
    """FGTS = 8% do salário bruto."""
    return round(salario_bruto * 0.08)


# ── CRUD Funcionários ──

def criar_funcionario(db: Session, nome: str, cpf: str, cargo: str,
                      salario_base_centavos: int, data_admissao: date,
                      regime: str = "clt", dependentes: int = 0) -> Funcionario:
    cpf_limpo = cpf.replace(".", "").replace("-", "")
    if len(cpf_limpo) != 11:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="CPF deve ter 11 dígitos")
    if salario_base_centavos <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Salário deve ser positivo")
    existente = db.query(Funcionario).filter(Funcionario.cpf == cpf_limpo).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="CPF já cadastrado")

    func = Funcionario(
        nome=nome, cpf=cpf_limpo, cargo=cargo,
        salario_base_centavos=salario_base_centavos,
        data_admissao=data_admissao,
        regime=RegimeContratacao(regime),
        dependentes=dependentes,
    )
    db.add(func)
    db.commit()
    db.refresh(func)
    return func


def listar_funcionarios(db: Session, apenas_ativos: bool = True) -> list[Funcionario]:
    q = db.query(Funcionario)
    if apenas_ativos:
        q = q.filter(Funcionario.status == StatusFuncionario.ATIVO)
    return q.order_by(Funcionario.nome).all()


def demitir_funcionario(db: Session, func_id: int, data_demissao: date) -> Funcionario:
    func = db.get(Funcionario, func_id)
    if not func:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
    if func.status == StatusFuncionario.DEMITIDO:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Já demitido")
    func.status = StatusFuncionario.DEMITIDO
    func.data_demissao = data_demissao
    db.commit()
    db.refresh(func)
    return func


# ── Eventos de Folha ──

def criar_evento(db: Session, funcionario_id: int, competencia: str,
                 tipo: str, valor_centavos: int, descricao: Optional[str] = None) -> EventoFolha:
    func = db.get(Funcionario, funcionario_id)
    if not func:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
    evento = EventoFolha(
        funcionario_id=funcionario_id, competencia=competencia,
        tipo=TipoEvento(tipo), valor_centavos=valor_centavos,
        descricao=descricao,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


def listar_eventos(db: Session, competencia: str, funcionario_id: Optional[int] = None) -> list[EventoFolha]:
    q = db.query(EventoFolha).filter(EventoFolha.competencia == competencia)
    if funcionario_id:
        q = q.filter(EventoFolha.funcionario_id == funcionario_id)
    return q.all()


# ── Cálculo de Folha ──

TIPOS_PROVENTO = {TipoEvento.HORA_EXTRA, TipoEvento.BONUS}
TIPOS_DESCONTO = {TipoEvento.FALTA, TipoEvento.DESCONTO, TipoEvento.VALE_TRANSPORTE, TipoEvento.VALE_REFEICAO}


def calcular_folha(db: Session, competencia: str) -> list[Folha]:
    """Calcula folha para todos os funcionários ativos na competência."""
    funcionarios = db.query(Funcionario).filter(
        Funcionario.status == StatusFuncionario.ATIVO
    ).all()

    if not funcionarios:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Nenhum funcionário ativo")

    folhas = []
    for func in funcionarios:
        # Verifica se já existe folha calculada
        existente = db.query(Folha).filter(and_(
            Folha.competencia == competencia,
            Folha.funcionario_id == func.id,
        )).first()
        if existente:
            folhas.append(existente)
            continue

        # Busca eventos do mês
        eventos = db.query(EventoFolha).filter(and_(
            EventoFolha.competencia == competencia,
            EventoFolha.funcionario_id == func.id,
        )).all()

        proventos = sum(e.valor_centavos for e in eventos if e.tipo in TIPOS_PROVENTO)
        descontos_evento = sum(e.valor_centavos for e in eventos if e.tipo in TIPOS_DESCONTO)

        salario_bruto = func.salario_base_centavos + proventos
        inss = calcular_inss(salario_bruto)
        irrf = calcular_irrf(salario_bruto, inss, func.dependentes)
        fgts = calcular_fgts(salario_bruto)
        outros_descontos = descontos_evento
        salario_liquido = salario_bruto - inss - irrf - outros_descontos

        folha = Folha(
            competencia=competencia,
            funcionario_id=func.id,
            salario_bruto=salario_bruto,
            inss=inss, irrf=irrf, fgts=fgts,
            outros_descontos=outros_descontos,
            salario_liquido=salario_liquido,
        )
        db.add(folha)
        db.flush()
        folhas.append(folha)

    db.commit()
    for f in folhas:
        db.refresh(f)
    return folhas


def listar_folhas(db: Session, competencia: Optional[str] = None) -> list[Folha]:
    q = db.query(Folha)
    if competencia:
        q = q.filter(Folha.competencia == competencia)
    return q.order_by(Folha.competencia.desc(), Folha.funcionario_id).all()


def obter_holerite(db: Session, folha_id: int) -> dict:
    """Retorna dados do holerite para renderização."""
    folha = db.get(Folha, folha_id)
    if not folha:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folha não encontrada")
    func = db.get(Funcionario, folha.funcionario_id)
    eventos = db.query(EventoFolha).filter(and_(
        EventoFolha.competencia == folha.competencia,
        EventoFolha.funcionario_id == folha.funcionario_id,
    )).all()
    return {
        "funcionario": {"nome": func.nome, "cpf": func.cpf, "cargo": func.cargo},
        "competencia": folha.competencia,
        "salario_bruto": folha.salario_bruto,
        "inss": folha.inss,
        "irrf": folha.irrf,
        "fgts": folha.fgts,
        "outros_descontos": folha.outros_descontos,
        "salario_liquido": folha.salario_liquido,
        "eventos": [{"tipo": e.tipo.value, "valor_centavos": e.valor_centavos, "descricao": e.descricao} for e in eventos],
    }
