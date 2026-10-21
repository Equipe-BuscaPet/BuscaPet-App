import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, baixarArquivo } from '../api'
import FiltroPeriodo, { periodoPadrao } from '../componentes/FiltroPeriodo'
import GraficoMensal, { TabelaMensal } from '../componentes/GraficoMensal'
import { ROTULO_TIPO } from '../componentes/MenuConta'
import { STATUS_ANIMAL, STATUS_VALIDACAO } from '../rotulos'
import { useUltimoPedido } from '../useUltimoPedido'

const COLUNAS_SERIE = [['interesses', 'Interesses de adoção'], ['registros_reencontro', 'Perdidos e avistados'], ['doacoes_confirmadas', 'Doações confirmadas']]

function Indicador({ valor, rotulo, nota, para }) {
  const conteudo = <><strong>{valor}</strong><span>{rotulo}</span>{nota && <small>{nota}</small>}</>
  return para ? <Link to={para} className="cartao indicador" style={{ textDecoration: 'none', color: 'inherit' }}>{conteudo}</Link>
    : <div className="cartao indicador">{conteudo}</div>
}

function Tabela({ titulo, linhas, rotulos }) {
  return (
    <div>
      <h3>{titulo}</h3>
      <div className="cartao rolagem">
        <table>
          <tbody>
            {linhas.length === 0 && <tr><td>Nenhum registro.</td></tr>}
            {linhas.map((l) => <tr key={l.chave}><td>{rotulos[l.chave] || l.chave}</td><td style={{ textAlign: 'right', fontWeight: 700 }}>{l.total}</td></tr>)}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Painel da administração (RF-38): indicadores dos três módulos no período, evolução mensal e as últimas ações.
export default function PainelAdmin() {
  const [periodo, setPeriodo] = useState(periodoPadrao)
  const [dados, setDados] = useState(null)
  const [verTabela, setVerTabela] = useState(false)
  const [erro, setErro] = useState('')
  const novoPedido = useUltimoPedido()

  useEffect(() => {
    const valido = novoPedido()
    setErro('')
    api(`/admin/painel?de=${periodo.de}&ate=${periodo.ate}`).then((d) => valido() && setDados(d)).catch((e) => valido() && setErro(e.message))
  }, [periodo, novoPedido])

  async function exportar() {
    try { await baixarArquivo(`/admin/relatorios/abrigos.csv?de=${periodo.de}&ate=${periodo.ate}`, 'abrigos.csv') } catch (e) { setErro(e.message) }
  }

  const n = dados?.no_periodo
  const serie = (chave) => dados.serie_mensal.map((p) => ({ mes: p.mes, valor: p[chave] }))
  const contas = Object.fromEntries((dados?.contas || []).map((c) => [c.chave, c.total]))

  return (
    <section aria-label="Painel da administração">
      <FiltroPeriodo periodo={periodo} aoMudar={setPeriodo}>
        <button type="button" className="botao botao--leve" onClick={exportar}>Exportar relatório de abrigos (CSV)</button>
      </FiltroPeriodo>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!dados && !erro && <p className="estado">Carregando…</p>}
      {dados && (
        <>
          <h2>No período</h2>
          <div className="indicadores">
            <Indicador valor={n.adocoes_aprovadas} rotulo="adoções aprovadas" nota={`${n.interesses} interesses registrados`} />
            <Indicador valor={n.resolvidos} rotulo="reencontros (casos resolvidos)" nota={`${n.perdidos} perdidos e ${n.avistamentos} avistamentos`} />
            <Indicador valor={n.doacoes_confirmadas} rotulo="doações confirmadas" />
            <Indicador valor={n.novas_contas} rotulo="contas novas" />
          </div>

          <h2>Agora</h2>
          <div className="indicadores">
            <Indicador valor={dados.agora.denuncias_pendentes} rotulo="denúncias para analisar" para="/admin?aba=denuncias" />
            <Indicador valor={dados.agora.abrigos_para_verificar} rotulo="abrigos para verificar" para="/admin?aba=abrigos" />
            <Indicador valor={dados.agora.perdidos_ativos} rotulo="animais perdidos sendo procurados" para="/reencontro" />
            <Indicador valor={dados.agora.doacoes_aguardando} rotulo="doações aguardando o abrigo" />
            <Indicador valor={dados.agora.necessidades_abertas} rotulo="necessidades no mural" para="/quem-apoia#mural" />
          </div>

          <div className="topo-pagina">
            <h2 style={{ margin: 0 }}>Evolução nos últimos 6 meses</h2>
            <button type="button" className="botao botao--leve botao--pequeno" aria-pressed={verTabela} onClick={() => setVerTabela(!verTabela)}>
              {verTabela ? 'Ver como gráfico' : 'Ver como tabela'}
            </button>
          </div>
          {verTabela ? <TabelaMensal serie={dados.serie_mensal} colunas={COLUNAS_SERIE} /> : (
            <div className="graficos">
              <GraficoMensal titulo="Interesses de adoção" serie={serie('interesses')} slot={1} />
              <GraficoMensal titulo="Perdidos e avistados registrados" serie={serie('registros_reencontro')} slot={2} />
              <GraficoMensal titulo="Doações confirmadas" serie={serie('doacoes_confirmadas')} slot={3} />
            </div>
          )}

          <div className="duas-tabelas" style={{ marginTop: '1.5rem' }}>
            <Tabela titulo={`Contas ativas (${Object.values(contas).reduce((a, b) => a + b, 0)})`} linhas={dados.contas} rotulos={ROTULO_TIPO} />
            <Tabela titulo="Abrigos" linhas={dados.abrigos} rotulos={STATUS_VALIDACAO} />
            <Tabela titulo="Animais por situação (hoje)" linhas={dados.animais} rotulos={STATUS_ANIMAL} />
          </div>

          <div className="topo-pagina">
            <h2 style={{ margin: 0 }}>Últimas ações</h2>
            <Link className="botao botao--leve botao--pequeno" to="/admin?aba=historico">Ver histórico completo</Link>
          </div>
          <div className="cartao rolagem">
            <table className="historico">
              <tbody>
                {dados.ultimas_acoes.map((l) => (
                  <tr key={l.id}>
                    <td>{new Date(l.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</td>
                    <td>{l.usuario_nome}<small>{ROTULO_TIPO[l.tipo_conta]}</small></td>
                    <td>{l.rotulo}{l.detalhes.animal && ` · ${l.detalhes.animal}`}{l.detalhes.item && ` · ${l.detalhes.item}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
