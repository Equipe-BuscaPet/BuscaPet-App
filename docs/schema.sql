-- BuscaPet — Modelo Relacional (Sprint 2)
-- Postgres. Pode ser rodado direto no SQL Editor do Supabase, OU gerado via
-- Alembic (api/alembic/versions/0001_initial_schema.py) a partir dos models
-- em api/app/models/ — as duas fontes descrevem o mesmo schema.
--
-- Ordem de criação respeita as dependências de chave estrangeira.

-- ===================== Contas e perfis (RF-01 a RF-06) =====================

CREATE TABLE usuarios (
    id            SERIAL PRIMARY KEY,
    nome          VARCHAR(150) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    senha_hash    VARCHAR(255) NOT NULL,
    tipo_conta    VARCHAR(10)  NOT NULL CHECK (tipo_conta IN ('tutor','abrigo','apoiador','admin')),
    ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE tutores (
    usuario_id    INTEGER PRIMARY KEY REFERENCES usuarios(id),
    telefone      VARCHAR(20),
    cidade        VARCHAR(120)
);

CREATE TABLE abrigos (
    usuario_id                  INTEGER PRIMARY KEY REFERENCES usuarios(id),
    nome_abrigo                 VARCHAR(150) NOT NULL,
    endereco                    VARCHAR(255) NOT NULL,
    latitude                    DOUBLE PRECISION NOT NULL,
    longitude                   DOUBLE PRECISION NOT NULL,
    horario_funcionamento       VARCHAR(255),
    descricao                   VARCHAR(2000),
    telefone                    VARCHAR(20),
    chave_doacao_financeira     VARCHAR(140), -- só exibida; a plataforma não processa doação financeira (fora do escopo)
    documento_comprobatorio_url VARCHAR(500),
    status_validacao            VARCHAR(10) NOT NULL DEFAULT 'pendente' CHECK (status_validacao IN ('pendente','aprovado','rejeitado')),
    validado_por_id             INTEGER REFERENCES usuarios(id),
    validado_em                 TIMESTAMPTZ,
    criado_em                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE membros_equipe_abrigo (
    id          SERIAL PRIMARY KEY,
    abrigo_id   INTEGER NOT NULL REFERENCES abrigos(usuario_id),
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    papel       VARCHAR(20) NOT NULL CHECK (papel IN ('admin_abrigo','operador')),
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (abrigo_id, usuario_id)
);

CREATE TABLE apoiadores (
    usuario_id           INTEGER PRIMARY KEY REFERENCES usuarios(id),
    cnpj                 VARCHAR(18) NOT NULL UNIQUE,
    tipo_estabelecimento VARCHAR(20) NOT NULL CHECK (tipo_estabelecimento IN ('petshop','clinica','distribuidora','pessoa_fisica')),
    endereco             VARCHAR(255) NOT NULL,
    latitude             DOUBLE PRECISION,
    longitude            DOUBLE PRECISION,
    status_validacao     VARCHAR(10) NOT NULL DEFAULT 'aprovado' CHECK (status_validacao IN ('pendente','aprovado','rejeitado')),
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===================== Abrigos e animais (RF-12 a RF-18) =====================

CREATE TABLE animais (
    id                          SERIAL PRIMARY KEY,
    abrigo_id                   INTEGER NOT NULL REFERENCES abrigos(usuario_id),
    nome                        VARCHAR(120) NOT NULL,
    especie                     VARCHAR(10) NOT NULL CHECK (especie IN ('cao','gato','outro')),
    raca_aproximada             VARCHAR(120),
    porte                       VARCHAR(20) NOT NULL,
    idade_estimada_meses        INTEGER,
    sexo                        VARCHAR(12) NOT NULL CHECK (sexo IN ('macho','femea','indefinido')),
    castrado                    BOOLEAN NOT NULL DEFAULT FALSE,
    vacinado                    BOOLEAN NOT NULL DEFAULT FALSE,
    vermifugado                 BOOLEAN NOT NULL DEFAULT FALSE,
    temperamento                VARCHAR(500),
    convivencia_criancas        BOOLEAN,
    convivencia_outros_animais  BOOLEAN,
    historia_resgate            VARCHAR(2000),
    data_entrada                TIMESTAMPTZ,
    condicao_chegada            VARCHAR(500),
    status                      VARCHAR(15) NOT NULL DEFAULT 'disponivel' CHECK (status IN ('disponivel','em_processo','adotado','obito','transferido')),
    criado_em                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Associação polimórfica deliberada: entidade_tipo indica se a foto é de um
-- animal, de um animal_perdido ou de um avistamento. entidade_id NÃO tem FK
-- de banco (não é possível apontar uma FK para "uma dentre três tabelas");
-- a integridade é garantida na camada de aplicação. Ver nota em app/models/animal.py.
CREATE TABLE fotos (
    id            SERIAL PRIMARY KEY,
    entidade_tipo VARCHAR(20) NOT NULL CHECK (entidade_tipo IN ('animal','animal_perdido','avistamento')),
    entidade_id   INTEGER NOT NULL,
    url           VARCHAR(500) NOT NULL,
    ordem         INTEGER NOT NULL DEFAULT 0,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_fotos_entidade ON fotos (entidade_tipo, entidade_id);

CREATE TABLE interesses (
    id         SERIAL PRIMARY KEY,
    animal_id  INTEGER NOT NULL REFERENCES animais(id),
    tutor_id   INTEGER NOT NULL REFERENCES tutores(usuario_id),
    status     VARCHAR(15) NOT NULL DEFAULT 'aguardando' CHECK (status IN ('aguardando','em_conversa','aprovado','recusado')),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===================== Reencontro — núcleo computacional (RF-19 a RF-29) =====================

CREATE TABLE animais_perdidos (
    id                     SERIAL PRIMARY KEY,
    tutor_id               INTEGER NOT NULL REFERENCES tutores(usuario_id),
    especie                VARCHAR(10) NOT NULL CHECK (especie IN ('cao','gato','outro')),
    porte                  VARCHAR(20) NOT NULL,
    cor_predominante       VARCHAR(60) NOT NULL,
    pelagem                VARCHAR(60),
    sexo                   VARCHAR(12) NOT NULL CHECK (sexo IN ('macho','femea','indefinido')),
    sinais_particulares    VARCHAR(500),
    latitude               DOUBLE PRECISION NOT NULL, -- área aproximada, nunca o endereço exato (escopo, seção 9)
    longitude              DOUBLE PRECISION NOT NULL,
    raio_busca_km          DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    data_desaparecimento   TIMESTAMPTZ NOT NULL,
    resolvido              BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE avistamentos (
    id                   SERIAL PRIMARY KEY,
    usuario_id           INTEGER NOT NULL REFERENCES usuarios(id),
    especie              VARCHAR(10) NOT NULL CHECK (especie IN ('cao','gato','outro')),
    porte                VARCHAR(20) NOT NULL,
    cor_predominante     VARCHAR(60) NOT NULL,
    pelagem              VARCHAR(60),
    sexo                 VARCHAR(12) NOT NULL CHECK (sexo IN ('macho','femea','indefinido')),
    sinais_particulares  VARCHAR(500),
    latitude             DOUBLE PRECISION NOT NULL,
    longitude            DOUBLE PRECISION NOT NULL,
    data_avistamento     TIMESTAMPTZ NOT NULL,
    criado_em            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE descritores_visuais (
    id                SERIAL PRIMARY KEY,
    foto_id           INTEGER NOT NULL UNIQUE REFERENCES fotos(id),
    histograma_cor    TEXT NOT NULL, -- JSON serializado, calculado pelo núcleo OpenCL (Sprint 3)
    textura           TEXT NOT NULL,
    proporcoes        TEXT NOT NULL,
    versao_algoritmo  VARCHAR(20) NOT NULL DEFAULT 'v1',
    calculado_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE buscas_salvas (
    id                 SERIAL PRIMARY KEY,
    tutor_id           INTEGER NOT NULL REFERENCES tutores(usuario_id),
    animal_perdido_id  INTEGER NOT NULL REFERENCES animais_perdidos(id),
    status             VARCHAR(15) NOT NULL DEFAULT 'monitorando' CHECK (status IN ('monitorando','resolvida')),
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolvida_em       TIMESTAMPTZ
);

-- Log de todo match relevante — alimenta a grade de candidatos (RF-23), o
-- alerta ao abrigo (RF-26) e a notificação de monitoramento (RF-24, RF-25).
CREATE TABLE correspondencias (
    id                 SERIAL PRIMARY KEY,
    tipo               VARCHAR(20) NOT NULL CHECK (tipo IN ('busca_tutor','alerta_abrigo','busca_inversa')),
    animal_perdido_id  INTEGER REFERENCES animais_perdidos(id),
    animal_id          INTEGER REFERENCES animais(id),
    avistamento_id     INTEGER REFERENCES avistamentos(id),
    score              DOUBLE PRECISION NOT NULL,
    grau_semelhanca    VARCHAR(6) NOT NULL CHECK (grau_semelhanca IN ('alta','media','baixa')),
    notificado         BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===================== Doações e reconhecimento (RF-30 a RF-35) =====================

CREATE TABLE necessidades (
    id         SERIAL PRIMARY KEY,
    abrigo_id  INTEGER NOT NULL REFERENCES abrigos(usuario_id),
    item       VARCHAR(200) NOT NULL,
    quantidade INTEGER NOT NULL,
    urgencia   VARCHAR(6) NOT NULL CHECK (urgencia IN ('baixa','media','alta')),
    status     VARCHAR(10) NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta','atendida')),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE doacoes (
    id              SERIAL PRIMARY KEY,
    apoiador_id     INTEGER NOT NULL REFERENCES apoiadores(usuario_id),
    abrigo_id       INTEGER NOT NULL REFERENCES abrigos(usuario_id),
    necessidade_id  INTEGER REFERENCES necessidades(id),
    item            VARCHAR(200) NOT NULL,
    quantidade      INTEGER NOT NULL,
    status          VARCHAR(25) NOT NULL DEFAULT 'aguardando_confirmacao' CHECK (status IN ('aguardando_confirmacao','confirmada','recusada')),
    registrado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmado_em   TIMESTAMPTZ
);

-- Cache mensal da pontuação (RF-33): permite "destaque do mês" (uma linha) e
-- "acumulado do ano" (soma das linhas do ano) sem reprocessar o histórico de doações.
CREATE TABLE pontuacoes_apoiador (
    id                   SERIAL PRIMARY KEY,
    apoiador_id          INTEGER NOT NULL REFERENCES apoiadores(usuario_id),
    mes_referencia        TIMESTAMPTZ NOT NULL, -- sempre dia 1 do mês
    pontos_volume        DOUBLE PRECISION NOT NULL DEFAULT 0,
    pontos_regularidade  DOUBLE PRECISION NOT NULL DEFAULT 0,
    pontos_total         DOUBLE PRECISION NOT NULL DEFAULT 0,
    atualizado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (apoiador_id, mes_referencia)
);

-- ===================== Transversais (RF-36 a RF-41) =====================

CREATE TABLE notificacoes (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    mensagem        VARCHAR(500) NOT NULL,
    referencia_tipo VARCHAR(30),
    referencia_id   INTEGER,
    lida            BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE denuncias (
    id               SERIAL PRIMARY KEY,
    denunciante_id   INTEGER NOT NULL REFERENCES usuarios(id),
    animal_id        INTEGER NOT NULL REFERENCES animais(id),
    motivo           VARCHAR(1000) NOT NULL,
    status           VARCHAR(10) NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','removido','advertido','banido','ignorado')),
    resolvido_por_id INTEGER REFERENCES usuarios(id),
    resolvido_em     TIMESTAMPTZ,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE logs_auditoria (
    id            SERIAL PRIMARY KEY,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    acao          VARCHAR(100) NOT NULL,
    entidade_tipo VARCHAR(50) NOT NULL,
    entidade_id   INTEGER NOT NULL,
    detalhes_json TEXT,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
);
