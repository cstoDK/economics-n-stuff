# DRI-redaktionen

Opgaven undersøger historier mandag til fredag og søndag kl. 07.30 dansk tid. Udgiv højst tre gange inden for syv kalenderdage og spring kørselen over, når der ikke er en stærk historie. Brug inkluderet webresearch og den tilsluttede GitHub-app. Den eksisterende kæde udgiver automatisk på Facebook efter bestået kontrol.

## Vælg én historie

- Find en ny, konkret beslutning, regelændring eller udvikling, der flytter noget for en dansk opsparer. Prioritér Danmark og Europa. Se efter incitamenter, markedsstruktur, pension, omkostninger, hvem der får gevinsten, og hvem der betaler. En kursbevægelse eller en samling almindelige nøgletal er ikke en historie i sig selv.
- Åbn de seneste 30 dages `dri/state/*.publication.json` og tilhørende `dri/incoming/*.json`. Kontrollér, at vinkel, rubrik og foto tilfører noget nyt. En opfølgning kræver en faktisk ny beslutning eller konsekvens.
- Skriv ét sammenhængende opslag på 260–550 ord. Navngiv den konkrete aktør og beslutning tidligt. Forklar mekanismen trin for trin, brug præcise tal og korte afsnit, og vis den håndgribelige konsekvens for læseren. Giv en modforklaring, når den ændrer vurderingen. Slut nøgternt. Søndag kan samle flere udviklinger, hvis de forklarer samme pointe fra den afsluttede uge.
- Undgå faste nummererede nyhedsoversigter, gentagne indledninger, skabelonafslutninger, reklamesprog, emojis, tankestreger og udråbstegn. Opfind aldrig personlige oplevelser, beholdninger, anbefalinger eller citater på afsenderens vegne. Hvis rubrikken eller mekanismen kan flyttes direkte til en anden historie, så omskriv eller spring over.
- Se det konkrete foto på Wikimedia Commons. Vælg et dokumentarfoto af et specifikt sted, en aktør eller et objekt i historien. Billedet skal have en tydelig redaktionel funktion, mindst 850 × 650 px og fri licens CC BY, CC0 eller public domain med ophavsangivelse. Brug et præcist `File:`-navn i JPEG, PNG eller WebP. Arkivfoto skal fremstå som arkivfoto. Spring over, hvis kun et generisk børsfoto, en aktiekurve, et AI-billede eller et tidligere brugt foto passer.

## Gennemgå den færdige tekst og det valgte foto

Gennemfør først et separat faktatjek. Åbn 2–5 forskellige, direkte og maskinlæselige HTML-kilder fra domæner tilladt i `dri/bot.py`. Vælg primærkilder til de centrale udsagn. Kontrollér tal, datoer, navne, beslutninger og citater. Skeln mellem begivenhed og kildeudgivelse samt mellem fakta og fortolkning. Hændelses- og kildedato skal ligge højst tre dage tilbage på hverdage og højst ni dage tilbage søndag. En fremtidig hændelse må ikke være beskrevet som indtruffet.

Gennemfør derefter en separat redaktionel gennemlæsning af præcis den færdige tekst og det præcise billede. Begrund konkret hvad der er nyt, hvilken mekanisme teksten forklarer, hvad læseren får ud af den, og hvorfor netop dette foto hører til. Et manglende eller svagt svar stopper leveringen.

## JSON ved bestået kontrol

- `date` er dagens dato i København, `mode` er `daily` på hverdage eller `weekly` søndag, og `approved` er boolsk `true`.
- `facebook_text` er den færdige tekst med en selvstændig rubrik på første linje. Brug almindelig tekst uden URL’er eller kildetags.
- `sources` indeholder 2–5 objekter med `headline`, `urls`, `event_date`, `source_date`, `core_fact` og `evidence`. Hvert `evidence` har en direkte læst `url` fra `urls`, `verified: true`, `checked_at` som dagens ISO-tid med dansk tidszoneoffset, et ordret `excerpt` på mindst 20 tegn og højst 25 ord samt `supported_claims` med kontrollerede påstande. Kørselen genhenter de nøjagtige uddrag og stopper ved afvigelser. Et uddrag erstatter aldrig kontrollen af den fulde tekst.
- `verification` har `status: "passed"`, `method: "independent_source_review"`, `reviewed_text` som en nøjagtig kopi af `facebook_text` og `unresolved_claims: []`.
- `editorial` har `status: "passed"`, `story_key`, `new_development`, `mechanism`, `reader_relevance`, `image_relevance` og `photo_file`. Brug en stabil, specifik nøgle på 3–10 led adskilt af bindestreger med små ASCII-bogstaver og tal. Brug samme nøgle for samme begivenhed, også ved en ny rubrik. Hver af de fire begrundelser er en konkret sætning på 20–500 tegn. `photo_file` er det præcise Commons-filnavn inklusive `File:`, uden URL, fragment eller billedtekst.
- `cover_title` og `cover_subtitle` er korte og konkrete, henholdsvis 8–60 og 8–80 tegn, på én linje hver.

## Aflever og kontrollér

1. Se efter dagens `dri/incoming/YYYY-MM-DD.json`, `dri/state/YYYY-MM-DD.buffer-id`, `.delivery.json` og `.publication.json` før en filskrivning. En kvittering eller reservation betyder stop. Eksisterende input uden reservation må kun rettes én gang efter bekræftet, afsluttet validerings- eller kildefejl før Buffer. Brug den aktuelle blob-SHA og kør hele kontrollen igen. Uklar leveringsstatus betyder stop og afstemning.
2. Ved bestået kontrol afleveres den ene UTF-8-JSON-fil i `dri/incoming` på `main` i `cstoDK/economics-n-stuff` gennem GitHub-appen. Opgaven må kun skrive denne fil.
3. Genlæs fil og commit. Find kørselen via `https://api.github.com/repos/cstoDK/economics-n-stuff/actions/runs?head_sha=COMMIT_SHA`, derefter jobs og logs. Vent kort og tjek igen, hvis kørslen endnu ikke er synlig. Kontrollér den faktiske `.publication.json`. Rapportér kun offentliggjort ved `sent` med Buffer-ID og `sent_at`. Medtag Facebook-linket, når det findes. Ved teknisk fejl rapporteres den præcise blokering og kørslens link. Ved redaktionelt fravalg oprettes ingen fil, og resultatet kan holdes til én linje.
