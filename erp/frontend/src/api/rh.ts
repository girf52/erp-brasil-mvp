import axios from 'axios'
import { formatReal } from './financeiro'
export { formatReal }

const api = axios.create({ baseURL: '/api/rh' })
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export interface Funcionario {
  id: number; nome: string; cpf: string; cargo: string
  salario_base_centavos: number; data_admissao: string
  data_demissao: string | null; regime: string; status: string
  dependentes: number
}

export interface EventoFolha {
  id: number; funcionario_id: number; competencia: string
  tipo: string; valor_centavos: number; descricao: string | null
}

export interface Folha {
  id: number; competencia: string; funcionario_id: number
  salario_bruto: number; inss: number; irrf: number; fgts: number
  outros_descontos: number; salario_liquido: number; status: string
}

export interface Holerite {
  funcionario: { nome: string; cpf: string; cargo: string }
  competencia: string
  salario_bruto: number; inss: number; irrf: number; fgts: number
  outros_descontos: number; salario_liquido: number
  eventos: { tipo: string; valor_centavos: number; descricao: string | null }[]
}

export const funcionariosApi = {
  listar: (apenas_ativos = true) =>
    api.get<Funcionario[]>('/funcionarios', { params: { apenas_ativos } }).then(r => r.data),
  criar: (data: Omit<Funcionario, 'id' | 'data_demissao' | 'status'>) =>
    api.post<Funcionario>('/funcionarios', data).then(r => r.data),
  demitir: (id: number, data_demissao: string) =>
    api.post<Funcionario>(`/funcionarios/${id}/demitir`, { data_demissao }).then(r => r.data),
}

export const eventosApi = {
  listar: (competencia: string, funcionario_id?: number) =>
    api.get<EventoFolha[]>('/eventos', { params: { competencia, funcionario_id } }).then(r => r.data),
  criar: (data: Omit<EventoFolha, 'id'>) =>
    api.post<EventoFolha>('/eventos', data).then(r => r.data),
}

export const folhaApi = {
  calcular: (competencia: string) =>
    api.post<Folha[]>('/folha/calcular', null, { params: { competencia } }).then(r => r.data),
  listar: (competencia?: string) =>
    api.get<Folha[]>('/folha', { params: competencia ? { competencia } : {} }).then(r => r.data),
  holerite: (id: number) =>
    api.get<Holerite>(`/folha/${id}/holerite`).then(r => r.data),
}
