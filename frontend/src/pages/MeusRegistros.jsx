import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CartaoRegistro, { TIPOS_REGISTRO } from '../componentes/CartaoRegistro'

// Os registros de reencontro da própria conta: perdidos (só tutor) e avistamentos (qualquer conta).
export default function MeusRegistros() {
  const { usuario } = useAuth()
  const { state } = useLocation()
  const ehTutor = usuario.tipo_conta === 'tutor'
  const [perdidos, setPerdidos] = useState(null)
  const [avistamentos, setAvistamentos] = useState(null)
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState(state?.aviso || '')

  const carregar = useCallback(() => {
    setErro('')
    if (ehTutor) api('/perdidos/meus').then(setPerdidos).catch((e) => setErro(e.message))
    api('/avistamentos/meus').then(setAvistamentos).catch((e) => setErro(e.message))
  }, [ehTutor])

  useEffect(() => { carregar() }, [carregar])

  async function excluir(tipo, registro) {
    if (!window.confirm('Excluir este registro e as fotos dele? Esta ação não pode ser desfeita.')) return
    setAviso('')
    try {
      await api(`${TIPOS_REGISTRO[tipo].caminhoApi}/${registro.id}`, { metodo: 'DELETE' })
      setAviso('Registro excluído.')
      carregar()
    } catch (e) {
      setErro(e.message)
    }
  }

  async function resolver(registro) {
    if (!window.confirm('Marcar como resolvido? O registro sai do mapa e você deixa de receber alertas de avistamentos.')) return
    setAviso('')
    try {
      await api(`/perdidos/${registro.id}/resolvido`, { metodo: 'PATCH' })
      setAviso('Caso marcado como resolvido. Que bom que vocês se reencontraram!')
      carregar()
    } catch (e) {
      setErro(e.message)
    }
  }

  function secao(titulo, tipo, lista, vazio, novo) {
    return (
      <section style={{ marginBottom: '2rem' }}>
        <div className="topo-pagina">
          <h2 style={{ margin: 0 }}>{titulo}</h2>
          <Link className="botao botao--pequeno" to={novo[0]}>{novo[1]}</Link>
        </div>
        {lista === null && <p className="estado">Carregando…</p>}
        {lista?.length === 0 && <p className="estado">{vazio}</p>}
        <div className="grade-animais">
          {lista?.map((r) => (
            <CartaoRegistro
              key={r.id} registro={r} tipo={tipo}
              acoes={<>
                {tipo === 'perdido' && !r.resolvido && (
                  <button type="button" className="botao botao--pequeno" onClick={() => resolver(r)}>Encontrei meu animal</button>
                )}
                <button type="button" className="botao botao--leve botao--pequeno" onClick={() => excluir(tipo, r)}>Excluir</button>
              </>}
            />
          ))}
        </div>
      </section>
    )
  }

  return (
    <main className="pagina">
      <h1>Meus registros</h1>
      <p className="subtitulo">Aqui você vê os seus registros com o ponto exato que marcou. Para as outras pessoas, o local aparece aproximado.</p>
      {aviso && <div className="aviso aviso--ok" role="status">{aviso}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      {ehTutor && secao('Animais que perdi', 'perdido', perdidos, 'Você não tem nenhum animal registrado como perdido.', ['/perdi', 'Registrar animal perdido'])}
      {secao('Animais que avistei', 'avistamento', avistamentos, 'Você ainda não registrou nenhum avistamento.', ['/encontrei', 'Registrar avistamento'])}
    </main>
  )
}
