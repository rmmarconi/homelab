# Preferência de áudio (Radarr e Sonarr) — 2026-10-24

O Seerr só cria o pedido; quem escolhe o lançamento é o Radarr/Sonarr, no perfil
**HD - 720p/1080p** (id 6, o que o Seerr usa). Configurado por Custom Formats:

| Custom Format | Condições | Pontos |
|---|---|---|
| Áudio original | idioma = Original (do filme/série) | +100 |
| Áudio PT-BR (dublado) | nome casa `(?i)\b(dual[ ._-]?(audio\|áudio)?\|dublado\|dub\|nacional\|multi\|portugu[eê]s\|pt[ ._-]?br)\b` **e** não contém `legendado` (as duas obrigatórias) | +50 |
| Legendado (já existia) | `legendado` ou `pt-br` no nome | 0 |

Resultado: **dual áudio = 150** (preferido) > só original = 100 > só dublado = 50.
Perfil com upgrade ligado até 150: se aparecer depois uma versão dual áudio de algo já
baixado, ele troca (só via RSS, sem busca em massa). Nota mínima 0: nada é bloqueado.

No Radarr o idioma do perfil é **Original**: lançamento só dublado (sem o áudio original)
continua recusado para filmes. No Sonarr não há essa trava (só dublado entra com 50 se for o único).

Testado com `/api/v3/parse` (Coyote vs. Acme, Silicon Valley).
Pegadinha: condições do mesmo tipo são "OU" entre as opcionais, então uma condição negada
sozinha satisfaz o grupo — por isso as duas do nome são obrigatórias.
