# SPA 2025

## To run

1. Copy .env.sample to .env

```sh
cp .env.sample .env
```

2. Run setup.sh

```sh
chmod +x setup.sh
./setup.sh
```

3. Access Browser http://localhost:8000

## Emails de inscrição e contato

No admin, abra **Core → Configurações de email** para editar o assunto e o
texto das mensagens de inscrição recebida e confirmada. As variáveis disponíveis
são `${nome}`, `${email}`, `${minicurso}` e `${protocolo}`. As mensagens são de
texto simples; escreva `$$` para incluir um cifrão literal.

Inscrições e contatos são enviados como `multipart/alternative`, com versões
`text/plain` e `text/html` equivalentes. O HTML escapa o conteúdo e não inclui
imagens. A Brevo pode adicionar pixels de rastreamento depois do envio; portanto,
confira também o MIME da mensagem recebida após implantar e reenviar um teste.
Anonimizar rastreamento na Brevo não equivale a desativá-lo. Se precisar remover
os pixels adicionados pelo provedor, consulte o suporte da Brevo sobre as opções
disponíveis na conta. Autenticação e MIME corretos não garantem saída do spam.

- O formulário de inscrição enfileira automaticamente a mensagem de recebimento.
  Isso não altera a aprovação da inscrição.
- A ação **Confirmar Inscrição**, ou marcar **Inscrição Confirmada?** ao editar
  no admin, enfileira a confirmação apenas quando o cadastro passa a confirmado.
- A ação **Reenviar email de inscrição (conforme status atual)** permite reenviar
  após corrigir o SMTP, inclusive para inscrições anteriores à implantação.
- O formulário de contato usa `DEFAULT_FROM_EMAIL` como remetente e o email do
  visitante em `Reply-To`. O destinatário é configurável no mesmo módulo; vazio,
  usa `contato@sistemasparainternet.com`, que também é o padrão de novas configurações.
  Essa caixa de entrada ou encaminhamento precisa existir no provedor de email
  do domínio; a configuração do site define apenas o destino das mensagens.

Os envios acontecem no worker e suas falhas ficam em DBTaskResult. As mensagens
personalizadas são lidas no momento da execução. O sucesso do formulário indica
cadastro e enfileiramento, não entrega na caixa de entrada.

### Atualizar na VPS

Depois de colocar esta versão do código na VPS, na pasta `~/capivara-tech`:

```sh
docker compose -p capivara-tech -f docker-compose.prod.yml build web worker
docker compose -p capivara-tech -f docker-compose.prod.yml up -d --force-recreate --no-deps --wait web
docker compose -p capivara-tech -f docker-compose.prod.yml up -d --force-recreate --no-deps worker
```

O entrypoint do web aplica a migration `0008_emailsettings`. Aguarde o comando
do web terminar com sucesso antes de recriar o worker. Os nomes dos containers
continuam os mesmos. Os comandos não recriam o banco nem removem volumes.

### Brevo: erro 535

`535 Authentication failed` significa que o servidor recusou o login ou a senha
SMTP. Use `EMAIL_HOST=smtp-relay.brevo.com`, `EMAIL_PORT=587`,
`EMAIL_USE_TLS=True`, o login SMTP em `EMAIL_HOST_USER` e uma chave **SMTP** em
`EMAIL_HOST_PASSWORD` (não a senha da conta ou chave da API). Configure também
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` e um remetente
verificado em `DEFAULT_FROM_EMAIL`.

Depois de editar o `.env`, recrie web e worker. Apenas reiniciar não atualiza as
variáveis do container. Para testar somente conexão e autenticação, sem enviar
uma mensagem e sem imprimir credenciais:

```sh
docker compose -p capivara-tech -f docker-compose.prod.yml exec worker python manage.py shell -c "from django.conf import settings; from django.core.mail import get_connection; assert settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend', 'Backend SMTP não configurado'; assert settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD, 'Credenciais SMTP ausentes'; c = get_connection(); c.open(); print('Conexão e autenticação SMTP OK'); c.close()"
```

Esse teste não comprova entrega nem autorização do remetente. Após corrigir as
credenciais, faça um contato de teste e use a ação de reenvio para inscrições.
Tasks que já falharam não são reenviadas por esses comandos de implantação.
 
