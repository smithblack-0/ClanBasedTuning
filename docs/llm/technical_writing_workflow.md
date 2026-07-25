# Business-technical writing workflow

This guide defines the standing process for substantial ClanBasedTuning writing:
roadmaps, decisions, designs, plans, reports, audits, READMEs, user guidance,
reference documentation, docstrings, and technical explanations.

It is a writing process, not a source of project authority. The roadmap,
decisions, gates, plans, implementation, evidence, and review records retain
their documented roles.

## Core imperative

Business-technical writing is the controlled transfer of a decision-relevant
technical model.

Its governing objective is **transmission efficiency**:

> Give the reader the most accurate and useful understanding possible for the
> least attention, inference, and rereading.

The relevant unit may be one artifact or a path through several artifacts. A
participating document should be complete for its assigned job, not repeat the
entire project until it can stand alone.

Business relevance selects information. Technical substance establishes
credibility. Information design controls how efficiently the reader builds the
right model.

Do not equate business writing with a shallow overview or technical writing with
exhaustive detail. Select technical detail according to the work it performs for
the reader.

## Establish the communication contract

Before drafting, determine:

1. **Transmission boundary:** Is this a standalone artifact or one part of a
   larger documentation path?
2. **Artifact role:** What unique job does this document perform? What may it
   assume, what must it establish, and where should it hand the reader next?
3. **Audience:** Who will use it, and how close are they to the subject?
4. **Reader purpose:** What decision, evaluation, implementation, or task brings
   the reader here?
5. **Starting model:** What can the reader safely be expected to know?
6. **Required result:** What should the reader understand, decide, or be able to
   do afterward?
7. **Authority:** Is the artifact descriptive, advisory, decisional,
   contractual, instructional, referential, or an audit record?
8. **Reading path:** Will the reader proceed in order, scan, compare options,
   follow steps, consult a section during work, or move among linked artifacts?

If these answers are unclear, writing prose is premature. Gather evidence,
resolve the artifact's place in the larger documentation system, and construct
its information model first.

## Standalone and participating artifacts

A standalone artifact owns the complete reader model required for its purpose.
It may cite supporting evidence, but its central task does not depend on an
undocumented path through other files.

A participating artifact owns one complete part of a larger reader path. It must
not repeat neighboring documents merely to become locally self-contained.
Participation does not excuse accidental incompleteness: prerequisites and
handoffs must be real, explicit, and navigable.

Before adding material, inspect:

- relevant entry points and neighboring documents;
- the public interfaces and behaviors the reader will encounter;
- existing authoritative homes for the same concepts;
- undocumented public behavior and stale or competing explanations;
- whether a discovered gap is a writing problem, product problem, API problem,
  ownership problem, or unresolved decision.

Do not let the current file absorb every gap discovered during research.

## Five simultaneous objectives

Review every substantial artifact against all five. Improving one does not
justify silently damaging another.

### Useful

- Does the artifact answer the questions that bring the reader there?
- Can the reader make the intended decision or perform the intended task?
- Does it cover the material consequences rather than merely describe nearby
  technology?
- Does it advance the larger reader path without rebuilding earlier material?

### Technically credible

- Are mechanisms, constraints, causal claims, and limitations correct?
- Can a knowledgeable reader see where the system works and where it stops?
- Are claims supported by evidence, precedent, or derivation?
- Are unsupported aspirations clearly expressed as intent, hypothesis, or
  candidate scope rather than current fact?

### Clear

- Does the reader receive the right mental model without repairing vague terms,
  hidden assumptions, or ambiguous references?
- Are definitions, examples, contrasts, and sequence supplied where they prevent
  material misunderstanding?
- Are current fact, evidence, intent, commitment, hypothesis, and possibility
  distinguishable?

### Efficient

- Does every sentence add information, orientation, justified confidence, or a
  useful relationship?
- Is precision purchased only where its benefit exceeds its attention cost?
- Have repetition, premature detail, empty emphasis, and defensive qualification
  been removed?

### Coherent

- Does the artifact or documentation path build one usable model from beginning
  to end?
- Does each material fact have an appropriate primary home?
- Do headings, prose, lists, tables, diagrams, transitions, and links expose the
  actual hierarchy and relationships?

## Select technical substance by reader work

Include enough material for the intended reader to answer the relevant subset
of these questions:

- What is this, in terms connected to familiar systems?
- Why does it exist, and what becomes possible if it works?
- How does it work at the level needed to evaluate the claim?
- How would someone use it?
- What does it own, support, or change?
- What can it not do, and why?
- What evidence or precedent exists?
- What is true now, intended, committed, hypothetical, or merely possible?
- What decision, risk, dependency, or next step follows?

These are selection questions, not a mandatory section template.

