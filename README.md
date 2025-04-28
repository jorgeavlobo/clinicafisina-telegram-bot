# 📦 clinicafisina_telegram_bot

Telegram Bot oficial para a Clínica Fisina.

Este bot é desenvolvido em [Aiogram 3.20](https://docs.aiogram.dev/en/latest/) (framework assíncrona para bots Telegram), com armazenamento de estado (`FSM`) em Redis, base de dados PostgreSQL, e deploy por Docker em servidor VPS.

---

## 🚀 Tecnologias utilizadas

- **Python 3.10+**
- **Aiogram 3.20**
- **Redis** (armazenamento de FSM)
- **PostgreSQL** (armazenamento de dados)
- **Docker + Docker Compose** (orquestração)
- **aiohttp** (servidor Webhook interno)

---

## 📂 Estrutura do projeto

```plaintext
clinicafisina_telegram_bot/
│
├── bot/
│   ├── auth/                 # Lógica de autenticação
│   ├── database/             # Ligação e queries à base de dados
│   ├── filters/              # Filtros personalizados Aiogram
│   ├── handlers/             # Handlers Telegram organizados por função
│   ├── menus/                # Inline e Reply keyboards
│   ├── middlewares/          # Middlewares globais
│   ├── scripts/              # Scripts auxiliares
│   ├── states/               # Definições de estados FSM
│   ├── utils/                # Utilitários comuns
│   ├── config.py             # Configurações (lidas do .env ou variáveis ambiente)
│   ├── main.py               # Ponto de entrada do bot
│   └── __init__.py
│
├── migrations/               # Scripts SQL de criação da base de dados
├── docker-compose.yml        # Docker Compose para serviços
├── Dockerfile                # Dockerfile do bot
├── requirements.txt          # Dependências Python
├── README.md                 # Este ficheiro
├── app.py                    # Entrypoint para Docker
└── .env                      # (opcional) Variáveis de ambiente locais
```

---

## 🛠 Como correr o bot localmente (modo desenvolvimento)

> Requisitos:
> - Python 3.10+
> - Redis local (ou remoto)
> - PostgreSQL local (ou remoto)

1. **Instalar dependências**

```bash
pip install -r requirements.txt
```

2. **Definir variáveis de ambiente**

Cria um ficheiro `.env` baseado no `.env.example` incluído.

Exemplo de `.env`:

```env
BOT_TOKEN=123456:ABCDEF
DOMAIN=telegram.seudominio.pt
WEBAPP_PORT=8444
TELEGRAM_SECRET_TOKEN=seu_token_secreto
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clinicafisina
DB_USER=seu_utilizador
DB_PASSWORD=sua_password
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PREFIX=clinicafisina:fsm
```

3. **Correr o bot localmente**

```bash
python app.py
```

⚠ Atenção: para Webhook funcionar localmente, é necessário expor o servidor (ex.: usar [ngrok](https://ngrok.com/)) ou configurar domínio + certificado SSL.

---

## 🐳 Como correr o bot em Docker

1. **Build da imagem**

```bash
docker-compose build
```

2. **Correr os serviços**

```bash
docker-compose up -d
```

3. **Verificar logs**

```bash
docker logs -f clinicafisina_telegram_bot
```

---

## 🔒 Segurança

- Proteção contra cliques em menus antigos implementada.
- Middleware de verificação de permissões (RoleCheckMiddleware).
- Segredo do Webhook validado através do cabeçalho `X-Telegram-Bot-Api-Secret-Token`.
- Logs em tempo real.
- Pool de ligações PostgreSQL eficiente.

---

## 📅 Roadmap (futuro)

- [ ] Implementar gestão de utilizadores (CRUD completo)
- [ ] Ligar o módulo de Agenda a eventos reais
- [ ] Melhorias UX/UI dos menus
- [ ] Deploy automático por CI/CD (GitHub Actions)
- [ ] Documentação Swagger/OpenAPI (para API paralela)

---

## 👨‍💻 Contribuição

Este projeto é desenvolvido de forma privada para a Clínica Fisina.  
Se precisar de alterar ou expandir funcionalidades, siga as práticas definidas:
- Código modular
- Comentado em inglês
- Clean Code
- Manter compatibilidade Docker

---

## 📄 Licença

Este projeto é privado e não licenciado publicamente.
