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

import build_board


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "site.json"
BOARD_SOURCE = ROOT / "data" / "xsub" / "mcu.kicad_pcb"
SOCIAL_IMAGE = "/assets/img/social-fde.jpg"
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


def text(value, tag="span", attrs=""):
    return f'<{tag}{attrs}>{esc(value)}</{tag}>'


def link(value, url, classes="", attrs=""):
    style = f' class="{classes}"' if classes else ""
    return text(value, "a", f' href="{esc(url)}"{style}{attrs}')


def paragraphs(items):
    return "\n".join(text(item, "p") for item in items)


def inline_markup(value):
    value = esc(value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)


def case_prose(value):
    result = []
    for group in value.split("\n\n"):
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
    return '<div class="case-block">' + "\n".join(result) + "</div>"


def label_attr(value):
    return f' aria-label="{esc(value)}"'


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def section(ident, title, body, classes=""):
    return (
        f'<section class="band {classes}" id="{ident}" aria-labelledby="{ident}-heading">'
        + text(title, "h2", f' id="{ident}-heading" class="section-head--trace"')
        + "\n" + body + "\n</section>"
    )


def page_header(title, intro):
    return '<header class="page-header">' + text(title, "h1") + text(intro, "p") + "</header>"


def svg_asset(path):
    source = (ROOT / path).read_text().strip()
    if not source.startswith("<svg") or re.search(r"<(?:script|foreignObject)\b|\bon\w+\s*=", source, re.I):
        raise ValueError(f"Unexpected markup in {path}")
    return source


