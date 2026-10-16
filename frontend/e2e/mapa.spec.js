import { expect, test } from '@playwright/test'
import { criarAvistamento, criarConta, criarPerdido } from './apoio'

// Mapa com abas (RF-07 a RF-09): "Abrigos" e "Perdidos e avistados"; cada aba muda o mapa e a lista lateral.

const aba = (page, nome) => page.getByRole('tablist', { name: 'O que ver no mapa' }).getByRole('tab', { name: new RegExp(nome) })
const filtro = (page, nome) => page.getByRole('group', { name: 'Mostrar no mapa' }).getByRole('button', { name: new RegExp(nome) })

test.describe('Mapa com abas', () => {
  test('Mapa é o primeiro item do menu @celular', async ({ page }) => {
    await page.goto('/')
    const primeiro = page.getByRole('navigation', { name: 'Principal' }).getByRole('link').first()
    await expect(primeiro).toHaveText('Mapa')
  })

  test('a aba Abrigos mostra só abrigos; a de animais troca o mapa e a lista @celular', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, tutor)
    const avistamento = await criarAvistamento(request, tutor)
    const linkPerdido = page.locator(`a[href="/reencontro/perdidos/${perdido.id}"]`)
    const linkAvistamento = page.locator(`a[href="/reencontro/avistamentos/${avistamento.id}"]`)

    await page.goto('/mapa')
    await expect(aba(page, 'Abrigos')).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('list', { name: 'Abrigos' })).toBeVisible()
    await expect(linkPerdido).toHaveCount(0)
    await expect(page.locator('.pino')).toHaveCount(0)

    await aba(page, 'Perdidos e avistados').click()
    await expect(page).toHaveURL(/ver=animais/)
    await expect(page.getByRole('list', { name: 'Abrigos' })).toHaveCount(0)
    await expect(linkPerdido).toBeVisible()
    await expect(linkAvistamento).toBeVisible()
    await expect(page.locator('.pino--perdido').first()).toBeVisible()

    // O filtro desliga os avistados: somem da lista e do mapa, e a escolha vai para a URL.
    await filtro(page, 'Avistados').click()
    await expect(filtro(page, 'Avistados')).toHaveAttribute('aria-pressed', 'false')
    await expect(page).toHaveURL(/mostrar=perdidos/)
    await expect(linkAvistamento).toHaveCount(0)
    await expect(page.locator('.pino--avistamento')).toHaveCount(0)
    await expect(linkPerdido).toBeVisible()
  })

  test('a lista de animais é mista e os filtros combinam', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const gato = await criarPerdido(request, tutor) // gato perdido
    const cao = await criarAvistamento(request, tutor) // cachorro avistado
    await page.goto('/mapa?ver=animais')
    const lista = page.getByRole('list', { name: 'Animais perdidos e avistados' })
    await expect(lista.locator(`a[href="/reencontro/perdidos/${gato.id}"]`)).toBeVisible()
    await expect(lista.locator(`a[href="/reencontro/avistamentos/${cao.id}"]`)).toBeVisible() // os dois na mesma lista

    await page.getByLabel('Espécie').selectOption('gato')
    await expect(lista.locator(`a[href="/reencontro/avistamentos/${cao.id}"]`)).toHaveCount(0)
    await expect(lista.locator(`a[href="/reencontro/perdidos/${gato.id}"]`)).toBeVisible()

    await page.getByRole('button', { name: 'Limpar filtros' }).click()
    await expect(lista.locator(`a[href="/reencontro/avistamentos/${cao.id}"]`)).toBeVisible()
  })

  test('"Perto de mim" vem antes dos filtros', async ({ page }) => {
    await page.goto('/mapa?ver=animais')
    const ferramentas = page.locator('.mapa-ferramentas')
    const primeiro = ferramentas.locator('button').first()
    await expect(primeiro).toHaveText('📍 Perto de mim')
  })

  test('o balão do perdido leva ao registro', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, tutor, { latitude: -8.3, longitude: -35.2 }) // longe dos outros
    await page.goto('/mapa?ver=animais&mostrar=perdidos')
    const cartao = page.locator('li', { has: page.locator(`a[href="/reencontro/perdidos/${perdido.id}"]`) })
    await cartao.getByRole('button', { name: 'Ver no mapa' }).click()
    const balao = page.locator('.leaflet-popup-content')
    await expect(balao).toContainText('Local aproximado')
    await balao.getByRole('button', { name: 'Ver registro' }).click()
    await expect(page).toHaveURL(new RegExp(`/reencontro/perdidos/${perdido.id}$`))
  })
})

test('a página inicial convida para perdidos e achados @celular', async ({ page }) => {
  await page.goto('/')
  const chamada = page.getByRole('region', { name: /Perdeu ou encontrou um animal/ })
  await expect(chamada).toBeVisible()
  await chamada.getByRole('link', { name: 'Ver no mapa' }).click()
  await expect(aba(page, 'Perdidos e avistados')).toHaveAttribute('aria-selected', 'true')
})

test.describe('Perto de mim', () => {
  test.use({ geolocation: { latitude: -8.0476, longitude: -34.877 }, permissions: ['geolocation'] })

  test('ordena os animais pela distância e permite limitar o raio', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await criarPerdido(request, tutor)
    await page.goto('/mapa?ver=animais')
    await page.getByRole('button', { name: '📍 Perto de mim' }).click()
    await expect(page.getByText('do mais perto ao mais longe')).toBeVisible()
    await expect(page.getByLabel('Distância máxima')).toBeVisible()
    await page.getByLabel('Distância máxima').selectOption('5')
    await expect(page.getByRole('list', { name: 'Animais perdidos e avistados' }).getByText(/ km$/).first()).toBeVisible()
  })
})
