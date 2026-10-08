import { Link, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'
import Admin from './pages/Admin'
import AnimalDetalhe from './pages/AnimalDetalhe'
import Cadastro from './pages/Cadastro'
import Catalogo from './pages/Catalogo'
import Interessados from './pages/Interessados'
import Login from './pages/Login'
import Mapa from './pages/Mapa'
import MeusInteresses from './pages/MeusInteresses'
import PainelAbrigo from './pages/PainelAbrigo'

const ROTULO_TIPO = { tutor: 'Tutor', abrigo: 'Abrigo', apoiador: 'Apoiador', admin: 'Administrador' }

function Cabecalho() {
  const { usuario, sair } = useAuth()
  const navegar = useNavigate()
  return (
    <header className="cabecalho">
      <div className="cabecalho__interno">
        <Link to="/" className="marca">
          Busca<span>Pet</span>
        </Link>
        <nav className="menu" aria-label="Principal">
          <NavLink to="/" end>Animais</NavLink>
          <NavLink to="/mapa">Mapa</NavLink>
          {usuario?.tipo_conta === 'tutor' && <NavLink to="/interesses">Meus interesses</NavLink>}
          {usuario?.tipo_conta === 'abrigo' && <NavLink to="/painel">Meus animais</NavLink>}
          {usuario?.tipo_conta === 'abrigo' && <NavLink to="/interessados">Interessados</NavLink>}
          {usuario?.tipo_conta === 'admin' && <NavLink to="/admin">Validar abrigos</NavLink>}
        </nav>
        <div className="conta">
          {usuario ? (
            <>
              <span className="conta__nome">
                {usuario.nome} <small>{ROTULO_TIPO[usuario.tipo_conta]}</small>
              </span>
              <button className="botao botao--leve" onClick={() => { sair(); navegar('/') }}>Sair</button>
            </>
          ) : (
            <>
              <Link className="botao botao--leve" to="/login">Entrar</Link>
              <Link className="botao" to="/cadastro">Cadastrar</Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

// Só deixa passar quem está logado com um dos tipos de conta permitidos (controle de perfil).
function Protegido({ tipos, children }) {
  const { usuario, carregando } = useAuth()
  if (carregando) return <p className="estado">Carregando…</p>
  if (!usuario) return <Navigate to="/login" replace />
  if (!tipos.includes(usuario.tipo_conta)) {
    return (
      <main className="pagina">
        <div className="aviso aviso--erro" role="alert">
          Seu tipo de conta ({ROTULO_TIPO[usuario.tipo_conta]}) não tem acesso a esta página.
        </div>
      </main>
    )
  }
  return children
}

export default function App() {
  return (
    <>
      <Cabecalho />
      <Routes>
        <Route path="/" element={<Catalogo />} />
        <Route path="/mapa" element={<Mapa />} />
        <Route path="/animais/:id" element={<AnimalDetalhe />} />
        <Route path="/login" element={<Login />} />
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/interesses" element={<Protegido tipos={['tutor']}><MeusInteresses /></Protegido>} />
        <Route path="/interessados" element={<Protegido tipos={['abrigo']}><Interessados /></Protegido>} />
        <Route path="/painel" element={<Protegido tipos={['abrigo']}><PainelAbrigo /></Protegido>} />
        <Route path="/admin" element={<Protegido tipos={['admin']}><Admin /></Protegido>} />
        <Route path="*" element={<main className="pagina"><p className="estado">Página não encontrada.</p></main>} />
      </Routes>
    </>
  )
}
