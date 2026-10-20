import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, baixarArquivo } from '../api'
import FiltroPeriodo, { periodoPadrao } from '../componentes/FiltroPeriodo'
import GraficoMensal, { TabelaMensal } from '../componentes/GraficoMensal'
import HistoricoOperacoes from '../componentes/HistoricoOperacoes'
import { STATUS_ANIMAL, STATUS_DOACAO, STATUS_INTERESSE } from '../rotulos'
import { useUltimoPedido } from '../useUltimoPedido'

const STATUS_NECESSIDADE = { aberta: 'Em aberto', atendida: 'Atendida' }
const soma = (lista) => lista.reduce((t, c) => t + c.total, 0)
const de = (lista, chave) => lista.find((c) => c.chave === chave)?.total ?? 0

function TabelaSimples({ titulo, cabecalho, linhas, vazio = 'Nada no período.' }) {
  return (
    <div>
      <h3>{titulo}</h3>
      <div className="cartao rolagem">
        <table>
          <thead><tr>{cabecalho.map((c, i) => <th key={c} style={i > 0 ? { textAlign: 'right' } : undefined}>{c}</th>)}</tr></thead>
          <tbody>
            {linhas.length === 0 && <tr><td colSpan={cabecalho.length}>{vazio}</td></tr>}
            {linhas.map((l) => <tr key={l[0]}>{l.map((v, i) => <td key={i} style={i > 0 ? { textAlign: 'right', fontWeight: 700 } : undefined}>{v}</td>)}</tr>)}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Relatorio() {
  const [periodo, setPeriodo] = useState(periodoPadrao)
  const [r, setR] = useState(null)
  const [verTabela, setVerTabela] = useState(false)
  const [erro, setErro] = useState('')
  const novoPedido = useUltimoPedido()

  useEffect(() => {
    const valido = novoPedido()
    setErro('')
    api(`/relatorios/abrigo?de=${periodo.de}&ate=${periodo.ate}`).then((d) => valido() && setR(d)).catch((e) => valido() && setErro(e.message))
  }, [periodo, novoPedido])

  const exportar = (arquivo, comPeriodo = true) => async () => {
    try { await baixarArquivo(`/relatorios/abrigo/${arquivo}${comPeriodo ? `?de=${periodo.de}&ate=${periodo.ate}` : ''}`, arquivo) } catch (e) { setErro(e.message) }
  }
  const serie = (chave) => r.serie_mensal.map((p) => ({ mes: p.mes, valor: p[chave] }))

  return (
    <section aria-label="Relatório do abrigo">
      <FiltroPeriodo periodo={periodo} aoMudar={setPeriodo} />
      <div className="acoes" style={{ marginBottom: '1.25rem' }}>
        <span className="legenda" style={{ margin: 0 }}>Exportar (CSV):</span>
        <button type="button" className="botao botao--leve botao--pequeno" onClick={exportar('interesses.csv')}>Interesses do período</button>
        <button type="button" className="botao botao--leve botao--pequeno" onClick={exportar('doacoes.csv')}>Doações do período</button>
        <button type="button" className="botao botao--leve botao--pequeno" onClick={exportar('animais.csv', false)}>Todos os animais</button>
      </div>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!r && !erro && <p className="estado">Carregando…</p>}
      {r && (
        <>
          <div className="indicadores">
            <div className="cartao indicador"><strong>{soma(r.interesses)}</strong><span>interesses recebidos</span><small>{de(r.interesses, 'aguardando')} aguardando resposta</small></div>
            <div className="cartao indicador"><strong>{r.adocoes_aprovadas}</strong><span>adoções aprovadas</span></div>
            <div className="cartao indicador">
              <strong>{r.tempo_medio_adocao_dias === null ? '—' : `${String(r.tempo_medio_adocao_dias).replace('.', ',')} dias`}</strong>
              <span>tempo médio até a adoção</span><small>da entrada no abrigo à aprovação</small>
            </div>
            <div className="cartao indicador"><strong>{de(r.doacoes, 'confirmada')}</strong><span>doações confirmadas</span><small>{de(r.doacoes, 'aguardando_confirmacao')} aguardando você</small></div>
          </div>

          <div className="topo-pagina">
            <h2 style={{ margin: 0 }}>Últimos 6 meses</h2>
            <button type="button" className="botao botao--leve botao--pequeno" aria-pressed={verTabela} onClick={() => setVerTabela(!verTabela)}>
              {verTabela ? 'Ver como gráfico' : 'Ver como tabela'}
            </button>
          </div>
          {verTabela ? <TabelaMensal serie={r.serie_mensal} colunas={[['interesses', 'Interesses de adoção'], ['doacoes_confirmadas', 'Doações confirmadas']]} /> : (
            <div className="graficos">
              <GraficoMensal titulo="Interesses de adoção recebidos" serie={serie('interesses')} slot={1} />
              <GraficoMensal titulo="Doações confirmadas" serie={serie('doacoes_confirmadas')} slot={3} />
            </div>
          )}

          <div className="duas-tabelas" style={{ marginTop: '1.5rem' }}>
            <TabelaSimples titulo="De onde vêm os interessados" cabecalho={['Cidade', 'Interesses']} linhas={r.origem_interessados.map((c) => [c.chave, c.total])} />
            <TabelaSimples titulo="Interesses por situação" cabecalho={['Situação', 'Total']} linhas={r.interesses.map((c) => [STATUS_INTERESSE[c.chave], c.total])} />
            <TabelaSimples titulo="Doações por apoiador (confirmadas)" cabecalho={['Apoiador', 'Doações', 'Itens']} linhas={r.por_apoiador.map((a) => [a.nome, a.doacoes, a.quantidade])} />
            <TabelaSimples titulo="O que foi recebido" cabecalho={['Item', 'Quantidade']} linhas={r.por_item.map((c) => [c.chave, c.total])} />
            <TabelaSimples titulo="Doações por situação (registradas no período)" cabecalho={['Situação', 'Total']} linhas={r.doacoes.map((c) => [STATUS_DOACAO[c.chave], c.total])} />
            <TabelaSimples titulo="Animais por situação (hoje)" cabecalho={['Situação', 'Animais']} linhas={r.animais.map((c) => [STATUS_ANIMAL[c.chave], c.total])} vazio="Nenhum animal cadastrado." />
            <TabelaSimples titulo="Necessidades (hoje)" cabecalho={['Situação', 'Total']} linhas={r.necessidades.map((c) => [STATUS_NECESSIDADE[c.chave], c.total])} vazio="Nenhuma necessidade publicada." />
          </div>
        </>
      )}
    </section>
  )
}

// Relatórios do abrigo (RF-40) e o histórico das operações feitas pela conta (RF-39).
export default function RelatoriosAbrigo() {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') === 'historico' ? 'historico' : 'relatorio'
  return (
    <main className="pagina">
      <h1>Relatórios</h1>
      <p className="subtitulo">Adoções, interessados e doações do seu abrigo no período escolhido, para acompanhar e prestar contas.</p>
      <div className="abas" role="tablist" aria-label="Relatórios" style={{ marginBottom: '1.25rem' }}>
        {[['relatorio', 'Relatório do período'], ['historico', 'Histórico de operações']].map(([valor, rotulo]) => (
          <button key={valor} role="tab" aria-selected={aba === valor} className={`abas__item${aba === valor ? ' abas__item--ativa' : ''}`}
            onClick={() => setParams(valor === 'relatorio' ? {} : { aba: valor })}>{rotulo}</button>
        ))}
      </div>
      {aba === 'relatorio' ? <Relatorio /> : <HistoricoOperacoes rota="/relatorios/abrigo/historico" mostrarQuem={false} />}
    </main>
  )
}
