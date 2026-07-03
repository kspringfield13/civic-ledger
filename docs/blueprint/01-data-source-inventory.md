# Blueprint 01 — Prioritized Data Source Inventory

Status: DRAFT registry candidates. Per `DATA_SOURCE_POLICY.md`, **no entry here
authorizes ingestion** — each source still needs a completed, operator-approved
entry (the `Approved by` line filled in) committed before ingestion code merges.
This document is the prioritized shortlist and working notes for those entries.

Conventions used below:

- **Tier** follows `DATA_SOURCE_POLICY.md` (1 authoritative / 2 supporting / 3 contextual).
- **Confidence** (high / moderate / low) is *our confidence that the source
  exists and works as described here*, not data quality. Every entry lists
  what must be verified before we rely on it. Nothing below has been
  live-verified from this repo; treat all URLs and field names as
  "verify on first pull."
- **Difficulty** is expected engineering effort to a reliable, provenance-
  compliant ingest (low / med / high).
- Field names in "Fields provided" are indicative, not gospel — the ingestion
  PR must pin exact column names from the actual data dictionary and record
  them in the registry entry.
- All raw pulls land in `data/raw/` (git-ignored) with SHA-256 +
  locator + timestamp on `SourceDocument`, per `EVIDENCE_STANDARD.md`.

---

## Tier 1 — authoritative (usable for matching and signals)

### 1. USAspending.gov — award data (bulk download + API)

