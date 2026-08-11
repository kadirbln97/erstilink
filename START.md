# erstilink.de live schalten — Schritt für Schritt

Alles ist gebaut, getestet und abgesichert. Was bleibt, sind fünf Schritte, die nur du machen kannst, weil sie deine Konten betreffen. Reine Arbeitszeit: rund 20 Minuten. Dazu kommt Wartezeit beim DNS.

Arbeite die Schritte der Reihe nach ab. Wo ein Befehl steht, kannst du ihn direkt kopieren.

---

## Vorher: Was ich geändert habe

**Der Admin-Bereich ist nicht mehr online.** Kein Passwort im Quelltext, weil es keins mehr gibt — und nichts, was jemand angreifen könnte. Die Verwaltung liegt in `admin.html` auf deinem Rechner und wird nie hochgeladen.

Der Grund: Auf einer statischen Seite läuft alles im Browser des Besuchers. Ein Passwort dort ist eine Türklinke ohne Tür — wer den Quelltext liest, sieht die Logik und kann sie umgehen. Netlifys echter Passwortschutz kostet Geld (Pro-Plan). Die kostenlose und zugleich sicherere Lösung ist, den Admin gar nicht erst zu veröffentlichen.

`build.py` prüft das bei jedem Build automatisch und **bricht ab**, wenn Admin-Code oder ein Passwort in `dist/` landen würde.

---

## Schritt 1 — GitHub-Repository anlegen

