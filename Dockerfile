FROM python:3.13.9-slim

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release && \
    rm -rf /var/lib/apt/lists/*

# Instala Docker CLI
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Instala Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de dependencias y el código fuente
COPY pyproject.toml poetry.lock ./
COPY src/ ./src/
COPY README.md ./

# Instala las dependencias
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Expone el puerto del servidor
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["poetry", "run", "deploy"]