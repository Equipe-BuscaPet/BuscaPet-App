import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, hojeISO, textoData } from '../rotulos'
import CartaoRegistro, { TIPOS_REGISTRO } from './CartaoRegistro'
import SeletorFotos, { usePrevias } from './SeletorFotos'
import SeletorLocal from './SeletorLocal'

// Assistente em etapas do reencontro (protótipo da Sprint 2, escopo §4.2), usado por
// "Perdi meu animal" (RF-19) e "Encontrei um animal" (RF-20).
// O visitante preenche tudo e só precisa entrar na hora de publicar, sem perder o que já fez.

const ETAPAS = ['Fotos', 'Características', 'Local e data', 'Revisar', 'Resultados']
const REVISAR = 3
const RESULTADOS = 4

// Em que etapa fica cada campo, para levar a pessoa direto ao erro que a API apontar.
const ETAPA_DO_CAMPO = {
  fotos: 0, especie: 1, porte: 1, sexo: 1, cor_predominante: 1, pelagem: 1, sinais_particulares: 1,
  latitude: 2, longitude: 2, data_desaparecimento: 2, data_avistamento: 2, raio_busca_km: 2,
}

const DESCRICAO_PORTE = { pequeno: 'até uns 10 kg', medio: 'de 10 a 25 kg', grande: 'mais de 25 kg' }
const CORES = ['Preto', 'Branco', 'Caramelo', 'Marrom', 'Cinza', 'Preto e branco', 'Tricolor', 'Rajado', 'Amarelo']
const PELAGENS = ['Curta', 'Média', 'Longa', 'Encaracolada', 'Sem pelo']
const RAIOS = [2, 5, 10, 20, 50]

const TEXTOS = {
  perdido: {
    titulo: 'Perdi meu animal',
    intro: 'Registre o seu animal para que quem o encontrar possa reconhecê-lo. Quanto mais detalhes, maiores as chances.',
    rotuloLocal: 'Onde ele foi visto pela última vez?',
    rotuloData: 'Quando ele sumiu?',
    privacidade: 'No site aparece só a região aproximada (cerca de 1 km), nunca o ponto exato nem os seus dados.',
    publicar: 'Publicar animal perdido',
    publicado: 'Pronto! O seu animal está registrado como perdido.',
    tituloResultados: 'Avistamentos perto de onde ele sumiu',
    vazio: 'Ainda não há avistamentos desta espécie nessa região. Assim que a busca salva estiver ativa, avisaremos quando aparecer um.',
    contaExigida: 'tutor',
  },
  avistamento: {
    titulo: 'Encontrei um animal',
    intro: 'Viu um animal que parece perdido? Registre onde e quando, com fotos. O tutor que estiver procurando pode reconhecê-lo.',
    rotuloLocal: 'Onde você viu o animal?',
    rotuloData: 'Quando você o viu?',
    privacidade: 'O local aparece com precisão de cerca de 100 m (para quem procura saber a rua). Os seus dados não aparecem.',
    publicar: 'Publicar avistamento',
    publicado: 'Obrigado! O avistamento foi registrado.',
    tituloResultados: 'Animais perdidos perto daqui',
    vazio: 'Nenhum animal desta espécie foi registrado como perdido nessa região até agora.',
    contaExigida: null,
  },
}

const DADOS_INICIAIS = {
  especie: '', porte: '', sexo: 'indefinido', cor_predominante: '', pelagem: '', sinais_particulares: '',
  data: '', raio_busca_km: '5',
}

function validar(etapa, dados, fotos, local) {
  const e = {}
  if (etapa === 0 && fotos.length === 0) e.fotos = 'Escolha pelo menos uma foto do animal.'
  if (etapa === 1) {
    if (!dados.especie) e.especie = 'Escolha a espécie.'
    if (!dados.porte) e.porte = 'Escolha o porte.'
    if (dados.cor_predominante.trim().length < 2) e.cor_predominante = 'Informe a cor (ex.: caramelo).'
  }
  if (etapa === 2) {
    if (!local) e.local = 'Marque o local no mapa.'
    if (!dados.data) e.data = 'Informe a data.'
    else if (dados.data > hojeISO()) e.data = 'A data não pode estar no futuro.'
  }
  return e
}

function LoginRapido() {
  const { entrar } = useAuth()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      await entrar(email, senha)
    } catch (err) {
      setErro(err.message)
      setEnviando(false)
    }
  }

  return (
    <form className="cartao formulario" onSubmit={enviar} aria-labelledby="titulo-login-rapido">
      <div>
        <h2 id="titulo-login-rapido">Entre para publicar</h2>
        <p className="subtitulo" style={{ margin: 0 }}>
          O que você preencheu fica guardado aqui. Ainda não tem conta?{' '}
          <a href="/cadastro" target="_blank" rel="noreferrer">Cadastre-se em outra aba</a> e volte para entrar.
        </p>
      </div>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      <div className="grade-campos">
        <div className="campo">
          <label htmlFor="lr-email">E-mail</label>
          <input id="lr-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="lr-senha">Senha</label>
          <input id="lr-senha" type="password" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
        </div>
      </div>
      <div><button className="botao" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button></div>
    </form>
  )
}

