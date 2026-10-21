import { expect, test } from '@playwright/test'
import { API, criarAnimal, criarConta, entrarComo, publicarNecessidade, verificarAbrigo } from './apoio'

// Terceiro módulo (RF-30 a RF-35): mural, doação, confirmação do abrigo, ranking e perfis públicos.

test.describe('Doações', () => {
  test('apoiador doa pelo mural, o abrigo confirma e a doação pontua @celular', async ({ page, request, browser }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await verificarAbrigo(request, abrigo)
    const necessidade = await publicarNecessidade(request, abrigo, { quantidade: 3 })
    const apoiador = await criarConta(request, 'apoiador')

    // Apoiador: encontra a necessidade no mural do Quem apoia e doa tudo o que falta.
    await entrarComo(page, apoiador)
    await page.goto('/quem-apoia')
    const cartao = page.getByRole('article', { name: necessidade.item })
    await expect(cartao.getByText('0 de 3 recebidos · faltam 3')).toBeVisible()
    await cartao.getByLabel('Quantidade').fill('3')
    await cartao.getByRole('button', { name: 'Quero doar' }).click()
    await expect(cartao.getByRole('status')).toContainText('Doação registrada!')

    // Abrigo: o painel avisa, e a confirmação acontece em Necessidades e doações.
    const paginaAbrigo = await (await browser.newContext()).newPage()
    await entrarComo(paginaAbrigo, abrigo)
    await paginaAbrigo.goto('/painel')
    await paginaAbrigo.getByRole('link', { name: /1 doação para confirmar/ }).click()
    await expect(paginaAbrigo).toHaveURL(/\/doacoes$/)
    const doacao = paginaAbrigo.getByRole('article', { name: `Doação de ${apoiador.nome}` })
    await expect(doacao).toContainText(`3 × ${necessidade.item}`)
    await doacao.getByRole('button', { name: 'Confirmar recebimento' }).click()
    await expect(paginaAbrigo.getByRole('status')).toContainText('passou a contar no ranking')
    await expect(doacao.getByText('Recebida pelo abrigo')).toBeVisible()

    // Apoiador: vê a confirmação, a pontuação no perfil público, e a necessidade (3 de 3) saiu do mural.
    await page.goto('/minhas-doacoes')
    await expect(page.getByRole('article', { name: `Doação para ${abrigo.nome_abrigo}` }).getByText('Recebida pelo abrigo')).toBeVisible()
    await page.getByRole('link', { name: 'Meu perfil público' }).click()
    await expect(page.getByText('20', { exact: true }).first()).toBeVisible() // 10 da doação + 10 do 1º mês
    await expect(page.getByText('Apoiador ativo')).toBeVisible()
    await page.goto('/quem-apoia')
    await expect(page.getByRole('article', { name: necessidade.item })).toHaveCount(0)
  })

  test('visitante é convidado a apoiar e chega ao cadastro já como apoiador', async ({ page }) => {
    await page.goto('/quem-apoia')
    await expect(page.getByRole('heading', { name: 'Ranking por categoria' })).toBeVisible()
    await page.getByRole('link', { name: 'Quero apoiar' }).click()
    await expect(page).toHaveURL(/\/cadastro\?tipo=apoiador$/)
    await expect(page.getByRole('radio', { name: /Apoiador/ })).toBeChecked()
  })

  test('abrigo sem selo não publica no mural e vê o motivo', async ({ page, request }) => {
    await entrarComo(page, await criarConta(request, 'abrigo'))
    await page.goto('/doacoes')
    await expect(page.getByText('Só abrigos com o selo Verificado publicam no mural.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Publicar no mural' })).toHaveCount(0)
  })

  test('abrigo verificado publica, marca como atendida e reabre', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await verificarAbrigo(request, abrigo)
    await entrarComo(page, abrigo)
    await page.goto('/doacoes')
    await page.getByLabel('O que o abrigo precisa').fill('Areia sanitária (pacote de 4 kg)')
    await page.getByLabel('Quantidade').fill('6')
    await page.getByLabel('Urgência').selectOption('baixa')
    await page.getByRole('button', { name: 'Publicar no mural' }).click()
    await expect(page.getByRole('status')).toHaveText('Necessidade publicada no mural do Quem apoia.')
    const cartao = page.getByRole('article', { name: 'Areia sanitária (pacote de 4 kg)' })
    await cartao.getByRole('button', { name: 'Marcar como atendida' }).click()
    await expect(cartao.getByText('Atendida')).toBeVisible()
    await cartao.getByRole('button', { name: 'Reabrir' }).click()
    await expect(cartao.getByText('Pode esperar')).toBeVisible()
  })
})

test.describe('Perfis públicos e navegação entre os módulos', () => {
  test('o perfil do abrigo junta animais, necessidades e a chave PIX', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await verificarAbrigo(request, abrigo)
    const r = await request.patch(`${API}/usuarios/eu`, {
      headers: { Authorization: `Bearer ${abrigo.token}` }, data: { chave_doacao_financeira: 'pix@abrigo-e2e.org' },
    })
    expect(r.ok(), await r.text()).toBeTruthy()
    const animal = await criarAnimal(request, abrigo)
    const necessidade = await publicarNecessidade(request, abrigo)

    // Da ficha do animal (adoção) para o perfil do abrigo, que mostra o mural (doações).
    await page.goto(`/animais/${animal.id}`)
    await page.getByRole('link', { name: abrigo.nome_abrigo }).click()
    await expect(page).toHaveURL(new RegExp(`/abrigos/${abrigo.usuario.id}$`))
    await expect(page.getByRole('heading', { name: abrigo.nome_abrigo })).toBeVisible()
    await expect(page.getByText('pix@abrigo-e2e.org')).toBeVisible()
    await expect(page.getByRole('article', { name: necessidade.item })).toBeVisible()
    await expect(page.getByRole('link', { name: new RegExp(animal.nome) })).toBeVisible()
    await expect(page.getByRole('link', { name: 'cadastre-se como apoiador' })).toBeVisible() // visitante é convidado
  })

  test('abrigo não verificado: sem chave PIX e com o aviso do selo', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await page.goto(`/abrigos/${abrigo.usuario.id}`)
    await expect(page.getByText(/ainda não foi verificado pela administração/)).toBeVisible()
    await expect(page.getByRole('heading', { name: 'O que o abrigo precisa agora' })).toHaveCount(0)
  })
})
