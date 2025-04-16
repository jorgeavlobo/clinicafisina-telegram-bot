# 📩 Clinica Fisina Telegram Bot

**Clinica Fisina Telegram Bot** is a Dockerized bot built with [Aiogram](https://github.com/aiogram/aiogram), designed to manage client interactions and appointments for Clinica Fisina. It leverages Redis for Finite State Machine (FSM) state storage and PostgreSQL for client data and logging. The bot is deployed on an OVHcloud VPS and automated via GitHub Actions for seamless updates.

---

## 🌟 Features

- **User-Friendly Interface**: Handles client interactions through Telegram with an intuitive command structure.
- **Finite State Machine (FSM)**: Manages multi-step conversations (e.g., booking appointments) with Redis-backed state storage.
- **Dual Database Support**: Uses PostgreSQL for client data (`fisina`) and bot logs (`logs`).
- **Dockerized Deployment**: Ensures consistent environments and easy scaling.
- **Automated Workflows**: GitHub Actions automate deployment to the VPS.

---

## 🛠 Setup

### Prerequisites

- **Docker** and **Docker Compose** installed on the target server.
- **GitHub SSH Key**: For cloning the private repository.
- **PostgreSQL Server**: With databases `fisina` and `logs` configured.
- **Redis Instance**: Running on the same network (e.g., `redis_fsm` container).

### Installation

1. **Clone the Repository**:
   ```bash
   git clone git@github.com:jorgeavlobo/clinicafisina-telegram-bot.git /opt/clinicafisina_telegram_bot
   cd /opt/clinicafisina_telegram_bot
   ```

2. **Configure Environment Variables**:
   - Create a `.env` file in the project root:
     ```bash
     nano .env
     ```
   - Add the following (replace placeholders with actual values):
     ```
     TELEGRAM_TOKEN=your_bot_token_here
     DB_HOST=your_db_host
     DB_PORT=5432
     DB_NAME_FISINA=fisina
     DB_NAME_LOGS=logs
     DB_USER=your_db_user
     DB_PASSWORD=your_db_password
     REDIS_HOST=redis
     REDIS_PORT=6379
     REDIS_DB=0
     REDIS_PREFIX=fisina_tel_bot:fsm
     ```

3. **Build and Run with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```

4. **Verify the Container**:
   ```bash
   docker ps
   ```
   - Look for the `clinicafisina_telegram_bot` container.

---

## 🚀 Usage

### Bot Commands

- `/start`: Initializes the bot and displays a welcome message.
- `/help`: Shows available commands and usage instructions.
- `/book`: Starts the appointment booking process (multi-step FSM interaction).

### Connecting to Databases

- **Client Data**: Stored in the `fisina` PostgreSQL database.
- **Logs**: Bot activity is logged in the `logs` PostgreSQL database.

---

## 📂 Repository Structure

- **`bot.py`**: Main bot logic, including handlers and FSM management.
- **`config.py`**: Configuration settings loaded from environment variables.
- **`requirements.txt`**: Python dependencies for the bot.
- **`docker-compose.yml`**: Defines the bot service and network connections.
- **`Dockerfile`**: Instructions for building the bot’s Docker image.
- **`.env`**: Environment variables (excluded from version control).
- **`.gitignore`**: Excludes sensitive files and build artifacts.

---

## 🔐 Security Notes

- **Environment Variables**: Sensitive data (e.g., `TELEGRAM_TOKEN`, `DB_PASSWORD`) is stored in `.env` and loaded securely.
- **Database Access**: PostgreSQL credentials are restricted to the bot’s user.
- **Redis**: FSM states are namespaced with `fisina_tel_bot:fsm` to avoid conflicts.

---

## 🤝 Contributing

Contributions are welcome! To suggest improvements or report issues:

1. Fork the repository.
2. Create a branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

---

## 📬 Contact

For questions or support, contact [Jorge Lobo](mailto:your.email@example.com) or open an issue in the repository.

---

*Built with ❤️ for Clinica Fisina’s clients and powered by Aiogram, Redis, and PostgreSQL.*
