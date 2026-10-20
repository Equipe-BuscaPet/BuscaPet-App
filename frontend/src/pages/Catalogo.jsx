import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, urlFoto } from '../api'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, textoIdade } from '../rotulos'
import { useUltimoPedido } from '../useUltimoPedido'

const POR_PAGINA = 12

export function CartaoAnimal({ animal }) {
  return (
    <Link to={`/animais/${animal.id}`} className="animal">
      {animal.fotos?.[0]
        ? <img className="animal__foto animal__foto--img" src={urlFoto(animal.fotos[0].url)} alt="" loading="lazy" />
        : <div className="animal__foto" aria-hidden="true">{EMOJI_ESPECIE[animal.especie]}</div>}
      <h3>{animal.nome}</h3>
      <p>
        {ESPECIES[animal.especie]} · {PORTES[animal.porte]} · {SEXOS[animal.sexo]}
      </p>
      <p>{textoIdade(animal.idade_estimada_meses)}</p>
      <p>{animal.nome_abrigo}{animal.abrigo_verificado && <span className="etiqueta etiqueta--ok" style={{ marginLeft: '0.4rem' }}>Verificado</span>}</p>
    </Link>
  )
}

// RF-14: além de busca, espécie e porte, os filtros combinados (todos valem ao mesmo tempo).
const FILTROS_VAZIOS = {
  busca: '', especie: '', porte: '', sexo: '', idade: '', castrado: '', vacinado: '', convive_criancas: '', convive_animais: '',
}
const EXTRAS = ['sexo', 'idade', 'castrado', 'vacinado', 'convive_criancas', 'convive_animais']
const MARCAS = [['castrado', 'Castrado'], ['vacinado', 'Vacinado'], ['convive_criancas', 'Convive bem com crianças'], ['convive_animais', 'Convive bem com outros animais']]

export default function Catalogo() {
  const [params, setParams] = useSearchParams()
  const abrigoId = params.get('abrigo') || ''
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS)
  const [maisFiltros, setMaisFiltros] = useState(false)
  const extrasAtivos = EXTRAS.filter((k) => filtros[k]).length
  const [animais, setAnimais] = useState([])
  const [temMais, setTemMais] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')

  const novoPedido = useUltimoPedido()

  const buscar = useCallback(async (deslocamento) => {
    const atual = novoPedido()
    setCarregando(true)
    setErro('')
    const consulta = new URLSearchParams({ limite: POR_PAGINA, deslocamento })
    Object.entries(filtros).forEach(([k, v]) => v && consulta.set(k, v))
    if (abrigoId) consulta.set('abrigo_id', abrigoId)
    try {
      const lista = await api(`/animais?${consulta}`)
      if (!atual()) return // chegou depois de um pedido mais novo: descarta
      setAnimais((anteriores) => (deslocamento === 0 ? lista : [...anteriores, ...lista]))
      setTemMais(lista.length === POR_PAGINA)
    } catch (err) {
      if (atual()) setErro(err.message)
    } finally {
      if (atual()) setCarregando(false)
    }
  }, [filtros, abrigoId, novoPedido])

  // Refaz a busca a cada mudança de filtro (com uma pequena espera para não consultar a cada tecla).
  useEffect(() => {
    const espera = setTimeout(() => buscar(0), 250)
    return () => clearTimeout(espera)
  }, [buscar])

  const mudar = (nome) => (e) => setFiltros({ ...filtros, [nome]: e.target.value })
  const marcar = (nome) => (e) => setFiltros({ ...filtros, [nome]: e.target.checked ? 'true' : '' })

  return (
    <main className="pagina">
      {!abrigoId && (
        <section className="cartao chamada-reencontro" aria-labelledby="titulo-chamada">
          <div>
            <h2 id="titulo-chamada">🐾 Perdeu ou encontrou um animal?</h2>
            <p>Registre com fotos e local. Veja os animais perdidos e os avistados na rua perto de você.</p>
          </div>
          <div className="acoes">
            <Link className="botao" to="/perdi">Perdi meu animal</Link>
            <Link className="botao botao--leve" to="/encontrei">Encontrei um animal</Link>
            <Link className="botao botao--leve" to="/reencontro">Ver perdidos e achados</Link>
            <Link className="botao botao--leve" to="/mapa?ver=animais">Ver no mapa</Link>
          </div>
        </section>
      )}

      <h1>Animais para adoção</h1>
      <p className="subtitulo">Animais de abrigos e protetores. O selo Verificado indica que a administração confirmou o abrigo.</p>

      {abrigoId && (
        <div className="aviso aviso--atencao" role="status">
          Mostrando só os animais de {animais[0]?.nome_abrigo || 'um abrigo'}.{' '}
          <button className="botao botao--leve botao--pequeno" onClick={() => setParams({})}>Ver todos os abrigos</button>{' '}
          <Link className="botao botao--leve botao--pequeno" to={`/abrigos/${abrigoId}`}>Perfil do abrigo</Link>{' '}
          <Link to="/mapa">Voltar ao mapa</Link>
        </div>
      )}

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
        <div className="campo">
          <span className="campo__rotulo" aria-hidden="true">&nbsp;</span>
          <button type="button" className="botao botao--leve" aria-expanded={maisFiltros} aria-controls="mais-filtros" onClick={() => setMaisFiltros(!maisFiltros)}>
            Mais filtros{extrasAtivos ? ` (${extrasAtivos})` : ''}
          </button>
        </div>
      </div>
      {maisFiltros && (
        <div id="mais-filtros" className="cartao filtros filtros--extras" role="group" aria-label="Mais filtros">
          <div className="campo">
            <label htmlFor="sexo">Sexo</label>
            <select id="sexo" value={filtros.sexo} onChange={mudar('sexo')}>
              <option value="">Tanto faz</option>
              <option value="macho">Macho</option>
              <option value="femea">Fêmea</option>
            </select>
          </div>
          <div className="campo">
            <label htmlFor="idade">Idade</label>
            <select id="idade" value={filtros.idade} onChange={mudar('idade')}>
              <option value="">Qualquer idade</option>
              <option value="filhote">Filhote (até 1 ano)</option>
              <option value="adulto">Adulto (1 a 7 anos)</option>
              <option value="idoso">Idoso (8 anos ou mais)</option>
            </select>
          </div>
          {MARCAS.map(([chave, rotulo]) => (
            <label key={chave} className="marcar"><input type="checkbox" checked={filtros[chave] === 'true'} onChange={marcar(chave)} /> {rotulo}</label>
          ))}
          {extrasAtivos > 0 && (
            <button type="button" className="botao botao--leve botao--pequeno" onClick={() => setFiltros({ ...filtros, ...Object.fromEntries(EXTRAS.map((k) => [k, ''])) })}>Limpar estes filtros</button>
          )}
        </div>
      )}

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
