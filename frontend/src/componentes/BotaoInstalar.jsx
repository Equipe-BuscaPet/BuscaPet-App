import { useEffect, useState } from 'react'

// "Instalar app": adiciona o BuscaPet à tela inicial (PWA).
// - Android/Chrome/Edge: o navegador avisa que dá para instalar (evento beforeinstallprompt) e o botão abre o pedido.
// - iPhone/iPad: o Safari não tem esse evento; o botão mostra o passo a passo (Compartilhar → Adicionar à Tela de Início).
// Já instalado (aberto como app), o botão não aparece.
const jaInstalado = () =>
  window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
const ehIOS = () => /iphone|ipad|ipod/i.test(window.navigator.userAgent)

export default function BotaoInstalar() {
  // O aviso do navegador costuma chegar antes do React montar: main.jsx o guarda em window.__buscapetInstalar.
  const [pedido, setPedido] = useState(() => window.__buscapetInstalar || null)
  const [dicaIOS, setDicaIOS] = useState(false)
  const [instalado, setInstalado] = useState(jaInstalado)

  useEffect(() => {
    const aoPoderInstalar = () => setPedido(window.__buscapetInstalar)
    const aoInstalar = () => { setInstalado(true); setPedido(null) }
    window.addEventListener('buscapet:pode-instalar', aoPoderInstalar)
    window.addEventListener('appinstalled', aoInstalar)
    return () => {
      window.removeEventListener('buscapet:pode-instalar', aoPoderInstalar)
      window.removeEventListener('appinstalled', aoInstalar)
    }
  }, [])

  if (instalado || (!pedido && !ehIOS())) return null

  async function instalar() {
    if (pedido) {
      pedido.prompt()
      const { outcome } = await pedido.userChoice
      if (outcome === 'accepted') setInstalado(true)
      window.__buscapetInstalar = null // o mesmo aviso só pode ser usado uma vez
      setPedido(null)
    } else {
      setDicaIOS((v) => !v)
    }
  }

  return (
    <div className="instalar">
      <button type="button" className="botao" onClick={instalar} aria-expanded={pedido ? undefined : dicaIOS}>
        <span aria-hidden="true">📲</span> Instalar app
      </button>
      {dicaIOS && (
        <div className="instalar__dica" role="dialog" aria-label="Como instalar no iPhone">
          No Safari, toque em <strong>Compartilhar</strong> <span aria-hidden="true">(□↑)</span> e depois em{' '}
          <strong>Adicionar à Tela de Início</strong>.
          <button type="button" className="botao botao--leve botao--pequeno" onClick={() => setDicaIOS(false)}>Entendi</button>
        </div>
      )}
    </div>
  )
}
