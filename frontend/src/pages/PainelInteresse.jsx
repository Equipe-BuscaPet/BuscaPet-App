import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { STATUS_INTERESSE } from '../rotulos'
import { ContatoAbrigo } from './MeusInteresses'

const LIMITE = 500

// Bloco da ficha do animal: convite para visitantes, formulário para tutores e,
// depois do interesse, a situação e o contato do abrigo.
export default function PainelInteresse({ animal }) {
  const { usuario, carregando } = useAuth()
  const [interesse, setInteresse] = useState(null)
  const [verificando, setVerificando] = useState(false)
  const [mensagem, setMensagem] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [recemRegistrado, setRecemRegistrado] = useState(false)

  const ehTutor = usuario?.tipo_conta === 'tutor'

  useEffect(() => {
    setInteresse(null)
    setRecemRegistrado(false)
    if (!ehTutor) return
    setVerificando(true)
    api('/interesses/meus')
      .then((lista) => setInteresse(lista.find((i) => i.animal_id === animal.id) || null))
      .catch((err) => setErro(err.message))
      .finally(() => setVerificando(false))
  }, [ehTutor, animal.id])

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      setInteresse(await api(`/animais/${animal.id}/interesses`, { metodo: 'POST', corpo: { mensagem } }))
      setRecemRegistrado(true)
    } catch (err) {
      setErro(err.message)
    } finally {
      setEnviando(false)
    }
  }

  if (carregando || verificando) return null

  if (!usuario) {
    return (
      <section className="cartao" aria-labelledby="titulo-interesse">
        <h2 id="titulo-interesse">Quer adotar {animal.nome}?</h2>
        <p>Entre ou crie uma conta de tutor para demonstrar interesse e receber o contato do abrigo.</p>
        <div className="acoes">
          <Link className="botao" to="/login">Entrar</Link>
          <Link className="botao botao--leve" to="/cadastro">Criar conta</Link>
        </div>
      </section>
    )
  }
  if (!ehTutor) return null

  if (interesse) {
    return (
      <section className="cartao" aria-labelledby="titulo-interesse">
        <h2 id="titulo-interesse">Seu interesse em {animal.nome}</h2>
        {recemRegistrado && <div className="aviso aviso--ok" role="status">Interesse registrado! O abrigo foi avisado. Fale com ele pelo contato abaixo.</div>}
        <p>Situação: <strong>{STATUS_INTERESSE[interesse.status]}</strong></p>
        <div className="detalhe"><ContatoAbrigo interesse={interesse} /></div>
        <p style={{ marginBottom: 0 }}><Link to="/interesses">Ver todos os meus interesses</Link></p>
      </section>
    )
  }

  if (animal.status !== 'disponivel') {
    return (
      <section className="cartao">
        <p style={{ margin: 0 }}>Este animal não está disponível para adoção no momento.</p>
      </section>
    )
  }

  return (
    <section className="cartao" aria-labelledby="titulo-interesse">
      <h2 id="titulo-interesse">Quer adotar {animal.nome}?</h2>
      <p>Conte um pouco sobre você. Depois de registrar o interesse, você recebe o contato do abrigo.</p>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      <form className="formulario" onSubmit={enviar}>
        <div className="campo">
          <label htmlFor="mensagem">Mensagem para o abrigo (opcional)</label>
          <textarea id="mensagem" value={mensagem} maxLength={LIMITE} onChange={(e) => setMensagem(e.target.value)} placeholder="Ex.: moro em casa com quintal e já tive cachorros." />
          <small>{mensagem.length}/{LIMITE}</small>
        </div>
        <button className="botao" disabled={enviando}>{enviando ? 'Enviando…' : 'Tenho interesse'}</button>
      </form>
    </section>
  )
}
