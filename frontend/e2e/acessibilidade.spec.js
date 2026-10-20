import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { contaAdmin, criarAnimal, criarConta, entrarComo, publicarNecessidade, verificarAbrigo } from './apoio'

// Sprint 9 — acessibilidade automática com o axe-core (a mesma regra usada pelo Lighthouse do Chrome):
// cada tela principal, com o perfil que a usa, não pode ter violação grave ou crítica (WCAG 2.1 A e AA).

test.describe.configure({ mode: 'serial' })

const REGRAS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
const GRAVES = new Set(['serious', 'critical'])

let cenario
test.beforeAll(async ({ request }) => {
  const abrigo = await criarConta(request, 'abrigo')
  await verificarAbrigo(request, abrigo)
  const animal = await criarAnimal(request, abrigo)
  await publicarNecessidade(request, abrigo)
  cenario = { abrigo, animal, admin: await contaAdmin(request), tutor: await criarConta(request, 'tutor') }
})

const TELAS = [
  ['visitante', () => ['/', '/mapa', '/mapa?ver=animais', '/reencontro', '/quem-apoia', '/login', '/cadastro', '/esqueci-senha', '/perdi',
    `/animais/${cenario.animal.id}`, `/abrigos/${cenario.abrigo.usuario.id}`]],
  ['tutor', () => ['/conta', '/notificacoes', '/interesses', '/meus-registros']],
  ['abrigo', () => ['/painel', '/interessados', '/doacoes', '/relatorios']],
  ['admin', () => ['/admin', '/admin?aba=abrigos', '/admin?aba=denuncias', '/admin?aba=historico', '/admin?aba=contas']],
]

for (const [perfil, rotas] of TELAS) {
  test(`acessibilidade (axe, WCAG 2.1 AA): telas do ${perfil}`, async ({ page }) => {
    test.setTimeout(180_000)
    if (perfil !== 'visitante') await entrarComo(page, cenario[perfil])
    const achados = []
    for (const rota of rotas()) {
      await page.goto(rota)
      await page.waitForLoadState('networkidle')
      const { violations } = await new AxeBuilder({ page }).withTags(REGRAS).exclude('.leaflet-container').analyze()
      for (const v of violations.filter((v) => GRAVES.has(v.impact))) {
        achados.push(`${rota} — ${v.id} (${v.impact}): ${v.help} [${v.nodes.length}x] ${v.nodes[0]?.target?.join(' ')}`)
      }
    }
    console.log(`[axe] ${perfil}: ${achados.length} violação(ões) grave(s)\n${achados.join('\n')}`)
    expect(achados, achados.join('\n')).toEqual([])
  })
}
