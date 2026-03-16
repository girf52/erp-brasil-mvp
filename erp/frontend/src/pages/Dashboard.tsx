import { useNavigate } from 'react-router-dom'

const modules = [
  { name: 'Financeiro', icon: '💰', desc: 'Plano de contas, lançamentos, DRE', sprint: 1 },
  { name: 'Vendas', icon: '🛒', desc: 'Clientes, pedidos, estoque', sprint: 2 },
  { name: 'Fiscal', icon: '🧾', desc: 'NF-e, cancelamento, SEFAZ mock', sprint: 3 },
  { name: 'RH / Folha', icon: '👥', desc: 'Funcionários, INSS, IRRF, holerite', sprint: 4 },
]

export default function Dashboard() {
  const navigate = useNavigate()

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">ERP Brasil</h1>
          <p className="text-xs text-gray-400">Sprint 0 — Fundação concluída</p>
        </div>
        <button onClick={logout} className="text-sm text-red-500 hover:text-red-700 font-medium">
          Sair
        </button>
      </header>
      <main className="p-8">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Módulos</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {modules.map(mod => (
            <div key={mod.name} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition">
              <div className="text-3xl mb-3">{mod.icon}</div>
              <h3 className="text-base font-semibold text-gray-700">{mod.name}</h3>
              <p className="text-xs text-gray-400 mt-1">{mod.desc}</p>
              <span className="inline-block mt-3 text-xs bg-blue-50 text-blue-500 px-2 py-0.5 rounded-full">
                Sprint {mod.sprint}
              </span>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
