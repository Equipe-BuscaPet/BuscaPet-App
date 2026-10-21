import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { destinoInterno, destinoPorTipo, useAuth } from '../auth'
import CampoSenha from '../componentes/CampoSenha'

export default function Login() {
  const { entrar } = useAuth()
  const navegar = useNavigate()
  const [params] = useSearchParams()
  const { state } = useLocation()
  // Volta para a página que pediu login. Só caminhos internos ("/..."), para o link não levar a outro site.
  const destinoSeguro = destinoInterno(params.get('voltar'))
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      const usuario = await entrar(email, senha)
      navegar(destinoSeguro || destinoPorTipo(usuario.tipo_conta))
    } catch (err) {
      setErro(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="pagina pagina--estreita">
      <div className="cartao">
        <h1>Entrar</h1>
        <p className="subtitulo">Um só login para tutores, abrigos, apoiadores e administradores.</p>
        {state?.aviso && !erro && <div className="aviso aviso--ok" role="status">{state.aviso}</div>}
        {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
        <form className="formulario" onSubmit={enviar}>
          <div className="campo">
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <CampoSenha id="senha" rotulo="Senha" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
          <p className="legenda" style={{ margin: 0 }}><Link to="/esqueci-senha">Esqueci minha senha</Link></p>
          <button className="botao" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
        </form>
        <p className="subtitulo" style={{ marginTop: '1rem', marginBottom: 0 }}>
          Ainda não tem conta? <Link to="/cadastro">Cadastre-se</Link>
        </p>
      </div>
    </main>
  )
}
