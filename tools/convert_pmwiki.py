#!/usr/bin/env python3
#######################################################################
#                                                                     #
#                 Colvin Gardens - colvingardens.info                 #
#                                                                     #
#######################################################################
#
# File:
#   tools/convert_pmwiki.py (ColvinGardens repo)
#
# Purpose:
#   One-time conversion of the PmWiki site at https://colvingardens.info
#   into plain HTML pages at the top of this repo. Kept as a record of
#   how the pages were made; from now on the HTML files are edited
#   directly and this is not run again (it would overwrite those edits).
#   Made from the BKBoK repo's tools/convert_pmwiki.py.
#
#   Input is a folder made by fetching the live site:
#       html/Main.<Page>.html   each page as PmWiki showed it
#       src/Main.<Page>.txt     each page's ?action=source
#       files/<name>            the site's own pictures (Images/)
#
#       python3 tools/convert_pmwiki.py <that folder>
#       python3 tools/build_site.py
#
#   For each page it takes PmWiki's <div id='wikitext'>, drops the
#   hidden ">>comment<<" blocks and the standard footer table, turns
#   wiki links into relative X.html links (beekeeping pages into links
#   to bkbok.info), marks links to other sites class="online", points
#   the site's own pictures at the local Images/ folder and wraps it
#   all in the site's header and footer.
#
#   Tables (Rich, 23 November 2026): every table with lines gets the
#   same thin lines (class "lined"); fixed pixel widths go, so they fit
#   a phone. The Cultivars section's tables get a dark green heading
#   row (class "cultivars", the first row as <th>) and every cell a
#   data-label, so on a phone each cultivar shows as a card; the
#   pictures in that section are left out.
#   Needs BeautifulSoup (beautifulsoup4).
#
# Version
#   1.0 - 23 November 2026
#
#######################################################################

import html
import os
import re
import shutil
import sys
import unicodedata
from urllib.parse import unquote

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = REPO                           # the site is the repo's top level
SITE = r"https?://(?:www\.)?colvingardens\.info"
BKBOK = "https://bkbok.info/"

# Pages not carried over: PmWiki's own and the page templates.
SKIP = {"Template", "Template1", "Template2", "WikiSandbox", "RecentChanges"}
# Beekeeping pages - older copies of BKBoK's (Rich, 23 November 2026:
# left out, old links go to bkbok.info).
BEE = set("""
AngryOrAggressive ApiaryLocation BeeEscapeBoard BeekeepingOperationSizes
BeingAGoodMentor BeingAGoodProtégé BottomBoard BroodBoxes Checkerboarding
ColonyOrHive ContestsAmpHoney EntranceReducer Feeders Foundation Frames
GettingAMentor Guidelines HardwareCloth HiveEquipment HivePlacement
HiveStands HivesAndSpring HivesAndSummer HivesAndWinter HoneyBeeSubspecies
HoneyHarvesting HoneyLabelling HoneySupers HorizontalHive InnerCover
InspectingColonies InspectionAndActionRecord
InspectionInspectionAndActionRecord IntegratedPestManagement
LangstrothBoxSizes LangstrothHive LangstrothHives LayingWorker
ManagementCalendar MergingColonies MigratoryCover ObservationHives Painting
Queen QueenExcluder QueenMarkingColors QuiltBox RecordKeeping
RegisteringYourBees ReplacingTheQueen Shim SlattedRack SmallHiveBeetle
SpanningCover SplittingColonies SplittingHives SwarmsAndSwarming
TelescopingCover TransportingBeesInsideACar Tropilaelaps Varroa
VarroaSensitiveHygiene VarroaSensitiveQueen
""".split())
# Page -> the page it now is (old copies under a common name).
SAME_AS = {"HomePage": "index", "About": "AboutThisSite",
           "AniseHyssop": "Agastache", "ButterflyBush": "Buddleja",
           "Coneflowers": "Echinacea", "RussianSage": "Perovskia",
           "Yarrow": "Achillea", "Blueberries": "Vaccinium",
           "JoePyeWeedHollow-stemmed": "Eutrochium",
           "EupatoriadelphusFistulous": "Eutrochium"}

