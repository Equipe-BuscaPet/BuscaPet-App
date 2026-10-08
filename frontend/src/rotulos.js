// Textos em português para os valores (enums) que a API usa.
export const ESPECIES = { cao: 'Cachorro', gato: 'Gato', outro: 'Outro' }
export const PORTES = { pequeno: 'Pequeno', medio: 'Médio', grande: 'Grande' }
export const SEXOS = { macho: 'Macho', femea: 'Fêmea', indefinido: 'Indefinido' }
export const STATUS_ANIMAL = {
  disponivel: 'Disponível',
  em_processo: 'Em processo de adoção',
  adotado: 'Adotado',
  obito: 'Óbito',
  transferido: 'Transferido',
}
export const TIPOS_ESTABELECIMENTO = {
  petshop: 'Petshop',
  clinica: 'Clínica veterinária',
  distribuidora: 'Distribuidora',
  pessoa_fisica: 'Pessoa física',
}
export const STATUS_VALIDACAO = { pendente: 'Não verificado', aprovado: 'Verificado', rejeitado: 'Suspenso' }

export const EMOJI_ESPECIE = { cao: '🐶', gato: '🐱', outro: '🐾' }

export function textoIdade(meses) {
  if (meses === null || meses === undefined) return 'Idade não informada'
  if (meses < 12) return `${meses} ${meses === 1 ? 'mês' : 'meses'}`
  const anos = Math.floor(meses / 12)
  const resto = meses % 12
  const a = `${anos} ${anos === 1 ? 'ano' : 'anos'}`
  return resto ? `${a} e ${resto} ${resto === 1 ? 'mês' : 'meses'}` : a
}

// Remove campos vazios antes de enviar: a API trata "não enviado" e "" de forma diferente.
export function limpar(objeto) {
  return Object.fromEntries(Object.entries(objeto).filter(([, v]) => v !== '' && v !== undefined && v !== null))
}
