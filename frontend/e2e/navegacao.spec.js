import { expect, test } from '@playwright/test'
import { SENHA, criarConta } from './apoio'

test.describe('Navegação', () => {
  test('o catálogo abre para visitantes @celular', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Animais para adoção' })).toBeVisible()
    await expect(page.getByLabel('Espécie')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Entrar' })).toBeVisible()
  })

  test('o menu leva a perdidos e achados @celular', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Perdidos e achados' }).click()
    await expect(page).toHaveURL(/\/reencontro$/)
    await expect(page.getByRole('heading', { name: 'Perdidos e achados' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Perdidos' })).toHaveAttribute('aria-selected', 'true')
  })

  test('no celular o menu fica em uma linha só @celular', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'regra de layout do celular')
    await page.goto('/')
    const menu = page.getByRole('navigation', { name: 'Principal' })
    const caixa = await menu.boundingBox()
    expect(caixa.height).toBeLessThan(60)
  })

  test('endereço inexistente mostra página não encontrada', async ({ page }) => {
    await page.goto('/isto-nao-existe')
    await expect(page.getByText('Página não encontrada.')).toBeVisible()
  })

  test('página protegida pede login e depois volta para ela', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await page.goto('/meus-registros')
    await expect(page).toHaveURL(/\/login\?voltar=%2Fmeus-registros/)
    await page.getByLabel('E-mail').fill(tutor.email)
    await page.getByLabel('Senha').fill(SENHA)
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page).toHaveURL(/\/meus-registros$/)
    await expect(page.getByRole('heading', { name: 'Meus registros' })).toBeVisible()
  })

  test('o retorno do login não leva para fora do site', async ({ page, request, baseURL }) => {
    const tutor = await criarConta(request, 'tutor')
    await page.goto('/login?voltar=//exemplo-malicioso.com')
    await page.getByLabel('E-mail').fill(tutor.email)
    await page.getByLabel('Senha').fill(SENHA)
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page).toHaveURL(`${baseURL}/`) // ficou no próprio site, na página inicial
  })
})
