import { readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { API, SENHA, caminhoFoto, contaAdmin, criarAnimal, criarConta, entrarComo, verificarAbrigo } from './apoio'

// Sprint 8: recuperação de senha (RF-05) com o e-mail de verdade, fotos dos animais (RF-17),
// denúncia e moderação (RF-41) e melhorias de usabilidade.

// A API de teste, sem SMTP, grava os e-mails em api/caixa-de-saida (ver api/app/core/email.py).
const CAIXA = fileURLToPath(new URL('../../api/caixa-de-saida/', import.meta.url))

async function ultimoEmailPara(email) {
  let texto = null
  await expect.poll(() => {
    const arquivos = readdirSync(CAIXA).filter((n) => n.endsWith('.eml')).sort().reverse()
    // Decodifica como um leitor de e-mail: o corpo vem em quoted-printable (linhas longas quebradas com "=").
    const decodificar = (bruto) => bruto.replace(/=\r?\n/g, '').replace(/=([0-9A-F]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16)))
    texto = arquivos.map((n) => decodificar(readFileSync(CAIXA + n, 'utf-8'))).find((t) => t.includes(`To: ${email}`)) || null
    return texto
  }, { message: `e-mail para ${email}` }).not.toBeNull()
  return texto
}

test('quem esqueceu a senha recebe o link por e-mail e cria uma nova', async ({ page, request }) => {
  const tutor = await criarConta(request, 'tutor')
  await page.goto('/login')
  await page.getByRole('link', { name: 'Esqueci minha senha' }).click()
  await page.getByLabel('E-mail').fill(tutor.email)
  await page.getByRole('button', { name: 'Enviar link' }).click()
  await expect(page.getByRole('status')).toContainText('Se houver uma conta com este e-mail')

  const email = await ultimoEmailPara(tutor.email)
  const caminho = /\/redefinir-senha\?token=\S+/.exec(email)[0]
  await page.goto(caminho)
  await page.getByLabel('Nova senha', { exact: true }).fill('NovaSenha123!')
  await page.getByLabel('Repita a nova senha').fill('NovaSenha123!')
  await page.getByRole('button', { name: 'Salvar nova senha' }).click()
  await expect(page.getByRole('status')).toHaveText('Senha alterada. Entre com a nova senha.')

  await page.getByLabel('E-mail').fill(tutor.email)
  await page.getByLabel('Senha', { exact: true }).fill('NovaSenha123!')
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Menu da conta' })).toBeVisible()

  await page.goto(caminho) // o mesmo link não serve de novo
  await page.getByLabel('Nova senha', { exact: true }).fill('OutraSenha123!')
  await page.getByLabel('Repita a nova senha').fill('OutraSenha123!')
  await page.getByRole('button', { name: 'Salvar nova senha' }).click()
  await expect(page.getByRole('alert')).toContainText('já foi usado')
})

test('o abrigo envia fotos, escolhe a capa e ela aparece no catálogo e na ficha', async ({ page, request }) => {
  const abrigo = await criarConta(request, 'abrigo')
  const animal = await criarAnimal(request, abrigo)
  await entrarComo(page, abrigo)
  await page.goto('/painel')
  await page.getByRole('row', { name: new RegExp(animal.nome) }).getByRole('button', { name: 'Editar' }).click()
  await page.getByLabel('Adicionar fotos').setInputFiles([caminhoFoto('cachorro-caramelo.jpg'), caminhoFoto('gato-cinza.jpg')])
  const fotos = page.getByRole('list', { name: `Fotos de ${animal.nome}` })
  await expect(fotos.locator('img')).toHaveCount(2)
  await fotos.getByRole('button', { name: 'Tornar capa' }).click()
  await expect(fotos.locator('li').first().getByText('Capa')).toBeVisible()
  const capa = await fotos.locator('li').first().locator('img').getAttribute('src')

  await page.goto(`/?abrigo=${abrigo.usuario.id}`)
  await expect(page.locator(`a[href="/animais/${animal.id}"] img`)).toHaveAttribute('src', capa)
  await page.goto(`/animais/${animal.id}`)
  await expect(page.getByRole('img', { name: `${animal.nome}, foto 1 de 2` })).toHaveAttribute('src', capa)
  await page.getByRole('button', { name: 'Ver foto 2' }).click()
  await expect(page.getByRole('img', { name: `${animal.nome}, foto 2 de 2` })).toBeVisible()
})

