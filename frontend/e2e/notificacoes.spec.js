import { expect, test } from '@playwright/test'
import { API, criarAnimal, criarConta, entrarComo } from './apoio'

// RF-36: sino de notificações no cabeçalho e página de notificações.

async function registrarInteresse(request, tutor, animal) {
  const r = await request.post(`${API}/animais/${animal.id}/interesses`, {
    headers: { Authorization: `Bearer ${tutor.token}` }, data: { mensagem: 'Tenho quintal.' },
  })
  expect(r.status(), await r.text()).toBe(201)
}

const sino = (page) => page.getByRole('button', { name: /^Notificações/ })

test.describe('Notificações', () => {
  test('o abrigo vê o sino acender, abre e vai para os interessados @celular', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    const tutor = await criarConta(request, 'tutor')
    const animal = await criarAnimal(request, abrigo)
    await registrarInteresse(request, tutor, animal)

    await entrarComo(page, abrigo)
    await page.goto('/mapa')
    await expect(sino(page)).toHaveAccessibleName('Notificações: 1 não lida')
    await sino(page).click()
    const painel = page.getByRole('dialog', { name: 'Notificações recentes' })
    const aviso = painel.getByRole('button', { name: new RegExp(`tem interesse em adotar ${animal.nome}`) })
    await expect(aviso).toBeVisible()
    await aviso.click()
    await expect(page).toHaveURL(/\/interessados$/)
    await expect(sino(page)).toHaveAccessibleName('Notificações') // lida: o contador some
  })

  test('na página, filtra as não lidas e marca todas como lidas', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    const animal = await criarAnimal(request, abrigo)
    for (let i = 0; i < 2; i++) await registrarInteresse(request, await criarConta(request, 'tutor'), animal)

    await entrarComo(page, abrigo)
    await page.goto('/notificacoes')
    const lista = page.getByRole('list', { name: 'Notificações' })
    await expect(lista.getByRole('listitem')).toHaveCount(2)
    await expect(sino(page)).toHaveAccessibleName('Notificações: 2 não lidas')

    await lista.getByRole('button', { name: 'Marcar como lida' }).first().click()
    await expect(sino(page)).toHaveAccessibleName('Notificações: 1 não lida') // o sino acompanha a página
    await page.getByRole('tab', { name: 'Não lidas' }).click()
    await expect(lista.getByRole('listitem')).toHaveCount(1)

    await page.getByRole('button', { name: 'Marcar todas como lidas' }).click()
    await expect(sino(page)).toHaveAccessibleName('Notificações')
    await expect(page.getByText('Nenhuma notificação não lida. Tudo em dia!')).toBeVisible() // a aba "Não lidas" esvazia
    await page.getByRole('tab', { name: 'Todas' }).click()
    await expect(lista.getByRole('listitem')).toHaveCount(2) // continuam no histórico, já lidas
    await expect(lista.getByRole('button', { name: 'Marcar como lida' })).toHaveCount(0)
  })

  test('conta nova vê o aviso de que ainda não há notificações; visitante não vê o sino', async ({ page, request }) => {
    await page.goto('/')
    await expect(sino(page)).toHaveCount(0)
    const tutor = await criarConta(request, 'tutor')
    await entrarComo(page, tutor)
    await page.goto('/')
    await sino(page).click()
    await expect(page.getByText('Nenhuma notificação por enquanto.')).toBeVisible()
  })
})
