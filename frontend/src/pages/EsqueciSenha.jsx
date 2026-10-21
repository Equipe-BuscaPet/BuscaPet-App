import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

// RF-05: pedir o link para criar uma nova senha. A resposta é a mesma exista ou não a conta.
export default function EsqueciSenha() {
  const [email, setEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [ok, setOk] = useState('')
  const [erro, setErro] = useState('')

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      setOk((await api('/auth/esqueci-senha', { metodo: 'POST', corpo: { email: email.trim() } })).mensagem)
    } catch (err) {
      setErro(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="pagina pagina--estreita">
      <div className="cartao">
        <h1>Esqueci minha senha</h1>
        <p className="subtitulo">Informe o e-mail da sua conta. Vamos enviar um link para você criar uma nova senha.</p>
        {ok ? (
          <>
            <div className="aviso aviso--ok" role="status">{ok}</div>
            <p className="subtitulo" style={{ margin: 0 }}>Não chegou? Confira a caixa de spam ou <button type="button" className="botao-link" onClick={() => setOk('')}>peça de novo</button>.</p>
          </>
        ) : (
          <form className="formulario" onSubmit={enviar}>
            {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
            <div className="campo">
              <label htmlFor="email">E-mail</label>
              <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <button className="botao" disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar link'}</button>
          </form>
        )}
        <p className="subtitulo" style={{ marginTop: '1rem', marginBottom: 0 }}><Link to="/login">← Voltar para o login</Link></p>
      </div>
    </main>
  )
}
