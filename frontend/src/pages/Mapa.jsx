import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { TIPOS_REGISTRO, resumoCaracteristicas } from '../componentes/CartaoRegistro'
import MenuFiltros from '../componentes/MenuFiltros'
import { ESPECIES, PORTES, linkWhatsApp, textoData, textoHaQuanto, textoKm } from '../rotulos'

// Mapa com abas acima dele (RF-07 a RF-09, protótipo da Sprint 2):
//   Abrigos                → o mapa e a lista lateral mostram os abrigos;
//   Perdidos e avistados   → o mapa e uma lista MISTA mostram os animais.
// Acima do mapa ficam só as abas (o mapa sobe). As opções ficam sobre a lista: "Perto de mim" e "Filtros".
// OpenStreetMap (gratuito, sem chave de API). Centro padrão: Recife.
const RECIFE = [-8.0476, -34.877]
const RAIOS = [['', 'Qualquer distância'], ['5', 'Até 5 km'], ['10', 'Até 10 km'], ['25', 'Até 25 km']]
const PERIODOS = [['', 'Qualquer data'], ['7', 'Últimos 7 dias'], ['30', 'Últimos 30 dias'], ['90', 'Últimos 3 meses']]
const COR = { verificado: '#2f7d3a', comum: '#c4541a', voce: '#2b6cb0' }

const ABAS = [
  { chave: 'abrigos', rotulo: 'Abrigos', icone: '🏠' },
  { chave: 'animais', rotulo: 'Perdidos e avistados', icone: '🐾' },
]
const TIPOS = [
  { chave: 'perdidos', tipo: 'perdido', rotulo: 'Perdidos' },
  { chave: 'avistamentos', tipo: 'avistamento', rotulo: 'Avistados' },
]
const FILTROS_ANIMAIS = { especie: '', porte: '', periodo: '' }
const FILTROS_ABRIGOS = { verificados: false, comAnimais: false }

