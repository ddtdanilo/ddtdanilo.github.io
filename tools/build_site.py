#!/usr/bin/env python3
"""Render and check the public portfolio from data/site.json."""

import argparse
import hashlib
import html
import json
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "site.json"
LANGS = ("en", "es")
# Normalized phrase fingerprints keep excluded legacy terms out of public source.
DENY = {
    1: {'57de4cf40144bdf7d000', '97037ff68fa8d08e57d2'},
    2: {'c190fde1c4682ceb4315', '9fa6eb7fd238217792ee', '66fa2aeb903c3bf38882', '1a1444e3900ba88f9242', '6a0c96d0ab81498a7c55', 'a625159d18da57180b72', '679cb4fcca0d1459b9f0', '5f595928ac6efa09743b', '947df3347c3387082af1', '527a2116d23a3f8d643e'},
    3: {'66497516ac19a5292ad6', 'bc660f94bc5a9b24da7a', '5754fcd9613b913544e3', 'bb025635b509842ac6e8', 'a77afa60a125fc8c924e', '9c671efb72dc67d858d2', '46856abebeb99f69e116', '39e2faaf71b88dd35ae0', 'b780eef3fa55d9a7ab55', '9b36121bfd478e523194'},
    4: {'484255bf4a0d10e5edec', 'a6f6e13d0693b8a15e68', 'f80f041796ccb46ce7a1', '2e47983912d6f78c3b54', 'b0650210c310e8e2784c'},
}
EMAIL = re.compile(r"(?i)(?<![\w@])[\w.+%-]+@(?:[\w-]+\.)+[a-z]{2,}\b")
PHONE = re.compile(
    r"(?i)\btel:\+?\d|(?<![\w])\+\d{1,3}[\s.-]*(?:\d[\s().-]*){8,14}\d"
    r"|(?<![\w])\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)"
)


def esc(value):
    return html.escape(str(value), quote=True)


def pair(value):
    return {"en": value, "es": value}


def text(value, lang, tag="span", attrs=""):
    if isinstance(value, str):
        value = pair(value)
    return (
        f'<{tag}{attrs} data-en="{esc(value["en"])}" data-es="{esc(value["es"])}">'
        f'{esc(value[lang])}</{tag}>'
    )


def link(value, lang, url, classes="", attrs=""):
    style = f' class="{classes}"' if classes else ""
    return text(value, lang, "a", f' href="{esc(url)}"{style}{attrs}')


def paragraphs(items, lang):
    return "\n".join(text(item, lang, "p") for item in items)


def inline_markup(value):
    value = esc(value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)


def case_prose(value, lang):
    result = []
    for group in value[lang].split("\n\n"):
        lines = group.splitlines()
        if not lines:
            continue
        if len(lines) == 1 and lines[0].startswith("### "):
            result.append("<h3>" + inline_markup(lines[0][4:]) + "</h3>")
            continue
        if all(re.match(r"^(?:- |\d+\. )", line) for line in lines):
            tag = "ul" if lines[0].startswith("- ") else "ol"
            items = "".join("<li>" + inline_markup(re.sub(r"^(?:- |\d+\. )", "", line)) +
                            "</li>" for line in lines)
            result.append(f"<{tag}>{items}</{tag}>")
            continue
        result.append("<p>" + inline_markup(" ".join(lines)) + "</p>")
    return f'<div data-lang-block="{lang}">' + "\n".join(result) + "</div>"


def alt_attrs(value, lang):
    return (
        f' aria-label="{esc(value[lang])}" data-aria-en="{esc(value["en"])}"'
        f' data-aria-es="{esc(value["es"])}"'
    )


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def section(ident, title, lang, body, classes=""):
    return (
        f'<section class="band {classes}" id="{ident}" aria-labelledby="{ident}-heading">'
        + text(title, lang, "h2", f' id="{ident}-heading"')
        + "\n" + body + "\n</section>"
    )


def page_header(title, intro, lang):
    return '<header class="page-header">' + text(title, lang, "h1") + text(intro, lang, "p") + "</header>"


def svg_asset(path, lang):
    source = (ROOT / path).read_text().strip()
    if not source.startswith("<svg") or re.search(r"<(?:script|foreignObject)\b|\bon\w+\s*=", source, re.I):
        raise ValueError(f"Unexpected markup in {path}")

    return re.sub(r"<(text|tspan|title|desc)(\s[^<>]*?)?>([^<>]*)</\1>",
                  lambda match: svg_label(match, lang), source)


def svg_label(match, lang):
    tag, attrs, original = match[1], match[2] or "", match[3]
    label = re.search(rf'\bdata-{lang}="([^"]*)"', attrs)
    return f"<{tag}{attrs}>{label[1] if label else original}</{tag}>"


