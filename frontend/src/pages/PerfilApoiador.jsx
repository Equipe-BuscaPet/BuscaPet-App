import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { EMOJI_ESTABELECIMENTO, TIPOS_ESTABELECIMENTO } from '../rotulos'

// Perfil público do apoiador (RF-34): a contrapartida de quem doa — marca, localização, selo e abrigos apoiados.
export default function PerfilApoiador() {
  const { id } = useParams()
  const [ap, setAp] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    setAp(null)
    api(`/apoiadores/${id}`).then(setAp).catch((e) => setErro(e.status === 404 ? 'Apoiador não encontrado.' : e.message))
  }, [id])

  const voltar = <p><Link to="/quem-apoia">← Quem apoia</Link></p>
  if (erro) return <main className="pagina">{voltar}<div className="aviso aviso--erro" role="alert">{erro}</div></main>
  if (!ap) return <p className="estado">Carregando…</p>

  return (
    <main className="pagina">
      {voltar}
      <div className="topo-pagina">
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}><span aria-hidden="true">{EMOJI_ESTABELECIMENTO[ap.tipo_estabelecimento]}</span> {ap.nome}</h1>
          <span className="etiqueta">{TIPOS_ESTABELECIMENTO[ap.tipo_estabelecimento]}</span>{' '}
          {ap.selo_ativo
            ? <span className="selo-apoio">Apoiador ativo</span>
            : <span className="etiqueta">Sem doação confirmada nos últimos dois meses</span>}
        </div>
      </div>

      <div className="resumo-hoje" style={{ marginTop: '1rem' }}>
        <div className="cartao"><strong>{ap.pontos_mes}</strong><span>pontos neste mês</span></div>
        <div className="cartao"><strong>{ap.pontos_ano}</strong><span>pontos no ano</span></div>
        <div className="cartao"><strong>{ap.meses_seguidos}</strong><span>{ap.meses_seguidos === 1 ? 'mês seguido doando' : 'meses seguidos doando'}</span></div>
        <div className="cartao"><strong>{ap.doacoes_confirmadas}</strong><span>doações confirmadas pelos abrigos</span></div>
      </div>

      <div className="duas-colunas">
        <section className="cartao" aria-labelledby="t-abrigos">
          <h2 id="t-abrigos">Abrigos que apoia</h2>
          {ap.abrigos_apoiados.length === 0 && <p className="estado" style={{ padding: '0.5rem 0' }}>Ainda sem doações confirmadas.</p>}
          <ul className="chips">
            {ap.abrigos_apoiados.map((a) => (
              <li key={a.id}><Link to={`/abrigos/${a.id}`}>{a.nome_abrigo} · {a.doacoes_confirmadas}</Link></li>
            ))}
          </ul>
        </section>
        <section className="cartao detalhe" aria-labelledby="t-onde">
          <h2 id="t-onde" style={{ margin: 0 }}>Onde fica</h2>
          <dl>
            <dt>Endereço</dt><dd>{ap.endereco}</dd>
            <dt>Na BuscaPet desde</dt><dd>{new Date(ap.membro_desde).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}</dd>
          </dl>
        </section>
      </div>
    </main>
  )
}
