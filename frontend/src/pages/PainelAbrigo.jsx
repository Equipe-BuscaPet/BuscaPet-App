import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { ESPECIES, PORTES, SEXOS, STATUS_ANIMAL, textoIdade } from '../rotulos'

const FORM_VAZIO = {
  nome: '', especie: 'cao', raca_aproximada: '', porte: 'medio', sexo: 'indefinido', idade_estimada_meses: '',
  castrado: false, vacinado: false, vermifugado: false, temperamento: '',
  convivencia_criancas: '', convivencia_outros_animais: '', historia_resgate: '', data_entrada: '',
  status: 'disponivel',
}

const triParaTexto = (v) => (v === null || v === undefined ? '' : String(v))
const textoParaTri = (v) => (v === '' ? null : v === 'true')
const vazioParaNulo = (v) => (v === '' ? null : v)

function doAnimal(a) {
  return {
    nome: a.nome, especie: a.especie, raca_aproximada: a.raca_aproximada ?? '', porte: a.porte, sexo: a.sexo,
    idade_estimada_meses: a.idade_estimada_meses ?? '', castrado: a.castrado, vacinado: a.vacinado, vermifugado: a.vermifugado,
    temperamento: a.temperamento ?? '', convivencia_criancas: triParaTexto(a.convivencia_criancas),
    convivencia_outros_animais: triParaTexto(a.convivencia_outros_animais), historia_resgate: a.historia_resgate ?? '',
    data_entrada: a.data_entrada ? a.data_entrada.slice(0, 10) : '', status: a.status,
  }
}

function paraApi(f) {
  return {
    nome: f.nome.trim(), especie: f.especie, raca_aproximada: vazioParaNulo(f.raca_aproximada), porte: f.porte, sexo: f.sexo,
    idade_estimada_meses: f.idade_estimada_meses === '' ? null : Number(f.idade_estimada_meses),
    castrado: f.castrado, vacinado: f.vacinado, vermifugado: f.vermifugado, temperamento: vazioParaNulo(f.temperamento),
    convivencia_criancas: textoParaTri(f.convivencia_criancas), convivencia_outros_animais: textoParaTri(f.convivencia_outros_animais),
    historia_resgate: vazioParaNulo(f.historia_resgate), data_entrada: vazioParaNulo(f.data_entrada),
  }
}

function FormularioAnimal({ inicial, editando, desabilitado, onSalvar, onCancelar }) {
  const [f, setF] = useState(inicial)
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)

  const campo = (nome) => ({ id: nome, value: f[nome], onChange: (e) => setF({ ...f, [nome]: e.target.value }) })
  const marca = (nome) => ({ id: nome, checked: f[nome], onChange: (e) => setF({ ...f, [nome]: e.target.checked }) })

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setSalvando(true)
    try {
      await onSalvar(f)
    } catch (err) {
      setErro(err.message)
    } finally {
      setSalvando(false)
    }
  }

  return (
    <form className="cartao formulario" onSubmit={enviar}>
      <h2>{editando ? `Editar ${inicial.nome}` : 'Cadastrar animal'}</h2>
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
      <fieldset disabled={desabilitado} className="formulario" style={{ display: 'grid', gap: '0.9rem' }}>
        <div className="campo"><label htmlFor="nome">Nome</label><input {...campo('nome')} required maxLength={120} /></div>
        <div className="grade-campos">
          <div className="campo"><label htmlFor="especie">Espécie</label>
            <select {...campo('especie')}>{Object.entries(ESPECIES).map(([v, r]) => <option key={v} value={v}>{r}</option>)}</select></div>
          <div className="campo"><label htmlFor="porte">Porte</label>
            <select {...campo('porte')}>{Object.entries(PORTES).map(([v, r]) => <option key={v} value={v}>{r}</option>)}</select></div>
          <div className="campo"><label htmlFor="sexo">Sexo</label>
            <select {...campo('sexo')}>{Object.entries(SEXOS).map(([v, r]) => <option key={v} value={v}>{r}</option>)}</select></div>
        </div>
        <div className="grade-campos">
          <div className="campo"><label htmlFor="raca_aproximada">Raça aproximada</label><input {...campo('raca_aproximada')} maxLength={120} /></div>
          <div className="campo"><label htmlFor="idade_estimada_meses">Idade estimada (meses)</label>
            <input {...campo('idade_estimada_meses')} type="number" min="0" max="600" /></div>
          <div className="campo"><label htmlFor="data_entrada">Data de entrada no abrigo</label><input {...campo('data_entrada')} type="date" /></div>
        </div>
        <div className="acoes">
          <label className="marcar"><input type="checkbox" {...marca('castrado')} /> Castrado</label>
          <label className="marcar"><input type="checkbox" {...marca('vacinado')} /> Vacinado</label>
          <label className="marcar"><input type="checkbox" {...marca('vermifugado')} /> Vermifugado</label>
        </div>
        <div className="grade-campos">
          <div className="campo"><label htmlFor="convivencia_criancas">Convive com crianças</label>
            <select {...campo('convivencia_criancas')}><option value="">Não informado</option><option value="true">Sim</option><option value="false">Não</option></select></div>
          <div className="campo"><label htmlFor="convivencia_outros_animais">Convive com outros animais</label>
            <select {...campo('convivencia_outros_animais')}><option value="">Não informado</option><option value="true">Sim</option><option value="false">Não</option></select></div>
          {editando && (
            <div className="campo"><label htmlFor="status">Situação</label>
              <select {...campo('status')}>{Object.entries(STATUS_ANIMAL).map(([v, r]) => <option key={v} value={v}>{r}</option>)}</select></div>
          )}
        </div>
        <div className="campo"><label htmlFor="temperamento">Temperamento</label><textarea {...campo('temperamento')} maxLength={500} /></div>
        <div className="campo"><label htmlFor="historia_resgate">História do resgate</label><textarea {...campo('historia_resgate')} maxLength={2000} /></div>
      </fieldset>
      <div className="acoes">
        <button className="botao" disabled={salvando || desabilitado}>{salvando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Cadastrar'}</button>
        {editando && <button type="button" className="botao botao--leve" onClick={onCancelar}>Cancelar</button>}
      </div>
    </form>
  )
}

