import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import axios from 'axios'

const API = 'http://localhost:8000/api'
const token = () => localStorage.getItem('access_token') || ''
const fmt = (c: number) => (c / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

interface DashData {
  clientes: number; produtos: number
  pedidos_total: number; pedidos_faturados: number
  faturamento_centavos: number
  nfes_emitidas: number; nfes_canceladas: number
  funcionarios_ativos: number; folha_total_centavos: number
  lancamentos: number
}

export default function Dashboard() {
  const [data, setData] = useState<DashData | null>(null)

  useEffect(() => {
    axios.get(`${API}/dashboard`, { headers: { Authorization: `Bearer ${token()}` } })
      .then(r => setData(r.data))
      .catch(() => {})
  }, [])

  if (!data) return <div className="p-6 text-gray-400 text-sm">Carregando dashboard...</div>

  const cards = [
    { label: 'Faturamento', value: fmt(data.faturamento_centavos), color: 'text-green-700', bg: 'bg-green-50 border-green-200', link: '/vendas/pedidos' },
    { label: 'Folha Liquida', value: fmt(data.folha_total_centavos), color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', link: '/rh/folha' },
    { label: 'Clientes', value: data.clientes, color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200', link: '/vendas/clientes' },
    { label: 'Produtos', value: data.produtos, color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', link: '/vendas/produtos' },
    { label: 'Pedidos', value: `${data.pedidos_faturados}/${data.pedidos_total}`, color: 'text-indigo-700', bg: 'bg-indigo-50 border-indigo-200', link: '/vendas/pedidos', sub: 'faturados' },
    { label: 'NF-e Emitidas', value: data.nfes_emitidas, color: 'text-teal-700', bg: 'bg-teal-50 border-teal-200', link: '/fiscal/nfe' },
    { label: 'NF-e Canceladas', value: data.nfes_canceladas, color: 'text-red-600', bg: 'bg-red-50 border-red-200', link: '/fiscal/nfe' },
    { label: 'Funcionarios', value: data.funcionarios_ativos, color: 'text-cyan-700', bg: 'bg-cyan-50 border-cyan-200', link: '/rh/funcionarios', sub: 'ativos' },
    { label: 'Lancamentos', value: data.lancamentos, color: 'text-gray-700', bg: 'bg-gray-50 border-gray-200', link: '/financeiro/plano-contas' },
  ]

  const shortcuts = [
    { label: 'Plano de Contas', to: '/financeiro/plano-contas', icon: '📊' },
    { label: 'DRE', to: '/financeiro/dre', icon: '📈' },
    { label: 'Novo Pedido', to: '/vendas/pedidos', icon: '🛒' },
    { label: 'Estoque', to: '/estoque', icon: '📦' },
    { label: 'Emitir NF-e', to: '/fiscal/nfe', icon: '🧾' },
    { label: 'Calcular Folha', to: '/rh/folha', icon: '💰' },
  ]

  return (
    <div className="p-6 max-w-7xl">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-800">Dashboard</h2>
        <p className="text-sm text-gray-500">Visao geral do ERP Brasil MVP</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
        {cards.map(c => (
          <NavLink key={c.label} to={c.link}
            className={`${c.bg} border rounded-xl p-4 hover:shadow-md transition block`}>
            <p className="text-xs text-gray-500 font-medium">{c.label}</p>
            <p className={`text-xl font-bold ${c.color} mt-1`}>{c.value}</p>
            {c.sub && <p className="text-[10px] text-gray-400 mt-0.5">{c.sub}</p>}
          </NavLink>
        ))}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-600 mb-3">Acesso Rapido</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {shortcuts.map(s => (
            <NavLink key={s.label} to={s.to}
              className="bg-white border rounded-xl p-4 hover:shadow-md transition text-center block">
              <div className="text-2xl mb-1">{s.icon}</div>
              <p className="text-xs font-medium text-gray-700">{s.label}</p>
            </NavLink>
          ))}
        </div>
      </div>
    </div>
  )
}
