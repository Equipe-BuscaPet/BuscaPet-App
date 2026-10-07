import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { STATUS_VALIDACAO } from '../rotulos'

const ABAS = ['pendente', 'aprovado', 'rejeitado']

export default function Admin() {
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
      setOk(`${abrigo.perfil.nome_abrigo} foi ${status === 'aprovado' ? 'aprovado' : 'rejeitado'}.`)
      await carregar()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <main className="pagina">
      <h1>Validação de abrigos</h1>
      <p className="subtitulo">Só abrigos aprovados podem publicar animais e aparecem no catálogo público.</p>

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
              {u.perfil.status_validacao !== 'aprovado' && <button className="botao" onClick={() => decidir(u, 'aprovado')}>Aprovar</button>}
              {u.perfil.status_validacao !== 'rejeitado' && <button className="botao botao--leve" onClick={() => decidir(u, 'rejeitado')}>Rejeitar</button>}
            </div>
          </article>
        ))}
      </div>
    </main>
  )
}
