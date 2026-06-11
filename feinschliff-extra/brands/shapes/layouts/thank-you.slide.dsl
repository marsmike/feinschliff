---
role: closer
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
when_not_to_use: [role=content-columns, role=data-quantity, role=data-comparison, role=data-timeline, role=concept-diagram]
family: closing
fixed_chrome: true
description: 'Closing slide: large blue circle left bearing Thank You title; name, phone, email, URL lines right; geometric
  accents'
chrome_subject: purple circle top-left, orange square outline bottom-left, teal circle partial and blue dots; brand-neutral
chrome_note: 'carries native source chrome verbatim: 1 illustration'
slide_index: 13
slots:
  text_1: {role: title, chars: 270, default: Thank you}
  text_2: {role: body, chars: 833, default: Brita Tamm\n502-555-0152\nbrita@firstupconsultants.com\nwww.firstupconsultant…}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: thank-you
canvas 1920x1080
theme shapes

native graphic1 xml_file:"native/5b4ca506197c.xml"
text 60,120 style:sub color:paper size:44pt autoshrink:true valign:middle padding:14,7,14,7 maxwidth:970 maxheight:839 "{{ text_1 | default(\"Thank you\") }}"
text 1040,119 style:body color:black size:24pt autoshrink:true valign:middle padding:14,7,14,7 maxwidth:870 maxheight:837 "{{ text_2 | default(\"Brita Tamm\n502-555-0152\nbrita@firstupconsultants.com\nwww.firstupconsultants.com\") }}"
