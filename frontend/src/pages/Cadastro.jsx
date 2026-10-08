import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { destinoPorTipo, useAuth } from '../auth'
import { limpar, TIPOS_ESTABELECIMENTO } from '../rotulos'

const TIPOS = [
  { valor: 'tutor', titulo: 'Tutor', texto: 'Quero adotar ou encontrar meu animal' },
  { valor: 'abrigo', titulo: 'Abrigo / protetor', texto: 'Tenho animais para a adoção' },
  { valor: 'apoiador', titulo: 'Apoiador', texto: 'Petshop, clínica ou distribuidora' },
]

const VAZIO = {
  nome: '', email: '', senha: '', telefone: '', cidade: '',
  nome_abrigo: '', endereco: '', latitude: '', longitude: '', horario_funcionamento: '', descricao: '',
  cnpj: '', tipo_estabelecimento: 'petshop',
}

export default function Cadastro() {
  const { entrar } = useAuth()
  const navegar = useNavigate()
  const [tipo, setTipo] = useState('tutor')
  const [f, setF] = useState(VAZIO)
  const [erro, setErro] = useState('')
  const [camposComErro, setCamposComErro] = useState({})
  const [aviso, setAviso] = useState('')
  const [enviando, setEnviando] = useState(false)

  const campo = (nome) => ({
    id: nome, value: f[nome], onChange: (e) => setF({ ...f, [nome]: e.target.value }),
    'aria-invalid': camposComErro[nome] ? 'true' : undefined,
    title: camposComErro[nome],
  })

  function usarMinhaLocalizacao() {
    setAviso('')
    if (!navigator.geolocation) return setAviso('Seu navegador não oferece geolocalização; digite as coordenadas.')
    navigator.geolocation.getCurrentPosition(
      (p) => setF((atual) => ({ ...atual, latitude: p.coords.latitude.toFixed(6), longitude: p.coords.longitude.toFixed(6) })),
      () => setAviso('Não foi possível obter a localização; digite as coordenadas.'),
    )
  }

  function montarCorpo() {
    const base = { tipo_conta: tipo, nome: f.nome, email: f.email, senha: f.senha }
    if (tipo === 'tutor') return limpar({ ...base, telefone: f.telefone, cidade: f.cidade })
    if (tipo === 'abrigo') {
      return limpar({
        ...base,
        nome_abrigo: f.nome_abrigo, endereco: f.endereco, telefone: f.telefone,
        latitude: f.latitude === '' ? '' : Number(f.latitude),
        longitude: f.longitude === '' ? '' : Number(f.longitude),
        horario_funcionamento: f.horario_funcionamento, descricao: f.descricao,
      })
    }
    return limpar({ ...base, cnpj: f.cnpj, tipo_estabelecimento: f.tipo_estabelecimento, endereco: f.endereco })
  }

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setCamposComErro({})
    setEnviando(true)
    try {
      await api('/auth/cadastro', { metodo: 'POST', corpo: montarCorpo() })
      const usuario = await entrar(f.email, f.senha)
      navegar(destinoPorTipo(usuario.tipo_conta))
    } catch (err) {
      setErro(err.message)
      setCamposComErro(err.campos || {})
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="pagina pagina--estreita">
      <div className="cartao">
        <h1>Criar conta</h1>
        <p className="subtitulo">Escolha o tipo de conta. Ele não muda depois.</p>
        {erro && <div className="aviso aviso--erro" role="alert">{erro}</div>}
        <form className="formulario" onSubmit={enviar}>
          <fieldset className="campo">
            <legend>Tipo de conta</legend>
            <div className="opcoes-tipo">
              {TIPOS.map((t) => (
                <label key={t.valor} className="opcao-tipo">
                  <input type="radio" name="tipo" value={t.valor} checked={tipo === t.valor} onChange={() => setTipo(t.valor)} />
                  <strong>{t.titulo}</strong>
                  <span>{t.texto}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="campo">
            <label htmlFor="nome">Seu nome</label>
            <input {...campo('nome')} required minLength={2} maxLength={150} autoComplete="name" />
          </div>
          <div className="grade-campos">
            <div className="campo">
              <label htmlFor="email">E-mail</label>
              <input {...campo('email')} type="email" required autoComplete="email" />
            </div>
            <div className="campo">
              <label htmlFor="senha">Senha</label>
              <input {...campo('senha')} type="password" required minLength={8} autoComplete="new-password" />
              <small>Mínimo de 8 caracteres.</small>
            </div>
          </div>

          {tipo === 'tutor' && (
            <div className="grade-campos">
              <div className="campo"><label htmlFor="telefone">Telefone (opcional)</label><input {...campo('telefone')} maxLength={20} inputMode="tel" /></div>
              <div className="campo"><label htmlFor="cidade">Cidade (opcional)</label><input {...campo('cidade')} maxLength={120} /></div>
            </div>
          )}

          {tipo === 'abrigo' && (
            <>
              <div className="aviso aviso--atencao">
                Todo abrigo passa por validação do administrador antes de publicar animais.
              </div>
              <div className="campo"><label htmlFor="nome_abrigo">Nome do abrigo</label><input {...campo('nome_abrigo')} required maxLength={150} /></div>
              <div className="campo"><label htmlFor="endereco">Endereço</label><input {...campo('endereco')} required maxLength={255} autoComplete="street-address" /></div>
              <div className="grade-campos">
                <div className="campo"><label htmlFor="latitude">Latitude</label><input {...campo('latitude')} type="number" step="any" min="-90" max="90" required /></div>
                <div className="campo"><label htmlFor="longitude">Longitude</label><input {...campo('longitude')} type="number" step="any" min="-180" max="180" required /></div>
              </div>
              <div className="acoes">
                <button type="button" className="botao botao--leve botao--pequeno" onClick={usarMinhaLocalizacao}>Usar minha localização</button>
                {aviso && <small role="status">{aviso}</small>}
              </div>
              <div className="grade-campos">
                <div className="campo"><label htmlFor="telefone">Telefone (opcional)</label><input {...campo('telefone')} maxLength={20} inputMode="tel" /></div>
                <div className="campo"><label htmlFor="horario_funcionamento">Horário (opcional)</label><input {...campo('horario_funcionamento')} maxLength={255} /></div>
              </div>
              <div className="campo"><label htmlFor="descricao">Sobre o abrigo (opcional)</label><textarea {...campo('descricao')} maxLength={2000} /></div>
            </>
          )}

          {tipo === 'apoiador' && (
            <>
              <div className="grade-campos">
                <div className="campo"><label htmlFor="cnpj">CNPJ</label><input {...campo('cnpj')} required inputMode="numeric" placeholder="00.000.000/0000-00" /></div>
                <div className="campo">
                  <label htmlFor="tipo_estabelecimento">Tipo de estabelecimento</label>
                  <select {...campo('tipo_estabelecimento')}>
                    {Object.entries(TIPOS_ESTABELECIMENTO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                  </select>
                </div>
              </div>
              <div className="campo"><label htmlFor="endereco">Endereço</label><input {...campo('endereco')} required maxLength={255} /></div>
            </>
          )}

          <button className="botao" disabled={enviando}>{enviando ? 'Criando conta…' : 'Criar conta'}</button>
        </form>
        <p className="subtitulo" style={{ marginTop: '1rem', marginBottom: 0 }}>
          Já tem conta? <Link to="/login">Entrar</Link>
        </p>
      </div>
    </main>
  )
}