const texto = (n) => (n === 1 ? '1 animal disponível' : `${n} animais disponíveis`)
const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`

// Data do registro (sumiu em / visto em) já está ≥ hoje − N dias?
function dentroDoPeriodo(r, dias) {
  if (!dias) return true
  const t = TIPOS_REGISTRO[r.tipo]
  const limite = new Date()
  limite.setDate(limite.getDate() - Number(dias))
  return String(r[t.campoData]).slice(0, 10) >= limite.toISOString().slice(0, 10)
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
  // A aba e o tipo ficam na URL (/mapa?ver=animais&mostrar=perdidos), para dar para compartilhar o link.
  const aba = params.get('ver') === 'animais' ? 'animais' : 'abrigos'
  const mostrarParam = params.get('mostrar')
  const tiposAtivos = TIPOS.map((t) => t.chave).filter((c) => !mostrarParam || mostrarParam === c)
  const elementoMapa = useRef(null)
  const mapa = useRef(null)
  const camada = useRef(null)
  const marcadores = useRef(new Map())
  const [dados, setDados] = useState({ abrigos: [], perdidos: [], avistamentos: [] })
  const [filtrosAnimais, setFiltrosAnimais] = useState(FILTROS_ANIMAIS)
  const [filtrosAbrigos, setFiltrosAbrigos] = useState(FILTROS_ABRIGOS)
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

  // Busca só o que a aba mostra. Espécie e porte são filtrados na API; o resto, aqui na tela.
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
      if (filtrosAnimais.especie) consulta.set('especie', filtrosAnimais.especie)
      if (filtrosAnimais.porte) consulta.set('porte', filtrosAnimais.porte)
      busca = Promise.all([api(`/perdidos?${consulta}`), api(`/avistamentos?${consulta}`)])
        .then(([perdidos, avistamentos]) => ({ abrigos: [], perdidos, avistamentos }))
    }
    let valido = true // vira false se a aba ou o filtro mudar antes da resposta (evita condição de corrida)
    busca
      .then((d) => valido && setDados(d))
      .catch((e) => valido && setErro(e.message))
      .finally(() => valido && setCarregando(false))
    return () => { valido = false }
  }, [aba, posicao, raio, filtrosAnimais.especie, filtrosAnimais.porte])

  const abrigos = useMemo(
    () => dados.abrigos.filter((a) => (!filtrosAbrigos.verificados || a.verificado) && (!filtrosAbrigos.comAnimais || a.animais_disponiveis > 0)),
    [dados.abrigos, filtrosAbrigos],
  )

  // Lista mista: perdidos e avistados juntos, do mais perto ao mais longe (com posição) ou do mais recente.
  const chaveTipos = tiposAtivos.join(',')
  const animais = useMemo(() => {
    const ativos = chaveTipos.split(',')
    const lista = TIPOS.filter((t) => ativos.includes(t.chave))
      .flatMap((t) => dados[t.chave].map((r) => ({ ...r, tipo: t.tipo })))
      .filter((r) => dentroDoPeriodo(r, filtrosAnimais.periodo))
    return lista.sort((a, b) => (a.distancia_km != null ? a.distancia_km - b.distancia_km : String(b.criado_em).localeCompare(String(a.criado_em))))
  }, [dados, chaveTipos, filtrosAnimais.periodo])
  const contagem = useMemo(() => {
    const c = {}
    for (const t of TIPOS) c[t.chave] = dados[t.chave].filter((r) => dentroDoPeriodo({ ...r, tipo: t.tipo }, filtrosAnimais.periodo)).length
    return c
  }, [dados, filtrosAnimais.periodo])

  // Redesenha os marcadores da aba atual e ajusta o enquadramento.
  useEffect(() => {
    const m = mapa.current
    if (!m) return
    camada.current.clearLayers()
    marcadores.current = new Map()
    const pontos = []

    abrigos.forEach((a) => {
      const marcador = L.circleMarker([a.latitude, a.longitude], { radius: 11, color: '#fff', weight: 2, fillColor: a.verificado ? COR.verificado : COR.comum, fillOpacity: 0.95 })
      marcador.bindPopup(() => caixaBalao(a.nome_abrigo, [
        a.verificado ? 'Abrigo verificado' : 'Abrigo não verificado', a.endereco, texto(a.animais_disponiveis),
        a.distancia_km != null && `A ${textoKm(a.distancia_km)} de você`,
      ], { texto: 'Ver perfil do abrigo', acao: () => ir(`/abrigos/${a.id}`) }))
      marcador.bindTooltip(a.nome_abrigo)
      marcador.addTo(camada.current)
      marcadores.current.set(`abrigo-${a.id}`, marcador)
      pontos.push([a.latitude, a.longitude])
    })

    animais.forEach((r) => {
      const t = TIPOS_REGISTRO[r.tipo]
      // Losango: diferencia registro de abrigo também para quem não distingue cores.
      // O Leaflet posiciona o ícone pelo transform do próprio elemento; quem gira é o filho.
      const marcador = L.marker([r.latitude, r.longitude], {
        icon: L.divIcon({ className: `pino pino--${r.tipo}`, html: '<span class="pino__losango"></span>', iconSize: [20, 20], iconAnchor: [10, 10] }),
        title: t.titulo(r.especie),
      })
      marcador.bindPopup(() => caixaBalao(t.titulo(r.especie), [
        resumoCaracteristicas(r), `${t.rotuloData} ${textoData(r[t.campoData])}`, 'Local aproximado',
        r.distancia_km != null && `A ${textoKm(r.distancia_km)} de você`,
      ], { texto: 'Ver registro', acao: () => ir(`${t.caminhoTela}/${r.id}`) }))
      marcador.addTo(camada.current)
      marcadores.current.set(`${r.tipo}-${r.id}`, marcador)
      pontos.push([r.latitude, r.longitude])
    })

    if (posicao) {
      L.circleMarker([posicao.lat, posicao.lng], { radius: 8, color: '#fff', weight: 2, fillColor: COR.voce, fillOpacity: 1 })
        .bindTooltip('Você está aqui').addTo(camada.current)
      pontos.push([posicao.lat, posicao.lng])
    }
    if (pontos.length > 1) m.fitBounds(pontos, { padding: [40, 40], maxZoom: 15 })
    else if (pontos.length === 1) m.setView(pontos[0], 14)
  }, [abrigos, animais, posicao, ir])

  function trocarAba(chave) {
    setParams(chave === 'animais' ? { ver: 'animais' } : {}, { replace: true })
  }

  // Liga/desliga Perdidos ou Avistados. Desligar o último religa os dois: lista vazia não ajuda ninguém.
  function alternarTipo(chave) {
    const novos = tiposAtivos.includes(chave) ? tiposAtivos.filter((c) => c !== chave) : [...tiposAtivos, chave]
    const proximo = { ver: 'animais' }
    if (novos.length === 1) proximo.mostrar = novos[0]
    setParams(proximo, { replace: true })
  }

  const mudarAnimais = (nome) => (e) => setFiltrosAnimais((f) => ({ ...f, [nome]: e.target.value }))
  const mudarAbrigos = (nome) => (e) => setFiltrosAbrigos((f) => ({ ...f, [nome]: e.target.checked }))
  const ativosAnimais = [filtrosAnimais.especie, filtrosAnimais.porte, filtrosAnimais.periodo, mostrarParam, raio].filter(Boolean).length
  const ativosAbrigos = [filtrosAbrigos.verificados, filtrosAbrigos.comAnimais, raio].filter(Boolean).length

  function limpar() {
    setRaio('')
    if (aba === 'abrigos') setFiltrosAbrigos(FILTROS_ABRIGOS)
    else {
      setFiltrosAnimais(FILTROS_ANIMAIS)
      setParams({ ver: 'animais' }, { replace: true })
    }
  }

  function perto() {
    setAvisoLocal('')
    if (posicao) { setPosicao(null); setRaio(''); return } // segundo clique desliga
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

  const total = aba === 'abrigos' ? abrigos.length : animais.length
  const ordem = posicao ? 'mais perto primeiro' : aba === 'animais' ? 'mais recentes primeiro' : ''

  const distancia = posicao && (
    <div className="campo">
      <label htmlFor="raio">Distância máxima</label>
      <select id="raio" value={raio} onChange={(e) => setRaio(e.target.value)}>
        {RAIOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
      </select>
    </div>
  )

  return (
    <main className="pagina">
      <h1>Mapa</h1>

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

      <div className="duas-colunas" id="painel-mapa" role="tabpanel" aria-labelledby={`aba-${aba}`}>
        <div ref={elementoMapa} className="mapa" role="region" aria-label={aba === 'abrigos' ? 'Mapa dos abrigos' : 'Mapa dos animais perdidos e avistados'} />

        <div className="mapa-coluna">
          {/* Barra da lista: resumo à esquerda; Perto de mim e Filtros no cantinho direito. */}
          <div className="mapa-barra">
            <p className="mapa-barra__resumo" aria-live="polite">
              {carregando ? 'Carregando…' : <strong>{aba === 'abrigos' ? plural(total, 'abrigo', 'abrigos') : plural(total, 'animal', 'animais')}</strong>}
              {!carregando && ordem && <small>{ordem}</small>}
            </p>
            <div className="mapa-barra__botoes">
              <button type="button" className={`botao botao--leve botao--pequeno${posicao ? ' menu-filtros__botao--ativo' : ''}`} onClick={perto} aria-pressed={Boolean(posicao)}>
                📍 Perto de mim
              </button>
              {aba === 'abrigos' ? (
                <MenuFiltros ativos={ativosAbrigos} aoLimpar={limpar}>
                  <label className="marcar"><input type="checkbox" checked={filtrosAbrigos.verificados} onChange={mudarAbrigos('verificados')} /> Só abrigos verificados</label>
                  <label className="marcar"><input type="checkbox" checked={filtrosAbrigos.comAnimais} onChange={mudarAbrigos('comAnimais')} /> Só com animais disponíveis</label>
                  {distancia}
                </MenuFiltros>
              ) : (
                <MenuFiltros ativos={ativosAnimais} aoLimpar={limpar}>
                  <fieldset className="campo">
                    <legend>Mostrar</legend>
                    {TIPOS.map((t) => (
                      <label key={t.chave} className="marcar">
                        <input type="checkbox" checked={tiposAtivos.includes(t.chave)} onChange={() => alternarTipo(t.chave)} />
                        <span className={`camada__marca camada__marca--${t.chave}`} aria-hidden="true" />
                        {t.rotulo} <small>({carregando ? '…' : contagem[t.chave]})</small>
                      </label>
                    ))}
                  </fieldset>
                  <div className="campo">
                    <label htmlFor="f-especie">Espécie</label>
                    <select id="f-especie" value={filtrosAnimais.especie} onChange={mudarAnimais('especie')}>
                      <option value="">Todas</option>
                      {Object.entries(ESPECIES).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                    </select>
                  </div>
                  <div className="campo">
                    <label htmlFor="f-porte">Porte</label>
                    <select id="f-porte" value={filtrosAnimais.porte} onChange={mudarAnimais('porte')}>
                      <option value="">Todos</option>
                      {Object.entries(PORTES).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                    </select>
                  </div>
                  <div className="campo">
                    <label htmlFor="f-periodo">Período</label>
                    <select id="f-periodo" value={filtrosAnimais.periodo} onChange={mudarAnimais('periodo')}>
                      {PERIODOS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                    </select>
                  </div>
                  {distancia}
                </MenuFiltros>
              )}
            </div>
          </div>

          {avisoLocal && <div className="aviso aviso--atencao" role="status">{avisoLocal}</div>}
          {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

          <div className="mapa-lista">
            {!carregando && !erro && total === 0 && (
              <p className="estado">
                {aba === 'abrigos' ? 'Nenhum abrigo com esses filtros.' : 'Nenhum animal com esses filtros.'} Tente limpar os filtros ou aumentar a distância.
              </p>
            )}

            {aba === 'abrigos' && !carregando && (
              <ul className="lista-abrigos" aria-label="Abrigos">
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
                        {a.distancia_km != null && <> · <strong>{textoKm(a.distancia_km)}</strong></>}
                      </p>
                      {a.horario_funcionamento && <p style={{ margin: '0 0 0.5rem' }}><small>Horário: {a.horario_funcionamento}</small></p>}
                      <div className="acoes">
                        <button className="botao botao--leve botao--pequeno" onClick={() => focar(`abrigo-${a.id}`, a.latitude, a.longitude)}>Ver no mapa</button>
                        <button className="botao botao--pequeno" onClick={() => ir(`/abrigos/${a.id}`)}>Ver abrigo</button>
                        {whats && <a className="botao botao--leve botao--pequeno" href={whats} target="_blank" rel="noreferrer">WhatsApp</a>}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}

            {aba === 'animais' && !carregando && animais.length > 0 && (
              <ul className="lista-abrigos" aria-label="Animais perdidos e avistados">
                {animais.map((r) => {
                  const t = TIPOS_REGISTRO[r.tipo]
                  return (
                    <li key={`${r.tipo}-${r.id}`} className="cartao registro-mini">
                      <span className={`camada__marca camada__marca--${r.tipo === 'perdido' ? 'perdidos' : 'avistamentos'}`} aria-hidden="true" />
                      <div>
                        <div className="registro-mini__topo">
                          <Link to={`${t.caminhoTela}/${r.id}`}><strong>{t.titulo(r.especie)}</strong></Link>
                          <span className={`etiqueta ${t.etiqueta[1]}`}>{t.etiqueta[0]}</span>
                        </div>
                        <p>{resumoCaracteristicas(r)}</p>
                        <p>
                          {t.rotuloData} {textoData(r[t.campoData])}
                          {r.distancia_km != null ? <> · <strong>{textoKm(r.distancia_km)}</strong></> : <> · publicado {textoHaQuanto(r.criado_em)}</>}
                        </p>
                      </div>
                      <button className="botao botao--leve botao--pequeno" onClick={() => focar(`${r.tipo}-${r.id}`, r.latitude, r.longitude)}>Ver no mapa</button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
