import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import CampoSenha from '../componentes/CampoSenha'

// RF-05: a página do link do e-mail. O link vale 30 minutos e uma vez só.
export default function RedefinirSenha() {
  const [params] = useSearchParams()
  const navegar = useNavigate()
  const token = params.get('token') || ''
  const [senha, setSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    if (senha !== confirmacao) return setErro('As duas senhas não são iguais.')
    setEnviando(true)
    try {
      await api('/auth/redefinir-senha', { metodo: 'POST', corpo: { token, senha_nova: senha } })
      navegar('/login', { state: { aviso: 'Senha alterada. Entre com a nova senha.' } })
    } catch (err) {
      setErro(err.message)
      setEnviando(false)
    }
  }

  if (!token) {
    return (
      <main className="pagina pagina--estreita">
        <div className="aviso aviso--erro" role="alert">Link incompleto. Abra o link do e-mail de novo ou <Link to="/esqueci-senha">peça um novo</Link>.</div>
      </main>
    )
  }

  return (
    <main className="pagina pagina--estreita">
      <div className="cartao">
        <h1>Criar nova senha</h1>
        <p className="subtitulo">Escolha uma senha com pelo menos 8 caracteres.</p>
        {erro && (
          <div className="aviso aviso--erro" role="alert">
            {erro} {erro.includes('Peça um novo') && <Link to="/esqueci-senha">Pedir novo link</Link>}
          </div>
        )}
        <form className="formulario" onSubmit={enviar}>
          <CampoSenha id="senha-nova" rotulo="Nova senha" autoComplete="new-password" minLength={8} required value={senha} onChange={(e) => setSenha(e.target.value)} />
          <CampoSenha id="senha-confirmacao" rotulo="Repita a nova senha" autoComplete="new-password" minLength={8} required value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} />
          <button className="botao" disabled={enviando}>{enviando ? 'Salvando…' : 'Salvar nova senha'}</button>
        </form>
      </div>
    </main>
  )
}
