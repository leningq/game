# Brickfall — spēles dizains

## Nosaukums un žanrs

Brickfall ir vienkārša 2D Breakout arkādes spēle Python un Pygame vidē.
Pamats ir sākotnējais skolas darba dokuments `Dizains.docx`.

## Mērķis

Iznīcināt visus ķieģeļus un pabeigt trīs līmeņus. Spēlētājam ir trīs dzīvības.
Kad bumbiņa nokrīt zem platformas, pazūd viena dzīvība.
Pēc trešā līmeņa ir uzvara; pēc visu dzīvību zaudēšanas spēle beidzas.
Priekšnieka, robota un papildu debufu nav.

## Vadība

| Taustiņš | Darbība |
| --- | --- |
| ← / → vai A / D | Platformas kustība |
| Space | Bumbiņas palaišana |
| Shift | Bumbiņas palēnināšana |
| P | Pauze / turpināt |
| Esc | Pauze; pauzes ekrānā — galvenā izvēlne |
| F5 | Apturēt un saglabāt spēli |
| F9 | Ielādēt saglabājumu izvēlnē vai pauzē |

Sākotnējā dokumentā Space bija palēnināšanas taustiņš.
Atbilstoši jaunajai prasībai Space palaiž bumbiņu, bet Shift palēnina to.

## Spēles cikls un līmeņi

Spēlētājs piesakās → izvēlas jaunu spēli → palaiž bumbiņu →
atsit to ar platformu → iznīcina ķieģeļus → saņem punktus.
Par katru ķieģeli ir 10 punktu.
Katram no trim līmeņiem ir savs ķieģeļu izkārtojums.
Nākamajos līmeņos bumbiņas ātrums pieaug.
Līmeņa sākumā un pēc dzīvības zaudēšanas bumbiņa gaida uz platformas.
Atsitiena leņķis atkarīgs no trāpījuma vietas uz platformas.

## Divas īpašās mehānikas

1. Pēc katriem pieciem iznīcinātiem ķieģeļiem platforma kļūst šaurāka
   uz trim sekundēm, pēc tam atgūst parasto platumu.
2. Vienu reizi katrā līmenī ar Shift var palēnināt kustībā esošu bumbiņu
   uz trim sekundēm. Dzīvības zaudēšana šo iespēju neatjauno.

Pauzē spēles kustība un efektu taimeri apstājas.

## Ekrāni un izskats

Pieteikšanās un reģistrācija, galvenā izvēlne, spēle, pauze,
vadības paskaidrojums, uzvara un zaudējums.
Spēlei ir tumšs fons, mierīgas ķieģeļu krāsas, labi redzama platforma
un bumbiņa. Ekrānā redzami punkti, dzīvības, līmenis un mehāniku stāvoklis.
Attēli un nelieli efekti tiek zīmēti ar Pygame.

## Saglabāšana un mājaslapa

FastAPI serveris lieto SQLite. Spēlētājs reģistrējas un piesakās ar vārdu
un paroli. Serverī ir tikai paroles hešs un nejauša sāls.
Pēc pieteikšanās klients saņem autorizācijas tokenu.

Saglabājumā ir līmenis, punkti, dzīvības, ķieģeļi, bumbiņas un platformas
pozīcijas, ātrums, efektu taimeri un spēles identifikators.
Vienam spēlētājam ir viens pēdējais saglabājums.

Pabeigtas spēles rezultāts nonāk tajā pašā datubāzē.
Mājaslapā ir top-10 pēc katra spēlētāja labākā rezultāta, profils ar
statistiku un noteikumi. Mājaslapai ir balts fons, tumša galvene,
vienkārša tabula un pielāgojums nelieliem ekrāniem.
Izdomātu rezultātu nav.

## Projekta sadalījums

`game/` veic aprēķinus bez Pygame.
`client/` atbild par logu, zīmēšanu, vadību un API pieprasījumiem.
`api/` apstrādā HTTP pieprasījumus un SQLite.
`templates/` un `static/` veido vienkāršo mājaslapu.

Sākotnējā ekrāna skice ir `docs/skice.png`.
