import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { TIPOS_REGISTRO, resumoCaracteristicas } from '../componentes/CartaoRegistro'
import { linkWhatsApp, textoData, textoKm } from '../rotulos'

// Mapa com abas acima dele (RF-07 a RF-09, protótipo da Sprint 2):
//   Abrigos                → o mapa e a lista lateral mostram os abrigos;
//   Perdidos e avistados   → o mapa e a lista mostram os animais, com filtro Perdidos / Avistados.
// OpenStreetMap (gratuito, sem chave de API). Centro padrão: Recife.
const RECIFE = [-8.0476, -34.877]
const RAIOS = [['', 'Qualquer distância'], ['5', 'Até 5 km'], ['10', 'Até 10 km'], ['25', 'Até 25 km']]
const COR = { verificado: '#2f7d3a', comum: '#c4541a', voce: '#2b6cb0' }

const ABAS = [
  { chave: 'abrigos', rotulo: 'Abrigos', icone: '🏠' },
  { chave: 'animais', rotulo: 'Perdidos e avistados', icone: '🐾' },
]
// Filtro dentro da aba de animais.
const TIPOS = [
  { chave: 'perdidos', tipo: 'perdido', rotulo: 'Perdidos', titulo: 'Animais perdidos' },
  { chave: 'avistamentos', tipo: 'avistamento', rotulo: 'Avistados', titulo: 'Animais avistados na rua' },
]

