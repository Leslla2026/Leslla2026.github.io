#!/usr/bin/env python3
import re, sys, io

BASE = "/Users/ludovica/Documents/Leslla2026.github.io"

STYLE_BLOCK = """<style>
  .boa-content {
    text-align: justify;
    text-justify: inter-word;
  }

  .boa-content p {
    margin-bottom: 1em;
  }

  .boa-content ul.boa-list,
  .boa-content ol.boa-list {
    text-align: left;
    margin: 0 0 1em 0;
  }

  .boa-main-title {
    text-align: left;
    font-size: 2rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid #333;
    padding-bottom: 0.3em;
    margin-bottom: 1em;
  }

  .boa-section-title {
    text-align: left;
    font-size: 1.4rem;
    font-weight: 700;
    margin: 2em 0 1em 0;
    border-bottom: 1px solid #999;
    padding-bottom: 0.2em;
  }

  .boa-toc {
    text-align: left;
    margin-bottom: 2em;
  }

  .boa-toc li {
    margin-bottom: 0.5em;
  }

  .abstract-entry {
    margin-bottom: 4em; /* almeno due righe vuote di distanza fra gli abstract */
    padding-top: 1em;
    border-top: 1px solid #e8e8e8;
  }

  .abstract-entry:first-of-type {
    border-top: none;
  }

  .abstract-authors {
    margin-bottom: 0.2em;
  }

  .abstract-keynote-note {
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 700;
    font-size: 0.85em;
    color: #555;
    margin: 0 0 0.5em 0;
  }

  .abstract-title {
    margin-top: 0;
    margin-bottom: 1em;
  }

  .abstract-refs-heading {
    margin-top: 1.5em;
  }

  .abstract-refs p {
    text-align: left; /* i riferimenti bibliografici restano non giustificati per leggibilità */
    text-indent: -2em;
    margin-left: 2em;
    margin-bottom: 1em;
  }

  .abstract-missing-note {
    font-style: italic;
    color: #a33;
  }
</style>"""


def strip_invisible(s):
    return s.replace('⁠', '').replace('​', '').replace('﻿', '')


def normalize_quotes(s):
    return (s.replace('“', '"').replace('”', '"')
             .replace('‘', "'").replace('’', "'"))


def wrap_url(m):
    url = m.group(1)
    trail = ''
    while url and url[-1] in '.,;:)]"\'':
        trail = url[-1] + trail
        url = url[:-1]
    return f'<a href="{url}">{url}</a>{trail}'


def process_text(s):
    s = strip_invisible(s)
    s = normalize_quotes(s)
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;').replace('>', '&gt;')
    # undo accidental escaping of already-desired < > none expected
    s = re.sub(r'(https?://\S+)', wrap_url, s)
    s = re.sub(r' {2,}', ' ', s)
    return s.strip()


def parse_body_blocks(lines):
    blocks = []
    para_buf = []
    list_buf = []
    list_type = None

    def flush_para():
        nonlocal para_buf
        if para_buf:
            blocks.append(('p', ' '.join(para_buf)))
            para_buf = []

    def flush_list():
        nonlocal list_buf, list_type
        if list_buf:
            blocks.append((list_type, list_buf))
        list_buf = []
        list_type = None

    for raw in lines:
        stripped = raw.strip()
        if stripped == '':
            flush_para()
            flush_list()
            continue
        m_dash = re.match(r'^[-•]\s+(.*)', stripped)
        m_num = re.match(r'^\d+\.\s+(.*)', stripped)
        m_o = re.match(r'^o\s+(.*)', stripped)
        if m_dash:
            flush_para()
            if list_type not in (None, 'ul'):
                flush_list()
            list_type = 'ul'
            list_buf.append(m_dash.group(1))
        elif m_num:
            flush_para()
            if list_type not in (None, 'ol'):
                flush_list()
            list_type = 'ol'
            list_buf.append(m_num.group(1))
        elif m_o and list_type == 'ol':
            list_buf.append(m_o.group(1))
        else:
            flush_list()
            para_buf.append(stripped)
    flush_para()
    flush_list()
    return blocks


