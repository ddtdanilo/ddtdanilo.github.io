# AGENTS.md

This repository is the public personal portfolio of Danilo Díaz Tarascó. GitHub Pages serves the repository root on master at https://ddtdanilo.github.io/.

## Content and privacy

- Keep facts grounded in the owner's approved career record or verifiable public work. Never publish private contact information, addresses, residency or nationality details, client identities, employer financials or proprietary implementation details. Public contact goes through LinkedIn.
- Keep the three Stripe links and the manual scheduling steps in sync. Confirm any proposed scheduling policy with the owner. The return page should explain next steps without asserting payment.
- Keep the Search Console verification file google8be6858017c655ce.html.
- Keep the IndexNow key file `db0b4ec5da19c502be5ee006c7e2dbd7.txt`. After publishing new or changed pages, submit their URLs to `https://api.indexnow.org/indexnow` with that key (host, key, keyLocation, urlList).

## Structure and checks

- Edit data/site.json for English copy, routes, public facts and offer details. The home illustration uses data/path.json for its seven stage descriptions. tools/build_site.py uses the Python standard library to write HTML, the sitemap and public machine-readable copies. Commit its outputs. No deploy-time build.
- Publish English-only pages and machine-readable records. Keep the five legacy language URLs as noindex redirects to their canonical counterparts.
- Use vanilla CSS and JavaScript with local fonts and assets. Light is the default theme. Dark requires an explicit, locally stored visitor choice. All page content and conversion links must work when JavaScript is blocked.
- Copy public-safe tokens, fonts with licences and marks from the design system. Record licence provenance and preserve the SVG board notice. Strip metadata from published raster images.
- Run python3 tools/build_site.py, python3 tools/build_site.py --check and git diff --check before committing. Test 320 px, 390 px and desktop, both themes, keyboard, reduced motion and JavaScript blocked.
- Use concise English Conventional Commits and the owner's GitHub noreply identity. Keep files, comments and commits free of automated authorship attribution.
- The generator hashes linked stylesheets and the favicon in HTML. Regenerate after changing those assets. Use new filenames for changed font or image binaries when their containing source does not change.