export default function PainelAbrigo() {
  const { usuario, atualizarUsuario } = useAuth()
  const [animais, setAnimais] = useState([])
  const [editando, setEditando] = useState(null)
  const [excluindo, setExcluindo] = useState(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')

  const status = usuario.perfil?.status_validacao
  const ativo = status !== 'rejeitado'  // só o abrigo suspenso fica bloqueado

  const carregar = useCallback(async () => {
    try {
      setAnimais(await api('/animais/meus'))
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }, [])

  // O administrador pode ter aprovado o abrigo depois do login: relê a conta ao abrir o painel.
  useEffect(() => {
    atualizarUsuario().catch(() => {})
    carregar()
  }, [atualizarUsuario, carregar])

  async function salvar(f) {
    setOk('')
    if (editando) {
      await api(`/animais/${editando.id}`, { metodo: 'PATCH', corpo: { ...paraApi(f), status: f.status } })
      setEditando(null)
      await carregar()
      setOk(`${f.nome} foi atualizado.`)
    } else {
      const corpo = Object.fromEntries(Object.entries(paraApi(f)).filter(([, v]) => v !== null))
      await api('/animais', { metodo: 'POST', corpo })
      await carregar()
      setOk(`${f.nome} foi cadastrado.`)
    }
  }

  async function excluir(animal) {
    setErro('')
    setOk('')
    try {
      await api(`/animais/${animal.id}`, { metodo: 'DELETE' })
      if (editando?.id === animal.id) setEditando(null)
      await carregar()
      setOk(`${animal.nome} foi excluído.`)
    } catch (err) {
      setErro(err.message)
    } finally {
      setExcluindo(null)
    }
  }

  return (
    <main className="pagina">
      <div className="topo-pagina">
        <div>
          <h1>Meus animais</h1>
          <p className="subtitulo" style={{ margin: 0 }}>{usuario.perfil?.nome_abrigo}</p>
        </div>
      </div>

      {status === 'pendente' && (
        <div className="aviso aviso--atencao" role="status">
          Seu abrigo ainda não tem o selo Verificado. Você já pode cadastrar animais; o selo, concedido pela administração, é o que libera a exibição da chave de doação e a entrada no ranking.
        </div>
      )}
      {status === 'rejeitado' && (
        <div className="aviso aviso--erro" role="alert">Seu abrigo foi suspenso pela administração e seus animais não aparecem no catálogo. Entre em contato com a equipe BuscaPet.</div>
      )}
      {ok && <div className="aviso aviso--ok" role="status">{ok}</div>}
      {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}

      <div className="duas-colunas">
        <section aria-labelledby="titulo-lista">
          <h2 id="titulo-lista">Animais cadastrados ({animais.length})</h2>
          {carregando && <p className="estado">Carregando…</p>}
          {!carregando && animais.length === 0 && (
            <p className="estado">{ativo ? 'Nenhum animal cadastrado ainda. Use o formulário ao lado.' : 'Nenhum animal cadastrado.'}</p>
          )}
          {animais.length > 0 && (
            <div className="cartao rolagem">
              <table>
                <thead><tr><th>Nome</th><th>Espécie</th><th>Idade</th><th>Situação</th><th><span className="sr-only">Ações</span></th></tr></thead>
                <tbody>
                  {animais.map((a) => (
                    <tr key={a.id}>
                      <td><Link to={`/animais/${a.id}`}>{a.nome}</Link></td>
                      <td>{ESPECIES[a.especie]}</td>
                      <td>{textoIdade(a.idade_estimada_meses)}</td>
                      <td><span className={`etiqueta ${a.status === 'disponivel' ? 'etiqueta--ok' : ''}`}>{STATUS_ANIMAL[a.status]}</span></td>
                      <td>
                        <div className="acoes">
                          <button className="botao botao--leve botao--pequeno" disabled={!ativo} onClick={() => { setEditando(a); setOk('') }}>Editar</button>
                          {excluindo === a.id ? (
                            <>
                              <button className="botao botao--perigo botao--pequeno" onClick={() => excluir(a)}>Confirmar exclusão</button>
                              <button className="botao botao--leve botao--pequeno" onClick={() => setExcluindo(null)}>Cancelar</button>
                            </>
                          ) : (
                            <button className="botao botao--leve botao--pequeno" disabled={!ativo} onClick={() => setExcluindo(a.id)}>Excluir</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <FormularioAnimal
          key={editando ? `editar-${editando.id}` : 'novo'}
          inicial={editando ? doAnimal(editando) : FORM_VAZIO}
          editando={Boolean(editando)}
          desabilitado={!ativo}
          onSalvar={salvar}
          onCancelar={() => setEditando(null)}
        />
      </div>
    </main>
  )
}