THIN = ("border", "cellpadding", "cellspacing", "width", "height", "style")


def file_name(page):
    '''PmWiki page name (after "Main.") -> HTML file name without .html.'''
    page = SAME_AS.get(page, page)
    return unicodedata.normalize("NFKD", page).encode("ascii", "ignore").decode()


def page_link(n):
    '''"Main.X#frag" from an index.php?n= link -> href or None.'''
    n = unquote(n)
    target, _, frag = n.partition("#")
    target = target.split("?")[0].split("&")[0]
    group, _, page = target.partition(".")
    frag = "#" + frag if frag else ""
    if group == "Main" and page in BEE:
        return BKBOK + "index.php?n=Main." + page    # bkbok.info sends it to the right page
    if group == "Main" and page and page not in SKIP:
        return file_name(page) + ".html" + frag
    if group == "PmWiki":
        return "https://www.pmwiki.org/wiki/PmWiki/" + page
    return None


def slug(text, used):
    s = re.sub(r"[^A-Za-z0-9]+", "-", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()).strip("-")
    s = s or "section"
    base, n = s, 2
    while s in used:
        s = "%s-%d" % (base, n)
        n += 1
    used.add(s)
    return s


def local_image(url):
    m = re.match(r"https?://(?:www\.)?(?:colvingardens\.info|colvintools\.com/gardening|gardening\.colvintools\.com)/images/(.+)$",
                 url, re.I)
    return "Images/" + unquote(m.group(1)) if m else None


def cultivar_sections(soup):
    '''Each Cultivars heading's section: the elements after it up to the
    next heading of the same level or higher.'''
    out = []
    for h in soup.find_all(["h1", "h2"]):
        if h.get_text(" ", strip=True).lower().startswith("cultivar"):
            level, items = int(h.name[1]), []
            for el in h.next_siblings:
                if isinstance(el, Tag) and re.fullmatch(r"h[1-%d]" % level, el.name):
                    break
                if isinstance(el, Tag) and el.name == "hr":
                    break
                items.append(el)
            out.append(items)
    return out


def drop_pictures(el):
    '''Remove every picture in el, with a link around it if the link
    held nothing else, and the line break left after it.'''
    for img in el.find_all("img") if isinstance(el, Tag) else []:
        target = img
        a = img.find_parent("a")
        if a is not None and not a.get_text(strip=True) and len(a.find_all("img")) == 1:
            target = a
        prev = target.previous_sibling
        # skip spaces and the empty %height% / %width% spans before it
        while (isinstance(prev, NavigableString) and not prev.strip()) or \
                (isinstance(prev, Tag) and prev.name == "span" and not prev.get_text(strip=True)):
            gone, prev = prev, prev.previous_sibling
            gone.extract()
        target.decompose()
        if isinstance(prev, Tag) and prev.name == "br":
            nxt = prev.next_sibling
            while isinstance(nxt, NavigableString) and not nxt.strip():
                nxt = nxt.next_sibling
            if nxt is None or (isinstance(nxt, Tag) and nxt.name == "br"):
                prev.decompose()
    if isinstance(el, Tag):
        # a paragraph or div left empty
        for p in el.find_all(["p", "div", "span"]):
            if not p.get_text(strip=True) and not p.find(["img", "br", "table", "hr"]) and "vspace" not in p.get("class", []):
                p.decompose()


