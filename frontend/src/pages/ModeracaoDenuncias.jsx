import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const ABAS = [['pendente', 'Pendentes'], ['removido', 'Removidos'], ['banido', 'Abrigos suspensos'], ['advertido', 'Advertidos'], ['ignorado', 'Ignorados']]
const DECISOES = [
  ['ignorado', 'Ignorar', 'Denúncia improcedente: o anúncio continua.'],
  ['advertido', 'Advertir o abrigo', 'O abrigo recebe um aviso; o anúncio continua.'],
  ['removido', 'Remover o anúncio', 'O anúncio sai do ar e os interesses abertos são encerrados.'],
  ['banido', 'Suspender o abrigo', 'Remove o anúncio e suspende o abrigo inteiro.'],
]

// Moderação de denúncias (RF-41): a administração decide; cada decisão avisa os envolvidos e vai ao histórico.
export default function ModeracaoDenuncias() {
  const [aba, setAba] = useState('pendente')
  const [denuncias, setDenuncias] = useState(null)
  const [observacao, setObservacao] = useState({})
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const carregar = useCallback(() => {
    api(`/admin/denuncias?status=${aba}`).then(setDenuncias).catch((e) => setErro(e.message))
  }, [aba])
  useEffect(() => { setDenuncias(null); carregar() }, [carregar])

  async function decidir(d, decisao, rotulo) {
    if ((decisao === 'removido' || decisao === 'banido') && !window.confirm(`${rotulo}: ${d.animal_nome} (${d.nome_abrigo})?`)) return
    setErro('')
    setOk('')
    try {
      await api(`/admin/denuncias/${d.id}`, { metodo: 'PATCH', corpo: { decisao, observacao: observacao[d.id] || null } })
      setOk(`${rotulo}: feito. Quem denunciou e o abrigo foram avisados.`)
      carregar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <section aria-label="Denúncias">
      <div className="acoes" role="tablist" aria-label="Situação das denúncias" style={{ marginBottom: '1rem' }}>
        {ABAS.map(([v, r]) => (
          <button key={v} role="tab" aria-selected={aba === v} className={`botao botao--pequeno ${aba === v ? '' : 'botao--leve'}`} onClick={() => setAba(v)}>{r}</button>
        ))}
      </div>
      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {denuncias === null && <p className="estado">Carregando…</p>}
      {denuncias?.length === 0 && <p className="estado">{aba === 'pendente' ? 'Nenhuma denúncia esperando análise.' : 'Nada por aqui.'}</p>}
      <div style={{ display: 'grid', gap: '1rem' }}>
        {denuncias?.map((d) => (
          <article key={d.id} className="cartao" aria-label={`Denúncia sobre ${d.animal_nome}`}>
            <div className="topo-pagina" style={{ marginBottom: '0.5rem' }}>
              <div>
                <h2 style={{ marginBottom: 0 }}><Link to={`/animais/${d.animal_id}`}>{d.animal_nome}</Link> · <Link to={`/abrigos/${d.abrigo_id}`}>{d.nome_abrigo}</Link></h2>
                <small>denunciado por {d.denunciante_nome} em {new Date(d.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</small>
              </div>
              {d.denuncias_do_animal > 1 && <span className="etiqueta etiqueta--erro">{d.denuncias_do_animal} denúncias deste anúncio</span>}
            </div>
            <blockquote className="denuncia__motivo">{d.motivo}</blockquote>
            {aba === 'pendente' && (
              <>
                <div className="campo">
                  <label htmlFor={`obs-${d.id}`}>Observação para o abrigo (opcional)</label>
                  <input id={`obs-${d.id}`} maxLength={500} value={observacao[d.id] || ''} onChange={(e) => setObservacao({ ...observacao, [d.id]: e.target.value })} />
                </div>
                <div className="acoes" style={{ marginTop: '0.75rem' }}>
                  {DECISOES.map(([valor, rotulo, dica]) => (
                    <button key={valor} type="button" title={dica} className={`botao botao--pequeno ${valor === 'banido' || valor === 'removido' ? 'botao--perigo' : 'botao--leve'}`}
                      onClick={() => decidir(d, valor, rotulo)}>{rotulo}</button>
                  ))}
                </div>
              </>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
