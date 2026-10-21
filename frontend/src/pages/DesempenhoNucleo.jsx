import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

// RF-29: modo comparativo de desempenho, ao vivo. Cada ponto roda no núcleo a mesma etapa em C sequencial e em
// OpenCL (média de 3, depois de 1 aquecimento) e confere se os resultados bateram.
const ETAPAS = {
  busca: { rotulo: 'Busca: 1 foto contra n registros', ns: [100, 1000, 10000, 100000], unidade: 'registros' },
  lote: { rotulo: 'Monitoramento: 100 fotos novas contra n buscas ativas', ns: [100, 1000, 5000, 20000], unidade: 'buscas ativas' },
  extracao: { rotulo: 'Extração: n fotos viram descritores', ns: [10, 100, 500, 1000], unidade: 'fotos' },
}
const ms = (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: v < 10 ? 2 : 1 })} ms`
const vezes = (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}×`

// Um gráfico só, uma série só: o ganho (speedup) de cada tamanho, com as referências de "empate" (1×) e do número
// de núcleos. Os tempos ficam na tabela ao lado.
function GraficoGanho({ pontos, nucleos }) {
  const L = 520, A = 210, esq = 34, dir = 10, topo = 16, base = A - 30
  const teto = Math.max(nucleos || 4, ...pontos.map((p) => p.speedup)) * 1.1
  const y = (v) => base - (v / teto) * (base - topo)
  const passo = (L - esq - dir) / Math.max(pontos.length, 1)
  const larg = Math.min(48, passo - 14)
  return (
    <svg viewBox={`0 0 ${L} ${A}`} className="grafico-ganho" role="img"
      aria-label={`Ganho do OpenCL sobre o sequencial: ${pontos.map((p) => `${p.n}: ${vezes(p.speedup)}`).join('; ')}`}>
      {[1, nucleos].filter(Boolean).map((ref) => (
        <g key={ref}>
          <line x1={esq} x2={L - dir} y1={y(ref)} y2={y(ref)} className="grafico-ganho__ref" />
          <text x={esq - 4} y={y(ref) + 4} textAnchor="end" className="grafico-ganho__eixo">{ref}×</text>
        </g>
      ))}
      <text x={L - dir} y={y(1) - 4} textAnchor="end" className="grafico-ganho__eixo">empate</text>
      {nucleos && <text x={L - dir} y={y(nucleos) - 4} textAnchor="end" className="grafico-ganho__eixo">{nucleos} núcleos</text>}
      {pontos.map((p, i) => {
        const x = esq + i * passo + (passo - larg) / 2
        return (
          <g key={p.n}>
            <title>{`${p.n.toLocaleString('pt-BR')}: sequencial ${ms(p.seq)}, OpenCL ${ms(p.ocl)}, ganho ${vezes(p.speedup)}`}</title>
            <rect x={x} y={y(p.speedup)} width={larg} height={Math.max(base - y(p.speedup), 1)} rx="4" className="grafico-ganho__barra" />
            <text x={x + larg / 2} y={y(p.speedup) - 5} textAnchor="middle" className="grafico-ganho__valor">{vezes(p.speedup)}</text>
            <text x={x + larg / 2} y={base + 16} textAnchor="middle" className="grafico-ganho__eixo">{p.n.toLocaleString('pt-BR')}</text>
          </g>
        )
      })}
      <line x1={esq} x2={L - dir} y1={base} y2={base} className="grafico-ganho__base" />
    </svg>
  )
}

