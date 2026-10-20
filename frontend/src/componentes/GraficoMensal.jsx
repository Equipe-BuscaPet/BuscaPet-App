import { useState } from 'react'

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
export const rotuloMes = (aaaaMm) => { const [a, m] = aaaaMm.split('-'); return `${MESES[Number(m) - 1]}/${a.slice(2)}` }

// Barras mensais de UMA série (um gráfico por medida, lado a lado: "small multiples", sem dois eixos).
// Cor por slot (--serie-1..3, validadas para daltonismo); textos sempre na cor de texto.
// Passar o mouse (ou o foco do teclado) numa barra mostra o valor; o último mês tem o valor escrito.
export default function GraficoMensal({ titulo, serie, slot = 1 }) {
  const [ativo, setAtivo] = useState(null)
  const L = 300, A = 150, topo = 18, base = A - 22, esq = 8
  const max = Math.max(1, ...serie.map((p) => p.valor))
  const passo = (L - esq * 2) / serie.length
  const largura = Math.min(34, passo - 8)
  const altura = (v) => (v / max) * (base - topo)
  const ultimo = serie.length - 1
  const resumo = serie.map((p) => `${rotuloMes(p.mes)}: ${p.valor}`).join(', ')

  return (
    <figure className="grafico">
      <figcaption className="grafico__titulo">{titulo}</figcaption>
      <div className="grafico__area">
        <svg viewBox={`0 0 ${L} ${A}`} role="img" aria-label={`${titulo}. ${resumo}.`}>
          <line x1={esq} x2={L - esq} y1={base} y2={base} className="grafico__base" />
          {serie.map((p, i) => {
            const h = altura(p.valor)
            const x = esq + i * passo + (passo - largura) / 2
            const r = Math.min(4, h / 2)
            const caminho = h > 0
              ? `M${x},${base} V${base - h + r} Q${x},${base - h} ${x + r},${base - h} H${x + largura - r} Q${x + largura},${base - h} ${x + largura},${base - h + r} V${base} Z`
              : null
            return (
              <g key={p.mes}>
                {/* alvo maior que a barra, para facilitar o hover */}
                <rect x={esq + i * passo} y={topo - 10} width={passo} height={base - topo + 10} fill="transparent"
                  tabIndex={0} onMouseEnter={() => setAtivo(i)} onMouseLeave={() => setAtivo(null)} onFocus={() => setAtivo(i)} onBlur={() => setAtivo(null)}>
                  <title>{`${rotuloMes(p.mes)}: ${p.valor}`}</title>
                </rect>
                {caminho && <path d={caminho} style={{ fill: `var(--serie-${slot})` }} opacity={ativo === null || ativo === i ? 1 : 0.45} pointerEvents="none" />}
                <text x={x + largura / 2} y={A - 6} textAnchor="middle" className="grafico__mes">{rotuloMes(p.mes).slice(0, 3)}</text>
                {(i === ultimo || ativo === i) && (
                  <text x={x + largura / 2} y={base - h - 5} textAnchor="middle" className="grafico__valor">{p.valor}</text>
                )}
              </g>
            )
          })}
        </svg>
      </div>
    </figure>
  )
}

// A mesma informação em tabela (acessibilidade e alternativa ao contraste baixo de uma das cores).
export function TabelaMensal({ serie, colunas }) {
  return (
    <div className="cartao rolagem">
      <table>
        <thead><tr><th>Mês</th>{colunas.map(([, rotulo]) => <th key={rotulo}>{rotulo}</th>)}</tr></thead>
        <tbody>
          {serie.map((p) => (
            <tr key={p.mes}><td>{rotuloMes(p.mes)}</td>{colunas.map(([chave, rotulo]) => <td key={rotulo}>{p[chave]}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