test('a denúncia chega à administração, que remove o anúncio', async ({ page, request, browser }) => {
  const abrigo = await criarConta(request, 'abrigo')
  await verificarAbrigo(request, abrigo)
  const animal = await criarAnimal(request, abrigo)
  await entrarComo(page, await criarConta(request, 'tutor'))
  await page.goto(`/animais/${animal.id}`)
  await page.getByRole('button', { name: /Denunciar este anúncio/ }).click()
  await page.getByLabel('O que há de errado neste anúncio?').fill('Estão cobrando pela adoção pelo WhatsApp.')
  await page.getByRole('button', { name: 'Enviar denúncia' }).click()
  await expect(page.getByRole('status')).toHaveText('Denúncia registrada. A administração vai analisar o anúncio.')

  const admin = await (await browser.newContext()).newPage()
  await entrarComo(admin, await contaAdmin(request))
  await admin.goto('/admin?aba=denuncias')
  const cartao = admin.getByRole('article', { name: `Denúncia sobre ${animal.nome}` })
  await expect(cartao).toContainText('Estão cobrando pela adoção')
  admin.once('dialog', (d) => d.accept())
  await cartao.getByRole('button', { name: 'Remover o anúncio' }).click()
  await expect(admin.getByRole('status')).toContainText('Remover o anúncio: feito.')

  const r = await request.get(`${API}/animais/${animal.id}`)
  expect(r.status()).toBe(404) // saiu do ar para o público
})

test('o próprio abrigo não vê o botão de denunciar seu anúncio', async ({ page, request }) => {
  const abrigo = await criarConta(request, 'abrigo')
  const animal = await criarAnimal(request, abrigo)
  await entrarComo(page, abrigo)
  await page.goto(`/animais/${animal.id}`)
  await expect(page.getByRole('heading', { name: animal.nome })).toBeVisible()
  await expect(page.getByRole('button', { name: /Denunciar este anúncio/ })).toHaveCount(0)
})

test('usabilidade: mostrar a senha, pular para o conteúdo e título da página', async ({ page }) => {
  await page.goto('/login')
  await expect(page).toHaveTitle('Entrar · BuscaPet')
  const senha = page.getByLabel('Senha', { exact: true })
  await senha.fill(SENHA)
  await expect(senha).toHaveAttribute('type', 'password')
  await page.getByRole('button', { name: 'Mostrar' }).click()
  await expect(senha).toHaveAttribute('type', 'text')

  await page.goto('/quem-apoia')
  await expect(page).toHaveTitle('Quem apoia · BuscaPet')
  await page.keyboard.press('Tab')
  const pular = page.getByRole('link', { name: 'Pular para o conteúdo' })
  await expect(pular).toBeFocused()
  await pular.press('Enter')
  await expect(page.locator('#conteudo')).toBeFocused()
})

test('sem permissão de localização, a pessoa marca a própria posição no mapa (RF-11)', async ({ page }) => {
  await page.goto('/mapa')
  await page.getByRole('button', { name: /Perto de mim/ }).click()
  await expect(page.getByRole('status')).toContainText('Não foi possível obter sua localização')
  await page.getByRole('button', { name: 'marcar sua posição no mapa' }).click()
  await expect(page.getByRole('status')).toContainText('Clique no mapa no lugar onde você está.')
  await page.locator('.mapa').first().click({ position: { x: 120, y: 120 } })
  await expect(page.getByText('mais perto primeiro')).toBeVisible()
  await expect(page.getByRole('button', { name: /Perto de mim/ })).toHaveAttribute('aria-pressed', 'true')
})

test('clicar no ponto do mapa destaca o item na lista (RF-09)', async ({ page, request }) => {
  await criarConta(request, 'abrigo') // garante pelo menos um abrigo no mapa
  await page.goto('/mapa')
  await expect(page.locator('.lista-abrigos li').first()).toBeVisible()
  await page.locator('path.leaflet-interactive').first().click({ force: true })
  await expect(page.locator('.lista-abrigos li.item-destacado')).toHaveCount(1)
})

test('filtros combinados do catálogo (RF-14)', async ({ page, request }) => {
  const abrigo = await criarConta(request, 'abrigo')
  const idoso = await criarAnimal(request, abrigo, { idade_estimada_meses: 130, castrado: true })
  const filhote = await criarAnimal(request, abrigo, { idade_estimada_meses: 3 })
  await page.goto(`/?abrigo=${abrigo.usuario.id}`)
  await page.getByRole('button', { name: 'Mais filtros' }).click()
  await page.getByLabel('Idade').selectOption('idoso')
  await expect(page.getByRole('button', { name: 'Mais filtros (1)' })).toBeVisible()
  await expect(page.locator(`a[href="/animais/${idoso.id}"]`)).toBeVisible()
  await expect(page.locator(`a[href="/animais/${filhote.id}"]`)).toHaveCount(0)
  await page.getByLabel('Castrado').check()
  await expect(page.locator(`a[href="/animais/${idoso.id}"]`)).toBeVisible()
  await page.getByRole('button', { name: 'Limpar estes filtros' }).click()
  await expect(page.locator(`a[href="/animais/${filhote.id}"]`)).toBeVisible()
})