class Site:
    def __init__(self, data):
        self.data = data
        self.origin = data["origin"]
        self.name = data["person"]["name"]
        self.social = data["person"]["profiles"]
        self.copy = data["copy"]
        self.pages = data["pages"]
        self.cases = data["cases"]
        self.indexed = [item["path"] for item in (*self.pages.values(), *self.cases) if "path" in item]
        self.redirects = data["redirects"]
        self.board_svg, board_json = build_board.build(build_board.parse(BOARD_SOURCE.read_text(encoding="utf-8")))
        self.board = json.loads(board_json)
        self.path_svg = svg_asset("assets/img/path.svg")
        self.path_figure_data = json.loads((ROOT / "data/path.json").read_text(encoding="utf-8"))
        stage_ids = [stage["id"] for stage in self.path_figure_data["stages"]]
        svg_stages = {elem.get("data-stage") for elem in ElementTree.fromstring(self.path_svg).iter()
                      if elem.get("data-stage")}
        if len(stage_ids) != 7 or len(set(stage_ids)) != 7 or set(stage_ids) != svg_stages:
            raise ValueError("The path SVG and seven stage descriptions must match")
        self.files = {"assets/img/xsub-board.svg": self.board_svg, "assets/img/board.json": board_json}

    def url(self, path):
        return urljoin(self.origin, path)

    def asset(self, path):
        version = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:12]
        return f"/{path}?v={version}"

    def nav(self, path):
        home = self.pages["home"]["path"]
        consult = self.pages["consult"]["path"]
        mark = svg_asset("assets/img/logo.svg").replace(
            "<svg ", '<svg class="brand-mark" aria-hidden="true" focusable="false" ', 1
        ).replace(' role="img" aria-labelledby="title"', "").replace('<title id="title">DDT</title>', "")
        brand = (
            f'<a class="brand" href="{home}"{label_attr(f"DDT · {self.name}")}>'
            + mark + text(self.name, attrs=' class="brand-name"') + "</a>"
        )
        main = "".join((
            link(self.copy["work"], home + "#work"),
            link(self.copy["experience"], home + "#experience"),
            link(self.copy["consult"], consult, attrs=' aria-current="page"' if path == consult else ""),
        ))
        theme = (
            '<button type="button" id="theme-toggle" class="theme-toggle">'
            + text(self.copy["theme"], attrs=' class="use-dark-theme"')
            + text(self.copy["theme_light"], attrs=' class="use-light-theme"')
            + "</button>"
        )
        skip = link(self.copy["skip"], "#main", "skip")
        return (
            f'{skip}<header class="site-header"><div class="wrap nav">{brand}'
            f'<nav class="nav-links"{label_attr(self.copy["primary_nav"])}>{main}</nav>'
            f'<div class="nav-utilities">{theme}</div></div></header>'
        )

    def footer(self):
        links = link(self.copy["privacy"], self.pages["privacy"]["path"])
        links += "".join(link(network, url) for network, url in self.social.items())
        return (
            '<footer class="site-footer"><div class="wrap footer-row">'
            + text(self.name) + '<div class="footer-links">' + links + "</div></div></footer>"
        )

    def document(self, item, body, schema=None, *, route=None, layout="", interactive_figure=False):
        indexed = route is None
        path = item["path"] if indexed else route
        title = item["meta"]["title"]
        description = item["meta"]["description"]
        og_title = item["meta"].get("og_title", title)
        og_description = item["meta"].get("og_description", description)
        crawl = (
            f'<link rel="canonical" href="{self.url(path)}">' if indexed
            else '<meta name="robots" content="noindex, follow">'
        )
        meta = f"""<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{crawl}
<meta property="og:type" content="{'article' if layout == 'case' else 'website'}">
<meta property="og:url" content="{self.url(path)}">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(og_description)}">
<meta property="og:image" content="{self.url(SOCIAL_IMAGE)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(self.copy['social_image'])}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">"""
        if schema:
            jsonld = json_text({"@context": "https://schema.org", **schema}).replace("<", "\\u003c")
            meta += f'\n<script type="application/ld+json">{jsonld}</script>'
        if indexed:
            if layout in ("home", "consult"):
                twin = self.markdown_path(layout)
                api = "resume.json" if layout == "home" else "consulting.json"
                meta += f'\n<link rel="alternate" type="text/markdown" href="/{twin}">'
                meta += f'\n<link rel="describedby" type="application/json" href="/api/{api}">'
            if layout == "home":
                meta += '\n<link rel="api-catalog" href="/.well-known/api-catalog">'
        script = (ROOT / "assets/js/main.js").read_text().strip()
        figure_script = (ROOT / "assets/js/figure.js").read_text().strip() if interactive_figure else ""
        figure_script = f"<script>{figure_script}</script>" if figure_script else ""
        stylesheets = ("assets/css/tokens.css", "assets/css/components.css", "assets/css/style.css")
        if interactive_figure:
            # Start layout without waiting for three stylesheet responses while the inline figure arrives.
            styles = "<style>\n" + "\n".join((ROOT / path).read_text() for path in stylesheets) + "</style>"
        else:
            styles = "\n".join(f'<link rel="stylesheet" href="{self.asset(path)}">' for path in stylesheets)
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<script>{script}</script>
<link rel="stylesheet" href="{self.asset('assets/fonts/fonts.css')}">
<link rel="preload" href="/assets/fonts/instrument-serif/InstrumentSerif-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/inter/inter-regular-latin.woff2" as="font" type="font/woff2" crossorigin>
{meta}
<link rel="icon" href="{self.asset('assets/img/favicon.svg')}" type="image/svg+xml">
{styles}
</head>
<body class="{layout}">
{self.nav(path)}
<main id="main" class="wrap" tabindex="-1">
{body}
</main>
{self.footer()}
{figure_script}
</body>
</html>
"""

    @staticmethod
    def markdown_path(layout):
        return "index.md" if layout == "home" else "consult.md"

    def offer_id(self, tier):
        return self.url(self.pages["consult"]["path"]) + "#offer-" + tier["id"]

    def person(self):
        data = self.data["person"]
        return {
            "@type": "Person",
            "@id": self.url("/#person"),
            "name": self.name,
            "alternateName": data["alternate_names"],
            "jobTitle": data["role"],
            "hasOccupation": {
                "@type": "Occupation", "name": data["positioning"], "skills": data["occupation_topics"],
            },
            "url": self.url("/"),
            "description": self.data["home"]["intro"],
            "worksFor": {"@type": "Organization", "name": data["employer"], "url": data["employer_url"]},
            "sameAs": list(self.social.values()),
            "knowsLanguage": "en",
            "makesOffer": [{"@id": self.offer_id(tier)} for tier in self.data["consult"]["tiers"]],
            "knowsAbout": data["occupation_topics"],
        }

    def spec_table(self, rows, title=None):
        entries = "".join(
            "<tr>" + text(row["label"], "th", ' scope="row"') + text(row["value"], "td") + "</tr>"
            for row in rows
        )
        return (
            '<table class="spec-table">' + text(title or self.copy["specifications"], "caption")
            + "<tbody>" + entries + "</tbody></table>"
        )

    def board_values(self):
        spec = self.board["spec"]
        return {**spec, "width_mm": f'{spec["width_mm"]:.1f}', "height_mm": f'{spec["height_mm"]:.1f}'}

    def board_specs(self):
        values = self.board_values()
        values["dimensions"] = "{width_mm} × {height_mm} mm".format(**values)
        return [{"label": label, "value": str(values[key])} for key, label in self.data["board"]["specs"].items()]

    def signal_controls(self, heading, resting_label, resting_note, signals, *, aligned=False):
        reset = (
            '<button type="button" class="signal" data-signal="" aria-pressed="true">'
            + text(resting_label, attrs=' class="signal-label"') + '</button>'
        )
        buttons = "" if aligned else f"<li>{reset}</li>"
        legend = ""
        for item in signals:
            target = item.get("nets", item["id"])
            buttons += (
                f'<li><button type="button" class="signal" data-signal="{esc(item["id"])}" '
                f'data-targets="{esc(target)}" data-note="{esc(item["sentence"])}" aria-pressed="false">'
                + text(item["label"], attrs=' class="signal-label"')
                + text(item["tag"].replace(" · ", "\u2009·\u2009") if aligned else item["tag"],
                       attrs=' class="signal-nets" aria-hidden="true"')
                + '</button></li>'
            )
            legend += "<div>" + text(item["label"], "dt") + text(item["sentence"], "dd") + "</div>"
        heading_class = "visually-hidden" if aligned else "board-label"
        panel = (
            '<div class="tech-panel board-interactive">'
            + text(heading, "h2", f' id="figure-signals" class="{heading_class}"')
            + '<ul class="signal-list" role="list" aria-labelledby="figure-signals">' + buttons + "</ul>"
            + (f'<div class="path-reset">{reset}</div>' if aligned else "")
            + text(resting_note, "p", ' class="signal-note"')
            + '<p class="signal-status visually-hidden" role="status" aria-atomic="true"></p></div>'
        )
        fallback = (
            '<details class="board-legend">' + text(heading, "summary") + "<dl>" + legend + "</dl></details>"
        )
        return panel, fallback

    def path_figure(self):
        panel, fallback = self.signal_controls(
            self.copy["whole_path"], self.copy["all_stages"], self.copy["path_rest"],
            self.path_figure_data["stages"], aligned=True,
        )
        return (
            '<figure class="tech-figure path-figure" data-trace>'
            + '<div class="path-stage">' + self.path_svg + "</div>"
            + panel + text(self.copy["path_caption"], "figcaption") + fallback + "</figure>"
        )

    def board_figure(self):
        copy = self.data["board"]
        values = self.board_values()
        desc = copy["description"].format(**values)
        caption = copy["caption"].format(**values)
        svg = ElementTree.fromstring(self.board_svg)
        _, _, width, height = svg.attrib["viewBox"].split()
        ns = "http://www.w3.org/2000/svg"
        ElementTree.register_namespace("", ns)
        svg_style = ElementTree.tostring(svg.find(f"{{{ns}}}style"), encoding="unicode")
        layer_sets = {
            "substrate": (("substrate", "zones", "drill", "Edge.Cuts"), 0),
            "B.Cu": (("B.Cu",), 1),
            "F.Cu": (("F.Cu",), 2),
            "F.SilkS": (("F.SilkS",), 3),
        }
        layers_by_name = {layer.attrib["data-layer"]: layer for layer in svg.findall(f"{{{ns}}}g")}
        layers = "".join(
            f'<svg class="board xsub-board tech-layer" viewBox="{svg.attrib["viewBox"]}" '
            f'data-layer="{plane}" style="--i:{depth}" '
            'aria-hidden="true" focusable="false">'
            + (svg_style if depth == 0 else "")
            + "".join(
                ElementTree.tostring(layers_by_name[layer], encoding="unicode")
                for layer in names
            )
            + "</svg>"
            for plane, (names, depth) in layer_sets.items()
        )
        groups = self.board["signals"]
        if set(groups) != set(copy["groups"]):
            raise ValueError("The X-Sub net groups and copy must match")
        signals = [
            {"id": group, "nets": " ".join(nets), **copy["groups"][group]} for group, nets in groups.items()
        ]
        panel, fallback = self.signal_controls(copy["trace"], copy["all"], copy["rest"], signals)
        return (
            '<figure class="tech-figure tech-figure--case" data-trace aria-labelledby="board-caption">'
            + f'<div class="tech-stage"><div id="board-stack" class="tech-board" style="aspect-ratio:{width}/{height}" role="img"'
            + label_attr(copy["title"]) + ' aria-describedby="board-desc">'
            + build_board.LICENCE + layers + "</div>"
            + text(desc, "p", ' id="board-desc" class="visually-hidden"') + "</div>"
            + panel + '<figcaption><div id="board-caption">' + text(caption)
            + '<span class="board-sources">' + link(copy["source_label"], copy["source_url"])
            + link(copy["license_label"], copy["license_url"]) + "</span></div>"
            + '<button type="button" class="btn btn-secondary board-interactive board-layers" '
            + f'data-spread data-stack-label="{esc(copy["stack"])}" aria-controls="board-stack">'
            + text(copy["layers"]) + "</button></figcaption>"
            + '<div class="board-specs">' + self.spec_table(self.board_specs()) + "</div>"
            + fallback + "</figure>"
        )

    def gateway_figure(self, feature):
        controls = "".join(
            f'<button type="button" class="btn btn-secondary" data-gateway-route="{route}" '
            f'aria-pressed="{str(not route).lower()}">{label}</button>'
            for route, label in (("", "Both paths"), ("read", "Read path"), ("write", "Write path"))
        )
        return (
            '<figure class="gateway-figure" data-gateway>'
            + svg_asset("assets/img/gateway.svg") + text(feature["figure_caption"], "figcaption")
            + '<div class="gateway-controls board-interactive" role="group" aria-label="Highlight a gateway path">'
            + controls + "</div>"
            + "</figure>"
        )

    def featured_work(self):
        feature = self.data["featured"]
        body = (
            '<div class="prose">' + paragraphs(feature["paragraphs"]) + "</div>"
            + '<div class="feature-grid">' + self.gateway_figure(feature)
            + self.spec_table(feature["controls"], self.copy["security_controls"])
            + "</div>"
            + link(self.copy["read_note"], feature["path"], "btn btn-secondary")
        )
        return section("plant-operations", feature["title"], body, "featured-work")

    def home(self):
        content = self.data["home"]
        page = self.pages["home"]
        hero = (
            '<section class="hero" aria-labelledby="hero-heading">'
            + text(content["roleline"], "p", ' class="hero-name"')
            + '<h1 id="hero-heading">' + esc(content["headline"]) + " "
            + text(content["headline_end"], "em") + "</h1>"
            + text(content["intro"], "p", ' class="hero-intro"')
            + text(content["proof_line"], "p", ' class="hero-availability"')
            + '<div class="actions">'
            + link(self.copy["view_consult"], self.pages["consult"]["path"], "btn btn-primary")
            + link(self.copy["view_work"], "#how-i-work", "btn btn-secondary")
            + "</div>" + self.path_figure() + "</section>"
        )
        proof = '<dl class="proof-strip">' + "".join(
            "<div>" + text(item["value"], "dt") + text(item["label"], "dd") + "</div>"
            for item in content["proof"]
        ) + "</dl>"
        method = '<ol class="steps work-steps">' + "".join(
            "<li>" + text(item["title"], "h3") + text(item["body"], "p") + "</li>"
            for item in content["working_method"]
        ) + "</ol>"
        selected = "".join(
            self.card(item["title"], item["body"], item["url"], action_label=item.get("action"))
            for item in content["selected"]
        )
        public_work = "".join(
            self.card(case["title"], case["card_intro"], case["path"], period=case["period"])
            for case in self.cases if not case.get("featured")
        )
        experience = '<ol class="timeline">' + "".join(
            "<li>" + text(item["dates"], "p", ' class="dates"')
            + "<div>" + text(item["title"], "h3") + text(item["org"], "p", ' class="organization"')
            + text(item["body"], "p") + "</div></li>"
            for item in content["experience"]
        ) + "</ol>"
        expertise = '<div class="card-grid capabilities-grid">' + "".join(
            self.card(item["title"], item["body"], ident=item.get("id")) for item in content["capabilities"]
        ) + '</div>'
        projects = "".join(
            f'<li>{link(item["title"], item["url"])}{text(item["body"], "p")}</li>'
            for item in content["projects"]
        )
        about = '<div class="prose">' + paragraphs(content["about"]) + "</div>"
        price = min(tier["price"] for tier in self.data["consult"]["tiers"])
        offer = (
            '<div class="offer-split"><div class="prose">'
            + paragraphs(content["consult_preview"])
            + text(self.copy["from_price"].format(price=price), "p", ' class="from-price"') + "</div>"
            + link(self.copy["view_consult"], self.pages["consult"]["path"], "btn btn-primary") + "</div>"
            + self.engagements(compact=True)
        )
        contact = (
            '<div class="prose">' + paragraphs(content["contact"])
            + link(self.copy["connect"], self.social["LinkedIn"], "btn btn-secondary") + "</div>"
        )
        body = "\n".join((
            hero, proof, self.featured_work(),
            section("how-i-work", self.copy["working_method"], method),
            section("expertise", self.copy["expertise"], expertise),
            section("offer", self.copy["consult"], offer),
            section("work", self.copy["selected_work"], '<div class="card-grid selected-grid">' + selected + "</div>"),
            section("public-work", self.copy["public_work"], '<div class="card-grid case-grid">' + public_work + "</div>"),
            section("about", self.copy["about"], about),
            section("experience", self.copy["experience"], experience),
            section("projects", self.copy["open_source"], f'<ul class="project-list">{projects}</ul>'),
            section("contact", self.copy["contact"], contact),
        ))
        profile = {"@type": "ProfilePage", "@id": self.url(page["path"]) + "#page",
                   "url": self.url(page["path"]), "name": page["meta"]["title"],
                   "inLanguage": "en", "mainEntity": {"@id": self.url("/#person")}}
        return self.document(page, body, {"@graph": [profile, self.person()]}, layout="home", interactive_figure=True)

    def card(self, title, body, url=None, *, period=None, action_label=None, ident=None):
        heading = f'<h3>{link(title, url, "card-link")}</h3>' if url else text(title, "h3")
        action = text(action_label or self.copy["read_note"], attrs=' class="note-action" aria-hidden="true"') if url else ""
        label = text(period, "p", ' class="case-period"') if period else ""
        target = f' id="{esc(ident)}"' if ident else ""
        return f'<article class="card"{target}>' + label + heading + text(body, "p") + action + "</article>"

    def engagements(self, *, compact=False):
        data = self.data["consult"]
        items = []
        for engagement in data["scoped_engagements"]:
            if compact:
                items.append("<li>" + esc(engagement["title"]) + "</li>")
            else:
                body = text(engagement["body"], "p")
                if engagement.get("url"):
                    body += link(engagement["link_label"], engagement["url"], "link")
                items.append("<li>" + text(engagement["title"], "h3") + body + "</li>")
        content = (
            text(data["engagement_intro"], "p")
            + '<ul class="engagement-list">' + "".join(items) + "</ul>"
            + link(self.copy["connect"], self.social["LinkedIn"], "btn btn-secondary")
        )
        if compact:
            return (
                '<div class="prose home-engagements">'
                + text(self.copy["scoped_engagements"], "h3") + content + "</div>"
            )
        return section("scoped-engagements", self.copy["scoped_engagements"], '<div class="prose">' + content + "</div>")

    def offer(self, tier):
        label = self.copy["pay"].format(price=tier["price"])
        price = self.copy["price"].format(price=tier["price"])
        return (
            f'<article class="card price-card" id="offer-{esc(tier["id"])}">' + text(tier["title"], "h3")
            + text(tier["duration"], "p", ' class="duration"')
            + text(price, "p", ' class="price"')
            + text(tier["scope"], "p") + text(tier["outcome"], "p", ' class="outcome"')
            + link(label, tier["url"], "btn btn-secondary", ' rel="noreferrer"') + "</article>"
        )

    def consult(self):
        data = self.data["consult"]
        item = self.pages["consult"]
        url = self.url(item["path"])
        steps = '<ol class="steps">' + "".join(
            '<li>' + text(step["title"], "h3") + text(step["body"], "p") + "</li>"
            for step in data["steps"]
        ) + "</ol>"
        faq = '<div class="faq">' + "".join(
            "<details>" + text(faq["question"], "summary") + text(faq["answer"], "p") + "</details>"
            for faq in data["faq"]
        ) + "</div>"
        body = page_header(data["title"], data["intro"])
        body += section("booking", self.copy["how_it_works"],
                        steps + '<div class="prose terms">' + paragraphs(data["terms"]) + "</div>")
        body += section("sessions", self.copy["sessions"],
                        '<div class="card-grid price-grid">' + "".join(self.offer(t) for t in data["tiers"]) + "</div>")
        body += self.engagements()
        body += section("faq", self.copy["faq"], faq)
        service = {
            "@type": "Service", "@id": url + "#service", "url": url,
            "name": data["document_title"], "serviceType": data["service_name"],
            "description": data["intro"],
            "provider": {"@type": "Person", "@id": self.url("/#person"), "name": self.name},
            "availableChannel": {"@type": "ServiceChannel", "availableLanguage": ["en"]},
            "offers": [{"@type": "Offer", "@id": self.offer_id(tier), "name": tier["title"],
                        "description": tier["outcome"],
                        "price": tier["price"], "priceCurrency": "USD", "url": tier["url"]}
                       for tier in data["tiers"]],
        }
        page = {"@type": "WebPage", "@id": url + "#page", "url": url, "inLanguage": "en",
                "mainEntity": {"@id": service["@id"]}}
        return self.document(item, body, {"@graph": [page, service]}, layout="consult")

    def case(self, item):
        url = self.url(item["path"])
        image = item.get("image")
        body = (
            '<article class="prose case-note">'
            + link(self.copy["work"] if item.get("featured") else self.copy["back_work"],
                   self.pages["home"]["path"] + ("#work" if item.get("featured") else "#public-work"), "back-link")
            + (text(item["period"], "p", ' class="case-period"') if item.get("period") else "")
            + page_header(item["title"], item["intro"])
            + text(self.copy["by"], "p", ' class="byline"')
        )
        if item.get("board"):
            body += self.board_figure()
        if image:
            alt = image["alt"]
            responsive = ""
            if image.get("small_path"):
                responsive = (
                    f' srcset="{esc(image["small_path"])} 480w, {esc(image["path"])} {image["width"]}w"'
                    ' sizes="(max-width: 640px) calc(100vw - 32px), 62ch"'
                )
            body += (
                f'<figure class="case-figure"><img src="{esc(image["path"])}" alt="{esc(alt)}"'
                + responsive
                + f' width="{image["width"]}" height="{image["height"]}" decoding="async" loading="lazy"'
                '>'
                + text(image["caption"], "figcaption") + "</figure>"
            )
        if item.get("specs"):
            body += self.spec_table(item["specs"])
        for block in item["blocks"]:
            body += text(block["heading"], "h2", ' class="section-head--trace"')
            body += "".join(case_prose(value) for value in block["paragraphs"])
            if block.get("figure"):
                body += self.gateway_figure(self.data["featured"])
            if block.get("security_controls"):
                body += self.spec_table(self.data["featured"]["controls"], self.copy["security_controls"])
        if item.get("sources"):
            body += text(self.copy["sources"], "h2") + "<ul>" + "".join(
                f'<li>{link(source["label"], source["url"])}</li>' for source in item["sources"]
            ) + "</ul>"
        body += link(self.copy["view_consult"], self.pages["consult"]["path"],
                     "btn btn-secondary") + "</article>"
        article = {
            "@type": "Article", "@id": url + "#article", "mainEntityOfPage": url,
            "headline": item["title"], "description": item["intro"], "inLanguage": "en",
            "datePublished": item["date_published"], "dateModified": self.data["last_updated"],
            "image": self.url(image["path"] if image else item.get("schema_image", SOCIAL_IMAGE)),
            "author": {"@type": "Person", "@id": self.url("/#person"), "name": self.name},
            **({"citation": [source["url"] for source in item["sources"]]} if item.get("sources") else {}),
        }
        return self.document(item, body, article, layout="case",
                             interactive_figure=bool(item.get("board") or item.get("featured")))

    def privacy(self):
        data = self.data["privacy"]
        body = '<div class="prose">' + page_header(data["title"], data["intro"])
        for block in data["blocks"]:
            body += text(block["heading"], "h2") + paragraphs(block["paragraphs"])
        body += link(self.copy["connect"], self.social["LinkedIn"], "btn btn-secondary") + "</div>"
        return self.document(self.pages["privacy"], body, layout="utility")

    def utility(self, key, route):
        data = self.data[key]
        action = link(self.copy["back_home"], self.pages["home"]["path"], "btn btn-secondary")
        if key == "success":
            action += link(self.copy["connect"], self.social["LinkedIn"], "btn btn-secondary")
        else:
            action += link(self.copy["view_consult"], self.pages["consult"]["path"], "btn btn-secondary")
        body = (
            '<div class="utility-content"><section class="prose utility-block" aria-labelledby="utility-heading">'
            + text(data["title"], "h1", ' id="utility-heading"') + paragraphs(data["paragraphs"])
            + f'<div class="actions">{action}</div></section></div>'
        )
        return self.document(self.pages[key], body, route=route, layout="utility")

    def redirect(self, destination):
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page moved</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{esc(self.url(destination))}">
<meta http-equiv="refresh" content="0; url={esc(destination)}">
</head>
<body><main>{link("Continue to the page", destination)}</main></body>
</html>
"""

    def sitemap(self):
        sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        updated = date.fromisoformat(self.data["last_updated"]).isoformat()
        for path in self.indexed:
            sitemap.extend(("  <url>", f"    <loc>{esc(self.url(path))}</loc>",
                            f"    <lastmod>{updated}</lastmod>", "  </url>"))
        return "\n".join(sitemap + ["</urlset>", ""])

    def render(self):
        for key, renderer in (("home", self.home), ("consult", self.consult), ("privacy", self.privacy)):
            self.files[filename(self.pages[key]["path"])] = renderer()
        for case in self.cases:
            self.files[filename(case["path"])] = self.case(case)
        for old, new in self.redirects.items():
            self.files[filename(old)] = self.redirect(new)
        self.files["consult-success.html"] = self.utility("success", "/consult-success.html")
        self.files["404.html"] = self.utility("missing", "/404.html")
        self.files["sitemap.xml"] = self.sitemap()
        self.files["robots.txt"] = self.data["crawler_policy"] + f'\nSitemap: {self.url("/sitemap.xml")}\n'
        self.machine_files()
        return self.files

    def portfolio_markdown(self):
        content = self.data["home"]
        feature = self.data["featured"]
        lines = [f"# {self.name}", f'{content["headline"]} {content["headline_end"]}',
                 content["intro"], content["proof_line"],
                 f'[{self.copy["view_consult"]}]({self.url(self.pages["consult"]["path"])})',
                 " · ".join(f'[{name}]({url})' for name, url in self.social.items()),
                 f'## {self.copy["whole_path"]}']
        lines.extend(f'- {stage["label"]} ({stage["tag"]}) — {stage["sentence"]}'
                     for stage in self.path_figure_data["stages"])
        lines.extend((f'## {feature["title"]}', *feature["paragraphs"],
                      f'[{self.copy["read_note"]}]({self.url(feature["path"])})',
                      f'## {self.copy["working_method"]}'))
        lines.extend(f'{i}. {step["title"]}. {step["body"]}' for i, step in enumerate(content["working_method"], 1))
        lines.append(f'## {self.copy["expertise"]}')
        lines.extend(f'- {item["title"]} — {item["body"]}' for item in content["capabilities"])
        lines.append(f'## {self.copy["selected_work"]}')
        for item in content["selected"]:
            title = f'[{item["title"]}]({self.url(item["url"])})' if item.get("url") else item["title"]
            lines.append(f'- {title} — {item["body"]}')
        lines.append(f'## {self.copy["public_work"]}')
        lines.extend(f'- [{case["title"]}]({self.url(case["path"])}) · {case["period"]} — {case["card_intro"]}'
                     for case in self.cases if not case.get("featured"))
        lines.extend((f'## {self.copy["about"]}', *content["about"],
                      f'## {self.copy["experience"]}'))
        lines.extend(f'- {item["dates"]} · {item["title"]} · {item["org"]} — {item["body"]}'
                     for item in content["experience"])
        lines.append(f'## {self.copy["open_source"]}')
        lines.extend(f'- [{item["title"]}]({item["url"]}) — {item["body"]}' for item in content["projects"])
        return "\n\n".join(lines) + "\n"

    def consult_markdown(self):
        data = self.data["consult"]
        lines = [f'# {data["document_title"]}', data["intro"],
                 f'[{self.copy["consult"]}]({self.url(self.pages["consult"]["path"])})',
                 f'## {self.copy["how_it_works"]}']
        lines.extend(f'{i}. {step["title"]}. {step["body"]}' for i, step in enumerate(data["steps"], 1))
        lines.extend(data["terms"])
        lines.append(f'## {self.copy["sessions"]}')
        for tier in data["tiers"]:
            price = self.copy["price"].format(price=tier["price"])
            lines.extend((f'### {tier["title"]} · {tier["duration"]} · {price}', tier["scope"], tier["outcome"],
                          f'[{self.copy["pay"].format(price=tier["price"])}]({tier["url"]})'))
        lines.extend((f'## {self.copy["scoped_engagements"]}', data["engagement_intro"]))
        for item in data["scoped_engagements"]:
            lines.append(f'- {item["title"]} — {item["body"]}')
            if item.get("url"):
                lines.append(f'[{item["link_label"]}]({self.url(item["url"])})')
        lines.append(f'[LinkedIn]({self.social["LinkedIn"]})')
        lines.append(f'## {self.copy["faq"]}')
        for item in data["faq"]:
            lines.extend((f'### {item["question"]}', item["answer"]))
        return "\n\n".join(lines) + "\n"

    def case_markdown(self, item):
        lines = [f'# {item["title"]}', item["intro"], f'<{self.url(item["path"])}>']
        if item.get("period"):
            lines.append(item["period"])
        specs = self.board_specs() if item.get("board") else item.get("specs")
        if specs:
            lines.append(f'## {self.copy["specifications"]}')
            lines.extend(f'- {row["label"]} — {row["value"]}' for row in specs)
        for block in item["blocks"]:
            lines.extend((f'## {block["heading"]}', *block["paragraphs"]))
            if block.get("figure"):
                lines.append(self.data["featured"]["figure_caption"])
            if block.get("security_controls"):
                lines.append(f'### {self.copy["security_controls"]}')
                lines.extend(f'- {row["label"]} — {row["value"]}' for row in self.data["featured"]["controls"])
        if item.get("sources"):
            lines.append(f'## {self.copy["sources"]}')
            lines.extend(f'- [{source["label"]}]({source["url"]})' for source in item["sources"])
        return "\n\n".join(lines) + "\n"

    def machine_files(self):
        content = self.data["home"]
        self.files["index.md"] = self.portfolio_markdown()
        self.files["consult.md"] = self.consult_markdown()
        self.files["llms-full.txt"] = "\n---\n\n".join((
            self.files["index.md"], self.files["consult.md"],
            *[self.case_markdown(case) for case in self.cases],
        ))
        llms = [f"# {self.name}", f'> {content["intro"]}', "", "## Profile and consulting"]
        for key in ("home", "consult"):
            page = self.pages[key]
            llms.append(f'- [{page["meta"]["title"]}]({self.url(page["path"])})')
        llms.extend(f'- [{case["title"]}]({self.url(case["path"])})' for case in self.cases)
        llms += ["", "## Other public formats",
                 f'- [Portfolio Markdown]({self.url("/index.md")})',
                 f'- [Consulting Markdown]({self.url("/consult.md")})',
                 f'- [API catalog]({self.url("/.well-known/api-catalog")})',
                 f'- [OpenAPI description]({self.url("/api/openapi.json")})',
                 f'- [Full profile, offers and case notes]({self.url("/llms-full.txt")})',
                 f'- [Resume JSON]({self.url("/api/resume.json")})',
                 f'- [Consulting JSON]({self.url("/api/consulting.json")})']
        self.files["llms.txt"] = "\n".join(llms) + "\n"

        resume = {
            "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
            "basics": {"name": self.name, "label": self.data["person"]["positioning"],
                       "url": self.url("/"), "summary": content["intro"], "location": self.data["person"]["location"],
                       "profiles": [{"network": network, "url": url} for network, url in self.social.items()]},
            "work": [{"name": item["org"], "position": item["title"], "startDate": item["start"],
                      **({"endDate": item["end"]} if item.get("end") else {}), "highlights": [item["body"]]}
                     for item in content["experience"]],
            "projects": [{"name": item["title"], "description": item["body"],
                          **({"url": self.url(item["url"])} if item.get("url") else {})}
                         for item in content["selected"]]
                        + [{"name": case["title"], "description": case["intro"], "url": self.url(case["path"])}
                           for case in self.cases if not case.get("featured")]
                        + [{"name": item["title"], "description": item["body"], "url": item["url"]}
                           for item in content["projects"]],
            "skills": [{"name": item["title"], "keywords": item["keywords"]} for item in content["expertise"]],
            "languages": [{"language": "English", "fluency": "C1+"}],
            "awards": self.data["person"]["awards"],
            "education": self.data["person"]["education"],
        }
        consult = self.data["consult"]
        consulting = {
            "provider": self.name, "page": self.url(self.pages["consult"]["path"]),
            "currency": "USD", "format": "1:1 Google Meet session",
            "flow": [step["body"] for step in consult["steps"]],
            "terms": consult["terms"], "scheduling": "manual",
            "sessions": [{"id": tier["id"], "name": tier["title"], "minutes": tier["minutes"],
                          "price": tier["price"], "covers": tier["scope"], "booking_url": tier["url"],
                          "scope": tier["scope"], "outcome": tier["outcome"]}
                         for tier in consult["tiers"]],
            "engagement_intro": consult["engagement_intro"],
            "engagement_contact": self.social["LinkedIn"],
            "scoped_engagements": [
                {"title": item["title"], "description": item["body"],
                 **({"url": self.url(item["url"])} if item.get("url") else {})}
                for item in consult["scoped_engagements"]
            ],
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
             ["/", "/index.md", "/api/resume.json", *[case["path"] for case in self.cases]]),
            ("book-consulting", "Compare and cite consulting sessions and scheduling terms.",
             ["/consult.html", "/consult.md", "/api/consulting.json"]),
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
        self.localized = False
        self.refresh = []
        self.anchors = []
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
        if "hreflang" in attrs or {"data-en", "data-es", "data-lang-block"} & attrs.keys():
            self.localized = True
        if tag == "meta" and attrs.get("http-equiv") == "refresh":
            self.refresh.append(attrs["content"])
        if tag == "a" and "href" in attrs:
            self.anchors.append(attrs["href"])
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
    for name, page in pages.items():
        if page.language != "en" or page.localized:
            problems.append(f"{name}: expected English-only markup")
    for path in site.indexed:
        page = pages[filename(path)]
        if page.canonicals != [site.url(path)] or "noindex" in page.robots or page.refresh:
            problems.append(f"{path}: canonical page is not indexable")
    for old, new in site.redirects.items():
        page = pages[filename(old)]
        if (new not in site.indexed or page.canonicals != [site.url(new)] or "noindex" not in page.robots
                or page.refresh != [f"0; url={new}"] or page.anchors != [new]):
            problems.append(f"{old}: invalid redirect stub")
    obsolete = {str(path.relative_to(ROOT)) for path in (ROOT / "es").rglob("*") if path.is_file()}
    for name in sorted(obsolete - {filename(path) for path in site.redirects}):
        problems.append(f"{name}: obsolete localized output")
    for name in ("consult-success.html", "404.html"):
        if "noindex" not in pages[name].robots:
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
    expected = {site.url(path) for path in site.indexed}
    if set(sitemap_entries) != expected or len(index) != len(expected):
        problems.append("sitemap.xml: indexed URLs do not match canonical pages")
    for url, entry in sitemap_entries.items():
        if len(entry) != 2 or entry.findtext("{*}lastmod") != site.data["last_updated"]:
            problems.append(f"sitemap.xml: unexpected metadata for {url}")
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
