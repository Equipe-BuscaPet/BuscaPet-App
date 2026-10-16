import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { TIPOS_REGISTRO, resumoCaracteristicas } from '../componentes/CartaoRegistro'
import { linkWhatsApp, textoData, textoKm } from '../rotulos'

// Mapa com camadas alternáveis (RF-07/08): abrigos, animais perdidos e animais avistados na rua.
// OpenStreetMap (gratuito, sem chave de API). Centro padrão: Recife.
const RECIFE = [-8.0476, -34.877]
const RAIOS = [['', 'Qualquer distância'], ['5', 'Até 5 km'], ['10', 'Até 10 km'], ['25', 'Até 25 km']]
const COR = {
  verificado: '#2f7d3a',
  comum: '#c4541a',
  perdido: '#c0262d',
  avistamento: '#7b3fa0',
  voce: '#2b6cb0',
}

const CAMADAS = [
  { chave: 'abrigos', rotulo: 'Abrigos', cor: COR.verificado },
  { chave: 'perdidos', rotulo: 'Perdidos', cor: COR.perdido, tipo: 'perdido' },
  { chave: 'avistamentos', rotulo: 'Avistados', cor: COR.avistamento, tipo: 'avistamento' },
]
const TODAS = CAMADAS.map((c) => c.chave)

const texto = (n) => (n === 1 ? '1 animal disponível' : `${n} animais disponíveis`)

// Camadas ligadas vêm da URL (?camadas=perdidos,avistamentos), para dar para compartilhar o link do mapa.
function lerCamadas(params) {
  const lista = (params.get('camadas') || '').split(',').filter((c) => TODAS.includes(c))
  return lista.length ? lista : TODAS
}

// Balões montados com nós de texto (nunca HTML), porque os textos são digitados por usuários.
function caixaBalao(titulo, linhas, botao) {
  const caixa = document.createElement('div')
  const forte = document.createElement('strong')
  forte.textContent = titulo
  caixa.append(forte)
  linhas.filter(Boolean).forEach((conteudo) => {
    const p = document.createElement('div')
    p.textContent = conteudo
    caixa.append(p)
  })
  const b = document.createElement('button')
  b.type = 'button'
  b.className = 'botao botao--pequeno'
  b.style.marginTop = '0.5rem'
  b.textContent = botao.texto
  b.addEventListener('click', botao.acao)
  caixa.append(b)
  return caixa
}

