import { useEffect, useState } from 'react'
import { pedidosApi, clientesApi, produtosApi, type Pedido, type Cliente, type Produto, type StatusPedido, formatReal } from '../../api/vendas'

const statusColor: Record<StatusPedido, string> = {
  rascunho: 'bg-gray-100 text-gray-600',
  confirmado: 'bg-blue-100 text-blue-700',
  faturado: 'bg-green-100 text-green-700',
  cancelado: 'bg-red-100 text-red-700',
}

interface ItemForm { produto_id: string; qtd: string; preco_unitario_centavos: string }

export default function Pedidos() {
  const [pedidos, setPedidos] = useState<Pedido[]>([])
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [erro, setErro] = useState('')
  const [form, setForm] = useState({ cliente_id: '', data: new Date().toISOString().slice(0, 10), observacao: '' })
  const [itens, setItens] = useState<ItemForm[]>([{ produto_id: '', qtd: '1', preco_unitario_centavos: '' }])

  const load = () => Promise.all([
    pedidosApi.listar().then(setPedidos),
    clientesApi.listar().then(setClientes),
    produtosApi.listar().then(setProdutos),
  ]).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  function addItem() { setItens(prev => [...prev, { produto_id: '', qtd: '1', preco_unitario_centavos: '' }]) }
  function removeItem(i: number) { setItens(prev => prev.filter((_, idx) => idx !== i)) }
  function updateItem(i: number, field: keyof ItemForm, val: string) {
    setItens(prev => prev.map((it, idx) => idx === i ? { ...it, [field]: val } : it))
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setErro('')
    try {
      await pedidosApi.criar({
        cliente_id: Number(form.cliente_id),
        data: form.data,
        observacao: form.observacao || undefined,
        itens: itens.map(it => ({
          produto_id: Number(it.produto_id),
          qtd: Number(it.qtd),
          preco_unitario_centavos: Math.round(Number(it.preco_unitario_centavos) * 100),
        })),
      })
      setShowForm(false)
      setForm({ cliente_id: '', data: new Date().toISOString().slice(0, 10), observacao: '' })
      setItens([{ produto_id: '', qtd: '1', preco_unitario_centavos: '' }])
      load()
    } catch (err: any) { setErro(err?.response?.data?.detail ?? 'Erro ao criar pedido') }
    finally { setSaving(false) }
  }

  async function faturar(id: number) {
    if (!confirm('Faturar este pedido? Esta ação baixa o estoque definitivamente.')) return
    try {
      await pedidosApi.faturar(id); load()
    } catch (err: any) { alert(err?.response?.data?.detail ?? 'Erro ao faturar') }
  }

  const clienteNome = (id: number) => clientes.find(c => c.id === id)?.nome ?? `#${id}`

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Pedidos de Venda</h2>
          <p className="text-sm text-gray-500">{pedidos.length} pedido(s)</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + Novo Pedido
        </button>
      </div>

      {showForm && (
        <form onSubmit={salvar} className="bg-white border rounded-xl p-5 mb-6 space-y-4">
          <h3 className="font-medium text-gray-700">Novo Pedido</h3>
          {erro && <p className="text-red-600 text-sm bg-red-50 rounded p-2">{erro}</p>}
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="text-xs text-gray-500 font-medium">Cliente *</label>
              <select required value={form.cliente_id} onChange={e => setForm(f => ({ ...f, cliente_id: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1">
                <option value="">Selecione…</option>
                {clientes.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Data</label>
              <input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-gray-500 font-medium">Itens</label>
              <button type="button" onClick={addItem} className="text-xs text-blue-600 hover:text-blue-800 font-medium">+ Adicionar item</button>
            </div>
            <div className="space-y-2">
              {itens.map((it, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-5">
                    <select required value={it.produto_id} onChange={e => updateItem(i, 'produto_id', e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm">
                      <option value="">Produto…</option>
                      {produtos.map(p => <option key={p.id} value={p.id}>{p.codigo} — {p.descricao}</option>)}
                    </select>
                  </div>
                  <div className="col-span-2">
                    <input required type="number" min="1" value={it.qtd} onChange={e => updateItem(i, 'qtd', e.target.value)}
                      placeholder="Qtd" className="w-full border rounded-lg px-3 py-2 text-sm" />
                  </div>
                  <div className="col-span-4">
                    <input required type="number" min="0.01" step="0.01" value={it.preco_unitario_centavos}
                      onChange={e => updateItem(i, 'preco_unitario_centavos', e.target.value)}
                      placeholder="Preço unit. (R$)" className="w-full border rounded-lg px-3 py-2 text-sm" />
                  </div>
                  <div className="col-span-1 text-center">
                    {itens.length > 1 && (
                      <button type="button" onClick={() => removeItem(i)} className="text-red-400 hover:text-red-600 text-lg leading-none">×</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 font-medium">Observação</label>
            <input value={form.observacao} onChange={e => setForm(f => ({ ...f, observacao: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="Opcional" />
          </div>

          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Criando…' : 'Criar Pedido'}
            </button>
          </div>
        </form>
      )}

      {loading ? <p className="text-gray-400 text-sm">Carregando…</p> : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['#', 'Cliente', 'Data', 'Itens', 'Total', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {pedidos.length === 0
                ? <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Nenhum pedido</td></tr>
                : pedidos.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 font-mono">#{p.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{clienteNome(p.cliente_id)}</td>
                    <td className="px-4 py-3 text-gray-600">{p.data}</td>
                    <td className="px-4 py-3 text-gray-500">{p.itens.length} item(s)</td>
                    <td className="px-4 py-3 font-medium">{formatReal(p.total_centavos)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${statusColor[p.status]}`}>{p.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      {p.status === 'confirmado' && (
                        <button onClick={() => faturar(p.id)} className="text-xs text-green-600 hover:text-green-800 font-medium">
                          Faturar
                        </button>
                      )}
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
