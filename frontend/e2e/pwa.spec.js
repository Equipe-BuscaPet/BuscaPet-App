import { expect, test } from '@playwright/test'

// PWA: instalar o BuscaPet na tela inicial do celular ou do computador.

test('o manifesto do app é válido e os ícones existem', async ({ page, request }) => {
  await page.goto('/')
  const href = await page.locator('link[rel="manifest"]').getAttribute('href')
  const manifesto = await (await request.get(new URL(href, page.url()).toString())).json()
  expect(manifesto.short_name).toBe('BuscaPet')
  expect(manifesto.display).toBe('standalone')
  expect(manifesto.start_url).toBe('/mapa')
  expect(manifesto.icons.map((i) => i.sizes)).toEqual(expect.arrayContaining(['192x192', '512x512']))
  expect(manifesto.icons.some((i) => i.purpose === 'maskable')).toBe(true)
  for (const icone of manifesto.icons) {
    const resposta = await request.get(new URL(icone.src, page.url()).toString())
    expect(resposta.ok(), icone.src).toBe(true)
    expect(resposta.headers()['content-type']).toContain('image/png')
  }
  await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveCount(1)
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content', '#c4541a')
})

test.describe('No iPhone', () => {
  test.use({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1' })

  test('o botão Instalar app explica o passo a passo do Safari', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Instalar app' }).click()
    const dica = page.getByRole('dialog', { name: 'Como instalar no iPhone' })
    await expect(dica).toContainText('Adicionar à Tela de Início')
    await dica.getByRole('button', { name: 'Entendi' }).click()
    await expect(dica).toHaveCount(0)
  })
})

test('sem o aviso do navegador (desktop comum), o botão não aparece', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Instalar app' })).toHaveCount(0)
})
