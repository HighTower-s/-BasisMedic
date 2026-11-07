# Feature Specification: Runbook Corpus, Labelled Eval Set, and Measured Retrieval

**Feature Branch**: `001-runbook-retrieval-eval`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Feature 1 of 3 for BasisMedic: the runbook knowledge base, the labelled evaluation set, and measured retrieval."

## User Scenarios & Testing *(mandatory)*

The actor throughout is **the author** — the student building BasisMedic. A secondary consumer is the
triage assistant built in Feature 2, which depends on this feature's search behaviour but is not part
of it.

Note on priorities: the author's own prioritisation listed five slices. User Story 1 below (the corpus
and its index) is the enabling slice that all of those assume — it is therefore also P1, and is stated
explicitly rather than left implicit.

### User Story 1 - Trustworthy runbook corpus and rebuildable index (Priority: P1)

As the author, I maintain a small, uniformly structured corpus of SAP Basis runbooks plus an
accompanying list of allowed transaction codes, and I can turn that corpus into a searchable index with
one command that always rebuilds from scratch.

**Why this priority**: Nothing else in the feature exists without it. Every search result, every
citation, and every eval label points at a runbook section, so the corpus is the unit of truth that
makes measurement meaningful.

**Independent Test**: Can be fully tested without any search or eval logic — validate that every
runbook carries the required metadata and exactly the six required sections, that every transaction
code named anywhere in the corpus exists in the allow-list, and that running the build command twice
produces an index with identical content and no leftover artifacts from the previous build.

**Acceptance Scenarios**:

1. **Given** the corpus directory with 16 runbooks, **When** the corpus is validated, **Then** each
   runbook has a unique id, exactly one of the 8 categories, an ordered list of transaction codes, an
   escalation target, at least one reference URL, and exactly the sections Symptoms, Cause, Check, Fix,
   Escalate, References — in that order.
2. **Given** a runbook that names a transaction code absent from the allow-list, **When** the corpus is
   validated, **Then** validation fails and names the offending runbook and code.
3. **Given** an index built from the corpus, **When** a runbook is edited and the build command is run
   again, **Then** the index reflects only the current corpus, with no entries surviving from the
   previous build.
4. **Given** the corpus, **When** the index is inspected, **Then** every searchable unit is traceable to
   exactly one `runbook-id#section` address that resolves to real text in the corpus.

---

### User Story 2 - One command reports retrieval quality on the test set (Priority: P1)

As the author, I run a single command and see recall@3 and MRR for the current search configuration on
the labelled test set, together with the out-of-scope rejection rate and the false-refusal rate, written
to files alongside the exact configuration that produced them.

**Why this priority**: Measurement must exist before the thing being measured is tuned, otherwise no
later design choice can be justified. This story is deliberately runnable against a trivial keyword-only
search, so it can be completed and demonstrated before any meaning-based retrieval exists.

**Independent Test**: Can be fully tested with a deliberately naive keyword-only search and no access to
the external gateway — the command still produces a complete, schema-valid results file with all four
metrics and a per-case breakdown. The numbers may be poor; the harness is what is being tested.

**Acceptance Scenarios**:

1. **Given** the labelled test set and any working search configuration, **When** the eval command is
   run, **Then** it reports recall@3 and MRR over the in-scope cases, out-of-scope rejection rate over
   the out-of-scope cases, and false-refusal rate over the in-scope cases.
2. **Given** a completed eval run, **When** the results file is opened, **Then** it records the full
   configuration used (chunking strategy, retrieval mode, result count, relevance floor, corpus version)
   next to the numbers.
3. **Given** a completed eval run, **When** the same command is run again with no changes, **Then** the
   retrieval metrics are identical.
4. **Given** the eval command, **When** it is run with the external gateway unreachable and a
   keyword-only configuration selected, **Then** it completes successfully.
5. **Given** an eval case whose expected runbook id does not exist in the corpus, **When** the eval
   command is run, **Then** it fails loudly naming that case, rather than silently scoring it as a miss.

---

### User Story 3 - Search a log and get cited sections, or a clear "nothing relevant" (Priority: P1)

