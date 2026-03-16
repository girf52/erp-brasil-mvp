import { useEffect, useState } from 'react'
import { produtosApi, type Produto, formatReal } from '../../api/vendas'

export default function Produtos() {
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showEntrada, setShowEntrada] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [erro, setErro] = useState('')
  const [form, setForm] = useState({ codigo: '', descricao: '', unidade: 'UN', ncm: '', estoque_minimo: '0', permite_negativo: false })
  const [entrada, setEntrada] = useState({ qtd: '1', custo_unitario_centavos: '', data: new Date().toISOString().slice(0, 10) })

  const load = () => produtosApi.listar(false).then(setProdutos).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  async function salvarProduto(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setErro('')
    try {
      await produtosApi.criar({ ...form, estoque_minimo: Number(form.estoque_minimo), ncm: form.ncm || null })
      setShowForm(false); setForm({ codigo: '', descricao: '', unidade: 'UN', ncm: '', estoque_minimo: '0', permite_negativo: false })
      load()
    } catch (err: any) { setErro(err?.response?.data?.detail ?? 'Erro ao salvar') }
    finally { setSaving(false) }
  }

  async function salvarEntrada(e: React.FormEvent) {
    e.preventDefault(); if (!showEntrada) return; setSaving(true); setErro('')
    try {
      await produtosApi.entradaEstoque({
        produto_id: showEntrada,
        qtd: Number(entrada.qtd),
        custo_unitario_centavos: Math.round(Number(entrada.custo_unitario_centavos) * 100),
        data: entrada.data,
      })
      setShowEntrada(null); load()
    } catch (err: any) { setErro(err?.response?.data?.detail ?? 'Erro na entrada') }
    finally { setSaving(false) }
  }

  const prod = produtos.find(p => p.id === showEntrada)

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Produtos</h2>
          <p className="text-sm text-gray-500">{produtos.length} produto(s)</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + Novo Produto
        </button>
      </div>

      {showForm && (
        <form onSubmit={salvarProduto} className="bg-white border rounded-xl p-5 mb-6 space-y-4">
          <h3 className="font-medium text-gray-700">Novo Produto</h3>
          {erro && <p className="text-red-600 text-sm bg-red-50 rounded p-2">{erro}</p>}
          <div className="grid grid-cols-3 gap-4">
            <div><label className="text-xs text-gray-500 font-medium">Código *</label>
              <input required value={form.codigo} onChange={e => setForm(f => ({ ...f, codigo: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="SKU-001" /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500 font-medium">Descrição *</label>
              <input required value={form.descricao} onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" /></div>
            <div><label className="text-xs text-gray-500 font-medium">Unidade</label>
              <input value={form.unidade} onChange={e => setForm(f => ({ ...f, unidade: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="UN" /></div>
            <div><label className="text-xs text-gray-500 font-medium">NCM</label>
              <input value={form.ncm} onChange={e => setForm(f => ({ ...f, ncm: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="0000.00.00" /></div>
            <div><label className="text-xs text-gray-500 font-medium">Estoque Mínimo</label>
              <input type="number" min="0" value={form.estoque_minimo} onChange={e => setForm(f => ({ ...f, estoque_minimo: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" /></div>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={form.permite_negativo} onChange={e => setForm(f => ({ ...f, permite_negativo: e.target.checked }))} />
            Permite estoque negativo
          </label>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Salvando…' : 'Salvar'}
            </button>
          </div>
        </form>
      )}

      {showEntrada !== null && prod && (
        <form onSubmit={salvarEntrada} className="bg-white border rounded-xl p-5 mb-6 space-y-4">
          <h3 className="font-medium text-gray-700">Entrada de Estoque — <span className="text-blue-600">{prod.codigo}</span></h3>
          {erro && <p className="text-red-600 text-sm bg-red-50 rounded p-2">{erro}</p>}
          <div className="grid grid-cols-3 gap-4">
            <div><label className="text-xs text-gray-500 font-medium">Quantidade *</label>
              <input required type="number" min="1" value={entrada.qtd} onChange={e => setEntrada(f => ({ ...f, qtd: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" /></div>
            <div><label className="text-xs text-gray-500 font-medium">Custo Unit. (R$) *</label>
              <input required type="number" min="0" step="0.01" value={entrada.custo_unitario_centavos}
                onChange={e => setEntrada(f => ({ ...f, custo_unitario_centavos: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" /></div>
            <div><label className="text-xs text-gray-500 font-medium">Data</label>
              <input type="date" value={entrada.data} onChange={e => setEntrada(f => ({ ...f, data: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" /></div>
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowEntrada(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
              {saving ? 'Registrando…' : 'Registrar Entrada'}
            </button>
          </div>
        </form>
      )}

      {loading ? <p className="text-gray-400 text-sm">Carregando…</p> : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Código', 'Descrição', 'Un', 'Estoque', 'Mín', 'CMP', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {produtos.length === 0
                ? <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Nenhum produto</td></tr>
                : produtos.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-blue-700">{p.codigo}</td>
                    <td className="px-4 py-3 text-gray-800">{p.descricao}</td>
                    <td className="px-4 py-3 text-gray-500">{p.unidade}</td>
                    <td className={`px-4 py-3 font-medium ${p.estoque_atual <= p.estoque_minimo ? 'text-red-600' : 'text-gray-800'}`}>{p.estoque_atual}</td>
                    <td className="px-4 py-3 text-gray-500">{p.estoque_minimo}</td>
                    <td className="px-4 py-3 text-gray-700">{formatReal(p.custo_medio_centavos)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${p.ativo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {p.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => { setShowEntrada(p.id); setErro('') }}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium">
                        + Entrada
                      </button>
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
