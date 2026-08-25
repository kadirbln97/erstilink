#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ErstiLink – Seitengenerator
===========================

Erzeugt aus src/app.html eine statische Website in dist/ mit einer eigenen
HTML-Datei pro Hochschule.

Warum überhaupt?
----------------
Vorher lieferte eine einzige index.html alle Adressen aus und JavaScript baute
den Inhalt nachträglich zusammen. Google kommt damit inzwischen zurecht, aber
erst nach einem zweiten Durchgang, und Titel wie Beschreibung standen nicht im
ausgelieferten HTML. Jetzt bekommt jede Hochschule eine echte Datei mit
fertigem Inhalt, eigenem Titel, eigener Beschreibung und strukturierten Daten.
Für Suchmaschinen sind das 214 vollwertige Seiten statt einer.

Aufruf
------
    python3 build.py              # Website nach dist/ bauen
    python3 build.py passwort     # neuen Admin-Passwort-Hash erzeugen
    python3 build.py pruefen      # dist/ auf typische Fehler prüfen

Keine externen Abhängigkeiten.
"""

import base64
import getpass
import hashlib
import html as htmlmod
import json
import os
import re
import shutil
import sys
import datetime

ROOT   = os.path.dirname(os.path.abspath(__file__))
SRC    = os.path.join(ROOT, "src", "app.html")
DIST   = os.path.join(ROOT, "dist")
STATIC = ["og.png", "favicon.png", "apple-touch-icon.png",
          "robots.txt", "_redirects", "_headers", "netlify.toml", "CNAME"]

E = lambda s: htmlmod.escape(str(s if s is not None else ""), quote=True)
b64 = lambda s: base64.b64encode(str(s or "").encode("utf-8")).decode("ascii")


# --------------------------------------------------------------------------
# Quelle einlesen
# --------------------------------------------------------------------------

def read_source():
    with open(SRC, encoding="utf-8") as f:
        src = f.read()

    css = re.search(r"<style>(.*?)</style>", src, re.S)
    js  = re.search(r"<script>(.*?)</script>", src, re.S)
    if not css or not js:
        sys.exit("src/app.html: <style> oder <script> nicht gefunden.")

    app_js = js.group(1)

    # Datenblock abtrennen, damit er getrennt ausgeliefert und gecacht wird
    m = re.search(r"const SEED_UNIS = \[.*?\n\];", app_js, re.S)
    if not m:
        sys.exit("SEED_UNIS nicht gefunden.")
    data_js = m.group(0)
    app_js  = app_js.replace(data_js, "/* Daten liegen in data.js */")

    # Admin-Teil abtrennen: er gehört ausschließlich in die lokale admin.html.
    # Ein Passwort im Browser schützt nichts – deshalb existiert der
    # Admin-Bereich auf dem Server gar nicht erst.
    a, b = app_js.find("/* ADMIN-START */"), app_js.find("/* ADMIN-ENDE */")
    if a == -1 or b == -1:
        sys.exit("ADMIN-START/ADMIN-ENDE nicht gefunden – src/app.html prüfen.")
    admin_js  = app_js[a + len("/* ADMIN-START */"):b]
    public_js = app_js[:a] + "/* Admin-Bereich: nur lokal, siehe admin.html */\n" + app_js[b + len("/* ADMIN-ENDE */"):]

    cfg = {}
    for key in ("siteName", "siteUrl", "semester", "contactEmail"):
        mm = re.search(r'%s:\s*"([^"]*)"' % key, app_js)
        cfg[key] = mm.group(1) if mm else ""

    return css.group(1), public_js, admin_js, data_js, cfg


def parse_unis(data_js):
    """Wandelt den JS-Block in echte Python-Objekte um."""
    body = data_js[data_js.index("["):data_js.rindex("]") + 1]
    body = re.sub(r"(\{|,)(\w+):", r'\1"\2":', body)
    return json.loads(body)


def public_data_js(unis):
    """Baut assets/data.js frisch aus den geparsten Objekten – nicht als
    Kopie der Quelle. Gruppenlinks werden dabei Base64-kodiert, damit sie in
    der ausgelieferten Datei nicht als Klartext-URL herausgreifbar sind (siehe
    Kommentar bei uni_body). Admin und Excel-Import bleiben unberührt: dort
    wird weiterhin mit normalen Links gearbeitet, die Kodierung passiert erst
    hier, beim Bau der öffentlichen Datei."""
    public = []
    for u in unis:
        u2 = dict(u)
        groups = []
        for g in (u.get("groups") or []):
            g2 = dict(g)
            url = (g2.get("url") or "").strip()
            g2["url"] = b64(url) if re.match(r"^https?://", url, re.I) else ""
            groups.append(g2)
        u2["groups"] = groups
        public.append(u2)
    return "const SEED_UNIS = " + json.dumps(public, ensure_ascii=False, separators=(",", ":")) + ";\n"


# --------------------------------------------------------------------------
# Seitengerüst
# --------------------------------------------------------------------------

def page(cfg, *, title, description, path, body, jsonld=None, noindex=False):
    url = cfg["siteUrl"] + "/" + path if path else cfg["siteUrl"] + "/"
    head = [
        '<!DOCTYPE html>',
        '<html lang="de">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>%s</title>' % E(title),
        '<meta name="description" content="%s">' % E(description),
        '<link rel="canonical" href="%s">' % E(url),
    ]
    if noindex:
        head.append('<meta name="robots" content="noindex, nofollow">')
    head += [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="%s">' % E(cfg["siteName"]),
        '<meta property="og:title" content="%s">' % E(title),
        '<meta property="og:description" content="%s">' % E(description),
        '<meta property="og:url" content="%s">' % E(url),
        '<meta property="og:locale" content="de_DE">',
        '<meta property="og:image" content="%s/og.png">' % E(cfg["siteUrl"]),
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % E(title),
        '<meta name="twitter:description" content="%s">' % E(description),
        '<meta name="twitter:image" content="%s/og.png">' % E(cfg["siteUrl"]),
        '<meta name="theme-color" content="#4f46e5">',
        '<link rel="icon" type="image/png" href="/favicon.png">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="stylesheet" href="/assets/style.css">',
    ]
    # jsonld darf ein einzelnes Objekt oder eine Liste mehrerer Schemas sein
    # (z. B. WebSite + FAQPage auf derselben Seite) – jedes bekommt sein eigenes Script-Tag.
    for block in (jsonld if isinstance(jsonld, list) else [jsonld] if jsonld else []):
        head.append('<script type="application/ld+json">%s</script>'
                    % json.dumps(block, ensure_ascii=False, separators=(",", ":")))
    head.append('</head>')

    return "\n".join(head) + """
