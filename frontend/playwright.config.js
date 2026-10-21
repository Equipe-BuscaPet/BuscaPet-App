// Testes de ponta a ponta (E2E): um navegador de verdade abre o BuscaPet e usa as telas como uma pessoa usaria.
// Rodar:  npm run e2e            (sobe a API e a interface de teste sozinho)
//         npm run e2e:ver        (abre a janela do Playwright para acompanhar passo a passo)
//
// Os testes usam um ambiente SÓ DELES, para não sujar o banco de desenvolvimento:
//   banco buscapet_e2e (criado e migrado sozinho) · API na porta 8100 · interface na porta 5174.
// Pré-requisito: o Postgres local ligado (o mesmo servidor do desenvolvimento).
import { defineConfig, devices } from '@playwright/test'

const CI = Boolean(process.env.CI)
const PORTA_API = 8100
const PORTA_WEB = 5174
const API_URL = `http://localhost:${PORTA_API}`
const BANCO = process.env.E2E_DATABASE_URL || 'postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet_e2e'
// Python do venv da API (Windows e Linux têm caminhos diferentes); a CI informa PYTHON=python.
// (No Windows o comando roda no cmd.exe, que exige barra invertida no caminho do executável.)
const PYTHON = process.env.PYTHON || (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python')
process.env.API_URL = API_URL // lido por e2e/apoio.js

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
    baseURL: `http://localhost:${PORTA_WEB}`,
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
      // Prepara o banco de teste (cria + migrations) e sobe a API apontando para ele.
      command: `${PYTHON} -m app.scripts.preparar_banco_teste ${BANCO} && ${PYTHON} -m uvicorn app.main:app --port ${PORTA_API}`,
      cwd: '../api',
      url: `${API_URL}/health/db`,
      env: {
        DATABASE_URL: BANCO,
        CORS_ORIGENS: `["http://localhost:${PORTA_WEB}"]`,
        PASTA_FOTOS: 'uploads/fotos-e2e', // fotos dos testes separadas das do desenvolvimento
        // Sem núcleo OpenCL nos E2E (a CI não o sobe): porta fechada = falha na hora, e a busca avisa e lista
        // por distância. Para testar com o núcleo no ar: E2E_NUCLEO_URL=http://127.0.0.1:8001 npm run e2e
        NUCLEO_OPENCL_URL: process.env.E2E_NUCLEO_URL || 'http://127.0.0.1:9',
        PGTZ: 'America/Recife',
        PYTHONIOENCODING: 'utf-8',
      },
      reuseExistingServer: !CI,
      timeout: 120_000,
    },
    {
      command: `npx vite --port ${PORTA_WEB} --strictPort`,
      url: `http://localhost:${PORTA_WEB}`,
      env: { VITE_API_URL: API_URL },
      reuseExistingServer: !CI,
      timeout: 60_000,
    },
  ],
})
