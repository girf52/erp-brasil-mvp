import axios from 'axios'
import { formatReal } from './financeiro'
export { formatReal }

const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export type TipoPessoa = 'fisica' | 'juridica'
export type StatusCliente = 'ativo' | 'inativo' | 'bloqueado'
export type StatusPedido = 'rascunho' | 'confirmado' | 'faturado' | 'cancelado'

export interface Cliente {
  id: number; tipo: TipoPessoa; nome: string
  email: string | null; telefone: string | null
  limite_credito_centavos: number; status: StatusCliente
}

export interface Produto {
  id: number; codigo: string; descricao: string; unidade: string
  ncm: string | null; custo_medio_centavos: number
  estoque_atual: number; estoque_minimo: number
  permite_negativo: boolean; ativo: boolean
}

export interface PedidoItem {
  id: number; produto_id: number; qtd: number; preco_unitario_centavos: number
}

export interface Pedido {
  id: number; cliente_id: number; data: string; status: StatusPedido
  total_centavos: number; observacao: string | null; itens: PedidoItem[]
}

export interface PosicaoEstoque {
  produto_id: number; codigo: string; descricao: string
  estoque_atual: number; estoque_minimo: number
  custo_medio_centavos: number; alerta_minimo: boolean
}

export interface MovEstoque {
  id: number; produto_id: number; tipo: string; qtd: number
  custo_unitario_centavos: number; data: string
  referencia_tipo: string | null; referencia_id: number | null
}

export const clientesApi = {
  listar: (apenas_ativos = true) => api.get<Cliente[]>('/clientes', { params: { apenas_ativos } }).then(r => r.data),
  criar: (data: Pick<Cliente, 'tipo' | 'nome' | 'email' | 'telefone' | 'limite_credito_centavos'>) =>
    api.post<Cliente>('/clientes', data).then(r => r.data),
}

export const produtosApi = {
  listar: (apenas_ativos = true) => api.get<Produto[]>('/produtos', { params: { apenas_ativos } }).then(r => r.data),
  criar: (data: Pick<Produto, 'codigo' | 'descricao' | 'unidade' | 'ncm' | 'estoque_minimo' | 'permite_negativo'>) =>
    api.post<Produto>('/produtos', data).then(r => r.data),
  entradaEstoque: (data: { produto_id: number; qtd: number; custo_unitario_centavos: number; data: string }) =>
    api.post<Produto>('/estoque/entrada', data).then(r => r.data),
}

export const estoqueApi = {
  posicao: () => api.get<PosicaoEstoque[]>('/estoque/posicao').then(r => r.data),
  movimentacoes: () => api.get<MovEstoque[]>('/estoque/movimentacoes').then(r => r.data),
}

export const pedidosApi = {
  listar: (params?: { cliente_id?: number; status?: StatusPedido }) =>
    api.get<Pedido[]>('/pedidos', { params }).then(r => r.data),
  criar: (data: { cliente_id: number; data: string; itens: Omit<PedidoItem, 'id'>[]; observacao?: string }) =>
    api.post<Pedido>('/pedidos', data).then(r => r.data),
  faturar: (id: number) => api.patch<Pedido>(`/pedidos/${id}/faturar`).then(r => r.data),
}
