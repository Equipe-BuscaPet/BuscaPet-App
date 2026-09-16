# 2. Diagrama de classes

Modelo de domínio do backend. `Usuario` concentra autenticação; os três
perfis de conta (`Tutor`, `Abrigo`, `Apoiador`) e o `Administrador` herdam
dele — no banco isso é implementado como tabelas separadas em relação 1:1
(table-per-type, ver seção 4), não como herança física, mas no código de
domínio a herança é a forma natural de expressar "todo perfil é um usuário".

```mermaid
classDiagram
    class Usuario {
        +int id
        +string nome
        +string email
        +string senhaHash
        +TipoConta tipoConta
        +bool ativo
        +autenticar(senha) bool
        +gerarToken() string
    }

    class Tutor {
        +string telefone
        +string cidade
        +registrarAnimalPerdido(dados) AnimalPerdido
        +registrarAvistamento(dados) Avistamento
    }

    class Abrigo {
        +string nomeAbrigo
        +string endereco
        +StatusValidacao statusValidacao
        +string chaveDoacaoFinanceira
        +cadastrarAnimal(dados) Animal
        +publicarNecessidade(dados) Necessidade
        +confirmarDoacao(doacao)
    }

    class Apoiador {
        +string cnpj
        +TipoEstabelecimento tipoEstabelecimento
        +registrarDoacao(necessidade, quantidade) Doacao
    }

    class Administrador {
        +validarAbrigo(abrigo, aprovado, motivo)
        +moderarDenuncia(denuncia, acao)
    }

    Usuario <|-- Tutor
    Usuario <|-- Abrigo
    Usuario <|-- Apoiador
    Usuario <|-- Administrador

    class MembroEquipeAbrigo {
        +PapelEquipeAbrigo papel
    }
    Abrigo "1" o-- "*" MembroEquipeAbrigo
    Usuario "1" o-- "*" MembroEquipeAbrigo

    class Animal {
        +string nome
        +Especie especie
        +string porte
        +Sexo sexo
        +bool castrado
        +bool vacinado
        +StatusAnimal status
        +moverStatus(novoStatus)
    }
    Abrigo "1" *-- "*" Animal

    class Foto {
        +string url
        +int ordem
    }
    Animal "1" *-- "*" Foto
    AnimalPerdido "1" *-- "*" Foto
    Avistamento "1" *-- "*" Foto

    class DescritorVisual {
        +json histogramaCor
        +json textura
        +json proporcoes
        +string versaoAlgoritmo
    }
    Foto "1" -- "0..1" DescritorVisual

    class Interesse {
        +StatusInteresse status
        +registrarContatoWhatsApp()
    }
    Tutor "1" o-- "*" Interesse
    Animal "1" o-- "*" Interesse

    class AnimalPerdido {
        +string corPredominante
        +Sexo sexo
        +float latitude
        +float longitude
        +float raioBuscaKm
        +bool resolvido
        +marcarResolvido()
    }
    Tutor "1" o-- "*" AnimalPerdido

    class Avistamento {
        +string corPredominante
        +float latitude
        +float longitude
    }

    class BuscaSalva {
        +StatusBusca status
        +monitorar()
        +resolver()
    }
    Tutor "1" o-- "*" BuscaSalva
    AnimalPerdido "1" o-- "*" BuscaSalva

    class Correspondencia {
        +TipoCorrespondencia tipo
        +float score
        +GrauSemelhanca grauSemelhanca
        +bool notificado
    }
    Correspondencia --> AnimalPerdido
    Correspondencia --> Animal
    Correspondencia --> Avistamento

    class NucleoComparacaoClient {
        +compararFoto(foto, candidatos) Correspondencia[]
        +extrairDescritor(foto) DescritorVisual
    }
    class MonitoramentoWorker {
        +processarLote(novoRegistro)
    }
    MonitoramentoWorker ..> NucleoComparacaoClient : usa
    NucleoComparacaoClient ..> Correspondencia : cria

    class Necessidade {
        +string item
        +int quantidade
        +UrgenciaNecessidade urgencia
        +StatusNecessidade status
    }
    Abrigo "1" o-- "*" Necessidade

    class Doacao {
        +string item
        +int quantidade
        +StatusDoacao status
        +confirmar()
    }
    Apoiador "1" o-- "*" Doacao
    Abrigo "1" o-- "*" Doacao
    Necessidade "1" o-- "*" Doacao

    class PontuacaoApoiador {
        +date mesReferencia
        +float pontosVolume
        +float pontosRegularidade
        +float pontosTotal
    }
    Apoiador "1" o-- "*" PontuacaoApoiador

    class Notificacao {
        +string mensagem
        +bool lida
    }
    Usuario "1" o-- "*" Notificacao

    class Denuncia {
        +string motivo
        +StatusDenuncia status
    }
    Usuario "1" o-- "*" Denuncia : denunciante
    Animal "1" o-- "*" Denuncia

    class LogAuditoria {
        +string acao
        +string entidadeTipo
        +int entidadeId
    }
    Usuario "1" o-- "*" LogAuditoria
```

![Diagrama de classes do BuscaPet](imagens/02-diagrama-classes.png)

_Imagem gerada a partir do bloco Mermaid acima — usar esta versão ao colar no Word/Google Docs, que não renderizam Mermaid nativamente._

## Notas sobre decisões de modelagem

- **`NucleoComparacaoClient` e `MonitoramentoWorker`** são classes de serviço do backend Python — não do núcleo em C. Elas encapsulam a chamada HTTP (`httpx`) ao serviço `nucleo-opencl`, mantendo o resto do domínio (Tutor, Abrigo etc.) sem nenhuma dependência direta de como o núcleo é implementado. Se o núcleo mudar de linguagem no futuro, só essas duas classes precisam mudar.
- **`Foto` é compartilhada por três donos possíveis** (`Animal`, `AnimalPerdido`, `Avistamento`) via associação polimórfica — o mesmo trade-off explicado na seção 3 (MER) e na seção 4 (modelo relacional): sem FK real de banco para `entidade_id`, a integridade é garantida no código de domínio.
- **`Correspondencia` é o registro central do reencontro**: toda vez que o núcleo encontra um match relevante — seja numa busca ativa do tutor, num alerta ao abrigo ou numa busca inversa — uma linha nasce aqui. Isso evita duplicar a lógica de "o que é um match" em três lugares diferentes do código.
