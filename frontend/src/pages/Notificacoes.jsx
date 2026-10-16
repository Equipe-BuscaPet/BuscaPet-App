import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { avisarMudancaNotificacoes } from '../componentes/Sino'
import { textoHaQuanto } from '../rotulos'
import { useUltimoPedido } from '../useUltimoPedido'

// Todas as notificações da conta (RF-36), com filtro "não lidas" e paginação.
const POR_PAGINA = 20

export default function Notificacoes() {
  const navegar = useNavigate()
  const [somenteNaoLidas, setSomenteNaoLidas] = useState(false)
  const [lista, setLista] = useState([])
  const [temMais, setTemMais] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const novoPedido = useUltimoPedido()

  const buscar = useCallback(async (deslocamento) => {
    const atual = novoPedido()
    setCarregando(true)
    setErro('')
    const consulta = new URLSearchParams({ limite: POR_PAGINA, deslocamento })
    if (somenteNaoLidas) consulta.set('somente_nao_lidas', 'true')
    try {
      const pagina = await api(`/notificacoes?${consulta}`)
      if (!atual()) return
      setLista((anteriores) => (deslocamento === 0 ? pagina : [...anteriores, ...pagina]))
      setTemMais(pagina.length === POR_PAGINA)
    } catch (e) {
      if (atual()) setErro(e.message)
    } finally {
      if (atual()) setCarregando(false)
    }
  }, [somenteNaoLidas, novoPedido])

  useEffect(() => { buscar(0) }, [buscar])

  async function marcarLida(n) {
    const atualizada = await api(`/notificacoes/${n.id}/lida`, { metodo: 'PATCH' })
    // Na aba "Não lidas", o que foi lido sai da lista; em "Todas", só deixa de ficar em destaque.
    setLista((l) => (somenteNaoLidas ? l.filter((x) => x.id !== n.id) : l.map((x) => (x.id === n.id ? atualizada : x))))
    avisarMudancaNotificacoes()
    return atualizada
  }

  async function abrir(n) {
    if (!n.lida) await marcarLida(n).catch(() => {})
    if (n.destino) navegar(n.destino)
  }

  async function marcarTodas() {
    await api('/notificacoes/marcar-todas-lidas', { metodo: 'POST' })
    setLista((l) => (somenteNaoLidas ? [] : l.map((x) => ({ ...x, lida: true }))))
    setTemMais(false)
    avisarMudancaNotificacoes()
  }

  const temNaoLida = lista.some((n) => !n.lida)

  return (
    <main className="pagina pagina--media">
      <div className="topo-pagina">
        <div>
          <h1>Notificações</h1>
          <p className="subtitulo" style={{ marginBottom: 0 }}>Avisos sobre os seus interesses, animais e abrigo.</p>
        </div>
        {temNaoLida && <button type="button" className="botao botao--leve" onClick={marcarTodas}>Marcar todas como lidas</button>}
      </div>

      <div className="abas" role="tablist" aria-label="Quais notificações">
        {[[false, 'Todas'], [true, 'Não lidas']].map(([valor, rotulo]) => (
          <button key={rotulo} type="button" role="tab" aria-selected={somenteNaoLidas === valor}
            className={`abas__item${somenteNaoLidas === valor ? ' abas__item--ativa' : ''}`} onClick={() => setSomenteNaoLidas(valor)}>
            {rotulo}
          </button>
        ))}
      </div>

      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!carregando && !erro && lista.length === 0 && (
        <p className="estado">{somenteNaoLidas ? 'Nenhuma notificação não lida. Tudo em dia!' : 'Você ainda não tem notificações.'}</p>
      )}

      <ul className="lista-notificacoes lista-notificacoes--pagina" aria-label="Notificações">
        {lista.map((n) => (
          <li key={n.id} className={`cartao notificacao-linha${n.lida ? '' : ' notificacao--nova'}`}>
            {!n.lida && <span className="notificacao__ponto" aria-label="não lida" />}
            <div className="notificacao-linha__texto">
              <p>{n.mensagem}</p>
              <small>{textoHaQuanto(n.criado_em)}</small>
            </div>
            <div className="acoes">
              {n.destino && <button type="button" className="botao botao--pequeno" onClick={() => abrir(n)}>Abrir</button>}
              {!n.lida && <button type="button" className="botao botao--leve botao--pequeno" onClick={() => marcarLida(n)}>Marcar como lida</button>}
            </div>
          </li>
        ))}
      </ul>
      {carregando && <p className="estado">Carregando…</p>}
      {!carregando && temMais && (
        <p className="estado"><button className="botao botao--leve" onClick={() => buscar(lista.length)}>Ver mais</button></p>
      )}
    </main>
  )
}