def parse_refs(lines):
    text = '\n'.join(lines)
    raw_blocks = re.split(r'\n\s*\n', text)
    refs = []
    for b in raw_blocks:
        b = b.strip()
        if not b:
            continue
        joined = ' '.join(x.strip() for x in b.split('\n') if x.strip())
        refs.append(joined)
    return refs


def render_body(blocks):
    out = []
    for kind, content in blocks:
        if kind == 'p':
            out.append(f'  <p>{process_text(content)}</p>')
        elif kind in ('ul', 'ol'):
            out.append(f'  <{kind} class="boa-list">')
            for item in content:
                out.append(f'    <li>{process_text(item)}</li>')
            out.append(f'  </{kind}>')
    return '\n'.join(out)


def render_refs(refs):
    if not refs:
        return ''
    lines = ['  <h4 class="abstract-refs-heading">References</h4>',
             '  <div class="abstract-refs">']
    for r in refs:
        lines.append(f'    <p>{process_text(r)}</p>')
    lines.append('  </div>')
    return '\n'.join(lines)


class Entry:
    def __init__(self, source_id, header_lines, keynote, body_lines, ref_lines):
        self.source_id = source_id
        self.header_lines = header_lines
        self.keynote = keynote
        self.body_lines = body_lines
        self.ref_lines = ref_lines


def parse_entries(md_text):
    # region from first anchor onward
    first = re.search(r'<a id="([^"]*)"></a>', md_text)
    region = md_text[first.start():]

    poster_marker = re.search(r'\n#{2,3}\s*Posters\s*\n', region)
    poster_pos = poster_marker.start() if poster_marker else None

    anchor_iter = list(re.finditer(r'<a id="([^"]*)"></a>', region))
    entries = []
    for i, m in enumerate(anchor_iter):
        source_id = m.group(1)
        start = m.end()
        end = anchor_iter[i + 1].start() if i + 1 < len(anchor_iter) else len(region)
        chunk = region[start:end]
        is_poster = poster_pos is not None and m.start() > poster_pos
        # strip a lone "### Posters" heading line if it leaked into this chunk's tail
        chunk = re.sub(r'\n#{2,3}\s*Posters\s*\n', '\n', chunk)
        lines = chunk.split('\n')
        idx = 0
        header_lines = []
        n = len(lines)
        # skip leading blank lines before the first header line
        while idx < n and lines[idx].strip() == '':
            idx += 1
        # collect leading ### lines, allowing blank lines between them
        while idx < n:
            s = lines[idx].strip()
            if s.startswith('###'):
                header_lines.append(s[3:].strip())
                idx += 1
            elif s == '' and header_lines and idx + 1 < n and lines[idx + 1].strip().startswith('###'):
                idx += 1
            else:
                break
        # skip blank lines
        while idx < n and lines[idx].strip() == '':
            idx += 1
        keynote = False
        if idx < n and lines[idx].strip().upper() == 'KEYNOTE':
            keynote = True
            idx += 1
            while idx < n and lines[idx].strip() == '':
                idx += 1
        rest = lines[idx:]
        # find references marker
        ref_idx = None
        for j, l in enumerate(rest):
            if re.match(r'^#{2,3}\s*References\s*$', l.strip(), re.IGNORECASE):
                ref_idx = j
                break
        if ref_idx is not None:
            body_lines = rest[:ref_idx]
            ref_lines = rest[ref_idx + 1:]
        else:
            body_lines = rest
            ref_lines = []
        entries.append((is_poster, Entry(source_id, header_lines, keynote, body_lines, ref_lines)))
    return entries


ID_FIXES = {
    'day3': {'van hout': 'van-hout', 'Hajská': 'hajská'},
}


