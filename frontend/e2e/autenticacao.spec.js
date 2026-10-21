import { expect, test } from '@playwright/test'
import { SENHA, criarConta, entrarComo } from './apoio'

test.describe('Cadastro e login', () => {
  test('tutor se cadastra pela interface e já entra logado', async ({ page }) => {
    const email = `e2e-cadastro-${Date.now()}@teste.buscapet.dev`
    await page.goto('/cadastro')
    await page.getByRole('radio', { name: /Tutor/ }).check()
    await page.getByLabel('Seu nome').fill('Ana Teste')
    await page.getByLabel('E-mail').fill(email)
    await page.getByLabel('Senha').fill(SENHA)
    await page.getByRole('button', { name: 'Criar conta' }).click()
    await page.getByRole('button', { name: 'Menu da conta' }).click()
    await expect(page.getByRole('navigation', { name: 'Menu da conta' })).toContainText('Ana Teste')
    await expect(page.getByRole('button', { name: /Sair/ })).toBeVisible()
  })

  test('senha errada mostra mensagem clara', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await page.goto('/login')
    await page.getByLabel('E-mail').fill(tutor.email)
    await page.getByLabel('Senha').fill('senha-errada-123')
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('cada perfil vê só o menu que lhe cabe', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await entrarComo(page, abrigo)
    await page.goto('/')
    // O menu principal é igual para todos; o que é do perfil fica no menu da conta (☰).
    await page.getByRole('button', { name: 'Menu da conta' }).click()
    const menu = page.getByRole('navigation', { name: 'Menu da conta' })
    await expect(menu.getByRole('link', { name: /Meus animais/ })).toBeVisible()
    await expect(menu.getByRole('link', { name: /Interessados/ })).toBeVisible()
    await expect(menu.getByRole('link', { name: /Meus interesses/ })).toHaveCount(0)
    await page.goto('/admin')
    await expect(page.getByRole('alert')).toContainText('não tem acesso')
  })

  test('sair volta ao estado de visitante', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await entrarComo(page, tutor)
    await page.goto('/')
    await page.getByRole('button', { name: 'Menu da conta' }).click()
    await page.getByRole('button', { name: /Sair/ }).click()
    await expect(page.getByRole('link', { name: 'Entrar' })).toBeVisible()
  })
})
