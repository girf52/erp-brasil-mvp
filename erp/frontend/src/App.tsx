import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import PlanoContas from './pages/financeiro/PlanoContas'
import DRE from './pages/financeiro/DRE'
import Clientes from './pages/vendas/Clientes'
import Produtos from './pages/vendas/Produtos'
import Pedidos from './pages/vendas/Pedidos'
import Estoque from './pages/vendas/Estoque'
import NotasFiscais from './pages/fiscal/NotasFiscais'
import Funcionarios from './pages/rh/Funcionarios'
import FolhaPagamento from './pages/rh/FolhaPagamento'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  return localStorage.getItem('access_token') ? <>{children}</> : <Navigate to="/login" replace />
}

function Layout({ children }: { children: React.ReactNode }) {
  function logout() { localStorage.clear(); window.location.href = '/login' }
  const nav = 'block px-3 py-2 rounded-lg text-sm font-medium transition'
  const active = 'bg-blue-50 text-blue-600'
  const inactive = 'text-gray-600 hover:bg-gray-100'
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-white border-r flex flex-col">
        <div className="px-4 py-5 border-b">
          <h1 className="font-bold text-gray-800">ERP Brasil</h1>
          <p className="text-xs text-gray-400">MVP v0.1</p>
        </div>
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          <p className="text-xs font-semibold text-gray-400 px-3 pt-2 pb-1 uppercase">Financeiro</p>
          <NavLink to="/financeiro/plano-contas" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Plano de Contas</NavLink>
          <NavLink to="/financeiro/dre" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>DRE</NavLink>
          <p className="text-xs font-semibold text-gray-400 px-3 pt-4 pb-1 uppercase">Vendas</p>
          <NavLink to="/vendas/clientes" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Clientes</NavLink>
          <NavLink to="/vendas/produtos" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Produtos</NavLink>
          <NavLink to="/vendas/pedidos" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Pedidos</NavLink>
          <p className="text-xs font-semibold text-gray-400 px-3 pt-4 pb-1 uppercase">Estoque</p>
          <NavLink to="/estoque" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Posição / Movimentos</NavLink>
          <p className="text-xs font-semibold text-gray-400 px-3 pt-4 pb-1 uppercase">Fiscal</p>
          <NavLink to="/fiscal/nfe" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Notas Fiscais</NavLink>
          <p className="text-xs font-semibold text-gray-400 px-3 pt-4 pb-1 uppercase">RH / Folha</p>
          <NavLink to="/rh/funcionarios" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Funcionários</NavLink>
          <NavLink to="/rh/folha" className={({ isActive }) => `${nav} ${isActive ? active : inactive}`}>Folha de Pagamento</NavLink>
        </nav>
        <button onClick={logout} className="m-3 text-sm text-red-500 hover:text-red-700 text-left px-3 py-2">Sair</button>
      </aside>
      <main className="flex-1 bg-gray-50 overflow-auto">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
      <Route path="/financeiro/plano-contas" element={<PrivateRoute><Layout><PlanoContas /></Layout></PrivateRoute>} />
      <Route path="/financeiro/dre" element={<PrivateRoute><Layout><DRE /></Layout></PrivateRoute>} />
      <Route path="/vendas/clientes" element={<PrivateRoute><Layout><Clientes /></Layout></PrivateRoute>} />
      <Route path="/vendas/produtos" element={<PrivateRoute><Layout><Produtos /></Layout></PrivateRoute>} />
      <Route path="/vendas/pedidos" element={<PrivateRoute><Layout><Pedidos /></Layout></PrivateRoute>} />
      <Route path="/estoque" element={<PrivateRoute><Layout><Estoque /></Layout></PrivateRoute>} />
      <Route path="/fiscal/nfe" element={<PrivateRoute><Layout><NotasFiscais /></Layout></PrivateRoute>} />
      <Route path="/rh/funcionarios" element={<PrivateRoute><Layout><Funcionarios /></Layout></PrivateRoute>} />
      <Route path="/rh/folha" element={<PrivateRoute><Layout><FolhaPagamento /></Layout></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
