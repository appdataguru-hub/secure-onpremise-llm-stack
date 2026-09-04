# Secure On-Premise LLM & MAS Infrastructure Stack 🐳🔒

Готовый конфигурационный стек для развертывания изолированной ИИ-инфраструктуры внутри корпоративного периметра компании. Исключает передачу конфиденциальных данных (PII, коммерческая тайна) во внешние облачные API.

---

### 🏗️ Архитектура контура

Стек поднимает локальную экосистему, готовую к высоким нагрузкам (High-Performance Inference) и сквозной автоматизации:

* **vLLM Engine:** Высокопроизводительный сервер инференса для локальных моделей (Llama-3, Gemma), поддерживающий непрерывное пакетное выполнение (Continuous Batching) и PagedAttention.
* **PostgreSQL + pgvector:** Реляционная база данных со специализированным расширением для хранения и быстрого HNSW-поиска по векторным эмбеддингам документов (База знаний RAG).
* **n8n Automation:** Селф-хостед версия платформы оркестрации для интеграции со смежными корпоративными системами (CRM, SIP-телефония).

---

### 💻 Системные требования (Hardware Requirements)

Для стабильного инференса моделей уровня `Llama-3-8B-Instruct` (в квантовании INT4/FP16) в локальном контуре рекомендуется:

* **GPU:** 1x NVIDIA A10G / A100 (или RTX 3090 / 4090 с 24GB VRAM)
* **Drivers:** NVIDIA Driver >= 535+, CUDA Toolkit >= 12.1
* **Runtime:** NVIDIA Container Toolkit (для проброса GPU в Docker-контейнеры)

---

### 🛠️ Быстрый запуск (Deployment)

1. Клонируйте репозиторий на ваш GPU-сервер:

```bash
git clone https://github.com/kvochkin-dev/secure-onpremise-llm-stack.git
cd secure-onpremise-llm-stack
```

2. Создайте файл `.env` из шаблона и задайте собственный пароль БД и токен Hugging Face:

```bash
cp .env.example .env
# сгенерируйте пароль:  openssl rand -base64 24
```

3. Запустите инфраструктурный стек:

```bash
docker compose up -d
```

4. Проверьте доступность локального инференса (OpenAI-compatible API):

```bash
curl http://localhost:8000/v1/models
```

Первый запуск vLLM скачивает веса модели, поэтому до ответа на `curl` может пройти несколько минут.

### ⚙️ Конфигурация (`docker-compose.yaml`)

Файл `docker-compose.yaml` лежит в корне репозитория. Секреты и параметры задаются через переменные окружения в файле `.env` (см. `.env.example`):

| Переменная | Назначение |
| --- | --- |
| `MODEL_NAME` | Модель, обслуживаемая vLLM (по умолчанию `meta-llama/Meta-Llama-3-8B-Instruct`) |
| `HF_TOKEN` | Токен Hugging Face для gated-моделей (Llama-3, Gemma) |
| `POSTGRES_USER` | Пользователь PostgreSQL (по умолчанию `dataguru_admin`) |
| `POSTGRES_PASSWORD` | **Обязательный** пароль БД — не используйте значение по умолчанию |
| `POSTGRES_DB` | Имя базы данных (по умолчанию `mas_knowledge_base`) |
