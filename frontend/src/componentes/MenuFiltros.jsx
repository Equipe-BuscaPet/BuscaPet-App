import { useEffect, useId, useRef, useState } from 'react'

// Botão "Filtros" que abre um painel com as opções (fecha com Esc, clique fora ou "Pronto").
// `ativos` é quantos filtros estão ligados: aparece no botão para a pessoa saber que há algo filtrando.
export default function MenuFiltros({ ativos = 0, aoLimpar, children }) {
  const [aberto, setAberto] = useState(false)
  const caixa = useRef(null)
  const id = useId()

  useEffect(() => {
    if (!aberto) return
    const fora = (e) => { if (!caixa.current?.contains(e.target)) setAberto(false) }
    const esc = (e) => { if (e.key === 'Escape') setAberto(false) }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  return (
    <div className="menu-filtros" ref={caixa}>
      <button
        type="button" className={`botao botao--leve botao--pequeno${ativos ? ' menu-filtros__botao--ativo' : ''}`}
        aria-expanded={aberto} aria-controls={id} onClick={() => setAberto((v) => !v)}
      >
        <span aria-hidden="true">⚙️</span> Filtros{ativos > 0 && <span className="camada__total">{ativos}</span>}
      </button>
      {aberto && (
        <div className="menu-filtros__painel" id={id} role="dialog" aria-label="Filtros">
          {children}
          <div className="acoes menu-filtros__rodape">
            {ativos > 0 && aoLimpar && (
              <button type="button" className="botao botao--leve botao--pequeno" onClick={aoLimpar}>Limpar filtros</button>
            )}
            <button type="button" className="botao botao--pequeno" onClick={() => setAberto(false)}>Pronto</button>
          </div>
        </div>
      )}
    </div>
  )
}
