import { expect, test } from '@playwright/test'
import { SENHA, criarConta, entrarComo } from './apoio'

// Menu da conta (☰) e a página Minha conta (RF-37).

const abrirMenu = (page) => page.getByRole('button', { name: 'Menu da conta' }).click()
const menu = (page) => page.getByRole('navigation', { name: 'Menu da conta' })

test.describe('Menu da conta', () => {
  test('o menu principal fica só com o que é de todos @celular', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await entrarComo(page, abrigo)
    await page.goto('/')
    const principal = page.getByRole('navigation', { name: 'Principal' })
    await expect(principal.getByRole('link')).toHaveText(['Mapa', 'Animais', 'Perdidos e achados', 'Quem apoia'])
    await expect(page.getByRole('button', { name: 'Sair' })).toHaveCount(0) // Sair foi para dentro do ☰
  })

  test('cada perfil vê os seus itens e o Sair no fim @celular', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await entrarComo(page, tutor)
    await page.goto('/')
    await abrirMenu(page)
    await expect(menu(page)).toContainText(tutor.nome)
    for (const item of ['Minha conta', 'Meus interesses de adoção', 'Minhas doações', 'Meus registros', 'Notificações']) {
      await expect(menu(page).getByRole('link', { name: new RegExp(item) })).toBeVisible()
    }
    await expect(menu(page).getByRole('link', { name: /Meus animais/ })).toHaveCount(0)
    await expect(menu(page).getByText('Em breve')).toHaveCount(0) // ranking e doações já existem de verdade
    await expect(menu(page).getByRole('button', { name: /Sair/ })).toBeVisible()
  })

  test('abrigo e apoiador veem os itens de doação no menu', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await entrarComo(page, abrigo)
    await page.goto('/')
    await abrirMenu(page)
    await expect(menu(page).getByRole('link', { name: /Necessidades e doações/ })).toBeVisible()
    await expect(menu(page).getByRole('link', { name: /Perfil público do abrigo/ })).toHaveAttribute('href', `/abrigos/${abrigo.usuario.id}`)

    const apoiador = await criarConta(request, 'apoiador')
    await page.context().clearCookies()
    await entrarComo(page, apoiador)
    await page.goto('/')
    await abrirMenu(page)
    await expect(menu(page).getByRole('link', { name: /Minhas doações/ })).toBeVisible()
    await expect(menu(page).getByRole('link', { name: /Meu perfil público/ })).toBeVisible()
  })

  test('fecha com Esc e ao navegar', async ({ page, request }) => {
    await entrarComo(page, await criarConta(request, 'tutor'))
    await page.goto('/')
    await abrirMenu(page)
    await page.keyboard.press('Escape')
    await expect(menu(page)).toHaveCount(0)
    await abrirMenu(page)
    await menu(page).getByRole('link', { name: /Notificações/ }).click()
    await expect(page).toHaveURL(/\/notificacoes$/)
    await expect(menu(page)).toHaveCount(0)
  })
})

test.describe('Minha conta', () => {
  test('tutor atualiza os dados e a mudança persiste', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await entrarComo(page, tutor)
    await page.goto('/')
    await abrirMenu(page)
    await menu(page).getByRole('link', { name: /Minha conta/ }).click()
    await expect(page.getByRole('heading', { name: 'Minha conta' })).toBeVisible()
    await page.getByLabel('Telefone').fill('81 99999-0000')
    await page.getByLabel('Cidade').fill('Olinda')
    await page.getByRole('button', { name: 'Salvar dados' }).click()
    await expect(page.getByRole('status')).toHaveText('Dados salvos.')
    await page.reload()
    await expect(page.getByLabel('Cidade')).toHaveValue('Olinda')
  })

  test('abrigo edita o perfil público e não pode apagar o nome do abrigo', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await entrarComo(page, abrigo)
    await page.goto('/conta')
    await page.getByLabel('Horário de funcionamento').fill('Seg a sáb, 9h às 17h')
    await page.getByRole('button', { name: 'Salvar dados' }).click()
    await expect(page.getByRole('status')).toHaveText('Dados salvos.')
    await expect(page.getByLabel('Nome do abrigo')).toHaveAttribute('required', '')
  })

  test('troca de senha: confirmação errada, senha atual errada e sucesso', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await entrarComo(page, tutor)
    await page.goto('/conta')
    const secao = page.getByRole('region', { name: 'Trocar senha' })
    await secao.getByLabel('Senha atual').fill(SENHA)
    await secao.getByLabel('Nova senha', { exact: true }).fill('NovaSenha123!')
    await secao.getByLabel('Confirmar nova senha').fill('outra-coisa')
    await secao.getByRole('button', { name: 'Trocar senha' }).click()
    await expect(secao.getByRole('alert')).toHaveText('A confirmação não é igual à nova senha.')

    await secao.getByLabel('Senha atual').fill('senha-errada')
    await secao.getByLabel('Confirmar nova senha').fill('NovaSenha123!')
    await secao.getByRole('button', { name: 'Trocar senha' }).click()
    await expect(secao.getByRole('alert')).toBeVisible()

    await secao.getByLabel('Senha atual').fill(SENHA)
    await secao.getByLabel('Nova senha', { exact: true }).fill('NovaSenha123!')
    await secao.getByLabel('Confirmar nova senha').fill('NovaSenha123!')
    await secao.getByRole('button', { name: 'Trocar senha' }).click()
    await expect(secao.getByRole('status')).toHaveText('Senha alterada.')
    const login = await request.post(`${process.env.API_URL}/auth/login`, { form: { username: tutor.email, password: 'NovaSenha123!' } })
    expect(login.ok()).toBe(true)
  })
})