export default function Mapa() {
  const navegar = useNavigate()
  const [params, setParams] = useSearchParams()
  const camadasAtivas = lerCamadas(params)
  const elementoMapa = useRef(null)
  const mapa = useRef(null)
  const grupos = useRef({})
  const marcadores = useRef(new Map())
  const [dados, setDados] = useState({ abrigos: [], perdidos: [], avistamentos: [] })
  const [posicao, setPosicao] = useState(null)
  const [raio, setRaio] = useState('')
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [avisoLocal, setAvisoLocal] = useState('')

  const ir = useCallback((caminho) => navegar(caminho), [navegar])

  // Cria o mapa e um grupo de marcadores por camada, uma única vez.
  useEffect(() => {
    const m = L.map(elementoMapa.current, { scrollWheelZoom: false }).setView(RECIFE, 12)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(m)
    grupos.current = { abrigos: L.layerGroup(), perdidos: L.layerGroup(), avistamentos: L.layerGroup(), voce: L.layerGroup().addTo(m) }
    mapa.current = m
    return () => { m.remove(); mapa.current = null }
  }, [])

  // Busca as três bases (com a distância, se a pessoa informou onde está). Camada desligada não é consultada.
  const chaveCamadas = camadasAtivas.join(',')
  useEffect(() => {
    setCarregando(true)
    setErro('')
    const consulta = new URLSearchParams()
    if (posicao) {
      consulta.set('lat', posicao.lat)
      consulta.set('lng', posicao.lng)
      if (raio) consulta.set('raio_km', raio)
    }
    const sufixo = consulta.size ? `?${consulta}` : ''
    const ativas = chaveCamadas.split(',')
    const registros = new URLSearchParams(consulta)
    registros.set('limite', 100)
    Promise.all([
      ativas.includes('abrigos') ? api(`/abrigos${sufixo}`) : [],
      ativas.includes('perdidos') ? api(`/perdidos?${registros}`) : [],
      ativas.includes('avistamentos') ? api(`/avistamentos?${registros}`) : [],
    ])
      .then(([abrigos, perdidos, avistamentos]) => setDados({ abrigos, perdidos, avistamentos }))
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false))
  }, [posicao, raio, chaveCamadas])

  // Redesenha os marcadores e ajusta o enquadramento.
  useEffect(() => {
    const m = mapa.current
    if (!m) return
    Object.values(grupos.current).forEach((g) => g.clearLayers())
    marcadores.current = new Map()
    const pontos = []

    dados.abrigos.forEach((a) => {
      const marcador = L.circleMarker([a.latitude, a.longitude], { radius: 11, color: '#fff', weight: 2, fillColor: a.verificado ? COR.verificado : COR.comum, fillOpacity: 0.95 })
      marcador.bindPopup(() => caixaBalao(a.nome_abrigo, [
        a.verificado ? 'Abrigo verificado' : 'Abrigo não verificado', a.endereco, texto(a.animais_disponiveis),
        a.distancia_km != null && `A ${textoKm(a.distancia_km)} de você`,
      ], { texto: 'Ver animais deste abrigo', acao: () => ir(`/?abrigo=${a.id}`) }))
      marcador.bindTooltip(a.nome_abrigo)
      marcador.addTo(grupos.current.abrigos)
      marcadores.current.set(`abrigo-${a.id}`, marcador)
      pontos.push([a.latitude, a.longitude])
    })

    for (const [chave, tipo] of [['perdidos', 'perdido'], ['avistamentos', 'avistamento']]) {
      const t = TIPOS_REGISTRO[tipo]
      dados[chave].forEach((r) => {
        // Losango: diferencia registro de abrigo também para quem não distingue cores.
        const marcador = L.marker([r.latitude, r.longitude], {
          // O Leaflet posiciona o ícone pelo transform do próprio elemento; quem gira é o filho.
          icon: L.divIcon({ className: `pino pino--${tipo}`, html: '<span class="pino__losango"></span>', iconSize: [20, 20], iconAnchor: [10, 10] }),
          title: t.titulo(r.especie),
        })
        marcador.bindPopup(() => caixaBalao(t.titulo(r.especie), [
          resumoCaracteristicas(r), `${t.rotuloData} ${textoData(r[t.campoData])}`, 'Local aproximado',
          r.distancia_km != null && `A ${textoKm(r.distancia_km)} de você`,
        ], { texto: 'Ver registro', acao: () => ir(`${t.caminhoTela}/${r.id}`) }))
        marcador.addTo(grupos.current[chave])
        marcadores.current.set(`${tipo}-${r.id}`, marcador)
        pontos.push([r.latitude, r.longitude])
      })
    }

    if (posicao) {
      L.circleMarker([posicao.lat, posicao.lng], { radius: 8, color: '#fff', weight: 2, fillColor: COR.voce, fillOpacity: 1 })
        .bindTooltip('Você está aqui').addTo(grupos.current.voce)
      pontos.push([posicao.lat, posicao.lng])
    }
    if (pontos.length > 1) m.fitBounds(pontos, { padding: [40, 40], maxZoom: 15 })
    else if (pontos.length === 1) m.setView(pontos[0], 14)
  }, [dados, posicao, ir])

  // Liga e desliga as camadas no mapa conforme a URL.
  useEffect(() => {
    const m = mapa.current
    if (!m) return
    const ativas = chaveCamadas.split(',')
    for (const c of TODAS) {
      const grupo = grupos.current[c]
      if (ativas.includes(c)) grupo.addTo(m)
      else grupo.remove()
    }
  }, [chaveCamadas])

  function alternar(chave) {
    const novas = camadasAtivas.includes(chave) ? camadasAtivas.filter((c) => c !== chave) : [...camadasAtivas, chave]
    const proximo = new URLSearchParams(params)
    if (novas.length === 0 || novas.length === TODAS.length) proximo.delete('camadas')
    else proximo.set('camadas', novas.join(','))
    // Desligar a última camada religa todas: mapa vazio não ajuda ninguém.
    setParams(proximo, { replace: true })
  }

  function perto() {
    setAvisoLocal('')
    if (!navigator.geolocation) return setAvisoLocal('Seu navegador não oferece localização. O mapa continua mostrando tudo.')
    navigator.geolocation.getCurrentPosition(
      (p) => setPosicao({ lat: Number(p.coords.latitude.toFixed(5)), lng: Number(p.coords.longitude.toFixed(5)) }),
      () => setAvisoLocal('Não foi possível obter sua localização. Verifique a permissão do navegador; enquanto isso o mapa mostra tudo.'),
      { timeout: 10000 },
    )
  }

  function focar(chave, lat, lng) {
    mapa.current.setView([lat, lng], 15)
    marcadores.current.get(chave)?.openPopup()
    elementoMapa.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const contagem = { abrigos: dados.abrigos.length, perdidos: dados.perdidos.length, avistamentos: dados.avistamentos.length }
  const nada = !carregando && !erro && camadasAtivas.every((c) => contagem[c] === 0)

  return (
    <main className="pagina">
      <h1>Mapa</h1>
      <p className="subtitulo">
        Abrigos, animais perdidos e animais vistos na rua. Os perdidos e avistados aparecem em local aproximado, para proteger quem registrou.
      </p>

      <div className="camadas" role="group" aria-label="Camadas do mapa">
        {CAMADAS.map((c) => {
          const ligada = camadasAtivas.includes(c.chave)
          return (
            <button key={c.chave} type="button" className={`camada${ligada ? ' camada--ligada' : ''}`} aria-pressed={ligada} onClick={() => alternar(c.chave)}>
              <span className={`camada__marca camada__marca--${c.chave}`} style={{ '--cor': c.cor }} aria-hidden="true" />
              {c.rotulo}
              {ligada && !carregando && <span className="camada__total">{contagem[c.chave]}</span>}
            </button>
          )
        })}
      </div>

      <div className="acoes" style={{ marginBottom: '1rem' }}>
        {posicao ? (
          <>
            <div className="campo" style={{ minWidth: 190 }}>
              <label htmlFor="raio">Distância máxima</label>
              <select id="raio" value={raio} onChange={(e) => setRaio(e.target.value)}>
                {RAIOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </select>
            </div>
            <button className="botao botao--leve" onClick={() => { setPosicao(null); setRaio('') }} style={{ alignSelf: 'flex-end' }}>Mostrar tudo</button>
          </>
        ) : (
          <button className="botao" onClick={perto}>📍 Perto de mim</button>
        )}
        <Link className="botao botao--leve" to="/perdi">Perdi meu animal</Link>
        <Link className="botao botao--leve" to="/encontrei">Encontrei um animal</Link>
      </div>

      {avisoLocal && <div className="aviso aviso--atencao" role="status">{avisoLocal}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

      <div className="duas-colunas">
        <div ref={elementoMapa} className="mapa" role="region" aria-label="Mapa com abrigos, animais perdidos e avistados" />
        <div className="mapa-lista">
          {carregando && <p className="estado">Carregando…</p>}
          {nada && <p className="estado">{posicao && raio ? 'Nada nessa distância. Tente aumentar o raio.' : 'Nada para mostrar nas camadas escolhidas.'}</p>}

          {camadasAtivas.includes('abrigos') && dados.abrigos.length > 0 && (
            <section aria-labelledby="titulo-abrigos" className="mapa-secao">
              <h2 id="titulo-abrigos" className="mapa-secao__titulo">Abrigos</h2>
              <ul className="lista-abrigos">
                {dados.abrigos.map((a) => {
                  const whats = linkWhatsApp(a.telefone)
                  return (
                    <li key={a.id} className="cartao" data-abrigo={a.id}>
                      <div className="topo-pagina" style={{ marginBottom: '0.25rem' }}>
                        <h3 style={{ marginBottom: 0, fontSize: '1.05rem' }}>{a.nome_abrigo}</h3>
                        <span className={`etiqueta ${a.verificado ? 'etiqueta--ok' : 'etiqueta--atencao'}`}>{a.verificado ? 'Verificado' : 'Não verificado'}</span>
                      </div>
                      <p style={{ margin: '0 0 0.25rem' }}>{a.endereco}</p>
                      <p style={{ margin: '0 0 0.5rem' }}>
                        {texto(a.animais_disponiveis)}
                        {a.distancia_km != null && <> · <strong>{textoKm(a.distancia_km)}</strong></>}
                      </p>
                      {a.horario_funcionamento && <p style={{ margin: '0 0 0.5rem' }}><small>Horário: {a.horario_funcionamento}</small></p>}
                      <div className="acoes">
                        <button className="botao botao--leve botao--pequeno" onClick={() => focar(`abrigo-${a.id}`, a.latitude, a.longitude)}>Ver no mapa</button>
                        <button className="botao botao--pequeno" onClick={() => ir(`/?abrigo=${a.id}`)}>Ver animais</button>
                        {whats && <a className="botao botao--leve botao--pequeno" href={whats} target="_blank" rel="noreferrer">WhatsApp</a>}
                      </div>
                    </li>
                  )
                })}
              </ul>
            </section>
          )}

          {[['perdidos', 'perdido', 'Animais perdidos'], ['avistamentos', 'avistamento', 'Animais avistados na rua']].map(([chave, tipo, titulo]) => {
            if (!camadasAtivas.includes(chave) || dados[chave].length === 0) return null
            const t = TIPOS_REGISTRO[tipo]
            return (
              <section key={chave} aria-labelledby={`titulo-${chave}`} className="mapa-secao">
                <h2 id={`titulo-${chave}`} className="mapa-secao__titulo">{titulo}</h2>
                <ul className="lista-abrigos">
                  {dados[chave].map((r) => (
                    <li key={r.id} className="cartao registro-mini">
                      <span className={`camada__marca camada__marca--${chave}`} aria-hidden="true" />
                      <div>
                        <Link to={`${t.caminhoTela}/${r.id}`}><strong>{t.titulo(r.especie)}</strong></Link>
                        <p>{resumoCaracteristicas(r)}</p>
                        <p>
                          {t.rotuloData} {textoData(r[t.campoData])}
                          {r.distancia_km != null && <> · <strong>{textoKm(r.distancia_km)}</strong></>}
                        </p>
                      </div>
                      <button className="botao botao--leve botao--pequeno" onClick={() => focar(`${tipo}-${r.id}`, r.latitude, r.longitude)}>Ver no mapa</button>
                    </li>
                  ))}
                </ul>
              </section>
            )
          })}
        </div>
      </div>
    </main>
  )
}
