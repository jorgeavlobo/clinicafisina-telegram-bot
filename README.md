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
- **Makefile** (automatização de comandos)

---

## 📂 Estrutura do projeto

```plaintext
clinicafisina_telegram_bot/
│
├── bot/
│   ├── auth/                  # Lógica de autenticação
│   ├── database/              # Ligação e queries à base de dados
│   ├── filters/               # Filtros personalizados Aiogram
│   ├── handlers/              # Handlers Telegram organizados por função
│   ├── menus/                 # Inline e Reply keyboards
│   ├── middlewares/           # Middlewares globais
│   ├── scripts/               # Scripts auxiliares
│   ├── states/                # Definições de estados FSM
│   ├── utils/                 # Utilitários comuns
│   ├── config.py              # Configurações (.env ou variáveis ambiente)
│   ├── main.py                # Ponto de entrada principal
│   └── __init__.py
│
├── migrations/                # Scripts SQL de criação de base de dados
├── docker-compose.yml         # Docker Compose para orquestração
├── Dockerfile                 # Dockerfile da aplicação
├── requirements.txt           # Dependências Python
├── README.md                  # Este ficheiro
├── Makefile                   # Automatização de comandos Docker
├── app.py                     # Entrypoint para Docker
└── .env                       # (opcional) Variáveis de ambiente locais
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

Cria um ficheiro `.env` baseado no `.env.example`.

3. **Correr o bot localmente**

```bash
python app.py
```

⚠ Atenção: para Webhook funcionar localmente, é necessário expor o servidor (ex.: ngrok) ou configurar domínio+SSL.

---

## 🐳 Como correr o bot em Docker

1. **Build da imagem e correr o serviço**

```bash
docker-compose up -d --build
```

2. **Verificar estado do container**

```bash
docker ps
```

Deverá aparecer `STATUS: healthy` se o healthcheck passou.

3. **Ver logs em tempo real**

```bash
docker logs -f clinicafisina_telegram_bot
```

---

## 📜 Comandos rápidos via Makefile

```bash
make up        # Sobe os serviços Docker
make down      # Derruba os serviços
make logs      # Vê logs da aplicação
make restart   # Reinicia o container do bot
make build     # Faz rebuild completo da imagem
make pull      # Faz pull da imagem mais recente
make health    # Faz teste de healthcheck (localhost)
make ping      # Faz ping ao bot (localhost)
```

---

## 🔒 Segurança

- Proteção automática contra cliques em menus antigos (middleware ativo).
- Webhook protegido com `SECRET_TOKEN` validado no header.
- Resposta rápida a healthchecks (`/healthz` e `/ping`) para Docker monitorizar.
- Acesso HTTP público apenas via Nginx (TLS / Let's Encrypt).
- Container protegido (porta 8444 exposta apenas internamente).

---

## 📅 Roadmap futuro

- [ ] CRUD completo de utilizadores
- [ ] Agenda ligada a eventos reais de sessões
- [ ] Melhorias UX dos menus de utilizador
- [ ] Setup de GitHub Actions para CI/CD automático
- [ ] Documentação OpenAPI futura (API REST se necessário)

---

## 👨‍💻 Contribuição

Projeto privado para a Clínica Fisina.  
Seguir práticas de:
- Código modular
- Comentado em inglês
- Clean Code
- Compatível com Docker + produção

---

## 📄 Licença

Projeto privado e não licenciado publicamente.
