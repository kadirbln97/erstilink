# ErstiLink.de – Anleitung

Die Website wird aus einer Vorlage erzeugt. Du bearbeitest `src/app.html`, lässt `build.py` laufen — im Ordner `dist/` liegt die fertige Seite, daneben entsteht `admin.html` für die Pflege.

```bash
python3 build.py            # Website nach dist/ bauen + admin.html erzeugen
python3 build.py pruefen    # dist/ auf typische Fehler prüfen
./deploy.sh "Nachricht"     # bauen, prüfen, zu GitHub pushen
```

Keine Installation nötig — nur Python 3, das auf jedem Mac schon da ist.

---

## Warum jetzt ein Generator?

Vorher war alles eine einzige `index.html`, die per JavaScript entschied, welche Uni sie anzeigt. Für Google war das eine einzige Seite. Jetzt bekommt jede Hochschule eine echte Datei mit fertigem Inhalt:

```
dist/uni/berlin-tu/index.html    → erstilink.de/uni/berlin-tu
dist/uni/muenchen-lmu/index.html → erstilink.de/uni/muenchen-lmu
```

Jede mit eigenem Titel („Ersti-Gruppen Berlin (TU) – ErstiLink"), eigener Beschreibung, eigenem Canonical-Tag und strukturierten Daten für Google. Der Inhalt steht direkt im ausgelieferten HTML — kein JavaScript nötig, damit eine Suchmaschine ihn sieht.

Aus einer indexierbaren Seite sind 215 geworden.

---

## 1. Verwaltung — nur lokal

Es gibt kein Admin-Passwort mehr, weil es keinen Online-Admin mehr gibt.

Die Verwaltung liegt in **`admin.html`** in deinem Projektordner. Doppelklick genügt, kein Server, kein Login. `build.py` erzeugt die Datei bei jedem Build neu und `.gitignore` sorgt dafür, dass sie weder in GitHub noch bei Netlify landet.

Warum so: Auf einer statischen Seite läuft alles im Browser des Besuchers. Ein Passwort im JavaScript ist eine Türklinke ohne Tür — der Quelltext liegt offen, die Prüfung lässt sich umgehen. Netlifys echter Passwortschutz gehört zum kostenpflichtigen Pro-Plan. Der Admin gar nicht erst online zu stellen ist kostenlos und sicherer.

`build.py` prüft das automatisch und **bricht den Build ab**, wenn Admin-Code oder ein Passwort in `dist/` landen würde:

```
Sicherheitsprüfung bestanden: kein Admin-Code und kein Passwort in dist/
```

## 2. Konfiguration

Oben in `src/app.html`:

```js
const CONFIG = {
  siteName: "ErstiLink",
  semester: "WiSe 2026/27",
  siteUrl: "https://erstilink.de",
  contactEmail: "kandir1997@googlemail.com",
  storageKey: "erstilink_data_v1",
  legacyKeys: [...],
  betreiber: { name, strasse, ort, land, email, ustId }
};
```

`betreiber` speist Impressum und Datenschutzerklärung — die Angaben stehen an einer Stelle und nicht dreimal im Text.

Wenn ein neues Semester ansteht, änderst du `semester` und baust neu. Der Wert erscheint im Hero, in den Gruppentiteln und in den Anschreiben.

---

## 3. Gruppen eintragen

1. `admin.html` per Doppelklick öffnen
2. Uni suchen → **Gruppen** → **+ Gruppe**
3. Studiengang, Einladungslink, optional einen Zusatz

**Prüfe jeden Link, bevor er live geht.** Als Betreiber haftest du für Verlinkungen, sobald du von einem Rechtsverstoß weißt.

### Änderungen veröffentlichen

Admin-Änderungen liegen im **localStorage deines Browsers** — nur auf deinem Gerät sichtbar. Damit Besucher sie sehen:

1. In `admin.html`: **Seed-Block kopieren**
2. In `src/app.html` den Block `const SEED_UNIS = [ … ];` durch den kopierten ersetzen
3. `./deploy.sh "Was du geändert hast"`

---

## 4. Outreach-Panel

Im Admin-Bereich listet das Panel alle Hochschulen **ohne** Gruppe:

- Status pro Uni: Offen → Angeschrieben → Antwort erhalten → Erledigt
- **Anschreiben kopieren** erzeugt die fertige Fachschafts-Mail
- **CSV exportieren** gibt dir die Liste für Excel oder ein Kanban-Board

Vorlagen und Strategie: `ANSCHREIBEN.md`.

---

## 5. Online gehen

**`START.md`** hat die vollständige Schritt-für-Schritt-Anleitung mit kopierfertigen Befehlen.

Kurzfassung: GitHub-Repo anlegen, mit Netlify verbinden, Domain bei Namecheap zeigen lassen. Danach genügt `./deploy.sh` für jede Änderung — Netlify baut selbst.

---

## Datenbestand

**214 Hochschulen in Deutschland.**

- **Bundesweit:** staatliche Universitäten (82) und staatliche Hochschulen für Angewandte Wissenschaften (103)
- **Berlin:** vollständig — alle 37 Hochschulen, unabhängig von Trägerschaft und Typ

Quellen: Wikipedia-Gesamtliste auf Basis von Hochschulkompass-Daten für Namen, Trägerschaft und Typ. Die Charité wurde von Hand ergänzt, weil sie dort als gemeinsame Fakultät von FU und HU geführt wird.

Jeder Eintrag hat Anzeigenamen, offiziellen Namen, Bundesland, Hochschultyp und Trägerschaft. Die Suche greift auf Anzeigename und offiziellen Namen zu — wortweise, deshalb findet „berlin tu" ebenso wie „tu berlin".

Einschränkungen: Die Quelle stammt aus 2022, Neugründungen seit 2023 können fehlen. Bei rund 15 Einträgen ist das Kürzel zulässig, aber nicht das gebräuchlichste.

---

## Dateien

### Quellen (bearbeitest du)

| Datei | Zweck |
|---|---|
| `src/app.html` | die Anwendung: Aussehen, Logik, Daten, Rechtstexte |
| `build.py` | Generator |
| `deploy.sh` | bauen, prüfen, veröffentlichen |
| `og.png`, `favicon.png`, `apple-touch-icon.png` | Bilder |
| `robots.txt`, `_redirects`, `_headers`, `netlify.toml`, `CNAME` | Hoster-Konfiguration |

### Erzeugt (Netlify baut das selbst)

| Pfad | Inhalt |
|---|---|
| `dist/index.html` | Startseite mit allen 214 Unis |
| `dist/uni/<slug>/index.html` | 214 Einzelseiten |
| `dist/impressum/`, `dist/datenschutz/` | Rechtsseiten |
| `dist/assets/style.css`, `app.js`, `data.js` | gemeinsame Dateien |
| `dist/sitemap.xml` | 215 Adressen für Google |
| `dist/404.html` | Fehlerseite |

### Lokal, nicht im Repo

| Datei | Zweck |
|---|---|
| `admin.html` | Verwaltung, wird bei jedem Build neu erzeugt |
| `dist/` | die fertige Website |

### Dokumentation

| Datei | Inhalt |
|---|---|
| `START.md` | Livegang Schritt für Schritt, DNS, Google Search Console |
| `ANSCHREIBEN.md` | Fachschafts-Vorlagen, Outreach-Strategie |
| `TELEGRAM.md` | Namensschema, Bot-Handbuch |
| `erstilink_bot.py` | Telegram-Verwaltungsbot |

---

## Was drin ist

- 214 Hochschulen, jede mit eigener indexierbarer Seite
- Live-Suche über Unis *und* Studiengänge, wortweise und umlauttolerant
- Bundesland-Filter und A–Z-Filter
- Zweigeteiltes Einreichungsformular (Link / Bedarf) mit Vorschau und Kopier-Fallback
- Lokale Verwaltung mit Gruppenpflege, Outreach-Tracking, Import/Export
- Vollständiges Impressum und Datenschutzerklärung
- Vorschaubild, Favicon, Sitemap, strukturierte Daten
- Responsive, Tastaturbedienung, `prefers-reduced-motion` respektiert

## Grenzen

- Die Verwaltung läuft nur auf deinem Rechner. Von unterwegs pflegen geht nicht — dafür bräuchte es ein Backend.
- Einreichungen kommen per E-Mail, nicht automatisch in die Datenbank. Bei Gruppenlinks ist das ein Feature.
- Wenn mehrere Leute pflegen sollen, lohnt der Umstieg auf ein Backend (z. B. Supabase).

## Rechtlicher Hinweis

Impressum und Datenschutzerklärung beschreiben den tatsächlichen Betrieb dieser Website und enthalten deine echten Angaben. Sie ersetzen keine Rechtsberatung. Wenn du später Werbung, Analytics oder ein Kontaktformular mit Serverübertragung ergänzt, müssen beide Texte angepasst werden.
