# Arquitetura do Banco de Dados - Projeto qCyber (Versão Final)

Este documento descreve a estrutura final e normalizada do banco de dados `qcyber_db`, projetado para ser robusto, escalável e de fácil manutenção.

## Visão Geral e Diagrama de Relacionamento

A arquitetura é dividida em três tipos de tabelas:
1.  **Tabelas de Lookup (Enum):** Armazenam os "tipos" de dados (status, riscos, etc.). Servem para garantir consistência e facilitar a manutenção.
2.  **Tabelas Fato (Principais):** Armazenam os eventos e registros principais do sistema, como detecções e incidentes.
3.  **Tabelas de Suporte:** Incluem gerenciamento de usuários e tabelas legadas.


````
+---------------------------+
|  enum_tipo_ataque         |
+---------------------------+
       ^
       | (tipo_ataque_id)
+---------------------------+       +---------------------------+
|  deteccoes                |------>|  incidentes_analisados    |
+---------------------------+       +---------------------------+
       ^      ^      ^                      ^
       |      |      | (dispositivo_id)     | (dispositivo_id)
       |      |      +----------------------+
       |      | (acao_executada_id)          |
       |      +---------------------------+  |
       | (status_resposta_id)            |  |
       |                                 |  |
+---------------------------+       +---------------------------+
|  enum_status_resposta     |       |  enum_acao_executada      |
+---------------------------+       +---------------------------+
                                             ^
                                             |
+---------------------------+       +---------------------------+
|  dispositivos             |<------|  enum_status_dispositivo  |
+---------------------------+       +---------------------------+
````


## 1. Tabelas de Lookup (Enum)

Estas tabelas substituem o uso de `ENUM`s diretamente nas tabelas principais, permitindo maior flexibilidade e a adição de metadados (como descrições).

| Tabela                      | Propósito                                                                  | Colunas Principais      |
| :-------------------------- | :------------------------------------------------------------------------- | :---------------------- |
| **`enum_tipo_ataque`** | Mapeia os códigos numéricos de ataques (0-13, 99) para nomes legíveis.      | `id`, `nome`, `descricao` |
| **`enum_status_resposta`** | Define os possíveis status de uma detecção (Pendente, Ignorado, etc.).      | `id`, `nome`, `descricao` |
| **`enum_status_incidente`** | Define os status de um incidente formal (Aberto, Resolvido, etc.).         | `id`, `nome`, `descricao` |
| **`enum_nivel_risco`** | Define os níveis de risco (Baixo, Médio, Alto, Crítico).                   | `id`, `nome`, `descricao` |
| **`enum_status_dispositivo`**| Define os status de um dispositivo (Ativo, Inativo, etc.).                | `id`, `nome`, `descricao` |
| **`enum_acao_executada`** | Cataloga as ações automáticas que o sistema pode tomar (BLOCK_IP, etc.).   | `id`, `nome`, `descricao` |

---

## 2. Tabelas Fato (Principais)

Estas são as tabelas centrais que armazenam os dados operacionais do sistema.

### `deteccoes` (Anteriormente `deteccoes_individuais`)

É a tabela mais importante. Cada linha representa uma única detecção feita pelo modelo de análise.

| Coluna                | Tipo          | Descrição                                                                                     |
| :-------------------- | :------------ | :-------------------------------------------------------------------------------------------- |
| `id`                  | INT           | Identificador único da detecção.                                                              |
| `data_deteccao`       | TIMESTAMP     | Data e hora exatas em que a detecção foi registrada.                                          |
| `dispositivo_id`      | INT (FK)      | **[Link para `dispositivos`]** Qual dispositivo foi analisado.                                 |
| `predicao`            | INT           | O código numérico bruto (0-13, 99) retornado pelo modelo.                                     |
| `tipo_ataque_id`      | INT (FK)      | **[Link para `enum_tipo_ataque`]** O tipo de ataque correspondente à `predicao`.               |
| `relatorio_api`       | TEXT          | O texto descritivo retornado pelo modelo de análise.                                          |
| `status_resposta_id`  | INT (FK)      | **[Link para `enum_status_resposta`]** O estado atual da detecção no fluxo de trabalho.        |
| `acao_executada_id`   | INT (FK)      | **[Link para `enum_acao_executada`]** (Opcional) Qual ação automática foi tomada.             |
| `acao_parametro`      | VARCHAR(255)  | (Opcional) O alvo da ação (ex: o IP a ser bloqueado, o usuário a ser desabilitado).           |
| `data_acao_executada` | TIMESTAMP     | (Opcional) Quando a ação automática foi executada.                                            |
| `incidente_id`        | INT (FK)      | **[Link para `incidentes_analisados`]** (Opcional) Se esta detecção foi escalada para um incidente formal. |

### `incidentes_analisados`

Armazena os relatórios formais e enriquecidos sobre ameaças que foram confirmadas e investigadas.

| Coluna               | Tipo     | Descrição                                                                      |
| :------------------- | :------- | :----------------------------------------------------------------------------- |
| `id`                 | INT      | Identificador único do incidente.                                              |
| `titulo`             | VARCHAR  | Título descritivo do incidente.                                                |
| `status_id`          | INT (FK) | **[Link para `enum_status_incidente`]** O estado atual do incidente.            |
| `dispositivo_id`     | INT (FK) | **[Link para `dispositivos`]** O principal dispositivo afetado.                 |
| `nivel_risco_id`     | INT (FK) | **[Link para `enum_nivel_risco`]** A gravidade do incidente.                    |
| `resumo_tecnico`     | TEXT     | Análise técnica detalhada.                                                     |
| `acoes_recomendadas` | JSON     | Lista de ações recomendadas para a equipe de TI/Segurança.                     |

### `dispositivos`

Catálogo de todos os dispositivos monitorados pelo sistema.

| Coluna    | Tipo     | Descrição                                                            |
| :-------- | :------- | :------------------------------------------------------------------- |
| `id`      | INT      | Identificador único do dispositivo.                                  |
| `nome`    | VARCHAR  | Nome amigável (ex: "Servidor Web Principal").                        |
| `host`    | VARCHAR  | Endereço de IP ou hostname do dispositivo.                           |
| `status_id`| INT (FK) | **[Link para `enum_status_dispositivo`]** O status operacional do dispositivo. |

---

## 3. Fluxo de Dados na Prática

1.  **Detecção:** Um modelo de análise envia um resultado para a API (ex: `predicao=10` para o `dispositivo_id=5`).
2.  **Registro:** A API insere uma nova linha na tabela **`deteccoes`**:
    * `dispositivo_id` = `5`
    * `predicao` = `10`
    * `tipo_ataque_id` = `10` (traduzido do mapa)
    * `status_resposta_id` = `1` (ID de 'Pendente')
3.  **Resposta Automática (Opcional):** Se o ataque (`tipo_ataque_id=10`) for crítico, o sistema:
    * Executa uma ação, como bloquear um IP.
    * Atualiza a linha em **`deteccoes`**:
        * `status_resposta_id` = `2` (ID de 'Ação Automática Executada')
        * `acao_executada_id` = `1` (ID de 'BLOCK_IP')
        * `acao_parametro` = `'203.0.113.75'`
        * `data_acao_executada` = (Timestamp atual)
4.  **Análise Humana:** Um analista vê a detecção na interface. Se for uma ameaça real, ele cria um relatório.
5.  **Escalonamento para Incidente:**
    * Uma nova linha é criada na tabela **`incidentes_analisados`**.
    * O `id` desse novo incidente é usado para atualizar o campo `incidente_id` na detecção original na tabela **`deteccoes`**, conectando o evento bruto à análise formal.