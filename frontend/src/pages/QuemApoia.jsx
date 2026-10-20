import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CartaoNecessidade from '../componentes/CartaoNecessidade'
import { EMOJI_ESTABELECIMENTO, TIPOS_ESTABELECIMENTO, URGENCIAS } from '../rotulos'
import { useUltimoPedido } from '../useUltimoPedido'

const MEDALHAS = ['🥇', '🥈', '🥉']
const CATEGORIAS = ['petshop', 'clinica', 'distribuidora', 'pessoa_fisica']

function Chamada() {
  const { usuario } = useAuth()
  let botao = <Link className="botao" to="/cadastro?tipo=apoiador">Quero apoiar</Link>
  if (usuario?.tipo_conta === 'apoiador') botao = <a className="botao" href="#mural">Ver o que os abrigos precisam</a>
  else if (usuario) botao = null
  return (
    <section className="chamada-apoio">
      <div>
        <h2>Petshop, clínica ou distribuidora?</h2>
        <p>Doe o que os abrigos precisam agora e apareça no ranking da sua categoria. A doação só conta depois que o abrigo confirma o recebimento.</p>
      </div>
      {botao}
    </section>
  )
}

// Aba "Quem apoia" (escopo §5): reconhecimento + mural de necessidades, para quem chega pelo ranking
// encontrar na hora uma necessidade concreta (RF-33, RF-35).
export default function QuemApoia() {
  const [destaques, setDestaques] = useState([])
  const [categoria, setCategoria] = useState('petshop')
  const [periodo, setPeriodo] = useState('mes')
  const [ranking, setRanking] = useState(null)
  const [urgencia, setUrgencia] = useState('')
  const [mural, setMural] = useState(null)
  const [erro, setErro] = useState('')
  const novoPedidoRanking = useUltimoPedido()
  const novoPedidoMural = useUltimoPedido()

  useEffect(() => {
    api('/apoiadores/ranking?limite=3').then(setDestaques).catch((e) => setErro(e.message))
  }, [])

  useEffect(() => {
    const valido = novoPedidoRanking()
    setRanking(null)
    api(`/apoiadores/ranking?categoria=${categoria}&periodo=${periodo}`)
      .then((r) => valido() && setRanking(r))
      .catch((e) => valido() && setErro(e.message))
  }, [categoria, periodo, novoPedidoRanking])

  function carregarMural() {
    const valido = novoPedidoMural()
    api(`/necessidades${urgencia ? `?urgencia=${urgencia}` : ''}`)
      .then((m) => valido() && setMural(m))
      .catch((e) => valido() && setErro(e.message))
  }
  useEffect(carregarMural, [urgencia]) // eslint-disable-line react-hooks/exhaustive-deps

  const mes = new Date().toLocaleDateString('pt-BR', { month: 'long' })

  return (
    <main className="pagina">
      <h1>Quem apoia</h1>
      <p className="subtitulo">Os estabelecimentos e pessoas que ajudam os abrigos, e o que os abrigos precisam agora.</p>
      <Chamada />
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

      {destaques.length > 0 && (
        <section aria-labelledby="t-destaques">
          <h2 id="t-destaques">Destaques de {mes}</h2>
          <div className="destaques">
            {destaques.map((d, i) => (
              <Link key={d.apoiador_id} to={`/apoiadores/${d.apoiador_id}`} className="cartao destaque" style={{ textDecoration: 'none', color: 'inherit' }}>
                <span className="destaque__medalha" aria-hidden="true">{MEDALHAS[i]}</span>
                <strong>{d.nome}</strong>
                <small>{TIPOS_ESTABELECIMENTO[d.tipo_estabelecimento]} · {d.pontos} pontos</small>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="t-ranking" style={{ marginBottom: '2rem' }}>
        <div className="topo-pagina">
          <h2 id="t-ranking" style={{ margin: 0 }}>Ranking por categoria</h2>
          <div className="acoes" role="tablist" aria-label="Período">
            {[['mes', 'Este mês'], ['ano', 'No ano']].map(([valor, rotulo]) => (
              <button key={valor} role="tab" aria-selected={periodo === valor} className={`botao botao--pequeno ${periodo === valor ? '' : 'botao--leve'}`} onClick={() => setPeriodo(valor)}>{rotulo}</button>
            ))}
          </div>
        </div>
        <div className="abas" role="tablist" aria-label="Categoria">
          {CATEGORIAS.map((c) => (
            <button key={c} role="tab" aria-selected={categoria === c} className={`abas__item${categoria === c ? ' abas__item--ativa' : ''}`} onClick={() => setCategoria(c)}>
              <span aria-hidden="true">{EMOJI_ESTABELECIMENTO[c]}</span> {TIPOS_ESTABELECIMENTO[c]}
            </button>
          ))}
        </div>
        <p className="legenda" style={{ marginBottom: '0.75rem' }}>
          Pontos: 10 por doação confirmada pelo abrigo + 10 por mês seguido doando. Manter a constância vale tanto quanto doar mais.
        </p>
        {ranking === null && <p className="estado">Carregando…</p>}
        {ranking?.length === 0 && <p className="estado">Ainda não há doações confirmadas nesta categoria {periodo === 'mes' ? 'neste mês' : 'neste ano'}. Que tal ser o primeiro?</p>}
        <ol className="ranking" aria-label={`Ranking de ${TIPOS_ESTABELECIMENTO[categoria]}`}>
          {ranking?.map((r) => (
            <li key={r.apoiador_id} className="cartao">
              <span className="ranking__posicao">{r.posicao}º</span>
              <div>
                <Link className="ranking__nome" to={`/apoiadores/${r.apoiador_id}`}>{r.nome}</Link>{' '}
                {r.selo_ativo && <span className="selo-apoio">Apoiador ativo</span>}
                <div className="ranking__detalhe">
                  {r.doacoes_confirmadas} {r.doacoes_confirmadas === 1 ? 'doação confirmada' : 'doações confirmadas'} · {r.meses_seguidos} {r.meses_seguidos === 1 ? 'mês seguido' : 'meses seguidos'}
                </div>
              </div>
              <div className="ranking__pontos">{r.pontos}<small>pontos</small></div>
            </li>
          ))}
        </ol>
      </section>

      <section id="mural" aria-labelledby="t-mural">
        <div className="topo-pagina">
          <h2 id="t-mural" style={{ margin: 0 }}>Mural de necessidades</h2>
          <div className="campo" style={{ minWidth: 180 }}>
            <label htmlFor="urgencia">Urgência</label>
            <select id="urgencia" value={urgencia} onChange={(e) => setUrgencia(e.target.value)}>
              <option value="">Todas</option>
              {Object.entries(URGENCIAS).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
            </select>
          </div>
        </div>
        <p className="subtitulo">O que os abrigos verificados precisam agora, dos mais urgentes para os que podem esperar.</p>
        {mural === null && <p className="estado">Carregando…</p>}
        {mural?.length === 0 && <p className="estado">Nenhuma necessidade em aberto{urgencia ? ' com essa urgência' : ''}.</p>}
        <div className="necessidades">
          {mural?.map((n) => <CartaoNecessidade key={n.id} necessidade={n} />)}
        </div>
      </section>
    </main>
  )
}
