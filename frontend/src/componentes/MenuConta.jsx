import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

// Menu "hambúrguer" da conta (☰), no canto direito do cabeçalho. Junta o que é da pessoa e do seu perfil,
// para o menu principal ficar só com o que é de todos (Mapa, Animais, Perdidos e achados).
export const ROTULO_TIPO = { tutor: 'Tutor', abrigo: 'Abrigo', apoiador: 'Apoiador', admin: 'Administrador' }

function itensDoPerfil(usuario) {
  return {
    tutor: [['/interesses', '❤️', 'Meus interesses de adoção']],
    abrigo: [
      ['/painel', '🐾', 'Meus animais'], ['/interessados', '📋', 'Interessados'],
      ['/doacoes', '📦', 'Necessidades e doações'], [`/abrigos/${usuario.id}`, '🏠', 'Perfil público do abrigo'],
    ],
    apoiador: [['/minhas-doacoes', '📦', 'Minhas doações'], [`/apoiadores/${usuario.id}`, '🏆', 'Meu perfil público']],
    admin: [['/admin', '✅', 'Validar abrigos']],
  }[usuario.tipo_conta]
}

export default function MenuConta() {
  const { usuario, sair } = useAuth()
  const navegar = useNavigate()
  const { pathname } = useLocation()
  const [aberto, setAberto] = useState(false)
  const caixa = useRef(null)

  useEffect(() => { setAberto(false) }, [pathname]) // fecha ao navegar

  useEffect(() => {
    if (!aberto) return
    const fora = (e) => { if (!caixa.current?.contains(e.target)) setAberto(false) }
    const esc = (e) => { if (e.key === 'Escape') setAberto(false) }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  const itens = [
    ['/conta', '👤', 'Minha conta'],
    ...itensDoPerfil(usuario),
    ...(usuario.tipo_conta !== 'admin' ? [['/meus-registros', '📍', 'Meus registros de perdidos e avistados']] : []),
    ['/notificacoes', '🔔', 'Notificações'],
  ]

  return (
    <div className="menu-conta" ref={caixa}>
      <button type="button" className="menu-conta__botao" aria-expanded={aberto} aria-label="Menu da conta" onClick={() => setAberto((v) => !v)}>
        <span className="menu-conta__inicial" aria-hidden="true">{usuario.nome.trim().charAt(0).toUpperCase()}</span>
        <span className="menu-conta__hamburguer" aria-hidden="true">☰</span>
      </button>
      {aberto && (
        <nav className="menu-conta__painel" aria-label="Menu da conta">
          <div className="menu-conta__quem">
            <strong>{usuario.nome}</strong>
            <small>{ROTULO_TIPO[usuario.tipo_conta]} · {usuario.email}</small>
          </div>
          <ul>
            {itens.map(([para, icone, rotulo]) => (
              <li key={para}>
                <NavLink to={para} className="menu-conta__item"><span aria-hidden="true">{icone}</span> {rotulo}</NavLink>
              </li>
            ))}
          </ul>
          <button type="button" className="menu-conta__item menu-conta__sair" onClick={() => { sair(); navegar('/') }}>
            <span aria-hidden="true">🚪</span> Sair
          </button>
        </nav>
      )}
    </div>
  )
}
