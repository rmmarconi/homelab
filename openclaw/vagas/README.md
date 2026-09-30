# 💼 Agente `vagas`

Busca vagas em fontes públicas, avalia contra o currículo e as preferências do Rafael e, para as que passam
(nota ≥ 75), escreve um currículo sob medida — **sem inventar nem omitir** — no idioma da vaga, gera o PDF e
envia no Telegram com o link para aplicar. Nunca se candidata nem fala com recrutadores.

- `AGENTS.md` → `~/.openclaw/workspace/agents/vagas/AGENTS.md` (fluxo, regras de verdade e de "cara de gente").
- `bin/` → `~/.openclaw/tools/vagas/bin/`:
  `vg-buscar` (LinkedIn público, Gupy, Remotive, RemoteOK, We Work Remotely, Jobicy, Arbeitnow),
  `vg-descricao`, `vg-importar-cv`, `vg-pdf` (Chromium headless + Inter), `vg-enviar` (Telegram, PDF como documento).
- `templates/curriculo.html` — modelo de uma coluna, compatível com ATS, até 2 páginas A4.
- `main-vagas.md` — anexado ao AGENTS.md do `main`, que repassa currículo/preferências/feedback ao `vagas`.
- Rotinas: busca em dias úteis às 8h e 15h; resumo semanal sexta 17h.
- Dependências na VM: `poppler-utils`, `fonts-inter`, `libasound2t64` (Chromium do Playwright).
- Dados pessoais (currículo, fatos, preferências) ficam só no workspace, com permissão 700/600, **fora do git**.
