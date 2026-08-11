# ErstiLink auf Telegram

## Was automatisierbar ist und was nicht

**Nicht automatisierbar: das Anlegen von Gruppen.** Die Telegram Bot API hat schlicht keine Methode dafür — ein Bot muss von einem Menschen in eine bestehende Gruppe geholt werden. Der einzige Weg, Gruppen programmatisch zu erzeugen, führt über MTProto mit einem echten Nutzerkonto (Telethon, Pyrogram). Das ist Kontenautomatisierung mit demselben Sperrrisiko wie bei WhatsApp, nur mit weniger Erstis am Ende.

**Automatisierbar: alles danach.** Einladungslinks erzeugen und erneuern, Gruppen erfassen, Links in die Website einspielen, Beitritte moderieren. Genau da setzt `erstilink_bot.py` an — und genau da liegt auch die eigentliche Arbeit. Eine Gruppe anzulegen dauert 20 Sekunden; ihren Link aktuell zu halten und in ein Verzeichnis zu bekommen, ist die Fleißarbeit.

Rechne mit ungefähr **eine Minute pro Gruppe** von Hand. 200 Gruppen sind ein langer Nachmittag, nicht ein Projekt.

---

## Namensschema

Der Bot liest Uni und Studiengang aus dem Gruppentitel. Deshalb muss der sitzen:

```
<Uni-Anzeigename> · <Studiengang>
```

Der Mittelpunkt `·` ist der Trenner. Er kommt in keinem der 214 Uni-Namen vor, deshalb gibt es keine Mehrdeutigkeiten. Auf dem Mac: `Alt` + `Shift` + `9`.

**Richtig:**

```
Aachen (RWTH) · Maschinenbau B.Sc.
Berlin (Charité) · Humanmedizin
Berlin (TU) · Wirtschaftsingenieurwesen
Köln (Uni) · Betriebswirtschaftslehre
München (LMU) · Rechtswissenschaft
```

**Falsch:**

```
RWTH Maschinenbau            fehlender Trenner
Aachen - Maschinenbau        Bindestrich statt ·
Maschinenbau Aachen (RWTH)   falsche Reihenfolge
```

Der Teil vor dem `·` muss **exakt dem Anzeigenamen auf der Website** entsprechen, sonst findet der Bot die Uni beim Export nicht. Den genauen Namen holst du dir im Admin-Bereich oder über die Suche auf der Startseite. Der offizielle Name funktioniert auch: „Ludwig-Maximilians-Universität München" statt „München (LMU)".

Ein Semester am Ende ist erlaubt und wird beim Einlesen abgeschnitten:

```
Aachen (RWTH) · Maschinenbau B.Sc. · WiSe 2026/27
```

---

## Gruppenbeschreibung

Telegram erlaubt 255 Zeichen. Vorlage:

> Ersti-Gruppe für **[Studiengang]** an der **[Uni]**, WiSe 2026/27. Fragen zur O-Woche, Stundenplan, Wohnungssuche, Lerngruppen. Kein Spam, keine Werbung, keine Altklausuren-Deals. Alle Gruppen: erstilink.de

## Angepinnte Startnachricht

Direkt nach dem Anlegen anpinnen. Kurz halten — lange Regelwerke liest niemand:

> **Willkommen in der Ersti-Gruppe [Studiengang]!**
>
> Kurz zur Orientierung:
> • Stell dich gern vor — Name, woher du kommst, worauf du dich freust
> • Fragen sind erwünscht, auch die vermeintlich dummen
> • Kein Spam, keine Werbung, kein Weiterverkauf von irgendwas
> • Keine Screenshots aus dieser Gruppe woanders posten
>
> Weitere Gruppen deiner Uni: erstilink.de/uni/[slug]
>
> Gruppe zu still? Schreib einfach was. Irgendjemand antwortet immer.

Den `[slug]` findest du in der Adresszeile, wenn du die Uni auf der Website öffnest — z. B. `aachen-rwth`.

---

## Der Bot

### Einrichten

1. In Telegram **@BotFather** anschreiben → `/newbot` → Namen vergeben → Token merken.
2. Noch bei BotFather: `/setjoingroups` → **enable**. Sonst darf der Bot keinen Gruppen beitreten.
3. Deine eigene User-ID herausfinden: **@userinfobot** anschreiben.
4. Terminal:

```bash
export ERSTILINK_BOT_TOKEN="123456:ABC..."
export ERSTILINK_ADMIN_ID="123456789"

python3 erstilink_bot.py check    # prüft Token und Einstellungen
python3 erstilink_bot.py run      # startet den Bot
```

Keine Installation nötig — der Bot nutzt nur die Python-Standardbibliothek.

### Pro Gruppe

1. Gruppe anlegen, Titel nach Schema.
2. Bot hinzufügen und zum **Administrator** machen. Das Recht *„Nutzer einladen"* genügt; mehr braucht er nicht und mehr solltest du ihm nicht geben.
3. In der Gruppe `/register` schreiben. Der Bot erzeugt den Einladungslink und merkt sich die Gruppe.

### Befehle

