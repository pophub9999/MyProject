# NOVA — loja em preparação

Loja de demonstração em português com apresentação, catálogo pesquisável, filtros e carrinho guardado no navegador. Nome, produtos e preços provisórios. Não processa pagamentos nem encomendas.

## Ficheiros

- `public/index.html`: interface completa, sem dependências externas.
- `compose.yaml`: serviço Nginx para alojamento com Docker e Traefik.

## Personalizar

Editar a marca e os textos em `public/index.html`. O array `products` define o catálogo; preços em cêntimos. O carrinho guarda apenas IDs e quantidades localmente no navegador.

## Alojamento

Definir `STORE_HOST` no ambiente do servidor, usar uma rede Docker externa chamada `coolify` e executar `docker compose up -d`. O proxy deve disponibilizar os entrypoints `http` e `https` e o resolvedor `letsencrypt`. As atualizações são manuais: sincronizar o repositório e executar novamente o Compose.

## Antes de vender

Definir catálogo real, stock, portes, domínio e contactos; integrar backend e pagamentos; preparar condições comerciais e informação legal aplicável. Esta versão não tem gestão de encomendas, contas de cliente ou checkout real.
