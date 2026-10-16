import { expect, test } from '@playwright/test'
import { criarAvistamento, criarConta, criarPerdido } from './apoio'

// Mapa com camadas alternáveis (RF-07/08) e o destaque do reencontro na página inicial.

const camada = (page, nome) => page.getByRole('group', { name: 'Camadas do mapa' }).getByRole('button', { name: new RegExp(nome) })

test.describe('Mapa com camadas', () => {
  test('mostra abrigos, perdidos e avistados, e cada camada liga e desliga @celular', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, tutor)
    const avistamento = await criarAvistamento(request, tutor)

    await page.goto('/mapa')
    for (const nome of ['Abrigos', 'Perdidos', 'Avistados']) await expect(camada(page, nome)).toHaveAttribute('aria-pressed', 'true')
    const linkPerdido = page.locator(`a[href="/reencontro/perdidos/${perdido.id}"]`)
    const linkAvistamento = page.locator(`a[href="/reencontro/avistamentos/${avistamento.id}"]`)
    await expect(linkPerdido).toBeVisible()
    await expect(linkAvistamento).toBeVisible()
    await expect(page.locator('.pino--perdido').first()).toBeVisible()

    // Desliga "Avistados": some da lista e do mapa, e a escolha vai para a URL (link compartilhável).
    await camada(page, 'Avistados').click()
    await expect(camada(page, 'Avistados')).toHaveAttribute('aria-pressed', 'false')
    await expect(page).toHaveURL(/camadas=abrigos%2Cperdidos|camadas=abrigos,perdidos/)
    await expect(linkAvistamento).toHaveCount(0)
    await expect(page.locator('.pino--avistamento')).toHaveCount(0)
    await expect(linkPerdido).toBeVisible()
  })

  test('o link com camadas abre o mapa só com elas', async ({ page }) => {
    await page.goto('/mapa?camadas=perdidos')
    await expect(camada(page, 'Perdidos')).toHaveAttribute('aria-pressed', 'true')
    await expect(camada(page, 'Abrigos')).toHaveAttribute('aria-pressed', 'false')
    await expect(page.getByRole('heading', { name: 'Abrigos', exact: true })).toHaveCount(0)
  })

  test('o balão do perdido leva ao registro', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, tutor, { latitude: -8.3, longitude: -35.2 }) // longe dos outros
    await page.goto('/mapa?camadas=perdidos')
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
  await chamada.getByRole('link', { name: 'Ver perdidos e achados' }).click()
  await expect(page.getByRole('heading', { name: 'Perdidos e achados' })).toBeVisible()
})
