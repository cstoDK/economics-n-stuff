# DRI: Gratis AI-redaktion

Dette setup bruger **ChatGPT Plus-opgaven, som brugeren allerede betaler for**, til research. Ingen OpenAI API-nøgle og ingen ekstra udgift til AI-research.

## Kæden

1. ChatGPT Scheduled Task "DRI: Gratis AI-redaktion" skriver et research- og faktakontrolleret opslag.
2. Den samme ChatGPT-opgave opretter via allerede tilsluttet GitHub-app `dri/incoming/YYYY-MM-DD.json`.
3. Denne GitHub Actions-workflow starter ved en ny JSON-fil. Koden validerer kildehenvisninger og datoer, finder et frit licenseret arkivfoto hos Wikimedia Commons eller bygger en tydeligt illustreret forside på 1080 × 1350 px.
4. Den færdige billedfil ligger på GitHub, og et opslag med billedet oprettes som **Buffer draft**, aldrig automatisk publiceret.
5. Redaktøren finpudser og publicerer selv fra Buffer.

## De eneste brugertrin, der mangler

- Opret en gratis konto på https://buffer.com (gratisplan med op til 3 kanaler, ubegrænsede kladder).
- Forbind Facebook-siden Den Rationelle Investor i Buffer.
- Gå til https://publish.buffer.com/settings/api og opret den gratis personlige **Buffer API-nøgle**.
- Gå til https://github.com/cstoDK/economics-n-stuff/settings/secrets/actions og opret en secret med navnet **BUFFER_API_KEY**. Indsæt nøglen dér, ALDRIG i chatten eller i en GitHub-fil.
- Normalt identificerer botten automatisk Facebook-kanalen. Hvis ikke: Tilføj kanalen som **BUFFER_CHANNEL_ID** under samme Secrets-side.

**Der skal IKKE oprettes eller indsættes `OPENAI_API_KEY`.** Den gamle kode i `dri/bot.py` indeholder en ikke-aktiveret OpenAI-genereringsfunktion, som den gratis arbejdsgang IKKE bruger.

## Realistiske begrænsninger

- ChatGPT Scheduled Tasks kan bruge tilsluttede apps, men en bestemt planlagt kørsel kan stadig kræve tilladelse for at udføre GitHub-skrivehandlinger. Test én automatisk kørsel, før du regner med, at overførslen er fuldt selvkørende.
- Repoet `cstoDK/economics-n-stuff` er **offentligt**: Opslagets ufærdige tekst og det genererede billede er derfor synlige i GitHub før offentliggørelse på Facebook. Brug ikke fortroligt materiale i opslagene. Vi kan senere flytte til et privat repo.
- Billedet er enten tydeligt krediteret arkivfoto, hvis rettighederne godkendes, eller en original illustration. Ingen Reuters-fotos bruges uden rettighed.
- Koden tjekker skema, kildernes domæner, datoer og billedlicens, men kan **ikke selv udføre et yderligere uafhængigt AI-faktatjek**. Fakta gennemgås af ChatGPT under researchen, og endelig ansvar ligger hos redaktøren.
- Facebook publiceres **aldrig uden godkendelse**.
- GitHub Actions og Buffer Free har brugsgrænser, men dette normale 6-opslag/uge-forløb ligger langt under Buffers månedlige API-grænse. Ingen planlagt betalt API-forbrug.
- Den aktuelle workflow trigges KUN når en ny `dri/incoming/*.json` oprettes eller ved manuel genstart. Den kører ikke selv research, og GitHub bruger ikke OpenAI API.

## Test

Når Buffer API-nøglen er tilføjet, kan næste planlagte ChatGPT-kørsel oprette den første `dri/incoming/YYYY-MM-DD.json`. Kontroller at kørsel og kladde vises i:

- https://github.com/cstoDK/economics-n-stuff/actions/workflows/dri-editorial.yml
- https://publish.buffer.com/

Ved fejl fungerer ChatGPTs eget svar stadig som backup, klar til copy/paste.

## Tekniske filer

- `dri/from_chatgpt.py`: lokal kontrol og Buffer draft
- `.github/workflows/dri-editorial.yml`: gratis automatisering
- `dri/bot.py`: hjælpefunktioner til licensfoto, design og Buffer API
