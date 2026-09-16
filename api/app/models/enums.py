"""Enums usados pelos models. Mantidos num único arquivo para facilitar consulta
cruzada com o MER e o modelo relacional (docs/schema.sql)."""
import enum


class TipoConta(str, enum.Enum):
    TUTOR = "tutor"
    ABRIGO = "abrigo"
    APOIADOR = "apoiador"
    ADMIN = "admin"


class StatusValidacao(str, enum.Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"


class PapelEquipeAbrigo(str, enum.Enum):
    ADMIN_ABRIGO = "admin_abrigo"
    OPERADOR = "operador"


class Especie(str, enum.Enum):
    CAO = "cao"
    GATO = "gato"
    OUTRO = "outro"


class Sexo(str, enum.Enum):
    MACHO = "macho"
    FEMEA = "femea"
    INDEFINIDO = "indefinido"


class StatusAnimal(str, enum.Enum):
    DISPONIVEL = "disponivel"
    EM_PROCESSO = "em_processo"
    ADOTADO = "adotado"
    OBITO = "obito"
    TRANSFERIDO = "transferido"


class EntidadeFoto(str, enum.Enum):
    """Entidade dona da foto — usado pela associação polimórfica em Foto."""
    ANIMAL = "animal"
    ANIMAL_PERDIDO = "animal_perdido"
    AVISTAMENTO = "avistamento"


class StatusInteresse(str, enum.Enum):
    AGUARDANDO = "aguardando"
    EM_CONVERSA = "em_conversa"
    APROVADO = "aprovado"
    RECUSADO = "recusado"


class StatusBusca(str, enum.Enum):
    MONITORANDO = "monitorando"
    RESOLVIDA = "resolvida"


class GrauSemelhanca(str, enum.Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class TipoCorrespondencia(str, enum.Enum):
    """De onde veio o match: busca de quem perdeu, alerta ao abrigo, ou busca
    inversa de quem encontrou (seção 4 do escopo — mesmo motor, três gatilhos)."""
    BUSCA_TUTOR = "busca_tutor"
    ALERTA_ABRIGO = "alerta_abrigo"
    BUSCA_INVERSA = "busca_inversa"


class UrgenciaNecessidade(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class StatusNecessidade(str, enum.Enum):
    ABERTA = "aberta"
    ATENDIDA = "atendida"


class TipoEstabelecimento(str, enum.Enum):
    PETSHOP = "petshop"
    CLINICA = "clinica"
    DISTRIBUIDORA = "distribuidora"
    PESSOA_FISICA = "pessoa_fisica"


class StatusDoacao(str, enum.Enum):
    AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
    CONFIRMADA = "confirmada"
    RECUSADA = "recusada"


class StatusDenuncia(str, enum.Enum):
    PENDENTE = "pendente"
    REMOVIDO = "removido"
    ADVERTIDO = "advertido"
    BANIDO = "banido"
    IGNORADO = "ignorado"
