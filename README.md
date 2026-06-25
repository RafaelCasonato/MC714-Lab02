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

Criar um evento local no `node1`:

```bash
curl -X POST http://localhost:8001/clock/local \
  -H "Content-Type: application/json" \
  -d '{"text": "processamento local"}'
```

Enviar uma mensagem do `node1` para o `node2`:

```bash
curl -X POST http://localhost:8001/send/2 \
  -H "Content-Type: application/json" \
  -d '{"text": "ola do node1"}'
```

Ver mensagens recebidas pelo `node2`:

```bash
curl http://localhost:8002/messages
```

O campo `clock` em `/status` mostra o relogio logico do no. Quando um no recebe mensagem, ele atualiza o relogio usando:

```text
max(relogio_local, relogio_recebido) + 1
```

Enviar uma mensagem do `node1` para todos os outros nos:

```bash
curl -X POST http://localhost:8001/broadcast \
  -H "Content-Type: application/json" \
  -d '{"text": "mensagem para todos"}'
```

Pedir para um no entrar na secao critica:

```bash
curl -X POST http://localhost:8002/mutex/enter \
  -H "Content-Type: application/json" \
  -d '{"hold_seconds": 2}'
```

O estado da exclusao mutua aparece em:

```bash
curl http://localhost:8002/status
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
- `app/client.py`: cliente HTTP simples para comunicacao entre os nos.
- `Dockerfile`: imagem da aplicacao.
- `docker-compose.yml`: sobe cinco nos na mesma rede Docker.
- `requirements.txt`: dependencias Python.
