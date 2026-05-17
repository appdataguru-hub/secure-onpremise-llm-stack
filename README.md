### 📄 Файл 1: `README.md`


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

git clone [https://github.com/appdataguru-hub/secure-onpremise-llm-stack.git](https://github.com/appdataguru-hub/secure-onpremise-llm-stack.git)
cd secure-onpremise-llm-stack

---

2. Запустите инфраструктурный стек:

docker compose up -d

---

3. Проверьте доступность локального инференса (OpenAI-compatible API):


curl http://localhost:8000/v1/models

---

### 📄 Файл 2: `docker-compose.yaml`

```yaml
version: '3.8'

services:
  # 1. Высокопроизводительный локальный инференс LLM
  vllm-inference:
    image: vllm/vllm-openai:latest
    container_name: vllm-core-node
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    ports:
      - "8000:8000"
    ipc: host
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

  # 2. Изолированная СУБД с поддержкой векторного поиска для RAG
  postgres-vector:
    image: ankane/pgvector:latest
    container_name: postgres-rag-db
    environment:
      POSTGRES_USER: dataguru_admin
      POSTGRES_PASSWORD: SecureEnterprisePassword2026
      POSTGRES_DB: mas_knowledge_base
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  # 3. Локальный сервер оркестрации бизнес-процессов
  n8n-automation:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: n8n-orchestrator
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres-vector
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=mas_knowledge_base
      - DB_POSTGRESDB_USER=dataguru_admin
      - DB_POSTGRESDB_PASSWORD=SecureEnterprisePassword2026
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - postgres-vector
    restart: unless-stopped

volumes:
  pgdata:
  n8n_data:

```
