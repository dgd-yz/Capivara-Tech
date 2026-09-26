# Revisão de configurações e certificados

Revisão do código em 26/09/2026. Não é uma verificação do banco ou dos arquivos da VPS.

## Corrigido nesta alteração

| Problema | Alteração |
| --- | --- |
| `django-extra-settings` constava apenas em requirements | App registrado, padrões criados pelo `migrate` e configurações ligadas às páginas. |
| Nome, edição, datas, local e contato repetidos nos templates | Dados centralizados em `core/event_config.py`, editáveis no admin. |
| Contadores fixos de palestras/minicursos | Contagem dos cadastros publicados; duração calculada pelas datas. Público esperado continua sendo uma estimativa editável. |
| Lista de frequência com data/nome antigos | PDF usa a mesma configuração das páginas. |
| Certificado geral com nome de agroecologia e 24 horas fixas | Nome e horas vêm das configurações do evento. |
| Participantes de minicursos excluídos do certificado geral | Todos os confirmados são elegíveis ao certificado geral; minicursos continuam tendo certificado próprio. |
| Oito horas fixas para qualquer minicurso | Campo de carga horária em cada minicurso; os existentes começam com 8 horas, preservando o comportamento anterior. |
| Upload de imagens indisponível no editor | URL, botão e controles de imagem habilitados, com upload restrito a usuários da equipe. |
| PDF buscava o fundo e uploads pela URL pública do site | Fundo incorporado no PDF e uploads lidos diretamente do storage. Recursos externos e arquivos arbitrários são bloqueados. |
| `.objects.get()` falhava sem configuração de certificado | `get_solo()` inicializa a configuração; fundo tornou-se opcional. |
| CSS aumentava todas as imagens e aplicava margem a todas as divs | Estilos limitados ao corpo do certificado e ao bloco de validação; margens em milímetros editáveis. |
| Fundo global alterava todos os certificados novos já emitidos | Novos certificados guardam a referência ao arquivo usado. Certificados antigos, sem referência, continuam usando o fundo global. |
| Ajuda das variáveis mostrava chaves incorretas | Exemplos agora mostram as chaves duplas esperadas pelo template. |

## Onde configurar

**Configurações do evento → Settings**: editar as entradas `EVENT_*` já criadas.
Não é necessário criar nomes novos nem reiniciar o servidor. Nome, edição,
datas, local, cidade, endereço, contato público, Instagram, mapa, apresentação,
público esperado e carga horária geral estão disponíveis.

Mantenha a data final igual ou posterior à inicial. Alterar essas datas não
reagenda as atividades: ajuste também **Core → Programação**. As imagens de
marca não mudam ao alterar o nome do evento.

**Core → Minicursos**: carga horária específica de cada minicurso.

**Core → Configurações de email**: assunto/corpo das confirmações e destino do
formulário. O contato público `EVENT_CONTACT_EMAIL` e a caixa que recebe o
formulário são configurações distintas. Os modelos de mensagem já personalizados
não são sobrescritos ao alterar a configuração geral do evento.

**Certificação → Configurações de Certificados**:

1. Preencher local, data de emissão, nome/cargo do responsável e texto.
2. Enviar um fundo A4 horizontal (proporção 297 × 210), se desejado.
3. Inserir assinaturas e logos pelo botão de imagem do editor e ajustar o tamanho.
4. Ajustar as quatro margens do texto. Reservar a parte inferior para o QR code.
5. Gerar um certificado de teste e abrir **Ver Certificado** antes de emitir em lote.

Imagens externas coladas por URL não são carregadas; envie-as pelo editor.
O fundo pertence à página, enquanto as imagens do editor acompanham o texto.
Textos longos podem gerar mais de uma página: valide o modelo real antes da emissão.
As margens são globais; mudá-las também altera o layout dos certificados antigos.
Não apague uploads usados por certificados emitidos.

## Conteúdo que ainda está fixo ou legado

| Prioridade | Local | Situação / próximo trabalho |
| --- | --- | --- |
| Alta | `core/templates/core/submissions.html` | Regulamento de agroecologia, prazos de 2025, email antigo e links de Google Forms/Docs. A rota continua acessível. Substituir por regulamento aprovado ou retirar a página de publicação. |
| Alta | `core/templates/core/letter.html` | Carta de outro evento, datada de abril de 2025. A rota continua acessível; precisa decisão editorial. |
| Média | Home, realização e rodapé | Patrocinador OxenteNet, logos e descrições institucionais fixos. Melhor solução: cadastro de parceiros com imagem, categoria, ordem e publicação. |
| Média | `core/templates/core/accommodations.html` | Hotéis, telefones e endereços fixos, incluindo links WhatsApp com barras duplicadas. Converter em cadastro de hospedagens e revisar os contatos. |
| Média | Home e sobre | Fotos de destaque `evento01/02/03.png` independentes da galeria, slogans e textos institucionais fixos. Campos de imagem/texto ou seleção de itens da galeria resolveriam. |
| Média | `core/tasks.py:generate_and_send_certification` | Task antiga sem chamadores encontrados, usa template ausente `core/certification.html`, nome de agroecologia e arquivo temporário. Não faz parte do fluxo atual do admin. Aposentar após conferir tasks antigas na VPS ou migrar eventuais consumidores. |
| Baixa | `core/templates/index.html` e antigos emails `registration.*` | Templates legados sem uso no fluxo atual de inscrição; revisar antes de remover. |
| Estrutural | Cadastros de inscrição/certificados | Sistema ainda representa uma única edição. Alterar `EVENT_*` não cria histórico separado de eventos; para múltiplas edições, criar entidade Evento e relacionar os cadastros. |

Não alterei regulamentos, contatos de terceiros nem promessas editoriais sem dados
atuais. Palestrantes, minicursos, agenda, galeria e mensagens de inscrição já têm
cadastros próprios; não precisam ser duplicados em configurações genéricas.

## Implantação e validação

Depois de atualizar os arquivos na VPS, na pasta do projeto:

```sh
docker compose -p capivara-tech -f docker-compose.prod.yml build web worker
docker compose -p capivara-tech -f docker-compose.prod.yml up -d --force-recreate --no-deps --wait web
docker compose -p capivara-tech -f docker-compose.prod.yml up -d --force-recreate --no-deps worker
```

Execute o próximo comando somente após sucesso do anterior. O entrypoint do web
aplica migrations de `extra_settings`, `core` e `certification` e coleta os assets
do editor. Não é necessário recriar banco nem remover volumes.

Validação local: suíte Django, geração real de PDF com fundo e upload no corpo,
inspeção visual do PDF em A4 horizontal com uma página, duas imagens e QR code.
O teste usa imagens sintéticas; ainda é necessário conferir a arte real na VPS.

Referências de integração: [django-extra-settings](https://github.com/fabiocaccamo/django-extra-settings)
e [django-ckeditor-5](https://github.com/hvlads/django-ckeditor-5).