<body>

<header class="site-head">
  <div class="wrap">
    <a class="logo" href="/"><span class="logo-mark">🎓</span> %(name)s</a>
    <nav class="head-nav">
      <a href="/fachschaften">Für Fachschaften</a>
      <a href="/starterkit">Starterkit</a>
    </nav>
    <div class="head-actions">
      <button class="btn btn-primary btn-sm" id="btnSubmit">Gruppe einreichen</button>
    </div>
  </div>
</header>

<main id="app">%(body)s</main>

<footer class="site-foot">
  <div class="wrap">
    <span>© <span id="year">%(year)s</span> %(name)s</span>
    <nav>
      <a href="/impressum">Impressum</a>
      <a href="/datenschutz">Datenschutz</a>
      <a href="/transparenz">Transparenz</a>
      <button class="link-btn" id="btnReport">Person melden</button>
    </nav>
  </div>
</footer>

<div id="modalRoot"></div>

<!-- Statisches Erkennungsformular für Netlify Forms: Das eigentliche Formular
     wird per JS in ein Modal gerendert, Netlifys Build-Bot liest aber nur das
     ausgelieferte HTML. Dieses versteckte Duplikat mit identischen Feldnamen
     sorgt dafür, dass Netlify das Formular-Schema kennt und Einreichungen des
     echten (JS-)Formulars per AJAX annimmt. Wird nie selbst angezeigt oder
     abgeschickt. -->
