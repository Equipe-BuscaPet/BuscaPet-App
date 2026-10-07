import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { destinoPorTipo, useAuth } from '../auth'

export default function Login() {
  const { entrar } = useAuth()
  const navegar = useNavigate()
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
      navegar(destinoPorTipo(usuario.tipo_conta))
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
        {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
        <form className="formulario" onSubmit={enviar}>
          <div className="campo">
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="senha">Senha</label>
            <input id="senha" type="password" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
          </div>
          <button className="botao" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
        </form>
        <p className="subtitulo" style={{ marginTop: '1rem', marginBottom: 0 }}>
          Ainda não tem conta? <Link to="/cadastro">Cadastre-se</Link>
        </p>
      </div>
    </main>
  )
}