As the author, I paste an error log (or type any query) and get back the 3 most relevant runbook
sections — each with its runbook id, section name, text, and relevance score — or an explicit statement
that nothing in the corpus is relevant enough.

**Why this priority**: This is the capability the whole feature delivers and the contract Feature 2 will
build on. Refusing to answer is as important as answering: a confident wrong transaction code is the
worst possible output for someone on call at 2am.

**Independent Test**: Can be fully tested by pasting known logs and confirming the expected runbook
sections come back with resolvable addresses, and by pasting a log from a domain the corpus does not
cover (for example a HANA log-volume-full alert) and confirming zero results plus a clear reason.

**Acceptance Scenarios**:

1. **Given** an indexed corpus, **When** a log containing the text `TSV_TNEW_PAGE_ALLOC_FAILED` is
   searched, **Then** at most 3 results are returned, each carrying a runbook id, a section name, the
   section text, and a relevance score, ordered best first.
2. **Given** an indexed corpus, **When** a HANA log-volume-full alert is searched, **Then** zero results
   are returned together with an explicit "nothing relevant" indication — not a weak best guess.
3. **Given** a configured relevance floor, **When** the floor is raised, **Then** strictly fewer or equal
   results pass it for the same query, and the behaviour change requires no change to the corpus or index.
4. **Given** a returned result, **When** its address is looked up in the corpus, **Then** the address
   resolves to the exact section text that was returned.
5. **Given** a query shorter than the minimum length or consisting only of whitespace, **When** it is
   searched, **Then** it is rejected with a clear message and no results.
6. **Given** a corpus where several sections of the same runbook all match a query, **When** it is
   searched, **Then** the returned results cover distinct runbooks rather than being filled by one
   runbook, so that 3 results mean 3 candidate answers.

---

### User Story 4 - Compare chunking and retrieval strategies by number (Priority: P2)

As the author, I compare competing strategies one variable at a time against named baselines and see,
in a table, which is better and by how much.

**Why this priority**: The project's claim is that section-aligned chunking and combined retrieval help.
Without a one-variable-at-a-time comparison that claim is an opinion. It is P2 because the harness
(US2) must exist and be trusted first.

**Independent Test**: Can be fully tested by running the comparison and checking that each row differs
from its baseline in exactly one named variable, that all rows were measured on the same case set, and
that the output table names the winner by number.

**Acceptance Scenarios**:

1. **Given** the eval harness, **When** the chunking comparison is run, **Then** a table reports
   naive fixed-size chunks versus section-aligned chunks with every other setting held constant, and the
   varied setting is named in the output.
2. **Given** the best chunking strategy from the previous comparison, **When** the retrieval comparison
   is run, **Then** a table reports keyword-only, meaning-based, and combined retrieval with every other
   setting held constant.
3. **Given** a completed comparison, **When** the report is read, **Then** each row states the baseline
   it is compared against and the before/after difference for each metric.
4. **Given** a comparison where the combined strategy does not beat both baselines, **When** the report
   is written, **Then** it states that plainly rather than omitting the row or reframing the metric.

---

### User Story 5 - Tune the relevance floor on dev cases and see the trade-off (Priority: P2)

As the author, I sweep the relevance floor across a range using only the dev cases, and see the
trade-off between correctly rejecting out-of-scope logs and wrongly rejecting in-scope ones, so I can
choose a floor for a defensible reason.

**Why this priority**: The floor is the single setting that decides when the system refuses to answer.
Choosing it by feel would undermine the refusal behaviour that US3 promises. It is P2 because it
presupposes both the harness and a search worth tuning.

**Independent Test**: Can be fully tested on the dev cases alone — run the sweep, confirm one row per
floor value with both rates, and confirm the test cases were never read during the sweep.

**Acceptance Scenarios**:

1. **Given** the dev cases, **When** the floor sweep is run, **Then** it reports, for each floor value in
   the swept range, the in-scope recall@3 and the out-of-scope rejection rate on the dev cases.
2. **Given** a completed sweep, **When** the chosen floor is recorded, **Then** the record names the
   sweep run it came from.
