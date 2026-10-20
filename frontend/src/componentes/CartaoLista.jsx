import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const POR_PAGINA = 20

// Janela com a lista inteira, buscada só quando é aberta e de 20 em 20 ("Carregar mais"),
// para o relatório não carregar tudo de uma vez quando há muitos dados.
function DialogoLista({ titulo, rota, aoFechar }) {
  const dialogo = useRef(null)
  const [pagina, setPagina] = useState(null)
  const [itens, setItens] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')

  async function carregar(deslocamento) {
    setCarregando(true)
    try {
      const sep = rota.includes('?') ? '&' : '?'
      const p = await api(`${rota}${sep}limite=${POR_PAGINA}&deslocamento=${deslocamento}`)
      setPagina(p)
      setItens((atuais) => (deslocamento === 0 ? p.itens : [...atuais, ...p.itens]))
    } catch (e) {
      setErro(e.message)
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    dialogo.current?.showModal()
    carregar(0)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <dialog ref={dialogo} className="dialogo-lista" aria-label={titulo} onClose={aoFechar} onClick={(e) => e.target === dialogo.current && dialogo.current.close()}>
      <div className="dialogo-lista__topo">
        <h2>{titulo}</h2>
        <button type="button" className="botao botao--leve botao--pequeno" onClick={() => dialogo.current.close()}>Fechar</button>
      </div>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {pagina && <p className="legenda" role="status">Mostrando {itens.length} de {pagina.total}</p>}
      <div className="dialogo-lista__corpo">
        {pagina && (
          <table>
            <thead><tr>{pagina.colunas.map((c, i) => <th key={c} style={i > 0 ? { textAlign: 'right' } : undefined}>{c}</th>)}</tr></thead>
            <tbody>
              {itens.map((l, n) => (
                <tr key={`${l.rotulo}-${n}`}><td>{l.rotulo}</td>{l.valores.map((v, i) => <td key={i} style={{ textAlign: 'right', fontWeight: 700 }}>{v}</td>)}</tr>
              ))}
            </tbody>
          </table>
        )}
        {carregando && <p className="estado">Carregando…</p>}
      </div>
      {pagina && itens.length < pagina.total && (
        <div className="acoes" style={{ justifyContent: 'center', marginTop: '0.75rem' }}>
          <button type="button" className="botao botao--leve" disabled={carregando} onClick={() => carregar(itens.length)}>Carregar mais</button>
        </div>
      )}
    </dialog>
  )
}

// Cartão de altura fixa com as primeiras linhas de uma lista do relatório. Nomes longos são cortados com "…"
// (o nome inteiro aparece ao passar o mouse). Se a lista tiver mais linhas, "Ver todos" abre a lista completa.
export default function CartaoLista({ titulo, cabecalho, linhas, total = linhas.length, rotaCompleta, vazio = 'Nada no período.' }) {
  const [aberto, setAberto] = useState(false)
  return (
    <div className="cartao-lista">
      <h3>{titulo}</h3>
      <div className="cartao cartao-lista__caixa">
        <table className={`colunas-${cabecalho.length}`}>
          <thead><tr>{cabecalho.map((c, i) => <th key={c} style={i > 0 ? { textAlign: 'right' } : undefined}>{c}</th>)}</tr></thead>
          <tbody>
            {linhas.length === 0 && <tr><td colSpan={cabecalho.length}>{vazio}</td></tr>}
            {linhas.map((l) => (
              <tr key={l[0]}>
                {l.map((v, i) => i === 0
                  ? <td key={i} className="cartao-lista__rotulo" title={v}>{v}</td>
                  : <td key={i} style={{ textAlign: 'right', fontWeight: 700 }}>{v}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        {total > linhas.length && rotaCompleta && (
          <button type="button" className="botao botao--leve botao--pequeno cartao-lista__mais" onClick={() => setAberto(true)}>
            Ver todos ({total})
          </button>
        )}
      </div>
      {aberto && <DialogoLista titulo={titulo} rota={rotaCompleta} aoFechar={() => setAberto(false)} />}
    </div>
  )
}
