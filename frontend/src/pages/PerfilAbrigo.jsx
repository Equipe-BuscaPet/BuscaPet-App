import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import CartaoNecessidade from '../componentes/CartaoNecessidade'
import DoarDinheiro from '../componentes/DoarDinheiro'
import { EMOJI_ESTABELECIMENTO, linkWhatsApp } from '../rotulos'
import { CartaoAnimal } from './Catalogo'

// Perfil público do abrigo (RF-12): junta os três módulos — animais para adoção, necessidades (doações)
// e quem já apoiou —, além de contatos e da chave de doação (só com o selo Verificado).
export default function PerfilAbrigo() {
  const { id } = useParams()
  const [abrigo, setAbrigo] = useState(null)
  const [animais, setAnimais] = useState([])
  const [erro, setErro] = useState('')

  useEffect(() => {
    setAbrigo(null)
    setErro('')
    api(`/abrigos/${id}`)
      .then(setAbrigo)
      .catch((e) => setErro(e.status === 404 ? 'Abrigo não encontrado.' : e.message))
    api(`/animais?abrigo_id=${id}&limite=8`).then(setAnimais).catch(() => setAnimais([]))
  }, [id])

  const recarregar = () => api(`/abrigos/${id}`).then(setAbrigo).catch(() => {})

  if (erro) return <main className="pagina"><p><Link to="/mapa">← Mapa de abrigos</Link></p><div className="aviso aviso--erro" role="alert">{erro}</div></main>
  if (!abrigo) return <p className="estado">Carregando…</p>
  const whats = linkWhatsApp(abrigo.telefone)

  return (
    <main className="pagina">
      <p><Link to="/mapa">← Mapa de abrigos</Link></p>
      <div className="topo-pagina">
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>{abrigo.nome_abrigo}</h1>
          <span className={`etiqueta ${abrigo.verificado ? 'etiqueta--ok' : 'etiqueta--atencao'}`}>{abrigo.verificado ? 'Verificado' : 'Não verificado'}</span>
        </div>
        <div className="acoes">
          <Link className="botao" to={`/?abrigo=${abrigo.id}`}>Ver os {abrigo.animais_disponiveis} animais para adoção</Link>
        </div>
      </div>

      <div className="duas-colunas" style={{ marginTop: '1rem' }}>
        <section className="cartao detalhe" aria-labelledby="t-contato">
          <h2 id="t-contato" style={{ margin: 0 }}>Sobre e contato</h2>
          {abrigo.descricao && <p style={{ margin: 0 }}>{abrigo.descricao}</p>}
          <dl>
            <dt>Endereço</dt><dd>{abrigo.endereco}</dd>
            {abrigo.horario_funcionamento && <><dt>Horário</dt><dd>{abrigo.horario_funcionamento}</dd></>}
            {abrigo.telefone && (
              <><dt>Telefone</dt><dd>{abrigo.telefone}{whats && <> · <a href={whats} target="_blank" rel="noreferrer">WhatsApp</a></>}</dd></>
            )}
          </dl>
          {!abrigo.verificado && (
            <div className="aviso aviso--atencao" style={{ margin: 0 }}>
              Este abrigo ainda não foi verificado pela administração. Por segurança, a chave de doação e o mural de necessidades só aparecem depois do selo.
            </div>
          )}
        </section>

        <section className="cartao" aria-labelledby="t-apoiadores">
          <h2 id="t-apoiadores">Quem apoia este abrigo</h2>
          {abrigo.apoiadores.length === 0
            ? <p className="estado" style={{ padding: '0.5rem 0' }}>Ainda sem doações confirmadas. <Link to="/quem-apoia">Conheça o Quem apoia</Link>.</p>
            : (
              <ul className="chips">
                {abrigo.apoiadores.map((a) => (
                  <li key={a.id}>
                    <Link to={`/apoiadores/${a.id}`}><span aria-hidden="true">{EMOJI_ESTABELECIMENTO[a.tipo_estabelecimento]}</span> {a.nome}{a.selo_ativo && <span className="selo-apoio">ativo</span>}</Link>
                  </li>
                ))}
              </ul>
            )}
        </section>
      </div>

      {abrigo.chave_doacao_financeira && (
        <div style={{ marginTop: '1rem' }}><DoarDinheiro abrigo={abrigo} aoDoar={recarregar} /></div>
      )}

      {abrigo.verificado && (
        <section aria-labelledby="t-necessidades" style={{ marginTop: '2rem' }}>
          <h2 id="t-necessidades">O que o abrigo precisa agora</h2>
          {abrigo.necessidades.length === 0 && <p className="estado">Nenhuma necessidade em aberto no momento.</p>}
          <div className="necessidades">
            {abrigo.necessidades.map((n) => <CartaoNecessidade key={n.id} necessidade={n} mostrarAbrigo={false} aoDoar={recarregar} />)}
          </div>
        </section>
      )}

      <section aria-labelledby="t-animais" style={{ marginTop: '2rem' }}>
        <h2 id="t-animais">Animais para adoção</h2>
        {animais.length === 0 && <p className="estado">Nenhum animal disponível agora.</p>}
        <div className="grade-animais">
          {animais.map((a) => <CartaoAnimal key={a.id} animal={a} />)}
        </div>
      </section>
    </main>
  )
}
