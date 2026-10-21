import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth'
import './styles.css'

// PWA (instalar na tela inicial). O navegador avisa cedo que o app pode ser instalado; guardamos o aviso
// para o botão "Instalar app" usar quando a pessoa quiser (componentes/BotaoInstalar.jsx).
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  window.__buscapetInstalar = e
  window.dispatchEvent(new Event('buscapet:pode-instalar'))
})
// O service worker só entra na versão de produção: no desenvolvimento ele guardaria arquivos velhos.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'))
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
