import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { ROTULO_TIPO } from '../componentes/MenuConta'
import { CATEGORIAS_EMPRESA } from '../rotulos'

// Minha conta (RF-37): dados da conta, troca de senha e atalhos. Usa a API que já existia (/usuarios/eu).
// Cada tipo de conta edita só os campos que lhe cabem (a mesma regra vale na API).
const CAMPOS = {
  tutor: [['telefone', 'Telefone', { maxLength: 20, inputMode: 'tel' }], ['cidade', 'Cidade', { maxLength: 120 }]],
  abrigo: [
    ['nome_abrigo', 'Nome do abrigo', { maxLength: 150, required: true }],
    ['endereco', 'Endereço', { maxLength: 255, required: true }],
    ['telefone', 'Telefone', { maxLength: 20, inputMode: 'tel' }],
    ['horario_funcionamento', 'Horário de funcionamento', { maxLength: 255 }],
    ['chave_doacao_financeira', 'Chave PIX para doações (só aparece com o selo Verificado)', { maxLength: 140 }],
    ['descricao', 'Sobre o abrigo', { maxLength: 2000, textarea: true }],
  ],
  apoiador: [['endereco', 'Endereço', { maxLength: 255, required: true }]],
  admin: [],
}

const ATALHOS = {
  tutor: [['/interesses', 'Meus interesses de adoção'], ['/meus-registros', 'Meus registros de perdidos e avistados']],
  abrigo: [['/painel', 'Meus animais'], ['/interessados', 'Interessados'], ['/meus-registros', 'Meus registros']],
  apoiador: [['/meus-registros', 'Meus registros']],
  admin: [['/admin', 'Validar abrigos']],
}

function valoresIniciais(usuario) {
  const v = { nome: usuario.nome }
  for (const [campo] of CAMPOS[usuario.tipo_conta]) v[campo] = usuario.perfil?.[campo] ?? ''
  if (usuario.tipo_conta === 'apoiador') v.tipo_estabelecimento = usuario.perfil?.tipo_estabelecimento ?? ''
  return v
}

