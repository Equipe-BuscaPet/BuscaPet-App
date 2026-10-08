// Cliente da API do backend (FastAPI). A URL vem de VITE_API_URL; o padrão é o
// backend rodando localmente.
import { ROTULO_CAMPO } from './rotulos'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const CHAVE_TOKEN = 'buscapet_token'

export const token = {
  ler: () => localStorage.getItem(CHAVE_TOKEN),
  salvar: (valor) => localStorage.setItem(CHAVE_TOKEN, valor),
  apagar: () => localStorage.removeItem(CHAVE_TOKEN),
}

export class ApiError extends Error {
  // `campos` mapeia o nome do campo com problema para a mensagem em português
  // (usado para destacar os campos do formulário).
  constructor(status, mensagem, campos = {}) {
    super(mensagem)
    this.status = status
    this.campos = campos
  }
}

const ERRO_GENERICO = 'Algo deu errado do nosso lado. Tente novamente em instantes.'

// Traduz um erro de validação do FastAPI/Pydantic para uma frase em português, sem jargão técnico.
function frase(d) {
  const ctx = d.ctx || {}
  switch (d.type) {
    case 'missing': return 'preencha este campo.'
    case 'string_too_short': return ctx.min_length === 1 ? 'preencha este campo.' : `use pelo menos ${ctx.min_length} caracteres.`
    case 'string_too_long': return `use no máximo ${ctx.max_length} caracteres.`
    case 'greater_than_equal': return `o valor mínimo é ${ctx.ge}.`
    case 'less_than_equal': return `o valor máximo é ${ctx.le}.`
    case 'greater_than': return `o valor deve ser maior que ${ctx.gt}.`
    case 'less_than': return `o valor deve ser menor que ${ctx.lt}.`
    case 'enum':
    case 'literal_error': return 'escolha uma das opções disponíveis.'
    case 'int_parsing':
    case 'int_from_float':
    case 'float_parsing': return 'informe um número válido.'
    case 'bool_parsing': return 'escolha Sim ou Não.'
    case 'date_parsing':
    case 'date_from_datetime_parsing': return 'informe uma data válida.'
    case 'value_error': {
      const msg = String(d.msg || '')
      if (/e-?mail/i.test(msg)) return 'informe um e-mail válido (exemplo: nome@dominio.com).'
      // Mensagens escritas por nós nos validadores já estão em português.
      return msg.replace(/^Value error, /, '').replace(/^./, (c) => c.toLowerCase())
    }
    default: return 'valor inválido.'
  }
}

// O FastAPI devolve `detail` como texto (erros de regra) ou lista (validação de campos).
function interpretarErro(status, detail) {
  if (typeof detail === 'string') return { mensagem: detail, campos: {} }
  if (Array.isArray(detail)) {
    const campos = {}
    const linhas = detail.map((d) => {
      const nome = (d.loc || []).slice(-1)[0] || ''
      const rotulo = ROTULO_CAMPO[nome] || nome || 'Campo'
      const texto = frase(d)
      if (nome && !campos[nome]) campos[nome] = texto.charAt(0).toUpperCase() + texto.slice(1)
      return `${rotulo}: ${texto}`
    })
    return { mensagem: `Confira os dados informados — ${linhas.join(' ')}`, campos }
  }
  return { mensagem: status >= 500 ? ERRO_GENERICO : 'Não foi possível concluir a ação. Tente novamente.', campos: {} }
}

export async function api(caminho, { metodo = 'GET', corpo, formulario } = {}) {
  const headers = {}
  const jwt = token.ler()
  if (jwt) headers.Authorization = `Bearer ${jwt}`

  let body
  if (formulario) {
    body = new URLSearchParams(formulario)
  } else if (corpo !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(corpo)
  }

  let resposta
  try {
    resposta = await fetch(`${BASE}${caminho}`, { method: metodo, headers, body })
  } catch {
    throw new ApiError(0, 'Não foi possível falar com o servidor. Verifique se a API está rodando.')
  }

  if (resposta.status === 204) return null
  const dados = await resposta.json().catch(() => null)
  if (!resposta.ok) {
    if (resposta.status === 401 && jwt) window.dispatchEvent(new Event('buscapet:sessao-expirada'))
    const { mensagem, campos } = interpretarErro(resposta.status, dados?.detail)
    throw new ApiError(resposta.status, mensagem, campos)
  }
  return dados
}
