# QCyber Security


```

+-------------------------------------------+                 +-------------------------------------------+
|               PC-1                        |                 |                    PC-2                   |
|                 |                         |                 |                     |                     |
|                                           |                 |                                           |
|  +-----------------+   +---------------+  |                 |  +--------------------------------------+ |
|  | Interface Web   |   | API Principal |  |                 |  |     API de Análise (mainAPI.py)      | |
|  |   (Flutter)     |-->|   (FastAPI)   |  |                 |  |          (Flask + crewai)            | |
|  +-----------------+   +---------------+  |                 |  +--------------------------------------+ |
|          ^                   |            |                 |                    ^                      |
|          | (Lê Dados)        v            |                 |                    | (Escreve Análise)    |
|  +-------------------------------+        |                 |                    |                      |
|  |     Banco de Dados (MySQL)    | <---------------------------------------------+                      |
|  +-------------------------------+        |    Porta        |                    ^                      |
|          ^                                |                 |                    |                      |
|          |                                |                 |                    |                      |
|  +-----------------------+                |                 |                    +                      |
|  |    Simulador Sensor   |----------------|-----------------|----->(Envia Dados para Análise)           |
|  | (simulador_sensor.py) |                |    Porta        |                                           |
|  +-----------------------+                |                 |                                           |
|                                           |                 |                                           |
+-------------------------------------------+                 +-------------------------------------------+


```


1- Simulador Sensor (simulador_sensor.py)
Função Principal: Atua como um "sensor de rede" simulado, gerando o fluxo de entrada de dados para o sistema.

Detalhes:

Lê dados de ataques de um arquivo .csv pré-definido, linha por linha.

Envia os dados de cada ataque via requisição HTTP POST para a API de Análise.

Pausa a execução por alguns segundos entre cada envio para simular a chegada de dados em tempo real.

2- API de Análise (main.py com Flask + crewai)
Função Principal: É o microsserviço de inteligência do sistema, responsável pela classificação inicial dos eventos.

Detalhes:

Expõe um endpoint (/analisar) que recebe os dados brutos enviados pelo Simulador.

Utiliza o sistema multiagente (crewai) para analisar e determinar o tipo específico de ataque (ex: "SQL Injection", "DDoS").

Conecta-se remotamente ao banco de dados e salva esta classificação inicial como um novo registo na tabela deteccoes.

3- Banco de Dados (MySQL)
Função Principal: É o repositório central e a única fonte de verdade para todas as informações do sistema.

Detalhes:

Armazena os dados permanentes, como a lista de dispositivos cadastrados (dispositivos).

Guarda o registo de cada ataque classificado pela API de Análise (deteccoes).

Armazena as análises aprofundadas geradas por modelos secundários (incidentes_analisados), vinculando-as a uma detecção específica através de uma chave estrangeira.

4- API Principal (FastAPI)
Função Principal: Serve como o backend para a interface do utilizador (BFF - Backend for Frontend), orquestrando o acesso aos dados.

Detalhes:

Comunica-se exclusivamente com o Banco de Dados para obter e agregar informações.

Fornece endpoints para popular o dashboard com KPIs e dados para os gráficos.

Oferece rotas para buscar listas detalhadas para as telas de histórico (ex: "todos os ataques no Dispositivo X").

Contém a lógica para gerar os relatórios em PDF quando solicitado pela interface.

5- Interface Web (Flutter)
Função Principal: É a camada de apresentação e interação com o utilizador.

Detalhes:

Comunica-se exclusivamente com a API Principal (FastAPI) para obter e enviar dados.

Apresenta os KPIs e os gráficos interativos no dashboard.

Permite ao utilizador filtrar dados por período (24h, 7 dias, etc.).

Fornece interfaces para a gestão de dispositivos (CRUD) e para a visualização detalhada de históricos de ataques e incidentes.

Inicia o download dos relatórios em PDF gerados pela API Principal.