<form name="einreichung" data-netlify="true" netlify-honeypot="bot-field" hidden>
  <input type="text" name="bot-field">
  <input type="text" name="typ">
  <input type="text" name="uni">
  <input type="text" name="studiengang">
  <input type="text" name="link">
  <input type="text" name="semester">
  <input type="text" name="gruppe">
  <input type="text" name="name">
  <input type="email" name="email">
  <textarea name="anmerkung"></textarea>
</form>

<script src="/assets/data.js"></script>
<script src="/assets/app.js"></script>
</body>
</html>
""" % {"name": E(cfg["siteName"]), "body": body,
       "year": datetime.date.today().year}


# --------------------------------------------------------------------------
# Vorgerenderte Inhalte
# --------------------------------------------------------------------------

def first_letter(name):
    c = name[0].upper()
    return c if c.isalpha() else "#"


def home_body(cfg, unis):
    laender = sorted({u.get("land", "") for u in unis if u.get("land")})
    groups = {}
    for u in sorted(unis, key=lambda x: x["name"].lower()):
        groups.setdefault(first_letter(u["name"]), []).append(u)

    blocks = []
    for letter in sorted(groups):
        cards = []
        for u in groups[letter]:
            n = len(u.get("groups") or [])
            label = ("%d %s" % (n, "Gruppe" if n == 1 else "Gruppen")) if n else "bald"
            cards.append(
                '<a class="uni-card" href="/uni/%s">'
                '<span class="nm">%s</span>'
                '<span class="meta"><span class="count%s">%s</span></span></a>'
                % (E(u["id"]), E(u["name"]), "" if n else " zero", E(label)))
        blocks.append('<section class="letter-group"><h3>%s</h3>'
                      '<div class="uni-grid">%s</div></section>'
                      % (E(letter), "".join(cards)))

    total_groups = sum(len(u.get("groups") or []) for u in unis)

    return """
  <section class="hero">
    <div class="wrap">
      <span class="badge"><span class="dot"></span> %(name)s · %(sem)s</span>
      <p class="kicker">%(name)s sammelt Ersti- und Uni-Gruppen aus ganz Deutschland.</p>
      <h1>Finde deine <em>Ersti-Gruppe</em> an deiner Uni</h1>
      <p class="lead">Finde die passende WhatsApp-Gruppe für Erstsemester an deiner Universität oder
      Hochschule. Wähle deine Uni und deinen Studiengang, tritt deiner Ersti-Gruppe bei und vernetze
      dich schon vor dem Semesterstart mit deinen Kommilitonen.</p>
      <ol class="hero-steps">
        <li><span>1</span>Uni auswählen</li>
        <li><span>2</span>Studiengang finden</li>
        <li><span>3</span>Gruppe beitreten</li>
      </ol>
      <div class="hero-stats">
        <div class="stat"><b>%(n)d</b><span>Hochschulen</span></div>
        <div class="stat"><b>%(g)d</b><span>Gruppen</span></div>
        <div class="stat"><b>%(l)d</b><span>Bundesländer</span></div>
      </div>
    </div>
  </section>

  <div class="wrap">
    <div class="section-head">
      <div>
        <h2>Wähle deine Uni</h2>
        <p class="sub">%(n)d Hochschulen</p>
      </div>
    </div>
    %(blocks)s

    <div class="cta">
      <div>
        <h3>Deine Gruppe fehlt?</h3>
        <p>Füge deine Ersti- oder Studiengangsgruppe kostenlos hinzu.</p>
      </div>
      <div class="cta-actions">
        <button class="btn btn-wa" data-open-submit>Link einreichen</button>
        <button class="btn btn-ghost" data-open-submit data-mode="demand">Gruppe vermisst</button>
      </div>
    </div>

    <section class="faq" aria-labelledby="faqHeading">
      <h2 id="faqHeading">Häufige Fragen</h2>
      <div class="faq-grid">
        <div class="faq-item">
          <h3>Wie finde ich meine Ersti-Gruppe?</h3>
          <p>Wähle oben deine Uni aus der Liste oder nutze die Suche. Auf der Uni-Seite siehst du alle hinterlegten WhatsApp-Gruppen nach Studiengang.</p>
        </div>
        <div class="faq-item">
          <h3>Ist %(name)s kostenlos?</h3>
          <p>Ja, komplett kostenlos – sowohl das Beitreten zu einer Gruppe als auch das Einreichen eines Links.</p>
        </div>
        <div class="faq-item">
          <h3>Meine Uni oder mein Studiengang fehlt, was jetzt?</h3>
          <p>Über „Link einreichen“ kannst du eine WhatsApp-Gruppe hinzufügen. Hast du noch keinen Link? Melde den Bedarf über „Gruppe vermisst“ – wir fragen bei der Fachschaft nach.</p>
        </div>
        <div class="faq-item">
          <h3>Sind die Gruppen offiziell von der Uni?</h3>
          <p>Nein. %(name)s ist ein unabhängiges Verzeichnis. Die Gruppen werden von Studierenden oder Fachschaften betrieben, nicht von den Hochschulen selbst.</p>
        </div>
      </div>
    </section>
  </div>