class Site:
    def __init__(self, data):
        self.data = data
        self.origin = data["origin"]
        self.name = data["person"]["name"]
        self.social = data["person"]["profiles"]
        self.copy = data["copy"]
        self.pages = data["pages"]
        self.cases = data["cases"]
        self.pairs = [item["paths"] for item in (*self.pages.values(), *self.cases) if "paths" in item]
        self.by_path = {path: pair_paths for pair_paths in self.pairs for path in pair_paths.values()}
        self.files = {}

    def url(self, path):
        return urljoin(self.origin, path)

    def asset(self, path):
        version = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:12]
        return f"/{path}?v={version}"

    def nav(self, lang, path, sibling):
        home = self.pages["home"]["paths"][lang]
        consult = self.pages["consult"]["paths"][lang]
        brand_label = pair(f"DDT · {self.name}")
        mark = svg_asset("assets/img/logo.svg", lang).replace(
            "<svg ", '<svg class="brand-mark" aria-hidden="true" focusable="false" ', 1
        ).replace(' role="img" aria-labelledby="title"', "").replace('<title id="title">DDT</title>', "")
        brand = (
            f'<a class="brand" href="{home}"{alt_attrs(brand_label, lang)}>'
            + mark
            + text(self.name, lang, attrs=' class="brand-name"') + "</a>"
        )
        main = "".join((
            link(self.copy["work"], lang, home + "#work"),
            link(self.copy["experience"], lang, home + "#experience"),
            link(self.copy["consult"], lang, consult,
                 attrs=' aria-current="page"' if path == consult else ""),
        ))
        other = "es" if lang == "en" else "en"
        locale = link(self.copy["locale"], lang, sibling, "locale",
                      f' lang="{other}" hreflang="{other}"')
        theme = (
            '<button type="button" id="theme-toggle" class="theme-toggle">'
            + text(self.copy["theme"], lang, attrs=' class="use-dark-theme"')
            + text(self.copy["theme_light"], lang, attrs=' class="use-light-theme"')
            + "</button>"
        )
        skip = link(self.copy["skip"], lang, "#main", "skip")
        return (
            f'{skip}<header class="site-header"><div class="wrap nav">{brand}'
            f'<nav class="nav-links"{alt_attrs(self.copy["primary_nav"], lang)}>{main}</nav>'
            f'<div class="nav-utilities">{locale}{theme}</div></div></header>'
        )

    def footer(self, lang):
        links = link(self.copy["privacy"], lang, self.pages["privacy"]["paths"][lang])
        links += "".join(link(network, lang, url) for network, url in self.social.items())
        return (
            '<footer class="site-footer"><div class="wrap footer-row">'
            + text(self.name, lang) + '<div class="footer-links">' + links + "</div></div></footer>"
        )

    def document(self, item, lang, body, schema=None, *, route=None, layout=""):
        indexed = route is None
        paths = item.get("paths", self.pages["home"]["paths"])
        path = route or paths[lang]
        title = item["meta"]["title"][lang]
        description = item["meta"]["description"][lang]
        og_title = item["meta"].get("og_title", item["meta"]["title"])[lang]
        og_description = item["meta"].get("og_description", item["meta"]["description"])[lang]
        other = "es" if lang == "en" else "en"
        alternate = paths[other]
        og_locale = {"en": "en_US", "es": "es_CO"}
        if indexed:
            alternates = "\n".join(
                f'<link rel="alternate" hreflang="{language}" href="{self.url(target)}">'
                for language, target in {**paths, "x-default": paths["en"]}.items()
            )
            crawl = f'<link rel="canonical" href="{self.url(path)}">\n{alternates}'
        else:
            crawl = '<meta name="robots" content="noindex, follow">'
        meta = f"""<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{crawl}
<meta property="og:type" content="{'article' if layout == 'case' else 'website'}">
<meta property="og:url" content="{self.url(path)}">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(og_description)}">
<meta property="og:image" content="{self.url('/assets/img/social.jpg')}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(self.copy['social_image'][lang])}">
<meta property="og:locale" content="{og_locale[lang]}">
<meta property="og:locale:alternate" content="{og_locale[other]}">
<meta name="twitter:card" content="summary_large_image">"""
        if schema:
            jsonld = json_text({"@context": "https://schema.org", **schema}).replace("<", "\\u003c")
            meta += f'\n<script type="application/ld+json">{jsonld}</script>'
        if indexed and path == paths[lang]:
            if layout in ("home", "consult"):
                twin = self.markdown_path(layout, lang)
                api = "resume.json" if layout == "home" else "consulting.json"
                meta += f'\n<link rel="alternate" type="text/markdown" href="/{twin}">'
                meta += f'\n<link rel="describedby" type="application/json" href="/api/{api}">'
            if layout == "home":
                meta += '\n<link rel="api-catalog" href="/.well-known/api-catalog">'
        script = (ROOT / "assets/js/main.js").read_text().strip()
        return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
{meta}
<script>{script}</script>
<link rel="preload" href="/assets/fonts/instrument-serif/InstrumentSerif-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/inter/inter-regular-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="{self.asset('assets/img/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{self.asset('assets/fonts/fonts.css')}">
<link rel="stylesheet" href="{self.asset('assets/css/tokens.css')}">
<link rel="stylesheet" href="{self.asset('assets/css/components.css')}">
<link rel="stylesheet" href="{self.asset('assets/css/style.css')}">
</head>
<body class="{layout}">
{self.nav(lang, path, alternate)}
<main id="main" class="wrap" tabindex="-1">
{body}
</main>
{self.footer(lang)}
</body>
</html>
"""

    @staticmethod
    def markdown_path(layout, lang):
        if layout == "home":
            return "index.md" if lang == "en" else "es/index.md"
        return "consult.md" if lang == "en" else "es/consultoria.md"

    def offer_id(self, lang, tier):
        return self.url(self.pages["consult"]["paths"][lang]) + "#offer-" + tier["id"]

    def person(self, lang):
        data = self.data["person"]
        return {
            "@type": "Person",
            "@id": self.url("/#person"),
            "name": self.name,
            "alternateName": data["alternate_names"],
            "jobTitle": data["role"][lang],
            "url": self.url("/"),
            "description": self.data["home"]["intro"][lang],
            "worksFor": {"@type": "Organization", "name": data["employer"], "url": data["employer_url"]},
            "sameAs": list(self.social.values()),
            "knowsLanguage": list(LANGS),
            "makesOffer": [{"@id": self.offer_id(lang, tier)} for tier in self.data["consult"]["tiers"]],
            "knowsAbout": [item["title"][lang] for item in self.data["home"]["expertise"]],
        }

    def home(self, lang):
        content = self.data["home"]
        home = self.pages["home"]["paths"][lang]
        consult = self.pages["consult"]["paths"][lang]
        art = content["illustration"]
        board = svg_asset("assets/img/hero-board.svg", lang)
        board = re.sub(r"<metadata>(.*?)</metadata>", r"<!--\1-->", board, flags=re.S)
        hero = (
            '<section class="hero" aria-labelledby="hero-heading">'
            + text(content["roleline"], lang, "p", ' class="hero-name"')
            + '<h1 id="hero-heading">' + text(content["headline"], lang) + " "
            + text(content["headline_end"], lang, "em") + "</h1>"
            + '<figure class="board-figure"><div class="board-stage">'
            + board
            + '</div><figcaption>'
            + link(art["caption"], lang, art["url"])
            + link(art["credit_label"], lang, art["license_url"], "board-credit")
            + "</figcaption></figure>"
            + text(content["intro"], lang, "p", ' class="hero-intro"')
            + text(content["availability"], lang, "p", ' class="hero-availability"')
            + '<div class="actions">' + link(self.copy["view_consult"], lang, consult, "btn btn-primary")
            + link(self.copy["view_work"], lang, "#work", "btn btn-secondary")
            + "</div></section>"
        )
        proof = '<dl class="proof-strip">' + "".join(
            "<div>" + text(item["value"], lang, "dt") + text(item["label"], lang, "dd") + "</div>"
            for item in content["proof"]
        ) + "</dl>"
        work_cards = "".join(
            self.card(case["title"], case["intro"], lang, case["paths"][lang])
            for case in self.cases
        )
        practice = "".join(
            '<li>' + text(item["title"], lang, "h3") + text(item["body"], lang, "p") + "</li>"
            for item in content["selected"]
        )
        work = section(
            "work", self.copy["selected_work"], lang,
            f'<div class="card-grid case-grid">{work_cards}</div><ul class="practice">{practice}</ul>'
        )
        experience = "<ol class=\"timeline\">" + "".join(
            "<li>" + text(item["dates"], lang, "p", ' class="dates"')
            + '<div>' + text(item["title"], lang, "h3") + text(item["org"], lang, "p", ' class="organization"')
            + text(item["body"], lang, "p") + "</div></li>"
            for item in content["experience"]
        ) + "</ol>"
        expertise = "".join(self.card(item["title"], item["body"], lang) for item in content["expertise"])
        projects = "".join(
            f'<li>{link(item["title"], lang, item["url"])}{text(item["body"], lang, "p")}</li>'
            for item in content["projects"]
        )
        about = '<div class="prose">' + paragraphs(content["about"], lang) + "</div>"
        price = min(tier["price"] for tier in self.data["consult"]["tiers"])
        from_price = {language: self.copy["from_price"][language].format(price=price) for language in LANGS}
        offer = (
            '<div class="offer-split"><div class="prose">'
            + paragraphs(content["consult_preview"], lang)
            + text(from_price, lang, "p", ' class="from-price"') + "</div>"
            + link(self.copy["view_consult"], lang, consult, "btn btn-primary") + "</div>"
        )
        contact = (
            '<div class="prose">' + paragraphs(content["contact"], lang)
            + link(self.copy["connect"], lang, self.social["LinkedIn"], "btn btn-secondary") + "</div>"
        )
        body = "\n".join((
            hero, proof, section("offer", self.copy["consult"], lang, offer),
            work, section("about", self.copy["about"], lang, about),
            section("experience", self.copy["experience"], lang, experience),
            section("expertise", self.copy["expertise"], lang, f'<div class="card-grid">{expertise}</div>'),
            section("projects", self.copy["open_source"], lang, f'<ul class="project-list">{projects}</ul>'),
            section("contact", self.copy["contact"], lang, contact),
        ))
        profile = {"@type": "ProfilePage", "@id": self.url(home) + "#page",
                   "url": self.url(home), "name": self.pages["home"]["meta"]["title"][lang],
                   "inLanguage": lang, "mainEntity": {"@id": self.url("/#person")}}
        return self.document(self.pages["home"], lang, body,
                             {"@graph": [profile, self.person(lang)]}, layout="home")

    def card(self, title, body, lang, url=None):
        heading = f'<h3>{link(title, lang, url, "card-link")}</h3>' if url else text(title, lang, "h3")
        action = text(self.copy["read_note"], lang, attrs=' class="note-action" aria-hidden="true"') if url else ""
        return '<article class="card">' + heading + text(body, lang, "p") + action + "</article>"

    def offer(self, tier, lang):
        label = {language: self.copy["pay"][language].format(price=tier["price"]) for language in LANGS}
        price = {language: self.copy["price"][language].format(price=tier["price"]) for language in LANGS}
        return (
            f'<article class="card price-card" id="offer-{esc(tier["id"])}">' + text(tier["title"], lang, "h3")
            + text(tier["duration"], lang, "p", ' class="duration"')
            + text(price, lang, "p", ' class="price"')
            + text(tier["scope"], lang, "p") + text(tier["outcome"], lang, "p", ' class="outcome"')
            + link(label, lang, tier["url"], "btn btn-secondary", ' rel="noreferrer"') + "</article>"
        )

    def consult(self, lang):
        data = self.data["consult"]
        item = self.pages["consult"]
        url = self.url(item["paths"][lang])
        steps = '<ol class="steps">' + "".join(
            '<li>' + text(step["title"], lang, "h3") + text(step["body"], lang, "p") + "</li>"
            for step in data["steps"]
        ) + "</ol>"
        faq = '<div class="faq">' + "".join(
            "<details>" + text(faq["question"], lang, "summary") + text(faq["answer"], lang, "p") + "</details>"
            for faq in data["faq"]
        ) + "</div>"
        body = page_header(data["title"], data["intro"], lang)
        body += section("booking", self.copy["how_it_works"], lang,
                        steps + '<div class="prose terms">' + paragraphs(data["terms"], lang) + "</div>")
        body += section("sessions", self.copy["sessions"], lang,
                        '<div class="card-grid price-grid">' + "".join(self.offer(t, lang) for t in data["tiers"]) + "</div>")
        body += section("faq", self.copy["faq"], lang, faq)
        body += section("other-work", self.copy["other_work"], lang,
                        '<div class="prose">' + paragraphs(data["other_work"], lang)
                        + link(self.copy["connect"], lang, self.social["LinkedIn"], "btn btn-secondary") + "</div>")
        service = {
            "@type": "Service", "@id": url + "#service", "url": url,
            "name": data["document_title"][lang], "serviceType": data["service_name"][lang],
            "description": data["intro"][lang],
            "provider": {"@type": "Person", "@id": self.url("/#person"), "name": self.name},
            "availableChannel": {"@type": "ServiceChannel", "availableLanguage": list(LANGS)},
            "offers": [{"@type": "Offer", "@id": self.offer_id(lang, tier), "name": tier["title"][lang],
                        "description": tier["outcome"][lang],
                        "price": tier["price"], "priceCurrency": "USD", "url": tier["url"]}
                       for tier in data["tiers"]],
        }
        page = {"@type": "WebPage", "@id": url + "#page", "url": url, "inLanguage": lang,
                "mainEntity": {"@id": service["@id"]}}
        return self.document(item, lang, body, {"@graph": [page, service]}, layout="consult")

    def case(self, item, lang):
        url = self.url(item["paths"][lang])
        image = item.get("image")
        body = (
            '<article class="prose case-note">'
            + link(self.copy["back_work"], lang, self.pages["home"]["paths"][lang] + "#work", "back-link")
            + page_header(item["title"], item["intro"], lang)
            + text(self.copy["by"], lang, "p", ' class="byline"')
        )
        if image:
            alt = image["alt"]
            responsive = ""
            if image.get("small_path"):
                responsive = (
                    f' srcset="{esc(image["small_path"])} 480w, {esc(image["path"])} {image["width"]}w"'
                    ' sizes="(max-width: 640px) calc(100vw - 32px), 62ch"'
                )
            body += (
                f'<figure class="case-figure"><img src="{esc(image["path"])}" alt="{esc(alt[lang])}"'
                + responsive
                + f' width="{image["width"]}" height="{image["height"]}" decoding="async" fetchpriority="high"'
                f' data-alt-en="{esc(alt["en"])}" data-alt-es="{esc(alt["es"])}">'
                + text(image["caption"], lang, "figcaption") + "</figure>"
            )
        for block in item["blocks"]:
            body += text(block["heading"], lang, "h2")
            body += "".join(case_prose(value, lang) for value in block["paragraphs"])
        body += text(self.copy["sources"], lang, "h2") + "<ul>" + "".join(
            f'<li>{link(item["label"], lang, item["url"])}</li>' for item in item["sources"]
        ) + "</ul>"
        body += link(self.copy["view_consult"], lang, self.pages["consult"]["paths"][lang],
                     "btn btn-secondary") + "</article>"
        article = {
            "@type": "Article", "@id": url + "#article", "mainEntityOfPage": url,
            "headline": item["title"][lang], "description": item["intro"][lang], "inLanguage": lang,
            "datePublished": item["date_published"], "dateModified": self.data["last_updated"],
            "image": self.url(image["path"] if image else "/assets/img/social.jpg"),
            "author": {"@type": "Person", "@id": self.url("/#person"), "name": self.name},
            "citation": [source["url"] for source in item["sources"]],
        }
        return self.document(item, lang, body, article, layout="case")

    def privacy(self, lang):
        data = self.data["privacy"]
        body = '<div class="prose">' + page_header(data["title"], data["intro"], lang)
        for block in data["blocks"]:
            body += text(block["heading"], lang, "h2") + paragraphs(block["paragraphs"], lang)
        body += link(self.copy["connect"], lang, self.social["LinkedIn"], "btn btn-secondary") + "</div>"
        return self.document(self.pages["privacy"], lang, body, layout="utility")

    def utility(self, key, route):
        data = self.data[key]
        body = ""
        for lang in LANGS:
            label = text(data["title"], lang, "h1" if lang == "en" else "h2", f' id="utility-{lang}"')
            action = link(self.copy["back_home"], lang, self.pages["home"]["paths"][lang], "btn btn-secondary")
            if key == "success":
                action += link(self.copy["connect"], lang, self.social["LinkedIn"], "btn btn-secondary")
            else:
                action += link(self.copy["view_consult"], lang, self.pages["consult"]["paths"][lang], "btn btn-secondary")
            body += (
                f'<section class="prose utility-block" lang="{lang}" aria-labelledby="utility-{lang}">'
                + label + paragraphs(data["paragraphs"], lang) + f'<div class="actions">{action}</div></section>'
            )
        return self.document(self.pages[key], "en", f'<div class="utility-content">{body}</div>',
                             route=route, layout="utility")

    def sitemap(self):
        sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
        updated = date.fromisoformat(self.data["last_updated"]).isoformat()
        for paths in self.pairs:
            for path in paths.values():
                sitemap.append("  <url>")
                sitemap.append(f"    <loc>{esc(self.url(path))}</loc>")
                sitemap.append(f"    <lastmod>{updated}</lastmod>")
                for lang, target in {**paths, "x-default": paths["en"]}.items():
                    sitemap.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{esc(self.url(target))}"/>')
                sitemap.append("  </url>")
        return "\n".join(sitemap + ["</urlset>", ""])

    def add_page(self, url, result):
        name = url.lstrip("/")
        self.files[name + "index.html" if url.endswith("/") else name] = result

    def render(self):
        for language in LANGS:
            for key, renderer in (("home", self.home), ("consult", self.consult), ("privacy", self.privacy)):
                self.add_page(self.pages[key]["paths"][language], renderer(language))
            for case in self.cases:
                self.add_page(case["paths"][language], self.case(case, language))
        self.add_page("/consult-success.html", self.utility("success", "/consult-success.html"))
        self.add_page("/404.html", self.utility("missing", "/404.html"))
        self.files["sitemap.xml"] = self.sitemap()
        self.files["robots.txt"] = self.data["crawler_policy"] + f'\nSitemap: {self.url("/sitemap.xml")}\n'
        self.machine_files()
        return self.files

    def portfolio_markdown(self, lang):
        content = self.data["home"]
        pages = self.pages
        lines = [f"# {self.name}", content["intro"][lang], content["availability"][lang],
                 f'[{self.copy["view_consult"][lang]}]({self.url(pages["consult"]["paths"][lang])})',
                 " · ".join(f'[{name}]({url})' for name, url in self.social.items()),
                 f'## {self.copy["about"][lang]}', *[p[lang] for p in content["about"]],
                 f'## {self.copy["selected_work"][lang]}']
        lines.extend(f'- [{case["title"][lang]}]({self.url(case["paths"][lang])}) — {case["intro"][lang]}'
                     for case in self.cases)
        lines.extend(f'- {item["title"][lang]} — {item["body"][lang]}' for item in content["selected"])
        lines.append(f'## {self.copy["experience"][lang]}')
        lines.extend(f'- {item["dates"][lang]} · {item["title"][lang]} · {item["org"][lang]} — {item["body"][lang]}'
                     for item in content["experience"])
        lines.append(f'## {self.copy["expertise"][lang]}')
        lines.extend(f'- {item["title"][lang]} — {item["body"][lang]}' for item in content["expertise"])
        lines.append(f'## {self.copy["open_source"][lang]}')
        lines.extend(f'- [{item["title"][lang]}]({item["url"]}) — {item["body"][lang]}'
                     for item in content["projects"])
        return "\n\n".join(lines) + "\n"

    def consult_markdown(self, lang):
        data = self.data["consult"]
        lines = [f'# {data["document_title"][lang]}', data["intro"][lang],
                 f'[{self.copy["consult"][lang]}]({self.url(self.pages["consult"]["paths"][lang])})',
                 f'## {self.copy["how_it_works"][lang]}']
        lines.extend(f'{i}. {step["title"][lang]}. {step["body"][lang]}'
                     for i, step in enumerate(data["steps"], 1))
        lines.extend(item[lang] for item in data["terms"])
        lines.append(f'## {self.copy["sessions"][lang]}')
        for tier in data["tiers"]:
            price = self.copy["price"][lang].format(price=tier["price"])
            lines.extend((f'### {tier["title"][lang]} · {tier["duration"][lang]} · {price}',
                          tier["scope"][lang], tier["outcome"][lang],
                          f'[{self.copy["pay"][lang].format(price=tier["price"])}]({tier["url"]})'))
        lines.append(f'## {self.copy["faq"][lang]}')
        for item in data["faq"]:
            lines.extend((f'### {item["question"][lang]}', item["answer"][lang]))
        lines.append(f'[LinkedIn]({self.social["LinkedIn"]})')
        return "\n\n".join(lines) + "\n"

    def case_markdown(self, item, lang):
        lines = [f'# {item["title"][lang]}', item["intro"][lang],
                 f'<{self.url(item["paths"][lang])}>']
        for block in item["blocks"]:
            lines.extend((f'## {block["heading"][lang]}', *[p[lang] for p in block["paragraphs"]]))
        lines.append(f'## {self.copy["sources"][lang]}')
        lines.extend(f'- [{source["label"][lang]}]({source["url"]})' for source in item["sources"])
        return "\n\n".join(lines) + "\n"

    def machine_files(self):
        content = self.data["home"]
        for lang in LANGS:
            self.files[self.markdown_path("home", lang)] = self.portfolio_markdown(lang)
            self.files[self.markdown_path("consult", lang)] = self.consult_markdown(lang)
        self.files["llms-full.txt"] = "\n---\n\n".join(
            part for lang in LANGS
            for part in (self.portfolio_markdown(lang), self.consult_markdown(lang),
                         *[self.case_markdown(case, lang) for case in self.cases])
        )
        llms = [f"# {self.name}", f'> {content["intro"]["en"]}', "",
                "## Profile and consulting"]
        for lang in LANGS:
            for key in ("home", "consult"):
                page = self.pages[key]
                llms.append(f'- [{page["meta"]["title"][lang]}]({self.url(page["paths"][lang])})')
            for case in self.cases:
                llms.append(f'- [{case["title"][lang]}]({self.url(case["paths"][lang])})')
        llms += ["", "## Other public formats",
                 f'- [Portfolio Markdown]({self.url("/index.md")})',
                 f'- [Consulting Markdown]({self.url("/consult.md")})',
                 f'- [Portafolio en Markdown]({self.url("/es/index.md")})',
                 f'- [Consultoría en Markdown]({self.url("/es/consultoria.md")})',
                 f'- [API catalog]({self.url("/.well-known/api-catalog")})',
                 f'- [OpenAPI description]({self.url("/api/openapi.json")})',
                 f'- [Bilingual profile, offers and case notes]({self.url("/llms-full.txt")})',
                 f'- [Resume JSON]({self.url("/api/resume.json")})',
                 f'- [Consulting JSON]({self.url("/api/consulting.json")})']
        self.files["llms.txt"] = "\n".join(llms) + "\n"

        resume = {
            "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
            "basics": {"name": self.name, "label": self.data["person"]["role"]["en"],
                       "url": self.url("/"),
                       "summary": content["intro"]["en"], "location": self.data["person"]["location"],
                       "profiles": [{"network": network, "url": url} for network, url in self.social.items()]},
            "work": [{"name": item["org"]["en"], "position": item["title"]["en"], "startDate": item["start"],
                      **({"endDate": item["end"]} if item.get("end") else {}), "highlights": [item["body"]["en"]]}
                     for item in content["experience"]],
            "projects": [{"name": item["title"]["en"], "description": item["body"]["en"], "url": item["url"]}
                         for item in content["projects"]] +
                        [{"name": case["title"]["en"], "description": case["intro"]["en"],
                          "url": self.url(case["paths"]["en"])} for case in self.cases],
            "skills": [{"name": item["title"]["en"], "keywords": item["keywords"]}
                       for item in content["expertise"]],
            "languages": [{"language": "Spanish", "fluency": "Native"}, {"language": "English", "fluency": "C1+"}],
            "awards": self.data["person"]["awards"],
            "education": self.data["person"]["education"],
        }
        consult = self.data["consult"]
        consulting = {
            "provider": self.name, "page": self.url(self.pages["consult"]["paths"]["en"]),
            "locales": {lang: self.url(path) for lang, path in self.pages["consult"]["paths"].items()},
            "currency": "USD", "format": "1:1 Google Meet session, English or Spanish",
            "flow": [step["body"]["en"] for step in consult["steps"]],
            "terms": consult["terms"], "scheduling": "manual",
            "sessions": [{"id": tier["id"], "name": tier["title"]["en"], "minutes": tier["minutes"],
                          "price": tier["price"], "covers": tier["scope"]["en"], "booking_url": tier["url"],
                          "nameLocalized": tier["title"], "scope": tier["scope"], "outcome": tier["outcome"]}
                         for tier in consult["tiers"]],
        }
        outputs = {"resume.json": resume, "consulting.json": consulting}
        for name, obj in outputs.items():
            self.files["api/" + name] = json_text(obj)
        paths = {}
        for name in outputs:
            paths["/api/" + name] = {
                "get": {"summary": name.removesuffix(".json").capitalize(),
                        "responses": {"200": {"description": "Public record",
                                               "content": {"application/json": {"schema": {"type": "object"}}}}}}
            }
        self.files["api/openapi.json"] = json_text({
            "openapi": "3.1.0", "info": {"title": self.name + " public profile", "version": "1.0.0"},
            "servers": [{"url": self.origin}], "paths": paths,
        })
        catalog = {
            "anchor": self.url("/api/openapi.json"),
            "service-desc": [{"href": self.url("/api/openapi.json"), "type": "application/openapi+json"}],
            "service-doc": [{"href": self.url("/llms.txt"), "type": "text/plain"}],
            "item": [{"href": self.url("/api/" + name), "type": "application/json"} for name in outputs],
        }
        self.files[".well-known/api-catalog"] = json_text({"linkset": [catalog]})
        skills = []
        for ident, description, paths in (
            ("danilo-profile", "Find and cite public profile and engineering work.",
             ["/", "/es/", "/index.md", "/es/index.md", "/api/resume.json",
              *[path for case in self.cases for path in case["paths"].values()]]),
            ("book-consulting", "Compare and cite consulting sessions and scheduling terms.",
             ["/consult.html", "/es/consultoria.html", "/consult.md", "/es/consultoria.md", "/api/consulting.json"]),
        ):
            path = f"/.well-known/agent-skills/{ident}/SKILL.md"
            details = "Cite the canonical pages below. Contact is through LinkedIn."
            if ident == "book-consulting":
                details += " Scheduling is manual after Stripe payment. Obtain the buyer's approval before any payment."
            body = (f"---\nname: {ident}\ndescription: {description}\n---\n\n# {description}\n\n{details}\n\n"
                    + "".join(f"- <{self.url(target)}>\n" for target in paths))
            self.files[path.lstrip("/")] = body
            skills.append({"name": ident, "type": "skill-md", "description": description, "url": path,
                           "digest": "sha256:" + hashlib.sha256(body.encode()).hexdigest()})
        self.files[".well-known/agent-skills/index.json"] = json_text({
            "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json", "skills": skills,
        })
        self.files[".well-known/ai-catalog.json"] = json_text({
            "specVersion": "1.0",
            "host": {"displayName": self.name, "identifier": "did:web:" + urlsplit(self.origin).hostname,
                     "url": self.url("/")},
            "entries": [{"identifier": "urn:air:" + urlsplit(self.origin).hostname + ":" + label,
                         "displayName": label, "url": self.url(path), "type": media}
                        for label, path, media in (
                            ("skills", "/.well-known/agent-skills/index.json", "application/json"),
                            ("catalog", "/.well-known/api-catalog", "application/linkset+json"),
                            ("reference", "/llms.txt", "text/plain"),
                        )],
        })
        self.files["auth.md"] = (
            f"# Public resources\n\nThe portfolio and public records require no authentication.\n\n"
            f"- [Portfolio]({self.url('/')})\n- [Public catalog]({self.url('/.well-known/api-catalog')})\n"
            f"- [Consulting terms]({self.url('/consult.html')})\n"
        )


class PageLinks(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.alternates = {}
        self.canonicals = []
        self.language = None
        self.robots = set()
        self.feed(source)

    def handle_starttag(self, tag, items):
        attrs = dict(items)
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "meta" and attrs.get("name") == "robots":
            self.robots.update(value.strip() for value in attrs["content"].split(","))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.links.append(attrs[key])
        if "srcset" in attrs:
            self.links.extend(part.strip().split()[0] for part in attrs["srcset"].split(","))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs["href"])
        if tag == "link" and attrs.get("rel") == "alternate" and "hreflang" in attrs:
            self.alternates[attrs["hreflang"]] = attrs["href"]
        if tag == "meta" and attrs.get("property") == "og:image":
            self.links.append(attrs["content"])


def fingerprint(words):
    return hashlib.sha256(" ".join(words).encode()).hexdigest()[:20]


def normalized_words(value):
    ascii_text = unicodedata.normalize("NFKD", unquote(html.unescape(value))).encode("ascii", "ignore")
    return re.findall(r"[a-z0-9]+", ascii_text.decode().lower())


def privacy_check(name, contents):
    problems = []
    if EMAIL.search(contents):
        problems.append(f"{name}: email-like string")
    if PHONE.search(contents):
        problems.append(f"{name}: phone-like string")
    words = normalized_words(contents)
    for width, fingerprints in DENY.items():
        if any(fingerprint(words[i:i + width]) in fingerprints for i in range(len(words) + 1 - width)):
            problems.append(f"{name}: excluded legacy content")
            break
    return problems


def tracked_text():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    extensions = {".css", ".html", ".js", ".json", ".md", ".mjs", ".svg", ".toml", ".txt", ".xml"}
    for name in filter(None, names):
        path = ROOT / name
        if path.is_file() and (path.suffix in extensions or name == ".well-known/api-catalog"):
            yield name, path.read_text()


def filename(url_path):
    path = unquote(url_path).lstrip("/")
    return path + "index.html" if url_path.endswith("/") else path


def validate(site, files):
    problems = []
    all_files = dict(tracked_text())
    all_files.update(files)
    all_files["data/site.json"] = SOURCE.read_text()
    for name, source in all_files.items():
        problems.extend(privacy_check(name, source))
    pages = {name: PageLinks(source) for name, source in files.items() if name.endswith(".html")}
    for path, alternates in site.by_path.items():
        page = pages[filename(path)]
        expected = {lang: site.url(target) for lang, target in {**alternates, "x-default": alternates["en"]}.items()}
        language = next(lang for lang, target in alternates.items() if target == path)
        if (page.alternates != expected or page.canonicals != [site.url(path)]
                or page.language != language or "noindex" in page.robots):
            problems.append(f"{path}: canonical or language pair mismatch")
        for target in alternates.values():
            if pages[filename(target)].alternates.get(language) != site.url(path):
                problems.append(f"{path}: missing reciprocal alternate")
    for name in ("consult-success.html", "404.html"):
        if "noindex" not in pages[name].robots or pages[name].alternates:
            problems.append(f"{name}: utility should be excluded from indexing")
    for name, source in all_files.items():
        if name in pages:
            page = pages[name]
            if len(page.ids) != len(set(page.ids)):
                problems.append(f"{name}: duplicate element id")
            links = page.links
        elif name in files and name.endswith((".json", ".txt", ".md")):
            links = re.findall(re.escape(site.origin) + r'/[^"\'<>\s)]+', source)
        else:
            continue
        origin_url = site.url("/" + name)
        for href in links:
            target = urlsplit(urljoin(origin_url, href))
            if target.netloc != urlsplit(site.origin).netloc or target.scheme not in ("http", "https"):
                continue
            path = filename(target.path)
            if path not in files and not (ROOT / path).is_file():
                problems.append(f"{name}: missing local link {target.path}")
            if target.fragment and path in pages and unquote(target.fragment) not in pages[path].ids:
                problems.append(f"{name}: broken fragment {target.path}#{target.fragment}")
    index = ElementTree.fromstring(files["sitemap.xml"])
    sitemap_entries = {url.findtext("{*}loc"): url for url in index}
    if set(sitemap_entries) != {site.url(path) for path in site.by_path}:
        problems.append("sitemap.xml: indexed URLs do not match canonical pages")
    for path, pair_paths in site.by_path.items():
        entry = sitemap_entries.get(site.url(path))
        if entry is None:
            continue
        expected = {lang: site.url(target) for lang, target in {**pair_paths, "x-default": pair_paths["en"]}.items()}
        alternates = {item.attrib["hreflang"]: item.attrib["href"] for item in entry.findall("{*}link")}
        if alternates != expected or entry.findtext("{*}lastmod") != site.data["last_updated"]:
            problems.append(f"sitemap.xml: alternates or lastmod mismatch for {path}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify that committed outputs match the source")
    args = parser.parse_args()
    site = Site(json.loads(SOURCE.read_text()))
    files = site.render()
    problems = validate(site, files)
    if args.check:
        for name, contents in files.items():
            path = ROOT / name
            if not path.is_file() or path.read_text() != contents:
                problems.append(f"{name}: generated output is missing or stale")
    if problems:
        parser.exit(1, "\n".join(sorted(set(problems))) + "\n")
    if not args.check:
        for name, contents in files.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
    print(f"{len(files)} deterministic outputs {'checked' if args.check else 'written'}")


if __name__ == "__main__":
    main()
