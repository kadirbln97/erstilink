#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ErstiLink Telegram-Bot
=======================

Verwaltet bestehende Telegram-Gruppen und erzeugt daraus die Importdatei
für die ErstiLink-Website.

Was der Bot NICHT kann
----------------------
Gruppen anlegen. Die Telegram Bot API hat dafür keine Methode -- ein Bot
muss von einem Menschen in eine bestehende Gruppe geholt werden. Das
Anlegen automatisiert nur ein Nutzerkonto über MTProto, und das ist
Kontenautomatisierung mit entsprechendem Sperrrisiko. Der Bot setzt
deshalb dort an, wo die Arbeit tatsächlich anfällt: beim Einsammeln und
Aktuellhalten der Einladungslinks.

Ablauf
------
1. Gruppe in Telegram anlegen, Titel nach Schema:
       Aachen (RWTH) · Maschinenbau B.Sc.
2. Bot als Administrator hinzufügen (Recht "Nutzer einladen" genügt).
3. In der Gruppe /register schreiben.
4. Später: /export im Privatchat mit dem Bot -> JSON für die Website.

Aufruf
------
    export ERSTILINK_BOT_TOKEN="123456:ABC..."
    export ERSTILINK_ADMIN_ID="123456789"        # deine Telegram-User-ID

    python3 erstilink_bot.py check      # Token und Bot-Identität prüfen
    python3 erstilink_bot.py run        # Bot starten (Long Polling)
    python3 erstilink_bot.py export     # Export ohne laufenden Bot
    python3 erstilink_bot.py list       # registrierte Gruppen anzeigen

