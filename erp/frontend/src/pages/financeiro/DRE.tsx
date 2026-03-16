import { useState } from 'react'
import { financeiroApi, DRE as DREType, formatReal } from '../../api/financeiro'

export default function DRE() {
  const today = new Date().toISOString().slice(0, 10)
  const firstDay = today.slice(0, 7) + '-01'
  const [inicio, setInicio] = useState(firstDay)
  const [fim, setFim] = useState(today)
  const [dre, setDre] = useState<DREType | null>(null)
  const [loading, setLoading] = useState(false)

  async function buscar() {
    setLoading(true)
    try { setDre(await financeiroApi.dre(inicio, fim)) }
    finally { setLoading(false) }
  }

  const corResultado = dre
    ? dre.resultado_liquido_centavos >= 0 ? 'text-green-600' : 'text-red-600'
    : ''

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-bold text-gray-800">DRE — Demonstração do Resultado</h2>

      <div className="bg-white rounded-xl shadow-sm border p-4 flex gap-4 items-end">
        <div>
          <label className="text-sm font-medium text-gray-600">De</label>
          <input type="date" value={inicio} onChange={e => setInicio(e.target.value)}
            className="block border rounded-lg px-3 py-1.5 mt-1 text-sm" />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-600">Até</label>
          <input type="date" value={fim} onChange={e => setFim(e.target.value)}
            className="block border rounded-lg px-3 py-1.5 mt-1 text-sm" />
        </div>
        <button onClick={buscar} disabled={loading}
          className="bg-blue-600 text-white px-5 py-1.5 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50">
          {loading ? 'Calculando...' : 'Gerar DRE'}
        </button>
      </div>

      {dre && (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="bg-gray-50 border-b px-4 py-3">
            <p className="text-sm font-semibold text-gray-700">
              Período: {dre.periodo.inicio} a {dre.periodo.fim}
            </p>
          </div>
          <table className="w-full text-sm">
            <tbody>
              {dre.linhas.map(linha => (
                <tr key={linha.grupo} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-700">{linha.grupo}</td>
                  <td className="px-4 py-3 text-right font-mono">{formatReal(linha.valor_centavos)}</td>
                </tr>
              ))}
              <tr className="bg-gray-50 border-t-2 border-gray-300">
                <td className={`px-4 py-4 font-bold ${corResultado}`}>Resultado Líquido</td>
                <td className={`px-4 py-4 text-right font-bold font-mono text-base ${corResultado}`}>
                  {formatReal(dre.resultado_liquido_centavos)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
