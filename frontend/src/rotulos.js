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

export const STATUS_INTERESSE = {
  aguardando: 'Aguardando resposta',
  em_conversa: 'Em conversa',
  aprovado: 'Aprovado',
  recusado: 'Não seguiu',
}

// Nomes dos campos como a pessoa os conhece, para as mensagens de erro.
export const ROTULO_CAMPO = {
  nome: 'Nome', email: 'E-mail', senha: 'Senha', telefone: 'Telefone', cidade: 'Cidade',
  nome_abrigo: 'Nome do abrigo', endereco: 'Endereço', latitude: 'Latitude', longitude: 'Longitude',
  horario_funcionamento: 'Horário', descricao: 'Sobre o abrigo', cnpj: 'CNPJ',
  tipo_estabelecimento: 'Tipo de estabelecimento', especie: 'Espécie', raca_aproximada: 'Raça',
  porte: 'Porte', sexo: 'Sexo', idade_estimada_meses: 'Idade (meses)', temperamento: 'Temperamento',
  historia_resgate: 'História do resgate', data_entrada: 'Data de entrada', condicao_chegada: 'Condição de chegada',
  status: 'Situação', mensagem: 'Mensagem', senha_nova: 'Nova senha', senha_atual: 'Senha atual',
}

// Link do WhatsApp a partir de um telefone brasileiro (só dígitos; acrescenta o 55 se faltar).
export function linkWhatsApp(telefone) {
  const digitos = String(telefone || '').replace(/\D/g, '')
  if (digitos.length < 10) return null
  return `https://wa.me/${digitos.startsWith('55') && digitos.length >= 12 ? digitos : `55${digitos}`}`
}

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
