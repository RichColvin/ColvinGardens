# Colvin Gardens

The website at https://colvingardens.info, as plain HTML pages. It was a
PmWiki site until 23 November 2026, when it was converted once to these
files (`tools/convert_pmwiki.py`, kept as a record). Edit the HTML files
here from now on; PmWiki is no longer the source. Made the same way as
the BKBoK site (RichColvin/BKBoK).

## What's where

- `index.html` - the Index (the old wiki's HomePage), which is also the
  order of the Previous / Next links.
- One `.html` file per page, named as on the old wiki
  (`index.php?n=Main.Achillea` is `Achillea.html`).
- `Images/` - pictures, the same folder name as before so old links to
  them still work. `Images/CG_Banner.png` is the header banner,
  recoloured dark green from `CGLogo.png`.
- `cg-docs.css` / `cg-docs.js` - the look, the search box and
  click-to-enlarge pictures (made from BKBoK's files).
- `search-index.js` - made by the builder; don't edit it.
- `apple-touch-icon.png` / `favicon.png` - the icon an iPhone uses when
  the site is added to its Home Screen, and the browser tab's icon.
- `tools/` - the builder, the one-time converter and
  `ColvinGardens_htaccess_redirects.txt` (the lines for the site's
  `.htaccess`). Not published.

The beekeeping pages the wiki also held (older copies of BKBoK's) were
left out; old links to them go to bkbok.info.

## After editing, adding or renaming a page

    python3 tools/build_site.py

It rebuilds the search index and each page's Previous / Next links (in
the order the Index links the pages). A second run changes nothing.

## Page rules

- Every page carries its own header and footer (copy an existing page).
- Links between pages and to pictures are relative (`Hosta.html`,
  `Images/Herbs-1.png`).
- Links to other web sites get `class="online" target="_blank"
  rel="noopener"`; the stylesheet adds the arrow.
- A Cultivars table is `<table class="cultivars">`: a `<thead>` row of
  `<th>` headings (dark green), then one `<tr>` per cultivar whose cells
  each carry `data-label="<its heading>"` - on a phone each cultivar is
  shown as a card, labelled from those. No pictures in the Cultivars
  section (Rich, 23 November 2026).
- Other tables with lines are `class="lined"` (all the same thin lines);
  tables without are `class="layout"`, plus `stack` if their columns
  should go one under the other on a phone.
- No tab characters; dates as "dd Month yyyy".

## Colours (option A, chosen 23 November 2026)

Light sage header `#dcebd0` with the banner lettering in dark green
`#1f4d1f` (7.9:1), near-white page `#fbfdf7`, headings `#2e6b1f`
(6.3:1), links `#1f5fa8` (6.3:1), cultivar table headings white on
`#008000` (5.1:1, the old site's green).