def build_html(day_key, title, permalink, md_text, toc_map, header_line_overrides=None):
    entries = parse_entries(md_text)
    id_fixes = ID_FIXES.get(day_key, {})
    header_line_overrides = header_line_overrides or {}

    main_entries = []
    poster_entries = []

    for is_poster, e in entries:
        anchor = id_fixes.get(e.source_id, e.source_id).lower().replace(' ', '-')
        header_lines = header_line_overrides.get(e.source_id, e.header_lines)
        if len(header_lines) < 2:
            raise ValueError(f'Entry {e.source_id} has fewer than 2 header lines: {header_lines}')
        title_raw = header_lines[-1].strip()
        title_raw = re.sub(r'^_+', '', title_raw)
        title_raw = re.sub(r'_+$', '', title_raw)
        authors_raw = '; '.join(h.strip() for h in header_lines[:-1])
        title_html = process_text(title_raw)
        authors_html = process_text(authors_raw)

        blocks = parse_body_blocks(e.body_lines)
        refs = parse_refs(e.ref_lines)

        keynote_html = '  <p class="abstract-keynote-note">Keynote</p>\n' if e.keynote else ''

        entry_html = (
            f'<!-- {anchor.upper()} -->\n'
            f'<div class="abstract-entry">\n'
            f'  <a id="{anchor}"></a>\n'
            f'  <h3 class="abstract-authors">{authors_html}</h3>\n'
            f'{keynote_html}'
            f'  <h3 class="abstract-title"><em>{title_html}</em></h3>\n\n'
            f'{render_body(blocks)}\n'
        )
        refs_html = render_refs(refs)
        if refs_html:
            entry_html += f'\n{refs_html}\n'
        entry_html += '</div>'

        toc_names, toc_title_override = toc_map[e.source_id]
        toc_title = toc_title_override if toc_title_override else title_html
        toc_item = f'  <li><a href="#{anchor}">{process_text(toc_names)}</a>, <em>{toc_title}</em></li>'

        if is_poster:
            poster_entries.append((toc_item, entry_html))
        else:
            main_entries.append((toc_item, entry_html))

    toc_lines = ['<h2 class="boa-main-title">Contents</h2>', '<ul class="boa-toc">']
    toc_lines += [t for t, _ in main_entries]
    toc_lines.append('</ul>')
    if poster_entries:
        toc_lines.append('<h3 class="boa-section-title">Posters</h3>')
        toc_lines.append('<ul class="boa-toc">')
        toc_lines += [t for t, _ in poster_entries]
        toc_lines.append('</ul>')

    body_parts = [h for _, h in main_entries]
    if poster_entries:
        body_parts.append('<h2 class="boa-section-title">Posters</h2>')
        body_parts += [h for _, h in poster_entries]

    html = f"""---
layout: default
title: {title}
permalink: {permalink}
---

{{% include site-logo.html %}}
{{% include page-header.html %}}

{STYLE_BLOCK}

<div class="boa-content">

{chr(10).join(toc_lines)}

{chr(10).join(2*chr(10)+e for e in [''])[2:]}
{(chr(10)+chr(10)).join(body_parts)}

</div>
"""
    return html


# ---------------------------------------------------------------------------
# TOC name-only maps: source_id -> (names_string, title_override_or_None)
# ---------------------------------------------------------------------------

DAY1_TOC = {
    'abbott': ("Marilyn L. Abbott, Kent K. Lee", "Shared metacognition in a LESLLA teacher journal club"),
    'aunio': ("Lotta Aunio", None),
    'bédard': ("Vincent Bédard", None),
    'drews': ("Kathrin Drews, Ina-Maria Maahs", None),
    'grünhage-monetti': ("Matilde Grünhage-Monetti, Silvia Miglio, Olessia Götzinger", None),
    'hauber-özer': ("Melissa Hauber-Özer, Kelly Leavitt", None),
    'hibbs': ("Brian Hibbs", None),
    'husby': ("Erika Husby", None),
    'lyasota': ("Victoria Lyasota", None),
    'lüpke': ("Friederike Lüpke", None),
    'maynard': ("Catherine Maynard, Véronique Fortier, Suzie Beaulieu, Valérie Amireault", None),
    'mendoza': ("Anna Mendoza, Elif Varlik, Eda Yildirimer", None),
    'obens': ("Katharina Obens, Ioanna Liakou, David Zimmermann", None),
    'pinto': ("Manuela Pinto, Darin Nshiwi, Ali Işik, Birgen Işik", None),
    'siekman': ("Bart Siekman, Sybren Spit, Josje Verhagen, Sible Andringa", None),
    'spit': ("Sybren Spit, Sible Andringa, Judith Rispens", None),
    'young-scholten': ("Martha Young-Scholten", None),
    'yildirimer': ("Eda Yildirimer", None),
}

