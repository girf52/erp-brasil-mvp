import { useEffect, useState } from 'react'
import { folhaApi, funcionariosApi, formatReal, type Folha, type Funcionario, type Holerite } from '../../api/rh'

export default function FolhaPagamento() {
  const [folhas, setFolhas] = useState<Folha[]>([])
  const [funcsMap, setFuncsMap] = useState<Record<number, Funcionario>>({})
  const [loading, setLoading] = useState(true)
  const [competencia, setCompetencia] = useState(() => {
    const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })
  const [calculando, setCalculando] = useState(false)
  const [holerite, setHolerite] = useState<Holerite | null>(null)
  const [erro, setErro] = useState('')

  const carregar = () => {
    setLoading(true)
    Promise.all([
      folhaApi.listar(competencia).then(setFolhas),
      funcionariosApi.listar(false).then(list => {
        const map: Record<number, Funcionario> = {}
        list.forEach(f => { map[f.id] = f })
        setFuncsMap(map)
      }),
    ]).finally(() => setLoading(false))
  }
  useEffect(() => { carregar() }, [competencia])

  const calcular = async () => {
    setErro('')
    setCalculando(true)
    try {
      await folhaApi.calcular(competencia)
      carregar()
    } catch (e: any) {
      setErro(e.response?.data?.detail || 'Erro ao calcular folha')
    } finally { setCalculando(false) }
  }

  const verHolerite = async (id: number) => {
    try {
      const h = await folhaApi.holerite(id)
      setHolerite(h)
    } catch { setErro('Erro ao carregar holerite') }
  }

  const totalBruto = folhas.reduce((s, f) => s + f.salario_bruto, 0)
  const totalLiquido = folhas.reduce((s, f) => s + f.salario_liquido, 0)
  const totalINSS = folhas.reduce((s, f) => s + f.inss, 0)
  const totalIRRF = folhas.reduce((s, f) => s + f.irrf, 0)
  const totalFGTS = folhas.reduce((s, f) => s + f.fgts, 0)

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Folha de Pagamento</h2>
          <p className="text-sm text-gray-500">{folhas.length} holerite(s) na competência</p>
        </div>
        <div className="flex gap-3 items-center">
          <input type="month" value={competencia} onChange={e => setCompetencia(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm" />
          <button onClick={calcular} disabled={calculando}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
            {calculando ? 'Calculando…' : 'Calcular Folha'}
          </button>
        </div>
      </div>

      {erro && <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg mb-4">{erro}</p>}

      {folhas.length > 0 && (
        <div className="grid grid-cols-5 gap-3 mb-5">
          {[
            ['Bruto Total', totalBruto, 'text-gray-800'],
            ['INSS', totalINSS, 'text-orange-600'],
            ['IRRF', totalIRRF, 'text-red-600'],
            ['FGTS', totalFGTS, 'text-blue-600'],
            ['Líquido Total', totalLiquido, 'text-green-700'],
          ].map(([label, val, color]) => (
            <div key={label as string} className="bg-white border rounded-xl p-4">
              <p className="text-xs text-gray-500">{label as string}</p>
              <p className={`text-lg font-semibold ${color}`}>{formatReal(val as number)}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? <p className="text-gray-400 text-sm">Carregando…</p> : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Funcionário', 'Cargo', 'Bruto', 'INSS', 'IRRF', 'FGTS', 'Outros Desc.', 'Líquido', 'Ações'].map(h => (
                  <th key={h} className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {folhas.length === 0
                ? <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Nenhuma folha calculada para esta competência</td></tr>
                : folhas.map(f => {
                  const func = funcsMap[f.funcionario_id]
                  return (
                    <tr key={f.id} className="hover:bg-gray-50">
                      <td className="px-3 py-3 font-medium text-gray-800">{func?.nome ?? `#${f.funcionario_id}`}</td>
                      <td className="px-3 py-3 text-gray-600">{func?.cargo ?? '—'}</td>
                      <td className="px-3 py-3 text-gray-800">{formatReal(f.salario_bruto)}</td>
                      <td className="px-3 py-3 text-orange-600">{formatReal(f.inss)}</td>
                      <td className="px-3 py-3 text-red-600">{formatReal(f.irrf)}</td>
                      <td className="px-3 py-3 text-blue-600">{formatReal(f.fgts)}</td>
                      <td className="px-3 py-3 text-gray-600">{formatReal(f.outros_descontos)}</td>
                      <td className="px-3 py-3 font-semibold text-green-700">{formatReal(f.salario_liquido)}</td>
                      <td className="px-3 py-3">
                        <button onClick={() => verHolerite(f.id)} className="text-xs text-blue-600 hover:underline">Holerite</button>
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      )}

      {holerite && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-800">Holerite — {holerite.competencia}</h3>
                <p className="text-xs text-gray-500">{holerite.funcionario.nome} — {holerite.funcionario.cargo}</p>
              </div>
              <button onClick={() => setHolerite(null)} className="text-gray-400 hover:text-gray-600 text-lg">x</button>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between border-b pb-2">
                <span className="text-gray-600">Salário Bruto</span>
                <span className="font-medium">{formatReal(holerite.salario_bruto)}</span>
              </div>
              {holerite.eventos.map((e, i) => (
                <div key={i} className="flex justify-between text-xs text-gray-500">
                  <span>{e.tipo} {e.descricao ? `— ${e.descricao}` : ''}</span>
                  <span>{formatReal(e.valor_centavos)}</span>
                </div>
              ))}
              <div className="flex justify-between border-t pt-2 text-orange-600">
                <span>INSS</span><span>- {formatReal(holerite.inss)}</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span>IRRF</span><span>- {formatReal(holerite.irrf)}</span>
              </div>
              <div className="flex justify-between text-blue-600">
                <span>FGTS (informativo)</span><span>{formatReal(holerite.fgts)}</span>
              </div>
              {holerite.outros_descontos > 0 && (
                <div className="flex justify-between text-gray-600">
                  <span>Outros Descontos</span><span>- {formatReal(holerite.outros_descontos)}</span>
                </div>
              )}
              <div className="flex justify-between border-t pt-2 font-semibold text-green-700 text-base">
                <span>Salário Líquido</span><span>{formatReal(holerite.salario_liquido)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
