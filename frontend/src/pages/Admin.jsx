import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import HistoricoOperacoes from '../componentes/HistoricoOperacoes'
import { STATUS_VALIDACAO } from '../rotulos'
import DesempenhoNucleo from './DesempenhoNucleo'
import ModeracaoDenuncias from './ModeracaoDenuncias'
import PainelAdmin from './PainelAdmin'
import PesquisaContas from './PesquisaContas'

const ABAS = ['pendente', 'aprovado', 'rejeitado']

function VerificarAbrigos() {
  const [aba, setAba] = useState('pendente')
  const [abrigos, setAbrigos] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro('')
    try {
      setAbrigos(await api(`/admin/abrigos?status=${aba}`))
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }, [aba])

  useEffect(() => { carregar() }, [carregar])

  async function decidir(abrigo, status) {
    setErro('')
    setOk('')
    try {
      await api(`/admin/abrigos/${abrigo.id}/validacao`, { metodo: 'PATCH', corpo: { status } })
      setOk(`${abrigo.perfil.nome_abrigo}: ${{ aprovado: 'selo Verificado concedido', rejeitado: 'abrigo suspenso', pendente: 'voltou para não verificado' }[status]}.`)
      await carregar()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <section aria-label="Verificação de abrigos">
      <p className="subtitulo">Todo abrigo opera assim que se cadastra. Aqui você concede o selo Verificado (necessário para publicar no mural, receber doações e exibir a chave PIX) ou suspende um abrigo suspeito, que some do catálogo.</p>

      <div className="acoes" role="tablist" aria-label="Situação" style={{ marginBottom: '1rem' }}>
        {ABAS.map((a) => (
          <button key={a} role="tab" aria-selected={aba === a} className={`botao ${aba === a ? '' : 'botao--leve'}`} onClick={() => setAba(a)}>
            {STATUS_VALIDACAO[a]}s
          </button>
        ))}
      </div>

      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {carregando && <p className="estado">Carregando…</p>}
      {!carregando && abrigos.length === 0 && <p className="estado">Nenhum abrigo {STATUS_VALIDACAO[aba].toLowerCase()}.</p>}

      <div style={{ display: 'grid', gap: '1rem' }}>
        {abrigos.map((u) => (
          <article key={u.id} className="cartao">
            <div className="topo-pagina" style={{ marginBottom: '0.5rem' }}>
              <div>
                <h2 style={{ marginBottom: 0 }}>{u.perfil.nome_abrigo}</h2>
                <small>Responsável: {u.nome} · {u.email}</small>
              </div>
              <span className={`etiqueta ${u.perfil.status_validacao === 'aprovado' ? 'etiqueta--ok' : u.perfil.status_validacao === 'rejeitado' ? 'etiqueta--erro' : 'etiqueta--atencao'}`}>
                {STATUS_VALIDACAO[u.perfil.status_validacao]}
              </span>
            </div>
            <div className="detalhe">
              <dl>
                <dt>Endereço</dt><dd>{u.perfil.endereco}</dd>
                <dt>Localização</dt><dd>{u.perfil.latitude}, {u.perfil.longitude}</dd>
                {u.perfil.telefone && <><dt>Telefone</dt><dd>{u.perfil.telefone}</dd></>}
                {u.perfil.descricao && <><dt>Sobre</dt><dd>{u.perfil.descricao}</dd></>}
              </dl>
            </div>
            <div className="acoes" style={{ marginTop: '0.75rem' }}>
              {u.perfil.status_validacao !== 'aprovado' && <button className="botao" onClick={() => decidir(u, 'aprovado')}>Verificar</button>}
              {u.perfil.status_validacao !== 'rejeitado' && <button className="botao botao--leve" onClick={() => decidir(u, 'rejeitado')}>Suspender</button>}
              {u.perfil.status_validacao !== 'pendente' && <button className="botao botao--leve" onClick={() => decidir(u, 'pendente')}>{u.perfil.status_validacao === 'aprovado' ? 'Remover selo' : 'Reativar'}</button>}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

const ABAS_ADMIN = [
  ['painel', 'Painel'],
  ['abrigos', 'Verificar abrigos'],
  ['denuncias', 'Denúncias'],
  ['historico', 'Histórico de operações'],
  ['contas', 'Contas'],
  ['nucleo', 'Núcleo OpenCL'],
]

// Área da administração (RF-38, RF-39): painel com indicadores, verificação de abrigos, histórico e pesquisa de contas.
export default function Admin() {
  const [params, setParams] = useSearchParams()
  const aba = ABAS_ADMIN.some(([v]) => v === params.get('aba')) ? params.get('aba') : 'painel'
  return (
    <main className="pagina">
      <h1>Administração</h1>
      <div className="abas" role="tablist" aria-label="Área da administração" style={{ marginBottom: '1.25rem' }}>
        {ABAS_ADMIN.map(([valor, rotulo]) => (
          <button key={valor} role="tab" aria-selected={aba === valor} className={`abas__item${aba === valor ? ' abas__item--ativa' : ''}`}
            onClick={() => setParams(valor === 'painel' ? {} : { aba: valor })}>
            {rotulo}
          </button>
        ))}
      </div>
      {aba === 'painel' && <PainelAdmin />}
      {aba === 'abrigos' && <VerificarAbrigos />}
      {aba === 'denuncias' && <ModeracaoDenuncias />}
      {aba === 'historico' && <HistoricoOperacoes rota="/admin/logs" rotaCsv="/admin/logs.csv" />}
      {aba === 'contas' && <PesquisaContas />}
      {aba === 'nucleo' && <DesempenhoNucleo />}
    </main>
  )
}
