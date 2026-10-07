import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, token } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [carregando, setCarregando] = useState(Boolean(token.ler()))

  const sair = useCallback(() => {
    token.apagar()
    setUsuario(null)
  }, [])

  // Ao abrir o site com um token guardado, confirma com o servidor quem é o usuário.
  useEffect(() => {
    if (!token.ler()) return
    api('/auth/eu')
      .then(setUsuario)
      .catch(() => token.apagar())
      .finally(() => setCarregando(false))
  }, [])

  // O token expirou ou a conta foi desativada: volta ao estado de visitante.
  useEffect(() => {
    window.addEventListener('buscapet:sessao-expirada', sair)
    return () => window.removeEventListener('buscapet:sessao-expirada', sair)
  }, [sair])

  const entrar = useCallback(async (email, senha) => {
    const resposta = await api('/auth/login', { metodo: 'POST', formulario: { username: email, password: senha } })
    token.salvar(resposta.access_token)
    setUsuario(resposta.usuario)
    return resposta.usuario
  }, [])

  const atualizarUsuario = useCallback(() => api('/auth/eu').then(setUsuario), [])

  return (
    <AuthContext.Provider value={{ usuario, carregando, entrar, sair, atualizarUsuario }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

// Página inicial de cada perfil depois do login.
export function destinoPorTipo(tipo) {
  if (tipo === 'admin') return '/admin'
  if (tipo === 'abrigo') return '/painel'
  return '/'
}
