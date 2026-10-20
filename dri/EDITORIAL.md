# Kontrakt for den eksisterende ChatGPT-opgave

Tid: mandag–fredag og søndag 07.30 Europe/Copenhagen, aldrig lørdag.
Brug kun inkluderet ChatGPT-webresearch, ingen betalte API'er.

1. Læs først dagens `dri/incoming/YYYY-MM-DD.json` og `dri/state/YYYY-MM-DD.buffer-id`
   eller `.delivery.json`. Eksisterende fil/kvittering/reservation: opret ikke igen.
   Ved uklar tidligere levering: stop og rapportér afstemningsbehov.
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

Brug åbne HTML-kilder på domæner tilladt i `dri/bot.py`. Workflow genhenter uddraget.
Et uddrag er et kontrollerbart kildebevis, ikke dokumentation for alt i sig selv.
Dæk alle påstande i den redaktionelle gennemgang. Daglige datoer: højst tre dage
gamle; søndag: højst ni. Ingen fremtidige hændelser som allerede indtrufne fakta.

Skriv gennem GitHub-connectoren til `cstoDK/economics-n-stuff`, main, den ene
incoming-fil. Opdater ikke kode, workflow eller state fra research-opgaven.
Kontrollér faktisk filindhold/commit og den tilhørende Actions-kørsel.
Rapportér kun Buffer-succes ved konkret kladde-ID og status, aldrig ud fra en
filskrivning alene. Hvis noget fejler, giv præcis blokering og kørselslink.
Ingen automatisk publicering, scheduling i Buffer eller automatisk genforsøg
efter usikker levering. Ingen kopier af samme opgave eller ekstra tidsplaner.
