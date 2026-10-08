import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { linkWhatsApp, STATUS_INTERESSE } from '../rotulos'

const COR = { aguardando: 'etiqueta--atencao', em_conversa: 'etiqueta--atencao', aprovado: 'etiqueta--ok', recusado: 'etiqueta--erro' }

export function ContatoAbrigo({ interesse }) {
  const whats = linkWhatsApp(interesse.abrigo_telefone)
  return (
    <dl>
      <dt>Abrigo</dt><dd>{interesse.nome_abrigo}</dd>
      <dt>Endereço</dt><dd>{interesse.abrigo_endereco}</dd>
      <dt>Telefone</dt>
      <dd>
        {interesse.abrigo_telefone || 'O abrigo não informou telefone.'}
        {whats && <> · <a href={whats} target="_blank" rel="noreferrer">Abrir no WhatsApp</a></>}
      </dd>
    </dl>
  )
}

export default function MeusInteresses() {
  const [interesses, setInteresses] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  const [desistindo, setDesistindo] = useState(null)

  const carregar = useCallback(async () => {
    try {
      setInteresses(await api('/interesses/meus'))
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => { carregar() }, [carregar])

  async function desistir(i) {
    setErro('')
    setOk('')
    try {
      await api(`/interesses/${i.id}`, { metodo: 'DELETE' })
      setOk(`Você desistiu do interesse em ${i.animal_nome}.`)
      setDesistindo(null)
      await carregar()
    } catch (err) {
      setErro(err.message)
      setDesistindo(null)
    }
  }

  return (
    <main className="pagina">
      <h1>Meus interesses</h1>
      <p className="subtitulo">Acompanhe as respostas dos abrigos e fale com eles pelo contato abaixo.</p>

      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {carregando && <p className="estado">Carregando…</p>}
      {!carregando && interesses.length === 0 && !erro && (
        <p className="estado">Você ainda não demonstrou interesse em nenhum animal. <Link to="/">Ver animais para adoção</Link></p>
      )}

      <div style={{ display: 'grid', gap: '1rem' }}>
        {interesses.map((i) => (
          <article key={i.id} className="cartao">
            <div className="topo-pagina" style={{ marginBottom: '0.5rem' }}>
              <h2 style={{ marginBottom: 0 }}><Link to={`/animais/${i.animal_id}`}>{i.animal_nome}</Link></h2>
              <span className={`etiqueta ${COR[i.status]}`}>{STATUS_INTERESSE[i.status]}</span>
            </div>
            {i.status === 'aprovado' && (
              <div className="aviso aviso--ok" role="status">O abrigo aprovou seu interesse. Entre em contato para combinar os próximos passos da adoção.</div>
            )}
            {i.status === 'recusado' && (
              <div className="aviso aviso--atencao" role="status">O abrigo não pôde seguir com este interesse. Você pode procurar outros animais no catálogo.</div>
            )}
            <div className="detalhe">
              <ContatoAbrigo interesse={i} />
              {i.mensagem && <p><strong>Sua mensagem:</strong> {i.mensagem}</p>}
            </div>
            {(i.status === 'aguardando' || i.status === 'em_conversa') && (
              <div className="acoes" style={{ marginTop: '0.75rem' }}>
                {desistindo === i.id ? (
                  <>
                    <span>Desistir do interesse em {i.animal_nome}?</span>
                    <button className="botao botao--perigo botao--pequeno" onClick={() => desistir(i)}>Sim, desistir</button>
                    <button className="botao botao--leve botao--pequeno" onClick={() => setDesistindo(null)}>Voltar</button>
                  </>
                ) : (
                  <button className="botao botao--leve botao--pequeno" onClick={() => setDesistindo(i.id)}>Desistir</button>
                )}
              </div>
            )}
          </article>
        ))}
      </div>
    </main>
  )
}
