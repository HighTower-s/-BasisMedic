# Specification Quality Checklist: Runbook Corpus, Labelled Eval Set, and Measured Retrieval

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Validation Notes

Iteration 1 — all items pass. Detail on the non-obvious judgements:

**Implementation-detail check**: named technologies from the author's design notes were deliberately
kept out. Retrieval modes are stated as *keyword-only / meaning-based / combined* rather than by
library or model name; the index is described by behaviour (rebuilt wholesale, addressable units)
rather than by storage format; the external dependency is referred to as "the course-provided
gateway". The citation address format `runbook-id#section` is retained because it is a user-visible
data contract that Feature 2 consumes, not an internal choice.

**Zero clarification markers — why no questions were asked**: four details were left open by the
feature description and each had a defensible source, so all four were resolved as documented
assumptions rather than as questions:

| Open detail | Resolution | Source |
|-------------|-----------|--------------|
| Dev split composition (10 cases, distribution unstated) | 8 in-scope, one per category, + 2 out-of-scope | `docs/prepare/09_eval_plan.md` |
| Thai case count ("2-3") | Fixed at 3, in the hard tier | Made exact so SC-001 is checkable |
| Whether the 2 mixed cases score as in-scope | Yes — 26 in-scope test cases for recall@3 / MRR / false refusal | `09_eval_plan.md` metrics table |
| Recall counted at section or runbook level | Runbook level; sections of one runbook collapse to one candidate | `09_eval_plan.md`, matching course reference |

**Measurability of the soft success criterion**: the feature description asked that out-of-scope logs
be rejected "at a rate the author can justify with the dev-set sweep". That is not directly
measurable, so it was split into two criteria that are: SC-009 (the floor in use is traceable to a
named dev sweep run, and both rejection and false-refusal rates are reported for it) and SC-014 (the
outcome is stated honestly either way). No numeric quality threshold is asserted anywhere in the
spec — see the Assumptions entry explaining why committing to a target before the first measurement
would work against Constitution Principle II (Honest Reporting).

**Structural deviations from the feature description, both deliberate**:

1. A sixth user story was added at P1 — the corpus and its rebuildable index. The description's five
   prioritised stories all presuppose it, and leaving it implicit would have left FR-001 through
   FR-012 without an owning story. It is independently testable (schema validation, allow-list
   coverage, clean-rebuild behaviour) without any search or eval code.
2. An `Out of Scope` section was added. The template does not include one, but the description listed
   explicit exclusions and they are load-bearing for a feature whose main risk is scope creep into
   Feature 2 (Constitution Principle VII).

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
- No `Constitution Check` section appears in this spec: the constitution requires that check in every
  **plan** and **task list**, which is where `/speckit-plan` and `/speckit-tasks` will add it.
