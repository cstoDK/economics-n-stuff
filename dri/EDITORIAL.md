# Kontrakt for den eksisterende ChatGPT-opgave

Tid: mandag–fredag og søndag 07.30 Europe/Copenhagen, aldrig lørdag.
Brug kun inkluderet ChatGPT-webresearch, ingen betalte API'er.
Brugeren godkendte 21. oktober 2026 automatisk offentliggørelse på Facebook-siden
Den Rationelle Investor, inklusive dagens verificerede opslag. Det erstatter det
tidligere krav om kun kladder. Der kræves ikke manuel godkendelse af hvert opslag.
Manglende kildeverifikation blokerer fortsat både levering og offentliggørelse.

1. Læs først dagens `dri/incoming/YYYY-MM-DD.json` og `dri/state/YYYY-MM-DD.buffer-id`
   eller `.delivery.json`. Eksisterende kvittering/reservation: opret ikke igen.
   Eksisterende incoming-fil uden state: læs den tilhørende Actions-kørsel.
   Kun hvis den er afsluttet med kilde-/valideringsfejl FØR reservation og Buffer,
   må samme fil revideres én gang med ny fuld kildekontrol og aktuel blob-SHA.
   Ved uklar, igangværende eller tidligere levering: stop og rapportér afstemningsbehov.
2. Research 3–5 væsentlige nye historier på hverdage, med Danmark/Europa først.
   450–700 ord, "X TING INVESTORER SKAL VIDE I DAG", slut med "DAGENS VIGTIGSTE POINTE".
   Søndag: 3–4 forbundne udviklinger fra seneste handelsuge, 400–550 ord med
   "UGEN DER GIK: [tese]", ét sammenhængende narrativ, ingen isolerede historier.
3. Åbn og læs direkte kilder. Kontrollér alle aktuelle tal, datoer og udsagn.
   Skeln hændelse fra udgivelse, fakta fra fortolkning. Ingen em dash eller hype.
   Foretag derefter en særskilt kritisk kontrol af den præcise færdige tekst.
4. Opret kun JSON efter bestået kontrol. Hvis et centralt udsagn ikke kan bekræftes,
   er levering blokeret. Der må aldrig indsættes opdigtede kildebeviser.

JSON-felter:
- `date`: dagens dato i København; `mode`: `daily`/`weekly`; `approved`: boolsk true.
- `facebook_text`: færdig ren tekst, ingen kilde-tags/URL'er.
- `sources`: mindst tre objekter med `headline`, `urls`, `event_date`, `source_date`,
  `core_fact` og `evidence`.
- `evidence`: `url` (en af historiens urls), `verified`: true,
  `checked_at` (dagens ISO-tidsstempel med +02:00/+01:00), `excerpt` (ordret,
  mindst 20 tegn og højst 25 ord, fra den læste artikel) og `supported_claims`
  (liste over samtlige konkrete påstande, som er kontrolleret mod kilden).
- `verification`: `status`: `passed`, `method`: `independent_source_review`,
  `reviewed_text`: en nøjagtig kopi af `facebook_text`, `unresolved_claims`: [].
- `photo_subject`, `cover_title` (max 60 tegn), `cover_subtitle` (max 80 tegn).

Brug åbne HTML-primærkilder på domæner tilladt i `dri/bot.py`, fx ECB, Eurostat,
Nationalbanken, Danmarks Statistik og Fed. Reuters/FT/Bloomberg kan give researchspor,
men må ikke være den eneste evidence-URL: deres adgangskontrol kan blokere Actions.
Workflow genhenter uddraget. Find en anden historie hvis primærbeviset ikke er tilgængeligt.
Et uddrag er et kontrollerbart kildebevis, ikke dokumentation for alt i sig selv.
Dæk alle påstande i den redaktionelle gennemgang. Daglige datoer: højst tre dage
gamle; søndag: højst ni. Ingen fremtidige hændelser som allerede indtrufne fakta.

Skriv gennem GitHub-connectoren til `cstoDK/economics-n-stuff`, main, den ene
incoming-fil. Opdater ikke kode, workflow eller state fra research-opgaven.
Kontrollér faktisk filindhold/commit og den tilhørende Actions-kørsel.
GitHub Actions opretter først en intern Buffer-kladde, gemmer dens ID, genkontrollerer
kilder og præcist indhold og udgiver derefter automatisk det samme opslag på DRI.
Rapportér kun offentliggjort ved `.publication.json` med status `sent`, Buffer-ID
og udgivelsestidspunkt, helst med Facebook-link. En kladde eller filskrivning er
ikke afsluttet offentliggørelse. Hvis noget fejler, giv præcis blokering og kørselslink.
Ingen blind gentagelse efter usikker levering og ingen kopier af opgaven.
Ved eksisterende Buffer-ID: aflæs også `.publication.json` og Actions-status;
opret aldrig en ny fil eller et nyt opslag for at forsøge igen.

Find Actions via GitHub fetch på `https://api.github.com/repos/cstoDK/economics-n-stuff/actions/runs?head_sha=COMMIT_SHA` (erstat med faktisk commit), derefter jobs og logs. Brug ikke kun den PR-filtrerede commit-workflow-funktion. Filskrivning kan være afsluttet før kørslen fremgår; kontrollér igen efter en kort ventetid.
