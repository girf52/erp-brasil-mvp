import { useEffect, useState } from 'react'
import { estoqueApi, type PosicaoEstoque, type MovEstoque, formatReal } from '../../api/vendas'

const tipoLabel: Record<string, string> = {
  entrada: 'Entrada', saida: 'Saída', reserva: 'Reserva', cancelamento_reserva: 'Cancel. Reserva',
}
const tipoColor: Record<string, string> = {
  entrada: 'bg-green-100 text-green-700',
  saida: 'bg-red-100 text-red-700',
  reserva: 'bg-yellow-100 text-yellow-700',
  cancelamento_reserva: 'bg-gray-100 text-gray-600',
}

export default function Estoque() {
  const [posicao, setPosicao] = useState<PosicaoEstoque[]>([])
  const [movs, setMovs] = useState<MovEstoque[]>([])
  const [tab, setTab] = useState<'posicao' | 'movimentacoes'>('posicao')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      estoqueApi.posicao().then(setPosicao),
      estoqueApi.movimentacoes().then(setMovs),
    ]).finally(() => setLoading(false))
  }, [])

  const alertas = posicao.filter(p => p.alerta_minimo).length

  return (
    <div className="p-6 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-800">Estoque</h2>
        <p className="text-sm text-gray-500">
          {posicao.length} produto(s)
          {alertas > 0 && <span className="ml-2 text-red-600 font-medium">⚠ {alertas} abaixo do mínimo</span>}
        </p>
      </div>

      <div className="flex gap-1 mb-5">
        {(['posicao', 'movimentacoes'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm rounded-lg font-medium transition ${tab === t ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>
            {t === 'posicao' ? 'Posição Atual' : 'Movimentações'}
          </button>
        ))}
      </div>

      {loading ? <p className="text-gray-400 text-sm">Carregando…</p> : tab === 'posicao' ? (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Código', 'Descrição', 'Estoque Atual', 'Mínimo', 'CMP', 'Valor Total', 'Situação'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {posicao.length === 0
                ? <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Nenhum produto com estoque</td></tr>
                : posicao.map(p => (
                  <tr key={p.produto_id} className={`hover:bg-gray-50 ${p.alerta_minimo ? 'bg-red-50' : ''}`}>
                    <td className="px-4 py-3 font-mono text-blue-700">{p.codigo}</td>
                    <td className="px-4 py-3 text-gray-800">{p.descricao}</td>
                    <td className={`px-4 py-3 font-semibold ${p.alerta_minimo ? 'text-red-600' : 'text-gray-800'}`}>{p.estoque_atual}</td>
                    <td className="px-4 py-3 text-gray-500">{p.estoque_minimo}</td>
                    <td className="px-4 py-3 text-gray-700">{formatReal(p.custo_medio_centavos)}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{formatReal(p.estoque_atual * p.custo_medio_centavos)}</td>
                    <td className="px-4 py-3">
                      {p.alerta_minimo
                        ? <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">⚠ Baixo</span>
                        : <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">OK</span>}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Data', 'Produto', 'Tipo', 'Qtd', 'Custo Unit.', 'Referência'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {movs.length === 0
                ? <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Nenhuma movimentação</td></tr>
                : movs.map(m => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-600">{m.data}</td>
                    <td className="px-4 py-3 text-gray-800">#{m.produto_id}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${tipoColor[m.tipo] ?? 'bg-gray-100 text-gray-600'}`}>
                        {tipoLabel[m.tipo] ?? m.tipo}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800">{m.qtd}</td>
                    <td className="px-4 py-3 text-gray-700">{formatReal(m.custo_unitario_centavos)}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {m.referencia_tipo ? `${m.referencia_tipo} #${m.referencia_id}` : '—'}
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
