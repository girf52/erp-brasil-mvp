# Projeto: SaaS ERP Vertical

**SaaS de ERP vertical** — um módulo por segmento, multi-tenant, NF-e via gateway. O grupo econômico do Raphael é o cliente piloto.

## Status: EM CONSTRUÇÃO

O gatilho (maturidade do MMX Gestão) foi acionado em **01/08/2026**. Existe código rodando, publicado e testado. O planejamento já foi feito — a planta está em `sistema/documentacao/` (51 documentos, comece pelo `INDICE_MESTRE.md` e pelo `PLANO_MESTRE_CONSTRUCAO.md`, que é o dono único de prazo, preço e ordem).

- **Código:** `sistema/` · repo privado `girf52/saas-erp-vertical`, branch **`main`**
- **Nuvem:** Supabase `ucflgecidugtolzplojg` (sa-east-1) · Vercel **`saas-erp-vertical-psi.vercel.app`** · CI no GitHub Actions
- **A Vercel mora na conta pessoal** (`garcia.couto90@gmail.com`), a mesma do GitHub `girf52` — é o que faz o deploy automático a cada push funcionar. O projeto no time `girf` ficou para trás: plano Hobby não faz colaboração em repositório privado, então todo commit era recusado como "autor externo". Voltar para o time só quando houver Pro
- **Estado em 05/08/2026:** 39 migrações, 513 testes verdes. **Onda 1 fechada no que não depende de contrato com terceiro**: pessoa → produtos/grade → estoque → vendas → categoria financeira/DRE → financeiro (títulos) → compras → OS/serviços → crediário → esqueleto fiscal → regime tributário (dual, com Simples híbrido) → conciliação bancária → relatórios/exportação → entrada de nota inteligente → migração assistida → GED
- **Travado por relógio externo (não por código):** emissão real de nota (contrato de gateway + certificado A1 + credenciamento SEFAZ), conteúdo tributário de presumido/real, BankingGateway (middleware bancário), TEF por adquirente
- **Estado em 06/08/2026:** 45 migrações, 533 testes verdes. **Telas auditadas** — 20 das 22 rotas percorridas com dado real; ficaram de fora só os três passos intermediários de `entrar`, que exigem segundo fator em curso. Oito defeitos achados e corrigidos, três viraram guarda (`mensagens`, `revogacao`, `relatorios_catalogo`)
- **Telas (05/08/2026):** o núcleo tem interface — caixa de entrada, cadastros (pessoa/produto/migração), vender, comprar (XML), financeiro (títulos/baixa/contas) e relatórios com exportação. 23 rotas. Tudo renderizado no servidor, formulários que postam, zero acesso ao banco pelo navegador
- **Estado em 07/08/2026 — Onda 2 construída:** 58 migrações, 619 testes verdes, 29 rotas, 10 seções no menu. Semana 0 (guarda ampliada) → produção/corte → expedição → CRM → PDV online → motor de nesting. Tudo no ar, semeado na nuvem e **percorrido com dado real** — o PDV foi testado de ponta a ponta pelo dono: abrir caixa → venda → troco → concluir
- **Segundo fator não vale em tenant de demonstração** (07/08/2026). A regra segue inteira para cliente real; o escopo é que mudou. Foi consequência de dar todas as capacidades ao papel da demonstração — **capacidade carrega exigência junto**, e três delas disparam MFA. Reverter é apagar o `and not t.demonstracao` em `interno.exige_mfa`
- **Tela não lê `interno.usuario` direto** — a tabela lista todas as pessoas de todos os clientes e não tem `tenant_id` para a RLS filtrar. Use `interno.quem_sou()` ou `interno.sessao_aberta()`. A regra existia só num comentário do `layout.tsx` e foi violada pela tela do PDV a um arquivo de distância; agora `testes/telas.test.ts` quebra o build
- **Estado em 07/08/2026 — Fase 9 fechada (contabilidade):** 61 migrações, 661 testes verdes, 33 rotas. Escrituração (partidas dobradas conferidas pelo banco), o ciclo (**provisório se cancela e some; definitivo se ESTORNA**, com espelho de sinal invertido, e os dois ficam), o motor (`contabilizar()` idempotente por origem, o lançamento nasce do documento), competência que recusa fechar com rascunho dentro, balancete/razão/DRE contábil, e o **painel do contador** — a segunda travessia de tenant deliberada, pelo mesmo consentimento do login, devolvendo contagens e nunca valores
- **`trocar_empresa` existe** (07/08/2026): trocar de empresa sem sair. O seletor de empresa vive numa pré-sessão do login, então quem já está dentro não o alcança. A função emite selo novo pelo MESMO caminho — identidade de `current_usuario()`, direito conferido por `emitir_sessao_usuario`
- **DÍVIDA ABERTA, de segurança:** a armadilha 4 (abaixo) é **sistêmica**. Foi corrigida só na contabilidade e em `revogar_consentimento`. O levantamento aponta ~81 funções `definer` nos outros módulos (venda, financeiro, PDV, expedição, produção, GED, migração, CRM) alcançando linha por id sem filtro. Provado com o banco: a RLS esconde `limite_credito` do outro cliente e `interno.limite_disponivel(pessoa_alheia)` devolve o limite dele mesmo assim. Exige id vazado, e `interno.exigir()` não protege — ele confere capacidade no contexto de quem chama, não sobre a linha alvo. **É a próxima onda, antes da folha**
- **A seguir:** a fronteira do tenant nas funções definer (acima), local-first do PDV (adiado pelo dono até a maturidade do projeto), folha essencial
- **Sem dependência nova, de propósito:** parser de XML (`lib/xml.ts`), leitor de NF-e (`lib/nfe.ts`), escritor de XLSX (`lib/exportar.ts`), leitor de CSV (`lib/importar.ts`), conferência de upload (`lib/arquivo.ts`)

