"""Generate small clearly-labelled TEST fixture PDFs for the test suite.

Run once before running pytest (or let conftest.py call it automatically):

    python tests/fixtures/create_fixtures.py

Produces:
  tests/fixtures/wheat_guide_TEST.pdf    + sidecar .json  (English doc)
  tests/fixtures/gehu_margdarshika_TEST.pdf + sidecar .json (Hindi doc)
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent


def _make_pdf(path: Path, text: str) -> None:
    """Write a minimal single-page PDF containing *text*."""
    import os
    import sys

    if sys.platform == "win32":
        scripts_dir = os.path.join(sys.prefix, "Scripts")
        if os.path.isdir(scripts_dir):
            os.add_dll_directory(scripts_dir)

    try:
        import pymupdf as fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=11)
    doc.save(str(path))
    doc.close()


def _make_sidecar(pdf_path: Path, meta: dict) -> None:
    with (pdf_path.with_suffix(".json")).open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def create_all() -> None:
    HERE.mkdir(parents=True, exist_ok=True)

    # ── English fixture: wheat production guide ─────────────────────────────
    wheat_text = (
        "TEST FIXTURE – ICAR Wheat Production Guide (English)\n\n"
        "Wheat (Triticum aestivum) is a major rabi crop in India.\n"
        "Recommended sowing time: October–November in North India.\n"
        "Irrigation: First irrigation at crown root initiation stage (21 days after sowing).\n"
        "Nutrient management: Apply 120 kg nitrogen, 60 kg phosphorus, 40 kg potash per hectare.\n"
        "Yellow leaves on wheat may indicate nitrogen deficiency or rust disease.\n"
        "For nitrogen deficiency, apply urea top-dressing.\n"
        "For rust, apply propiconazole fungicide as per ICAR guidelines.\n"
        "Contact your Krishi Vigyan Kendra (KVK) for local variety recommendations.\n"
        "Source: ICAR Wheat Research Directorate, Karnal.\n"
    )
    wheat_pdf = HERE / "wheat_guide_TEST.pdf"
    _make_pdf(wheat_pdf, wheat_text)
    _make_sidecar(
        wheat_pdf,
        {
            "source_title": "ICAR Wheat Production Guide [TEST FIXTURE]",
            "publisher": "ICAR – Indian Council of Agricultural Research",
            "url": "https://icar.org.in/test-fixture/wheat-guide",
            "topic": "wheat production, nitrogen deficiency, rust disease",
            "language": "en",
            "published_date": "2023-01-15",
            "retrieval_date": "2026-11-26",
            "region": "North India",
        },
    )
    print(f"Created: {wheat_pdf}")

    # ── Hindi fixture: gehu margdarshika ───────────────────────────────────
    gehu_text = (
        "परीक्षण सामग्री – गेहूँ उत्पादन मार्गदर्शिका (हिन्दी)\n\n"
        "गेहूँ भारत की प्रमुख रबी फसल है।\n"
        "बुआई का समय: अक्टूबर–नवम्बर, उत्तर भारत।\n"
        "सिंचाई: पहली सिंचाई बुआई के 21 दिन बाद करें।\n"
        "उर्वरक: प्रति हेक्टेयर 120 किलोग्राम नाइट्रोजन, 60 किलोग्राम फॉस्फोरस।\n"
        "पत्तियाँ पीली होने पर नाइट्रोजन की कमी या किट्ट रोग हो सकता है।\n"
        "नाइट्रोजन की कमी के लिए यूरिया का प्रयोग करें।\n"
        "अधिक जानकारी के लिए अपने कृषि विज्ञान केंद्र (KVK) से संपर्क करें।\n"
        "स्रोत: भारतीय गेहूँ एवं जौ अनुसंधान संस्थान, करनाल।\n"
    )
    gehu_pdf = HERE / "gehu_margdarshika_TEST.pdf"
    _make_pdf(gehu_pdf, gehu_text)
    _make_sidecar(
        gehu_pdf,
        {
            "source_title": "गेहूँ उत्पादन मार्गदर्शिका [TEST FIXTURE]",
            "publisher": "ICAR – भारतीय कृषि अनुसंधान परिषद",
            "url": "https://icar.org.in/test-fixture/gehu-guide",
            "topic": "गेहूँ, नाइट्रोजन, किट्ट",
            "language": "hi",
            "published_date": "2023-03-01",
            "retrieval_date": "2026-11-26",
            "region": "उत्तर भारत",
        },
    )
    print(f"Created: {gehu_pdf}")

    # ── NyayaSathi legal fixtures (in tests/fixtures/nyayasathi/) ───────────
    nyaya_dir = HERE / "nyayasathi"
    nyaya_dir.mkdir(parents=True, exist_ok=True)

    # 1. Central Consumer Protection Act (English)
    consumer_text = (
        "TEST FIXTURE – Consumer Protection Act, 2019 (Central)\n\n"
        "Section 35: Manner in which complaint shall be made.\n"
        "A consumer may file a complaint with the District Consumer Disputes Redressal "
        "Commission regarding defective goods or deficient services.\n"
        "Complaints can be filed electronically through the e-Daakhil portal or in writing.\n"
        "Effective Date: 2020-07-20.\n"
        "If you need help drafting a complaint, consult a qualified advocate or your "
        "District Legal Services Authority (DLSA / NALSA).\n"
    )
    consumer_pdf = nyaya_dir / "consumer_protection_TEST.pdf"
    _make_pdf(consumer_pdf, consumer_text)
    _make_sidecar(
        consumer_pdf,
        {
            "document_title": "Consumer Protection Act, 2019 [TEST FIXTURE]",
            "issuing_authority": "Ministry of Law and Justice, Government of India",
            "url": "https://www.indiacode.nic.in/test-fixture/consumer-protection-2019",
            "jurisdiction": "central",
            "applicable_state": "",
            "act_name": "Consumer Protection Act, 2019",
            "section_number": "Section 35",
            "publication_date": "2019-08-09",
            "effective_date": "2020-07-20",
            "last_updated_date": "2020-07-20",
            "retrieval_date": "2026-11-28",
            "language": "en",
        },
    )

    # 2. Central Legal Aid / NALSA (English doc – tests cross-lingual Hindi query)
    nalsa_text = (
        "TEST FIXTURE – Legal Services Authorities Act, 1987 (Central)\n\n"
        "Section 12: Criteria for giving free legal services (free legal aid).\n"
        "Women, children, members of Scheduled Castes or Scheduled Tribes, and "
        "citizens with low annual income are entitled to free legal aid from the "
        "National Legal Services Authority (NALSA) or State Legal Services Authority (SLSA).\n"
        "Effective Date: 1995-11-09.\n"
    )
    nalsa_pdf = nyaya_dir / "nalsa_legal_aid_hi_TEST.pdf"
    _make_pdf(nalsa_pdf, nalsa_text)
    _make_sidecar(
        nalsa_pdf,
        {
            "document_title": "विधिक सेवा प्राधिकरण अधिनियम, 1987 [TEST FIXTURE]",
            "issuing_authority": "NALSA – राष्ट्रीय विधिक सेवा प्राधिकरण",
            "url": "https://nalsa.gov.in/test-fixture/legal-aid-section-12",
            "jurisdiction": "central",
            "applicable_state": "",
            "act_name": "Legal Services Authorities Act, 1987",
            "section_number": "Section 12",
            "publication_date": "1987-10-11",
            "effective_date": "1995-11-09",
            "last_updated_date": "2020-01-01",
            "retrieval_date": "2026-11-28",
            "language": "hi",
        },
    )

    # 3. State law – Bihar Rent Control
    bihar_text = (
        "TEST FIXTURE – Bihar Buildings (Lease, Rent and Eviction) Control Act, 1982\n\n"
        "Section 11: Eviction of tenants in Bihar.\n"
        "In Bihar, a landlord cannot evict a tenant except in execution of a court decree "
        "on specified statutory grounds such as non-payment of rent or bona fide personal necessity.\n"
        "Effective Date: 1983-01-31.\n"
    )
    bihar_pdf = nyaya_dir / "bihar_rent_control_TEST.pdf"
    _make_pdf(bihar_pdf, bihar_text)
    _make_sidecar(
        bihar_pdf,
        {
            "document_title": "Bihar Buildings (Lease, Rent and Eviction) Control Act, 1982 [TEST FIXTURE]",
            "issuing_authority": "Government of Bihar, Law Department",
            "url": "https://state.bihar.gov.in/test-fixture/bihar-rent-control-1982",
            "jurisdiction": "state",
            "applicable_state": "Bihar",
            "act_name": "Bihar Buildings (Lease, Rent and Eviction) Control Act, 1982",
            "section_number": "Section 11",
            "publication_date": "1982-12-01",
            "effective_date": "1983-01-31",
            "last_updated_date": "2016-04-01",
            "retrieval_date": "2026-11-28",
            "language": "en",
        },
    )

    # 4. State law – Maharashtra Rent Control
    mh_text = (
        "TEST FIXTURE – Maharashtra Rent Control Act, 1999\n\n"
        "Section 16: When landlord may recover possession of premises in Maharashtra.\n"
        "In Maharashtra, a landlord may sue for eviction only before the Small Causes Court "
        "or Civil Judge on grounds listed in Section 16 of the Maharashtra Rent Control Act.\n"
        "Effective Date: 2000-03-31.\n"
    )
    mh_pdf = nyaya_dir / "maharashtra_rent_control_TEST.pdf"
    _make_pdf(mh_pdf, mh_text)
    _make_sidecar(
        mh_pdf,
        {
            "document_title": "Maharashtra Rent Control Act, 1999 [TEST FIXTURE]",
            "issuing_authority": "Government of Maharashtra, Law and Judiciary Department",
            "url": "https://lj.maharashtra.gov.in/test-fixture/maharashtra-rent-control-1999",
            "jurisdiction": "state",
            "applicable_state": "Maharashtra",
            "act_name": "Maharashtra Rent Control Act, 1999",
            "section_number": "Section 16",
            "publication_date": "2000-03-10",
            "effective_date": "2000-03-31",
            "last_updated_date": "2018-01-01",
            "retrieval_date": "2026-11-28",
            "language": "en",
        },
    )

    print("All test fixtures created successfully.")


if __name__ == "__main__":
    create_all()
