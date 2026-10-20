import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api, urlFoto } from '../api'
import { useAuth } from '../auth'
import { TIPOS_REGISTRO } from '../componentes/CartaoRegistro'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, textoData, textoHaQuanto, textoKm } from '../rotulos'

// Mostra a área do registro: um círculo quando o ponto é aproximado (público), um marcador quando é o exato (autor).
function MapaArea({ registro, raioAproximadoM }) {
  const elemento = useRef(null)
  useEffect(() => {
    const centro = [registro.latitude, registro.longitude]
    const m = L.map(elemento.current, { scrollWheelZoom: false }).setView(centro, registro.localizacao_aproximada && raioAproximadoM > 500 ? 14 : 16)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(m)
    if (registro.localizacao_aproximada) {
      L.circle(centro, { radius: raioAproximadoM, color: '#c4541a', weight: 2, fillOpacity: 0.15 }).addTo(m)
    } else {
      L.circleMarker(centro, { radius: 10, color: '#fff', weight: 3, fillColor: '#c4541a', fillOpacity: 1 }).addTo(m)
    }
    return () => m.remove()
  }, [registro, raioAproximadoM])
  return <div ref={elemento} className="mapa mapa--pequeno" role="img" aria-label="Mapa com a região do registro" />
}

export default function RegistroDetalhe({ tipo }) {
  const t = TIPOS_REGISTRO[tipo]
  const { id } = useParams()
  const { usuario } = useAuth()
  const navegar = useNavigate()
  const [registro, setRegistro] = useState(null)
  const [fotoAtual, setFotoAtual] = useState(0)
  const [erro, setErro] = useState('')
  const [excluindo, setExcluindo] = useState(false)
  const [resolvendo, setResolvendo] = useState(false)
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    setRegistro(null)
    setErro('')
    setFotoAtual(0)
    api(`${t.caminhoApi}/${id}`)
      .then(setRegistro)
      .catch((e) => setErro(e.status === 404 ? 'Registro não encontrado. Ele pode ter sido excluído.' : e.message))
  }, [t.caminhoApi, id, usuario])

  async function excluir() {
    if (!window.confirm('Excluir este registro e as fotos dele? Esta ação não pode ser desfeita.')) return
    setExcluindo(true)
    try {
      await api(`${t.caminhoApi}/${id}`, { metodo: 'DELETE' })
      navegar('/meus-registros', { state: { aviso: 'Registro excluído.' } })
    } catch (e) {
      setErro(e.message)
      setExcluindo(false)
    }
  }

  async function resolver() {
    if (!window.confirm('Marcar como resolvido? O registro sai do mapa e você deixa de receber alertas de avistamentos.')) return
    setResolvendo(true)
    setErro('')
    try {
      setRegistro(await api(`/perdidos/${id}/resolvido`, { metodo: 'PATCH' }))
      setAviso('Que bom que vocês se reencontraram! O caso foi marcado como resolvido e saiu do mapa.')
    } catch (e) {
      setErro(e.message)
    } finally {
      setResolvendo(false)
    }
  }

  const voltar = <p><Link to={tipo === 'perdido' ? '/reencontro' : '/reencontro?aba=avistamento'}>← Perdidos e achados</Link></p>

  if (erro && !registro) return <main className="pagina">{voltar}<div className="aviso aviso--erro" role="alert">{erro}</div></main>
  if (!registro) return <p className="estado">Carregando…</p>

  // Só o autor recebe o ponto exato; o administrador também pode excluir (moderação).
  const ehAutor = !registro.localizacao_aproximada
  const podeExcluir = ehAutor || usuario?.tipo_conta === 'admin'
  const fotos = registro.fotos

  return (
    <main className="pagina">
      {voltar}
      <div className="duas-colunas">
        <div className="galeria">
          {fotos.length ? (
            <img className="galeria__principal" src={urlFoto(fotos[fotoAtual])} alt={`Foto ${fotoAtual + 1} de ${fotos.length}`} />
          ) : (
            <div className="animal__foto" style={{ minHeight: 260, fontSize: '5rem' }} aria-hidden="true">{EMOJI_ESPECIE[registro.especie]}</div>
          )}
          {fotos.length > 1 && (
            <ul className="miniaturas" aria-label="Outras fotos">
              {fotos.map((f, i) => (
                <li key={f}>
                  <button type="button" className={`miniatura${i === fotoAtual ? ' miniatura--atual' : ''}`} onClick={() => setFotoAtual(i)} aria-label={`Ver foto ${i + 1}`} aria-pressed={i === fotoAtual}>
                    <img src={urlFoto(f)} alt="" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="cartao detalhe">
          <div>
            <h1>{t.titulo(registro.especie)}</h1>
            {registro.resolvido
              ? <span className="etiqueta etiqueta--ok">Caso resolvido</span>
              : <span className={`etiqueta ${t.etiqueta[1]}`}>{t.etiqueta[0]}</span>}
            {ehAutor && <span className="etiqueta" style={{ marginLeft: '0.4rem' }}>Seu registro</span>}
          </div>
          <dl>
            <dt>Espécie</dt><dd>{ESPECIES[registro.especie]}</dd>
            <dt>Porte</dt><dd>{PORTES[registro.porte]}</dd>
            <dt>Cor</dt><dd>{registro.cor_predominante}</dd>
            {registro.pelagem && <><dt>Pelagem</dt><dd>{registro.pelagem}</dd></>}
            <dt>Sexo</dt><dd>{registro.sexo === 'indefinido' ? 'Não informado' : SEXOS[registro.sexo]}</dd>
            <dt>{t.rotuloData}</dt><dd>{textoData(registro[t.campoData])}</dd>
            {tipo === 'perdido' && ehAutor && <><dt>Raio de busca</dt><dd>{textoKm(registro.raio_busca_km)}</dd></>}
            <dt>Publicado</dt><dd>{textoHaQuanto(registro.criado_em)}</dd>
          </dl>
          {registro.sinais_particulares && <section><h2>Sinais particulares</h2><p style={{ margin: 0 }}>{registro.sinais_particulares}</p></section>}

          <section>
            <h2>Onde</h2>
            <MapaArea registro={registro} raioAproximadoM={t.raioAproximadoM} />
            <small className="legenda">
              {ehAutor
                ? 'Você vê o ponto exato que marcou. As outras pessoas veem só a região aproximada.'
                : `Região aproximada (cerca de ${t.raioAproximadoM >= 1000 ? '1 km' : '100 m'}), para proteger quem registrou.`}
            </small>
          </section>

          {aviso && <div className="aviso aviso--ok" role="status">{aviso}</div>}
          {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
          <div className="acoes">
            {ehAutor && tipo === 'perdido' && !registro.resolvido && (
              <button type="button" className="botao" onClick={resolver} disabled={resolvendo}>
                {resolvendo ? 'Salvando…' : 'Encontrei meu animal'}
              </button>
            )}
            {!ehAutor && tipo === 'perdido' && <Link className="botao" to="/encontrei">Vi este animal</Link>}
            {!ehAutor && tipo === 'avistamento' && <Link className="botao" to="/perdi">É o meu animal? Registre a perda</Link>}
            {podeExcluir && (
              <button type="button" className="botao botao--perigo" onClick={excluir} disabled={excluindo}>
                {excluindo ? 'Excluindo…' : 'Excluir registro'}
              </button>
            )}
          </div>
          {!ehAutor && (
            <p className="subtitulo" style={{ margin: 0 }}>
              <small>O contato com quem registrou será feito pela própria plataforma, sem expor telefone nem endereço (em construção).</small>
            </p>
          )}
        </div>
      </div>
    </main>
  )
}