def make_cultivar_table(soup, t):
    '''The first row becomes the heading row; every cell gets the
    heading's name as data-label (shown on a phone).'''
    rows = t.find_all("tr", recursive=False) or t.find_all("tr")
    if len(rows) < 2:
        return False
    names = [c.get_text(" ", strip=True) for c in rows[0].find_all(["td", "th"], recursive=False)]
    if not names or not any(n.lower().startswith("cultivar") or n.lower() in ("height", "spread", "sun") for n in names):
        return False
    thead = soup.new_tag("thead")
    tr = soup.new_tag("tr")
    for n in names:
        th = soup.new_tag("th", scope="col")
        th.string = n
        tr.append(th)
    thead.append(tr)
    rows[0].decompose()
    # Cells spanning several rows (Strawberries): the later rows' cells
    # are put into the first row's cells for their column, one paragraph
    # each, so every cultivar is one row (and one card on a phone).
    body_rows, spans = [], {}
    for r in rows[1:]:
        cells = r.find_all(["td", "th"], recursive=False)
        if spans and len(cells) < len(names):
            free = [i for i in range(len(names)) if spans.get(i, 0) <= 0]
            for i, c in zip(free, cells):
                target = body_rows[-1].find_all(["td", "th"], recursive=False)[i]
                p = soup.new_tag("p")
                for x in list(c.contents):
                    p.append(x.extract())
                target.append(p)
            spans = {i: n - 1 for i, n in spans.items()}
            r.decompose()
            continue
        spans = {}
        for i, c in enumerate(cells):
            n = int(c.get("rowspan", "1") or 1)
            if n > 1:
                spans[i] = n - 1
            c.attrs.pop("rowspan", None)
        body_rows.append(r)
    tbody = soup.new_tag("tbody")
    for r in body_rows:
        for i, c in enumerate(r.find_all(["td", "th"], recursive=False)):
            c.name = "td"
            if i < len(names) and names[i]:
                c["data-label"] = names[i]
            for k in ("bgcolor", "valign", "width", "height", "style", "nowrap"):
                c.attrs.pop(k, None)
            if c.get("align") == "center" or "center" in c.get("class", []):
                c["class"] = ["center"]
            else:
                c.attrs.pop("class", None)
            c.attrs.pop("align", None)
        tbody.append(r.extract())
    t.clear()
    t.append(thead)
    t.append(tbody)
    t.attrs = {"class": ["cultivars"]}
    return True


def tidy_tables(soup):
    for t in soup.find_all("table"):
        if "cultivars" in t.get("class", []):
            continue
        lined = (t.get("border") or "0").strip("'\"") not in ("0", "")
        width = t.get("width", "")
        style = t.get("style", "")
        for k in THIN:
            t.attrs.pop(k, None)
        cls = [c for c in t.get("class", []) if c]
        cls.append("lined" if lined else "layout")
        # a layout table holding columns of lists, tables or headings
        # (the Index's two columns) stacks on a phone; a small one
        # (Plant Type / Hardiness Zone, the Index's two icons) doesn't
        if not lined and any(len(r.find_all(["td", "th"], recursive=False)) > 1 for r in t.find_all("tr")) \
                and t.find(["ul", "ol", "table", "h1", "h2", "h3", "h4"]):
            cls.append("stack")
        if width.endswith("%") and width != "100%" and not lined:
            t["style"] = "width:%s" % width
        elif width == "100%":
            cls.append("full")
        if t.get("align") in ("right", "left"):
            cls.append("float-" + t["align"])
            t.attrs.pop("align")
            if width.endswith("px"):
                t["style"] = "width:%s" % width        # the side boxes keep their width (not on a phone)
        if "float:" in style.replace(" ", ""):
            cls.append("float-right" if "right" in style else "float-left")
        t["class"] = cls
        for c in t.find_all(["td", "th"]):
            w = c.get("width", "")
            c.attrs.pop("height", None)
            if w.endswith("px") or w == "100%":
                c.attrs.pop("width", None)


