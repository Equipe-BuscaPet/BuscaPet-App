import { expect, test } from '@playwright/test'
import { SENHA, caminhoFoto, criarAvistamento, criarConta, criarPerdido, entrarComo } from './apoio'

// RF-19 (animal perdido) e RF-20 (avistamento): assistente, lista, detalhe e "Meus registros".

const continuar = (page) => page.getByRole('button', { name: 'Continuar' }).click()
const etapa = (page, n, nome) => expect(page.getByRole('heading', { name: `Etapa ${n} de 5: ${nome}` })).toBeVisible()

test.describe('Perdi meu animal', () => {
  test('visitante preenche tudo, entra na revisão sem perder as fotos e publica', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    await page.goto('/perdi')
    await expect(page.getByText('Você pode preencher tudo sem conta')).toBeVisible()

    // Etapa 1: sem foto não avança
    await continuar(page)
    await expect(page.getByText('Escolha pelo menos uma foto do animal.')).toBeVisible()
    await page.locator('input[type=file]').setInputFiles([caminhoFoto('cachorro-caramelo.jpg'), caminhoFoto('gato-cinza.jpg')])
    await expect(page.getByText('Escolha pelo menos uma foto do animal.')).toHaveCount(0) // o erro some ao corrigir
    await expect(page.getByRole('list', { name: 'Fotos escolhidas' }).locator('img')).toHaveCount(2)
    await continuar(page)

    // Etapa 2: obrigatórios
    await etapa(page, 2, 'Características')
    await continuar(page)
    await expect(page.getByText('Escolha a espécie.')).toBeVisible()
    await page.getByRole('radio', { name: /Cachorro/ }).check()
    await page.getByRole('radio', { name: /Grande/ }).check()
    await page.getByLabel('Cor predominante').fill('Preto')
    await page.getByLabel(/Sinais particulares/).fill('Coleira azul')
    await continuar(page)

    // Etapa 3: local no mapa e data
    await etapa(page, 3, 'Local e data')
    await continuar(page)
    await expect(page.getByText('Marque o local no mapa.')).toBeVisible()
    await page.locator('.mapa--seletor').click()
    await expect(page.getByText('Ponto marcado.')).toBeVisible()
    await page.getByLabel('Quando ele sumiu?').fill('2026-10-15')
    await continuar(page)

    // Etapa 4: revisão. Sem conta, publicar fica bloqueado; o login acontece aqui mesmo.
    await etapa(page, 4, 'Revisar')
    const publicar = page.getByRole('button', { name: 'Publicar animal perdido' })
    await expect(publicar).toBeDisabled()
    await page.locator('#lr-email').fill(tutor.email)
    await page.locator('#lr-senha').fill(SENHA)
    await page.getByRole('form', { name: 'Entre para publicar' }).getByRole('button', { name: 'Entrar' }).click()
    await expect(publicar).toBeEnabled()
    const miniaturas = page.locator('.revisao img')
    await expect(miniaturas).toHaveCount(2)
    // As miniaturas precisam carregar de verdade (o defeito antigo deixava a imagem quebrada).
    expect(await miniaturas.first().evaluate((img) => img.complete && img.naturalWidth > 0)).toBe(true)
    await publicar.click()

    // Etapa 5: resultados
    await etapa(page, 5, 'Resultados')
    await expect(page.getByText('Pronto! O seu animal está registrado como perdido.')).toBeVisible()
    await expect(page.getByText('A comparação por foto está em construção.')).toBeVisible()

    // O detalhe mostra a data exatamente como foi digitada (regressão do defeito do fuso horário).
    await page.getByRole('link', { name: 'Ver o registro' }).click()
    await expect(page.getByRole('heading', { name: 'Cachorro perdido' })).toBeVisible()
    await expect(page.locator('dd', { hasText: '15/10/2026' })).toBeVisible()
    await expect(page.getByText('Seu registro')).toBeVisible()
    await expect(page.getByText('Você vê o ponto exato que marcou.')).toBeVisible()
  })

  test('arquivo que não é imagem é recusado já no navegador', async ({ page }) => {
    await page.goto('/perdi')
    await page.locator('input[type=file]').setInputFiles(caminhoFoto('nao-e-foto.txt'))
    await expect(page.getByText(/Não incluídas — nao-e-foto\.txt: use JPEG, PNG ou WebP/)).toBeVisible()
    await expect(page.getByText('0 de 5', { exact: false })).toBeVisible()
  })

  test('conta de abrigo é avisada de que só tutor registra perdido', async ({ page, request }) => {
    const abrigo = await criarConta(request, 'abrigo')
    await entrarComo(page, abrigo)
    await page.goto('/perdi')
    await expect(page.getByText('Só contas de tutor registram animal perdido.')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Encontrei um animal' }).first()).toBeVisible()
  })
})

test.describe('Encontrei um animal', () => {
  test('quem avistou vê os perdidos da mesma espécie por perto', async ({ page, request }) => {
    const dono = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, dono) // gato no centro do mapa
    const quemViu = await criarConta(request, 'tutor')
    await entrarComo(page, quemViu)

    await page.goto('/encontrei')
    await page.locator('input[type=file]').setInputFiles(caminhoFoto('gato-cinza.jpg'))
    await continuar(page)
    await page.getByRole('radio', { name: /Gato/ }).check()
    await page.getByRole('radio', { name: /Pequeno/ }).check()
    await page.getByLabel('Cor predominante').fill('Cinza')
    await continuar(page)
    await page.locator('.mapa--seletor').click()
    await page.getByLabel('Quando você o viu?').fill('2026-10-16')
    await continuar(page)
    await page.getByRole('button', { name: 'Publicar avistamento' }).click()

    await etapa(page, 5, 'Resultados')
    await expect(page.getByRole('heading', { name: 'Animais perdidos perto daqui' })).toBeVisible()
    await expect(page.locator(`a[href="/reencontro/perdidos/${perdido.id}"]`)).toBeVisible()
  })
})

test.describe('Lista, detalhe e privacidade', () => {
  test('a lista pública alterna entre perdidos e avistados', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const avistamento = await criarAvistamento(request, tutor)
    await page.goto('/reencontro')
    await page.getByRole('tab', { name: 'Avistados na rua' }).click()
    await expect(page).toHaveURL(/aba=avistamento/)
    await expect(page.locator(`a[href="/reencontro/avistamentos/${avistamento.id}"]`)).toBeVisible()
  })

  test('outra pessoa vê só a região aproximada e não pode excluir', async ({ page, request }) => {
    const dono = await criarConta(request, 'tutor')
    const perdido = await criarPerdido(request, dono)
    const outra = await criarConta(request, 'tutor')
    await entrarComo(page, outra)
    await page.goto(`/reencontro/perdidos/${perdido.id}`)
    await expect(page.getByText(/Região aproximada \(cerca de 1 km\)/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Excluir registro' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Vi este animal' })).toBeVisible()
  })

  test('o autor exclui o próprio registro em Meus registros', async ({ page, request }) => {
    const tutor = await criarConta(request, 'tutor')
    const avistamento = await criarAvistamento(request, tutor)
    await entrarComo(page, tutor)
    await page.goto('/meus-registros')
    const cartao = page.locator('article', { has: page.locator(`a[href="/reencontro/avistamentos/${avistamento.id}"]`) })
    await expect(cartao).toBeVisible()
    page.once('dialog', (dialogo) => dialogo.accept())
    await cartao.getByRole('button', { name: 'Excluir' }).click()
    await expect(page.getByRole('status')).toHaveText('Registro excluído.')
    await expect(cartao).toHaveCount(0)
  })
})
