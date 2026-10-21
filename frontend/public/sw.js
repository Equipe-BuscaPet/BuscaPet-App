// Service worker do BuscaPet: permite instalar o site como app e abrir a "casca" da interface mesmo com
// internet ruim. Só cuida de arquivos do próprio site; a API e o mapa (outros endereços) passam direto.
// Registrado apenas na versão de produção (src/main.jsx), para não atrapalhar o desenvolvimento.
const VERSAO = 'buscapet-v1'
const CASCA = ['/', '/manifest.webmanifest', '/icones/icone-192.png', '/favicon.png']

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(VERSAO).then((cache) => cache.addAll(CASCA)))
  self.skipWaiting()
})

// Apaga caches de versões antigas.
self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request
  const url = new URL(pedido.url)
  if (pedido.method !== 'GET' || url.origin !== self.location.origin) return

  // Páginas: tenta a rede (conteúdo sempre atual); sem internet, abre a casca guardada.
  if (pedido.mode === 'navigate') {
    evento.respondWith(fetch(pedido).catch(() => caches.match('/')))
    return
  }

  // Arquivos com hash no nome (/assets/...) e ícones nunca mudam: usa o guardado e só baixa o que falta.
  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icones/')) {
    evento.respondWith(
      caches.match(pedido).then((guardado) => guardado || fetch(pedido).then((resposta) => {
        if (resposta.ok) {
          const copia = resposta.clone()
          caches.open(VERSAO).then((cache) => cache.put(pedido, copia))
        }
        return resposta
      })),
    )
  }
})
