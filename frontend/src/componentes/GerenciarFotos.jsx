import { useState } from 'react'
import { api, urlFoto } from '../api'

const MAXIMO = 5
const ACEITOS = ['image/jpeg', 'image/png', 'image/webp']

// Fotos do animal no painel do abrigo (RF-17): enviar (até 5), escolher a capa e remover.
// A primeira foto é a capa que aparece no catálogo.
export default function GerenciarFotos({ animal, aoMudar }) {
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const fotos = animal.fotos || []
  const restam = MAXIMO - fotos.length

  async function chamar(promessa) {
    setErro('')
    try {
      aoMudar(await promessa)
    } catch (e) {
      setErro(e.message)
    }
  }

  async function escolher(e) {
    const arquivos = [...e.target.files]
    e.target.value = ''
    if (!arquivos.length) return
    const invalidos = arquivos.filter((f) => !ACEITOS.includes(f.type)).map((f) => f.name)
    if (invalidos.length) return setErro(`Use fotos em JPEG, PNG ou WebP (não aceito: ${invalidos.join(', ')}).`)
    if (arquivos.length > restam) return setErro(`Você pode enviar mais ${restam} foto(s) para ${animal.nome}.`)
    const corpo = new FormData()
    arquivos.forEach((f) => corpo.append('fotos', f))
    setEnviando(true)
    await chamar(api(`/animais/${animal.id}/fotos`, { metodo: 'POST', multipart: corpo }))
    setEnviando(false)
  }

  return (
    <section className="cartao" aria-labelledby="titulo-fotos" style={{ marginTop: '1rem' }}>
      <h2 id="titulo-fotos">Fotos de {animal.nome} <small className="legenda" style={{ display: 'inline' }}>{fotos.length} de {MAXIMO}</small></h2>
      <p className="subtitulo" style={{ marginBottom: '0.75rem' }}>A primeira foto é a capa no catálogo. Fotos de celular perdem a localização (GPS) ao serem enviadas.</p>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      <ul className="miniaturas" aria-label={`Fotos de ${animal.nome}`}>
        {fotos.map((f, i) => (
          <li key={f.id} className="foto-gerenciada">
            <span className={`miniatura${i === 0 ? ' miniatura--atual' : ''}`}><img src={urlFoto(f.url)} alt={`Foto ${i + 1} de ${animal.nome}`} /></span>
            {i === 0
              ? <small className="etiqueta etiqueta--ok">Capa</small>
              : <button type="button" className="botao botao--leve botao--pequeno" onClick={() => chamar(api(`/animais/${animal.id}/fotos/${f.id}/capa`, { metodo: 'PATCH' }))}>Tornar capa</button>}
            <button type="button" className="botao botao--leve botao--pequeno" aria-label={`Remover foto ${i + 1}`}
              onClick={() => window.confirm('Remover esta foto?') && chamar(api(`/animais/${animal.id}/fotos/${f.id}`, { metodo: 'DELETE' }))}>Remover</button>
          </li>
        ))}
        {restam > 0 && (
          <li>
            <label className="miniatura miniatura--adicionar" aria-disabled={enviando}>
              <span aria-hidden="true">+</span>
              <small>{enviando ? 'Enviando…' : 'Adicionar'}</small>
              <input type="file" accept={ACEITOS.join(',')} multiple className="sr-only" disabled={enviando} onChange={escolher} aria-label="Adicionar fotos" />
            </label>
          </li>
        )}
      </ul>
    </section>
  )
}
