import { useEffect, useState } from 'react'
import { api } from '../api'
import { ROTULO_TIPO } from '../componentes/MenuConta'
import { useUltimoPedido } from '../useUltimoPedido'

// Pesquisa de contas para a administração: por nome, e-mail ou nome do abrigo, com filtros de tipo e situação.
export default function PesquisaContas() {
  const [texto, setTexto] = useState('')
  const [q, setQ] = useState('')
  const [tipo, setTipo] = useState('')
  const [ativo, setAtivo] = useState('')
  const [contas, setContas] = useState(null)
  const [erro, setErro] = useState('')
  const novoPedido = useUltimoPedido()

  useEffect(() => {
    const valido = novoPedido()
    const p = new URLSearchParams()
    if (q) p.set('q', q)
    if (tipo) p.set('tipo', tipo)
    if (ativo) p.set('ativo', ativo)
    api(`/admin/usuarios?${p}`).then((c) => valido() && setContas(c)).catch((e) => valido() && setErro(e.message))
  }, [q, tipo, ativo, novoPedido])

  return (
    <section aria-label="Pesquisa de contas">
      <form className="filtro-periodo" role="search" onSubmit={(e) => { e.preventDefault(); setQ(texto.trim()) }}>
        <div className="campo" style={{ minWidth: 260 }}>
          <label htmlFor="pesquisa-conta">Pesquisar</label>
          <input id="pesquisa-conta" type="search" value={texto} placeholder="Nome, e-mail ou nome do abrigo"
            onChange={(e) => { setTexto(e.target.value); if (!e.target.value) setQ('') }} />
        </div>
        <div className="campo">
          <label htmlFor="filtro-tipo">Tipo de conta</label>
          <select id="filtro-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(ROTULO_TIPO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="filtro-ativo">Situação</label>
          <select id="filtro-ativo" value={ativo} onChange={(e) => setAtivo(e.target.value)}>
            <option value="">Todas</option>
            <option value="true">Ativas</option>
            <option value="false">Desativadas</option>
          </select>
        </div>
        <button className="botao">Pesquisar</button>
      </form>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {contas === null && !erro && <p className="estado">Carregando…</p>}
      {contas && <p className="legenda" role="status">{contas.length} {contas.length === 1 ? 'conta encontrada' : 'contas encontradas'}</p>}
      {contas?.length > 0 && (
        <div className="cartao rolagem">
          <table>
            <thead><tr><th>Nome</th><th>E-mail</th><th>Tipo</th><th>Detalhe</th><th>Desde</th><th>Situação</th></tr></thead>
            <tbody>
              {contas.map((c) => (
                <tr key={c.id}>
                  <td>{c.nome}</td><td>{c.email}</td><td>{ROTULO_TIPO[c.tipo_conta]}</td><td>{c.detalhe || '—'}</td>
                  <td>{new Date(c.criado_em).toLocaleDateString('pt-BR')}</td>
                  <td><span className={`etiqueta ${c.ativo ? 'etiqueta--ok' : 'etiqueta--erro'}`}>{c.ativo ? 'Ativa' : 'Desativada'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
