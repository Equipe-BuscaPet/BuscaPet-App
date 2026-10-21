import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { paraCentavos, reais } from '../rotulos'

// Área do abrigo: define a meta de gastos do mês (dinheiro via PIX) e acompanha quanto já foi confirmado.
// A meta só aparece no perfil público com o selo Verificado e a chave PIX cadastrada.
export default function MetaDoMes({ verificado, aoMudar }) {
  const { usuario, atualizarUsuario } = useAuth()
  const perfil = usuario.perfil || {}
  const [meta, setMeta] = useState(null)
  const [editando, setEditando] = useState(false)
  const [valor, setValor] = useState('')
  const [descricao, setDescricao] = useState('')
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const carregar = useCallback(() => {
    api(`/abrigos/${usuario.id}`).then((a) => setMeta(a.meta_mensal)).catch(() => setMeta(null))
  }, [usuario.id])
  useEffect(() => { carregar() }, [carregar])

  function abrir() {
    setValor(perfil.meta_mensal_centavos ? String(perfil.meta_mensal_centavos / 100).replace('.', ',') : '')
    setDescricao(perfil.meta_mensal_descricao || '')
    setErro('')
    setOk('')
    setEditando(true)
  }

  async function salvar(corpo, mensagem) {
    setErro('')
    try {
      await api('/usuarios/eu', { metodo: 'PATCH', corpo })
      await atualizarUsuario()
      setEditando(false)
      setOk(mensagem)
      carregar()
      aoMudar?.()
    } catch (e) {
      setErro(e.message)
    }
  }

  function enviar(e) {
    e.preventDefault()
    const centavos = paraCentavos(valor)
    if (centavos === null || centavos < 100) {
      setErro('Informe a meta em reais, a partir de R$ 1,00 (ex.: 3000 ou 3.000,00).')
      return
    }
    salvar({ meta_mensal_centavos: centavos, meta_mensal_descricao: descricao.trim() || null }, `Meta do mês definida: ${reais(centavos)}.`)
  }

  if (!verificado) return null
  const pct = meta ? Math.min(100, Math.round((meta.arrecadado_centavos / meta.valor_centavos) * 100)) : 0

  return (
    <section className="cartao doar-dinheiro" aria-labelledby="t-meta" style={{ marginBottom: '2rem' }}>
      <h2 id="t-meta" style={{ margin: 0 }}>Meta do mês em dinheiro</h2>
      <p className="progresso__texto">
        Quem apoia faz o PIX para a chave do abrigo e informa o valor; quando você confirma que o dinheiro chegou, a meta avança.
      </p>
      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {!perfil.chave_doacao_financeira && (
        <div className="aviso aviso--atencao" style={{ margin: 0 }}>
          Para receber em dinheiro, cadastre a chave PIX do abrigo em <Link to="/conta">Minha conta</Link>.
        </div>
      )}

      {meta && !editando && (
        <>
          <p className="doar-dinheiro__valores"><strong>{reais(meta.arrecadado_centavos)}</strong> de {reais(meta.valor_centavos)}</p>
          <div className="progresso" role="progressbar" aria-valuemin={0} aria-valuemax={meta.valor_centavos} aria-valuenow={meta.arrecadado_centavos}
            aria-valuetext={`${reais(meta.arrecadado_centavos)} de ${reais(meta.valor_centavos)}`} aria-label="Meta do mês">
            <div className="progresso__barra" style={{ width: `${pct}%` }} />
          </div>
          {meta.descricao && <p className="progresso__texto">Para que serve: {meta.descricao}</p>}
        </>
      )}
      {!meta && !editando && perfil.chave_doacao_financeira && (
        <p className="estado" style={{ padding: 0 }}>Nenhuma meta definida. Com ela, quem visita o perfil vê quanto falta para fechar as contas do mês.</p>
      )}

      {editando ? (
        <form className="formulario" onSubmit={enviar}>
          <div className="grade-campos">
            <div className="campo">
              <label htmlFor="meta-valor">Meta do mês (R$)</label>
              <input id="meta-valor" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Ex.: 3.000,00" required />
            </div>
            <div className="campo" style={{ gridColumn: '1 / -1' }}>
              <label htmlFor="meta-descricao">Para que serve (aparece no perfil)</label>
              <input id="meta-descricao" value={descricao} onChange={(e) => setDescricao(e.target.value)} maxLength={500}
                placeholder="Ex.: ração R$ 1.500 · veterinário R$ 900 · contas R$ 600" />
            </div>
          </div>
          <div className="acoes">
            <button className="botao">Salvar meta</button>
            <button type="button" className="botao botao--leve" onClick={() => setEditando(false)}>Cancelar</button>
          </div>
        </form>
      ) : perfil.chave_doacao_financeira && (
        <div className="acoes">
          <button type="button" className="botao botao--leve botao--pequeno" onClick={abrir}>{perfil.meta_mensal_centavos ? 'Alterar meta' : 'Definir meta'}</button>
          {perfil.meta_mensal_centavos && (
            <button type="button" className="botao botao--leve botao--pequeno"
              onClick={() => window.confirm('Retirar a meta do perfil público?') && salvar({ meta_mensal_centavos: null, meta_mensal_descricao: null }, 'Meta retirada do perfil.')}>
              Retirar meta
            </button>
          )}
        </div>
      )}
    </section>
  )
}
