// Testes de ponta a ponta (E2E): um navegador de verdade abre o BuscaPet e usa as telas como uma pessoa usaria.
// Rodar:  npm run e2e            (sobe API e interface sozinho, se ainda não estiverem no ar)
//         npm run e2e:ver        (abre a janela do Playwright para acompanhar passo a passo)
// Pré-requisitos: banco com as migrations aplicadas e api/.env configurado (ver README da raiz).
import { defineConfig, devices } from '@playwright/test'

const CI = Boolean(process.env.CI)
const API_URL = process.env.API_URL || 'http://localhost:8000'
// Python do venv da API (Windows e Linux têm caminhos diferentes); a CI informa PYTHON=python.
const PYTHON = process.env.PYTHON || (process.platform === 'win32' ? '.venv/Scripts/python' : '.venv/bin/python')

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: true,
  forbidOnly: CI, // um `test.only` esquecido não pode passar na CI
  retries: CI ? 1 : 0,
  workers: CI ? 2 : undefined,
  reporter: CI ? [['github'], ['html', { open: 'never' }], ['list']] : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5173',
    locale: 'pt-BR',
    timezoneId: 'America/Recife', // o fuso dos usuários; foi assim que o defeito das datas apareceu
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'computador', use: { ...devices['Desktop Chrome'] } },
    // No celular roda só o que tem a marca @celular (layout e navegação).
    { name: 'celular', use: { ...devices['Pixel 7'] }, grep: /@celular/ },
  ],
  webServer: [
    {
      command: `${PYTHON} -m uvicorn app.main:app --port 8000`,
      cwd: '../api',
      url: `${API_URL}/health/db`,
      reuseExistingServer: !CI,
      timeout: 60_000,
    },
    {
      command: 'npx vite --port 5173 --strictPort',
      url: 'http://localhost:5173',
      reuseExistingServer: !CI,
      timeout: 60_000,
    },
  ],
})
