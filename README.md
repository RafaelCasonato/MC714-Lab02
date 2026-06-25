# MC714 - Lab 02

Projeto do segundo trabalho de MC714, usando FastAPI e Docker para executar varios nos localmente.

## Como executar

Subir os containers:

```bash
docker compose up --build
```

Em outro terminal, testar alguns nos:

```bash
curl http://localhost:8001/status
curl http://localhost:8002/status
curl http://localhost:8003/status
```

Cada servico representa um no:

- node1: http://localhost:8001
- node2: http://localhost:8002
- node3: http://localhost:8003
- node4: http://localhost:8004
- node5: http://localhost:8005

Parar o ambiente:

```bash
docker compose down
```

## Estrutura atual

- `app/main.py`: API inicial de cada no.
- `Dockerfile`: imagem da aplicacao.
- `docker-compose.yml`: sobe cinco nos na mesma rede Docker.
- `requirements.txt`: dependencias Python.