3. **Given** the floor sweep, **When** it is run, **Then** no test case is loaded or scored by it.
4. **Given** a chosen floor, **When** the test set is later evaluated, **Then** the floor value used is
   the one chosen from the dev sweep and is reported unchanged alongside the test numbers.

---

### User Story 6 - Read a failures list explaining each wrong result (Priority: P3)

As a reader of the report (course assessor, or the author six weeks later), I can open a failures list
and see every case the system got wrong, what was expected, what was actually retrieved, and what kind
of failure it was.

**Why this priority**: It converts bad numbers into understanding and is what makes the honesty claim
checkable. P3 because the metrics must be trustworthy before their failures are worth cataloguing.

**Independent Test**: Can be fully tested by forcing a known failure (for example a deliberately high
floor) and confirming the affected cases appear in the failures list with the expected-versus-retrieved
detail and a failure type.

**Acceptance Scenarios**:

1. **Given** an eval run with at least one wrong result, **When** the failures list is opened, **Then**
   every wrong case appears exactly once with its id, expected category and runbook(s), the results
   actually retrieved in order, and a failure type.
2. **Given** an eval run with no wrong results, **When** the failures list is opened, **Then** it exists
   and is empty rather than absent.
3. **Given** the failures list, **When** it is compared against the metrics file, **Then** the count of
   failing cases is consistent with the reported metrics.

---

### Edge Cases

- **Out-of-scope log that looks in-scope**: a dump-formatted log whose runtime error has no runbook (for
  example a duplicate-key error) shares its layout and much of its vocabulary with covered dumps. It must
  still be rejected, so the floor cannot rely on log formatting alone.
- **Mixed log, two problems**: a job log showing both a cancelled job and a locked step user has two
  expected runbooks. Partial credit must be scored correctly rather than counted as a total miss.
- **Thai-language log**: a paraphrased complaint written in Thai against an English corpus. Whether
  cross-language matching works is an open measurement, and a poor result here is reported, not hidden.
- **Query with no distinctive tokens**: a log reduced to timestamps and client numbers should fall below
  the floor rather than returning an arbitrary nearest section.
- **Very long log**: a full dump pasted at the maximum accepted length must still be searchable.
- **Stale index**: the corpus is edited but the index is not rebuilt. Searching must not silently return
  text that no longer exists in the corpus.
- **Empty or whitespace-only query**: rejected before any search is attempted.
- **Duplicate or near-duplicate runbooks**: two runbooks in the same category describing adjacent
  symptoms can both legitimately match. The case labels distinguish "must find" from "acceptable", so
  such a result is not scored as an error.
- **Acceptable-but-not-expected result**: a result listed as an acceptable alternative must neither earn
  recall credit nor be recorded as a failure.
- **Gateway unavailable**: meaning-based retrieval cannot run. Keyword-only configurations must remain
  fully usable, and the failure must be reported clearly rather than producing silently empty results.

## Requirements *(mandatory)*

### Functional Requirements

**Corpus and transaction-code list**

- **FR-001**: The corpus MUST contain 16 runbooks: 2 for each of the 8 incident categories — memory dump,
  timeout, job failure, lock issue, update error, transport error, user/authorization, and RFC error.
- **FR-002**: Every runbook MUST carry a unique identifier, exactly one category, a title, an ordered
  list of transaction codes to open, an escalation target, and at least one reference URL.
- **FR-003**: Every runbook MUST contain exactly the sections Symptoms, Cause, Check, Fix, Escalate, and
  References, in that order, with no sections added or omitted.
- **FR-004**: The Check section of every runbook MUST present transaction codes in the order they should
  be opened.
- **FR-005**: Runbook prose MUST be written in the author's own words in English, summarising publicly
  available SAP documentation, with source URLs listed in the References section. Verbatim passages from
  SAP documentation or SAP Notes MUST NOT appear.
- **FR-006**: An allow-list of permitted transaction codes MUST accompany the corpus, each entry carrying
  the code and a one-line description of what it is for.
- **FR-007**: Corpus validation MUST fail, naming the offending runbook and value, if any runbook
  violates FR-002 through FR-004, or names a transaction code absent from the allow-list.

**Index**

