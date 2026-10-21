import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { paraCentavos, reais } from '../rotulos'

const NOME_MES = (aaaaMm) => new Date(`${aaaaMm}-15T12:00:00`).toLocaleDateString('pt-BR', { month: 'long' })

// Meta de gastos do mês e doação em dinheiro (só para abrigo verificado com chave PIX). A BuscaPet não processa
// pagamentos: quem doa faz o PIX no app do banco e informa o valor aqui; a meta avança quando o abrigo confirma.
export default function DoarDinheiro({ abrigo, aoDoar }) {
  const { usuario } = useAuth()
  const { pathname } = useLocation()
  const [valor, setValor] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  const [copiada, setCopiada] = useState(false)
  const meta = abrigo.meta_mensal
  const pct = meta ? Math.min(100, Math.round((meta.arrecadado_centavos / meta.valor_centavos) * 100)) : 0
  const podeDoar = ['tutor', 'apoiador'].includes(usuario?.tipo_conta)

  async function copiar() {
    try {
      await navigator.clipboard.writeText(abrigo.chave_doacao_financeira)
      setCopiada(true)
    } catch {
      setCopiada(false)
    }
  }

  async function informar(e) {
    e.preventDefault()
    setErro('')
    const centavos = paraCentavos(valor)
    if (centavos === null || centavos < 100) {
      setErro('Informe o valor que você enviou, a partir de R$ 1,00 (ex.: 50 ou 50,00).')
      return
    }
    setEnviando(true)
    try {
      await api('/doacoes', { metodo: 'POST', corpo: { abrigo_id: abrigo.id, valor_centavos: centavos } })
      setOk(`Obrigado! Avisamos o ${abrigo.nome_abrigo} do seu PIX de ${reais(centavos)}. A meta avança quando o abrigo confirmar que recebeu. Acompanhe em Minhas doações.`)
      setValor('')
      aoDoar?.()
    } catch (err) {
      setErro(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="cartao doar-dinheiro" aria-labelledby="t-dinheiro">
      <h2 id="t-dinheiro" style={{ margin: 0 }}>{meta ? `Meta de ${NOME_MES(meta.mes)}` : 'Doe em dinheiro'}</h2>
      {meta && (
        <>
          <p className="doar-dinheiro__valores">
            <strong>{reais(meta.arrecadado_centavos)}</strong> de {reais(meta.valor_centavos)}
            <small> · {meta.doacoes_confirmadas} {meta.doacoes_confirmadas === 1 ? 'doação confirmada' : 'doações confirmadas'}</small>
          </p>
          <div className="progresso" role="progressbar" aria-valuemin={0} aria-valuemax={meta.valor_centavos} aria-valuenow={meta.arrecadado_centavos}
            aria-valuetext={`${reais(meta.arrecadado_centavos)} de ${reais(meta.valor_centavos)}`} aria-label="Meta do mês">
            <div className="progresso__barra" style={{ width: `${pct}%` }} />
          </div>
          {meta.descricao && <p className="progresso__texto">Para que serve: {meta.descricao}</p>}
        </>
      )}

      <div className="pix">
        <small>Faça o PIX direto para o abrigo, pelo app do seu banco (a BuscaPet não intermedia pagamentos):</small>
        <p style={{ margin: '0.25rem 0 0' }}>
          Chave PIX: <code>{abrigo.chave_doacao_financeira}</code>{' '}
          <button type="button" className="botao botao--leve botao--pequeno" onClick={copiar}>{copiada ? 'Copiada ✓' : 'Copiar'}</button>
        </p>
      </div>

      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {podeDoar && !ok && (
        <form className="doar" onSubmit={informar}>
          <div className="campo">
            <label htmlFor="valor-pix">Já fez o PIX? Informe o valor (R$)</label>
            <input id="valor-pix" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Ex.: 50,00" required />
          </div>
          <button className="botao" disabled={enviando}>{enviando ? 'Enviando…' : 'Informar doação'}</button>
        </form>
      )}
      {!usuario && (
        <p className="progresso__texto">
          <Link to={`/login?voltar=${encodeURIComponent(pathname)}`}>Entre</Link> ou <Link to="/cadastro">crie sua conta</Link> para
          informar a sua doação e aparecer no ranking de quem apoia.
        </p>
      )}
    </section>
  )
}
