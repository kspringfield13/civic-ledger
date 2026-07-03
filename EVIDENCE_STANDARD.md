# Evidence Standard

## Every RiskSignal must carry
- `detector_id` + `detector_version`
- one or more `EvidenceItem`s, each with:
  - source document reference (`SourceDocument.id`)
  - original source locator (URL, document ID, or file hash for uploads)
  - retrieval timestamp and method
  - the specific fields/values relied on (quoted, not paraphrased)
- computed `severity` and `confidence` with the inputs that produced them
- the false-positive modes inherited from the detector spec

## Chain of custody
- Raw source bytes are hashed (SHA-256) at ingestion; the hash is stored on
  `SourceDocument` so later exports can prove the record wasn't altered.
- Normalization never destroys the raw pointer; transformations are recorded
  in `services/normalization.py` output metadata.

## Case packets
When a reviewer escalates a lead, `docs/case-packet-template.md` produces a
packet containing: the hypothesis, all evidence items with locators, the
innocent explanations considered, reviewer notes, and explicit uncertainty
language. Packets never contain conclusory fraud language.

## Language standard
Approved: "pattern consistent with…", "warrants review", "matches exclusion
record", "risk signal". Prohibited: "fraudulent", "criminal", "guilty",
"committed", or any assertion of intent.
