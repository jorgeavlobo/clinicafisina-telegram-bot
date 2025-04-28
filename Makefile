# Makefile para facilitar gestão do bot Telegram da Clínica Fisina

PROJECT=clinicafisina_telegram_bot

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker logs -f $(PROJECT)

restart:
	docker-compose restart $(PROJECT)

build:
	docker-compose build --no-cache

pull:
	docker-compose pull

health:
	curl -f http://localhost:8444/healthz

ping:
	curl -f http://localhost:8444/ping