""" % {"name": E(cfg["siteName"]), "sem": E(cfg["semester"]),
       "n": len(unis), "g": total_groups, "l": len(laender),
       "blocks": "".join(blocks)}


def uni_body(cfg, u):
    grp = sorted(u.get("groups") or [], key=lambda g: g["name"].lower())
    if grp:
        items = []
        for g in grp:
            url = (g.get("url") or "").strip()
            safe = url if re.match(r"^https?://", url, re.I) else ""
            # Der echte Link steht bewusst nicht als href im ausgelieferten HTML –
            # sonst liest ein simpler Scraper (curl + Regex) ihn direkt aus dem
            # Quelltext, ohne die Seite je im Browser zu öffnen. Stattdessen liegt
            # er Base64-kodiert in einem data-Attribut; JS löst ihn erst beim Klick
            # auf. Kein Schutz gegen einen Scraper, der selbst JavaScript ausführt –
            # aber gegen die weit verbreiteten einfachen Crawler.
            btn = ('<button class="btn btn-wa btn-sm" type="button" data-wa="%s">Gruppe beitreten</button>' % E(b64(safe))) \
                  if safe else '<span class="btn btn-ghost btn-sm">Link folgt</span>'
            note = '<div class="note">%s</div>' % E(g["note"]) if g.get("note") else ""
            items.append('<li class="group-item"><div class="info">'
                         '<div class="title">%s</div>%s</div>%s</li>'
                         % (E(g["name"]), note, btn))
        listing = '<ul class="group-list">%s</ul>' % "".join(items)
    else:
        listing = ('<div class="empty"><h3>Noch keine Gruppen hinterlegt</h3>'
                   '<p>Für %s ist bisher keine Gruppe eingetragen. Du hast einen Link?</p>'
                   '<button class="btn btn-primary" data-open-submit data-uni="%s">Link einreichen</button>'
                   '</div>' % (E(u["name"]), E(u["name"])))

    meta = " · ".join(x for x in [
        (u.get("typ", "") + (", " + u["traeger"] if u.get("traeger") else "")) if u.get("typ") else "",
        u.get("land", ""),
        "%d %s" % (len(grp), "Gruppe" if len(grp) == 1 else "Gruppen"),
        cfg["semester"]] if x)

    return """
  <div class="wrap">
    <a class="crumb" href="/">← Alle Hochschulen</a>
    <div class="detail-head">
      <h1>Ersti-Gruppen %(name)s</h1>
      %(full)s
      <p class="sub">%(meta)s</p>
    </div>
    %(listing)s
    <div class="cta">
      <div>
        <h3>Dein Studiengang fehlt?</h3>
        <p>Link vorhanden? Wir hängen ihn unter %(name)s. Noch keine Gruppe? Melde den Bedarf.</p>
      </div>
      <div class="cta-actions">
        <button class="btn btn-wa" data-open-submit data-uni="%(name)s">Link einreichen</button>
        <button class="btn btn-ghost" data-open-submit data-mode="demand" data-uni="%(name)s">Gruppe vermisst</button>
      </div>
    </div>
  </div>