def clean(soup, this_file):
    '''Tidy PmWiki's wikitext in place.'''
    # hidden ">>comment<<" blocks
    for d in soup.find_all(style=re.compile(r"display:\s*none")):
        d.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    # the standard footer (About this Site / eMail) - the page footer has it now
    for t in soup.find_all("table"):
        txt = t.get_text()
        if "About this Site" in txt and "GardeningBoK" in txt:
            t.decompose()
    # the "----" every page starts with, under the title
    for el in list(soup.children):
        if isinstance(el, NavigableString) and not el.strip():
            continue
        if el.name == "div" and "vspace" in el.get("class", []) and not el.contents:
            el.decompose()
            continue
        if el.name == "hr":
            el.decompose()
        break

    # the Cultivars sections: no pictures, dark green heading row
    for items in cultivar_sections(soup):
        for el in items:
            drop_pictures(el)
            if isinstance(el, Tag):
                for t in ([el] if el.name == "table" else []) + el.find_all("table"):
                    if t.parent is not None:
                        make_cultivar_table(soup, t)

    # wiki links
    for a in soup.find_all("a"):
        if a.parent is None:
            continue
        cls = a.get("class", [])
        if isinstance(cls, str):
            cls = cls.split()
        href = a.get("href", "")
        if "createlink" in cls:            # the "?" after a link to a page that doesn't exist
            a.decompose()
            continue
        if "createlinktext" in cls:        # ... and its text
            a.unwrap()
            continue
        m = re.match(SITE + r"/(?:index\.php|pmwiki\.php)?\?n=([^'\"]+)$", href, re.I)
        if m or re.match(SITE + r"/?(index\.php)?$", href, re.I):
            new = page_link(m.group(1)) if m else "index.html"
            if new is None:                # e.g. Profiles.RichColvin
                a.unwrap()
                continue
            a.attrs = {"href": new}
            if new.startswith("https://"):
                a.attrs.update({"class": "online", "target": "_blank", "rel": "noopener"})
            continue
        img = local_image(href)
        if img:
            a.attrs = {"href": img}
            if not img.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                a["download"] = img.split("/")[-1]
            continue
        if href.startswith(("http://", "https://")):
            a.attrs = {"class": "online", "href": href, "target": "_blank", "rel": "noopener"}
            nxt = a.next_sibling
            if isinstance(nxt, NavigableString) and re.match(r"\s*[↗]", str(nxt)):
                nxt.replace_with(re.sub(r"^(\s*)↗", r"\1", str(nxt), count=1))
            continue
        if href.startswith(("mailto:", "#")):
            a.attrs = {"href": href}
            continue

    for img in soup.find_all("img"):
        src = img.get("src", "")
        img["src"] = local_image(src) or src
        img.attrs.pop("title", None)
        img["alt"] = img.get("alt", "")
        for k in ("width", "height"):
            if img.get(k, "").endswith("px"):
                img[k] = img[k][:-2]
        if src.startswith("http") and not local_image(src):
            img["loading"] = "lazy"

    # %new% / %newwin% wrappers, and the old green colour on headings
    for s in soup.find_all("span", class_="new"):
        s.unwrap()
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        for s in h.find_all("span", style=re.compile(r"color:\s*(green|navy)")):
            s.unwrap()
    used = {a["id"] for a in soup.find_all(id=True)}
    for h in soup.find_all(["h1", "h2", "h3"]):
        if not h.get("id"):
            text = h.get_text(" ", strip=True)
            if text:
                h["id"] = slug(text, used)
        if h.contents and isinstance(h.contents[0], NavigableString):
            h.contents[0].replace_with(h.contents[0].lstrip())
    # links to PmWiki's numbered contents (#toc-3.1): to the heading
    # whose text starts with the link's text
    for a in soup.find_all("a", href=re.compile(r"^#toc-")):
        word = a.get_text(" ", strip=True).lower()
        for h in soup.find_all(["h1", "h2", "h3"]):
            if h.get_text(" ", strip=True).lower().startswith(word):
                a["href"] = "#" + h["id"]
                break
    tidy_tables(soup)
    for el in soup.find_all(class_=True):
        cls = el["class"].split() if isinstance(el["class"], str) else el["class"]
        el["class"] = [c for c in cls if c not in ("wikilink", "urllink", "selflink")]
        if not el["class"]:
            del el["class"]
    for el in soup.find_all(rel="nofollow"):
        del el["rel"]


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_text}</title>
<link rel="stylesheet" href="cg-docs.css">
<script src="search-index.js" defer></script>
<script src="cg-docs.js" defer></script>
<link rel="icon" href="favicon.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-title" content="Colvin Gardens">
<meta name="theme-color" content="#dcebd0">
</head>
<body>
<header class="site-header">
  <a class="brand" href="index.html" title="Index">
    <img src="Images/CG_Banner.png" alt="Colvin Gardens" width="466" height="69">
  </a>
  <nav class="site-nav" aria-label="Site">
    <a href="index.html">Index</a>
    <a href="AboutThisSite.html">About This Site</a>
  </nav>
