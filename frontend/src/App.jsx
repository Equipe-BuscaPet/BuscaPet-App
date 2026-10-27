import { useEffect } from 'react'
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import AssistenteRegistro from './componentes/AssistenteRegistro'
import BotaoInstalar from './componentes/BotaoInstalar'
import MenuConta, { ROTULO_TIPO } from './componentes/MenuConta'
import Sino from './componentes/Sino'
import Admin from './pages/Admin'
import AnimalDetalhe from './pages/AnimalDetalhe'
import Cadastro from './pages/Cadastro'
import Catalogo from './pages/Catalogo'
import EsqueciSenha from './pages/EsqueciSenha'
import DoacoesAbrigo from './pages/DoacoesAbrigo'
import Interessados from './pages/Interessados'
import Login from './pages/Login'
import Mapa from './pages/Mapa'
import MeusInteresses from './pages/MeusInteresses'
import MeusRegistros from './pages/MeusRegistros'
import MinhasDoacoes from './pages/MinhasDoacoes'
import MinhaConta from './pages/MinhaConta'
import Notificacoes from './pages/Notificacoes'
import PainelAbrigo from './pages/PainelAbrigo'
import PerfilAbrigo from './pages/PerfilAbrigo'
import PerfilApoiador from './pages/PerfilApoiador'
import QuemApoia from './pages/QuemApoia'
import RedefinirSenha from './pages/RedefinirSenha'
import Reencontro from './pages/Reencontro'
import RelatoriosAbrigo from './pages/RelatoriosAbrigo'
import RegistroDetalhe from './pages/RegistroDetalhe'

// Título da aba do navegador por página (usabilidade: várias abas abertas e histórico do navegador legíveis).
const TITULOS = [
  ['/mapa', 'Mapa'], ['/reencontro', 'Perdidos e achados'], ['/perdi', 'Perdi meu animal'], ['/encontrei', 'Encontrei um animal'],
  ['/quem-apoia', 'Quem apoia'], ['/abrigos/', 'Abrigo'], ['/apoiadores/', 'Apoiador'], ['/animais/', 'Animal para adoção'],
  ['/login', 'Entrar'], ['/cadastro', 'Criar conta'], ['/esqueci-senha', 'Esqueci minha senha'], ['/redefinir-senha', 'Nova senha'],
  ['/conta', 'Minha conta'], ['/notificacoes', 'Notificações'], ['/meus-registros', 'Meus registros'], ['/interesses', 'Meus interesses'],
  ['/interessados', 'Interessados'], ['/painel', 'Meus animais'], ['/doacoes', 'Necessidades e doações'],
  ['/minhas-doacoes', 'Minhas doações'], ['/relatorios', 'Relatórios'], ['/admin', 'Administração'],
]

function TituloDaPagina() {
  const { pathname } = useLocation()
  useEffect(() => {
    const achado = TITULOS.find(([prefixo]) => pathname === prefixo || pathname.startsWith(prefixo.endsWith('/') ? prefixo : `${prefixo}/`))
    document.title = achado ? `${achado[1]} · BuscaPet` : 'BuscaPet · adoção, reencontro e doações'
  }, [pathname])
  return null
}

// Menu principal só com o que é de todos; o que é da conta fica no menu ☰ (componentes/MenuConta.jsx).
function Cabecalho() {
  const { usuario } = useAuth()
  return (
    <header className="cabecalho">
      <div className="cabecalho__interno">
        <Link to="/" className="marca">
          Busca<span>Pet</span>
        </Link>
        <nav className="menu" aria-label="Principal">
          <NavLink to="/mapa">Mapa</NavLink>
          <NavLink to="/" end>Animais</NavLink>
          <NavLink to="/reencontro">Perdidos e achados</NavLink>
          <NavLink to="/quem-apoia">Quem apoia</NavLink>
        </nav>
        <div className="conta">
          {usuario ? (
            <>
              <Sino />
              <MenuConta />
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

function Rodape() {
  return (
    <footer className="rodape">
      <div className="rodape__interno">
        <BotaoInstalar />
        <p>BuscaPet · adoção, reencontro e doações · projeto acadêmico UNINASSAU</p>
      </div>
    </footer>
  )
}

// Só deixa passar quem está logado com um dos tipos de conta permitidos (controle de perfil).
function Protegido({ tipos, children }) {
  const { usuario, carregando } = useAuth()
  const { pathname } = useLocation()
  if (carregando) return <p className="estado">Carregando…</p>
  if (!usuario) return <Navigate to={`/login?voltar=${encodeURIComponent(pathname)}`} replace />
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
      <a href="#conteudo" className="pular-conteudo">Pular para o conteúdo</a>
      <TituloDaPagina />
      <Cabecalho />
      <div id="conteudo" tabIndex={-1}>
      <Routes>
        <Route path="/" element={<Catalogo />} />
        <Route path="/mapa" element={<Mapa />} />
        <Route path="/animais/:id" element={<AnimalDetalhe />} />
        <Route path="/reencontro" element={<Reencontro />} />
        <Route path="/quem-apoia" element={<QuemApoia />} />
        <Route path="/abrigos/:id" element={<PerfilAbrigo />} />
        <Route path="/apoiadores/:id" element={<PerfilApoiador />} />
        <Route path="/doacoes" element={<Protegido tipos={['abrigo']}><DoacoesAbrigo /></Protegido>} />
        <Route path="/relatorios" element={<Protegido tipos={['abrigo']}><RelatoriosAbrigo /></Protegido>} />
        <Route path="/minhas-doacoes" element={<Protegido tipos={['apoiador', 'tutor']}><MinhasDoacoes /></Protegido>} />
        <Route path="/reencontro/perdidos/:id" element={<RegistroDetalhe key="perdido" tipo="perdido" />} />
        <Route path="/reencontro/avistamentos/:id" element={<RegistroDetalhe key="avistamento" tipo="avistamento" />} />
        <Route path="/perdi" element={<AssistenteRegistro key="perdido" tipo="perdido" />} />
        <Route path="/encontrei" element={<AssistenteRegistro key="avistamento" tipo="avistamento" />} />
        <Route path="/login" element={<Login />} />
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/esqueci-senha" element={<EsqueciSenha />} />
        <Route path="/redefinir-senha" element={<RedefinirSenha />} />
        <Route path="/conta" element={<Protegido tipos={['tutor', 'abrigo', 'apoiador', 'admin']}><MinhaConta /></Protegido>} />
        <Route path="/notificacoes" element={<Protegido tipos={['tutor', 'abrigo', 'apoiador', 'admin']}><Notificacoes /></Protegido>} />
        <Route path="/meus-registros" element={<Protegido tipos={['tutor', 'abrigo', 'apoiador']}><MeusRegistros /></Protegido>} />
        <Route path="/interesses" element={<Protegido tipos={['tutor']}><MeusInteresses /></Protegido>} />
        <Route path="/interessados" element={<Protegido tipos={['abrigo']}><Interessados /></Protegido>} />
        <Route path="/painel" element={<Protegido tipos={['abrigo']}><PainelAbrigo /></Protegido>} />
        <Route path="/admin" element={<Protegido tipos={['admin']}><Admin /></Protegido>} />
        <Route path="*" element={<main className="pagina"><p className="estado">Página não encontrada.</p></main>} />
      </Routes>
      </div>
      <Rodape />
    </>
  )
}
