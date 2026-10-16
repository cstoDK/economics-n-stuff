# Den Rationelle Investor: redaktionsbot

Automatisk research, faktatjek, en vertikal 1080×1350-forside og en **ikke-publiceret** Buffer-kladde. Kører mandag-fredag og søndag cirka kl. 07.35 dansk tid.

## Opsætning

1. Opret Buffer-konto på https://buffer.com og forbind Facebook-siden Den Rationelle Investor.
2. Opret en personlig API-nøgle i Buffer: https://publish.buffer.com/settings/api
3. Opret en separat OpenAI API-nøgle på https://platform.openai.com/api-keys. ChatGPT-abonnement giver ikke i sig selv API-kredit.
4. Indsæt nøglerne som GitHub Actions-secrets **BUFFER_API_KEY** og **OPENAI_API_KEY** her: https://github.com/cstoDK/economics-n-stuff/settings/secrets/actions . Del dem aldrig i chat eller kode.
5. Gå til https://github.com/cstoDK/economics-n-stuff/actions/workflows/dri-editorial.yml og vælg Run workflow, når secrets er tilføjet. Hvis din kanal ikke genkendes entydigt, skal BUFFER_CHANNEL_ID tilføjes som en tredje secret.

Forsiden er et licenseret *arkivfoto* fra Wikimedia Commons med rettighedsangivelse eller en tydeligt original grafisk illustration. Et arkivfoto må ikke omtales som et billede fra dagens nyhed.

Et uafhængigt andet AI-kald gennemgår fakta og kilder. Hvis kvalitetskontrollen afviser opslaget, oprettes ingen Buffer-kladde. **Publicering foretages kun manuelt fra Buffer.**

Programmet ligger i dri/bot.py. Workflowet ligger i .github/workflows/dri-editorial.yml.

## Omkostning og sikkerhed

OpenAI API faktureres særskilt efter forbrug og websearch; gennemfør testkørsler og sæt et budget i OpenAI Platform. Der er også gældende forbrugsgrænser for Buffer og GitHub Actions. Kode og billeder ligger i et offentligt GitHub-repository. API-nøgler må kun ligge som GitHub Actions-secrets.

## Bemærk

Automatiseret nyhedsresearch kan fejle eller fejlfortolke kilder. Du er redaktør og godkender altid fakta, kilder, billedret og sluttekst, før du trykker Publish. Hvis formatet også kører som ChatGPT-automation, så slå den ene strøm fra efter end-to-end-test for at undgå dubletter.