function MiniaturasRevisao({ fotos }) {
  const previas = usePrevias(fotos)
  return (
    <ul className="miniaturas" aria-label="Fotos">
      {previas.map((u, i) => <li key={u} className="miniatura"><img src={u} alt={`Foto ${i + 1}`} /></li>)}
    </ul>
  )
}

function Opcoes({ nome, opcoes, valor, aoMudar, erro, colunas }) {
  return (
    <div className="opcoes-tipo" style={colunas ? { gridTemplateColumns: `repeat(auto-fit, minmax(${colunas}px, 1fr))` } : undefined}>
      {opcoes.map(([v, titulo, detalhe]) => (
        <label key={v} className="opcao-tipo">
          <input type="radio" name={nome} value={v} checked={valor === v} onChange={() => aoMudar(v)} aria-invalid={Boolean(erro)} />
          <strong>{titulo}</strong>
          {detalhe && <span>{detalhe}</span>}
        </label>
      ))}
    </div>
  )
}

export default function AssistenteRegistro({ tipo }) {
  const t = TIPOS_REGISTRO[tipo]
  const textos = TEXTOS[tipo]
  const { usuario } = useAuth()
  const [etapa, setEtapa] = useState(0)
  const [fotos, setFotos] = useState([])
  const [dados, setDados] = useState(DADOS_INICIAIS)
  const [local, setLocal] = useState(null)
  const [erros, setErros] = useState({})
  const [erroGeral, setErroGeral] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [publicado, setPublicado] = useState(null)
  const [proximos, setProximos] = useState(null)
  const titulo = useRef(null)
  const etapaAnterior = useRef(0)

  const contaBloqueada = usuario && textos.contaExigida && usuario.tipo_conta !== textos.contaExigida
  const mudar = (campo) => (e) => {
    setDados((d) => ({ ...d, [campo]: e.target ? e.target.value : e }))
    setErros((atual) => ({ ...atual, [campo]: undefined }))
  }
  const mudarFotos = (lista) => {
    setFotos(lista)
    setErros((atual) => ({ ...atual, fotos: undefined }))
  }
  const mudarLocal = useCallback((ponto) => {
    setLocal(ponto)
    setErros((atual) => ({ ...atual, local: undefined, latitude: undefined }))
  }, [])

  // A cada etapa, leva a leitura (e o leitor de tela) para o topo do assistente.
  useEffect(() => {
    if (etapaAnterior.current === etapa) return // na abertura da página, não rola nem rouba o foco
    etapaAnterior.current = etapa
    titulo.current?.focus()
    titulo.current?.scrollIntoView({ block: 'nearest' })
  }, [etapa])

  function avancar() {
    const e = validar(etapa, dados, fotos, local)
    setErros(e)
    if (Object.keys(e).length === 0) setEtapa(etapa + 1)
  }

  async function publicar() {
    setErroGeral('')
    setEnviando(true)
    const corpo = new FormData()
    const campos = {
      especie: dados.especie, porte: dados.porte, sexo: dados.sexo, cor_predominante: dados.cor_predominante,
      pelagem: dados.pelagem, sinais_particulares: dados.sinais_particulares,
      latitude: local.lat, longitude: local.lng, [t.campoData]: dados.data,
    }
    if (tipo === 'perdido') campos.raio_busca_km = dados.raio_busca_km
    Object.entries(campos).forEach(([k, v]) => corpo.append(k, v))
    fotos.forEach((f) => corpo.append('fotos', f))
    try {
      const registro = await api(t.caminhoApi, { metodo: 'POST', multipart: corpo })
      setPublicado(registro)
      setEtapa(RESULTADOS)
      buscarProximos(registro)
    } catch (err) {
      setErroGeral(err.message)
      const campos = Object.keys(err.campos || {})
      if (campos.length) {
        setErros(err.campos)
        setEtapa(Math.min(...campos.map((c) => ETAPA_DO_CAMPO[c] ?? REVISAR)))
      }
    } finally {
      setEnviando(false)
    }
  }

  // Enquanto o núcleo OpenCL não compara as fotos, mostramos registros reais da outra base:
  // mesma espécie, perto do ponto marcado, do mais próximo ao mais distante.
  async function buscarProximos(registro) {
    const outra = tipo === 'perdido' ? 'avistamento' : 'perdido'
    const raio = tipo === 'perdido' ? registro.raio_busca_km : 10
    const consulta = new URLSearchParams({
      especie: registro.especie, lat: registro.latitude, lng: registro.longitude, raio_km: raio, limite: 12,
    })
    try {
      setProximos({ tipo: outra, lista: await api(`${TIPOS_REGISTRO[outra].caminhoApi}?${consulta}`) })
    } catch {
      setProximos({ tipo: outra, lista: [] })
    }
  }

  function recomecar() {
    setEtapa(0)
    setFotos([])
    setDados(DADOS_INICIAIS)
    setLocal(null)
    setErros({})
    setErroGeral('')
    setPublicado(null)
    setProximos(null)
  }

  return (
    <main className="pagina">
      <p><Link to="/reencontro">← Perdidos e achados</Link></p>
      <h1>{textos.titulo}</h1>
      <p className="subtitulo">{textos.intro}</p>

      <ol className="etapas" aria-label="Etapas">
        {ETAPAS.map((nome, i) => (
          <li key={nome} className={i < etapa ? 'feita' : i === etapa ? 'atual' : ''} aria-current={i === etapa ? 'step' : undefined}>
            <span className="etapas__numero">{i < etapa ? '✓' : i + 1}</span>
            <span className="etapas__nome">{nome}</span>
          </li>
        ))}
      </ol>

      {contaBloqueada && etapa < RESULTADOS && (
        <div className="aviso aviso--atencao" role="status">
          Só contas de tutor registram animal perdido. Se você viu um animal na rua, use{' '}
          <Link to="/encontrei">Encontrei um animal</Link>.
        </div>
      )}
      {!usuario && etapa === 0 && (
        <div className="aviso aviso--atencao" role="status">
          Você pode preencher tudo sem conta. Para publicar, vamos pedir que você entre.
        </div>
      )}

      <section className="cartao formulario assistente" aria-labelledby="titulo-etapa">
        <h2 id="titulo-etapa" ref={titulo} tabIndex={-1}>
          Etapa {etapa + 1} de {ETAPAS.length}: {ETAPAS[etapa]}
        </h2>

        {etapa === 0 && <SeletorFotos fotos={fotos} aoMudar={mudarFotos} erro={erros.fotos} />}

        {etapa === 1 && (
          <>
            <fieldset className="campo">
              <legend>Espécie</legend>
              <Opcoes
                nome="especie" valor={dados.especie} aoMudar={mudar('especie')} erro={erros.especie} colunas={130}
                opcoes={Object.entries(ESPECIES).map(([v, r]) => [v, `${EMOJI_ESPECIE[v]} ${r}`])}
              />
              {erros.especie && <span className="campo__erro">{erros.especie}</span>}
            </fieldset>
            <fieldset className="campo">
              <legend>Porte</legend>
              <Opcoes
                nome="porte" valor={dados.porte} aoMudar={mudar('porte')} erro={erros.porte} colunas={130}
                opcoes={Object.entries(PORTES).map(([v, r]) => [v, r, DESCRICAO_PORTE[v]])}
              />
              {erros.porte && <span className="campo__erro">{erros.porte}</span>}
            </fieldset>
            <div className="grade-campos">
              <div className="campo">
                <label htmlFor="cor">Cor predominante</label>
                <input id="cor" list="lista-cores" maxLength={60} value={dados.cor_predominante} onChange={mudar('cor_predominante')}
                  aria-invalid={Boolean(erros.cor_predominante)} aria-describedby="cor-erro" />
                <datalist id="lista-cores">{CORES.map((c) => <option key={c} value={c} />)}</datalist>
                {erros.cor_predominante && <span id="cor-erro" className="campo__erro">{erros.cor_predominante}</span>}
              </div>
              <div className="campo">
                <label htmlFor="pelagem">Pelagem <small>(opcional)</small></label>
                <input id="pelagem" list="lista-pelagens" maxLength={60} value={dados.pelagem} onChange={mudar('pelagem')} />
                <datalist id="lista-pelagens">{PELAGENS.map((p) => <option key={p} value={p} />)}</datalist>
              </div>
              <div className="campo">
                <label htmlFor="sexo">Sexo</label>
                <select id="sexo" value={dados.sexo} onChange={mudar('sexo')}>
                  {Object.entries(SEXOS).map(([v, r]) => <option key={v} value={v}>{v === 'indefinido' ? 'Não sei' : r}</option>)}
                </select>
              </div>
            </div>
            <div className="campo">
              <label htmlFor="sinais">Sinais particulares <small>(opcional)</small></label>
              <textarea id="sinais" maxLength={500} value={dados.sinais_particulares} onChange={mudar('sinais_particulares')}
                placeholder="Coleira vermelha, mancha branca no peito, orelha caída, manca da pata traseira…" />
              <small>{dados.sinais_particulares.length}/500 · Não coloque telefone nem endereço: este texto é público.</small>
            </div>
          </>
        )}

        {etapa === 2 && (
          <>
            <SeletorLocal valor={local} aoMudar={mudarLocal} erro={erros.local || erros.latitude} rotulo={textos.rotuloLocal} />
            <p className="aviso aviso--ok" style={{ margin: 0 }}>🔒 {textos.privacidade}</p>
            <div className="grade-campos">
              <div className="campo">
                <label htmlFor="data">{textos.rotuloData}</label>
                <input id="data" type="date" max={hojeISO()} value={dados.data} onChange={mudar('data')}
                  aria-invalid={Boolean(erros.data)} />
                {(erros.data || erros[t.campoData]) && <span className="campo__erro">{erros.data || erros[t.campoData]}</span>}
              </div>
              {tipo === 'perdido' && (
                <div className="campo">
                  <label htmlFor="raio">Até que distância procurar</label>
                  <select id="raio" value={dados.raio_busca_km} onChange={mudar('raio_busca_km')}>
                    {RAIOS.map((r) => <option key={r} value={r}>Até {r} km</option>)}
                  </select>
                  <small>Usado para mostrar avistamentos perto de onde ele sumiu.</small>
                </div>
              )}
            </div>
          </>
        )}

        {etapa === REVISAR && (
          <div className="revisao">
            <MiniaturasRevisao fotos={fotos} />
            <dl className="detalhe-lista">
              <dt>Espécie</dt><dd>{ESPECIES[dados.especie]}</dd>
              <dt>Porte</dt><dd>{PORTES[dados.porte]}</dd>
              <dt>Cor</dt><dd>{dados.cor_predominante}</dd>
              {dados.pelagem && <><dt>Pelagem</dt><dd>{dados.pelagem}</dd></>}
              <dt>Sexo</dt><dd>{dados.sexo === 'indefinido' ? 'Não sei' : SEXOS[dados.sexo]}</dd>
              {dados.sinais_particulares && <><dt>Sinais</dt><dd>{dados.sinais_particulares}</dd></>}
              <dt>{t.rotuloData}</dt><dd>{textoData(dados.data)}</dd>
              {tipo === 'perdido' && <><dt>Procurar até</dt><dd>{dados.raio_busca_km} km</dd></>}
            </dl>
            {erroGeral && <div className="aviso aviso--erro" role="alert">{erroGeral}</div>}
            {!usuario && <LoginRapido />}
          </div>
        )}

        {etapa === RESULTADOS && publicado && (
          <div className="formulario">
            <div className="aviso aviso--ok" role="status" style={{ margin: 0 }}>
              {textos.publicado}{' '}
              <Link to={`${t.caminhoTela}/${publicado.id}`}>Ver o registro</Link> · <Link to="/meus-registros">Meus registros</Link>
            </div>
            <div className="aviso aviso--atencao" style={{ margin: 0 }}>
              <strong>A comparação por foto está em construção.</strong> Em breve o núcleo de similaridade (OpenCL) vai
              comparar as suas fotos e ordenar os candidatos por semelhança (alta, média ou baixa). Por enquanto, mostramos os
              registros da mesma espécie mais próximos do local marcado. A decisão final é sempre sua.
            </div>
            <h3>{textos.tituloResultados}</h3>
            {!proximos && <p className="estado">Procurando…</p>}
            {proximos && proximos.lista.length === 0 && <p className="estado">{textos.vazio}</p>}
            {proximos && proximos.lista.length > 0 && (
              <div className="grade-animais">
                {proximos.lista.map((r) => <CartaoRegistro key={r.id} registro={r} tipo={proximos.tipo} />)}
              </div>
            )}
            <div className="acoes">
              <Link className="botao botao--leve" to="/reencontro">Ver todos os perdidos e achados</Link>
              <button type="button" className="botao botao--leve" onClick={recomecar}>Fazer outro registro</button>
            </div>
          </div>
        )}

        {etapa < RESULTADOS && (
          <div className="acoes assistente__navegacao">
            {etapa > 0 && (
              <button type="button" className="botao botao--leve" onClick={() => { setErros({}); setEtapa(etapa - 1) }}>Voltar</button>
            )}
            {etapa < REVISAR && <button type="button" className="botao" onClick={avancar}>Continuar</button>}
            {etapa === REVISAR && (
              <button type="button" className="botao" onClick={publicar} disabled={enviando || !usuario || contaBloqueada}>
                {enviando ? 'Enviando fotos…' : textos.publicar}
              </button>
            )}
          </div>
        )}
      </section>
    </main>
  )
}
