import { useEffect, useState } from 'react'
import { funcionariosApi, formatReal, type Funcionario } from '../../api/rh'

const statusColor: Record<string, string> = {
  ativo: 'bg-green-100 text-green-700',
  afastado: 'bg-yellow-100 text-yellow-700',
  demitido: 'bg-red-100 text-red-700',
}

function formatCPF(v: string) {
  return v.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4')
}

export default function Funcionarios() {
  const [funcs, setFuncs] = useState<Funcionario[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ nome: '', cpf: '', cargo: '', salario: '', data_admissao: '', regime: 'clt', dependentes: '0' })
  const [erro, setErro] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const carregar = () => {
    setLoading(true)
    funcionariosApi.listar(false).then(setFuncs).finally(() => setLoading(false))
  }
  useEffect(() => { carregar() }, [])

  const criar = async () => {
    setErro('')
    const cpf = form.cpf.replace(/\D/g, '')
    if (cpf.length !== 11) { setErro('CPF deve ter 11 dígitos'); return }
    const sal = parseFloat(form.salario.replace(',', '.'))
    if (!sal || sal <= 0) { setErro('Salário inválido'); return }
    if (!form.nome.trim() || !form.cargo.trim()) { setErro('Nome e cargo são obrigatórios'); return }
    if (!form.data_admissao) { setErro('Data de admissão obrigatória'); return }

    setSubmitting(true)
    try {
      await funcionariosApi.criar({
        nome: form.nome.trim(), cpf, cargo: form.cargo.trim(),
        salario_base_centavos: Math.round(sal * 100),
        data_admissao: form.data_admissao,
        regime: form.regime,
        dependentes: parseInt(form.dependentes) || 0,
      })
      setShowForm(false)
      setForm({ nome: '', cpf: '', cargo: '', salario: '', data_admissao: '', regime: 'clt', dependentes: '0' })
      carregar()
    } catch (e: any) {
      setErro(e.response?.data?.detail || 'Erro ao cadastrar')
    } finally { setSubmitting(false) }
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Funcionários</h2>
          <p className="text-sm text-gray-500">{funcs.length} cadastrado(s)</p>
        </div>
        <button onClick={() => { setShowForm(!showForm); setErro('') }}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium">
          {showForm ? 'Fechar' : 'Novo Funcionário'}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 mb-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">Cadastrar Funcionário</h3>
          {erro && <p className="text-sm text-red-600 bg-red-50 p-2 rounded">{erro}</p>}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Nome</label>
              <input value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">CPF</label>
              <input value={form.cpf} onChange={e => setForm({ ...form, cpf: e.target.value })}
                placeholder="000.000.000-00" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Cargo</label>
              <input value={form.cargo} onChange={e => setForm({ ...form, cargo: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Salário Base (R$)</label>
              <input value={form.salario} onChange={e => setForm({ ...form, salario: e.target.value })}
                placeholder="3.500,00" className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Data Admissão</label>
              <input type="date" value={form.data_admissao} onChange={e => setForm({ ...form, data_admissao: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Regime</label>
              <select value={form.regime} onChange={e => setForm({ ...form, regime: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="clt">CLT</option>
                <option value="pj">PJ</option>
                <option value="estagio">Estágio</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Dependentes IR</label>
              <input type="number" min="0" value={form.dependentes} onChange={e => setForm({ ...form, dependentes: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <button onClick={criar} disabled={submitting}
            className="px-5 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium">
            {submitting ? 'Salvando…' : 'Cadastrar'}
          </button>
        </div>
      )}

      {loading ? <p className="text-gray-400 text-sm">Carregando…</p> : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Nome', 'CPF', 'Cargo', 'Salário Base', 'Admissão', 'Regime', 'Dep.', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {funcs.length === 0
                ? <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Nenhum funcionário</td></tr>
                : funcs.map(f => (
                  <tr key={f.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-800 font-medium">{f.nome}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{formatCPF(f.cpf)}</td>
                    <td className="px-4 py-3 text-gray-700">{f.cargo}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{formatReal(f.salario_base_centavos)}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{new Date(f.data_admissao + 'T00:00').toLocaleDateString('pt-BR')}</td>
                    <td className="px-4 py-3 text-gray-600 uppercase text-xs">{f.regime}</td>
                    <td className="px-4 py-3 text-gray-600">{f.dependentes}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[f.status] ?? 'bg-gray-100 text-gray-600'}`}>
                        {f.status.charAt(0).toUpperCase() + f.status.slice(1)}
                      </span>
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