| Befehl | Wo | Wirkung |
|---|---|---|
| `/register` | Gruppe | Gruppe erfassen, Einladungslink erzeugen |
| `/link` | Gruppe | aktuellen Link anzeigen |
| `/refresh` | Gruppe | neuen Link erzeugen, alten zurückziehen |
| `/status` | Gruppe | zeigt, was der Bot über die Gruppe weiß |
| `/export` | Privatchat | Importdatei für die Website erzeugen |
| `/list` | Privatchat | alle registrierten Gruppen auflisten |

Alle Befehle außer `/help` sind auf deine User-ID beschränkt.

### Der Kreislauf zur Website

```
Website: Admin → JSON exportieren     →  erstilink_data.json
                                          neben erstilink_bot.py legen
Telegram: /export im Privatchat       →  erstilink_data_neu.json
Website: Admin → JSON importieren     →  Links sind drin
```

Der Bot ordnet jede Gruppe ihrer Uni zu, trägt den Studiengang mit Link ein und setzt den Outreach-Status auf *erledigt*. Unis, die er nicht zuordnen kann, meldet er einzeln — meist ein Tippfehler im Gruppentitel.

Läuft der Export ein zweites Mal, werden bestehende Einträge **aktualisiert statt dupliziert**. Du kannst also gefahrlos so oft exportieren, wie du willst.

---

## Chat-Ordner statt Community

Telegram hat keine Communities wie WhatsApp. Das nächstbeste sind **teilbare Chat-Ordner**: ein Link fügt dem Empfänger mehrere Chats auf einmal hinzu.

Für dich heißt das: pro Uni ein Ordner mit allen Studiengangsgruppen, ein Link auf der Uni-Detailseite. Wer draufklickt, sieht alle Gruppen der Uni und wählt aus.

So geht's: Einstellungen → Chat-Ordner → Ordner anlegen → Gruppen hinzufügen → *Teilen* → Link kopieren.

Zwei Haken, bevor du das für alle 214 Unis planst:

- Der Ordner **spiegelt nicht automatisch nach**. Kommt eine Gruppe dazu, musst du sie in den Ordner legen und der Link muss neu geteilt werden.
- In der kostenlosen Version sind Anzahl der Ordner und geteilten Links begrenzt (Telegram Premium hebt die Grenzen an). Die genauen Zahlen ändert Telegram gelegentlich — bevor du dich darauf verlässt, leg zwei, drei Ordner an und schau, wo die Wand kommt.

Für die ersten zwanzig Unis reicht es allemal.

---

## Grenzen, die du kennen solltest

**Gruppengröße:** Telegram-Supergruppen fassen bis zu 200.000 Mitglieder. Das ist für Erstis nie das Problem.

**Einladungslinks:** Ein Link pro Gruppe reicht. Wenn du `/refresh` nutzt, wird der alte ungültig — geteilte Links in alten WhatsApp-Nachrichten oder auf Instagram laufen dann ins Leere. Nutze `/refresh` also nur, wenn ein Link wirklich verbrannt ist.

**Bot-Rate-Limits:** Etwa 30 Nachrichten pro Sekunde insgesamt, ca. 20 pro Minute und Gruppe. Der Bot respektiert `retry_after` automatisch und wartet, statt gesperrt zu werden. Bei normaler Nutzung wirst du das nie merken.

**Spam-Erkennung:** Auch Telegram hat Grenzen. Wenn du an einem Abend 200 Gruppen anlegst, kann dein Konto vorübergehend eingeschränkt werden. Verteil das über mehrere Tage — 20 bis 30 Gruppen pro Tag sind unauffällig. Das ist kein von Telegram veröffentlichter Wert, sondern schlicht Vorsicht.

---

## Der ehrliche Teil

Telegram löst dein Verteilungsproblem nicht. Deutsche Erstis sind auf WhatsApp — eine Telegram-Gruppe für einen Studiengang ist erst dann wertvoll, wenn genug Leute drin sind, und die kommen nur, wenn sie schon wertvoll ist. Das ist ein Henne-Ei-Problem, und Telegram macht es schwerer, nicht leichter.

Wo Telegram **wirklich** gewinnt: Du besitzt die Infrastruktur. Niemand kann dir eine Gruppe wegnehmen, du kannst Links regenerieren, Moderation automatisieren und Gruppen zusammenlegen. Das ist ein echter Vorteil — aber erst ab dem Punkt, an dem Leute schon da sind.

Der pragmatische Weg wäre beides parallel: WhatsApp-Links von Fachschaften sammeln (Reichweite jetzt), Telegram-Gruppen für die Unis anlegen, wo du selbst Kontakte hast (Infrastruktur für später). Die Website trägt beides — im Feld „Zusatz" steht dann *Telegram* oder *WhatsApp*, und der Ersti sucht sich aus, was er ohnehin installiert hat.

Fang mit deiner eigenen Uni an. Wenn dort in zwei Wochen Leben in den Gruppen ist, funktioniert das Modell und du skalierst es. Wenn nicht, hast du zwanzig Gruppen verloren statt fünfhundert.
