import axios from 'axios'

const api = axios.create({ baseURL: '/api/financeiro' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export type Natureza = 'ativo' | 'passivo' | 'patrimonio' | 'receita' | 'despesa' | 'cmv' | 'resultado_financeiro'
export type Tipo = 'sintetica' | 'analitica'

export interface Conta {
  id: number; codigo: string; descricao: string
  natureza: Natureza; tipo: Tipo; conta_pai_id: number | null; ativo: boolean
}

export interface Lancamento {
  id: number; data_competencia: string; data_pagamento: string | null
  historico: string; debito_conta_id: number; credito_conta_id: number
  valor_centavos: number; centro_custo: string | null; usuario_id: number | null
}

export interface DRELinha { grupo: string; valor_centavos: number }
export interface DRE {
  periodo: { inicio: string; fim: string }
  linhas: DRELinha[]
  receita_bruta_centavos: number
  total_custos_centavos: number
  resultado_liquido_centavos: number
}

export const financeiroApi = {
  listarContas: () => api.get<Conta[]>('/plano-contas').then(r => r.data),
  criarConta: (data: Omit<Conta, 'id' | 'ativo'>) => api.post<Conta>('/plano-contas', data).then(r => r.data),

  listarLancamentos: (inicio?: string, fim?: string) =>
    api.get<Lancamento[]>('/lancamentos', { params: { inicio, fim } }).then(r => r.data),
  criarLancamento: (data: Omit<Lancamento, 'id' | 'usuario_id'>) =>
    api.post<Lancamento>('/lancamentos', data).then(r => r.data),

  dre: (inicio: string, fim: string) =>
    api.get<DRE>('/dre', { params: { inicio, fim } }).then(r => r.data),
}

export const formatReal = (centavos: number) =>
  (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
