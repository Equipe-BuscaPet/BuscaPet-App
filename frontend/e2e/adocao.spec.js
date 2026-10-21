import { expect, test } from '@playwright/test'
import { criarAnimal, criarConta, entrarComo } from './apoio'

test.describe('Interesse de adoção', () => {
  test('tutor demonstra interesse e o abrigo vê o interessado', async ({ page, request, browser }) => {
    const abrigo = await criarConta(request, 'abrigo')
    const tutor = await criarConta(request, 'tutor')
    const animal = await criarAnimal(request, abrigo)

    await entrarComo(page, tutor)
    await page.goto(`/animais/${animal.id}`)
    await expect(page.getByRole('heading', { name: animal.nome, exact: true })).toBeVisible()
    await page.getByLabel('Mensagem para o abrigo (opcional)').fill('Tenho quintal e muito carinho.')
    await page.getByRole('button', { name: 'Tenho interesse' }).click()
    await expect(page.getByRole('status')).toContainText('Interesse registrado')

    // O abrigo, em outra sessão de navegador, recebe o interessado.
    const contexto = await browser.newContext()
    const paginaAbrigo = await contexto.newPage()
    await entrarComo(paginaAbrigo, abrigo)
    await paginaAbrigo.goto('/interessados')
    await expect(paginaAbrigo.getByRole('heading', { name: tutor.nome })).toBeVisible()
    await contexto.close()
  })

  test('visitante é convidado a entrar para adotar', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    const animal = await criarAnimal(request, abrigo)
    await page.goto(`/animais/${animal.id}`)
    await expect(page.getByRole('heading', { name: `Quer adotar ${animal.nome}?` })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Tenho interesse' })).toHaveCount(0)
  })
})
