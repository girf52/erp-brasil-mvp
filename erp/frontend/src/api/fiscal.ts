import axios from 'axios'
import { formatReal } from './financeiro'
export { formatReal }

const api = axios.create({ baseURL: '/api/fiscal' })
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export type StatusNFe = 'pendente' | 'autorizada' | 'cancelada' | 'rejeitada'

export interface NFe {
  id: number; numero: number; serie: number
  chave_acesso: string | null; cnpj_emit: string; cnpj_dest: string
  valor_total_centavos: number; status: StatusNFe
  protocolo: string | null; motivo_cancelamento: string | null
  emitido_em: string | null; cancelado_em: string | null
}

export const nfeApi = {
  listar: (status?: StatusNFe) =>
    api.get<NFe[]>('/nfe', { params: status ? { status } : {} }).then(r => r.data),
  emitir: (data: { cnpj_emit: string; cnpj_dest: string; valor_total_centavos: number; serie?: number }) =>
    api.post<NFe>('/nfe/emitir', data).then(r => r.data),
  cancelar: (id: number, motivo: string) =>
    api.post<NFe>(`/nfe/${id}/cancelar`, { motivo }).then(r => r.data),
  xml: (id: number) =>
    api.get<string>(`/nfe/${id}/xml`, { responseType: 'text' as any }).then(r => r.data),
}
