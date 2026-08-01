# Technical writing workflow

Use this workflow for roadmaps, decisions, contracts, architecture, plans, evidence, audits, READMEs, references, docstrings, and substantial technical explanations.

The objective is accurate transfer of the model the reader needs, with the least unnecessary inference and rereading.

## 1. Identify authority and reader result

Before drafting, determine:

- the requested artifact and the question it must answer;
- its authority: descriptive, decisional, contractual, implementation, evidence, process, or history;
- its intended reader and what that reader may safely know already;
- the owning project artifact for every proposed change; and
- the concrete understanding, decision, or task the reader should be able to complete afterward.

Consult the user before changing accepted product meaning, milestone criteria, scientific interpretation, state authority, or material scope.

## 2. Establish the technical model

Inspect current source, tests, framework evidence, accepted contracts, neighboring documents, and public surfaces.

Separate:

- current fact;
- direct evidence;
- accepted commitment;
- product intent;
- hypothesis;
- replaceable implementation choice;
- unsupported candidate; and
- open question.

A writing task must not silently absorb an API, implementation, product, or unresolved design problem discovered nearby.

## 3. Define the artifact's unique job

Decide whether the artifact stands alone or participates in a larger path. State what it must establish, what it may assume, and where detail owned elsewhere should be linked rather than repeated.

If two documents claim the same job, repair the documentation structure before polishing either one.

## 4. Build the content model

Arrange information around the reader's developing model rather than discovery chronology or file order.

Assign one primary home to each material point. Elsewhere, omit it, orient briefly, or link to its owner.

Specify detail at the level its consequence requires:

- fully specify behavior, authority, lifecycle, failure, or commitment where ambiguity would change the system or decision;
- leave representation and local mechanics to implementation when they can vary without changing those facts; and
- do not use generic wording such as “provisional” to avoid resolving a consequential design question.

Ask of every added detail: **What error, ambiguity, or decision does this precision change, and is this where the reader needs it?**

## 5. Draft the complete reader path

Write the complete source-order argument or task flow before optimizing isolated sentences.

Use:

- paragraphs for reasoning and causality;
- lists for genuinely parallel items or steps;
- tables for repeated exact dimensions;
- diagrams only when they communicate topology, sequence, ownership, or state more efficiently than prose; and
- descriptive links for movement between authority layers.

Explain causal relationships, not only operational sequence. Define terms at the point of consequential ambiguity.

## 6. Review independently

### Contract pass

- Does the artifact fulfill one reader purpose and authority?
- Is it complete for that job without rebuilding the whole project?
- Are prerequisites and handoffs real and navigable?

### Technical pass

- Are mechanisms, sequences, limits, ownership, and strongest claims correct?
- Are support claims bounded by evidence?
- Is the distinction between current behavior and intended behavior explicit?

### Information-architecture pass

- Does every material point have one primary home?
- Are there repetitions, orphans, missing transitions, competing summaries, or broken links?
- Does a move preserve coverage and authority?

### Precision pass

- Which consequential claims remain vague?
- Which details are more specific than their purpose earns?
- Has an implementation detail been promoted into architecture?
- Has generic wording hidden a decision that should be made?

### Status and register pass

- Are fact, evidence, commitment, intent, hypothesis, candidate, and history legible?
- Does confident grammar overstate an unsupported claim?
- Does defensive qualification weaken an accepted commitment?

### Compression pass

- Can structure or a link replace repetition?
- Does every sentence add information, orientation, justified confidence, cause, contrast, or action?
- Would further shortening remove a necessary explanation or transition?

## 7. Fresh-reader review

Enter through the path a technically literate reader would plausibly use.

Ask:

> Where would the reader build the wrong model, lose the thread, doubt the claim, or need another file merely to repair this one?

Follow links far enough to confirm that promised information exists and that historical material is not masquerading as active authority.

## Common failures

- **Every document becomes standalone:** local completeness creates global duplication and drift.
- **The current file absorbs every gap:** information lands where editing is convenient rather than where it belongs.
- **Rigor means maximum detail:** the governing point disappears among qualifications.
- **Concision means removing explanation:** isolated facts remain but the causal model vanishes.
- **Tables replace synthesis:** rows appear without the relationship that makes them useful.
- **Status is flattened:** current fact, decision, intention, and candidate use the same certainty.
- **Revision chases the latest criticism:** one correction damages unrelated quality dimensions.
- **Documentation describes a PR rather than the repository:** titles and prose remain true only for the moment they were written.

## Completion

Writing is complete when:

- the artifact has one clear job;
- the technical model and strongest claims are supported;
- necessary detail is specified and safely variable detail is not frozen;
- each material point has one primary home;
- authority and status are accurate;
- the reader path works without reconstruction; and
- all accepted corrections have been applied to the artifacts that own them.

A polished document is not complete when its underlying model, ownership, or place in the repository remains wrong.
