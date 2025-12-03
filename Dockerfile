FROM python:3.13.9-slim

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Instala Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de dependencias y el código fuente
COPY pyproject.toml poetry.lock ./
COPY src/ ./src/

# Copia archivos de configuración si existen
COPY api_config.json ./
COPY .env ./
COPY README.md ./

# Instala las dependencias
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Expone el puerto del servidor
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["poetry", "run", "deploy"]