Keine externen Abhängigkeiten -- nur Python-Standardbibliothek.
"""

import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------
# Konfiguration
# --------------------------------------------------------------------------

TOKEN     = os.environ.get("ERSTILINK_BOT_TOKEN", "").strip()
ADMIN_ID  = os.environ.get("ERSTILINK_ADMIN_ID", "").strip()

STATE_FILE   = "bot_state.json"           # was der Bot sich merkt
SITE_FILE    = "erstilink_data.json"     # Export aus dem Admin-Bereich
OUTPUT_FILE  = "erstilink_data_neu.json" # Ergebnis zum Reimport

SEPARATOR    = "·"          # trennt Uni und Studiengang im Gruppentitel
SEMESTER     = "WiSe 2026/27"
GROUP_NOTE   = "Telegram"   # erscheint als Zusatz unter dem Studiengang

API = "https://api.telegram.org/bot%s/%s"


# --------------------------------------------------------------------------
# Telegram-API
# --------------------------------------------------------------------------

class ApiError(Exception):
    pass


def call(method, **params):
    """Ruft eine Bot-API-Methode auf. Respektiert 429/retry_after."""
    data = urllib.parse.urlencode(
        {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
         for k, v in params.items() if v is not None}
    ).encode("utf-8")

    for attempt in range(5):
        try:
            req = urllib.request.Request(API % (TOKEN, method), data=data)
            with urllib.request.urlopen(req, timeout=65) as r:
                payload = json.loads(r.read().decode("utf-8"))
            if payload.get("ok"):
                return payload["result"]
            raise ApiError(payload.get("description", "unbekannter Fehler"))

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                payload = json.loads(body)
            except ValueError:
                raise ApiError("HTTP %s: %s" % (e.code, body[:200]))

            if e.code == 429:
                wait = payload.get("parameters", {}).get("retry_after", 3)
                log("Rate-Limit, warte %ss" % wait)
                time.sleep(wait + 1)
                continue
            raise ApiError(payload.get("description", "HTTP %s" % e.code))

        except urllib.error.URLError as e:
            log("Netzwerkfehler (%s), neuer Versuch in 5s" % e.reason)
            time.sleep(5)

    raise ApiError("Nach 5 Versuchen aufgegeben: " + method)


def send(chat_id, text, **kw):
    try:
        return call("sendMessage", chat_id=chat_id, text=text,
                    disable_web_page_preview=True, **kw)
    except ApiError as e:
        log("Senden an %s fehlgeschlagen: %s" % (chat_id, e))
        return None


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


# --------------------------------------------------------------------------
# Zustand
# --------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"offset": 0, "groups": {}}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)   # atomar, damit nichts halb geschrieben liegenbleibt


# --------------------------------------------------------------------------
# Titel zerlegen
# --------------------------------------------------------------------------

def parse_title(title):
    """'Aachen (RWTH) · Maschinenbau B.Sc.' -> ('Aachen (RWTH)', 'Maschinenbau B.Sc.')"""
    if not title or SEPARATOR not in title:
        return None, None
    uni, _, rest = title.partition(SEPARATOR)
    # Ein evtl. angehängtes Semester am Ende abschneiden
    rest = re.sub(r"\s*%s\s*(WiSe|SoSe)\s*[\d/]+\s*$" % re.escape(SEPARATOR), "", rest)
    return uni.strip(), rest.strip()


def norm(s):
    """Vergleichsform: Umlaute auflösen, Sonderzeichen raus."""
    s = (s or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


# --------------------------------------------------------------------------
# Gruppen registrieren
# --------------------------------------------------------------------------

def is_admin(user_id):
    return not ADMIN_ID or str(user_id) == ADMIN_ID


def register(state, chat, user_id):
    """Gruppe erfassen und Einladungslink erzeugen."""
    chat_id = chat["id"]
    title   = chat.get("title", "")
    uni, course = parse_title(title)

    if not uni or not course:
        return ("Der Gruppentitel passt nicht zum Schema.\n\n"
                "Erwartet:  Uni (Kürzel) %s Studiengang\n"
                "Beispiel:  Aachen (RWTH) %s Maschinenbau B.Sc.\n\n"
                "Aktuell:   %s" % (SEPARATOR, SEPARATOR, title or "(kein Titel)"))

    # Prüfen, ob der Bot Links erzeugen darf
    try:
        me = call("getMe")
        member = call("getChatMember", chat_id=chat_id, user_id=me["id"])
    except ApiError as e:
        return "Konnte meine Rechte nicht prüfen: %s" % e

    if member.get("status") != "administrator" or not member.get("can_invite_users"):
        return ("Ich brauche Administratorrechte mit der Berechtigung "
                "\"Nutzer einladen\" (Einladungslinks verwalten), sonst kann ich "
                "keinen Link erzeugen.")

    try:
        link = call("createChatInviteLink", chat_id=chat_id,
                    name="ErstiLink %s" % SEMESTER[:30])
    except ApiError as e:
        return "Einladungslink fehlgeschlagen: %s" % e

    state["groups"][str(chat_id)] = {
        "chat_id":    chat_id,
        "title":      title,
        "uni":        uni,
        "course":     course,
        "invite":     link["invite_link"],
        "registered": int(time.time()),
        "by":         user_id,
    }
    save_state(state)

    return ("Eingetragen.\n\n"
            "Uni:         %s\n"
            "Studiengang: %s\n"
            "Link:        %s\n\n"
            "Mit /export im Privatchat erzeugst du die Datei für die Website."
            % (uni, course, link["invite_link"]))


# --------------------------------------------------------------------------
# Export für die Website
# --------------------------------------------------------------------------

def export(state, verbose=True):
    """Verbindet die registrierten Gruppen mit dem Datenbestand der Website."""
    groups = list(state["groups"].values())
    if not groups:
        return "Noch keine Gruppen registriert.", None

    if not os.path.exists(SITE_FILE):
        return ("Datei %s fehlt.\n\nExportiere sie im Admin-Bereich der Website "
                "über \"JSON exportieren\" und lege sie neben dieses Skript."
                % SITE_FILE), None

    with open(SITE_FILE, encoding="utf-8") as f:
        unis = json.load(f)

    by_name = {norm(u.get("name", "")): u for u in unis}
    by_full = {norm(u.get("full", "")): u for u in unis if u.get("full")}

    matched, unmatched = 0, []

    for g in groups:
        target = by_name.get(norm(g["uni"])) or by_full.get(norm(g["uni"]))
        if not target:
            unmatched.append(g)
            continue

        target.setdefault("groups", [])
        entry = {"name": g["course"], "url": g["invite"], "note": GROUP_NOTE}

        # Vorhandenen Eintrag desselben Studiengangs aktualisieren statt doppeln
        for i, existing in enumerate(target["groups"]):
            if norm(existing.get("name", "")) == norm(g["course"]):
                target["groups"][i] = entry
                break
        else:
            target["groups"].append(entry)

        if target.get("status") in (None, "", "offen", "angeschrieben", "antwort"):
            target["status"] = "erledigt"
        matched += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unis, f, ensure_ascii=False, indent=2)

    report = ["%d von %d Gruppen zugeordnet." % (matched, len(groups)),
              "Datei geschrieben: %s" % OUTPUT_FILE]
    if unmatched:
        report.append("")
        report.append("Nicht zugeordnet (Uni-Name unbekannt):")
        for g in unmatched[:15]:
            report.append("  · %s  ->  %s" % (g["uni"], g["title"]))
        if len(unmatched) > 15:
            report.append("  ... und %d weitere" % (len(unmatched) - 15))
        report.append("")
        report.append("Tipp: Der Teil vor dem %s muss exakt dem Anzeigenamen "
                      "auf der Website entsprechen." % SEPARATOR)
    report.append("")
    report.append("Zum Einspielen: Admin -> JSON importieren -> %s wählen." % OUTPUT_FILE)

    text = "\n".join(report)
    if verbose:
        print(text)
    return text, OUTPUT_FILE


# --------------------------------------------------------------------------
# Nachrichtenverarbeitung
# --------------------------------------------------------------------------

HELP = """ErstiLink-Bot