## Regras do usuário

- Responder sempre em **português brasileiro**.
- **NÃO misturar projetos.** Este é isolado do MMX, do APP Beleza e de qualquer outro. Nunca citar dados de outro projeto aqui.
- **Política de entrega:** sanar todas as dívidas antes de fechar uma etapa, sem deixar remendos. Backup depois que estiver limpo.
- Ao propor uma estratégia, reavaliar criticamente antes de implementar — o usuário cobra isso, e já retirei propostas por causa dessa cobrança.

## Antes de mexer no banco

Quatro armadilhas do Postgres que já custaram caro aqui e voltam a cada migração nova:

1. **`CREATE FUNCTION` concede EXECUTE a `PUBLIC`.** Um `revoke ... from <papel>` não tira nada. Desde 07/08/2026 a cura é uma linha no fim do arquivo: `select interno.fechar_para_public();`
2. **`ALTER DEFAULT PRIVILEGES` (migrações 0004/0005) faz toda tabela nova em `public` nascer gravável** pelos papéis da aplicação. Todo migration novo precisa do bloco explícito de `revoke`/`grant`.
3. **`revoke update (coluna)` não restringe um grant de tabela inteira.** Revogue a tabela e conceda coluna a coluna.
4. **`security definer` roda como o dono, e o dono tem `BYPASSRLS`: dentro dessas funções a RLS NÃO filtra nada.** (07/08/2026) Um `where id = $1` numa função definer alcança a linha de **qualquer cliente**. Toda função que recebe id de linha de negócio precisa do filtro escrito à mão — `empresa_id = interno.current_empresa()` para o que é da empresa, `tenant_id = interno.current_tenant()` para o que é do tenant. O padrão está em `interno.revogar_consentimento` e nas funções da contabilidade.

E: quem faz `revoke execute on all functions in schema interno from public` derruba os grants das migrações anteriores — reabra a lista inteira no fim do arquivo.

**Um cliente só no banco não prova isolamento.** A armadilha 4 passou por 19 testes verdes porque só existia um tenant com plano de contas — `select ... into` pegava a linha certa por sorte. Suíte que fala de fronteira precisa de **dois** clientes com a mesma configuração, e o teste tem de ser determinista (evento que só o vizinho tem), não "confere de quem veio a linha".

**`to_char` com `G` e `D` segue o `lc_numeric` do servidor, que aqui é `C`** — mensagem de dinheiro saía "100.00" em tela portuguesa. Use `interno.dinheiro_br(cents)`, que usa separadores literais.

Rotina ao fechar uma etapa: `npx.cmd supabase db reset --no-seed` → `npx.cmd tsc --noEmit` → `npm test` → commit → push → CI → `npx.cmd supabase db push`.

