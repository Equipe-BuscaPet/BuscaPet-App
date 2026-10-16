import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const RECIFE = [-8.0476, -34.877]
const COR = '#c4541a'

// Mapa para marcar um ponto: clique (ou toque) no mapa, ou use a localização do aparelho.
// `valor` é { lat, lng } ou null.
export default function SeletorLocal({ valor, aoMudar, erro, rotulo }) {
  const elemento = useRef(null)
  const mapa = useRef(null)
  const marcador = useRef(null)
  const [aviso, setAviso] = useState('')
  const [localizando, setLocalizando] = useState(false)

  useEffect(() => {
    const m = L.map(elemento.current, { scrollWheelZoom: false }).setView(valor ? [valor.lat, valor.lng] : RECIFE, valor ? 16 : 12)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(m)
    m.on('click', (e) => aoMudar({ lat: Number(e.latlng.lat.toFixed(6)), lng: Number(e.latlng.lng.toFixed(6)) }))
    mapa.current = m
    return () => { m.remove(); mapa.current = null; marcador.current = null }
    // O mapa é criado uma vez (aoMudar precisa ser estável); o ponto é atualizado pelo efeito abaixo.
  }, [])

  useEffect(() => {
    const m = mapa.current
    if (!m) return
    if (!valor) {
      marcador.current?.remove()
      marcador.current = null
      return
    }
    if (!marcador.current) {
      marcador.current = L.circleMarker([valor.lat, valor.lng], { radius: 10, color: '#fff', weight: 3, fillColor: COR, fillOpacity: 1 }).addTo(m)
    } else {
      marcador.current.setLatLng([valor.lat, valor.lng])
    }
  }, [valor])

  function usarMinhaLocalizacao() {
    setAviso('')
    if (!navigator.geolocation) return setAviso('Seu navegador não oferece localização. Marque o ponto clicando no mapa.')
    setLocalizando(true)
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const ponto = { lat: Number(p.coords.latitude.toFixed(6)), lng: Number(p.coords.longitude.toFixed(6)) }
        aoMudar(ponto)
        mapa.current?.setView([ponto.lat, ponto.lng], 16)
        setLocalizando(false)
      },
      () => {
        setAviso('Não foi possível obter sua localização. Verifique a permissão do navegador ou marque o ponto no mapa.')
        setLocalizando(false)
      },
      { timeout: 10000, enableHighAccuracy: true },
    )
  }

  return (
    <div className="campo">
      <span className="campo__rotulo">{rotulo}</span>
      <div className="acoes">
        <button type="button" className="botao botao--leve botao--pequeno" onClick={usarMinhaLocalizacao} disabled={localizando}>
          {localizando ? 'Localizando…' : '📍 Estou no local agora'}
        </button>
        <small>{valor ? 'Ponto marcado. Clique em outro lugar do mapa para ajustar.' : 'ou clique no mapa no ponto exato.'}</small>
      </div>
      <div
        ref={elemento}
        className={`mapa mapa--seletor${erro ? ' mapa--erro' : ''}`}
        role="application"
        aria-label="Mapa para marcar o local. Clique para posicionar o marcador."
      />
      {aviso && <span className="campo__erro" role="status">{aviso}</span>}
      {erro && <span className="campo__erro">{erro}</span>}
    </div>
  )
}