const texto = (n) => (n === 1 ? '1 animal disponível' : `${n} animais disponíveis`)

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
  // A aba e o filtro ficam na URL (/mapa?ver=animais&mostrar=perdidos), para dar para compartilhar o link.
  const aba = params.get('ver') === 'animais' ? 'animais' : 'abrigos'
  const mostrarParam = params.get('mostrar')
  const tiposAtivos = TIPOS.map((t) => t.chave).filter((c) => !mostrarParam || mostrarParam === c)
  const elementoMapa = useRef(null)
  const mapa = useRef(null)
  const camada = useRef(null)
  const marcadores = useRef(new Map())
  const [dados, setDados] = useState({ abrigos: [], perdidos: [], avistamentos: [] })
  const [posicao, setPosicao] = useState(null)
  const [raio, setRaio] = useState('')
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [avisoLocal, setAvisoLocal] = useState('')

  const ir = useCallback((caminho) => navegar(caminho), [navegar])

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

  // Busca só o que a aba mostra (com a distância, se a pessoa informou onde está).
  useEffect(() => {
    setCarregando(true)
    setErro('')
    const consulta = new URLSearchParams()
    if (posicao) {
      consulta.set('lat', posicao.lat)
      consulta.set('lng', posicao.lng)
      if (raio) consulta.set('raio_km', raio)
    }
    let busca
    if (aba === 'abrigos') {
      busca = api(`/abrigos${consulta.size ? `?${consulta}` : ''}`).then((abrigos) => ({ abrigos, perdidos: [], avistamentos: [] }))
    } else {
      consulta.set('limite', 100)
      busca = Promise.all([api(`/perdidos?${consulta}`), api(`/avistamentos?${consulta}`)])
        .then(([perdidos, avistamentos]) => ({ abrigos: [], perdidos, avistamentos }))
    }
    busca.then(setDados).catch((e) => setErro(e.message)).finally(() => setCarregando(false))
  }, [aba, posicao, raio])

  // Redesenha os marcadores da aba atual e ajusta o enquadramento.
  const chaveTipos = tiposAtivos.join(',')
  useEffect(() => {
    const m = mapa.current
    if (!m) return
    camada.current.clearLayers()
    marcadores.current = new Map()
    const pontos = []

    dados.abrigos.forEach((a) => {
      const marcador = L.circleMarker([a.latitude, a.longitude], { radius: 11, color: '#fff', weight: 2, fillColor: a.verificado ? COR.verificado : COR.comum, fillOpacity: 0.95 })
      marcador.bindPopup(() => caixaBalao(a.nome_abrigo, [
        a.verificado ? 'Abrigo verificado' : 'Abrigo não verificado', a.endereco, texto(a.animais_disponiveis),
        a.distancia_km != null && `A ${textoKm(a.distancia_km)} de você`,
      ], { texto: 'Ver animais deste abrigo', acao: () => ir(`/?abrigo=${a.id}`) }))
      marcador.bindTooltip(a.nome_abrigo)
      marcador.addTo(camada.current)
      marcadores.current.set(`abrigo-${a.id}`, marcador)
      pontos.push([a.latitude, a.longitude])
    })

    const ativos = chaveTipos.split(',')
    for (const { chave, tipo } of TIPOS) {
      if (!ativos.includes(chave)) continue
      const t = TIPOS_REGISTRO[tipo]
      dados[chave].forEach((r) => {
        // Losango: diferencia registro de abrigo também para quem não distingue cores.
        // O Leaflet posiciona o ícone pelo transform do próprio elemento; quem gira é o filho.
        const marcador = L.marker([r.latitude, r.longitude], {
          icon: L.divIcon({ className: `pino pino--${tipo}`, html: '<span class="pino__losango"></span>', iconSize: [20, 20], iconAnchor: [10, 10] }),
          title: t.titulo(r.especie),
        })
        marcador.bindPopup(() => caixaBalao(t.titulo(r.especie), [
          resumoCaracteristicas(r), `${t.rotuloData} ${textoData(r[t.campoData])}`, 'Local aproximado',
          r.distancia_km != null && `A ${textoKm(r.distancia_km)} de você`,
        ], { texto: 'Ver registro', acao: () => ir(`${t.caminhoTela}/${r.id}`) }))
        marcador.addTo(camada.current)
        marcadores.current.set(`${tipo}-${r.id}`, marcador)
        pontos.push([r.latitude, r.longitude])
      })
    }

    if (posicao) {
      L.circleMarker([posicao.lat, posicao.lng], { radius: 8, color: '#fff', weight: 2, fillColor: COR.voce, fillOpacity: 1 })
        .bindTooltip('Você está aqui').addTo(camada.current)
      pontos.push([posicao.lat, posicao.lng])
    }
    if (pontos.length > 1) m.fitBounds(pontos, { padding: [40, 40], maxZoom: 15 })
    else if (pontos.length === 1) m.setView(pontos[0], 14)
  }, [dados, posicao, ir, chaveTipos])

  function trocarAba(chave) {
    setParams(chave === 'animais' ? { ver: 'animais' } : {}, { replace: true })
  }

  // Liga/desliga Perdidos ou Avistados. Desligar o último religa os dois: mapa vazio não ajuda ninguém.
  function alternarTipo(chave) {
    const novos = tiposAtivos.includes(chave) ? tiposAtivos.filter((c) => c !== chave) : [...tiposAtivos, chave]
    const proximo = { ver: 'animais' }
    if (novos.length === 1) proximo.mostrar = novos[0]
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

  const registrosVisiveis = TIPOS.filter((t) => tiposAtivos.includes(t.chave)).reduce((n, t) => n + dados[t.chave].length, 0)
  const vazio = !carregando && !erro && (aba === 'abrigos' ? dados.abrigos.length === 0 : registrosVisiveis === 0)

  return (
    <main className="pagina">
      <h1>Mapa</h1>
      <p className="subtitulo">
        {aba === 'abrigos'
          ? 'Abrigos e protetores perto de você. Verde: abrigo verificado pela administração; laranja: ainda não verificado.'
          : 'Animais procurados pelos tutores e animais vistos na rua. O local é aproximado, para proteger quem registrou.'}
      </p>

      <div className="abas abas--mapa" role="tablist" aria-label="O que ver no mapa">
        {ABAS.map((a) => (
          <button
            key={a.chave} type="button" role="tab" id={`aba-${a.chave}`} aria-selected={aba === a.chave} aria-controls="painel-mapa"
            className={`abas__item${aba === a.chave ? ' abas__item--ativa' : ''}`} onClick={() => trocarAba(a.chave)}
          >
            <span aria-hidden="true">{a.icone}</span> {a.rotulo}
          </button>
        ))}
      </div>

      <div className="mapa-ferramentas">
        {aba === 'animais' && (
          <div className="camadas" role="group" aria-label="Mostrar no mapa">
            {TIPOS.map((t) => {
              const ligado = tiposAtivos.includes(t.chave)
              return (
                <button key={t.chave} type="button" className={`camada${ligado ? ' camada--ligada' : ''}`} aria-pressed={ligado} onClick={() => alternarTipo(t.chave)}>
                  <span className={`camada__marca camada__marca--${t.chave}`} aria-hidden="true" />
                  {t.rotulo}
                  {!carregando && <span className="camada__total">{dados[t.chave].length}</span>}
                </button>
              )
            })}
          </div>
        )}
        <div className="acoes">
          {posicao ? (
            <>
              <label className="sr-only" htmlFor="raio">Distância máxima</label>
              <select id="raio" value={raio} onChange={(e) => setRaio(e.target.value)} style={{ width: 'auto' }}>
                {RAIOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </select>
              <button className="botao botao--leve" onClick={() => { setPosicao(null); setRaio('') }}>Mostrar tudo</button>
            </>
          ) : (
            <button className="botao botao--leve" onClick={perto}>📍 Perto de mim</button>
          )}
          {aba === 'animais' && (
            <>
              <Link className="botao" to="/perdi">Perdi meu animal</Link>
              <Link className="botao botao--leve" to="/encontrei">Encontrei um animal</Link>
            </>
          )}
        </div>
      </div>

      {avisoLocal && <div className="aviso aviso--atencao" role="status">{avisoLocal}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

      <div className="duas-colunas" id="painel-mapa" role="tabpanel" aria-labelledby={`aba-${aba}`}>
        <div ref={elementoMapa} className="mapa" role="region" aria-label={aba === 'abrigos' ? 'Mapa dos abrigos' : 'Mapa dos animais perdidos e avistados'} />
        <div className="mapa-lista">
          {carregando && <p className="estado">Carregando…</p>}
          {vazio && (
            <p className="estado">
              {posicao && raio ? 'Nada nessa distância. Tente aumentar o raio.' : aba === 'abrigos' ? 'Nenhum abrigo cadastrado ainda.' : 'Nenhum animal perdido ou avistado registrado.'}
            </p>
          )}

          {aba === 'abrigos' && !carregando && (
            <ul className="lista-abrigos" aria-label="Abrigos">
              {dados.abrigos.map((a) => {
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
          )}

          {aba === 'animais' && !carregando && TIPOS.filter((t) => tiposAtivos.includes(t.chave) && dados[t.chave].length > 0).map(({ chave, tipo, titulo }) => {
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
