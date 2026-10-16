import { useCallback, useRef } from 'react'

// Evita a "condição de corrida" nas buscas: se a pessoa troca de aba ou de filtro antes da resposta chegar,
// um pedido antigo e mais lento pode voltar DEPOIS do novo e sobrescrever a lista certa.
// Uso:  const atual = novoPedido()  →  depois do await: if (!atual()) return  (resposta velha, ignora).
export function useUltimoPedido() {
  const contador = useRef(0)
  return useCallback(() => {
    const numero = ++contador.current
    return () => numero === contador.current
  }, [])
}
