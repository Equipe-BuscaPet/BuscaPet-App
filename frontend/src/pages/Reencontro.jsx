import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import CartaoRegistro, { TIPOS_REGISTRO } from '../componentes/CartaoRegistro'
import { ESPECIES, PORTES } from '../rotulos'

// Vitrine pública do reencontro: animais perdidos (RF-19) e avistados na rua (RF-20).
const POR_PAGINA = 12
const ABAS = [['perdido', 'Perdidos'], ['avistamento', 'Avistados na rua']]
const RAIOS = [['', 'Qualquer distância'], ['2', 'Até 2 km'], ['5', 'Até 5 km'], ['10', 'Até 10 km'], ['25', 'Até 25 km']]

export default function Reencontro() {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') === 'avistamento' ? 'avistamento' : 'perdido'
  const [filtros, setFiltros] = useState({ especie: '', porte: '', raio_km: '' })
  const [posicao, setPosicao] = useState(null)
  const [registros, setRegistros] = useState([])
  const [temMais, setTemMais] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [avisoLocal, setAvisoLocal] = useState('')

  const buscar = useCallback(async (deslocamento) => {
    setCarregando(true)
    setErro('')
    const consulta = new URLSearchParams({ limite: POR_PAGINA, deslocamento })
    if (filtros.especie) consulta.set('especie', filtros.especie)
    if (filtros.porte) consulta.set('porte', filtros.porte)
    if (posicao) {
      consulta.set('lat', posicao.lat)
      consulta.set('lng', posicao.lng)
      if (filtros.raio_km) consulta.set('raio_km', filtros.raio_km)
    }
    try {
      const lista = await api(`${TIPOS_REGISTRO[aba].caminhoApi}?${consulta}`)
      setRegistros((atual) => (deslocamento === 0 ? lista : [...atual, ...lista]))
      setTemMais(lista.length === POR_PAGINA)
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }, [aba, filtros, posicao])

  useEffect(() => { setRegistros([]) }, [aba]) // não mostra cartões de uma aba com o formato da outra
  useEffect(() => { buscar(0) }, [buscar])

  const mudar = (nome) => (e) => setFiltros({ ...filtros, [nome]: e.target.value })

  function perto() {
    setAvisoLocal('')
    if (!navigator.geolocation) return setAvisoLocal('Seu navegador não oferece localização.')
    navigator.geolocation.getCurrentPosition(
      (p) => setPosicao({ lat: Number(p.coords.latitude.toFixed(5)), lng: Number(p.coords.longitude.toFixed(5)) }),
      () => setAvisoLocal('Não foi possível obter sua localização. Verifique a permissão do navegador.'),
      { timeout: 10000 },
    )
  }

  return (
    <main className="pagina">
      <div className="topo-pagina">
        <div>
          <h1>Perdidos e achados</h1>
          <p className="subtitulo" style={{ marginBottom: 0 }}>
            Animais procurados pelos tutores e animais vistos na rua. A localização exibida é aproximada, para proteger quem registrou.
          </p>
        </div>
        <div className="acoes">
          <Link className="botao" to="/perdi">Perdi meu animal</Link>
          <Link className="botao botao--leve" to="/encontrei">Encontrei um animal</Link>
        </div>
      </div>

      <div className="abas" role="tablist" aria-label="Tipo de registro">
        {ABAS.map(([valor, rotulo]) => (
          <button
            key={valor} type="button" role="tab" aria-selected={aba === valor}
            className={`abas__item${aba === valor ? ' abas__item--ativa' : ''}`}
            onClick={() => setParams(valor === 'perdido' ? {} : { aba: valor })}
          >
            {rotulo}
          </button>
        ))}
      </div>

      <div className="filtros" role="search">
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
        {posicao ? (
          <div className="campo">
            <label htmlFor="raio">Distância de você</label>
            <div className="acoes" style={{ flexWrap: 'nowrap' }}>
              <select id="raio" value={filtros.raio_km} onChange={mudar('raio_km')}>
                {RAIOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </select>
              <button type="button" className="botao botao--leve botao--pequeno" onClick={() => { setPosicao(null); setFiltros({ ...filtros, raio_km: '' }) }}>
                Limpar
              </button>
            </div>
          </div>
        ) : (
          <div className="campo" style={{ alignSelf: 'end' }}>
            <button type="button" className="botao botao--leve" onClick={perto}>📍 Perto de mim</button>
          </div>
        )}
      </div>

      {avisoLocal && <div className="aviso aviso--atencao" role="status">{avisoLocal}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!erro && !carregando && registros.length === 0 && (
        <p className="estado">
          {aba === 'perdido' ? 'Nenhum animal perdido com esses filtros.' : 'Nenhum avistamento com esses filtros.'}
          {posicao && filtros.raio_km && ' Tente aumentar a distância.'}
        </p>
      )}
      <div className="grade-animais" role="tabpanel">
        {registros.map((r) => <CartaoRegistro key={r.id} registro={r} tipo={aba} />)}
      </div>
      {carregando && <p className="estado">Carregando…</p>}
      {!carregando && temMais && (
        <p className="estado"><button className="botao botao--leve" onClick={() => buscar(registros.length)}>Ver mais</button></p>
      )}
    </main>
  )
}
