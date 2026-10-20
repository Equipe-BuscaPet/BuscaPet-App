import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, urlFoto } from '../api'
import DenunciarAnuncio from '../componentes/DenunciarAnuncio'
import PainelInteresse from './PainelInteresse'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, STATUS_ANIMAL, textoIdade } from '../rotulos'

const simNao = (v) => (v === null || v === undefined ? 'Não informado' : v ? 'Sim' : 'Não')

export default function AnimalDetalhe() {
  const { id } = useParams()
  const [animal, setAnimal] = useState(null)
  const [erro, setErro] = useState('')
  const [fotoAtual, setFotoAtual] = useState(0)

  useEffect(() => {
    setAnimal(null)
    setErro('')
    setFotoAtual(0)
    api(`/animais/${id}`).then(setAnimal).catch((e) => setErro(e.status === 404 ? 'Animal não encontrado.' : e.message))
  }, [id])

  if (erro) {
    return (
      <main className="pagina">
        <div className="aviso aviso--erro" role="alert">{erro}</div>
        <Link to="/">← Voltar aos animais</Link>
      </main>
    )
  }
  if (!animal) return <p className="estado">Carregando…</p>

  return (
    <main className="pagina">
      <p><Link to="/">← Voltar aos animais</Link></p>
      <div className="duas-colunas">
        <div className="galeria">
          {animal.fotos.length ? (
            <img className="galeria__principal" src={urlFoto(animal.fotos[fotoAtual].url)} alt={`${animal.nome}, foto ${fotoAtual + 1} de ${animal.fotos.length}`} />
          ) : (
            <div className="animal__foto" style={{ minHeight: 260, fontSize: '5rem' }} aria-hidden="true">{EMOJI_ESPECIE[animal.especie]}</div>
          )}
          {animal.fotos.length > 1 && (
            <ul className="miniaturas" aria-label="Outras fotos">
              {animal.fotos.map((f, i) => (
                <li key={f.id}>
                  <button type="button" className={`miniatura${i === fotoAtual ? ' miniatura--atual' : ''}`} onClick={() => setFotoAtual(i)} aria-label={`Ver foto ${i + 1}`} aria-pressed={i === fotoAtual}>
                    <img src={urlFoto(f.url)} alt="" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="cartao detalhe">
          <div>
            <h1>{animal.nome}</h1>
            <span className={`etiqueta ${animal.status === 'disponivel' ? 'etiqueta--ok' : 'etiqueta--atencao'}`}>
              {STATUS_ANIMAL[animal.status]}
            </span>
          </div>
          <dl>
            <dt>Espécie</dt><dd>{ESPECIES[animal.especie]}{animal.raca_aproximada ? ` (${animal.raca_aproximada})` : ''}</dd>
            <dt>Porte</dt><dd>{PORTES[animal.porte]}</dd>
            <dt>Sexo</dt><dd>{SEXOS[animal.sexo]}</dd>
            <dt>Idade</dt><dd>{textoIdade(animal.idade_estimada_meses)}</dd>
            <dt>Castrado</dt><dd>{simNao(animal.castrado)}</dd>
            <dt>Vacinado</dt><dd>{simNao(animal.vacinado)}</dd>
            <dt>Vermifugado</dt><dd>{simNao(animal.vermifugado)}</dd>
            <dt>Convive com crianças</dt><dd>{simNao(animal.convivencia_criancas)}</dd>
            <dt>Convive com outros animais</dt><dd>{simNao(animal.convivencia_outros_animais)}</dd>
            <dt>Abrigo</dt><dd><Link to={`/abrigos/${animal.abrigo_id}`}>{animal.nome_abrigo}</Link> <span className={`etiqueta ${animal.abrigo_verificado ? 'etiqueta--ok' : 'etiqueta--atencao'}`}>{animal.abrigo_verificado ? 'Verificado' : 'Não verificado'}</span></dd>
          </dl>
          {animal.temperamento && <section><h2>Temperamento</h2><p>{animal.temperamento}</p></section>}
          {animal.historia_resgate && <section><h2>História</h2><p>{animal.historia_resgate}</p></section>}
        </div>
      </div>
      <div style={{ marginTop: '1rem' }}>
        <PainelInteresse animal={animal} />
      </div>
      <DenunciarAnuncio animal={animal} />
    </main>
  )
}
