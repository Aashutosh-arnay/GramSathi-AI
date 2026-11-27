# GramSathi AI Starter Dataset — Official Sources

**Total `dataset/` size:** 12.69 MB (under the 50 MB threshold).  
**Retrieval date:** `2026-11-28`

---

## FarmSathi AI (`dataset/farmsathi/` — 9 PDFs, 1,110 chunks)

| File | Publisher / Issuing Authority | Source URL | Retrieval Date | Unknown / `null` Fields |
|---|---|---|---|---|
| `pmkisan_operational_guidelines.pdf` | Ministry of Agriculture & Farmers Welfare, Government of India | https://pmkisan.gov.in/Documents/OPERATIONAL%20GUIDELINES.pdf | 2026-11-28 | `published_date` |
| `pmkisan_faq.pdf` | Ministry of Agriculture & Farmers Welfare, Government of India | https://pmkisan.gov.in/Documents/FAQPMKISAN.PDF | 2026-11-28 | `published_date` |
| `pmkisan_additional_faq.pdf` | Ministry of Agriculture & Farmers Welfare, Government of India | https://pmkisan.gov.in/Documents/ADDITIONAL-FAQ-IN-RESPECTIVE-OF-THE-PM2.pdf | 2026-11-28 | None |
| `pmkisan_amendment_og.pdf` | Ministry of Agriculture & Farmers Welfare, Government of India | https://pmkisan.gov.in/Documents/Amendment%20to%20OG-converted.pdf | 2026-11-28 | None |
| `nmsa_soil_health_management_guidelines.pdf` | Department of Agriculture, Cooperation & Farmers Welfare, MoA&FW | https://agriwelfare.gov.in/sites/default/files/NMSA%20-%20Guidelines%20updated%20on%2009.02.2017%20%20.pdf | 2026-11-28 | None |
| `icar_iiwbr_wheat_pocket_guide.pdf` | ICAR - Directorate of Wheat Research (IIWBR), Karnal | https://iiwbr.org.in/wp-content/uploads/2023/08/EB-52-Wheat-Cultivation-in-India-Pocket-Guide.pdf | 2026-11-28 | None |
| `icar_crri_direct_seeded_rice.pdf` | ICAR - Central Rice Research Institute (CRRI) | https://icar-crri.in/wp-content/uploads/2025/12/CRRI_Technology-Bulletin_No-250.pdf | 2026-11-28 | `published_date` |
| `ppqs_ipm_wheat.pdf` | Directorate of Plant Protection, Quarantine & Storage (PPQS), MoA&FW | https://www.ppqs.gov.in/sites/default/files/wheat.pdf | 2026-11-28 | `published_date` |
| `ppqs_ipm_rice.pdf` | NCIPM / Directorate of Plant Protection, Quarantine & Storage (PPQS) | https://www.ppqs.gov.in/sites/default/files/rice.pdf | 2026-11-28 | `published_date` |

---

## NyayaSathi AI (`dataset/nyayasathi/` — 8 PDFs, 749 chunks)

| File | Publisher / Issuing Authority | Source URL | Retrieval Date | Unknown / `null` Fields |
|---|---|---|---|---|
| `consumer_protection_act_2019.pdf` | Ministry of Law and Justice, Government of India | https://consumeraffairs.gov.in/public/upload/files/CP%20Act%202019_1732700731.pdf | 2026-11-28 | `section_number`, `effective_date`, `last_updated_date` |
| `consumeraffairs_citizen_charter_2025_26.pdf` | Department of Consumer Affairs, Government of India | https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/menus/Citizen_Chartermenu.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date`, `last_updated_date` |
| `nalsa_lok_adalat_regulations_2009.pdf` | National Legal Services Authority (NALSA) | https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2025/04/202504081740620817.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date` |
| `nalsa_free_competent_legal_services_2010.pdf` | National Legal Services Authority (NALSA) | https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2025/04/20250408420654188.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date` |
| `nalsa_public_grievance_sop.pdf` | National Legal Services Authority (NALSA) | https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2025/04/202504081003291904.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date`, `last_updated_date` |
| `nalsa_widows_access_to_justice.pdf` | National Legal Services Authority (NALSA) | https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2025/04/202504081285168343.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date`, `last_updated_date` |
| `nalsa_parole_furlough_sop_2022.pdf` | National Legal Services Authority (NALSA) | https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2025/04/202504081828372825.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date`, `last_updated_date` |
| `rti_act_2005_en.pdf` | Ministry of Law and Justice, Government of India (hosted on CIC) | https://cic.gov.in/sites/default/files/RTI-Act_English.pdf | 2026-11-28 | `section_number`, `publication_date`, `effective_date` |

---

## Documents Not Included (Could Not Download, Verify, or Extract Clean Text)

| Document | Reason Excluded | Attempted Source |
|---|---|---|
| PMFBY Operational Guidelines | `pmfby.gov.in/guidelines` is a client-rendered SPA; direct PDF URL could not be extracted via HTTP fetch without browser rendering | `https://pmfby.gov.in/guidelines` |
| PM-KISAN KCC Leaflet (`Kcc.pdf`) | Downloaded PDF is a scanned image with 0 extractable text characters | `https://pmkisan.gov.in/Documents/Kcc.pdf` |
| India Code Acts (CP Act 2019, LSA Act 1987, RTI Act 2005) | `indiacode.nic.in` handle pages timed out on HTTP requests (CP Act 2019 and RTI Act 2005 were instead obtained from `consumeraffairs.gov.in` and `cic.gov.in`) | `https://www.indiacode.nic.in/handle/123456789/15256`, `1643`, `2083` |
| Legal Services Authorities Act, 1987 (`thc.nic.in`) | One URL returned HTTP 404; the alternate URL (`10.5 MB`) is a 29-page scanned image with 0 extractable text characters | `https://www.thc.nic.in/Central%20Governmental%20Acts/Legal%20Services%20Authorities%20Act,%201987.pdf` |
| RTI Act, 2005 (Hindi) | Returned HTTP 404 | `https://cic.gov.in/sites/default/files/RTI-Act_Hindi.pdf` |
| DoJ Tele-Law / DISHA Scheme Booklet | Downloaded PDF (`6.5 MB`) is image-based with 0 extractable text characters | `https://www.doj.gov.in/static/uploads/2025/11/9063ae52916891653adf8ffc4720a897.pdf` |
