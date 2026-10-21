// Filtro de período usado no painel, nos relatórios e no histórico: atalhos (30 dias, 90 dias, este ano)
// e as datas exatas. As datas são dias no fuso local; a API trata "até" como o dia inteiro.
const hoje = () => new Date().toLocaleDateString('sv-SE') // AAAA-MM-DD no fuso do navegador
const diasAtras = (n) => { const d = new Date(); d.setDate(d.getDate() - n + 1); return d.toLocaleDateString('sv-SE') }

export const periodoPadrao = () => ({ de: diasAtras(90), ate: hoje() })

const ATALHOS = [
  ['30 dias', () => ({ de: diasAtras(30), ate: hoje() })],
  ['90 dias', () => ({ de: diasAtras(90), ate: hoje() })],
  ['Este ano', () => ({ de: `${new Date().getFullYear()}-01-01`, ate: hoje() })],
]

export default function FiltroPeriodo({ periodo, aoMudar, children }) {
  const ativo = ATALHOS.find(([, f]) => { const p = f(); return p.de === periodo.de && p.ate === periodo.ate })?.[0]
  return (
    <div className="filtro-periodo" role="group" aria-label="Período">
      <div className="acoes">
        {ATALHOS.map(([rotulo, f]) => (
          <button key={rotulo} type="button" aria-pressed={ativo === rotulo} className={`botao botao--pequeno ${ativo === rotulo ? '' : 'botao--leve'}`} onClick={() => aoMudar(f())}>
            {rotulo}
          </button>
        ))}
      </div>
      <div className="campo">
        <label htmlFor="periodo-de">De</label>
        <input id="periodo-de" type="date" value={periodo.de} max={periodo.ate} onChange={(e) => e.target.value && aoMudar({ ...periodo, de: e.target.value })} />
      </div>
      <div className="campo">
        <label htmlFor="periodo-ate">Até</label>
        <input id="periodo-ate" type="date" value={periodo.ate} min={periodo.de} onChange={(e) => e.target.value && aoMudar({ ...periodo, ate: e.target.value })} />
      </div>
      {children}
    </div>
  )
}
