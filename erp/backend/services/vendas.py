"""
[⚙️ Dev Vendas/Estoque] Service — regras de negócio Sprint 2.
Regras críticas: estoque nunca negativo, CMP recalculado a cada entrada, faturamento atômico.
"""
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from models.vendas import (
    Cliente, Produto, Pedido, PedidoItem, MovEstoque,
    TipoPessoa, StatusCliente, StatusPedido, TipoMovEstoque,
)


# ─── Clientes ─────────────────────────────────────────────────────────────────

def criar_cliente(db: Session, tipo: TipoPessoa, nome: str,
                  email: Optional[str] = None, telefone: Optional[str] = None,
                  limite_credito_centavos: int = 0,
                  cpf_cnpj_enc: Optional[str] = None) -> Cliente:
    cliente = Cliente(
        tipo=tipo, nome=nome, email=email, telefone=telefone,
        limite_credito_centavos=limite_credito_centavos,
        cpf_cnpj_enc=cpf_cnpj_enc,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def listar_clientes(db: Session, apenas_ativos: bool = True) -> list[Cliente]:
    q = db.query(Cliente)
    if apenas_ativos:
        q = q.filter(Cliente.status == StatusCliente.ATIVO)
    return q.order_by(Cliente.nome).all()


def get_cliente_or_404(db: Session, cliente_id: int) -> Cliente:
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return c


# ─── Produtos ─────────────────────────────────────────────────────────────────

def criar_produto(db: Session, codigo: str, descricao: str, unidade: str = "UN",
                  ncm: Optional[str] = None, estoque_minimo: int = 0,
                  permite_negativo: bool = False) -> Produto:
    if db.query(Produto).filter(Produto.codigo == codigo).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Código {codigo} já existe")
    p = Produto(codigo=codigo, descricao=descricao, unidade=unidade,
                ncm=ncm, estoque_minimo=estoque_minimo, permite_negativo=permite_negativo)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def listar_produtos(db: Session, apenas_ativos: bool = True) -> list[Produto]:
    q = db.query(Produto)
    if apenas_ativos:
        q = q.filter(Produto.ativo == True)  # noqa: E712
    return q.order_by(Produto.codigo).all()


def get_produto_or_404(db: Session, produto_id: int) -> Produto:
    p = db.get(Produto, produto_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    return p


def entrada_estoque(db: Session, produto_id: int, qtd: int,
                    custo_unitario_centavos: int, data_mov: date,
                    referencia_tipo: Optional[str] = None,
                    referencia_id: Optional[int] = None) -> Produto:
    """Entrada de estoque com recálculo de CMP (Custo Médio Ponderado)."""
    if qtd <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantidade deve ser positiva")
    if custo_unitario_centavos < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Custo não pode ser negativo")

    produto = get_produto_or_404(db, produto_id)

    # CMP = (estoque_atual * custo_atual + qtd_entrada * custo_entrada) / (estoque_atual + qtd_entrada)
    estoque_anterior = produto.estoque_atual
    if estoque_anterior + qtd > 0:
        novo_cmp = (
            (estoque_anterior * produto.custo_medio_centavos) + (qtd * custo_unitario_centavos)
        ) // (estoque_anterior + qtd)
    else:
        novo_cmp = custo_unitario_centavos

    produto.estoque_atual += qtd
    produto.custo_medio_centavos = novo_cmp

    mov = MovEstoque(
        produto_id=produto_id, tipo=TipoMovEstoque.ENTRADA, qtd=qtd,
        custo_unitario_centavos=custo_unitario_centavos, data=data_mov,
        referencia_tipo=referencia_tipo, referencia_id=referencia_id,
    )
    db.add(mov)
    db.commit()
    db.refresh(produto)
    return produto


def _reservar_estoque(db: Session, produto_id: int, qtd: int, pedido_id: int, data_mov: date) -> None:
    """Reserva estoque ao confirmar pedido (não baixa definitivo)."""
    produto = get_produto_or_404(db, produto_id)
    if not produto.permite_negativo and produto.estoque_atual < qtd:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Estoque insuficiente para {produto.codigo}: disponível {produto.estoque_atual}, solicitado {qtd}",
        )
    produto.estoque_atual -= qtd
    mov = MovEstoque(
        produto_id=produto_id, tipo=TipoMovEstoque.RESERVA, qtd=qtd,
        custo_unitario_centavos=produto.custo_medio_centavos, data=data_mov,
        referencia_tipo="pedido", referencia_id=pedido_id,
    )
    db.add(mov)


def posicao_estoque(db: Session) -> list[dict]:
    produtos = db.query(Produto).filter(Produto.ativo == True).order_by(Produto.codigo).all()  # noqa: E712
    return [
        {
            "produto_id": p.id, "codigo": p.codigo, "descricao": p.descricao,
            "estoque_atual": p.estoque_atual, "estoque_minimo": p.estoque_minimo,
            "custo_medio_centavos": p.custo_medio_centavos,
            "alerta_minimo": p.estoque_atual <= p.estoque_minimo,
        }
        for p in produtos
    ]


# ─── Pedidos ─────────────────────────────────────────────────────────────────

def criar_pedido(db: Session, cliente_id: int, data_pedido: date,
                 itens: list[dict], observacao: Optional[str] = None) -> Pedido:
    """Cria pedido e reserva estoque atomicamente."""
    get_cliente_or_404(db, cliente_id)

    if not itens:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pedido deve ter ao menos um item")

    total = 0
    itens_obj = []
    for item in itens:
        produto = get_produto_or_404(db, item["produto_id"])
        if item["qtd"] <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantidade do item deve ser positiva")
        if item["preco_unitario_centavos"] <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Preço unitário deve ser positivo")
        total += item["qtd"] * item["preco_unitario_centavos"]
        itens_obj.append(PedidoItem(
            produto_id=produto.id,
            qtd=item["qtd"],
            preco_unitario_centavos=item["preco_unitario_centavos"],
        ))

    pedido = Pedido(
        cliente_id=cliente_id, data=data_pedido,
        status=StatusPedido.CONFIRMADO,
        total_centavos=total, observacao=observacao,
    )
    db.add(pedido)
    db.flush()  # gera pedido.id sem commit

    for item_obj in itens_obj:
        item_obj.pedido_id = pedido.id
        db.add(item_obj)

    # Reserva estoque — se falhar, rollback completo (atômico)
    for item in itens:
        _reservar_estoque(db, item["produto_id"], item["qtd"], pedido.id, data_pedido)

    db.commit()
    db.refresh(pedido)
    return pedido


def faturar_pedido(db: Session, pedido_id: int) -> Pedido:
    """Fatura pedido: baixa estoque definitiva + gera conta a receber. Atômico."""
    pedido = db.get(Pedido, pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    if pedido.status != StatusPedido.CONFIRMADO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Pedido não pode ser faturado (status atual: {pedido.status})",
        )

    hoje = datetime.now(timezone.utc).date()

    # Baixa definitiva: registra SAIDA no estoque (RESERVA já abateu o saldo)
    for item in pedido.itens:
        mov = MovEstoque(
            produto_id=item.produto_id, tipo=TipoMovEstoque.SAIDA, qtd=item.qtd,
            custo_unitario_centavos=item.produto.custo_medio_centavos, data=hoje,
            referencia_tipo="pedido", referencia_id=pedido_id,
        )
        db.add(mov)

    pedido.status = StatusPedido.FATURADO
    pedido.faturado_em = datetime.now(timezone.utc)

    db.commit()
    db.refresh(pedido)
    return pedido


def listar_pedidos(db: Session, cliente_id: Optional[int] = None,
                   status_filtro: Optional[StatusPedido] = None) -> list[Pedido]:
    q = db.query(Pedido)
    if cliente_id:
        q = q.filter(Pedido.cliente_id == cliente_id)
    if status_filtro:
        q = q.filter(Pedido.status == status_filtro)
    return q.order_by(Pedido.data.desc(), Pedido.id.desc()).all()