Prefer details that perform several jobs at once. A precise contrast with a
familiar system may define the mechanism, establish value, and expose a limit
more efficiently than a list of internal classes.

### Explain causality, not merely sequence

Where the mechanism matters:

1. establish the relevant lifecycle or data flow;
2. identify what is shared and what differs;
3. explain why the difference produces the claimed behavior; and
4. derive the useful domain and hard boundary from the same mechanism.

An operational list that omits causality may be accurate but still fail to
transmit the design.

## Allocate precision deliberately

Precision is a cost-bearing resource.

Add precision when it:

- prevents a consequential misunderstanding;
- defines a capability, boundary, responsibility, lifecycle, or commitment;
- establishes mechanism or causality;
- supports a decision or implementation;
- distinguishes the system from a familiar alternative; or
- provides necessary evidence.

Defer or omit precision when it:

- explains a standard consequence the reader can safely infer;
- answers a question the current section has not raised;
- introduces implementation detail before its governing concept;
- repeats a qualification already established by structure or authority;
- narrows a deliberately broad and accurate statement without decision value; or
- competes with a more important point for attention.

Ask:

> What error, ambiguity, or decision would this added precision change, and is
> this the place where the reader needs it?

Define terms at the point of consequential ambiguity. Use one term consistently
for one concept. Do not introduce vocabulary that saves the writer words while
making the reader memorize unnecessary labels.

## Give each fact a primary home

Assign every material point to the artifact or section whose purpose requires
its full precision.

Elsewhere:

- omit it when the reader does not need it;
- name or summarize it briefly for orientation;
- link to its primary home when the reader may need the detail; or
- repeat it only when repetition saves more attention than it consumes.

Cross-references are part of the design. They let early layers name important
concepts without duplicating their complete contracts.

### Detect orphans

An orphan is an accurate fact whose purpose at its location is unclear. It often
means:

- the fact belongs elsewhere;
- the document is missing the concept that gives it meaning; or
- the fact is unnecessary for this reader task.

During source-order review, ask why each paragraph appears at that exact point,
what the reader can assume afterward, and whether another artifact is its better
owner.

## Design the reader path

Organize around the reader's developing model, not discovery chronology, file
tree order, or implementation structure.

A common explanatory path is:

1. familiar context and unmet need;
2. specific contrast with existing approaches;
3. mechanism and causal explanation;
4. use and supported domain;
5. limits and costs;
6. evidence or precedent; and
7. status, decision, or next step.

Change the order when the reader task requires it. A decision memo normally
begins with the decision. A troubleshooting guide begins with symptoms and
recovery.

Use layout as syntax:

- paragraphs for reasoning and causal continuity;
- lists for parallel items, steps, criteria, or options;
- tables for exact repeated dimensions or mappings;
- diagrams for topology, sequence, ownership, or state change when prose is
  materially slower; and
- descriptive links for movement among documentation layers.

Do not turn relational arguments into stacks of bullets merely to appear
scannable.

## Keep authority and status legible

Use wording and artifact context to distinguish:

| Status | Meaning |
| --- | --- |
| Current fact | True of the present system or situation. |
| Evidence | An observed result with a stated basis. |
| Product intent | Direction the project is trying to make possible. |
| Commitment | Capability or behavior a named scope must provide. |
| Hypothesis | Claim that evidence is intended to test. |
| Candidate | Possible future scope without present commitment. |

Do not weaken intentions into evasive possibilities merely because they are not
release promises. Do not promote aspirations into commitments through confident
grammar. Do not burden every sentence with a status label when the section or
artifact already establishes it.

Accepted decisions remain accepted unless a specific clause is explicitly
reopened. Do not flatten a mixed authority state into “everything accepted” or
“everything provisional.”

## Write efficient prose

Every sentence should perform at least one job:

- add a fact or claim;
- establish scope, status, or authority;
- explain mechanism, cause, consequence, or contrast;
- orient the reader within the argument;
- define a term or resolve an ambiguity;
- support a decision or next action; or
- derive a result not already stated.

Remove empty emphasis and repeated conclusions. Preserve transitions that explain
why the next topic follows, show a change in abstraction or authority, or connect
mechanism to value or limitation.

Use concrete, stable language. Keep actors visible when ownership matters. Keep
terms consistent. Avoid vague pronouns, filler, stacked modifiers, and abstract
nouns that hide the action.

Concision means reducing total reader effort, not mechanically shortening every
sentence or removing explanations.

## Drafting workflow

Treat the first coherent draft as a working implementation.

### 1. Establish evidence and authority

Read the governing sources, current artifact, relevant implementation, comments,
and consumers. Separate verified fact from inference, intent, commitment, and
open question. Do not reconstruct technical meaning from names or prior prose
alone.

### 2. Map the relevant documentation system and public surface

