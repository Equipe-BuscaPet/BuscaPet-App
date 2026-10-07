// Cliente da API do backend (FastAPI). A URL vem de VITE_API_URL; o padrão é o
// backend rodando localmente.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const CHAVE_TOKEN = 'buscapet_token'

export const token = {
  ler: () => localStorage.getItem(CHAVE_TOKEN),
  salvar: (valor) => localStorage.setItem(CHAVE_TOKEN, valor),
  apagar: () => localStorage.removeItem(CHAVE_TOKEN),
}

export class ApiError extends Error {
  constructor(status, mensagem) {
    super(mensagem)
    this.status = status
  }
}

// O FastAPI devolve `detail` como texto (erros de regra) ou lista (validação de campos).
function mensagemDeErro(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).slice(1).join('.') || 'campo'}: ${d.msg}`)
      .join('; ')
  }
  return 'Erro inesperado. Tente novamente.'
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
    throw new ApiError(resposta.status, mensagemDeErro(dados?.detail))
  }
  return dados
}
