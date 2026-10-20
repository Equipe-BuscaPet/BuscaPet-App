import { readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { API, contaAdmin, criarAnimal, criarConta, entrarComo } from './apoio'

// Sprint 7: painel da administração (RF-38), histórico de operações (RF-39), relatórios do abrigo (RF-40),
// pesquisa, filtros e exportação CSV.

async function adocaoAprovada(request) {
  const abrigo = await criarConta(request, 'abrigo')
  const tutor = await criarConta(request, 'tutor')
  const animal = await criarAnimal(request, abrigo)
  const i = await request.post(`${API}/animais/${animal.id}/interesses`, { headers: { Authorization: `Bearer ${tutor.token}` }, data: {} })
  expect(i.status(), await i.text()).toBe(201)
  const id = (await i.json()).id
  const a = await request.patch(`${API}/interesses/${id}`, { headers: { Authorization: `Bearer ${abrigo.token}` }, data: { status: 'aprovado' } })
  expect(a.ok(), await a.text()).toBeTruthy()
  return { abrigo, tutor, animal }
}

async function baixar(page, botao) {
  const [download] = await Promise.all([page.waitForEvent('download'), botao.click()])
  return { nome: download.suggestedFilename(), texto: readFileSync(await download.path(), 'utf-8') }
}

test.describe('Administração', () => {
  test('o painel mostra indicadores, gráficos e as últimas ações @celular', async ({ page, request }) => {
    await adocaoAprovada(request)
    await entrarComo(page, await contaAdmin(request))
    await page.goto('/admin')
    await expect(page.getByRole('tab', { name: 'Painel' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByText('adoções aprovadas')).toBeVisible()
    await expect(page.getByRole('img', { name: /^Interesses de adoção\./ })).toBeVisible()
    await page.getByRole('button', { name: 'Ver como tabela' }).click()
    await expect(page.getByRole('table').first()).toContainText('Doações confirmadas')
    // As últimas ações são do sistema todo (outros testes rodam em paralelo): confere só que a lista aparece.
    await expect(page.getByRole('heading', { name: 'Últimas ações' })).toBeVisible()
    await expect(page.locator('table.historico tr').first()).toBeVisible()
  })

  test('o histórico filtra por ação e pesquisa, e exporta o que está filtrado', async ({ page, request }) => {
    const { animal } = await adocaoAprovada(request)
    await entrarComo(page, await contaAdmin(request))
    await page.goto('/admin?aba=historico')
    await page.getByLabel('Ação', { exact: true }).selectOption({ label: 'Adoção aprovada' })
    await page.getByLabel('Pesquisar').fill(animal.nome)
    await page.getByLabel('Pesquisar').press('Enter')
    await expect(page.getByRole('status')).toHaveText('1 operação encontrada')
    await expect(page.getByRole('cell', { name: `Animal: ${animal.nome}` })).toBeVisible()

    const { nome, texto } = await baixar(page, page.getByRole('button', { name: 'Exportar CSV' }))
    expect(nome).toMatch(/^historico-\d{4}-\d{2}-\d{2}-a-\d{4}-\d{2}-\d{2}\.csv$/)
    const linhas = texto.replace('﻿', '').trim().split(/\r?\n/)
    expect(linhas[0]).toBe('Data;Quem;E-mail;Tipo de conta;Ação;Registro;Detalhes')
    expect(linhas).toHaveLength(2)
    expect(linhas[1]).toContain(`Adoção aprovada;interesse #`)
  })

  test('a pesquisa de contas encontra pelo e-mail e filtra por tipo', async ({ page, request }) => {
    const apoiador = await criarConta(request, 'apoiador')
    await entrarComo(page, await contaAdmin(request))
    await page.goto('/admin?aba=contas')
    await page.getByLabel('Pesquisar').fill(apoiador.email)
    await page.getByRole('button', { name: 'Pesquisar' }).click()
    await expect(page.getByRole('status')).toHaveText('1 conta encontrada')
    await expect(page.getByRole('cell', { name: apoiador.email })).toBeVisible()
    await page.getByLabel('Tipo de conta').selectOption('tutor')
    await expect(page.getByRole('status')).toHaveText('0 contas encontradas')
  })
})

test.describe('Relatórios do abrigo', () => {
  test('o abrigo vê o relatório do período e exporta os interesses', async ({ page, request }) => {
    const { abrigo, tutor, animal } = await adocaoAprovada(request)
    await entrarComo(page, abrigo)
    await page.goto('/painel')
    await page.getByRole('link', { name: 'Relatórios' }).first().click()
    await expect(page).toHaveURL(/\/relatorios$/)
    const adocoes = page.locator('.indicador', { hasText: 'adoções aprovadas' })
    await expect(adocoes.locator('strong')).toHaveText('1')
    await expect(page.locator('.indicador', { hasText: 'tempo médio até a adoção' }).locator('strong')).toHaveText('0 dias')

    const { texto } = await baixar(page, page.getByRole('button', { name: 'Interesses do período' }))
    const linhas = texto.replace('﻿', '').trim().split(/\r?\n/)
    expect(linhas).toHaveLength(2)
    expect(linhas[1]).toContain(`${animal.nome};${tutor.nome};${tutor.email}`)
    expect(linhas[1].endsWith(';Aprovado')).toBeTruthy()

    await page.getByRole('tab', { name: 'Histórico de operações' }).click()
    await expect(page.getByRole('cell', { name: 'Adoção aprovada' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Animal cadastrado' })).toBeVisible()
  })

  test('o filtro de período muda o relatório', async ({ page, request }) => {
    const { abrigo } = await adocaoAprovada(request)
    await entrarComo(page, abrigo)
    await page.goto('/relatorios')
    await expect(page.locator('.indicador', { hasText: 'adoções aprovadas' }).locator('strong')).toHaveText('1')
    await page.getByLabel('Até', { exact: true }).fill('2025-12-31')
    await page.getByLabel('De', { exact: true }).fill('2025-01-01')
    await expect(page.locator('.indicador', { hasText: 'adoções aprovadas' }).locator('strong')).toHaveText('0')
  })
})
