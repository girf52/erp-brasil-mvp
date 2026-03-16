import { useEffect, useState } from 'react'
import { nfeApi, formatReal, type NFe, type StatusNFe } from '../../api/fiscal'

const statusLabel: Record<StatusNFe, string> = {
  pendente: 'Pendente', autorizada: 'Autorizada', cancelada: 'Cancelada', rejeitada: 'Rejeitada',
}
const statusColor: Record<StatusNFe, string> = {
  pendente: 'bg-yellow-100 text-yellow-700',
  autorizada: 'bg-green-100 text-green-700',
  cancelada: 'bg-red-100 text-red-700',
  rejeitada: 'bg-gray-100 text-gray-600',
}

function formatCNPJ(v: string) {
  return v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')
}

export default function NotasFiscais() {
  const [nfes, setNfes] = useState<NFe[]>([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState<StatusNFe | ''>('')
  const [showForm, setShowForm] = useState(false)
  const [showCancel, setShowCancel] = useState<number | null>(null)
  const [motivo, setMotivo] = useState('')
  const [form, setForm] = useState({ cnpj_emit: '', cnpj_dest: '', valor: '', serie: '1' })
  const [erro, setErro] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const carregar = () => {
    setLoading(true)
    nfeApi.listar(filtro || undefined).then(setNfes).finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [filtro])

  const emitir = async () => {
    setErro('')
    const cnpjE = form.cnpj_emit.replace(/\D/g, '')
    const cnpjD = form.cnpj_dest.replace(/\D/g, '')
    if (cnpjE.length !== 14 || cnpjD.length !== 14) { setErro('CNPJ deve ter 14 dígitos'); return }
    const valorFloat = parseFloat(form.valor.replace(',', '.'))
    if (!valorFloat || valorFloat <= 0) { setErro('Valor inválido'); return }
    const centavos = Math.round(valorFloat * 100)

    setSubmitting(true)
    try {
      await nfeApi.emitir({ cnpj_emit: cnpjE, cnpj_dest: cnpjD, valor_total_centavos: centavos, serie: parseInt(form.serie) || 1 })
      setShowForm(false)
      setForm({ cnpj_emit: '', cnpj_dest: '', valor: '', serie: '1' })
      carregar()
    } catch (e: any) {
      setErro(e.response?.data?.detail || 'Erro ao emitir NF-e')
    } finally { setSubmitting(false) }
  }

  const cancelar = async (id: number) => {
    if (motivo.trim().length < 15) { setErro('Motivo deve ter no mínimo 15 caracteres'); return }
    setSubmitting(true)
    try {
      await nfeApi.cancelar(id, motivo.trim())
      setShowCancel(null)
      setMotivo('')
      carregar()
    } catch (e: any) {
      setErro(e.response?.data?.detail || 'Erro ao cancelar NF-e')
    } finally { setSubmitting(false) }
  }

  const verXml = async (id: number) => {
    try {
      const xml = await nfeApi.xml(id)
      const w = window.open('', '_blank')
      if (w) { w.document.write('<pre>' + xml.replace(/</g, '&lt;') + '</pre>') }
    } catch { alert('XML não disponível') }
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Notas Fiscais Eletrônicas</h2>
          <p className="text-sm text-gray-500">{nfes.length} nota(s)</p>
        </div>
        <button onClick={() => { setShowForm(!showForm); setErro('') }}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium">
          {showForm ? 'Fechar' : 'Emitir NF-e'}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 mb-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">Nova NF-e</h3>
          {erro && <p className="text-sm text-red-600 bg-red-50 p-2 rounded">{erro}</p>}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">CNPJ Emitente</label>
              <input value={form.cnpj_emit} onChange={e => setForm({ ...form, cnpj_emit: e.target.value })}
                placeholder="00.000.000/0001-00" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">CNPJ Destinatário</label>
              <input value={form.cnpj_dest} onChange={e => setForm({ ...form, cnpj_dest: e.target.value })}
                placeholder="00.000.000/0001-00" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Valor Total (R$)</label>
              <input value={form.valor} onChange={e => setForm({ ...form, valor: e.target.value })}
                placeholder="1.500,00" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Série</label>
              <input value={form.serie} onChange={e => setForm({ ...form, serie: e.target.value })}
                type="number" min="1" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <button onClick={emitir} disabled={submitting}
            className="px-5 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium">
            {submitting ? 'Emitindo…' : 'Emitir NF-e'}
          </button>
        </div>
      )}

      <div className="flex gap-2 mb-5">
        {(['', 'autorizada', 'cancelada', 'pendente', 'rejeitada'] as const).map(s => (
          <button key={s} onClick={() => setFiltro(s)}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition ${filtro === s ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100 border'}`}>
            {s === '' ? 'Todas' : statusLabel[s]}
          </button>
        ))}
      </div>

      {loading ? <p className="text-gray-400 text-sm">Carregando…</p> : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Nº', 'Série', 'CNPJ Emit.', 'CNPJ Dest.', 'Valor', 'Status', 'Emissão', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {nfes.length === 0
                ? <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Nenhuma NF-e encontrada</td></tr>
                : nfes.map(nf => (
                  <tr key={nf.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-blue-700">{nf.numero}</td>
                    <td className="px-4 py-3 text-gray-600">{nf.serie}</td>
                    <td className="px-4 py-3 text-gray-700 font-mono text-xs">{formatCNPJ(nf.cnpj_emit)}</td>
                    <td className="px-4 py-3 text-gray-700 font-mono text-xs">{formatCNPJ(nf.cnpj_dest)}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{formatReal(nf.valor_total_centavos)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[nf.status]}`}>
                        {statusLabel[nf.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      {nf.emitido_em ? new Date(nf.emitido_em).toLocaleString('pt-BR') : '—'}
                    </td>
                    <td className="px-4 py-3 space-x-2">
                      <button onClick={() => verXml(nf.id)} className="text-xs text-blue-600 hover:underline">XML</button>
                      {nf.status === 'autorizada' && (
                        <button onClick={() => { setShowCancel(nf.id); setMotivo(''); setErro('') }}
                          className="text-xs text-red-600 hover:underline">Cancelar</button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {showCancel !== null && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Cancelar NF-e #{showCancel}</h3>
            {erro && <p className="text-sm text-red-600 bg-red-50 p-2 rounded mb-3">{erro}</p>}
            <textarea value={motivo} onChange={e => setMotivo(e.target.value)}
              placeholder="Motivo do cancelamento (mín. 15 caracteres)…"
              className="w-full border rounded-lg px-3 py-2 text-sm h-24 resize-none" />
            <p className="text-xs text-gray-400 mb-4">{motivo.trim().length}/15 caracteres mínimos</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCancel(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Voltar
              </button>
              <button onClick={() => cancelar(showCancel)} disabled={submitting}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium">
                {submitting ? 'Cancelando…' : 'Confirmar Cancelamento'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
