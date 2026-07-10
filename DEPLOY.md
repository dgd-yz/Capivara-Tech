# Deploy — Capivara Tech

Mesmo padrão do Baby Tracker: **docker-compose** (web + worker + Postgres) rodando
na VPS, exposto só em `127.0.0.1:8002`, com o **nginx do host** fazendo proxy
reverso + HTTPS (certbot), e **GitHub Actions** disparando o deploy por SSH a cada
push na `main`.

```
push na main → GitHub Actions (testa) → SSH na VPS → docker/deploy.sh
             → docker compose up --build → nginx do host faz HTTPS → 127.0.0.1:8002
```

- Domínio: **capivaratech.dgdlabs.com.br**
- Porta interna na VPS: **8002** (o Baby Tracker usa 8001)
- Pasta na VPS: **`~/capivara-tech`**

---

## 1) Uma vez só — preparar a VPS

> Docker + Docker Compose plugin já estão instalados (mesma VPS do Baby Tracker).

```sh
# clonar no caminho fixo usado pelo deploy.sh
git clone https://github.com/dgd-yz/Capivara-Tech.git ~/capivara-tech
cd ~/capivara-tech

# criar o .env de produção a partir do sample e preencher os segredos
cp .env.prod.sample .env
nano .env        # SECRET_KEY, POSTGRES_PASSWORD, DATABASE_URL, e-mail...

# gerar um SECRET_KEY forte, por exemplo:
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# primeira subida (roda migrations e collectstatic sozinho pelo entrypoint)
docker compose -f docker-compose.prod.yml up -d --build
```

Confira: `curl -s http://127.0.0.1:8002/health/` deve responder `ok`.

## 2) nginx do host + HTTPS

```sh
sudo cp docker/nginx-capivaratech.conf.example \
        /etc/nginx/sites-available/capivaratech.dgdlabs.com.br
sudo ln -s /etc/nginx/sites-available/capivaratech.dgdlabs.com.br \
           /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# DNS: crie um registro A "capivaratech" apontando pro IP da VPS antes deste passo
sudo certbot --nginx -d capivaratech.dgdlabs.com.br
```

## 3) Ligar o GitHub Actions à VPS

Reaproveite a mesma chave SSH de deploy da VPS (a pública já está no
`~/.ssh/authorized_keys`). Em **Settings → Secrets and variables → Actions** do
repositório `dgd-yz/Capivara-Tech`:

**Secrets:**
| Nome | Valor |
|------|-------|
| `VPS_HOST` | IP/host da VPS |
| `VPS_USER` | usuário SSH |
| `VPS_SSH_KEY` | chave **privada** de deploy |
| `VPS_PORT` | porta SSH (ex.: 22) |

**Variables:**
| Nome | Valor |
|------|-------|
| `ENABLE_DEPLOY` | `true` |

> O job `deploy` só roda quando `ENABLE_DEPLOY=true` — assim o CI não fica vermelho
> antes de tudo estar pronto. Enquanto isso, o job `test` roda normalmente.

## 4) A partir daí

Todo `git push` na `main`:
1. **test**: sobe um Postgres, checa migrations, roda testes, `collectstatic` e `check --deploy`.
2. **deploy** (se `main` + `ENABLE_DEPLOY=true`): SSH na VPS → `docker/deploy.sh`, que
   faz checkout do commit exato, backup do Postgres (gzip em `backups/`, 14 dias),
   `docker compose up -d --build` e espera o `/health/` ficar verde.

---

## Notas

- **Migrations sempre aditivas** — o deploy faz backup antes, mas evite migrations destrutivas.
- **Worker**: o container `worker` roda `db_worker` (fila de e-mails de contato/inscrição).
  Sem SMTP configurado no `.env`, os e-mails ficam na fila mas não saem.
- **Galeria/uploads** usam S3 (`django-storages`). Sem as vars `AWS_*` no `.env`, o site
  funciona normal; só o upload de imagens no admin/galeria falha.
- **Rollback**: `git checkout <sha_anterior>` em `~/capivara-tech` e
  `docker compose -f docker-compose.prod.yml up -d --build`. Backups do banco ficam em `backups/`.
