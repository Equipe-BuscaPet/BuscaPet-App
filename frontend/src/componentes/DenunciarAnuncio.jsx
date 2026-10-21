import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

// Denúncia de anúncio (RF-41): link discreto na ficha que abre um formulário curto.
// Não aparece para o próprio abrigo nem para a administração (que modera direto).
export default function DenunciarAnuncio({ animal }) {
  const { usuario } = useAuth()
  const { pathname } = useLocation()
  const [aberto, setAberto] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  if (usuario && (usuario.id === animal.abrigo_id || usuario.tipo_conta === 'admin')) return null

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      const r = await api(`/animais/${animal.id}/denuncias`, { metodo: 'POST', corpo: { motivo: motivo.trim() } })
      setOk(r.mensagem)
      setAberto(false)
    } catch (err) {
      setErro(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="denuncia" aria-label="Denunciar anúncio">
      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {!aberto && !ok && (
        <button type="button" className="botao-link" onClick={() => setAberto(true)}>⚑ Denunciar este anúncio</button>
      )}
      {aberto && !usuario && (
        <p className="legenda"><Link to={`/login?voltar=${encodeURIComponent(pathname)}`}>Entre</Link> para denunciar este anúncio.</p>
      )}
      {aberto && usuario && (
        <form className="formulario cartao" onSubmit={enviar}>
          <div className="campo">
            <label htmlFor="motivo-denuncia">O que há de errado neste anúncio?</label>
            <textarea id="motivo-denuncia" rows={3} minLength={10} maxLength={1000} required value={motivo}
              placeholder="Ex.: estão cobrando pela adoção; o animal não existe; fotos de outro anúncio."
              onChange={(e) => setMotivo(e.target.value)} />
            <small>A administração analisa e pode remover o anúncio. Quem denunciou não é identificado para o abrigo.</small>
          </div>
          {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
          <div className="acoes">
            <button className="botao botao--perigo" disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar denúncia'}</button>
            <button type="button" className="botao botao--leve" onClick={() => setAberto(false)}>Cancelar</button>
          </div>
        </form>
      )}
    </section>
  )
}
