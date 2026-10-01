# Assignment requirements and acceptance evidence

Page citations refer to originals/Assignment_MR_Housing_final_v2.pdf, counted1-4. Section/paragraph descriptions identify the actual text; no fabricated paragraph numbering is used.

| ID | Assignment location and requirement | Handoff design | Evidence required from implementation |
|---|---|---|---|
|R01|p.1heading: dueOct16,2026; teams2|Deadline/team recorded, no inferred hour|two author names in report; submission metadata|
|R02|p.1§1first paragraph: residential Dallas listings, user criteria, past12 months, nice interactive UI|Dallas synthetic observations,12-month query, Explore controls/charts|working UI screenshots, API request/output and browser smoke test|
|R03|p.1§11.29 second paragraph(a): downstream feedback upstream|Reviewer→Orchestrator C1|actual live JSONL trace with causal parent and revised plan|
|R04|same paragraph(b): conditional stop/iterate signal|sparse/completeness signals; bounded review decisions|actual decisions, budgets and stop tests|
|R05|same paragraph(c): genuine action-changing dependency|indexed→full_csv and Region activation|before/after plan, executed tool path and role-set assertions|
|R06|same paragraph: design note within first10days, graph/cycles/rationale; final actual loop trace|three architecture pages preserved; updated diagrams specified|design-note/history artifact if available; final cycle graph and live trace; do not falsely claim past submission|
|R07|p.1Data source paragraph: accessible source, frozen local snapshot|fully documented24-month generator|committed CSV, manifest, generator/config/seed/hash and regeneration log|
|R08|p.1§2Required paragraph: ≥8MRs, all 3 families, relation/subdomain/tolerance/fault|10formalMRs, canonical output contract first|catalog/version, code/comparator mapping and preflight witnesses|
|R09|same paragraph: exact12-month output contract before MRs|SPEC§4, schemas and mathfixtures|typed contracts and unit tests; report metric definitions|
|R10|p.1Statistical checking and p.2opening: ≥30 distinct base inputs/MR; k≥3 fixed seeds; rates95% CIs|30 eligible bases*3 paired seeds/MR, base-any-seed Wilson|cohort/seed manifests,900case outcomes,10-row table, denominator/CI checks|
|R11|p.2Diagnosing violations: three most violated, classify cause with evidence|ranking and RCA protocol, truthful zero-failure fallback|actual trace/row/diff/minimal repro per diagnosis; no fabricated failure|
|R12|p.2§3bullets: design note, working app+catalog, executed harness, half-page reflection|full build gates; report template|actual application/results/report, reflection and AI_USE|
|R13|p.2§3final paragraph:10-12 page report, system/source/MRs/results+CIs/RCA/threats|12-page allocation including refs|rendered finalPDF/page-count+visualQA|
|R14|same paragraph: gitrepo+code+snapshot+NOTEBOOK.md+AI_USE.md+one-command headline reproduction|Make targets, frozen capture/data, notebook/disclosure templates|clean-checkout setup then disconnected make reproduce, saved output/hashes|
|R15|p.2§4: disclose substantiveLLMuse/errors; live-only irreproducible gets zero rigor; MR hypothesis; public/exported/syntheticdata only|strict evidence/versioning; local synthetic data; no paid/private source|AI_USE errors/corrections, frozen evidence, reproducibility and revisedMR history|
|R16|p.3Frameworks/getting-started: local model allowed, small deterministic agents, freezefirst, oneMRend-to-end first|Fast Agent choice retained, seedprobe, MR01pilot|probe/locks/modeldigest, pilot then fullcampaign|
|R17|p.3dataset table and synthetic paragraph: real listings or generator; cite source|generator is the actual source, no falseKaggle claim|generation provenance and explicit synthetic limitations|
|R18|p.4Indian metro optional, same protocol; single-point data caveat; document assumptions|Dallas retained,24true generated monthly partitions, DECISIONS|assumptions in report; no rebranded single-date data|

The early design-note source requirement includes architecture+data source+8MR sketches. The handed-in diagrams are preserved, but their existence alone does not prove that note was submitted on time. The final project should retain whatever actual design-note/submission history exists and update it to match the implemented contract.
