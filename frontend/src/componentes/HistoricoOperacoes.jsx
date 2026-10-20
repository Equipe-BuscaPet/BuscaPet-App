import { useEffect, useState } from 'react'
import { api, baixarArquivo } from '../api'
import { useUltimoPedido } from '../useUltimoPedido'
import FiltroPeriodo, { periodoPadrao } from './FiltroPeriodo'

const POR_PAGINA = 20
const ROTULO_DETALHE = {
  animal: 'Animal', item: 'Item', quantidade: 'Quantidade', abrigo: 'Abrigo', campos: 'Campos', situacao: 'Situação',
  tipo: 'Tipo de conta', especie: 'Espécie', pelo_admin: 'Pela administração',
}
const OCULTOS = new Set(['animal_id', 'abrigo_id', 'apoiador_id'])

function textoDetalhes(d) {
  return Object.entries(d).filter(([k]) => !OCULTOS.has(k))
    .map(([k, v]) => `${ROTULO_DETALHE[k] || k}: ${Array.isArray(v) ? v.join(', ') : v === true ? 'sim' : v}`).join(' · ')
}

// Histórico de operações (RF-39) com filtros de período, ação e pesquisa. A administração vê tudo
// (com exportação CSV); o abrigo vê só o que a própria conta fez (`rota="/relatorios/abrigo/historico"`).
export default function HistoricoOperacoes({ rota, rotaCsv, mostrarQuem = true }) {
  const [periodo, setPeriodo] = useState(periodoPadrao)
  const [acao, setAcao] = useState('')
  const [texto, setTexto] = useState('')
  const [busca, setBusca] = useState('')
  const [pagina, setPagina] = useState(0)
  const [acoes, setAcoes] = useState({})
  const [dados, setDados] = useState(null)
  const [erro, setErro] = useState('')
  const novoPedido = useUltimoPedido()

  // A lista de ações (para o filtro) é da administração; o abrigo filtra por período e pesquisa.
  useEffect(() => { if (mostrarQuem) api('/admin/acoes').then(setAcoes).catch(() => setAcoes({})) }, [mostrarQuem])
  useEffect(() => { setPagina(0) }, [periodo, acao, busca])

  const consulta = () => {
    const q = new URLSearchParams({ de: periodo.de, ate: periodo.ate })
    if (acao) q.set('acao', acao)
    if (busca) q.set('q', busca)
    return q
  }

  useEffect(() => {
    const valido = novoPedido()
    const q = consulta()
    q.set('limite', POR_PAGINA)
    q.set('deslocamento', pagina * POR_PAGINA)
    setErro('')
    api(`${rota}?${q}`).then((d) => valido() && setDados(d)).catch((e) => valido() && setErro(e.message))
  }, [rota, periodo, acao, busca, pagina, novoPedido]) // eslint-disable-line react-hooks/exhaustive-deps

  async function exportar() {
    try { await baixarArquivo(`${rotaCsv}?${consulta()}`, 'historico.csv') } catch (e) { setErro(e.message) }
  }

  const total = dados?.total ?? 0
  return (
    <section aria-label="Histórico de operações">
      <FiltroPeriodo periodo={periodo} aoMudar={setPeriodo}>
        {Object.keys(acoes).length > 0 && (
          <div className="campo">
            <label htmlFor="filtro-acao">Ação</label>
            <select id="filtro-acao" value={acao} onChange={(e) => setAcao(e.target.value)}>
              <option value="">Todas</option>
              {Object.entries(acoes).map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}
            </select>
          </div>
        )}
        <form className="campo" style={{ minWidth: 220 }} onSubmit={(e) => { e.preventDefault(); setBusca(texto.trim()) }} role="search">
          <label htmlFor="filtro-texto">Pesquisar</label>
          <input id="filtro-texto" type="search" value={texto} onChange={(e) => { setTexto(e.target.value); if (!e.target.value) setBusca('') }}
            placeholder={mostrarQuem ? 'Nome, e-mail ou detalhe (ex.: Thor)' : 'Detalhe (ex.: Thor)'} />
        </form>
        {rotaCsv && <button type="button" className="botao botao--leve" onClick={exportar}>Exportar CSV</button>}
      </FiltroPeriodo>

      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {dados === null && !erro && <p className="estado">Carregando…</p>}
      {dados && (
        <>
          <p className="legenda" role="status">{total} {total === 1 ? 'operação encontrada' : 'operações encontradas'}</p>
          {total > 0 && (
            <div className="cartao rolagem">
              <table className="historico">
                <thead><tr><th>Quando</th>{mostrarQuem && <th>Quem</th>}<th>Ação</th><th>Detalhes</th></tr></thead>
                <tbody>
                  {dados.itens.map((l) => (
                    <tr key={l.id}>
                      <td>{new Date(l.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</td>
                      {mostrarQuem && <td>{l.usuario_nome}<small>{l.usuario_email}</small></td>}
                      <td>{l.rotulo}</td>
                      <td>{textoDetalhes(l.detalhes) || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {total > POR_PAGINA && (
            <div className="paginacao">
              <button type="button" className="botao botao--leve botao--pequeno" disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}>Anterior</button>
              <span className="legenda">Página {pagina + 1} de {Math.ceil(total / POR_PAGINA)}</span>
              <button type="button" className="botao botao--leve botao--pequeno" disabled={(pagina + 1) * POR_PAGINA >= total} onClick={() => setPagina(pagina + 1)}>Próxima</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
