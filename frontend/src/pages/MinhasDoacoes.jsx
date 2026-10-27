import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { COR_DOACAO, STATUS_DOACAO, textoDoacao } from '../rotulos'

// Doações de quem apoia (apoiador ou tutor, RF-31): acompanha a confirmação de cada abrigo e pode desistir enquanto aguarda.
export default function MinhasDoacoes() {
  const { usuario } = useAuth()
  const [doacoes, setDoacoes] = useState(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const carregar = useCallback(() => {
    api('/doacoes/minhas').then(setDoacoes).catch((e) => setErro(e.message))
  }, [])
  useEffect(() => { carregar() }, [carregar])

  async function cancelar(d) {
    if (!window.confirm(`Cancelar a doação de ${textoDoacao(d)}?`)) return
    setErro('')
    try {
      await api(`/doacoes/${d.id}`, { metodo: 'DELETE' })
      setOk('Doação cancelada. O abrigo foi avisado.')
      carregar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <main className="pagina">
      <div className="topo-pagina">
        <h1 style={{ margin: 0 }}>Minhas doações</h1>
        <div className="acoes">
          {usuario.tipo_conta === 'apoiador' && <Link className="botao botao--leve" to={`/apoiadores/${usuario.id}`}>Meu perfil público</Link>}
          <Link className="botao" to="/quem-apoia#mural">Ver o mural de necessidades</Link>
        </div>
      </div>
      <p className="subtitulo">
        Cada doação conta no ranking quando o abrigo confirma que recebeu. Itens: combine a entrega pelo contato do abrigo.
        Dinheiro: faça o PIX pela chave do perfil do abrigo e informe o valor lá.
        {usuario.tipo_conta === 'tutor' && ' Você aparece no ranking de pessoa física com o primeiro nome e a inicial do sobrenome.'}
      </p>
      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {doacoes === null && <p className="estado">Carregando…</p>}
      {doacoes?.length === 0 && <p className="estado">Você ainda não registrou doações. Escolha uma necessidade no mural ou doe em dinheiro pelo perfil de um abrigo.</p>}
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {doacoes?.map((d) => (
          <article key={d.id} className="cartao" aria-label={`Doação para ${d.nome_abrigo}`}>
            <div className="topo-pagina" style={{ marginBottom: '0.25rem' }}>
              <div>
                <strong>{textoDoacao(d)}</strong>
                <div><small>para <Link to={`/abrigos/${d.abrigo_id}`}>{d.nome_abrigo}</Link> · registrada em {new Date(d.registrado_em).toLocaleDateString('pt-BR')}</small></div>
                {d.contato && <div><small>Contato do abrigo: {d.contato}</small></div>}
              </div>
              <span className={`etiqueta ${COR_DOACAO[d.status]}`}>{STATUS_DOACAO[d.status]}</span>
            </div>
            {d.status === 'aguardando_confirmacao' && (
              <div className="acoes"><button className="botao botao--leve botao--pequeno" onClick={() => cancelar(d)}>Cancelar doação</button></div>
            )}
          </article>
        ))}
      </div>
    </main>
  )
}
