# Font licences

Every font file in this directory is listed here. All three families are licensed under the SIL Open Font License 1.1; the full text sits next to each family as `OFL.txt`. Any font not listed here must not be committed (never Apple Garamond, ITC Garamond, or any file without a licence that allows self-hosting).

| Family | Role | Licence | Reserved Font Name | Source | Files | State |
|---|---|---|---|---|---|---|
| Instrument Serif | Display (roman + italic) | OFL 1.1 | none | github.com/Instrument/instrument-serif, commit `65c0ef2`, `fonts/webfonts/` | `instrument-serif/InstrumentSerif-Regular.woff2`, `InstrumentSerif-Italic.woff2` | Upstream, unmodified |
| Inter | Text and UI | OFL 1.1 | none | github.com/rsms/inter, release v4.1, `web/` | `inter/inter-{regular,italic,medium,semibold}-latin.woff2` | Subset from `Inter-{Regular,Italic,Medium,SemiBold}.woff2` to Latin, Latin-1, Latin Extended-A, general punctuation, € ™ arrows and math signs; layout features: defaults plus `tnum`, `case`, `zero`, `ss01`. Allowed because Inter declares no Reserved Font Name. |
| IBM Plex Mono | Data and code | OFL 1.1 | **"Plex"** | github.com/IBM/plex, release `@ibm/plex-mono@2.5.0`, `fonts/split/woff2/` | `ibm-plex-mono/IBMPlexMono-{Regular,Medium}-{Latin1,Latin2}.woff2` | Upstream, unmodified (IBM's own split files) |

## Rules

- **Reserved Font Names.** OFL section 3 forbids a Modified Version from using a Reserved Font Name. IBM Plex reserves "Plex", so any subset, instance or conversion we make of it counts as a Modified Version and would have to be renamed. Keep using IBM's own files unchanged. To change coverage, take a different upstream split; never run a subsetter on Plex. The same applies to Source Sans/Code ("Source") if they are ever added.
- **Subsetting** is allowed only for families with no Reserved Font Name (here: Inter, Instrument Serif). Record the exact range and features in the table above.
- **Coverage.** All files cover Spanish and English: á é í ó ú ü ñ Á É Í Ó Ú Ü Ñ ¿ ¡ « » € — – “ ” ‘ ’ … ·. Checked against each font's character map.
- **The logo** is outlined artwork drawn from Junicode 2 (OFL 1.1, no Reserved Font Name) letterforms. It ships as SVG paths, not as a font, so Junicode is not a font dependency of the system. See `logo/README.md`.
- **Paid upgrade path.** If a licensed ITC Garamond (Light Condensed) web licence is ever bought, its files stay out of this repository unless the licence allows storage in a private repo. Swap only `--font-display` in `tokens.css`, record the licence here, and remeasure the display sizes.

## SHA-256

```
ca21b99b0d6b88a0dc34cebfe48104611e5c7f8f92746bed26c37aa470174322  instrument-serif/InstrumentSerif-Regular.woff2
4f7aacc18d491dea8778bbc591db87b9455625899ed5f913957e7fd82604c294  instrument-serif/InstrumentSerif-Italic.woff2
7039280ab493298966c944868f96b9822809d74ea00b458317f4568e2b52b873  inter/inter-regular-latin.woff2
8ea2ac30a2b7ac5ec3eb7a5218fcc50d3d2e855d072fdfe21c0f02b735c8b992  inter/inter-italic-latin.woff2
a3ddf024f0f7a4ad980db04d58f785dcf9d09d1acdc2a443d25760d3ff3b9cbb  inter/inter-medium-latin.woff2
1f5cc5631b419c23a7125e1f0525064ccb6edbadb94e3fd53f20339d12262553  inter/inter-semibold-latin.woff2
e8993d946649b9d01abb1ed06d574b19d8ea3e66b5c3948602db335c44c18e56  ibm-plex-mono/IBMPlexMono-Regular-Latin1.woff2
8c5e48e4c6ee60346744db62fd8bbf530c21e531e1a1498c3a410ed8f7d3986e  ibm-plex-mono/IBMPlexMono-Regular-Latin2.woff2
41201b658a328b9d00368215c2f1102770f80b15952ab82631e4006255e6365d  ibm-plex-mono/IBMPlexMono-Medium-Latin1.woff2
86208dbe8e00256a77bc3edd09aa6a584b0da393caa1fb200d44eac1d578512c  ibm-plex-mono/IBMPlexMono-Medium-Latin2.woff2
```