**A guarda olha INSERT e UPDATE** (desde 06/08/2026). Olhava só UPDATE, e foi assim por toda a Onda 1: as 67 colunas derivadas estavam protegidas contra alteração e abertas para criação — que é a metade que importa, porque o número errado nasce com a linha. Gravei R$ 999.999,99 no total de uma venda sem item nenhum com a guarda verde. Ao abrir o olho ela acusou **128 violações**, incluindo a prova do aceite do crediário e o `sha256` do GED.

Daí saíram dois conceitos que o registro não separava:

- **`momento = 'nunca'`** — calculada por nós (`venda.total_cents`). A aplicação não escreve em tempo nenhum.
- **`momento = 'na_criacao'`** — fato externo gravado uma vez (`movimento_bancario.valor_cents`, `documento_fiscal.chave`). Quem importa precisa gravar; ninguém edita depois. São **5** e a lista é conferida por teste — `na_criacao` é exceção justificada, não porta de saída.

E **`interno.tabela_historico`**: livro-razão não aceita UPDATE nem DELETE. `movimento_bancario` aceitava DELETE e ninguém via, porque nenhuma regra perguntava.

**Coluna derivada entra em `interno.coluna_derivada`.** A guarda `interno.auditar_padroes()` roda no teste e quebra o build se alguma delas estiver gravável — foi ela que pegou 18 colunas abertas no fim da Onda 1, incluindo a prova do aceite do crediário. Se `testes/padroes.test.ts` falhar, ou faltou um `revoke` na migração nova, ou a coluna derivada não foi registrada. Não "ajustar o teste".

**Revisão de fim de onda** (prática adotada em 05/08/2026): antes de fechar cada onda, rodar a auditoria, sondar o que ela ainda não cobre e transformar todo achado repetível em regra da guarda.

**A revisão do banco não cobre as telas** (aprendido em 06/08/2026). A auditoria olha esquema; ela não abre uma página. Percorrer as 22 rotas com dado real achou 8 defeitos que 521 testes não pegavam — inclusive uma sessão que sobrevivia à revogação de acesso e dois relatórios que nunca funcionaram. Duas regras que saíram daí:

1. **Semear um cenário com movimento antes de conferir tela.** Tela vazia esconde defeito: formatação de dinheiro, soma, ordenação e faixa de atraso só erram quando há linha. O cenário está em `scripts/cenario.ts` e é semeado pelas MESMAS funções que a tela usa — `insert` no que é derivado cria um banco que a aplicação nunca produziria.
2. **Guarda que nunca falhou não prova nada.** Toda guarda nova é verificada quebrando o código de propósito antes de consertar. Uma delas "falhou" por erro meu de harness e precisou ser refeita — falha por engano do teste não é prova.

## Arquitetura que não se desfaz

- **Contexto selado, não JWT.** `interno.current_tenant()` só aceita tenant acompanhado de selo HMAC cujo segredo mora em `interno`. Claim de JWT não é fonte aceita.
- **RLS com `force row level security`** em toda tabela de negócio, nunca filtro na aplicação. `interno.verificar_isolamento()` quebra o build se uma tabela nova nascer desprotegida.
- **Dado derivado não se escreve.** Saldo deriva do movimento; total da venda, dos itens.

## Stack

Next.js 16 + React 19 + Supabase + RLS. Dinheiro em centavos inteiros; quantidade em `numeric(18,4)`. Pooler de transação (6543) para a app, pooler de sessão (5432) para os testes.

**`DATABASE_URL` não conecta sozinha.** A senha vem separada em `DATABASE_PASSWORD` e é embutida na URL por `lib/conexao.ts`, codificada — senha de gerenciador tem `#`, `@` ou `%`, que quebrariam a URL. Faltando a variável, o `pg` recebe `undefined` e devolve `SASL: client password must be a string`. Já derrubou a semeadura na nuvem e o primeiro deploy na Vercel. Ao configurar ambiente novo, as duas variáveis andam juntas — e a porta é 6543, não a 5432 do `.env.nuvem`.

**Mensagem de erro em ação de servidor usa `falhar()` de `lib/tela`**, nunca `redirect('...?erro=')` na mão. Sem `revalidatePath` antes, o Next devolve o RSC que já tinha da rota: a URL muda e a tela não — o erro some, ou herda o aviso verde da tentativa anterior e diz "salvo" depois de uma recusa. `testes/mensagens.test.ts` quebra o build se alguém voltar a montar na mão.
