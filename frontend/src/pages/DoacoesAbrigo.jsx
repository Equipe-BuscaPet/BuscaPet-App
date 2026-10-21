import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CartaoNecessidade from '../componentes/CartaoNecessidade'
import { COR_DOACAO, STATUS_DOACAO, textoDoacao, URGENCIAS } from '../rotulos'
import MetaDoMes from '../componentes/MetaDoMes'

const VAZIA = { item: '', quantidade: 1, urgencia: 'media' }
const HISTORICO_INICIAL = 5

// Uma doação recebida: quem doou, o quê e, se ainda aguarda, os botões para responder.
function CartaoDoacao({ doacao: d, decidir }) {
  return (
    <article className="cartao" aria-label={`Doação de ${d.nome_apoiador}`}>
      <div className="topo-pagina" style={{ marginBottom: '0.25rem' }}>
        <div>
          <strong>{textoDoacao(d)}</strong>
          <div><small>de {d.perfil_publico_doador ? <Link to={`/apoiadores/${d.apoiador_id}`}>{d.nome_apoiador}</Link> : <>{d.nome_apoiador} (pessoa física)</>} · {new Date(d.registrado_em).toLocaleDateString('pt-BR')} · <a href={`mailto:${d.contato}`}>{d.contato}</a></small></div>
        </div>
        <span className={`etiqueta ${COR_DOACAO[d.status]}`}>{STATUS_DOACAO[d.status]}</span>
      </div>
      {decidir && d.status === 'aguardando_confirmacao' && (
        <div className="acoes">
          <button className="botao" onClick={() => decidir(d, 'confirmada')}>{d.valor_centavos != null ? 'Confirmar: o PIX chegou' : 'Confirmar recebimento'}</button>
          <button className="botao botao--leve" onClick={() => decidir(d, 'recusada')}>Não recebi</button>
        </div>
      )}
    </article>
  )
}

