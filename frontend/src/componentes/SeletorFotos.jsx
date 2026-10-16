import { useEffect, useRef, useState } from 'react'

// Mesmos limites da API (api/app/core/fotos.py): conferir aqui só poupa a pessoa de esperar o envio para descobrir.
export const MAX_FOTOS = 5
const MAX_MB = 8
const TIPOS = ['image/jpeg', 'image/png', 'image/webp']

// Endereços temporários (blob:) para mostrar as fotos antes do envio. São criados e liberados no mesmo
// efeito: assim cada montagem tem os seus, e nenhum endereço é liberado enquanto ainda está na tela.
export function usePrevias(fotos) {
  const [previas, setPrevias] = useState({ de: null, urls: [] })
  useEffect(() => {
    const urls = fotos.map((f) => URL.createObjectURL(f))
    setPrevias({ de: fotos, urls })
    return () => urls.forEach((u) => URL.revokeObjectURL(u))
  }, [fotos])
  // Enquanto o efeito não roda para a lista nova, não devolve endereços da lista antiga (já liberados).
  return previas.de === fotos ? previas.urls : []
}

// Escolha de 1 a 5 fotos com pré-visualização. Aceita clique, câmera do celular e arrastar-e-soltar.
export default function SeletorFotos({ fotos, aoMudar, erro }) {
  const entrada = useRef(null)
  const [arrastando, setArrastando] = useState(false)
  const [aviso, setAviso] = useState('')

  const previas = usePrevias(fotos)

  function adicionar(lista) {
    const recusadas = []
    const novas = []
    for (const arquivo of lista) {
      if (!TIPOS.includes(arquivo.type)) recusadas.push(`${arquivo.name}: use JPEG, PNG ou WebP`)
      else if (arquivo.size > MAX_MB * 1024 * 1024) recusadas.push(`${arquivo.name}: maior que ${MAX_MB} MB`)
      else novas.push(arquivo)
    }
    const vagas = MAX_FOTOS - fotos.length
    if (novas.length > vagas) recusadas.push(`limite de ${MAX_FOTOS} fotos: ${novas.length - vagas} ficaram de fora`)
    setAviso(recusadas.length ? `Não incluídas — ${recusadas.join('; ')}.` : '')
    if (novas.length && vagas > 0) aoMudar([...fotos, ...novas.slice(0, vagas)])
  }

  function remover(indice) {
    aoMudar(fotos.filter((_, i) => i !== indice))
    setAviso('')
  }

  function soltar(e) {
    e.preventDefault()
    setArrastando(false)
    adicionar([...e.dataTransfer.files])
  }

  const cheio = fotos.length >= MAX_FOTOS

  return (
    <div className="campo">
      <div
        className={`zona-fotos${arrastando ? ' zona-fotos--ativa' : ''}${erro ? ' zona-fotos--erro' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setArrastando(true) }}
        onDragLeave={() => setArrastando(false)}
        onDrop={soltar}
      >
        <ul className="miniaturas" aria-label="Fotos escolhidas">
          {fotos.map((f, i) => (
            <li key={`${f.name}-${f.lastModified}-${i}`} className="miniatura">
              {previas[i] && <img src={previas[i]} alt={`Foto ${i + 1}`} />}
              {i === 0 && <span className="miniatura__principal">Principal</span>}
              <button type="button" className="miniatura__remover" onClick={() => remover(i)} aria-label={`Remover foto ${i + 1}`}>×</button>
            </li>
          ))}
          {!cheio && (
            <li>
              <button type="button" className="miniatura miniatura--adicionar" onClick={() => entrada.current.click()}>
                <span aria-hidden="true">+</span>
                <small>{fotos.length ? 'Adicionar' : 'Escolher fotos'}</small>
              </button>
            </li>
          )}
        </ul>
        <p className="zona-fotos__dica">
          Arraste até {MAX_FOTOS} fotos para cá ou toque em <strong>+</strong>. Prefira o <strong>corpo inteiro</strong>,
          com <strong>boa luz</strong> e de <strong>ângulos diferentes</strong>: é isso que a busca por semelhança compara.
        </p>
        <input
          ref={entrada}
          type="file"
          accept={TIPOS.join(',')}
          multiple
          hidden
          onChange={(e) => { adicionar([...e.target.files]); e.target.value = '' }}
        />
      </div>
      <small>{fotos.length} de {MAX_FOTOS} · JPEG, PNG ou WebP · até {MAX_MB} MB cada. A localização gravada dentro da foto é apagada no envio.</small>
      {aviso && <span className="campo__erro" role="status">{aviso}</span>}
      {erro && <span className="campo__erro">{erro}</span>}
    </div>
  )
}