1. [github.com/new](https://github.com/new) öffnen
2. Repository name: `erstilink`
3. **Private** auswählen (nicht Public)
4. Keine Häkchen bei README, .gitignore oder Lizenz
5. **Create repository**

GitHub zeigt dir danach eine Seite mit Befehlen. Ignorier sie, meine unten sind vollständiger.

> **Warum privat?** Im Repo liegen `src/app.html` und `build.py`. Nichts Geheimes, aber auch kein Grund, es öffentlich zu machen.

---

## Schritt 2 — Repository verbinden und ersten Push machen

Terminal öffnen, in den Projektordner wechseln, dann:

```bash
git init
git branch -M main
git add -A
git commit -m "ErstiLink: erste Version"
```

Jetzt die Verbindung zu GitHub — **ersetze `DEINNAME` durch deinen GitHub-Benutzernamen**:

```bash
git remote add origin https://github.com/DEINNAME/erstilink.git
git push -u origin main
```

Beim ersten Push fragt Git nach Zugangsdaten. GitHub akzeptiert seit Jahren kein Passwort mehr — du brauchst einen Token:

1. [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)**
2. Note: `erstilink`, Expiration: `No expiration`, Haken bei **repo**
3. **Generate token**, Token kopieren
4. Im Terminal als Passwort einfügen (der Benutzername ist dein GitHub-Name)

Alternativ, falls du es bequemer willst: `brew install gh && gh auth login` erledigt die Anmeldung im Browser.

**Sag mir Bescheid, wenn der Push durch ist** — oder wenn eine Fehlermeldung kommt.

---

## Schritt 3 — Netlify mit GitHub verbinden

1. [app.netlify.com/signup](https://app.netlify.com/signup) → mit GitHub anmelden
2. **Add new project → Import an existing project → GitHub**
3. Repository `erstilink` auswählen
4. Die Einstellungen sind schon richtig, weil `netlify.toml` im Repo liegt:
   - Build command: `python3 build.py`
   - Publish directory: `dist`
5. **Deploy**

Nach etwa einer Minute läuft die Seite unter einer Adresse wie `zufallsname-123.netlify.app`.

**Jetzt prüfen, bevor die Domain drankommt:**

- Startseite lädt und zeigt 214 Hochschulen
- `…netlify.app/uni/berlin-tu` funktioniert **direkt in die Adresszeile eingegeben**
- `…netlify.app/admin` zeigt „Diese Seite gibt es nicht"
- Rechtsklick → *Seitenquelltext anzeigen* auf einer Uni-Seite: „Technische Universität Berlin" muss im HTML stehen

**Schick mir die netlify.app-Adresse**, dann prüfe ich die Header und die ausgelieferten Seiten von außen.

---

## Schritt 4 — Domain verbinden

### In Netlify

**Site configuration → Domain management → Add a domain** → `erstilink.de` → *Add domain*.

Netlify fragt, ob du die Nameserver umstellen willst. **Nein** — wähle die Variante mit eigenen DNS-Einträgen. Netlify zeigt dir dann die genauen Werte.

### Bei Namecheap

**Domain List → erstilink.de → Manage → Advanced DNS**

Zuerst die vorhandenen Parking-Einträge löschen (meist ein `CNAME www → parkingpage.namecheap.com` und ein `URL Redirect`). Dann anlegen:

| Type | Host | Value | TTL |
|---|---|---|---|
| A Record | `@` | `75.2.60.5` | Automatic |
| CNAME Record | `www` | *der Wert aus Netlify*, z. B. `erstilink.netlify.app.` | Automatic |

Der Punkt am Ende des CNAME-Werts gehört dazu.

`75.2.60.5` ist Netlifys Load-Balancer-IP für Apex-Domains bei externem DNS. Wenn Netlify dir im Dialog eine andere IP nennt, nimm die aus dem Dialog.

### Warten

30 Minuten bis 2 Stunden, selten länger. Prüfen: [dnschecker.org](https://dnschecker.org) mit `erstilink.de`, Typ A.

HTTPS beantragt Netlify von selbst, sobald DNS greift. Falls es hängt: **Domain management → HTTPS → Verify DNS configuration**, dann **Provision certificate**.

---

## Schritt 5 — Bei Google anmelden

1. [search.google.com/search-console](https://search.google.com/search-console) → Property hinzufügen → **Domain** → `erstilink.de`
2. Google gibt dir einen TXT-Eintrag. Bei Namecheap unter **Advanced DNS**: Type `TXT Record`, Host `@`, Value = der Google-Wert
3. Nach der Bestätigung: **Sitemaps** → `sitemap.xml` eintragen → absenden
4. **URL-Prüfung** → `https://erstilink.de/` → *Indexierung beantragen*
5. Dasselbe für zwei, drei große Uni-Seiten, etwa `/uni/berlin-tu` und `/uni/muenchen-lmu`

Erwartungshaltung: Erste Seiten im Index nach ein bis zwei Wochen, Rankings dauern länger. Für dieses Semester wird Google nicht dein Hauptkanal — dafür ist es Mitte August zu spät. Instagram-DMs an Fachschaften wirken jetzt schneller. Die Sitemap zahlt sich zum Sommersemester aus.

---

## Ab dann: der Arbeitsablauf

### Gruppen eintragen

1. `admin.html` per Doppelklick öffnen (liegt lokal, kein Server nötig)
2. Uni suchen → **Gruppen** → **+ Gruppe** → Studiengang und Link eintragen
3. Wenn du fertig bist: **Seed-Block kopieren**
4. In `src/app.html` den Block `const SEED_UNIS = [ … ];` durch den kopierten ersetzen
5. Veröffentlichen:

```bash
./deploy.sh "Gruppen für TU Berlin ergänzt"
```

Das Skript baut, prüft und pusht. Netlify veröffentlicht innerhalb einer Minute.

### Nur schauen, ohne zu veröffentlichen

```bash
python3 build.py
python3 build.py pruefen
```

Dann `dist/index.html` im Browser öffnen.

### Semesterwechsel

In `src/app.html` den Wert `semester` ändern, dann `./deploy.sh "SoSe 2027"`.

---

## Sicherheit: was jetzt gilt

| Maßnahme | Wirkung |
|---|---|
| Kein Admin online | Nichts zum Angreifen, kein Passwort nirgends |
| Content-Security-Policy | Browser darf nur Code von deiner Domain ausführen |
| HSTS | Erzwingt HTTPS, zwei Jahre, inkl. Unterdomains |
| X-Frame-Options: DENY | Niemand kann die Seite in einen fremden Rahmen einbetten |
| Referrer-Policy | Beim Klick auf Gruppenlinks wird die genaue Uni-Seite nicht weitergegeben |
| Permissions-Policy | Kamera, Mikrofon, Standort von vornherein gesperrt |
| Alle Ausgaben escaped | Eingeschleustes HTML wird als Text dargestellt, nicht ausgeführt |
| `javascript:`-Links blockiert | Nur `http` und `https` werden verlinkt |
| `rel="noopener"` | Externe Links bekommen keinen Zugriff auf dein Fenster |
| Sicherheitsprüfung im Build | Build bricht ab, wenn Admin-Code oder Passwort in `dist/` landen |

Was das **nicht** leistet: Die Linkliste ist öffentlich, das soll sie sein. Und für die Gruppen hinter den Links bist du nicht verantwortlich, solange du sie prüfst und auf Hinweise reagierst — das steht so im Impressum.

---

## Wenn etwas klemmt

Schick mir:

- die Fehlermeldung aus dem Terminal, oder
- einen Screenshot der Namecheap-DNS-Seite, oder
- die netlify.app-Adresse

Dann sage ich dir genau, was zu ändern ist.
