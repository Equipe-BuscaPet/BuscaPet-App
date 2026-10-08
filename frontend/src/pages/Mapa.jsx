import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { linkWhatsApp } from '../rotulos'

// Mapa de abrigos com OpenStreetMap (gratuito, sem chave de API). Centro padrão: Recife.
const RECIFE = [-8.0476, -34.877]
const RAIOS = [['', 'Qualquer distância'], ['5', 'Até 5 km'], ['10', 'Até 10 km'], ['25', 'Até 25 km']]
const COR_VERIFICADO = '#2f7d3a'
const COR_COMUM = '#c4541a'

const texto = (n) => (n === 1 ? '1 animal disponível' : `${n} animais disponíveis`)
const distancia = (km) => `${String(km).replace('.', ',')} km`

// O conteúdo do balão é montado com nós de texto (nunca HTML), porque o nome do abrigo é digitado por usuários.
function montarBalao(abrigo, aoVerAnimais) {
  const caixa = document.createElement('div')
  const titulo = document.createElement('strong')
  titulo.textContent = abrigo.nome_abrigo
  caixa.append(titulo)
  const linha = (conteudo) => { const p = document.createElement('div'); p.textContent = conteudo; caixa.append(p) }
  linha(abrigo.verificado ? 'Abrigo verificado' : 'Abrigo não verificado')
  linha(abrigo.endereco)
  linha(texto(abrigo.animais_disponiveis))
  if (abrigo.distancia_km != null) linha(`A ${distancia(abrigo.distancia_km)} de você`)
  const botao = document.createElement('button')
  botao.type = 'button'
  botao.className = 'botao botao--pequeno'
  botao.style.marginTop = '0.5rem'
  botao.textContent = 'Ver animais deste abrigo'
  botao.addEventListener('click', () => aoVerAnimais(abrigo.id))
  caixa.append(botao)
  return caixa
}

