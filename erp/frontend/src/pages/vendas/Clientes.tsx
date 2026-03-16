import { useEffect, useState } from 'react'
import { clientesApi, type Cliente, type TipoPessoa, formatReal } from '../../api/vendas'

const TIPOS: { value: TipoPessoa; label: string }[] = [
  { value: 'fisica', label: 'Pessoa Física' },
  { value: 'juridica', label: 'Pessoa Jurídica' },
]

const statusColor: Record<string, string> = {
  ativo: 'bg-green-100 text-green-700',
  inativo: 'bg-gray-100 text-gray-600',
  bloqueado: 'bg-red-100 text-red-700',
}

export default function Clientes() {
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [erro, setErro] = useState('')
  const [form, setForm] = useState({ tipo: 'juridica' as TipoPessoa, nome: '', email: '', telefone: '', limite_credito_centavos: '0' })

  const load = () => clientesApi.listar(false).then(setClientes).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true); setErro('')
    try {
      await clientesApi.criar({ ...form, limite_credito_centavos: Number(form.limite_credito_centavos) * 100 })
      setShowForm(false)
      setForm({ tipo: 'juridica', nome: '', email: '', telefone: '', limite_credito_centavos: '0' })
      load()
    } catch (err: any) {
      setErro(err?.response?.data?.detail ?? 'Erro ao salvar')
    } finally { setSaving(false) }
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Clientes</h2>
          <p className="text-sm text-gray-500">{clientes.length} cliente(s) cadastrado(s)</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + Novo Cliente
        </button>
      </div>

      {showForm && (
        <form onSubmit={salvar} className="bg-white border rounded-xl p-5 mb-6 space-y-4">
          <h3 className="font-medium text-gray-700">Novo Cliente</h3>
          {erro && <p className="text-red-600 text-sm bg-red-50 rounded p-2">{erro}</p>}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 font-medium">Tipo</label>
              <select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value as TipoPessoa }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1">
                {TIPOS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Nome / Razão Social *</label>
              <input required value={form.nome} onChange={e => setForm(f => ({ ...f, nome: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="Nome completo" />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">E-mail</label>
              <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="email@empresa.com" />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Telefone</label>
              <input value={form.telefone} onChange={e => setForm(f => ({ ...f, telefone: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="(11) 99999-9999" />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Limite de Crédito (R$)</label>
              <input type="number" min="0" step="0.01" value={form.limite_credito_centavos}
                onChange={e => setForm(f => ({ ...f, limite_credito_centavos: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Salvando…' : 'Salvar'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-gray-400 text-sm">Carregando…</p>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Nome', 'Tipo', 'E-mail', 'Limite de Crédito', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {clientes.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Nenhum cliente cadastrado</td></tr>
              ) : clientes.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{c.nome}</td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{c.tipo === 'fisica' ? 'Pessoa Física' : 'Pessoa Jurídica'}</td>
                  <td className="px-4 py-3 text-gray-500">{c.email ?? '—'}</td>
                  <td className="px-4 py-3">{formatReal(c.limite_credito_centavos)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${statusColor[c.status]}`}>{c.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
