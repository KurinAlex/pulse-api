FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

ENV Authorization=${Authorization}
ENV Cookie=${Cookie}

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen
COPY . .

EXPOSE 8000

CMD ["uv", "run", "src/main.py"]