Inspect the entry path, neighboring artifacts, public interfaces, existing
concepts, stale claims, competing sources of truth, and undocumented behavior
needed for the intended reader task.

Restrict the map to the relevant boundary. This is not a demand to rewrite the
entire repository.

### 3. Define the artifact contract

Record the artifact's role, prerequisites, handoffs, audience, assumed knowledge,
reader task, required post-reading model, authority, and likely reading path.

### 4. Build the content model before prose

Gather candidate facts, mechanisms, limits, evidence, decisions, and dependencies
in scratch form. For each, state why the reader needs it and whether another
artifact already owns it. Resolve material technical gaps before polishing.

### 5. Assign information homes

Construct the local outline and cross-document path. Give each material fact one
primary home. Record uncovered work explicitly rather than quietly making the
current artifact absorb it.

### 6. Draft in source order

Write the whole argument or task flow. Do not optimize isolated paragraphs while
the document model remains unstable. Preserve enough connective tissue for each
section to inherit the correct model from the previous one.

### 7. Run independent review passes

#### Contract pass

- Does the artifact fulfill its reader purpose and authority?
- Is it complete for its assigned job without pretending to own the entire
  documentation system?
- Are prerequisites and handoffs explicit and usable?
- Has another document type contaminated it?

#### Technical pass

- Are mechanisms, sequences, comparisons, limits, and causal claims correct?
- Is the strongest wording supported?
- Are central facts specific enough for the intended decision or implementation?

#### Information-architecture pass

- Does the reader receive the governing model before dependent detail?
- Does each fact have one appropriate home?
- Are there repetitions, missing transitions, or orphans?
- Do cross-document moves preserve coverage and authority?

#### Precision pass

- Which important claims remain vague?
- Which details are more precise than their purpose justifies?
- Did a clarification narrow an intentionally broad claim?
- Would a contrast, definition, example, or reference transmit the point better?

#### Status and register pass

- Are fact, evidence, intent, commitment, hypothesis, and candidate scope legible?
- Does modest persuasion stop after establishing relevance?
- Are limits candid without becoming generic defensive prose?

#### Compression pass

- What can be removed without losing information, orientation, or justified
  confidence?
- Can layout or a link replace repetition?
- Does every remaining sentence improve the transmission?

#### Fresh adversarial pass

Enter through the path a technically literate reader would plausibly use. Reread
from the beginning and ask:

> Where would I build the wrong model, lose the thread, doubt the writer, or have
> to reread?

Follow prerequisite and outward links far enough to verify the promised reader
path. Correct the artifact or its assigned path, then rerun all objectives.

## Common failure patterns

### Every document becomes standalone

Each artifact repeats orientation, definitions, mechanism, limits, and reference
detail. Local completeness creates global duplication and inconsistency.

**Correction:** define each artifact's role, prerequisites, and handoffs. Keep it
complete for that role.

### The current file absorbs every discovered gap

Research finds stale or missing material elsewhere, so the target file quietly
becomes its home.

**Correction:** classify each gap as local documentation, cross-document work,
public-surface work, implementation work, or an unresolved decision.

### Rigor means maximum precision

Every claim accumulates qualifications and edge cases until the main point is one
detail among many.

**Correction:** require each precision increase to name the consequential
ambiguity or decision it serves.

### Concision means removing explanation

Transitions, examples, comparisons, and causal links disappear while isolated
facts remain.

**Correction:** optimize total reader effort, not word count.

### Tables replace synthesis

Accurate rows appear without the governing relationship that makes them useful.

**Correction:** state the relational model in prose, then use the table for exact
comparison or reference.

### Status is flattened

Current facts, accepted decisions, proposals, intentions, and candidates use the
same level of certainty.

**Correction:** restore status through artifact authority, section role, and
precise wording.

### Revision chases the latest criticism

The newest correction becomes the entire writing theory.

**Correction:** treat feedback as evidence against the whole model. Apply the
correction, then recheck all objectives for regressions.

## Completion test

Before delivery, answer from the finished artifact and reader path:

1. What exact part of the transmission does this artifact own?
2. What model should the intended reader now hold?
3. What decision or action can the reader now take?
4. Which technical details establish the central claims?
5. Which major limitation prevents overgeneralization?
6. Where is exact support, implementation, or reference detail located?
7. Are prerequisites, handoffs, and authorities real and navigable?
8. Is every material statement's status legible?
9. Which sentence contributes the least, and why does it remain?
10. Which detail received the most precision, and what consequence earns it?
11. Does the path contain any orphan, repetition, coverage gap, or unexplained
    transition?
12. Did the final revision improve the whole transmission rather than optimize
    one recent complaint?

The artifact is complete only when its technical content is correct, its local
contract is fulfilled, its place in the larger reader path is coherent, and
further compression would cost more understanding than it saves.
