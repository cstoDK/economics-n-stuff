# DRI: gratis research → verificeret Buffer-kladde

Den eksisterende ChatGPT-opgave researcher mandag–fredag og søndag kl. 07.30
Europe/Copenhagen. Ingen lørdag. ChatGPT-abonnementets inkluderede research bruges;
OpenAI API-kald og den gamle direkte bot-indgang er deaktiveret i koden.
GitHub Actions bruger gratis HTTP/Pillow og den eksisterende Buffer-nøgle.

## Redaktion og kildebevis

Før skrivning skal ChatGPT læse `dri/EDITORIAL.md`. Én ny fil pr. københavnsk dato:
`dri/incoming/YYYY-MM-DD.json`. En eksisterende fil må ikke automatisk overskrives.
Kun dagens udgave kan leveres. Søndag: 400–550 ord, én tese og sammenhængende narrativ.

`approved: true` alene er utilstrækkeligt. Alle historier kræver direkte URL,
hændelses-/udgivelsesdato og et dokumenteret kildebevis. Et særskilt faktatjek skal
omfatte præcis den færdige Facebook-tekst. Pipeline genhenter hvert kildeuddrag fra
en godkendt kilde; manglende felt, utilgængelig kilde, forkert uddrag, fremtidsdato,
for gammel kilde eller uløste påstande stopper før billedgenerering og levering.

Dette er en mekanisk kontrol af evidens, ikke automatisk semantisk sandhedsbevis.
ChatGPT skal kontrollere ALLE aktuelle tal og påstande, også dem uden for uddraget.
Brug åbne primærkilder. Paywall/anti-bot-blokering stopper levering; find en anden
reel kilde og gennemfør kontrollen igen. Opfind aldrig et uddrag for at bestå.

## Levering og genkørsel

Workflow tester først. Push med incoming-ændring leverer dagens fil. Andre
kodeændringer kører en **læsekontrol** af eksisterende Buffer-kvitteringer.
Manuel kørsel har `audit` som standard og `deliver` som eksplicit mulighed.
Ingen anden research-planlægning oprettes i GitHub.

Pipeline tjekker seneste main, springer gemte Buffer-ID'er over og gemmer en
leveringsreservation + billedet på GitHub **før** Buffer-kaldet. Ved timeout,
nedbrud eller fejl under kvitteringslagring bevares reservationen. En genkørsel
stopper da til afstemning i Buffer, frem for at risikere en dublet. Det giver
højst ét automatisk oprettelsesforsøg pr. dato; det garanterer ikke levering ved
netværksfejl. Slet aldrig en reservation uden først at kontrollere Buffer.
En afvist Git-push må ikke efterfølges af et Buffer-kald.

Buffer modtager altid `saveToDraft: true`, Facebook-type `post`, ingen `dueAt`.
Returstatus skal være `draft`. Billed-URL'en er bundet til en uforanderlig commit.
Kildepakke og kvitteringer gemmes også som Actions-artifact, inklusive ved fejl.

## Billedrettigheder

Kun Commons CC0/PD/standard CC BY vælges. CC BY kræver forfatter og licenslink.
Kreditering, kilde, licenslink og tilpasningsnote følger teksten. Hvis et egnet
foto ikke kan hentes, bruges original grafisk illustration på 1080 × 1350.
Fotooplysninger ligger i kildepakken. Illustration er aldrig en faktisk kursgraf.

## Drift

Secrets: `BUFFER_API_KEY`, eventuelt `BUFFER_CHANNEL_ID`. Eksisterende hemmeligheder
skal blive i GitHub Secrets. Repoet er offentligt; tekst, billeder og registreret
kildebevis kan læses dér. Ingen fortroligt materiale i incoming.

Test: `python -m unittest discover -s dri/tests -v`.
Live læsekontrol: workflow_dispatch → audit. Den skaber eller ændrer ingen kladder.
En fuld ny levering er kun bestået, når den faktiske kildekontrol, billedoprettelse,
Buffer-status og gemte kvittering alle er kontrolleret. Grønne enhedstests alene
beviser ikke, at næste planlagte ChatGPT-kørsel kan skrive via connectoren.
