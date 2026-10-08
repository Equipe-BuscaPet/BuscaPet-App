import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { linkWhatsApp, STATUS_INTERESSE } from '../rotulos'

const FILTROS = [['', 'Todos'], ['aguardando', 'Aguardando'], ['em_conversa', 'Em conversa'], ['aprovado', 'Aprovados'], ['recusado', 'Recusados']]
const COR = { aguardando: 'etiqueta--atencao', em_conversa: 'etiqueta--atencao', aprovado: 'etiqueta--ok', recusado: 'etiqueta--erro' }

export default function Interessados() {
  const [filtro, setFiltro] = useState('')
  const [interesses, setInteresses] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const carregar = useCallback(async () => {
    setCarregando(true)
    try {
      setInteresses(await api(`/interesses/recebidos${filtro ? `?status=${filtro}` : ''}`))
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }, [filtro])

  useEffect(() => { carregar() }, [carregar])

  async function decidir(i, status) {
    setErro('')
    setOk('')
    try {
      await api(`/interesses/${i.id}`, { metodo: 'PATCH', corpo: { status } })
      setOk({
        em_conversa: `Marcado como em conversa com ${i.tutor_nome}.`,
        aprovado: `Interesse de ${i.tutor_nome} aprovado. ${i.animal_nome} passou para “Em processo de adoção” e saiu do catálogo.`,
        recusado: `Interesse de ${i.tutor_nome} recusado.`,
      }[status])
      await carregar()
    } catch (err) {
      setErro(err.message)
      await carregar()
    }
  }

  return (
    <main className="pagina">
      <h1>Interessados</h1>
      <p className="subtitulo">Pessoas que querem adotar os animais do seu abrigo.</p>

      <div className="acoes" role="tablist" aria-label="Situação" style={{ marginBottom: '1rem' }}>
        {FILTROS.map(([valor, rotulo]) => (
          <button key={valor} role="tab" aria-selected={filtro === valor} className={`botao ${filtro === valor ? '' : 'botao--leve'}`} onClick={() => { setFiltro(valor); setOk(''); setErro('') }}>
            {rotulo}
          </button>
        ))}
      </div>

      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {carregando && <p className="estado">Carregando…</p>}
      {!carregando && interesses.length === 0 && !erro && <p className="estado">Nenhum interesse {filtro ? 'nesta situação' : 'recebido ainda'}.</p>}

      <div style={{ display: 'grid', gap: '1rem' }}>
        {interesses.map((i) => {
          const whats = linkWhatsApp(i.tutor_telefone)
          const aberto = i.status === 'aguardando' || i.status === 'em_conversa'
          return (
            <article key={i.id} className="cartao">
              <div className="topo-pagina" style={{ marginBottom: '0.5rem' }}>
                <div>
                  <h2 style={{ marginBottom: 0 }}>{i.tutor_nome}</h2>
                  <small>quer adotar <Link to={`/animais/${i.animal_id}`}>{i.animal_nome}</Link> · {new Date(i.criado_em).toLocaleDateString('pt-BR')}</small>
                </div>
                <span className={`etiqueta ${COR[i.status]}`}>{STATUS_INTERESSE[i.status]}</span>
              </div>
              <div className="detalhe">
                <dl>
                  <dt>E-mail</dt><dd><a href={`mailto:${i.tutor_email}`}>{i.tutor_email}</a></dd>
                  <dt>Telefone</dt>
                  <dd>
                    {i.tutor_telefone || 'Não informado'}
                    {whats && <> · <a href={whats} target="_blank" rel="noreferrer">Abrir no WhatsApp</a></>}
                  </dd>
                  {i.tutor_cidade && <><dt>Cidade</dt><dd>{i.tutor_cidade}</dd></>}
                  {i.mensagem && <><dt>Mensagem</dt><dd>{i.mensagem}</dd></>}
                </dl>
              </div>
              {aberto && (
                <div className="acoes" style={{ marginTop: '0.75rem' }}>
                  {i.status === 'aguardando' && <button className="botao botao--leve" onClick={() => decidir(i, 'em_conversa')}>Iniciar conversa</button>}
                  <button className="botao" onClick={() => decidir(i, 'aprovado')}>Aprovar</button>
                  <button className="botao botao--leve" onClick={() => decidir(i, 'recusado')}>Recusar</button>
                </div>
              )}
            </article>
          )
        })}
      </div>
    </main>
  )
}