- **FR-008**: A single command MUST build a searchable index from the corpus.
- **FR-009**: The build MUST discard any previous index before writing, so that no content from a removed
  or edited runbook survives a rebuild.
- **FR-010**: Every searchable unit in the index MUST be addressable as `runbook-id#section`, and that
  address MUST resolve to a real section of a real runbook in the corpus.
- **FR-011**: The system MUST support two chunking strategies so they can be compared: naive fixed-size
  text chunks, and chunks aligned to runbook sections.
- **FR-012**: The build MUST report what it produced — number of runbooks read and number of searchable
  units written — so an incomplete build is visible rather than silent.

**Search**

- **FR-013**: Users MUST be able to submit an error log or free-text query and receive at most 3 results.
- **FR-014**: Each result MUST carry its runbook id, section name, section text, relevance score, and
  rank.
- **FR-015**: Results MUST be ordered by relevance, best first, and MUST cover distinct runbooks rather
  than multiple sections of the same runbook.
- **FR-016**: The system MUST support three retrieval modes so they can be compared: keyword-only,
  meaning-based, and combined.
- **FR-017**: The keyword-only mode MUST work without any access to the external gateway.
- **FR-018**: A configurable relevance floor MUST gate all results. When nothing clears the floor, the
  system MUST return zero results together with an explicit "nothing relevant" indication, and MUST NOT
  substitute a weaker best guess.
- **FR-019**: Queries that are empty, whitespace-only, or shorter than the minimum accepted length MUST
  be rejected with a clear message before any search is performed.
- **FR-020**: Search MUST reject or clearly flag a query made against an index that is older than the
  corpus it was built from.

**Labelled evaluation set**

- **FR-021**: The evaluation set MUST be authored and committed before any retrieval or search logic is
  written.
- **FR-022**: The evaluation set MUST contain exactly 10 dev cases and 30 test cases, in separate
  collections that cannot be loaded accidentally in place of one another.
- **FR-023**: The 30 test cases MUST comprise 24 in-scope cases — 3 per category, one each at easy
  (exact error code present), medium (a different log format such as a job log, system log, or transport
  log), and hard (no exact code; a paraphrased user complaint) difficulty — plus 4 out-of-scope cases and
  2 mixed cases that contain two problems in one log.
- **FR-024**: 3 of the hard test cases MUST be written in Thai.
- **FR-025**: Every one of the 16 runbooks MUST be the expected answer of at least one test case.
- **FR-026**: Each case MUST record: a unique id, its split, its log text, the log format, the difficulty
  tier, the expected category, the expected runbook(s), any acceptable alternative runbook(s), and the
  expected transaction codes.
- **FR-027**: Out-of-scope cases MUST record an out-of-scope category with no expected runbooks and no
  expected transaction codes.
- **FR-028**: Every case log MUST be marked as synthetic, and the corpus-wide report MUST state that all
  logs are synthetic.
- **FR-029**: Case log text MUST NOT be copied from runbook text, so that keyword matching is not
  flattered by shared phrasing.
- **FR-030**: Evaluation-set validation MUST fail, naming the offending case, if any case violates
  FR-026 or FR-027, or names a runbook id absent from the corpus.

**Evaluation and reporting**

- **FR-031**: A single command MUST produce every reported number.
- **FR-032**: The evaluation MUST report recall@3 and MRR over in-scope cases, the out-of-scope rejection
  rate over out-of-scope cases, and the false-refusal rate over in-scope cases.
- **FR-033**: Recall@3 and MRR MUST be computed at runbook level, collapsing multiple sections of the
  same runbook to a single candidate before ranking.
- **FR-034**: Expected runbooks MUST count towards recall; acceptable alternatives MUST NOT count towards
  recall and MUST NOT be recorded as failures.
- **FR-035**: Every results file MUST record the configuration that produced it: chunking strategy,
  retrieval mode, number of results, relevance floor, and the corpus version measured.
- **FR-036**: Two consecutive evaluation runs with unchanged inputs and configuration MUST produce
  identical retrieval metrics.
- **FR-037**: The system MUST support comparing configurations that differ in exactly one named variable,
  and the comparison output MUST name that variable and the baseline for each row.