</header>
<main class="page">
  <p class="crumbs">{crumbs}</p>
  <h1>{title}</h1>

  <div class="content">
{content}
  </div>
<!--pager--><!--/pager-->
</main>
<footer class="site-footer">
  <div class="footer-links">
    <div><a href="AboutThisSite.html">About this Site</a></div>
    <div class="footer-contact">Questions or comments?<br>
      <a href="mailto:GardeningBoK@gmail.com">GardeningBoK@gmail.com</a></div>
  </div>
</footer>
</body>
</html>
"""


def title_of(raw_html, src):
    m = re.search(r"\(:title\s+(.*?)\s*:\)", src)
    if m:
        return html.unescape(m.group(1)).replace("&amp", "&")
    m = re.search(r"class='pagetitle'[^>]*>(.*?)<", raw_html, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def main():
    raw = sys.argv[1]
    os.makedirs(os.path.join(OUT, "Images"), exist_ok=True)
    pages = {}
    for f in sorted(os.listdir(os.path.join(raw, "html"))):
        page = f[len("Main."):-len(".html")]
        if page in SKIP or page in BEE or page in SAME_AS and SAME_AS[page] != "index":
            continue
        pages[page] = f

    for page, f in pages.items():
        raw_html = open(os.path.join(raw, "html", f), encoding="utf-8").read()
        src = open(os.path.join(raw, "src", f[:-5] + ".txt"), encoding="utf-8").read()
        name = file_name(page)
        a = raw_html.index("<div id='wikitext'>")
        b = raw_html.index("<!--PageFooterFmt-->")
        body = raw_html[a:b]
        body = body[:body.rindex("</main>")]
        body = body[:body.rindex("</div>")] + "</div>"
        soup = BeautifulSoup(body, "html.parser")
        wt = soup.find("div", id="wikitext") or soup
        clean(wt, name)
        content = "".join(str(c) for c in wt.contents).strip()
        title = title_of(raw_html, src)
        if name == "index":
            crumbs = "<span>Colvin Gardens</span>"
            title_text = "Index – Colvin Gardens"
        else:
            crumbs = '<a href="index.html">Index</a> <span aria-hidden="true">›</span> <span>%s</span>' % html.escape(title)
            title_text = "%s – Colvin Gardens" % title
        text = PAGE.format(title_text=html.escape(title_text, quote=False), crumbs=crumbs,
                           title=html.escape(title, quote=False), content=content)
        text = text.replace("\t", "    ")
        open(os.path.join(OUT, name + ".html"), "w", encoding="utf-8").write(text)

    for f in os.listdir(os.path.join(raw, "files")):
        shutil.copy(os.path.join(raw, "files", f), os.path.join(OUT, "Images", f))
    print("%d pages written to %s" % (len(pages), OUT))


if __name__ == "__main__":
    main()