export default function DesempenhoNucleo() {
  const [estado, setEstado] = useState(null)
  const [etapa, setEtapa] = useState('busca')
  const [pontos, setPontos] = useState([])
  const [rodando, setRodando] = useState(null)
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')

  const carregar = useCallback(() => api('/admin/nucleo').then(setEstado).catch((e) => setErro(e.message)), [])
  useEffect(() => { carregar() }, [carregar])

  async function rodarCurva() {
    setErro('')
    setPontos([])
    for (const n of ETAPAS[etapa].ns) {
      setRodando(n)
      try {
        const r = await api(`/admin/nucleo/benchmark?etapa=${etapa}&n=${n}`)
        setPontos((atual) => [...atual, { n, seq: r.sequencial.total_ms, ocl: r.opencl.total_ms, speedup: r.speedup, iguais: r.resultados_iguais, kernel: r.speedup_kernel }])
      } catch (e) {
        setErro(e.message)
        break
      }
    }
    setRodando(null)
  }

  async function indexar() {
    setErro('')
    try {
      const r = await api('/admin/nucleo/indexar', { metodo: 'POST' })
      setAviso(`${r.indexadas} foto(s) processada(s). Faltam ${r.sem_descritor}.`)
      carregar()
    } catch (e) {
      setErro(e.message)
    }
  }

  const nucleos = estado?.nucleo?.opencl?.unidades_computo
  return (
    <section className="desempenho">
      <div className="cartao">
        <h2>Núcleo OpenCL</h2>
        {!estado && !erro && <p className="estado">Consultando o núcleo…</p>}
        {estado && (estado.no_ar ? (
          <p className="aviso aviso--ok" role="status" style={{ margin: 0 }}>
            <strong>No ar</strong> · {estado.nucleo.opencl.dispositivo} · {nucleos} núcleo(s) · {estado.nucleo.opencl.plataforma}
          </p>
        ) : (
          <p className="aviso aviso--erro" role="alert" style={{ margin: 0 }}>
            <strong>Fora do ar.</strong> A busca por foto mostra os registros por distância até o núcleo voltar. {estado.motivo}
          </p>
        ))}
        {estado && (
          <p>
            Fotos com descritor: <strong>{estado.com_descritor}</strong> de {estado.fotos}.
            {estado.sem_descritor > 0 && estado.no_ar && <> <button type="button" className="botao botao--pequeno" onClick={indexar}>Calcular os {estado.sem_descritor} que faltam</button></>}
          </p>
        )}
        {aviso && <p className="aviso aviso--ok" role="status">{aviso}</p>}
      </div>

      <div className="cartao">
        <h2>Sequencial × OpenCL (RF-29)</h2>
        <p className="subtitulo">
          Cada tamanho roda no núcleo a mesma conta das duas formas: em C, um núcleo por vez, e em OpenCL, todos os
          núcleos juntos. Dica para a apresentação: deixe o Gerenciador de Tarefas aberto em Desempenho → CPU →
          Processadores lógicos e rode o monitoramento.
        </p>
        <div className="semelhanca__filtros">
          <label>Etapa
            <select value={etapa} onChange={(e) => { setEtapa(e.target.value); setPontos([]) }} disabled={rodando !== null}>
              {Object.entries(ETAPAS).map(([v, e]) => <option key={v} value={v}>{e.rotulo}</option>)}
            </select>
          </label>
          <button type="button" className="botao" onClick={rodarCurva} disabled={rodando !== null || !estado?.no_ar}>
            {rodando !== null ? `Medindo n = ${rodando.toLocaleString('pt-BR')}…` : 'Rodar a curva'}
          </button>
        </div>
        {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
        {pontos.length > 0 && (
          <div className="desempenho__resultado">
            <figure style={{ margin: 0 }}>
              <figcaption><strong>Ganho do OpenCL</strong> (quantas vezes mais rápido) por número de {ETAPAS[etapa].unidade}</figcaption>
              <GraficoGanho pontos={pontos} nucleos={nucleos} />
            </figure>
            <table className="tabela">
              <thead><tr><th>n</th><th>Sequencial</th><th>OpenCL</th><th>Ganho</th><th>Mesmo resultado</th></tr></thead>
              <tbody>
                {pontos.map((p) => (
                  <tr key={p.n}>
                    <td>{p.n.toLocaleString('pt-BR')}</td><td>{ms(p.seq)}</td><td>{ms(p.ocl)}</td>
                    <td><strong>{vezes(p.speedup)}</strong> <small>(kernel {vezes(p.kernel)})</small></td>
                    <td>{p.iguais ? '✓ sim' : '✗ não'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p><small>
          Com pouco volume o OpenCL perde: o custo fixo de preparar o trabalho domina. Com volume, o ganho se aproxima do
          número de núcleos, sem passar dele, porque sempre sobra uma parte que não paraleliza (Lei de Amdahl).
        </small></p>
      </div>
    </section>
  )
}
