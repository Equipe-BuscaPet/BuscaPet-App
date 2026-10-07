import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, STATUS_ANIMAL, textoIdade } from '../rotulos'

const simNao = (v) => (v === null || v === undefined ? 'Não informado' : v ? 'Sim' : 'Não')

export default function AnimalDetalhe() {
  const { id } = useParams()
  const [animal, setAnimal] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    setAnimal(null)
    setErro('')
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
        <div className="animal__foto" style={{ minHeight: 260, fontSize: '5rem' }} aria-hidden="true">
          {EMOJI_ESPECIE[animal.especie]}
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
            <dt>Abrigo</dt><dd>{animal.nome_abrigo}</dd>
          </dl>
          {animal.temperamento && <section><h2>Temperamento</h2><p>{animal.temperamento}</p></section>}
          {animal.historia_resgate && <section><h2>História</h2><p>{animal.historia_resgate}</p></section>}
        </div>
      </div>
    </main>
  )
}