// Área do abrigo para doações (RF-30 e RF-32): meta do mês em dinheiro, necessidades e confirmação do que recebeu.
export default function DoacoesAbrigo() {
  const { usuario } = useAuth()
  const verificado = usuario.perfil?.status_validacao === 'aprovado'
  const [form, setForm] = useState(VAZIA)
  const [necessidades, setNecessidades] = useState(null)
  const [doacoes, setDoacoes] = useState(null)
  const [erro, setErro] = useState('')
  const [camposComErro, setCamposComErro] = useState({})
  const [ok, setOk] = useState('')
  const [verTodas, setVerTodas] = useState(false)

  const carregar = useCallback(() => {
    api('/necessidades/minhas').then(setNecessidades).catch((e) => setErro(e.message))
    api('/doacoes/recebidas').then(setDoacoes).catch((e) => setErro(e.message))
  }, [])
  useEffect(() => { carregar() }, [carregar])

  async function acao(fn, mensagem) {
    setErro('')
    setOk('')
    try {
      await fn()
      setOk(mensagem)
      carregar()
    } catch (e) {
      setErro(e.message)
      setCamposComErro(e.campos || {})
    }
  }

  function publicar(e) {
    e.preventDefault()
    setCamposComErro({})
    acao(async () => {
      await api('/necessidades', { metodo: 'POST', corpo: { ...form, item: form.item.trim(), quantidade: Number(form.quantidade) } })
      setForm(VAZIA)
    }, 'Necessidade publicada no mural do Quem apoia.')
  }

  const decidir = (d, status) => acao(
    () => api(`/doacoes/${d.id}`, { metodo: 'PATCH', corpo: { status } }),
    status === 'confirmada'
      ? `Recebimento confirmado. A doação de ${d.nome_apoiador} passou a contar no ranking${d.valor_centavos != null ? ' e na meta do mês' : ''}.`
      : `Doação de ${d.nome_apoiador} marcada como não recebida.`,
  )
  const pendentes = doacoes?.filter((d) => d.status === 'aguardando_confirmacao') ?? []
  const respondidas = doacoes?.filter((d) => d.status !== 'aguardando_confirmacao') ?? []

  return (
    <main className="pagina">
      <h1>Necessidades e doações</h1>
      <p className="subtitulo">Defina a meta do mês, publique o que o abrigo precisa e confirme as doações quando chegarem. Só doação confirmada conta no ranking e na meta.</p>
      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

      <MetaDoMes verificado={verificado} aoMudar={carregar} />

      <section aria-labelledby="t-recebidas" style={{ marginBottom: '2rem' }}>
        <h2 id="t-recebidas">Doações para confirmar {pendentes.length > 0 && <span className="etiqueta etiqueta--atencao">{pendentes.length}</span>}</h2>
        {doacoes === null && <p className="estado">Carregando…</p>}
        {doacoes !== null && pendentes.length === 0 && <p className="estado">Nenhuma doação esperando a sua confirmação.</p>}
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {pendentes.map((d) => <CartaoDoacao key={d.id} doacao={d} decidir={decidir} />)}
        </div>
      </section>

      {respondidas.length > 0 && (
        <section aria-labelledby="t-historico-doacoes" style={{ marginBottom: '2rem' }}>
          <h2 id="t-historico-doacoes">Histórico de doações <span className="etiqueta">{respondidas.length}</span></h2>
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {(verTodas ? respondidas : respondidas.slice(0, HISTORICO_INICIAL)).map((d) => <CartaoDoacao key={d.id} doacao={d} />)}
          </div>
          {respondidas.length > HISTORICO_INICIAL && (
            <div className="acoes" style={{ marginTop: '0.75rem' }}>
              <button type="button" className="botao botao--leve botao--pequeno" onClick={() => setVerTodas((v) => !v)} aria-expanded={verTodas}>
                {verTodas ? 'Mostrar só as mais recentes' : `Ver todas as ${respondidas.length}`}
              </button>
            </div>
          )}
        </section>
      )}

      <section aria-labelledby="t-publicar" className="cartao" style={{ marginBottom: '2rem' }}>
        <h2 id="t-publicar">Publicar necessidade</h2>
        {!verificado ? (
          <div className="aviso aviso--atencao" style={{ margin: 0 }}>
            Só abrigos com o selo Verificado publicam no mural. A administração concede o selo depois de conferir o abrigo.
          </div>
        ) : (
          <form className="formulario" onSubmit={publicar}>
            <div className="grade-campos">
              <div className="campo" style={{ gridColumn: '1 / -1' }}>
                <label htmlFor="item">O que o abrigo precisa</label>
                <input id="item" value={form.item} onChange={(e) => setForm({ ...form, item: e.target.value })} placeholder="Ex.: ração para cão adulto (saco de 15 kg)" required minLength={2} maxLength={200} aria-invalid={camposComErro.item ? 'true' : undefined} />
              </div>
              <div className="campo">
                <label htmlFor="quantidade">Quantidade</label>
                <input id="quantidade" type="number" min={1} max={10000} value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })} required />
              </div>
              <div className="campo">
                <label htmlFor="urgencia">Urgência</label>
                <select id="urgencia" value={form.urgencia} onChange={(e) => setForm({ ...form, urgencia: e.target.value })}>
                  {Object.entries(URGENCIAS).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </div>
            </div>
            <div className="acoes"><button className="botao">Publicar no mural</button></div>
          </form>
        )}
      </section>

      <section aria-labelledby="t-minhas">
        <h2 id="t-minhas">Necessidades do abrigo</h2>
        {necessidades === null && <p className="estado">Carregando…</p>}
        {necessidades?.length === 0 && <p className="estado">Nenhuma necessidade publicada.</p>}
        <div className="necessidades">
          {necessidades?.map((n) => (
            <CartaoNecessidade
              key={n.id} necessidade={n} mostrarAbrigo={false}
              acoes={(
                <div className="acoes">
                  {n.status === 'aberta'
                    ? <button className="botao botao--leve botao--pequeno" onClick={() => acao(() => api(`/necessidades/${n.id}`, { metodo: 'PATCH', corpo: { status: 'atendida' } }), `"${n.item}" marcada como atendida e retirada do mural.`)}>Marcar como atendida</button>
                    : <button className="botao botao--leve botao--pequeno" onClick={() => acao(() => api(`/necessidades/${n.id}`, { metodo: 'PATCH', corpo: { status: 'aberta' } }), `"${n.item}" voltou ao mural.`)}>Reabrir</button>}
                  <button className="botao botao--leve botao--pequeno" onClick={() => window.confirm('Excluir esta necessidade?') && acao(() => api(`/necessidades/${n.id}`, { metodo: 'DELETE' }), 'Necessidade excluída.')}>Excluir</button>
                </div>
              )}
            />
          ))}
        </div>
      </section>
    </main>
  )
}
