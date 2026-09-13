# Sri Lanka district geography

`districts.geojson` contains real administrative polygons for all 25 districts,
mapped to all nine provinces in `districts.json`. Coordinates use GeoJSON
longitude/latitude order (WGS 84). This is a district overview layer, not an
incident footprint or a cadastral survey.

## Boundary source and attribution

**District boundaries: © OpenStreetMap contributors / Wambacher, via
geoBoundaries gbOpen. Licensed under the Open Data Commons Open Database
License 1.0 (ODbL).** Retain this attribution in the map interface and when
redistributing the geographic database. The boundary database remains subject
to the source license, independently of the application's code license.

- [geoBoundaries metadata API](https://www.geoboundaries.org/api/current/gbOpen/LKA/ADM2/)
- [Pinned simplified GeoJSON, revision 9469f09](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/LKA/ADM2/geoBoundaries-LKA-ADM2_simplified.geojson)
- [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright)
- [ODbL 1.0 license](https://opendatacommons.org/licenses/odbl/1-0/)

Downloaded 2026-09-13. The metadata identifies boundary ID
`LKA-ADM2-46371173`, represented year **2017**, source update **2023-01-19**,
build date **2023-12-12**, source **OpenStreetMap, Wambacher**, and 25
administrative units. The download date does not imply that boundaries were
surveyed or updated in 2026.

The upstream simplified file is 241,213 bytes; its SHA-256 is
`90c7e2940f78f85d9810a1f0915627b660a2b6efe381c2becf245b4cbaa8286c`.
The packaged file is 204,326 bytes. Optimization removes JSON whitespace;
upstream coordinates, polygon rings, and islands are retained without further
geometric simplification or rounding. Features are sorted by canonical name.
Properties are normalized to `name` and `province`, with original `sourceName`,
`shapeID`, and `shapeISO` retained. `Monaragala District` is normalized to
`Moneragala`; both spellings are recognized by the dictionary. Source ISO
codes must not be treated as Sri Lankan census district codes, whose Northern
Province numbering differs.

## Names and administrative mapping

`districts.json` has `districts` and `provinces` arrays. District entries have
`name`, `province`, and `aliases` objects with `en`, `si`, and `ta` arrays.
Province entries have `name` and the same alias structure. District canonical
names and province membership are factual administrative data. References:
[Department of Census and Statistics administrative resources](https://www.statistics.gov.lk/qlink/AdminDivCode)
and the [Sri Lanka subdivision reference table](https://en.wikipedia.org/wiki/ISO_3166-2:LK).
The reference table's Sinhala and Tamil forms were used to check the locally
curated search aliases; these are practical matching terms, not an exhaustive
official transliteration standard. Province English aliases generally use
the full phrase ending in "Province" so ordinary directional words do not
automatically become province-wide alerts.

Location matching should resolve the longest province phrase first, so
"North Central Province" does not become "Central Province". The same care is
needed for Sinhala and Tamil names. A mentioned location indicates textual
relevance, not confirmation that the whole district or province is affected.

Run `python -m pytest tests/test_geography.py -q` to check completeness,
province membership, multilingual aliases, boundary matching, coordinate
bounds, ring closure, and payload size.