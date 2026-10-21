import { expect, test } from '@playwright/test'
import { contaAdmin, entrarComo } from './apoio'

// Aba "Núcleo OpenCL" da administração (RF-29). O E2E roda sem o núcleo (igual na CI): a tela precisa dizer
// isso com clareza e não deixar rodar o benchmark. Com o núcleo no ar: E2E_NUCLEO_URL=http://127.0.0.1:8001.
test('a administração vê o estado do núcleo e o benchmark só roda com ele no ar', async ({ page, request }) => {
  await entrarComo(page, await contaAdmin(request))
  await page.goto('/admin')
  await page.getByRole('tab', { name: 'Núcleo OpenCL' }).click()
  await expect(page).toHaveURL(/aba=nucleo/)
  await expect(page.getByRole('heading', { name: 'Sequencial × OpenCL (RF-29)' })).toBeVisible()
  if (process.env.E2E_NUCLEO_URL) {
    await expect(page.getByText('No ar')).toBeVisible()
    await page.getByRole('button', { name: 'Rodar a curva' }).click()
    await expect(page.getByRole('table')).toContainText('100.000', { timeout: 120_000 })
  } else {
    await expect(page.getByRole('alert')).toContainText('Fora do ar.')
    await expect(page.getByRole('button', { name: 'Rodar a curva' })).toBeDisabled()
  }
})