DAY2_TOC = {
    'bartoli': ("Cecilia Bartoli, Kristýna Lorenzová", None),
    "d'agostino": ("Mari D'Agostino", None),
    'dalderop': ("Kaatje Dalderop, Annemarie Nuwenhoud", None),
    'egan': ("Patsy Egan, Janet Isserlis", None),
    'farina': ("Clelia Farina", None),
    'fortier': ("Véronique Fortier, Catherine Maynard, Suzie Beaulieu, Valérie Amireault", None),
    'gujord': ("Ann-Kristin Helland Gujord, Linda Evenstad Emilsen", None),
    'haznedar': ("Belma Haznedar, Elifcan Öztekin", None),
    'kerschhofer-puhalo': ("Nadja Kerschhofer-Puhalo", None),
    'laberge': ("Carl Laberge", None),
    'morand': ("Marie-Anne Morand, Claudia Kossinna", None),
    'schirò': ("Davide Schirò", None),
    'albanesi': ("Lorenzo Albanesi, Kristýna Lorenzová", None),
    'chuang': ("Tsun Yang Chuang, Morgane Jourdain, Emanuelle Canut", None),
    'dos-santos': ("Martina Franz dos Santos", None),
    'hayes-laughton': ("Rebecca Hayes Laughton", None),
}

DAY3_TOC = {
    'cotesta': ("Valentina Cotesta", None),
    'farina': ("Clelia Farina", None),
    'förster': ("Franziska Förster", None),
    'grinden': ("Live Grinden", None),
    'gujord': ("Ann-Kristin Helland Gujord, Linda Evenstad Emilsen", None),
    'Hajská': ("Markéta Hajská, Pavel Kubanik", None),
    'kurvers': ("Jeanne Kurvers, Roeland van Hout", None),
    'maffia': ("Marta Maffia, Raymond Siebetcheu, Anna De Meo, Noemi Lari", None),
    'malessa': ("Eva Malessa, Live Grinder, Skye Playsted, Jemima Riller Kempster", None),
    'minuz': ("Fernanza Minuz, Alessandro Borri", None),
    'van hout': ("Roeland van Hout", None),
    'vanbuel': ("Marieke Vanbuel", None),
}

DAY3_HEADER_OVERRIDES = {
    'gujord': [
        "Ann-Kristin Helland Gujord, Universitetet i Bergen",
        "Linda Evenstad Emilsen, Høgskolen i Østfold",
        "_Early grammatical development in a non-academic sample_",
    ],
}

if __name__ == '__main__':
    with open(f'{BASE}/hidden_book_abstracts_day1.md', encoding='utf-8') as f:
        md1 = f.read()
    with open(f'{BASE}/hidden_book_abstracts_day2.md', encoding='utf-8') as f:
        md2 = f.read()
    with open(f'{BASE}/hidden_book_abstracts_day3.md', encoding='utf-8') as f:
        md3 = f.read()

    html1 = build_html('day1', 'Book of abstracts - day 1', '/html_book_abstracts_day1/', md1, DAY1_TOC)
    html2 = build_html('day2', 'Book of abstracts - day 2', '/html_book_abstracts_day2/', md2, DAY2_TOC)
    html3 = build_html('day3', 'Book of abstracts - day 3', '/html_book_abstracts_day3/', md3, DAY3_TOC,
                        header_line_overrides=DAY3_HEADER_OVERRIDES)

    import os
    OUT = os.path.dirname(os.path.abspath(__file__))
    with open(f'{OUT}/out_day1.html', 'w', encoding='utf-8') as f:
        f.write(html1)
    with open(f'{OUT}/out_day2.html', 'w', encoding='utf-8') as f:
        f.write(html2)
    with open(f'{OUT}/out_day3.html', 'w', encoding='utf-8') as f:
        f.write(html3)

    print('done')
