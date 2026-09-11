# Template execution contract - artigo técnico Projeto 100K

## Reference

- Retained reference: `C:\Users\vinic\Downloads\Do ambiente virtual à imersão internacional.docx`
- SHA-256: `3cd380db38fcd3954752e52d7fe4b6bc4b092820240d6d414ccd772d0f7927da`
- Rendered reference: 6 pages in `.codex/tmp_artigo_100k/template-reference-render/`
- Evidence: `.codex/tmp_artigo_100k/reference_inventory.json` and `.codex/tmp_artigo_100k/template-style-evidence.json`
- Sections: 1; body paragraphs: 78; body tables: 4; inline shapes: 5.

## Page system

- A4 portrait: 8.2708 x 11.6944 in.
- Margins: top 1.1812 in, bottom 0.7875 in, left 1.1812 in, right 0.7875 in.
- Header distance: 0.5 in; footer distance: 0.6292 in.
- One continuous section; no different first page and no odd/even variants.
- Preserve the reference header and footer parts unchanged. They provide the red upper-right page-number shape, gray lower-left polygon, and SENAI lower-right mark.

## Typography and paragraph roles

- Typeface: Arial throughout.
- Portuguese and English titles: 12 pt, bold, uppercase, centered. A blank paragraph separates the two title lines and the author block.
- Author lines: 12 pt, bold, left aligned; superscript author markers preserved in the same visual position.
- Abstract labels: 12 pt, bold, uppercase. The Portuguese label uses `Heading 1` without numbering; the English label is a bold Normal paragraph.
- Body: 12 pt, justified, first-line indent 0.2958 in for narrative paragraphs; compact paragraph spacing. Abstract paragraphs are justified without first-line indent and use 5 pt space after.
- Main section headings: Arial 12 pt, bold, uppercase, 12 pt after. Use explicit visible section numbers to avoid dependence on cached numbering fields.
- Subheadings: Arial 12 pt, bold, sentence case, 12 pt after.
- Captions: `Caption` style, centered, Arial, compact; keep with the image immediately above.
- References: Arial 10 pt, left aligned, 12 pt after; italics only for publication titles when appropriate.

## Lists and tables

- No list or table is required in the technical article body. Narrative paragraphs and figures carry the argument.
- Do not reuse the biography tables from the reference because the requested page budget is 3-5 pages.

## Components and content flow

1. Portuguese title, English title, and four-author block.
2. `RESUMO`, keywords, `ABSTRACT`, and keywords.
3. Numbered sections: Introdução; Materiais e métodos; Resultados e discussão; Considerações finais.
4. Two compact composite figures with centered captions and source/limitation text.
5. References.

## Slot map

- Reference body (`word/document.xml`): editable and intentionally replaced with the technical article.
- Header/footer (`word/header1.xml`, `word/footer1.xml`, footer relationships): preserve-only.
- Styles, numbering, theme, settings, and section geometry: preserve-only except for paragraph-level overrides needed by the new body.
- Existing body figures and biography tables: removable; their media parts may remain unused to avoid package-wide cleanup.
- New article figures: add as inline drawings anchored in body paragraphs only.
- Reference biographies: omitted to satisfy the user-specified 3-5 page limit; no author facts are invented.

## Package preservation and fidelity gates

- Preserve header, footer, footer relationship, styles, numbering, theme, and section geometry.
- The new document must remain recognizably in the same SENAI article family: identical A4 geometry, repeating corner/footer furniture, Arial hierarchy, title/author block, abstract structure, justified text, caption treatment, and compact academic references.
- Expected deviations: body content, figures, pagination, and omission of the biography page.
- Final gate: 3-5 rendered pages; no clipping, overlap, unexpected blank page, broken caption, or orphaned heading; every page inspected at 100% zoom.
