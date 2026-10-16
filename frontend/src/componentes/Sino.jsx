import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { textoHaQuanto } from '../rotulos'

// Sino de notificações do cabeçalho (RF-36). Consulta só a contagem (leve) a cada minuto, ao trocar de página
// e quando a aba do navegador volta a ficar visível; a lista é buscada quando o sino é aberto.
// Outras telas avisam mudanças com o evento 'buscapet:notificacoes' (ex.: marcar como lida na página).
const INTERVALO_MS = 60_000
const NA_LISTA = 6

export function avisarMudancaNotificacoes() {
  window.dispatchEvent(new Event('buscapet:notificacoes'))
}

export default function Sino() {
  const [naoLidas, setNaoLidas] = useState(0)
  const [aberto, setAberto] = useState(false)
  const [lista, setLista] = useState(null)
  const caixa = useRef(null)
  const navegar = useNavigate()
  const { pathname } = useLocation()

  const contar = useCallback(() => {
    api('/notificacoes/contagem').then((r) => setNaoLidas(r.nao_lidas)).catch(() => {})
  }, [])

  useEffect(() => { contar() }, [contar, pathname])
  useEffect(() => {
    const relogio = setInterval(() => { if (document.visibilityState === 'visible') contar() }, INTERVALO_MS)
    const aoVoltar = () => { if (document.visibilityState === 'visible') contar() }
    document.addEventListener('visibilitychange', aoVoltar)
    window.addEventListener('buscapet:notificacoes', contar)
    return () => {
      clearInterval(relogio)
      document.removeEventListener('visibilitychange', aoVoltar)
      window.removeEventListener('buscapet:notificacoes', contar)
    }
  }, [contar])

  // Fecha com Esc ou clique fora.
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

  function alternar() {
    const abrir = !aberto
    setAberto(abrir)
    if (abrir) {
      setLista(null)
      api(`/notificacoes?limite=${NA_LISTA}`).then(setLista).catch(() => setLista([]))
    }
  }

  async function abrirNotificacao(n) {
    if (!n.lida) {
      await api(`/notificacoes/${n.id}/lida`, { metodo: 'PATCH' }).catch(() => {})
      contar()
    }
    setAberto(false)
    if (n.destino) navegar(n.destino)
  }

  async function marcarTodas() {
    await api('/notificacoes/marcar-todas-lidas', { metodo: 'POST' }).catch(() => {})
    setLista((atual) => atual?.map((n) => ({ ...n, lida: true })))
    contar()
  }

  const rotulo = naoLidas ? `Notificações: ${naoLidas} não ${naoLidas === 1 ? 'lida' : 'lidas'}` : 'Notificações'

  return (
    <div className="sino" ref={caixa}>
      <button type="button" className="sino__botao" aria-label={rotulo} aria-expanded={aberto} onClick={alternar}>
        <span aria-hidden="true">🔔</span>
        {naoLidas > 0 && <span className="sino__contador" aria-hidden="true">{naoLidas > 9 ? '9+' : naoLidas}</span>}
      </button>
      {aberto && (
        <div className="sino__painel" role="dialog" aria-label="Notificações recentes">
          <div className="sino__topo">
            <strong>Notificações</strong>
            {naoLidas > 0 && <button type="button" className="botao botao--leve botao--pequeno" onClick={marcarTodas}>Marcar todas como lidas</button>}
          </div>
          {lista === null && <p className="estado">Carregando…</p>}
          {lista?.length === 0 && <p className="estado">Nenhuma notificação por enquanto.</p>}
          {lista?.length > 0 && (
            <ul className="lista-notificacoes">
              {lista.map((n) => (
                <li key={n.id}>
                  <button type="button" className={`notificacao${n.lida ? '' : ' notificacao--nova'}`} onClick={() => abrirNotificacao(n)}>
                    {!n.lida && <span className="notificacao__ponto" aria-label="não lida" />}
                    <span className="notificacao__texto">{n.mensagem}</span>
                    <small>{textoHaQuanto(n.criado_em)}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <Link className="sino__todas" to="/notificacoes" onClick={() => setAberto(false)}>Ver todas as notificações</Link>
        </div>
      )}
    </div>
  )
}
