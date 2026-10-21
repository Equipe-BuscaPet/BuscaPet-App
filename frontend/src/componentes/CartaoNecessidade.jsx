import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { COR_URGENCIA, URGENCIAS } from '../rotulos'

// Uma necessidade do mural (RF-30/RF-35), usada no "Quem apoia", no perfil do abrigo e na área do abrigo.
// Apoiador e tutor doam ali mesmo; o visitante é convidado a entrar ou criar a conta.
export default function CartaoNecessidade({ necessidade: n, mostrarAbrigo = true, acoes, aoDoar }) {
  const { usuario } = useAuth()
  const { pathname } = useLocation()
  const [quantidade, setQuantidade] = useState(1)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  const falta = Math.max(n.quantidade - n.quantidade_recebida, 0)
  const pct = Math.min(100, Math.round((n.quantidade_recebida / n.quantidade) * 100))
  const podeDoar = n.status === 'aberta' && !acoes

  async function doar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      await api('/doacoes', { metodo: 'POST', corpo: { necessidade_id: n.id, quantidade: Number(quantidade) } })
      setOk(`Doação registrada! O ${n.nome_abrigo} vai confirmar quando receber. Acompanhe em Minhas doações.`)
      aoDoar?.()
    } catch (err) {
      setErro(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <article className="cartao necessidade" aria-label={n.item}>
      <div className="necessidade__topo">
        <h3>{n.item}</h3>
        {n.status === 'aberta'
          ? <span className={`etiqueta ${COR_URGENCIA[n.urgencia]}`}>{URGENCIAS[n.urgencia]}</span>
          : <span className="etiqueta etiqueta--ok">Atendida</span>}
      </div>
      {mostrarAbrigo && <p className="necessidade__abrigo"><Link to={`/abrigos/${n.abrigo_id}`}>{n.nome_abrigo}</Link>{n.distancia_km != null && ` · a ${n.distancia_km} km`}</p>}
      <div className="progresso" role="progressbar" aria-valuemin={0} aria-valuemax={n.quantidade} aria-valuenow={n.quantidade_recebida} aria-label="Já recebido">
        <div className="progresso__barra" style={{ width: `${pct}%` }} />
      </div>
      <p className="progresso__texto">{n.quantidade_recebida} de {n.quantidade} recebidos{falta > 0 && n.status === 'aberta' ? ` · faltam ${falta}` : ''}</p>

      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {acoes}
      {podeDoar && !ok && ['apoiador', 'tutor'].includes(usuario?.tipo_conta) && (
        <form className="doar" onSubmit={doar}>
          <div className="campo">
            <label htmlFor={`qtd-${n.id}`}>Quantidade</label>
            <input id={`qtd-${n.id}`} type="number" min={1} max={10000} value={quantidade} onChange={(e) => setQuantidade(e.target.value)} required />
          </div>
          <button className="botao" disabled={enviando}>{enviando ? 'Registrando…' : 'Quero doar'}</button>
        </form>
      )}
      {podeDoar && !usuario && (
        <p className="progresso__texto">
          <Link to={`/login?voltar=${encodeURIComponent(pathname)}`}>Entre</Link> ou <Link to="/cadastro">crie sua conta</Link> para doar.
        </p>
      )}
    </article>
  )
}
