# Projeto: SaaS ERP Vertical

**SaaS de ERP vertical** — um módulo por segmento, multi-tenant, NF-e via gateway. O grupo econômico do Raphael é o cliente piloto.

## Status: EM CONSTRUÇÃO

O gatilho (maturidade do MMX Gestão) foi acionado em **01/08/2026**. Existe código rodando, publicado e testado. O planejamento já foi feito — a planta está em `sistema/documentacao/` (51 documentos, comece pelo `INDICE_MESTRE.md` e pelo `PLANO_MESTRE_CONSTRUCAO.md`, que é o dono único de prazo, preço e ordem).

- **Código:** `sistema/` · repo privado `girf52/saas-erp-vertical`, branch **`main`**
- **Nuvem:** Supabase `ucflgecidugtolzplojg` (sa-east-1) · Vercel `saas-erp-vertical.vercel.app` · CI no GitHub Actions
- **Estado em 05/08/2026:** 39 migrações, 513 testes verdes. **Onda 1 fechada no que não depende de contrato com terceiro**: pessoa → produtos/grade → estoque → vendas → categoria financeira/DRE → financeiro (títulos) → compras → OS/serviços → crediário → esqueleto fiscal → regime tributário (dual, com Simples híbrido) → conciliação bancária → relatórios/exportação → entrada de nota inteligente → migração assistida → GED
- **Travado por relógio externo (não por código):** emissão real de nota (contrato de gateway + certificado A1 + credenciamento SEFAZ), conteúdo tributário de presumido/real, BankingGateway (middleware bancário), TEF por adquirente
- **Telas (05/08/2026):** o núcleo tem interface — caixa de entrada, cadastros (pessoa/produto/migração), vender, comprar (XML), financeiro (títulos/baixa/contas) e relatórios com exportação. 23 rotas. Tudo renderizado no servidor, formulários que postam, zero acesso ao banco pelo navegador
- **A seguir:** PDV (Onda 2) — local-first com contingência offline, a engenharia mais pesada do plano
- **Sem dependência nova, de propósito:** parser de XML (`lib/xml.ts`), leitor de NF-e (`lib/nfe.ts`), escritor de XLSX (`lib/exportar.ts`), leitor de CSV (`lib/importar.ts`), conferência de upload (`lib/arquivo.ts`)

## Regras do usuário

- Responder sempre em **português brasileiro**.
- **NÃO misturar projetos.** Este é isolado do MMX, do APP Beleza e de qualquer outro. Nunca citar dados de outro projeto aqui.
- **Política de entrega:** sanar todas as dívidas antes de fechar uma etapa, sem deixar remendos. Backup depois que estiver limpo.
- Ao propor uma estratégia, reavaliar criticamente antes de implementar — o usuário cobra isso, e já retirei propostas por causa dessa cobrança.

## Antes de mexer no banco

Três armadilhas do Postgres que já custaram caro aqui e voltam a cada migração nova:

1. **`CREATE FUNCTION` concede EXECUTE a `PUBLIC`.** Um `revoke ... from <papel>` não tira nada.
2. **`ALTER DEFAULT PRIVILEGES` (migrações 0004/0005) faz toda tabela nova em `public` nascer gravável** pelos papéis da aplicação. Todo migration novo precisa do bloco explícito de `revoke`/`grant`.
3. **`revoke update (coluna)` não restringe um grant de tabela inteira.** Revogue a tabela e conceda coluna a coluna.

E: quem faz `revoke execute on all functions in schema interno from public` derruba os grants das migrações anteriores — reabra a lista inteira no fim do arquivo.

Rotina ao fechar uma etapa: `npx.cmd supabase db reset --no-seed` → `npx.cmd tsc --noEmit` → `npm test` → commit → push → CI → `npx.cmd supabase db push`.

**Coluna derivada entra em `interno.coluna_derivada`.** A guarda `interno.auditar_padroes()` roda no teste e quebra o build se alguma delas estiver gravável — foi ela que pegou 18 colunas abertas no fim da Onda 1, incluindo a prova do aceite do crediário. Se `testes/padroes.test.ts` falhar, ou faltou um `revoke` na migração nova, ou a coluna derivada não foi registrada. Não "ajustar o teste".

**Revisão de fim de onda** (prática adotada em 05/08/2026): antes de fechar cada onda, rodar a auditoria, sondar o que ela ainda não cobre e transformar todo achado repetível em regra da guarda.

## Arquitetura que não se desfaz

- **Contexto selado, não JWT.** `interno.current_tenant()` só aceita tenant acompanhado de selo HMAC cujo segredo mora em `interno`. Claim de JWT não é fonte aceita.
- **RLS com `force row level security`** em toda tabela de negócio, nunca filtro na aplicação. `interno.verificar_isolamento()` quebra o build se uma tabela nova nascer desprotegida.
- **Dado derivado não se escreve.** Saldo deriva do movimento; total da venda, dos itens.

## Stack

Next.js 14 + Supabase + RLS. Dinheiro em centavos inteiros; quantidade em `numeric(18,4)`. Pooler de transação (6543) para a app, pooler de sessão (5432) para os testes.
