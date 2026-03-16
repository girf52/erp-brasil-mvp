from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from core.deps import get_db, get_current_user
from core.crypto import encrypt
from models.vendas import TipoPessoa, StatusPedido, MovEstoque
from services import vendas as svc

router = APIRouter(prefix="/api", tags=["vendas"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ClienteIn(BaseModel):
    tipo: TipoPessoa
    nome: str
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    limite_credito_centavos: int = 0


class ClienteOut(BaseModel):
    id: int; tipo: TipoPessoa; nome: str
    email: Optional[str]; telefone: Optional[str]
    limite_credito_centavos: int; status: str
    model_config = {"from_attributes": True}


class ProdutoIn(BaseModel):
    codigo: str; descricao: str; unidade: str = "UN"
    ncm: Optional[str] = None; estoque_minimo: int = 0
    permite_negativo: bool = False


class ProdutoOut(BaseModel):
    id: int; codigo: str; descricao: str; unidade: str
    ncm: Optional[str]; custo_medio_centavos: int
    estoque_atual: int; estoque_minimo: int; permite_negativo: bool; ativo: bool
    model_config = {"from_attributes": True}


class EntradaEstoqueIn(BaseModel):
    produto_id: int; qtd: int
    custo_unitario_centavos: int; data: date

    @field_validator("qtd")
    @classmethod
    def qtd_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("qtd deve ser positiva")
        return v


class PedidoItemIn(BaseModel):
    produto_id: int; qtd: int; preco_unitario_centavos: int


class PedidoIn(BaseModel):
    cliente_id: int; data: date
    itens: list[PedidoItemIn]
    observacao: Optional[str] = None


class PedidoItemOut(BaseModel):
    id: int; produto_id: int; qtd: int; preco_unitario_centavos: int
    model_config = {"from_attributes": True}


class PedidoOut(BaseModel):
    id: int; cliente_id: int; data: date; status: str
    total_centavos: int; observacao: Optional[str]
    itens: list[PedidoItemOut]
    model_config = {"from_attributes": True}


# ─── Clientes ─────────────────────────────────────────────────────────────────

@router.post("/clientes", response_model=ClienteOut, status_code=201)
def criar_cliente(payload: ClienteIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cpf_cnpj_enc = encrypt(payload.cpf_cnpj) if payload.cpf_cnpj else None
    return svc.criar_cliente(db, payload.tipo, payload.nome, payload.email,
                             payload.telefone, payload.limite_credito_centavos,
                             cpf_cnpj_enc)


@router.get("/clientes", response_model=list[ClienteOut])
def listar_clientes(apenas_ativos: bool = True, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_clientes(db, apenas_ativos)


# ─── Produtos ─────────────────────────────────────────────────────────────────

@router.post("/produtos", response_model=ProdutoOut, status_code=201)
def criar_produto(payload: ProdutoIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.criar_produto(db, payload.codigo, payload.descricao, payload.unidade,
                             payload.ncm, payload.estoque_minimo, payload.permite_negativo)


@router.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(apenas_ativos: bool = True, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.listar_produtos(db, apenas_ativos)


@router.post("/estoque/entrada", response_model=ProdutoOut)
def entrada_estoque(payload: EntradaEstoqueIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.entrada_estoque(db, payload.produto_id, payload.qtd,
                               payload.custo_unitario_centavos, payload.data)


@router.get("/estoque/posicao")
def posicao_estoque(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.posicao_estoque(db)


@router.get("/estoque/movimentacoes")
def movimentacoes(db: Session = Depends(get_db), _=Depends(get_current_user)):
    movs = db.query(MovEstoque).order_by(MovEstoque.criado_em.desc()).limit(200).all()
    return [{"id": m.id, "produto_id": m.produto_id, "tipo": m.tipo,
             "qtd": m.qtd, "custo_unitario_centavos": m.custo_unitario_centavos,
             "data": m.data, "referencia_tipo": m.referencia_tipo,
             "referencia_id": m.referencia_id} for m in movs]


# ─── Pedidos ─────────────────────────────────────────────────────────────────

@router.post("/pedidos", response_model=PedidoOut, status_code=201)
def criar_pedido(payload: PedidoIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.criar_pedido(db, payload.cliente_id, payload.data,
                            [i.model_dump() for i in payload.itens], payload.observacao)


@router.patch("/pedidos/{pedido_id}/faturar", response_model=PedidoOut)
def faturar_pedido(pedido_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return svc.faturar_pedido(db, pedido_id)


@router.get("/pedidos", response_model=list[PedidoOut])
def listar_pedidos(
    cliente_id: Optional[int] = Query(None),
    status: Optional[StatusPedido] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return svc.listar_pedidos(db, cliente_id, status)