export default function MinhaConta() {
  const { usuario, atualizarUsuario } = useAuth()
  const [dados, setDados] = useState(() => valoresIniciais(usuario))
  const [aviso, setAviso] = useState({ dados: null, senha: null })
  const [erros, setErros] = useState({})
  const [salvando, setSalvando] = useState(false)
  const [senhas, setSenhas] = useState({ senha_atual: '', senha_nova: '', confirmar: '' })

  const campos = CAMPOS[usuario.tipo_conta]
  const mudar = (campo) => (e) => setDados((d) => ({ ...d, [campo]: e.target.value }))

  async function salvarDados(e) {
    e.preventDefault()
    setErros({})
    setAviso((a) => ({ ...a, dados: null }))
    // Só envia o que mudou; campo opcional apagado vira null ("não informado").
    const iniciais = valoresIniciais(usuario)
    const corpo = {}
    for (const [campo, valor] of Object.entries(dados)) {
      if (valor !== iniciais[campo]) corpo[campo] = valor.trim() === '' ? null : valor.trim()
    }
    if (Object.keys(corpo).length === 0) return setAviso((a) => ({ ...a, dados: ['ok', 'Nada mudou.'] }))
    setSalvando(true)
    try {
      await api('/usuarios/eu', { metodo: 'PATCH', corpo })
      await atualizarUsuario()
      setAviso((a) => ({ ...a, dados: ['ok', 'Dados salvos.'] }))
    } catch (err) {
      setErros(err.campos || {})
      setAviso((a) => ({ ...a, dados: ['erro', err.message] }))
    } finally {
      setSalvando(false)
    }
  }

  async function trocarSenha(e) {
    e.preventDefault()
    setAviso((a) => ({ ...a, senha: null }))
    if (senhas.senha_nova !== senhas.confirmar) return setAviso((a) => ({ ...a, senha: ['erro', 'A confirmação não é igual à nova senha.'] }))
    try {
      await api('/usuarios/eu/senha', { metodo: 'POST', corpo: { senha_atual: senhas.senha_atual, senha_nova: senhas.senha_nova } })
      setSenhas({ senha_atual: '', senha_nova: '', confirmar: '' })
      setAviso((a) => ({ ...a, senha: ['ok', 'Senha alterada.'] }))
    } catch (err) {
      setAviso((a) => ({ ...a, senha: ['erro', err.message] }))
    }
  }

  const caixaAviso = (par) => par && (
    <div className={`aviso ${par[0] === 'ok' ? 'aviso--ok' : 'aviso--erro'}`} role={par[0] === 'ok' ? 'status' : 'alert'}>{par[1]}</div>
  )

  return (
    <main className="pagina pagina--media">
      <h1>Minha conta</h1>
      <p className="subtitulo">{ROTULO_TIPO[usuario.tipo_conta]} · {usuario.email} · conta criada em {new Date(usuario.criado_em).toLocaleDateString('pt-BR')}</p>

      {ATALHOS[usuario.tipo_conta].length > 0 && (
        <div className="acoes" style={{ marginBottom: '1.25rem' }}>
          {ATALHOS[usuario.tipo_conta].map(([para, rotulo]) => <Link key={para} className="botao botao--leve botao--pequeno" to={para}>{rotulo}</Link>)}
          <Link className="botao botao--leve botao--pequeno" to="/notificacoes">Notificações</Link>
        </div>
      )}

      <section className="cartao formulario" aria-labelledby="titulo-dados" style={{ marginBottom: '1.25rem' }}>
        <h2 id="titulo-dados">Seus dados</h2>
        {caixaAviso(aviso.dados)}
        <form className="formulario" onSubmit={salvarDados}>
          <div className="grade-campos">
            <div className="campo">
              <label htmlFor="nome">Nome</label>
              <input id="nome" value={dados.nome} onChange={mudar('nome')} required minLength={2} maxLength={150} aria-invalid={Boolean(erros.nome)} />
              {erros.nome && <span className="campo__erro">{erros.nome}</span>}
            </div>
            {campos.filter(([, , o]) => !o.textarea).map(([campo, rotulo, { textarea, ...opcoes }]) => (
              <div className="campo" key={campo}>
                <label htmlFor={campo}>{rotulo}</label>
                <input id={campo} value={dados[campo]} onChange={mudar(campo)} {...opcoes} aria-invalid={Boolean(erros[campo])} />
                {erros[campo] && <span className="campo__erro">{erros[campo]}</span>}
              </div>
            ))}
            {usuario.tipo_conta === 'apoiador' && (
              <div className="campo">
                <label htmlFor="tipo_estabelecimento">Tipo de estabelecimento</label>
                <select id="tipo_estabelecimento" value={dados.tipo_estabelecimento} onChange={mudar('tipo_estabelecimento')}>
                  {CATEGORIAS_EMPRESA.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </div>
            )}
          </div>
          {campos.filter(([, , o]) => o.textarea).map(([campo, rotulo, { maxLength }]) => (
            <div className="campo" key={campo}>
              <label htmlFor={campo}>{rotulo}</label>
              <textarea id={campo} value={dados[campo]} onChange={mudar(campo)} maxLength={maxLength} />
            </div>
          ))}
          <div><button className="botao" disabled={salvando}>{salvando ? 'Salvando…' : 'Salvar dados'}</button></div>
        </form>
      </section>

      <section className="cartao formulario" aria-labelledby="titulo-senha">
        <h2 id="titulo-senha">Trocar senha</h2>
        {caixaAviso(aviso.senha)}
        <form className="formulario" onSubmit={trocarSenha}>
          <div className="grade-campos">
            <div className="campo">
              <label htmlFor="senha_atual">Senha atual</label>
              <input id="senha_atual" type="password" autoComplete="current-password" required value={senhas.senha_atual} onChange={(e) => setSenhas((s) => ({ ...s, senha_atual: e.target.value }))} />
            </div>
            <div className="campo">
              <label htmlFor="senha_nova">Nova senha</label>
              <input id="senha_nova" type="password" autoComplete="new-password" required minLength={8} value={senhas.senha_nova} onChange={(e) => setSenhas((s) => ({ ...s, senha_nova: e.target.value }))} />
              <small>Pelo menos 8 caracteres.</small>
            </div>
            <div className="campo">
              <label htmlFor="confirmar">Confirmar nova senha</label>
              <input id="confirmar" type="password" autoComplete="new-password" required value={senhas.confirmar} onChange={(e) => setSenhas((s) => ({ ...s, confirmar: e.target.value }))} />
            </div>
          </div>
          <div><button className="botao">Trocar senha</button></div>
        </form>
      </section>
    </main>
  )
}
