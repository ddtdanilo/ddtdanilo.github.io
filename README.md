# Danilo Díaz Tarascó

Bilingual portfolio and consulting site, served as static files from GitHub Pages. The English and Spanish routes work independently and share a design system.

## Edit the site

Update the public facts and bilingual copy in [data/site.json](data/site.json). The English keys and Spanish keys travel together. The home and consulting pages, case notes, sitemap, Markdown copies and JSON are generated together.

Run python3 tools/build_site.py to regenerate the committed output. Run python3 tools/build_site.py --check to check freshness, privacy patterns, local links and locale pairs. Preview all pages using a static HTTP server from the repository root. Pages serves the committed output without running the generator.

The site assets under assets/css, assets/fonts and assets/img carry the appearance. The generated HTML includes content hashes in linked stylesheet and favicon URLs. The theme and board scripts and SVG artwork are embedded during generation. Font binaries and licences are recorded in [assets/fonts/LICENSES.md](assets/fonts/LICENSES.md). Swap the logo and favicon with their matching versions. The hero board is generated from the [public X-Sub layout](data/xsub/README.md) and includes its licence in the SVG.

Consulting uses the three existing Stripe Payment Links. The return page gives scheduling instructions for buyers. It does not verify a payment. The bilingual [privacy page](https://ddtdanilo.github.io/privacy.html) describes site storage and checkout handling. Professional contact is on [LinkedIn](https://www.linkedin.com/in/ddtdanilo/).

The optional Worker under worker/ is separate from the Pages deployment.
