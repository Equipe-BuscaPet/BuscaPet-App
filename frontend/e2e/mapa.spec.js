import { expect, test } from '@playwright/test'
import { criarAvistamento, criarConta, criarPerdido } from './apoio'

// Mapa (RF-07 a RF-09): só as abas acima do mapa; "Perto de mim" e "Filtros" ficam sobre a lista.

const aba = (page, nome) => page.getByRole('tablist', { name: 'O que ver no mapa' }).getByRole('tab', { name: new RegExp(nome) })
const abrirFiltros = (page) => page.getByRole('button', { name: /Filtros/ }).click()
const painel = (page) => page.getByRole('dialog', { name: 'Filtros' })

test.describe('Mapa', () => {
  test('Mapa é o primeiro item do menu @celular', async ({ page }) => {
    await page.goto('/')
    const primeiro = page.getByRole('navigation', { name: 'Principal' }).getByRole('link').first()
    await expect(primeiro).toHaveText('Mapa')
  })

  test('acima do mapa ficam só as abas; Perto de mim e Filtros ficam sobre a lista @celular', async ({ page }) => {
    await page.goto('/mapa?ver=animais')
    const abas = await page.getByRole('tablist', { name: 'O que ver no mapa' }).boundingBox()
    const mapa = await page.getByRole('region', { name: /Mapa dos animais/ }).boundingBox()
    // Entre as abas e o mapa não sobra faixa de botões.
    expect(mapa.y - (abas.y + abas.height)).toBeLessThan(40)
    const barra = page.locator('.mapa-barra')
    await expect(barra.getByRole('button', { name: '📍 Perto de mim' })).toBeVisible()
    await expect(barra.getByRole('button', { name: /Filtros/ })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Perdi meu animal' })).toHaveCount(0)
    // Botões na mesma linha da contagem, encostados à direita da coluna.
    const resumo = await page.locator('.mapa-barra__resumo').boundingBox()
    const filtros = await barra.getByRole('button', { name: /Filtros/ }).boundingBox()
    const coluna = await barra.boundingBox()
    expect(Math.abs((filtros.y + filtros.height / 2) - (resumo.y + resumo.height / 2))).toBeLessThan(16)
    expect(coluna.x + coluna.width - (filtros.x + filtros.width)).toBeLessThan(4)
  })

  test('a aba Abrigos mostra só abrigos; a de animais troca o mapa e a lista @celular', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, tutor)
    const linkPerdido = page.locator(`a[href="/reencontro/perdidos/${perdido.id}"]`)

    await page.goto('/mapa')
    await expect(aba(page, 'Abrigos')).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('list', { name: 'Abrigos' })).toBeVisible()
    await expect(linkPerdido).toHaveCount(0)
    await expect(page.locator('.pino')).toHaveCount(0)

    await aba(page, 'Perdidos e avistados').click()
    await expect(page).toHaveURL(/ver=animais/)
    await expect(page.getByRole('list', { name: 'Abrigos' })).toHaveCount(0)
    await expect(linkPerdido).toBeVisible()
    await expect(page.locator('.pino--perdido').first()).toBeVisible()
  })

  test('lista mista e filtros no painel (tipo, espécie) com contagem no botão', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const gato = await criarPerdido(request, tutor) // gato perdido
    const cao = await criarAvistamento(request, tutor) // cachorro avistado
    await page.goto('/mapa?ver=animais')
    const lista = page.getByRole('list', { name: 'Animais perdidos e avistados' })
    const linkGato = lista.locator(`a[href="/reencontro/perdidos/${gato.id}"]`)
    const linkCao = lista.locator(`a[href="/reencontro/avistamentos/${cao.id}"]`)
    await expect(linkGato).toBeVisible()
    await expect(linkCao).toBeVisible() // os dois na mesma lista

    await abrirFiltros(page)
    // O filtro mora na URL, e o React Router 7 atualiza a URL em transição: a caixa muda logo depois do clique,
    // não no mesmo instante. Por isso clicar e esperar o estado, em vez de uncheck()/check() (que conferem na hora).
    const avistados = painel(page).getByRole('checkbox', { name: /Avistados/ })
    await avistados.click()
    await expect(avistados).not.toBeChecked()
    await expect(page).toHaveURL(/mostrar=perdidos/)
    await expect(linkCao).toHaveCount(0)
    await expect(page.locator('.pino--avistamento')).toHaveCount(0)

    await avistados.click()
    await expect(avistados).toBeChecked()
    await painel(page).getByLabel('Espécie').selectOption('gato')
    await expect(linkCao).toHaveCount(0)
    await expect(linkGato).toBeVisible()
    await painel(page).getByRole('button', { name: 'Pronto' }).click()
    await expect(painel(page)).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Filtros/ })).toContainText('1') // um filtro ligado

    await abrirFiltros(page)
    await painel(page).getByRole('button', { name: 'Limpar filtros' }).click()
    await expect(linkCao).toBeVisible()
  })

  test('o painel de filtros fecha com Esc', async ({ page }) => {
    await page.goto('/mapa')
    await abrirFiltros(page)
    await expect(painel(page).getByRole('checkbox', { name: 'Só abrigos verificados' })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(painel(page)).toHaveCount(0)
  })

  test('filtro de abrigos: só verificados', async ({ page, request }) => {
    await criarConta(request, 'abrigo') // nasce não verificado
    await page.goto('/mapa')
    const lista = page.getByRole('list', { name: 'Abrigos' })
    await expect(lista.getByText('Não verificado').first()).toBeVisible()
    await abrirFiltros(page)
    await painel(page).getByRole('checkbox', { name: 'Só abrigos verificados' }).check()
    await expect(lista.getByText('Não verificado')).toHaveCount(0)
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

  test('ordena pela distância, oferece o raio no filtro e desliga no segundo clique', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await criarPerdido(request, tutor)
    await page.goto('/mapa?ver=animais')
    const perto = page.getByRole('button', { name: '📍 Perto de mim' })
    await perto.click()
    await expect(perto).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByText(/mais perto primeiro/i)).toBeVisible()
    await abrirFiltros(page)
    await painel(page).getByLabel('Distância máxima').selectOption('5')
    await painel(page).getByRole('button', { name: 'Pronto' }).click()
    await expect(page.getByRole('list', { name: 'Animais perdidos e avistados' }).getByText(/ km$/).first()).toBeVisible()
    await perto.click()
    await expect(perto).toHaveAttribute('aria-pressed', 'false')
    await expect(page.getByText(/mais recentes primeiro/i)).toBeVisible()
  })
})

test('o Instalar app fica no rodapé, centralizado', async ({ page }) => {
  await page.goto('/')
  const rodape = page.locator('footer.rodape')
  await expect(rodape).toBeVisible()
  await expect(page.locator('header').getByRole('button', { name: 'Instalar app' })).toHaveCount(0)
})