export default function Mapa() {
  const navegar = useNavigate()
  const elementoMapa = useRef(null)
  const mapa = useRef(null)
  const camada = useRef(null)
  const marcadores = useRef(new Map())
  const [abrigos, setAbrigos] = useState([])
  const [posicao, setPosicao] = useState(null)
  const [raio, setRaio] = useState('')
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [avisoLocal, setAvisoLocal] = useState('')

  const verAnimais = useCallback((id) => navegar(`/?abrigo=${id}`), [navegar])

  // Cria o mapa uma única vez.
  useEffect(() => {
    const m = L.map(elementoMapa.current, { scrollWheelZoom: false }).setView(RECIFE, 12)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(m)
    camada.current = L.layerGroup().addTo(m)
    mapa.current = m
    return () => { m.remove(); mapa.current = null }
  }, [])

  // Busca os abrigos (com a distância, se a pessoa informou onde está).
  useEffect(() => {
    setCarregando(true)
    setErro('')
    const params = new URLSearchParams()
    if (posicao) {
      params.set('lat', posicao.lat)
      params.set('lng', posicao.lng)
      if (raio) params.set('raio_km', raio)
    }
    api(`/abrigos${params.size ? `?${params}` : ''}`)
      .then(setAbrigos)
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false))
  }, [posicao, raio])

  // Redesenha os marcadores quando a lista muda e ajusta o enquadramento.
  useEffect(() => {
    const m = mapa.current
    if (!m) return
    camada.current.clearLayers()
    marcadores.current = new Map()
    const pontos = []
    abrigos.forEach((a) => {
      const cor = a.verificado ? COR_VERIFICADO : COR_COMUM
      const marcador = L.circleMarker([a.latitude, a.longitude], { radius: 11, color: '#fff', weight: 2, fillColor: cor, fillOpacity: 0.95 })
      marcador.bindPopup(() => montarBalao(a, verAnimais))
      marcador.bindTooltip(a.nome_abrigo)
      marcador.addTo(camada.current)
      marcadores.current.set(a.id, marcador)
      pontos.push([a.latitude, a.longitude])
    })
    if (posicao) {
      L.circleMarker([posicao.lat, posicao.lng], { radius: 8, color: '#fff', weight: 2, fillColor: '#2b6cb0', fillOpacity: 1 })
        .bindTooltip('Você está aqui').addTo(camada.current)
      pontos.push([posicao.lat, posicao.lng])
    }
    if (pontos.length > 1) m.fitBounds(pontos, { padding: [40, 40], maxZoom: 15 })
    else if (pontos.length === 1) m.setView(pontos[0], 14)
  }, [abrigos, posicao, verAnimais])

  function perto() {
    setAvisoLocal('')
    if (!navigator.geolocation) return setAvisoLocal('Seu navegador não oferece localização. O mapa continua mostrando todos os abrigos.')
    navigator.geolocation.getCurrentPosition(
      (p) => setPosicao({ lat: Number(p.coords.latitude.toFixed(5)), lng: Number(p.coords.longitude.toFixed(5)) }),
      () => setAvisoLocal('Não foi possível obter sua localização. Verifique a permissão do navegador; enquanto isso o mapa mostra todos os abrigos.'),
      { timeout: 10000 },
    )
  }

  function limparLocal() {
    setPosicao(null)
    setRaio('')
  }

  function focar(a) {
    mapa.current.setView([a.latitude, a.longitude], 15)
    marcadores.current.get(a.id)?.openPopup()
    elementoMapa.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <main className="pagina">
      <h1>Mapa de abrigos</h1>
      <p className="subtitulo">Encontre abrigos e protetores perto de você. <span style={{ color: COR_VERIFICADO }}>●</span> verificado · <span style={{ color: COR_COMUM }}>●</span> ainda não verificado</p>

      <div className="acoes" style={{ marginBottom: '1rem' }}>
        {posicao ? (
          <>
            <div className="campo" style={{ minWidth: 190 }}>
              <label htmlFor="raio">Distância máxima</label>
              <select id="raio" value={raio} onChange={(e) => setRaio(e.target.value)}>
                {RAIOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </select>
            </div>
            <button className="botao botao--leve" onClick={limparLocal} style={{ alignSelf: 'flex-end' }}>Mostrar todos</button>
          </>
        ) : (
          <button className="botao" onClick={perto}>Abrigos perto de mim</button>
        )}
      </div>

      {avisoLocal && <div className="aviso aviso--atencao" role="status">{avisoLocal}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

      <div className="duas-colunas">
        <div ref={elementoMapa} className="mapa" role="region" aria-label="Mapa com a localização dos abrigos" />
        <div>
          {carregando && <p className="estado">Carregando…</p>}
          {!carregando && !erro && abrigos.length === 0 && (
            <p className="estado">{posicao && raio ? 'Nenhum abrigo nessa distância. Tente aumentar o raio.' : 'Nenhum abrigo cadastrado ainda.'}</p>
          )}
          <ul className="lista-abrigos">
            {abrigos.map((a) => {
              const whats = linkWhatsApp(a.telefone)
              return (
                <li key={a.id} className="cartao" data-abrigo={a.id}>
                  <div className="topo-pagina" style={{ marginBottom: '0.25rem' }}>
                    <h2 style={{ marginBottom: 0, fontSize: '1.05rem' }}>{a.nome_abrigo}</h2>
                    <span className={`etiqueta ${a.verificado ? 'etiqueta--ok' : 'etiqueta--atencao'}`}>{a.verificado ? 'Verificado' : 'Não verificado'}</span>
                  </div>
                  <p style={{ margin: '0 0 0.25rem' }}>{a.endereco}</p>
                  <p style={{ margin: '0 0 0.5rem' }}>
                    {texto(a.animais_disponiveis)}
                    {a.distancia_km != null && <> · <strong>{distancia(a.distancia_km)}</strong></>}
                  </p>
                  {a.horario_funcionamento && <p style={{ margin: '0 0 0.5rem' }}><small>Horário: {a.horario_funcionamento}</small></p>}
                  <div className="acoes">
                    <button className="botao botao--leve botao--pequeno" onClick={() => focar(a)}>Ver no mapa</button>
                    <button className="botao botao--pequeno" onClick={() => verAnimais(a.id)}>Ver animais</button>
                    {whats && <a className="botao botao--leve botao--pequeno" href={whats} target="_blank" rel="noreferrer">WhatsApp</a>}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </main>
  )
}