In einer Gruppe (nur Admins):
  /register   Gruppe erfassen und Einladungslink erzeugen
  /link       aktuellen Einladungslink anzeigen
  /refresh    neuen Link erzeugen, alten zurückziehen
  /status     zeigt, was ich über diese Gruppe weiß

Im Privatchat:
  /export     Importdatei für die Website erzeugen
  /list       alle registrierten Gruppen auflisten

Gruppentitel-Schema:
  Uni (Kürzel) %s Studiengang
  Beispiel: Aachen (RWTH) %s Maschinenbau B.Sc.

Ich kann keine Gruppen anlegen -- das erlaubt die Telegram Bot API nicht.
Leg sie von Hand an und hol mich als Admin dazu.""" % (SEPARATOR, SEPARATOR)


def handle(update, state):
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    chat    = msg.get("chat", {})
    chat_id = chat.get("id")
    text    = (msg.get("text") or "").strip()
    user    = msg.get("from", {}) or {}
    user_id = user.get("id")

    if not text.startswith("/"):
        return

    cmd = text.split()[0].split("@")[0].lower()
    private = chat.get("type") == "private"
    key = str(chat_id)

    if cmd in ("/start", "/help"):
        send(chat_id, HELP)
        return

    if not is_admin(user_id):
        send(chat_id, "Diesen Befehl darf nur der Betreiber nutzen.")
        return

    # ---- Gruppenbefehle ----
    if cmd == "/register":
        if private:
            send(chat_id, "Das geht nur in der Gruppe, die eingetragen werden soll.")
        else:
            send(chat_id, register(state, chat, user_id))
        return

    if cmd in ("/link", "/status"):
        g = state["groups"].get(key)
        if not g:
            send(chat_id, "Diese Gruppe ist noch nicht eingetragen. Nutze /register.")
        elif cmd == "/link":
            send(chat_id, g["invite"])
        else:
            send(chat_id, "Uni:         %s\nStudiengang: %s\nLink:        %s"
                 % (g["uni"], g["course"], g["invite"]))
        return

    if cmd == "/refresh":
        g = state["groups"].get(key)
        if not g:
            send(chat_id, "Diese Gruppe ist noch nicht eingetragen. Nutze /register.")
            return
        try:
            new = call("createChatInviteLink", chat_id=chat_id, name="ErstiLink")
            try:
                call("revokeChatInviteLink", chat_id=chat_id, invite_link=g["invite"])
            except ApiError:
                pass   # alter Link evtl. schon ungültig -- kein Grund abzubrechen
            g["invite"] = new["invite_link"]
            save_state(state)
            send(chat_id, "Neuer Link:\n%s\n\nDer alte wurde zurückgezogen."
                 % new["invite_link"])
        except ApiError as e:
            send(chat_id, "Fehlgeschlagen: %s" % e)
        return

    # ---- Privatchat ----
    if cmd == "/export":
        text_out, path = export(state, verbose=False)
        send(chat_id, text_out)
        if path and os.path.exists(path):
            try:
                upload_document(chat_id, path)
            except ApiError as e:
                log("Datei-Upload fehlgeschlagen: %s" % e)
        return

    if cmd == "/list":
        gs = list(state["groups"].values())
        if not gs:
            send(chat_id, "Noch keine Gruppen registriert.")
            return
        gs.sort(key=lambda g: (g["uni"], g["course"]))
        lines, chunk = [], []
        for g in gs:
            chunk.append("· %s %s %s" % (g["uni"], SEPARATOR, g["course"]))
            if len(chunk) == 40:
                lines.append("\n".join(chunk)); chunk = []
        if chunk:
            lines.append("\n".join(chunk))
        send(chat_id, "%d Gruppen registriert:" % len(gs))
        for block in lines:
            send(chat_id, block)
        return


def upload_document(chat_id, path):
    """Datei-Upload als multipart/form-data, ohne externe Bibliothek."""
    boundary = "----ErstiLink%d" % int(time.time())
    with open(path, "rb") as f:
        content = f.read()

    body = b"".join([
        ("--%s\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n%s\r\n"
         % (boundary, chat_id)).encode("utf-8"),
        ("--%s\r\nContent-Disposition: form-data; name=\"document\"; filename=\"%s\"\r\n"
         "Content-Type: application/json\r\n\r\n"
         % (boundary, os.path.basename(path))).encode("utf-8"),
        content,
        ("\r\n--%s--\r\n" % boundary).encode("utf-8"),
    ])

    req = urllib.request.Request(
        API % (TOKEN, "sendDocument"), data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if not payload.get("ok"):
        raise ApiError(payload.get("description", "Upload fehlgeschlagen"))


# --------------------------------------------------------------------------
# Hauptschleife
# --------------------------------------------------------------------------

def run():
    state = load_state()
    me = call("getMe")
    log("Gestartet als @%s" % me.get("username"))
    log("%d Gruppen im Bestand" % len(state["groups"]))
    if not ADMIN_ID:
        log("WARNUNG: ERSTILINK_ADMIN_ID nicht gesetzt -- jeder darf Befehle nutzen.")

    while True:
        try:
            updates = call("getUpdates", offset=state["offset"], timeout=50)
        except ApiError as e:
            log("getUpdates: %s" % e)
            time.sleep(5)
            continue

        for u in updates:
            state["offset"] = u["update_id"] + 1
            try:
                handle(u, state)
            except Exception as e:                     # ein defektes Update
                log("Fehler bei Update %s: %s" % (u.get("update_id"), e))
        if updates:
            save_state(state)


def check():
    me = call("getMe")
    print("Bot:      @%s (%s)" % (me.get("username"), me.get("id")))
    print("Name:     %s" % me.get("first_name"))
    print("Gruppen:  %s" % ("darf beitreten" if me.get("can_join_groups")
                            else "DARF KEINEN GRUPPEN BEITRETEN -- in @BotFather "
                                 "unter /setjoingroups aktivieren"))
    priv = me.get("can_read_all_group_messages")
    print("Privacy:  %s" % ("aus -- liest alle Nachrichten" if priv else
                            "an -- liest nur Befehle (das genügt)"))
    state = load_state()
    print("Bestand:  %d registrierte Gruppen" % len(state["groups"]))


def main():
    if not TOKEN:
        sys.exit("ERSTILINK_BOT_TOKEN ist nicht gesetzt.\n"
                 "Token bei @BotFather holen, dann:\n"
                 "  export ERSTILINK_BOT_TOKEN=\"123456:ABC...\"")

    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "run":
        run()
    elif mode == "check":
        check()
    elif mode == "export":
        export(load_state())
    elif mode == "list":
        gs = sorted(load_state()["groups"].values(),
                    key=lambda g: (g["uni"], g["course"]))
        for g in gs:
            print("%-46s %s" % ("%s %s %s" % (g["uni"], SEPARATOR, g["course"]),
                                g["invite"]))
        print("\n%d Gruppen" % len(gs))
    else:
        sys.exit("Unbekannter Modus: %s\nErlaubt: run, check, export, list" % mode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBeendet.")
