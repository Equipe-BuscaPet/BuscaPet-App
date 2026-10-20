// Apoio dos testes E2E: contas e registros são criados direto pela API (rápido) com e-mail único,
// para cada teste ser independente dos outros e de qualquer dado que já exista no banco.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect } from '@playwright/test'

export const API = process.env.API_URL || 'http://localhost:8100' // API de teste (playwright.config.js)
export const SENHA = 'Senha1234!'
export const RECIFE = { latitude: -8.0476, longitude: -34.877 } // centro inicial dos mapas

export const caminhoFoto = (nome) => fileURLToPath(new URL(`./fixtures/${nome}`, import.meta.url))

const unico = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`

// CNPJ válido e diferente a cada chamada (o CNPJ do apoiador é único no banco).
export function cnpjAleatorio() {
  const base = Array.from({ length: 8 }, () => Math.floor(Math.random() * 10)).concat([0, 0, 0, 1])
  const digito = (nums, pesos) => {
    const r = nums.reduce((s, n, i) => s + n * pesos[i], 0) % 11
    return r < 2 ? 0 : 11 - r
  }
  const d1 = digito(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
  const d2 = digito([...base, d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
  return [...base, d1, d2].join('')
}

const EXTRAS = {
  tutor: () => ({}),
  abrigo: () => ({ nome_abrigo: 'Abrigo de Teste E2E', endereco: 'Rua dos Testes, 100', latitude: -8.05, longitude: -34.9 }),
  apoiador: () => ({ cnpj: cnpjAleatorio(), tipo_estabelecimento: 'petshop', endereco: 'Rua dos Apoiadores, 1' }),
}

export async function criarConta(request, tipo = 'tutor') {
  const sufixo = unico()
  const conta = { tipo_conta: tipo, nome: `Teste ${tipo} ${sufixo}`, email: `e2e-${tipo}-${sufixo}@teste.buscapet.dev`, senha: SENHA, ...EXTRAS[tipo]() }
  const cadastro = await request.post(`${API}/auth/cadastro`, { data: conta })
  expect(cadastro.ok(), await cadastro.text()).toBeTruthy()
  const login = await request.post(`${API}/auth/login`, { form: { username: conta.email, password: SENHA } })
  expect(login.ok()).toBeTruthy()
  const { access_token: token, usuario } = await login.json()
  return { ...conta, token, usuario }
}

// Administrador só de teste, criado por api/app/scripts/preparar_banco_teste.py.
const ADMIN_E2E = 'admin-e2e@teste.buscapet.dev'

// Concede o selo Verificado a um abrigo (só abrigo verificado publica necessidades e recebe doações).
export async function verificarAbrigo(request, abrigo) {
  const login = await request.post(`${API}/auth/login`, { form: { username: ADMIN_E2E, password: SENHA } })
  expect(login.ok(), 'admin de teste: rode o e2e pelo Playwright para o banco ser preparado').toBeTruthy()
  const { access_token: token } = await login.json()
  const r = await request.patch(`${API}/admin/abrigos/${abrigo.usuario.id}/validacao`, {
    headers: { Authorization: `Bearer ${token}` }, data: { status: 'aprovado' },
  })
  expect(r.ok(), await r.text()).toBeTruthy()
}

export async function publicarNecessidade(request, abrigo, campos = {}) {
  const r = await request.post(`${API}/necessidades`, {
    headers: { Authorization: `Bearer ${abrigo.token}` }, data: { item: `Ração ${unico()}`, quantidade: 3, urgencia: 'alta', ...campos },
  })
  expect(r.status(), await r.text()).toBe(201)
  return r.json()
}

// Abre o site já logado: grava o token como o próprio frontend faz (src/api.js).
export async function entrarComo(page, conta) {
  await page.addInitScript((t) => window.localStorage.setItem('buscapet_token', t), conta.token)
}

const autorizacao = (conta) => ({ Authorization: `Bearer ${conta.token}` })

function multipartRegistro(campos, foto = 'gato-cinza.jpg') {
  return {
    ...Object.fromEntries(Object.entries(campos).map(([k, v]) => [k, String(v)])),
    fotos: { name: foto, mimeType: 'image/jpeg', buffer: readFileSync(caminhoFoto(foto)) },
  }
}

export async function criarPerdido(request, conta, campos = {}) {
  const r = await request.post(`${API}/perdidos`, {
    headers: autorizacao(conta),
    multipart: multipartRegistro({
      especie: 'gato', porte: 'pequeno', cor_predominante: 'Cinza', ...RECIFE, data_desaparecimento: '2026-10-10', raio_busca_km: 5, ...campos,
    }),
  })
  expect(r.status(), await r.text()).toBe(201)
  return r.json()
}

export async function criarAvistamento(request, conta, campos = {}) {
  const r = await request.post(`${API}/avistamentos`, {
    headers: autorizacao(conta),
    multipart: multipartRegistro({ especie: 'cao', porte: 'medio', cor_predominante: 'Caramelo', ...RECIFE, data_avistamento: '2026-10-12', ...campos }, 'cachorro-caramelo.jpg'),
  })
  expect(r.status(), await r.text()).toBe(201)
  return r.json()
}

export async function criarAnimal(request, abrigo, campos = {}) {
  const r = await request.post(`${API}/animais`, {
    headers: autorizacao(abrigo),
    data: { nome: `Bidu ${unico()}`, especie: 'cao', porte: 'medio', sexo: 'macho', ...campos },
  })
  expect(r.status(), await r.text()).toBe(201)
  return r.json()
}