- **FR-038**: The named baselines MUST include keyword-only retrieval and meaning-based retrieval over
  naive fixed-size chunks, and all compared rows MUST be measured on the same case set.
- **FR-039**: The relevance floor sweep MUST read only dev cases, and MUST report in-scope recall and
  out-of-scope rejection rate for each floor value swept.
- **FR-040**: The chosen relevance floor MUST be recorded together with the dev sweep run it came from,
  and MUST be reported unchanged alongside test-set numbers.
- **FR-041**: Test cases MUST be used for reporting only. No tuning command may read them, and no
  configuration value may be selected from test-set results.
- **FR-042**: Every failing case MUST be written to a failures list recording its id, expected category
  and runbook(s), the results actually retrieved in order, and a failure type.
- **FR-043**: The failures list MUST exist even when empty.
- **FR-044**: The report MUST state the comparison outcome honestly, including when the combined strategy
  does not beat its baselines, and MUST state the corpus's known limitations.

### Key Entities

- **Runbook**: one incident playbook. Identified by a stable id; carries a category, title, ordered
  transaction codes, escalation target, and reference URLs; composed of the six fixed sections. The unit
  that eval labels and recall are counted against.
- **Runbook Section**: one of the six named parts of a runbook. Addressed as `runbook-id#section`. The
  citable unit — what search returns and what Feature 2 will cite.
- **Transaction Code Entry**: a permitted SAP transaction code and a one-line description of its purpose.
  Collectively the allow-list that bounds what the corpus — and later the assistant — may name.
- **Index**: the searchable form of the corpus, derived and disposable, rebuilt wholesale from the corpus.
  Holds searchable units, each traceable to one runbook section address.
- **Searchable Unit (Chunk)**: a passage of corpus text produced by the active chunking strategy, carrying
  its runbook id and section address. Under section-aligned chunking one unit equals one section; under
  naive chunking a unit may span or split sections.
- **Search Result**: a returned match — runbook id, section name, section text, relevance score, rank.
- **Evaluation Case**: one labelled incident. Carries id, split, synthetic log text, log format,
  difficulty tier, expected category, expected runbook(s), acceptable alternative runbook(s), and expected
  transaction codes. Belongs to exactly one split.
- **Evaluation Set**: the dev collection (10 cases, for tuning) and the test collection (30 cases, for
  reporting only) — deliberately separate, because the separation is what keeps reported numbers honest.
- **Evaluation Run Result**: the metrics from one evaluation, inseparable from the configuration that
  produced it and the corpus version measured.
- **Comparison**: two or more evaluation runs differing in exactly one named variable, plus the named
  baseline each is measured against.
- **Failure Record**: one wrong case — what was expected, what was retrieved, and what kind of failure it
  was.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The evaluation set contains exactly 10 dev and 30 test cases, the test split matches the
  required distribution (24 in-scope as 3 per category across the three difficulty tiers, 4 out-of-scope,
  2 mixed) including 3 Thai hard cases, and 100% of cases pass schema validation.
- **SC-002**: 100% of the 16 runbooks are the expected answer of at least one test case; zero runbooks are
  never exercised.
- **SC-003**: Zero case logs share a contiguous eight-word span with any runbook section text.
- **SC-004**: One documented command reproduces every number that appears in the report, and running it
  twice in a row yields identical retrieval metrics.
- **SC-005**: 100% of search results carry a `runbook-id#section` address that resolves to existing
  corpus text; zero dangling addresses across a full pass over both splits.
- **SC-006**: 100% of transaction codes named anywhere in the corpus appear in the allow-list.
- **SC-007**: Rebuilding the index twice from the same corpus produces identical index content, and
  rebuilding after deleting a runbook leaves zero traces of it.
- **SC-008**: Every out-of-scope test case that is correctly handled returns exactly zero results; no
  out-of-scope case is answered with a partial or low-confidence result.
- **SC-009**: The relevance floor used for test-set reporting is traceable to a dev-set sweep run, and
  both the out-of-scope rejection rate and the false-refusal rate are reported for it. No configuration
  value in any committed results file was selected from test-set numbers.
