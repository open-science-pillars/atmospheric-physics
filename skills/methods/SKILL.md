---
name: methods
description: "Write the methods paragraph and the reference list of an attested ASDC run from the receipt's bookkeeping block and the concept's sources and from nothing else, naming the edition, the release date, the clear-sky convention, the anchoring decade and the Argo receipt's identity as the receipt records them, with the receipt field behind every sentence. Keywords: methods section, methods paragraph, write up, reference list, references, citation, provenance, how was this computed, what do I put in the paper, data availability, edition, release date, convention, anchoring decade, Argo receipt."
---

# methods

This skill computes nothing and composes nothing freehand. Every
sentence it writes is filled from fields of one receipt the provider
bundle's attester passed, by the dotted paths the script records in a
provenance table beside the paragraph, and every reference is a source
entry the concept's own frontmatter carries, in the concept's own
words. The computation that owns the numbers is the concept the
receipt names (`knowledge/asdc/computations/cloud-radiative-effect.md`,
`knowledge/asdc/computations/energy-budget.md`). A fact the receipt
does not carry is not written: the script lists it as not carried, and
a sentence from anywhere else is refused by name.

This is the atmospheric-physics analogue of ocean-science's `cite-ecco`:
there the citation block is the tool's output byte for byte, and here
the paragraph and the reference list are. Use it when a run is going
into a draft, a data availability statement or a report, and the
question is what to write down about how the number was made.

The writer ships beside this skill (`scripts/methods.py`, PEP 723,
standard library only). It finds the concepts and the attesters in the
installed provider bundle through the installer's record
(`claude plugin list --json`), or in a checkout named by
`NASA_DAAC_KNOWLEDGE`, the same way the wrapping skills, the sweep and
the receipt-figures renderer do, and copies nothing into this
repository.

## What the paragraph names

For the cloud radiative effect: the region and the window, the run
identifier and the executor digest, the stamped record and its manifest
digest (or the fixture seed and digest), the product edition and its
release date and DOI and file, the bound clear-sky convention with the
variable suffix it reads and the definition the receipt carries, why
the convention is a receipt fact at all, the weighting, the latitude
band, the months used of the months in the window, the uncertainty
basis, the three terms with their uncertainties, the decomposition
residual against its stated tolerance and the verdict, the same three
terms under the other convention, and the distance from the published
global mean where the run is of its region, convention and period (or
the receipt's own statement of why no distance is stated).

For the energy budget closure: the window, the run identifier and the
executor digest, the input as above, the radiation product's edition
and release date, the anchoring statement, the anchoring decade with
the anchor's value and uncertainty and the count of months this window
shares with it, the Argo receipt's identity (its run id, its
computation and code digest, its window, its record, the capability and
version that produced it, and its stated rate), the Argo domain rule,
the area convention, the months used, the four terms, the residual
against the combined uncertainty and the verdict, and the anomaly trend
with the rule it was formed on.

On a fixture receipt the bookkeeping statements say in the receipt's
own words that the run is synthetic, and the paragraph says so rather
than naming an edition or an Argo receipt that does not exist.

## Behavior, in order

1. **Get the receipt from a run of the wrapping skill** and read that
   skill first: it states the parameters, the refusal codes and the
   caveats that travel with every number the paragraph quotes.
2. **Write it, from the plugin root:**

   ```bash
   uv run skills/methods/scripts/methods.py RECEIPT.json \
     --data-root $ASDC/references/retrieval/cloud-radiative-effect-root \
     --out methods.md
   ```

   `--data-root DIR` is given for a receipt produced on a stamped tree:
   without it the ASDC attesters take the data digests on the
   executor's word rather than verifying them against the tree.
   `--cited-only` narrows the reference list to the entries the
   paragraph actually cites; `--cite ID` narrows it to named source
   entries of the concept, and an id the concept does not carry is a
   refusal.
3. **Read the provenance table before pasting anything.** It names the
   receipt field behind every sentence and carries the attester's own
   verdict line. Check any sentence you doubt against the receipt at
   that path.
4. **Read the "not carried by this receipt" section.** Anything listed
   there is a gap in the write-up that the receipt cannot fill, and it
   is filled by running the computation differently or not at all,
   never by writing the sentence anyway.
5. **Paste the paragraph and the reference list into the draft**, under
   Methods and References, and say which run identifier it is of. Keep
   the footnote markers with the entries they point at.
6. **Add the concept's caveats beside the numbers**, in the draft and
   not in a footnote: for the cloud radiative effect that an effect is
   not a feedback and that the two conventions are not interchangeable;
   for the closure the anchor, the shared-month count, what the
   combined uncertainty is made of, and the Argo domain. The paragraph
   states the bookkeeping; the caveats are the concept's and are cited
   by bundle path.
7. **Anything else goes in your own words, over your own name.** The
   script refuses `--claim TEXT` for exactly that reason: a sentence
   this skill signs with a run identifier is a sentence the receipt can
   be checked against, and a sentence from anywhere else is not.

## Must NOT

- Never quote or write up a receipt the attester did not pass, and
  never write up a refusal receipt as a method that produced a number.
- Never add a fact the receipt does not carry and the concept's sources
  do not state, however certain it is. The script refuses it; do not do
  by hand what it refuses.
- Never reconstruct, abbreviate or reorder a citation. The reference
  list is the concept's source entries in the concept's own words; a
  reference the concept does not carry is not written here.
- Never write a number for a run that was not made: no combined figure
  across two receipts, no mean of the two clear-sky conventions, and no
  single headline effect standing for a table of runs.
- Never drop the convention from a cloud radiative effect sentence, and
  never drop the shared-month count or the Argo receipt's identity from
  a closure sentence.
- Never present a fixture paragraph as a statement about the Earth, and
  never commit a receipt, an attestation or a generated paragraph to
  the provider bundle or to this repository.
