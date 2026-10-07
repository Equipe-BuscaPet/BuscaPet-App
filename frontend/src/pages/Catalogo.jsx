import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, textoIdade } from '../rotulos'

const POR_PAGINA = 12

export function CartaoAnimal({ animal }) {
  return (
    <Link to={`/animais/${animal.id}`} className="animal">
      <div className="animal__foto" aria-hidden="true">{EMOJI_ESPECIE[animal.especie]}</div>
      <h3>{animal.nome}</h3>
      <p>
        {ESPECIES[animal.especie]} · {PORTES[animal.porte]} · {SEXOS[animal.sexo]}
      </p>
      <p>{textoIdade(animal.idade_estimada_meses)}</p>
      <p>{animal.nome_abrigo}</p>
    </Link>
  )
}

export default function Catalogo() {
  const [filtros, setFiltros] = useState({ busca: '', especie: '', porte: '' })
  const [animais, setAnimais] = useState([])
  const [temMais, setTemMais] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')

  const buscar = useCallback(async (deslocamento) => {
    setCarregando(true)
    setErro('')
    const params = new URLSearchParams({ limite: POR_PAGINA, deslocamento })
    Object.entries(filtros).forEach(([k, v]) => v && params.set(k, v))
    try {
      const lista = await api(`/animais?${params}`)
      setAnimais((atual) => (deslocamento === 0 ? lista : [...atual, ...lista]))
      setTemMais(lista.length === POR_PAGINA)
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }, [filtros])

  // Refaz a busca a cada mudança de filtro (com uma pequena espera para não consultar a cada tecla).
  useEffect(() => {
    const espera = setTimeout(() => buscar(0), 250)
    return () => clearTimeout(espera)
  }, [buscar])

  const mudar = (nome) => (e) => setFiltros({ ...filtros, [nome]: e.target.value })

  return (
    <main className="pagina">
      <h1>Animais para adoção</h1>
      <p className="subtitulo">Animais de abrigos e protetores validados pela plataforma.</p>

      <div className="filtros" role="search">
        <div className="campo">
          <label htmlFor="busca">Buscar por nome ou raça</label>
          <input id="busca" value={filtros.busca} onChange={mudar('busca')} maxLength={100} />
        </div>
        <div className="campo">
          <label htmlFor="especie">Espécie</label>
          <select id="especie" value={filtros.especie} onChange={mudar('especie')}>
            <option value="">Todas</option>
            {Object.entries(ESPECIES).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="porte">Porte</label>
          <select id="porte" value={filtros.porte} onChange={mudar('porte')}>
            <option value="">Todos</option>
            {Object.entries(PORTES).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </div>
      </div>

      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!erro && !carregando && animais.length === 0 && (
        <p className="estado">Nenhum animal encontrado com esses filtros.</p>
      )}
      <div className="grade-animais">
        {animais.map((a) => <CartaoAnimal key={a.id} animal={a} />)}
      </div>
      {carregando && <p className="estado">Carregando…</p>}
      {!carregando && temMais && (
        <p className="estado"><button className="botao botao--leve" onClick={() => buscar(animais.length)}>Ver mais</button></p>
      )}
    </main>
  )
}
