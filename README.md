# NOVA — loja e backoffice

Loja em português e administração protegida em `/admin/`. O catálogo público usa os dados do backoffice. Checkout e pagamentos online permanecem desativados.

## Gestão

- Produtos: nome, descrição, fotografia JPG/PNG/WebP (até 5 MB), categoria, preço, stock, publicação e identificação de demonstração.
- Categorias e ordem no catálogo.
- Encomendas manuais com cliente, artigos, portes, notas e pagamento registado manualmente.
- Estados: rascunho → confirmada → enviada → concluída. Rascunhos e confirmadas podem ser cancelados.
- Confirmar desconta stock numa transação; cancelar uma confirmada repõe stock uma única vez. Enviadas não podem ser canceladas.
- Artigos e portes ficam bloqueados após confirmação. Os preços registados preservam o histórico.
- Exportação CSV das encomendas selecionadas.
- Nome da loja, slogan, título, apresentação e email público.
- Utilizadores, grupos de permissões e histórico de alterações.

## Instalação no servidor

Django 5.2 LTS, Gunicorn, SQLite persistente e Nginx atrás de Traefik. Backend sem portas publicadas no host.

1. Definir `STORE_HOST`, `COMPOSE_PROJECT_NAME` e uma `DJANGO_SECRET_KEY` aleatória longa em `.env` **apenas no servidor**.
2. Disponibilizar rede externa `coolify`, entrypoints `http`/`https` e resolvedor `letsencrypt`.
3. Executar `docker compose up -d --build`.
4. Obter o token inicial por SSH: `docker compose exec -T backend cat /data/setup-token`.
5. Abrir `https://SEU_DOMINIO/setup/#token=TOKEN` e escolher utilizador, email e palavra-passe. Ligação de utilização única, válida por 48 horas. Nunca publicar o token.
6. Depois, usar `/admin/`. Recuperação por email não configurada; recuperação por SSH: `docker compose exec backend python manage.py changepassword UTILIZADOR`.
7. Para renovar uma ligação expirada antes da ativação: `docker compose exec -T backend python manage.py bootstrap`.

## Atualizações

```sh
docker compose exec -T backend python manage.py backup_store
git pull --ff-only
docker compose build backend
docker compose run --rm --no-deps backend python manage.py test shop
docker compose up -d
docker compose exec -T backend python manage.py check --deploy
```

Os testes usam uma base de dados isolada. `/health/` verifica o processo; `/api/catalog/` só expõe produtos publicados e dados públicos.

## Persistência e backups

Volumes `store_data`, `media` e `admin_static` persistem nas atualizações. Nunca usar `docker compose down -v` para atualizar. `backup_store` guarda um snapshot consistente de SQLite e um arquivo de imagens em `/data/backups/`. Estes backups devem ser copiados para fora do VPS para proteção contra perda do servidor. Não há envio externo de backups configurado.

Restauro: parar o backend, preservar os volumes atuais, substituir base e imagens por uma cópia verificada, repor propriedade UID 10001, reiniciar e verificar o catálogo e login.

## Limites

Loja em preparação, com encomendas criadas manualmente. Sem checkout, cobranças, emails automáticos, faturas, transportadoras ou devoluções. "Pago" apenas regista um pagamento externo. O carrinho não reserva stock. Dados de demonstração são carregados apenas na primeira instalação. Definir catálogo real e condições comerciais antes de abrir vendas.