""" % {"name": E(u["name"]),
       "full": '<p class="official">%s</p>' % E(u["full"]) if u.get("full") else "",
       "meta": E(meta), "listing": listing}


# --------------------------------------------------------------------------
# Bauen
# --------------------------------------------------------------------------

def write(path, content):
    full = os.path.join(DIST, path)
    d = os.path.dirname(full)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def build():
    css, app_js, admin_js, data_js, cfg = read_source()
    unis = parse_unis(data_js)

    # Alten Stand entfernen, damit keine Reste gelöschter Unis liegenbleiben.
    # Schlägt das fehl (z. B. gesperrte Dateien), wird stattdessen überschrieben.
    stale = []
    if os.path.isdir(DIST):
        try:
            shutil.rmtree(DIST)
        except OSError as e:
            print("Hinweis: dist/ konnte nicht geleert werden (%s) – wird überschrieben." % e.strerror)
            # Reste früherer Builds einsammeln, damit nichts Altes online geht
            for d in ("admin",):
                if os.path.isdir(os.path.join(DIST, d)):
                    stale.append(d)
    os.makedirs(DIST, exist_ok=True)

    write("assets/style.css", css.strip() + "\n")
    write("assets/data.js", public_data_js(unis))
    write("assets/app.js", app_js.strip() + "\n")

    site, name = cfg["siteUrl"], cfg["siteName"]

    # ---- Startseite ----
    home_faq = [
        ("Wie finde ich meine Ersti-Gruppe?",
         "Wähle deine Uni aus der Liste oder nutze die Suche. Auf der Uni-Seite stehen alle "
         "hinterlegten WhatsApp-Gruppen nach Studiengang."),
        ("Ist %s kostenlos?" % name,
         "Ja, komplett kostenlos – sowohl das Beitreten zu einer Gruppe als auch das Einreichen eines Links."),
        ("Meine Uni oder mein Studiengang fehlt, was jetzt?",
         "Über „Link einreichen“ kannst du eine WhatsApp-Gruppe hinzufügen. Hast du noch keinen Link? "
         "Melde den Bedarf über „Gruppe vermisst“ – wir fragen bei der Fachschaft nach."),
        ("Sind die Gruppen offiziell von der Uni?",
         "Nein. %s ist ein unabhängiges Verzeichnis. Die Gruppen werden von Studierenden oder "
         "Fachschaften betrieben, nicht von den Hochschulen selbst." % name),
    ]
    write("index.html", page(cfg,
        title="%s – WhatsApp-Gruppen für Erstsemester finden" % name,
        description="Finde die WhatsApp-Gruppe deiner Uni für Erstsemester. %s bündelt Ersti-Gruppen "
                    "von %d Hochschulen in Deutschland – nach Uni und Studiengang sortiert."
                    % (name, len(unis)),
        path="", body=home_body(cfg, unis),
        jsonld=[
            {"@context": "https://schema.org", "@type": "WebSite",
             "name": name, "url": site + "/", "inLanguage": "de-DE",
             "description": "Verzeichnis von WhatsApp-Ersti-Gruppen deutscher Hochschulen."},
            {"@context": "https://schema.org", "@type": "FAQPage",
             "mainEntity": [
                 {"@type": "Question", "name": q,
                  "acceptedAnswer": {"@type": "Answer", "text": a}}
                 for q, a in home_faq]},
        ]))

    # ---- Uni-Seiten ----
    for u in unis:
        typ = u.get("typ") or "Hochschule"
        desc = ("Ersti-Gruppen für %s: WhatsApp-Gruppen nach Studiengang für das %s. "
                "Finde die Gruppe deines Jahrgangs." % (u.get("full") or u["name"], cfg["semester"]))
        write("uni/%s/index.html" % u["id"], page(cfg,
            title="Ersti-Gruppen %s – %s" % (u["name"], name),
            description=desc,
            path="uni/" + u["id"],
            body=uni_body(cfg, u),
            jsonld={"@context": "https://schema.org", "@type": "CollectionPage",
                    "name": "Ersti-Gruppen %s" % u["name"],
                    "url": "%s/uni/%s" % (site, u["id"]),
                    "inLanguage": "de-DE", "description": desc,
                    "about": {"@type": "CollegeOrUniversity",
                              "name": u.get("full") or u["name"],
                              "address": {"@type": "PostalAddress",
                                          "addressRegion": u.get("land", ""),
                                          "addressCountry": "DE"}},
                    "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Startseite", "item": site + "/"},
                        {"@type": "ListItem", "position": 2, "name": u["name"],
                         "item": "%s/uni/%s" % (site, u["id"])}]}}))

    # ---- Rechtsseiten und Admin ----
    for slug, titel in (("impressum", "Impressum"), ("datenschutz", "Datenschutzerklärung"),
                        ("transparenz", "Transparenzhinweis")):
        write("%s/index.html" % slug, page(cfg,
            title="%s – %s" % (titel, name),
            description="%s von %s." % (titel, name),
            path=slug, noindex=True,
            body='<div class="wrap"><article class="legal"><h1>%s</h1>'
                 '<p>Wird geladen …</p></article></div>' % E(titel)))

    # ---- Inhaltsseiten (Starterkit, Für Fachschaften) – indexierbar ----
    for slug, titel, beschreibung in (
        ("starterkit", "Startklar für den Studienbeginn",
         "Checkliste für den Studienstart und ein Angebot für Studierende – klar als Werbung gekennzeichnet."),
        ("fachschaften", "Eure WhatsApp-Gruppe dort, wo Erstis zuerst suchen",
         "So landet die offizielle Ersti-Gruppe eurer Fachschaft im Verzeichnis von %s." % name),
    ):
        write("%s/index.html" % slug, page(cfg,
            title="%s – %s" % (titel, name),
            description=beschreibung,
            path=slug,
            body='<div class="wrap"><section class="page-hero"><h1>%s</h1>'
                 '<p class="lead">Wird geladen …</p></section></div>' % E(titel)))

    write("404.html", page(cfg,
        title="Seite nicht gefunden – %s" % name,
        description="Diese Seite existiert nicht.",
        path="404", noindex=True,
        body='<div class="wrap"><div class="empty empty-lg">'
             '<h1 class="h1-tight">Diese Seite gibt es nicht</h1>'
             '<p>Vielleicht hat sich die Adresse geändert.</p>'
             '<a class="btn btn-primary" href="/">Zur Startseite</a></div></div>'))

    # ---- sitemap.xml ----
    today = datetime.date.today().isoformat()
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '  <url><loc>%s/</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq>'
            '<priority>1.0</priority></url>' % (site, today),
            '  <url><loc>%s/starterkit</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq>'
            '<priority>0.6</priority></url>' % (site, today),
            '  <url><loc>%s/fachschaften</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq>'
            '<priority>0.6</priority></url>' % (site, today)]
    for u in unis:
        rows.append('  <url><loc>%s/uni/%s</loc><lastmod>%s</lastmod>'
                    '<changefreq>weekly</changefreq><priority>0.8</priority></url>'
                    % (site, u["id"], today))
    rows.append("</urlset>")
    write("sitemap.xml", "\n".join(rows) + "\n")

    # ---- Reste früherer Builds neutralisieren ----
    for d in stale:
        try:
            shutil.rmtree(os.path.join(DIST, d))
            print("Entfernt: dist/%s/ (Rest eines früheren Builds)" % d)
        except OSError:
            write("%s/index.html" % d, page(cfg,
                title="Seite nicht gefunden – %s" % name,
                description="Diese Seite existiert nicht.",
                path=d, noindex=True,
                body='<div class="wrap"><div class="empty empty-lg">'
                     '<h1 class="h1-tight">Diese Seite gibt es nicht</h1>'
                     '<p>Die Verwaltung läuft ausschließlich lokal.</p>'
                     '<a class="btn btn-primary" href="/">Zur Startseite</a></div></div>'))
            print("Überschrieben: dist/%s/ mit einer Fehlerseite" % d)

    # ---- lokale Admin-Oberfläche (bewusst NICHT in dist/) ----
    admin_html = ADMIN_TEMPLATE % {
        "css": css.strip(),
        "data": data_js,
        "app": app_js.strip(),
        "admin": admin_js.strip(),
        "name": E(cfg["siteName"]),
    }
    with open(os.path.join(ROOT, "admin.html"), "w", encoding="utf-8") as f:
        f.write(admin_html)

    # ---- unveränderte Dateien kopieren ----
    for f in STATIC:
        srcf = os.path.join(ROOT, f)
        if os.path.exists(srcf):
            with open(srcf, "rb") as a, open(os.path.join(DIST, f), "wb") as b:
                b.write(a.read())

    guard()
    pages = sum(len(files) for _, _, files in os.walk(DIST))
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(DIST) for f in fs)
    print("dist/ gebaut")
    print("  %d Uni-Seiten, %d Dateien insgesamt, %.1f MB" % (len(unis), pages, size / 1048576))
    print("  Startseite:   dist/index.html")
    print("  Beispiel-Uni: dist/uni/%s/index.html" % unis[0]["id"])
    print("  Admin (lokal, wird NICHT hochgeladen): admin.html")


# --------------------------------------------------------------------------
# Passwort
# --------------------------------------------------------------------------

def passwort():
    pw = sys.argv[2] if len(sys.argv) > 2 else getpass.getpass("Neues Admin-Passwort: ")
    if len(pw) < 8:
        print("Warnung: kürzer als 8 Zeichen.")
    h = hashlib.sha256(pw.encode("utf-8")).hexdigest()
    print("\nDiese Zeile in src/app.html ersetzen (im CONFIG-Block):\n")
    print('  adminPasswordHash: "%s",' % h)
    print("\nDanach: python3 build.py")


# --------------------------------------------------------------------------
# Prüfen
# --------------------------------------------------------------------------

def pruefen():
    if not os.path.isdir(DIST):
        sys.exit("dist/ fehlt – erst 'python3 build.py' ausführen.")
    problems, checked = [], 0

    for dp, _, files in os.walk(DIST):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            checked += 1
            p = os.path.join(dp, fn)
            t = open(p, encoding="utf-8").read()
            rel = os.path.relpath(p, DIST)
            if "<title>" not in t:            problems.append("%s: kein <title>" % rel)
            if 'name="description"' not in t: problems.append("%s: keine Beschreibung" % rel)
            if 'rel="canonical"' not in t:    problems.append("%s: kein Canonical" % rel)
            if t.count("<h1") != 1:           problems.append("%s: %d h1-Überschriften" % (rel, t.count("<h1")))
            if "adminPassword:" in t:         problems.append("%s: Klartext-Passwort!" % rel)

    for f in ("sitemap.xml", "robots.txt", "assets/app.js", "assets/data.js",
              "assets/style.css", "og.png", "index.html", "404.html"):
        if not os.path.exists(os.path.join(DIST, f)):
            problems.append("fehlt: " + f)

    sm = open(os.path.join(DIST, "sitemap.xml"), encoding="utf-8").read()
    for loc in re.findall(r"<loc>[^<]*/uni/([^<]+)</loc>", sm):
        if not os.path.exists(os.path.join(DIST, "uni", loc, "index.html")):
            problems.append("Sitemap zeigt auf fehlende Seite: /uni/%s" % loc)

    print("%d HTML-Dateien geprüft" % checked)
    if problems:
        print("\n%d Probleme:" % len(problems))
        for x in problems[:40]:
            print("  ✗", x)
        sys.exit(1)
    print("Keine Probleme gefunden.")


# --------------------------------------------------------------------------
# Lokale Admin-Oberfläche
# --------------------------------------------------------------------------

ADMIN_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Admin – %(name)s (lokal)</title>
<style>%(css)s
.local-banner{background:#fff8e6;border-bottom:1px solid #f5e2ac;color:#7a5b06;
  padding:10px 20px;font-size:13.5px;font-weight:600;text-align:center}
</style>
</head>
<body>
<div class="local-banner">Lokale Verwaltung — diese Datei gehört nicht auf den Server.</div>
<header class="site-head">
  <div class="wrap">
    <a class="logo" href="#/"><span class="logo-mark">🎓</span> %(name)s Admin</a>
    <div class="head-actions">
      <a class="btn btn-ghost btn-sm" href="#/">Vorschau</a>
      <a class="btn btn-primary btn-sm" href="#/admin">Verwaltung</a>
    </div>
  </div>
</header>
<main id="app"></main>
<footer class="site-foot">
  <div class="wrap"><span>Lokale Verwaltung · <span id="year"></span></span>
    <nav><a href="#/admin">Verwaltung</a></nav></div>
</footer>
<div id="modalRoot"></div>
<script>
%(data)s
%(app)s
%(admin)s
if(!location.hash) location.hash = "#/admin";
route();
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Sicherheitsprüfung des Auslieferungsordners
# --------------------------------------------------------------------------

VERBOTEN = [
    ("adminPassword",           "Passwort oder Hash in der Konfiguration"),
    ("function renderAdmin",    "Admin-Oberfläche"),
    ("function uniForm",        "Admin-Formular"),
    ("function groupForm",      "Gruppen-Formular"),
    ("function outreachText",   "Outreach-Generator"),
    ("function sha256",         "Passwort-Hashfunktion"),
    ("ersti2026",               "altes Klartext-Passwort"),
    ("STATUS =",                "Outreach-Status"),
]

# Domains, unter denen Gruppen-Einladungslinks laufen. Nach der Base64-
# Kodierung in public_data_js() darf keine davon noch im Klartext in dist/
# auftauchen – täte sie es doch, wäre die Verschleierung wirkungslos.
VERBOTENE_LINKS = [
    "chat.whatsapp.com/", "t.me/", "discord.gg/", "signal.group/",
]


def guard():
    """Bricht ab, wenn etwas in dist/ landet, das dort nicht hingehört."""
    treffer = []
    for dp, _, files in os.walk(DIST):
        for fn in files:
            if not fn.endswith((".html", ".js", ".css", ".json", ".xml", ".txt")):
                continue
            path = os.path.join(dp, fn)
            text = open(path, encoding="utf-8", errors="ignore").read()
            for needle, was in VERBOTEN:
                if needle in text:
                    treffer.append("%s enthält %s (%s)"
                                   % (os.path.relpath(path, DIST), was, needle))
            # Nur in den Uni-Seiten und in data.js prüfen – dort landet der
            # echte Link. app.js darf die Domainnamen weiterhin nennen (z. B.
            # als Platzhaltertext im Formular), das ist kein Leck.
            rel = os.path.relpath(path, DIST)
            if rel.startswith("uni" + os.sep) or rel == os.path.join("assets", "data.js"):
                for needle in VERBOTENE_LINKS:
                    if needle in text:
                        treffer.append("%s enthält einen Klartext-Gruppenlink (%s) – "
                                        "Base64-Kodierung hat nicht gegriffen" % (rel, needle))
    if os.path.exists(os.path.join(DIST, "admin.html")):
        treffer.append("dist/admin.html existiert")

    if treffer:
        print("\nSICHERHEITSPRÜFUNG FEHLGESCHLAGEN:")
        for t in treffer:
            print("  ✗", t)
        sys.exit("\nBuild abgebrochen – nichts hochladen.")
    print("Sicherheitsprüfung bestanden: kein Admin-Code und kein Passwort in dist/")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode in ("build", "bauen"):   build()
    elif mode == "passwort":         passwort()
    elif mode in ("pruefen", "check"): pruefen()
    else: sys.exit("Unbekannt: %s\nErlaubt: build, passwort, pruefen" % mode)
