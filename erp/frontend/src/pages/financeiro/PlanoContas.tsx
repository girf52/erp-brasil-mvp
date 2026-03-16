import { useEffect, useState } from 'react'
import { financeiroApi, Conta, Natureza, Tipo } from '../../api/financeiro'

const NATUREZAS: Natureza[] = ['ativo','passivo','patrimonio','receita','despesa','cmv','resultado_financeiro']

export default function PlanoContas() {
  const [contas, setContas] = useState<Conta[]>([])
  const [form, setForm] = useState({ codigo: '', descricao: '', natureza: 'ativo' as Natureza, tipo: 'analitica' as Tipo })
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)

  async function carregar() {
    setContas(await financeiroApi.listarContas())
  }

  useEffect(() => { carregar() }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setErro(''); setLoading(true)
    try {
      await financeiroApi.criarConta({ ...form, conta_pai_id: null })
      setForm({ codigo: '', descricao: '', natureza: 'ativo', tipo: 'analitica' })
      await carregar()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setErro(msg ?? 'Erro ao criar conta')
    } finally { setLoading(false) }
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Plano de Contas</h2>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border p-4 grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-gray-600">Código</label>
          <input value={form.codigo} onChange={e => setForm(f => ({ ...f, codigo: e.target.value }))} required
            className="w-full border rounded-lg px-3 py-1.5 mt-1 text-sm focus:ring-2 focus:ring-blue-500 outline-none" placeholder="1.1.001" />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-600">Descrição</label>
          <input value={form.descricao} onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))} required
            className="w-full border rounded-lg px-3 py-1.5 mt-1 text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-600">Natureza</label>
          <select value={form.natureza} onChange={e => setForm(f => ({ ...f, natureza: e.target.value as Natureza }))}
            className="w-full border rounded-lg px-3 py-1.5 mt-1 text-sm">
            {NATUREZAS.map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-600">Tipo</label>
          <select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value as Tipo }))}
            className="w-full border rounded-lg px-3 py-1.5 mt-1 text-sm">
            <option value="analitica">Analítica</option>
            <option value="sintetica">Sintética</option>
          </select>
        </div>
        {erro && <p className="col-span-2 text-red-500 text-sm">{erro}</p>}
        <button type="submit" disabled={loading}
          className="col-span-2 bg-blue-600 text-white rounded-lg py-2 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50">
          {loading ? 'Salvando...' : '+ Adicionar Conta'}
        </button>
      </form>

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>{['Código','Descrição','Natureza','Tipo'].map(h => (
              <th key={h} className="text-left px-4 py-3 font-semibold text-gray-600">{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {contas.length === 0 && (
              <tr><td colSpan={4} className="text-center py-8 text-gray-400">Nenhuma conta cadastrada</td></tr>
            )}
            {contas.map(c => (
              <tr key={c.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-blue-600">{c.codigo}</td>
                <td className="px-4 py-3">{c.descricao}</td>
                <td className="px-4 py-3 capitalize">{c.natureza}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${c.tipo === 'analitica' ? 'bg-green-50 text-green-600' : 'bg-orange-50 text-orange-600'}`}>
                    {c.tipo}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
