# Danilo Díaz Tarascó

English-language engineering portfolio and consulting site served as static files from GitHub Pages. Light is the default theme. The theme button saves the visitor’s choice in local storage.

## Edit the site

Update public facts and copy in [data/site.json](data/site.json). The home and consulting pages, case notes, sitemap, Markdown copies and JSON are generated together.

Run python3 tools/build_site.py to regenerate the committed output. Run python3 tools/build_site.py --check to check freshness, privacy patterns, local links and the five legacy redirects. Preview all pages using a static HTTP server from the repository root. Pages serves the committed output without running the generator.

The site assets under assets/css, assets/fonts and assets/img carry the appearance. The generated HTML includes content hashes in linked stylesheet and favicon URLs. The theme and figure scripts and SVG artwork are embedded during generation. Font binaries and licences are recorded in [assets/fonts/LICENSES.md](assets/fonts/LICENSES.md). Swap the logo and favicon with their matching versions. The [home figure](assets/img/path.svg) is a vector illustration of the connected-system stages in [data/path.json](data/path.json). The [plant gateway figure](assets/img/gateway.svg) illustrates the generalized architecture described in the case note. The historical board in the X-Sub note is generated from the [public X-Sub layout](data/xsub/README.md) and includes its licence in the SVG.

Consulting uses the three existing Stripe Payment Links. The return page gives scheduling instructions for buyers. It does not verify a payment. The [privacy page](https://ddtdanilo.github.io/privacy.html) describes site storage and checkout handling. Professional contact is on [LinkedIn](https://www.linkedin.com/in/ddtdanilo/).

The optional Worker under worker/ is separate from the Pages deployment.