- **SC-010**: The comparison table contains a row for the combined strategy and a row for each of the two
  named baselines, measured on the same case set, each differing from its baseline in exactly one named
  variable.
- **SC-011**: 100% of failing test cases appear in the failures list with expected-versus-retrieved detail
  and a failure type.
- **SC-012**: The evaluation command completes successfully in a keyword-only configuration with no
  network access, so retrieval quality can be measured before any gateway dependency exists.
- **SC-013**: A single search over the full corpus returns within 3 seconds on the author's development
  machine, so the author can iterate interactively.
- **SC-014**: The report states, in writing, that all logs are synthetic and lists the corpus's known
  limitations, and states the combined strategy's comparison outcome whether or not it wins.

## Out of Scope

These are explicitly excluded from this feature and belong to later features or to no feature at all:

- Language-model-generated answers of any kind.
- The triage assistant, its agent loop, and its tools.
- Structured triage output (category, ordered transaction codes, steps, escalation target) as a validated
  response object.
- Any HTTP API, streaming interface, or web UI.
- Multi-turn conversation or follow-up questions.
- Connecting to real SAP systems, reading live system data, or executing any fix.
- End-to-end metrics that depend on a language model (category accuracy, transaction-code recall,
  hallucination rate, valid-output rate), and their baselines.

## Assumptions

Resolved from the author's reference notes in `docs/prepare/` or from reasonable defaults where the
feature description left a detail open:

- **Corpus scale**: 16 runbooks at six sections each gives roughly 100 searchable units under
  section-aligned chunking. All retrieval behaviour and the 3-second interactive target assume this scale.
  Sixteen runbooks rather than eight is deliberate: with only eight documents, recall@3 would be high by
  luck and the metric would carry little information.
- **Dev split composition**: the feature description fixes the test split's distribution but not the dev
  split's. Taken from `docs/prepare/09_eval_plan.md`: 8 in-scope cases, one per category, plus 2
  out-of-scope cases.
- **Thai case count**: the description says 2–3 Thai cases; 3 is specified here, placed in the hard tier,
  because the hard tier is where paraphrased complaints live and because a fixed count makes SC-001
  checkable.
- **Mixed cases count as in-scope**: the 2 mixed test cases carry expected runbooks and are therefore
  scored within the in-scope population, giving 26 in-scope test cases for recall@3, MRR, and
  false-refusal rate; the 4 out-of-scope cases are scored separately.
- **Recall is counted at runbook level**: multiple returned sections of the same runbook collapse to one
  candidate before ranking, matching the course reference approach, so that "3 results" means three
  distinct candidate answers.
- **Expected versus acceptable**: expected runbooks drive recall; acceptable alternatives are recorded so
  that a defensible near-miss is neither rewarded as a hit nor punished as a failure.
- **No numeric quality target is asserted**: this specification requires that recall@3, MRR,
  out-of-scope rejection, and false-refusal rates be measured, reported with their configuration, and
  compared against named baselines. It deliberately sets no threshold any of them must reach, because
  committing to a number before the first measurement would create pressure to report a flattering one.
  The honesty requirement (FR-044, SC-014) replaces a target.
- **Cross-language retrieval is an open question**: whether Thai queries match English runbooks is
  something this feature measures, not something it guarantees. A poor Thai result is a reported finding.
- **Reproducibility of meaning-based retrieval**: identical metrics across repeated runs (SC-004,
  FR-036) assume that the derived representations of a fixed corpus are stable and reusable across runs
  rather than recomputed differently each time.
- **External dependency**: meaning-based retrieval depends on the course-provided gateway being reachable.
  Keyword-only retrieval has no external dependency, which is why User Story 2 is specified to be
  completable without one.
- **Single author, local execution**: there is one maintainer running everything locally. No concurrent
  index writes, multi-user access, authentication, or deployment concerns are in scope.
- **Reference material**: runbook subject matter, incident taxonomy, case schema, and metric definitions
  are drawn from `docs/prepare/02_design.md`, `07_short_dump_and_incidents.md`, `09_eval_plan.md`, and
  `templates/`. Those notes are inputs to this feature, not deliverables of it.
