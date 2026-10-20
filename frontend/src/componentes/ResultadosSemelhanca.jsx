import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, urlFoto } from '../api'
import { textoData, textoKm } from '../rotulos'
import { useUltimoPedido } from '../useUltimoPedido'

// Grau sempre com ícone + palavra (nunca só a cor): o escopo pede grau qualitativo, não porcentagem.
const GRAU = {
  alta: ['●●●', 'Semelhança alta', 'etiqueta--ok'],
  media: ['●●○', 'Semelhança média', 'etiqueta--atencao'],
  baixa: ['●○○', 'Semelhança baixa', ''],
}
const ORIGEM = { avistamento: 'Avistado na rua', animal: 'Num abrigo', animal_perdido: 'Perdido' }
const RAIOS = [5, 10, 25, 50]

function Candidato({ c }) {
  const [icone, rotulo, classe] = GRAU[c.grau] || []
  return (
    <article className="animal registro">
      <Link to={c.caminho} className="registro__link">
        {c.foto ? <img className="animal__foto animal__foto--img" src={urlFoto(c.foto)} alt="" loading="lazy" />
          : <div className="animal__foto" aria-hidden="true">📷</div>}
        <div className="registro__topo">
          <h3>{c.rotulo}</h3>
          {c.grau && <span className={`etiqueta ${classe}`}><span aria-hidden="true">{icone}</span> {rotulo}</span>}
        </div>
        <p>{ORIGEM[c.tipo]} · <strong>a {textoKm(c.distancia_km)}</strong></p>
        {c.data && <p>{c.tipo === 'animal' ? 'No abrigo desde' : c.tipo === 'animal_perdido' ? 'Sumiu em' : 'Visto em'} {textoData(c.data)}</p>}
      </Link>
    </article>
  )
}

// Busca por semelhança visual (RF-22, RF-23, RF-27): as fotos do registro contra a outra base, no núcleo OpenCL.
export default function ResultadosSemelhanca({ origem, id, raioInicial, titulo, vazio }) {
  const [raio, setRaio] = useState(raioInicial || (origem === 'perdido' ? 5 : 10))
  const [mesmoPorte, setMesmoPorte] = useState(false)
  const [mesmaCor, setMesmaCor] = useState(false)
  const [resposta, setResposta] = useState(null)
  const [erro, setErro] = useState('')
  const novoPedido = useUltimoPedido()

  useEffect(() => {
    const atual = novoPedido()
    const q = new URLSearchParams({ origem, id, raio_km: raio, mesmo_porte: mesmoPorte, mesma_cor: mesmaCor })
    setResposta(null)
    setErro('')
    api(`/reencontro/semelhantes?${q}`)
      .then((r) => atual() && setResposta(r))
      .catch((e) => atual() && setErro(e.message))
  }, [origem, id, raio, mesmoPorte, mesmaCor, novoPedido])

  const parecidos = resposta?.candidatos.filter((c) => c.grau === 'alta' || c.grau === 'media').length ?? 0

  return (
    <section className="semelhanca" aria-labelledby="titulo-semelhanca">
      <h3 id="titulo-semelhanca">{titulo}</h3>
      <div className="semelhanca__filtros">
        <label>Até
          <select value={raio} onChange={(e) => setRaio(Number(e.target.value))}>
            {[...new Set([...RAIOS, raio])].sort((a, b) => a - b).map((r) => <option key={r} value={r}>{r} km</option>)}
          </select>
        </label>
        <label><input type="checkbox" checked={mesmoPorte} onChange={(e) => setMesmoPorte(e.target.checked)} /> Mesmo porte</label>
        <label><input type="checkbox" checked={mesmaCor} onChange={(e) => setMesmaCor(e.target.checked)} /> Mesma cor</label>
      </div>

      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!resposta && !erro && <p className="estado" role="status">Comparando as fotos…</p>}
      {resposta && (
        <>
          {resposta.comparacao_por_foto ? (
            <p className="semelhanca__resumo" role="status">
              Comparamos as fotos com <strong>{resposta.registros_comparados}</strong> registro(s) da mesma espécie até{' '}
              {resposta.raio_km} km ({resposta.comparacoes} comparações de foto em {resposta.tempo_nucleo_ms.toLocaleString('pt-BR')} ms no
              núcleo OpenCL). {parecidos > 0 ? <strong>{parecidos} com semelhança alta ou média.</strong> : 'Nenhum muito parecido por enquanto.'}
            </p>
          ) : (
            <div className="aviso aviso--atencao" role="status">
              <strong>Comparação por foto indisponível agora.</strong> Mostramos os registros da mesma espécie do mais
              perto ao mais longe. {resposta.motivo}
            </div>
          )}
          {resposta.candidatos.length === 0 ? <p className="estado">{vazio}</p> : (
            <div className="grade-animais">{resposta.candidatos.map((c) => <Candidato key={`${c.tipo}-${c.id}`} c={c} />)}</div>
          )}
          <p className="semelhanca__nota"><small>
            O BuscaPet nunca afirma que encontrou o animal: a semelhança das fotos ajuda a ordenar, mas só você
            reconhece o seu. Abra o registro para ver todas as fotos e os detalhes.
          </small></p>
        </>
      )}
    </section>
  )
}
