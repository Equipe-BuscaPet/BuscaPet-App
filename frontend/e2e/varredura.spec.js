import { expect, test } from '@playwright/test'
import { API, contaAdmin, criarAnimal, criarAvistamento, criarConta, criarPerdido, entrarComo, publicarNecessidade, verificarAbrigo } from './apoio'

// Sprint 9 — teste de navegação por varredura: para cada perfil, parte das telas principais e dos menus, visita
// TODOS os links internos encontrados e falha se aparecer erro no console, erro 5xx da API, "Página não encontrada"
// ou "não tem acesso" num link que o próprio perfil recebeu no menu.

test.describe.configure({ mode: 'serial' }) // um perfil por vez: a varredura pesa na máquina

const MAX_PAGINAS = 45
const INICIO = ['/', '/mapa', '/mapa?ver=animais', '/reencontro', '/quem-apoia', '/login', '/cadastro', '/esqueci-senha']
const DO_PERFIL = {
  visitante: [],
  tutor: ['/conta', '/notificacoes', '/interesses', '/meus-registros', '/perdi', '/encontrei'],
  abrigo: ['/conta', '/notificacoes', '/painel', '/interessados', '/doacoes', '/relatorios', '/relatorios?aba=historico', '/meus-registros'],
  apoiador: ['/conta', '/notificacoes', '/minhas-doacoes', '/meus-registros'],
  admin: ['/conta', '/notificacoes', '/admin', '/admin?aba=abrigos', '/admin?aba=denuncias', '/admin?aba=historico', '/admin?aba=contas'],
}

async function cenario(request) {
  const abrigo = await criarConta(request, 'abrigo')
  await verificarAbrigo(request, abrigo)
  const animal = await criarAnimal(request, abrigo)
  await publicarNecessidade(request, abrigo)
  const tutor = await criarConta(request, 'tutor')
  await criarPerdido(request, tutor)
  await criarAvistamento(request, tutor)
  await request.post(`${API}/animais/${animal.id}/interesses`, { headers: { Authorization: `Bearer ${tutor.token}` }, data: {} })
  return { abrigo, tutor, apoiador: await criarConta(request, 'apoiador'), admin: await contaAdmin(request), animal }
}

async function varrer(page, perfil, contas, extras = [], maximo = MAX_PAGINAS) {
  const problemas = []
  page.on('console', (m) => { if (m.type() === 'error') problemas.push(`console em ${page.url()}: ${m.text()}`) })
  page.on('pageerror', (e) => problemas.push(`erro de script em ${page.url()}: ${e.message}`))
  page.on('response', (r) => { if (r.url().startsWith(API) && r.status() >= 500) problemas.push(`API ${r.status()} em ${r.url()}`) })
  if (contas[perfil]) await entrarComo(page, contas[perfil])

  const fila = [...extras, ...INICIO, ...DO_PERFIL[perfil], `/animais/${contas.animal.id}`, `/abrigos/${contas.abrigo.usuario.id}`]
  const doMenu = new Set(DO_PERFIL[perfil])
  const visitados = new Set()
  while (fila.length && visitados.size < maximo) {
    const url = fila.shift()
    if (visitados.has(url)) continue
    visitados.add(url)
    await page.goto(url)
    await page.waitForLoadState('networkidle')
    const texto = await page.locator('main').first().innerText().catch(() => '')
    if (texto.includes('Página não encontrada')) problemas.push(`página não encontrada: ${url}`)
    if (doMenu.has(url) && texto.includes('não tem acesso')) problemas.push(`o menu de ${perfil} leva a uma tela sem acesso: ${url}`)
    if (perfil !== 'visitante' && visitados.size === 1) {
      // Os links do menu da conta (☰) também entram na varredura e não podem dar "sem acesso".
      await page.getByRole('button', { name: 'Menu da conta' }).click()
      for (const href of await page.getByRole('navigation', { name: 'Menu da conta' }).locator('a').evaluateAll((as) => as.map((a) => a.getAttribute('href')))) {
        doMenu.add(href)
        fila.push(href)
      }
      await page.keyboard.press('Escape')
    }
    const links = await page.locator('a[href^="/"]').evaluateAll((as) => as.map((a) => a.getAttribute('href')))
    for (const href of links) if (!visitados.has(href) && !href.startsWith('/fotos/')) fila.push(href)
  }
  return { problemas, visitados: visitados.size }
}

let contas
test.beforeAll(async ({ request }) => { contas = await cenario(request) })

for (const perfil of Object.keys(DO_PERFIL)) {
  test(`varredura de navegação: ${perfil}`, async ({ page }) => {
    test.setTimeout(240_000)
    const { problemas, visitados } = await varrer(page, perfil, perfil === 'visitante' ? { ...contas, visitante: null } : contas)
    console.log(`[varredura] ${perfil}: ${visitados} páginas visitadas, ${problemas.length} problema(s)`)
    expect(problemas, problemas.join('\n')).toEqual([])
    expect(visitados).toBeGreaterThan(10)
  })
}

test('autoverificação: a varredura acusa um endereço que não existe', async ({ page }) => {
  // Garante que a varredura não passa "às cegas": um link quebrado de propósito tem de aparecer como problema.
  const { problemas } = await varrer(page, 'visitante', { ...contas, visitante: null }, ['/isto-nao-existe'], 3)
  expect(problemas).toContain('página não encontrada: /isto-nao-existe')
})