- **Name:** USAspending.gov (prime awards: contracts + assistance)
- **Tier:** 1
- **URL / access point:** `https://www.usaspending.gov` (bulk: Award Data Archive / custom download); API: `https://api.usaspending.gov`
- **Access basis:** public (U.S. government open data, DATA Act / FFATA mandate)
- **License / terms summary:** U.S. government work; public domain in practice. Verify current data-use notice on the site and record it.
- **Rate limits / etiquette:** API is keyless as of our knowledge; be polite (backoff, cache, prefer bulk for volume). **Verify** current rate-limit guidance before writing the client.
- **Purpose in pipeline:** primary population of `ContractAward` and `GrantAward`; the transaction universe that detectors run over; base-rate denominators for dashboards.
- **Fields provided (key fields we need):** award ID (PIID/FAIN), awarding/funding agency + sub-agency codes, recipient name, recipient UEI, recipient address, action date, period of performance, obligated amount, NAICS, PSC, award type, description. Exact field names differ between bulk CSV and API JSON — pin per retrieval method.
- **Update cadence:** agencies report on a rolling basis; site data generally refreshed nightly/near-daily, but **underlying agency submissions lag** (see quality issues). Verify current refresh schedule.
- **Retrieval method:** bulk download (monthly archives) for backfill; API for incremental/targeted pulls.
- **Expected difficulty:** med (volume + schema breadth; the API itself is straightforward).
- **Known quality issues:** (a) reporting lag — agencies submit on statutory schedules, and some transactions appear weeks late; (b) documented agency underreporting/quality gaps (GAO and agency IGs have repeatedly reported DATA Act quality issues — cite specific reports in the registry entry, don't hand-wave); (c) recipient name inconsistency across awards; (d) DUNS→UEI transition (April 2022): pre-2022 records key on DUNS, later on UEI — crosswalk needed, and some historical linkage is genuinely broken; (e) award descriptions are free text and often uninformative.
- **Personal data present?** Sole proprietors' names can appear as recipient names; within policy (public spending record, official capacity). No enrichment.
- **Confidence:** high that the source, bulk archive, and public API exist. **Verify:** current API endpoints/pagination, bulk file layout + data dictionary, refresh cadence.

### 2. SAM.gov — Exclusions extract

- **Name:** SAM.gov Exclusions (debarment/suspension list)
- **Tier:** 1
- **URL / access point:** `https://sam.gov` → Data Services (public exclusions extract, CSV/flat file); there is also an Exclusions API under `api.sam.gov`.
- **Access basis:** public. **Caveat:** downloading extracts and getting an API key may require a *free* SAM.gov user account. That is a registered account on a public system used as intended — permitted — but record it in the registry entry as the access basis detail, and the operator (not the agent) creates/holds the account.
- **License / terms summary:** U.S. government data; verify SAM.gov terms of use for data services and record excerpt.
- **Rate limits / etiquette:** API keys have quotas (verify current numbers). Prefer the daily extract; do not hammer the API.
- **Purpose in pipeline:** populates `ExclusionRecord`; the authoritative input for the Phase-2 `debarred_vendor_match` detector.
- **Fields provided (key fields we need):** excluded entity/individual name, UEI (formerly DUNS), classification (firm/individual), exclusion type/program, activation date, termination date, excluding agency, CT (cross-reference) records, address. Pin exact extract column names on first pull.
- **Update cadence:** extract regenerated daily (verify).
- **Retrieval method:** bulk download (daily extract) preferred; API for spot lookups.
- **Expected difficulty:** low (single flat file, modest size).
- **Known quality issues:** name-only records without UEI (older/individual exclusions) force fuzzy matching — the dominant FP mode for the debarment detector; UEI/DUNS transition affects historical joins; some records are individuals, which our matching must handle under the individuals-in-official-capacity rule only.
- **Personal data present?** Yes — excluded *individuals* are listed by name/address in the official record. Within policy (official exclusion record); we store what the record contains, no enrichment.
- **Confidence:** high that public exclusions data exists (successor to EPLS). **Verify:** whether current extract download requires an account/API key, exact file name/format, refresh schedule.

### 3. SAM.gov — Entity registrations (public extract)

- **Name:** SAM.gov Entity Management (registration) data
- **Tier:** 1
- **URL / access point:** `https://sam.gov` Data Services / Entity Management API (`api.sam.gov`)
- **Access basis:** public *for the non-sensitive subset*. SAM entity data is split: a public extract, and restricted ("FOUO"/sensitive) fields (e.g., banking data, some POC details) that require roles we do not have and **must not** be sought.
- **License / terms summary:** U.S. government data; verify data services ToU. Explicitly record which extract variant (public) we use.
- **Rate limits / etiquette:** API key quotas; monthly public extract is large. Verify.
- **Purpose in pipeline:** vendor master data — canonical names, UEI, CAGE, addresses, registration dates, entity structure, points of contact in registered capacities. Feeds `Vendor`, `Address`, `PersonOfficer`, and entity resolution; enables signals like "newly registered vendor wins large sole-source award."
- **Fields provided:** legal business name, DBA name, UEI, CAGE code, physical/mailing address, registration/expiration dates, entity structure, NAICS list, socio-economic certifications (self-reported). Pin exact columns per public-extract data dictionary.
- **Update cadence:** monthly public extract; API near-real-time (verify).
- **Retrieval method:** bulk download (monthly) + API for deltas.
- **Expected difficulty:** med (large fixed-width/pipe-delimited legacy formats are fiddly; verify current format).
- **Known quality issues:** self-reported fields (size/socio-economic status) are assertions, not verified facts — a signal input, never a conclusion; registrations lapse and re-register, creating duplicate-looking entities; UEI transition again.
- **Personal data present?** Registered POCs and officers by name — official/registered capacity only, within policy. We ingest only the public extract; **never** attempt access to restricted fields.
- **Confidence:** moderate. The public entity extract exists to our knowledge, but the exact split of public vs. restricted fields and the current file format **must be verified** against SAM.gov data services documentation before writing ingestion.

### 4. FPDS-NG — federal contract actions (via USAspending, or ATOM feed)

- **Name:** Federal Procurement Data System – Next Generation
- **Tier:** 1
- **URL / access point:** primary path: already included in USAspending contract data (FPDS is USAspending's contract source). Direct path: `https://www.fpds.gov` ATOM feed / archives.
- **Access basis:** public.
- **License / terms summary:** U.S. government data; verify FPDS.gov usage terms if we hit it directly.
- **Rate limits / etiquette:** the ATOM feed pages small (10 records/page historically) — slow for bulk; be polite. Verify current limits.
- **Purpose in pipeline:** contract-action detail beyond USAspending's rollups when a detector needs it: modification history, extent-competed, number of offers received, IDV linkage. Feeds competition-related detectors (e.g., repeated sole-source, split purchases just under thresholds).
- **Fields provided (key):** PIID, modification number, extent competed, solicitation procedures, number of offers, type of contract, IDV PIID, contracting office. Verify against the FPDS data dictionary / USAspending field mapping.
- **Update cadence:** contract actions generally reported within days; **DoD actions are delayed ~90 days by policy** (verify current delay rule).
- **Retrieval method:** prefer USAspending bulk/API (already-normalized FPDS data); ATOM feed only if a needed field is missing there.
- **Expected difficulty:** low via USAspending; high via ATOM (pagination, XML, throughput).
- **Known quality issues:** data-entry quality varies by contracting office (misclassified competition codes are a known FP mode for competition detectors); DoD delay skews recency analyses.
- **Personal data present?** Contracting officer names may appear — official capacity, within policy.
- **Confidence:** high that FPDS exists and feeds USAspending; moderate on ATOM feed mechanics. **Verify:** which specific fields survive into USAspending before deciding we need the direct feed at all.

### 5. Federal subaward data (FFATA/FSRS, served via USAspending)

- **Name:** FFATA Subaward Reporting (FSRS) data
- **Tier:** 1
- **URL / access point:** via USAspending (subawards download/API endpoints). Origin system was FSRS.gov; **note:** FSRS functions have been transitioning into SAM.gov — verify current system of record before citing it.
- **Access basis:** public.
- **License / terms summary:** U.S. government data (same posture as USAspending).
- **Rate limits / etiquette:** same as USAspending.
- **Purpose in pipeline:** first-tier subcontract/subgrant visibility — enables pass-through signals (prime keeps X%, sub does the work; sub is on the exclusions list while prime is clean).
- **Fields provided (key):** prime award ID, subawardee name + UEI, subaward amount, subaward date, place of performance, description.
- **Update cadence:** primes report monthly for subawards ≥ $30k (verify current threshold and schedule).
- **Retrieval method:** bulk download via USAspending; API.
- **Expected difficulty:** low-med (piggybacks on USAspending ingest).
- **Known quality issues:** **substantial underreporting** — subaward reporting compliance is a long-documented weakness (GAO/IG coverage exists; cite specifics in registry entry). Absence of a subaward record is weak evidence of anything. Only first-tier subs are reported.
- **Personal data present?** Same posture as prime awards.
- **Confidence:** moderate-high that subaward data is retrievable via USAspending; low on FSRS.gov's current status as a standalone system. **Verify:** current reporting threshold, and where the authoritative feed now lives.

### 6. SBA open data (loan/assistance programs)

- **Name:** SBA published datasets (e.g., 7(a)/504 loan data; PPP loan-level FOIA data)
- **Tier:** 1
- **URL / access point:** SBA open data pages / `data.sba.gov` (verify exact portal); PPP loan-level data was published following FOIA litigation.
- **Access basis:** public (agency-published datasets).
- **License / terms summary:** U.S. government data; verify per-dataset notes — PPP files carry specific context/caveat documentation that must be recorded.
- **Purpose in pipeline:** cross-program view of the same vendors (a vendor's SBA assistance footprint next to its contract footprint); historically a high-yield domain for *documented* FWA enforcement, so useful for retro-validation of detectors against public DOJ/OIG outcomes.
- **Fields provided (key):** borrower/recipient name, address, loan amount, approval date, lender, jobs reported, NAICS, forgiveness data (PPP). Field availability varies by dataset — pin per file.
- **Update cadence:** varies by dataset; PPP data is essentially historical/closed. Verify per dataset.
- **Retrieval method:** bulk download.
- **Expected difficulty:** low-med (flat files; entity resolution to our vendor table is the real work — these datasets have **no UEI**, name+address matching only).
- **Known quality issues:** self-reported application data; name/address inconsistency is severe; PPP data includes many sole proprietors, i.e., individuals — heightened care under the individuals policy (analysis stays at transaction/organization level; no ranking or profiling of individuals).
- **Personal data present?** Yes — sole-proprietor borrower names are personal names in a public record. Within policy only if we treat them strictly as recipients-of-record and never enrich. Flag this in the registry entry for explicit operator sign-off.
- **Confidence:** moderate-high the datasets exist; **verify** current hosting location and each file's data dictionary before ingest.

### 7. Agency OIG reports + Oversight.gov

- **Name:** Oversight.gov (CIGIE aggregate of Inspector General reports) + individual agency OIG sites
- **Tier:** 1
- **URL / access point:** `https://www.oversight.gov` (search + report listings); agency OIG sites for source PDFs.
- **Access basis:** public.
- **License / terms summary:** U.S. government works; verify site terms for any bulk-access guidance.
- **Rate limits / etiquette:** no published API to our knowledge — polite, low-rate retrieval of listing pages and PDFs only; respect robots.txt; **verify** whether an API or bulk export exists before building anything.
- **Purpose in pipeline:** two uses: (a) corroboration evidence attached to case leads (an IG already flagged this program/vendor pattern); (b) detector-design input — IG findings tell us which patterns actually materialize. Also the natural *destination* context: leads that a human escalates go to an OIG, outside this system.
- **Fields provided:** report title, agency, date, type, PDF. Unstructured — we extract citations, not structured records.
- **Update cadence:** continuous as reports publish.
- **Retrieval method:** manual/curated at first (operator saves PDFs, uploads with provenance); semi-automated later only after verifying acceptable access method.
- **Expected difficulty:** med (PDF text extraction; no stable structured feed assumed).
- **Known quality issues:** reports are conclusions about *programs and past periods*, not live vendor data; mapping a report's subject to our entity table is manual.
- **Personal data present?** Names appear in official findings; we quote, never extend.
- **Confidence:** high that oversight.gov exists and aggregates IG reports. **Verify:** robots.txt/ToS and any bulk/API option.

### 8. GAO reports

- **Name:** U.S. Government Accountability Office reports
- **Tier:** 1 for what they assert about programs/data quality; used in practice as corroboration and design input (like OIG reports), not as transaction data.
- **URL / access point:** `https://www.gao.gov` (reports, searchable listings).
- **Access basis:** public.
- **License / terms summary:** GAO works are generally free to reproduce (verify GAO's copyright page — some contained images/material may be third-party).
- **Purpose in pipeline:** documented base rates and known failure modes (improper-payment estimates, DATA Act quality findings) → calibrates detector confidence and dashboard base-rate honesty (`DETECTION_PRINCIPLES.md` #7).
- **Fields provided:** report metadata + PDFs; unstructured.
- **Update cadence:** continuous.
- **Retrieval method:** manual/curated; verify whether a feed/API exists before automating.
- **Expected difficulty:** low (curated, low volume).
- **Known quality issues:** none unusual; recency — findings age.
- **Personal data present?** Rarely; officials in official capacity.
- **Confidence:** high the source exists. **Verify:** reuse terms page, any bulk endpoint.

### 9. CourtListener / RECAP (public court records)

- **Name:** CourtListener + RECAP archive (Free Law Project)
- **Tier:** 1 (court dockets are named Tier-1 in `DATA_SOURCE_POLICY.md`)
- **URL / access point:** `https://www.courtlistener.com` — REST API and bulk data; RECAP is its archive of PACER documents.
- **Access basis:** public / openly provided by Free Law Project (nonprofit). API key registration may be required for meaningful rate limits — free account, used as intended.
- **License / terms summary:** court records themselves are public domain; CourtListener's API/bulk terms should be read and excerpted into the registry entry. **Verify** current API-key requirements and quotas.
- **Rate limits / etiquette:** documented API throttles (verify numbers); use bulk data for volume.
- **PACER cost note:** RECAP only contains what someone has already purchased from PACER and shared. Gaps are systematic. Filling gaps means *paying PACER fees* (per-page fees, with a quarterly fee-waiver threshold — verify current pricing) under an operator-held PACER account. That is a lawful, budgeted, operator decision — record it as `operator-authorized` access basis if used.
- **Purpose in pipeline:** corroboration: procurement-fraud civil/criminal filings, False Claims Act qui tam cases (once unsealed), suspension/debarment-related litigation involving vendors already in our data. Docket existence is a *signal input with heavy caveats*, never more.
- **Fields provided:** docket metadata (court, case number, parties, dates), documents where archived.
- **Update cadence:** continuous, coverage-dependent.
- **Retrieval method:** API (targeted party-name queries), bulk for research.
- **Expected difficulty:** med (party-name matching to vendors is noisy; common names dominate FPs).
- **Known quality issues:** RECAP coverage is partial and skewed; party names are free text; a filed complaint is an allegation only — our language standard applies with full force ("named in filed litigation," never more).
- **Personal data present?** Yes, litigants. We query only organization names and individuals already present in official/registered capacities in our data; no general people-search.
- **Confidence:** high that CourtListener/RECAP and its API exist. **Verify:** API auth/quota, bulk-data terms, current PACER fee schedule.

### 10. State checkbook / procurement transparency portals (pilot: 2–3 states)

- **Name:** State expenditure portals — pilot candidates: **Ohio Checkbook** (`checkbook.ohio.gov`), **Open Book New York** (NY State Comptroller, `openbooknewyork.com`), **Texas Comptroller transparency data** (`comptroller.texas.gov` transparency section).
- **Tier:** 1 (official government payment records)
- **Access basis:** public.
- **License / terms summary:** each portal has its own terms — **must be read per portal and excerpted**; do not assume uniformity. Some offer explicit downloads (fine); some only interactive UIs (then: only documented export functions, no scraping around intended access paths).
- **Rate limits / etiquette:** per portal; only use published download/export/API mechanisms.
- **Purpose in pipeline:** payment-level data (`Payment` model) that federal sources lack — enables `duplicate_payment` and vendor-payment-pattern detectors at the state level; broadens beyond federal awards.
- **Fields provided (varies!):** payee name, amount, payment date, agency/fund, sometimes check/document number and expenditure category. **No UEI** — name/address resolution only.
- **Update cadence:** per portal (monthly/quarterly typical; verify each).
- **Retrieval method:** bulk download where offered; otherwise operator-mediated export.
- **Expected difficulty:** high in aggregate — **extreme heterogeneity** (schemas, granularity, redaction practices differ per state). Pilot 1 state end-to-end before generalizing.
- **Known quality issues:** payee name inconsistency worse than federal; some states redact certain payees (e.g., assistance recipients) — respect redactions absolutely; fiscal-year vs. calendar-year framing differs.
- **Personal data present?** State payments can include individuals (refunds, benefits) — those categories are **out of scope**; ingestion filters to vendor/procurement payments only. State it in the registry entry.
- **Confidence:** moderate-high that these three portals exist under roughly these names (all are long-standing, well-known transparency sites). **Verify per portal before any code:** exact URL, download availability, schema, terms, redaction policy. Confidence on any *specific* schema detail: low until checked.

### 11. USAspending reference data (NAICS, PSC, agency/toptier codes)

- **Name:** Federal reference/code tables (NAICS via Census, PSC via GSA, agency codes via USAspending/OMB)
- **Tier:** 1 (reference data, not evidence)
- **URL / access point:** USAspending API reference endpoints and download pages; Census (`census.gov`) for canonical NAICS; GSA for the PSC manual.
- **Access basis:** public.
- **License / terms summary:** U.S. government data.
- **Purpose in pipeline:** normalization backbone — `Agency.canonical_code`, industry/product classification for peer-group baselines ("this award is an outlier *within its NAICS/PSC peer group*"), which is how we keep base rates honest.
- **Fields provided:** code, title, hierarchy, effective years (NAICS revises on a 5-year cycle — 2017/2022 vintages matter for joins).
- **Update cadence:** slow (NAICS ~5-year revisions; PSC updated periodically; agency codes occasionally).
- **Retrieval method:** bulk download, versioned and committed as small reference files (these are tiny and public — candidate for `data/reference/` in-repo with provenance headers, operator's call).
- **Expected difficulty:** low.
- **Known quality issues:** vintage mismatches (a 2017 NAICS code joined against a 2022 table); PSC codes misassigned at entry in FPDS.
- **Personal data present?** No.
- **Confidence:** high. **Verify:** exact download endpoints for each table.

---

## Tier 2 — supporting (corroboration; weighted lower)

### 12. State corporate registries (Secretary of State business filings)

- **Name:** State SoS business-entity registries (per state)
- **Tier:** 2
- **URL / access point:** per state — heterogeneous. Some publish **bulk open data** (verifiable examples to check first: several states expose corporation datasets on their open-data portals); many offer only per-record search UIs; a few sell bulk extracts.
- **Access basis:** public where bulk/open data is offered; otherwise operator-mediated lookups. **No scraping of search UIs that prohibit it.**
- **License / terms summary:** per state — must be read individually. **OpenCorporates caveat:** OpenCorporates aggregates these registries and has an API, but its data is licensed (share-alike/attribution for open use; commercial/API use requires a paid license, and terms have changed over time — confidence: moderate; verify current licensing before ANY use). Prefer going to the primary state source; treat OpenCorporates as a licensing decision for the operator, not a default.
- **Purpose in pipeline:** corroboration for entity resolution and relationship edges — registered agents, officers/principals (registered capacity), formation dates, shared addresses across vendors. Feeds `PersonOfficer`, `RelationshipEdge` (e.g., `officer_of`, `shared_address`).
- **Fields provided (typical):** entity name, entity number, status, formation date, registered agent name/address, principal address, sometimes officers. Varies widely.
- **Update cadence:** per state; bulk files often monthly.
- **Retrieval method:** bulk download where lawfully offered; manual operator lookups otherwise.
- **Expected difficulty:** high (50+ schemas; start with the 1–2 states matching our state-checkbook pilot).
- **Known quality issues:** self-reported filings; agent addresses are often registered-agent companies serving thousands of entities (the single biggest FP mode for shared-address signals — must be baselined, see `DETECTION_PRINCIPLES.md` #4); stale statuses.
- **Personal data present?** Officers/agents by name and address — registered capacity, within policy; commercial-registered-agent addresses are business addresses.
- **Confidence:** high that registries exist per state; low-moderate on which specific states offer lawful bulk access — **verify state-by-state before selection.**

### 13. DOJ press releases (and USAO district releases)

- **Name:** U.S. Department of Justice press releases (procurement-fraud, FCA settlements, charges/convictions)
- **Tier:** 2 (official press release — explicitly Tier 2 in policy)
- **URL / access point:** `https://www.justice.gov/news` and USAO district news pages.
- **Access basis:** public.
- **License / terms summary:** U.S. government works; verify site terms; check robots.txt before any automated retrieval — default to curated manual capture.
- **Purpose in pipeline:** corroboration and retro-validation: settled/adjudicated matters let us test detectors against known outcomes; a DOJ settlement naming a vendor is strong corroboration on a lead. Careful language: a press release about *charges* is an allegation; only *settlements/convictions* are outcomes — and even then our outputs still say "publicly reported settlement," never our own characterization.
- **Fields provided:** unstructured text + date + component.
- **Update cadence:** continuous.
- **Retrieval method:** manual/curated initially (operator saves pages as evidence uploads); automation only after ToS/robots verification.
- **Expected difficulty:** med (entity extraction from prose).
- **Known quality issues:** press releases are selective (survivorship bias — don't calibrate base rates from them); entity names in prose need careful resolution.
- **Personal data present?** Named defendants — we link only to entities/officials already in our data via official records; no person-centric ingestion.
- **Confidence:** high. **Verify:** robots.txt/terms for any automation; existence of any structured feed (unknown).

### 14. Federal Register

- **Name:** Federal Register (rules, notices, agency actions)
- **Tier:** 2
- **URL / access point:** `https://www.federalregister.gov`; it has a public developer API (confidence: high that an API exists; verify current endpoints/terms).
- **Access basis:** public; U.S. government work.
- **Purpose in pipeline:** context that changes detector interpretation: suspension/debarment-related notices, program rule changes, threshold changes (e.g., micro-purchase/simplified acquisition thresholds move — detectors keyed to dollar thresholds must version against the era's threshold, not today's).
- **Fields provided:** document metadata, agency, type, full text, publication date.
- **Update cadence:** each federal business day.
- **Retrieval method:** API, filtered queries only (we need slivers, not the corpus).
- **Expected difficulty:** low.
- **Known quality issues:** none unusual; the work is knowing what to query.
- **Personal data present?** Rarely; officials in official capacity.
- **Confidence:** high. **Verify:** API base URL, query parameters, terms.

### 15. FOIA.gov + published agency FOIA logs

- **Name:** FOIA.gov (request planning/filing) + agency FOIA reading rooms and FOIA logs
- **Tier:** 2 (logs/reading-room docs support and contextualize; documents obtained via FOIA become Tier-1 agency records once received, registered individually)
- **URL / access point:** `https://www.foia.gov`; per-agency electronic reading rooms and posted FOIA logs.
- **Access basis:** public; FOIA requesting is the lawful public-records process explicitly permitted in `LEGAL_AND_ETHICAL_BOUNDARIES.md`.
- **Purpose in pipeline:** (a) *FOIA planning* — when a detector needs a record type no open source provides (e.g., agency purchase-card transaction detail), the pipeline output is a **drafted FOIA request for the operator to review and file**, not a workaround; (b) FOIA logs show what others have requested — useful for finding already-released datasets ("frequently requested records") before filing anything new.
- **Fields provided:** logs vary wildly (requester (often redacted), subject, date, disposition); reading-room docs are arbitrary records.
- **Update cadence:** per agency, irregular.
- **Retrieval method:** manual/curated; FOIA.gov API for agency contact/statistics data may exist (confidence: low-moderate — verify before relying on it).
- **Expected difficulty:** med (unstructured, per-agency).
- **Known quality issues:** logs are inconsistent and often incomplete; long response latencies make FOIA a background channel, never a pipeline dependency.
- **Personal data present?** Requester names sometimes appear in logs — we do not ingest or use requester identities.
- **Confidence:** high that FOIA.gov and reading rooms exist; low on any specific machine-readable interface. **Verify** per agency.

### 16. Grants.gov (opportunities) — supporting note

- **Name:** Grants.gov funding-opportunity data
- **Tier:** 2 for our purposes (opportunities are pre-award context; actual grant *awards* come from USAspending — entry #1 — which is the Tier-1 path named in this blueprint's scope)
- **URL / access point:** `https://www.grants.gov`; a periodic XML extract of opportunities has historically been published (confidence: moderate — verify current extract/API availability).
- **Access basis:** public.
- **Purpose in pipeline:** context for grant-side signals: match awards to their originating opportunity (eligibility, competition type); "award without discoverable opportunity" is a weak context flag, never standalone.
- **Fields provided:** opportunity number, CFDA/Assistance Listing, agency, open/close dates, eligibility.
- **Update cadence:** daily-ish extract (verify).
- **Retrieval method:** bulk download.
- **Expected difficulty:** low-med (XML).
- **Known quality issues:** opportunity↔award linkage is imperfect; Assistance Listing numbering changed over time (CFDA → Assistance Listings — verify mapping).
- **Personal data present?** Agency contacts, official capacity.
- **Confidence:** moderate. **Verify:** current extract location/format before scheduling any work.

---

## Tier 3 — contextual (never the basis of a signal on its own)

No Tier-3 sources are proposed for the first 90 days. When added (news coverage,
academic research on procurement risk), they enter the registry with the same
template and the policy's hard rule: context only.

---

## Priority ranking — first 90 days

Matches `ROADMAP.md` Phase 1–2 needs. Order = build order.

| Rank | Source | Why now | Difficulty |
|---|---|---|---|
| 1 | **SAM.gov Exclusions extract** (#2) | ROADMAP Phase-1 Tier-1 starter; small, daily, directly powers `debarred_vendor_match` | low |
| 2 | **USAspending awards — API + bulk** (#1) | ROADMAP Phase-1 Tier-1 starter; the transaction universe everything else joins to | med |
| 3 | **USAspending reference data** (#11) | Cheap; required for normalization and base-rate peer groups before detectors run | low |
| 4 | **FPDS detail via USAspending** (#4) | Same ingest path as #2; unlocks competition-pattern detectors | low (via #2) |
| 5 | **SAM.gov entity registrations (public extract)** (#3) | Vendor master + entity resolution quality; needed before fuzzy matching goes live | med |
| 6 | **Subaward data via USAspending** (#5) | Extends #2 with pass-through visibility | low-med |
| 7 | **One state checkbook pilot** (#10 — pick ONE, verify terms first) | Payment-level data for `duplicate_payment`; proves the state-heterogeneity playbook | high |
| 8 | **OIG reports / oversight.gov, curated** (#7) | Manual corroboration workflow; near-zero engineering | low |
| 9 | **CourtListener API, targeted lookups** (#9) | Corroboration on existing leads only; not a crawl | med |

Deferred past 90 days: state corporate registries (#12 — pick states after the
checkbook pilot chooses a state), SBA datasets (#6 — needs the individuals-
handling sign-off noted in its entry), DOJ releases (#13), Federal Register
(#14), FOIA logs (#15), Grants.gov opportunities (#16), GAO curation (#8 —
opportunistic, not scheduled).

**Recommended first two registry entries to complete and get operator-approved
(per ROADMAP Phase 1): SAM.gov Exclusions + USAspending award data.**

---

## DO-NOT-INGEST list

Hard exclusions under `LEGAL_AND_ETHICAL_BOUNDARIES.md` and
`DATA_SOURCE_POLICY.md`. If a future goal seems to need one of these, stop and
ask the operator; the answer is a FOIA draft or "no," not a workaround.

1. **Anything behind authentication we don't hold proper authorization for** —
   including SAM.gov restricted/FOUO entity fields, non-public agency systems,
   grantee portals, contractor extranets. A free public-account signup used as
   the system intends (SAM data services, CourtListener API key) is acceptable
   *only* when the operator creates and holds the account and the registry
   entry records it.
2. **ToS-prohibited or robots-excluded scraping** — no scraping of any portal
   whose terms or robots.txt disallow it, no CAPTCHA circumvention, no
   rate-limit evasion, no rotating identities to look like different users.
   If a state portal offers only a search UI with prohibitive terms: skip the
   state or file a public-records request.
3. **Aggregated personal data / people-search services** — data brokers,
   people-finder sites, social media profiles, voter files, property records
   used to profile individuals, leaked or breached datasets (regardless of how
   public they've become). Individuals exist in this system only as
   officers/agents/COs of record in official documents.
4. **PACER via shared/borrowed credentials** — PACER only through an
   operator-held account with budget sign-off; RECAP first.
5. **OpenCorporates (or similar aggregators) without a verified, current
   license** covering our use — primary state sources preferred.
6. **Paywalled news/research content** beyond lawful subscription terms;
   Tier-3 anyway and never signal-bearing.
7. **State-portal categories containing benefit/assistance payments to
   individuals** — filtered out at ingestion even when technically public
   (entry #10).
8. **Any dataset whose license we haven't read.** No registry entry with the
   license line blank gets ingestion code, full stop (policy admission
   criterion #2/#4).
