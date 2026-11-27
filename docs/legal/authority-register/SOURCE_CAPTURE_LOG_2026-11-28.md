# Primary-source capture log — 2026-11-28

## Capture status

**Step 2 is not complete.** Official primary-source locations have been identified and some PDF text is visible through the web renderer, but the original HTML/PDF bytes could not be downloaded into the execution environment. Direct download attempts failed with DNS/network errors, and BDLaws/IRD page opens returned HTTP 502. Therefore no original primary-source file has been committed and no primary-source binary SHA-256 is claimed.

The only hashed source-related file in this PR is a **derived text extract** from the Finance Act 2022 Gazette. Its hash is not the Gazette PDF hash.

## Source inventory

| Instrument / source | Official provenance and URL | Retrieval observation | Original bytes / SHA-256 |
|---|---|---|---|
| Companies Act 1994 (Act XVIII of 1994), current consolidated text | Legislative and Parliamentary Affairs Division / BDLaws: https://bdlaws.minlaw.gov.bd/act-print-788.html | Search-rendered official text observed 2026-11-28; page open returned 502 | NOT CAPTURED / NOT HASHED |
| SRO No. 321-Law/1994 (commencement notification) | Bangladesh Government Press Gazette index (10 Nov 1994, Ministry of Commerce, Gazette p.5033): https://www.dpp.gov.bd/upload_file/gazettes/321-Law-1994.pdf | Official PDF URL resolved; one-page PDF text extraction is garbled; binary not downloaded | NOT CAPTURED / NOT HASHED |
| Companies (Second Amendment) Act 2020 (Act No.24 of 2020) | Bangladesh Government Press, Extraordinary Gazette, 26 Nov 2020, pp.12417-12427: https://www.dpp.gov.bd/upload_file/gazettes/37932_40268.pdf | Official 11-page PDF resolved from Government Press index; text extraction observed; binary not downloaded | NOT CAPTURED / NOT HASHED |
| Finance Act 2022 (Act XIII of 2022) | Bangladesh Government Press, Extraordinary Gazette, 30 Jun 2022, pp.10951-11074: https://www.dpp.gov.bd/upload_file/gazettes/45026_26037.pdf | Official 124-page PDF resolved; Schedule I extract inspected at printed pp.10980-10981; binary not downloaded | NOT CAPTURED / NOT HASHED |
| Stamp Act 1899 (Act II of 1899), current consolidated text | Legislative and Parliamentary Affairs Division / BDLaws: https://bdlaws.minlaw.gov.bd/act-print-77.html | Official search result observed 2026-11-28; page open returned 502 | NOT CAPTURED / NOT HASHED |
| SRO No.386-Law/2026 (listed 2 Nov 2026) | Internal Resources Division official stamp-law index: https://ird.gov.bd/pages/static-pages/694032d135ce18e1c0562e66 | Index search result lists the SRO; page open returned 502; instrument text not retrieved | NOT LOCATED AS TEXT / NOT HASHED |

## Derived extract

- File: `derived-extracts/FINANCE_ACT_2022_SCHEDULE_I_SHARE_TRANSFER_EXCERPT.txt`
- Extract SHA-256: `aef36969fe703053554d5c4ca7e3d14c0a9ae25719fd76a35e3f998a0bab4ab6`
- It is a transcription of the English Schedule I excerpt as rendered from the official Gazette PDF, not a binary source capture.
- It records Article 61(a), the 1.5% consideration rate, and the listed-public-company exemption as published in the 2022 Finance Act Gazette.
- It does not prove that no later SRO or amendment changed the position by 2026-11-28.

## Next capture operation

Obtain the original PDFs/HTML from a network-enabled workstation or by user upload. For every original source file, preserve the exact downloaded bytes, URL, retrieval timestamp/timezone, publisher, language, file size, and SHA-256; do not replace the binary with OCR text. Prioritise SRO No.386-Law/2026 and the commencement SRO No.321-Law/1994.
