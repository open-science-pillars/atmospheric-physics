---
name: receipt-figures
description: "Draw a time series or a convention contrast from an attested ASDC computation receipt, and from nothing else: the renderer runs the receipt's attester first, verifies every array it draws against the receipt's own bookkeeping and hashes, and writes the run identifier, the code digest and the verdict into the caption. Keywords: plot, figure, chart, show me the series, net TOA flux series, energy budget figure, all-sky and clear-sky series, cloud radiative effect series, convention contrast, total-region against cloud-free-area, caption, provenance."
---

# receipt-figures

This skill computes nothing. Every point it plots is a value the
receipt carries, every line it annotates is annotated with the
receipt's own field, and the computation that owns those numbers is
the concept the receipt names
(`knowledge/asdc/computations/energy-budget.md`,
`knowledge/asdc/computations/cloud-radiative-effect.md`). The renderer
fits no trend, takes no mean and combines no two receipts. A picture is
the easiest place for an unattested number to slip in, so this one
draws only from a receipt the attester passed, verifies every array it
draws, and stamps the figure with what it was drawn from.

This is the port of the ocean-science skill of the same name, with its
discipline intact and its modes changed to what these receipts carry.
The renderer ships beside this skill
(`scripts/receipt_figure.py`, PEP 723, matplotlib). It finds the
attesters in the installed provider bundle through the installer's
record (`claude plugin list --json`), or in a checkout named by
`NASA_DAAC_KNOWLEDGE`, the same way the wrapping skills and the sweep
do, and copies nothing into this repository.

## The three modes, and what each draws

- **`budget`**, from an energy budget receipt: the monthly net
  top-of-atmosphere flux the receipt carries
  (`series.toa_net_product_W_m2`, the product's own geodetic global
  mean, which is the series the anchor is defined on) against the ocean
  side the same receipt read from the Argo receipt. The window mean of
  the radiation term with its uncertainty, the ocean side sum with its
  uncertainty band, the residual against the bar, the verdict and the
  count of months shared with the anchor decade are all the receipt's
  own fields.
- **`cre-series`**, from a cloud radiative effect receipt: the all-sky
  and the clear-sky series in one band (`--band net`, `shortwave` or
  `longwave`), with the effect series the receipt carries below them
  and the window mean term drawn across it. The legend names the bound
  convention and the variable suffix the receipt says it read.
- **`contrast`**, from a cloud radiative effect receipt: the three
  terms under the bound convention against the same three under the
  other convention, from the receipt's own `convention_contrast` block.
  Six numbers, each a receipt field, and no seventh: that block carries
  no difference between the two conventions, so the renderer draws and
  prints none, and the two bars of each pair are the gap. The picture
  is the size of the incomparability between the two conventions and
  never a conversion.

There is no map mode. These receipts carry regional and global window
means and monthly regional series, and no per-cell field, so a map
would have to be loaded from beside the receipt and would be a picture
no receipt licenses. `map` exists only to refuse, by name.

## Behavior, in order

1. **Get the receipt from a run of the wrapping skill.** Read that
   skill first (`energy-budget-closure`, `cloud-radiative-effect`): it
   states the parameters, the refusal codes and the caveats that travel
   with every number in the picture. A figure from a sweep's receipts
   is a figure of one of its rows; name the row and its run id.
2. **Name the attester from the concept's `attester.resource`**
   (`energy_budget_check`, `cloud_radiative_effect_check`). The
   renderer runs it first and refuses to draw on anything but PASS. For
   a receipt produced on a stamped data root, pass `--data-root DIR`:
   without it the ASDC attesters take the data digests on the
   executor's word and do not verify them against the tree.
3. **Draw, from the plugin root:**

   ```bash
   uv run skills/receipt-figures/scripts/receipt_figure.py budget RECEIPT.json \
     --attester energy_budget_check \
     --data-root $ASDC/references/retrieval/energy-budget-root \
     --out budget.png

   uv run skills/receipt-figures/scripts/receipt_figure.py cre-series RECEIPT.json \
     --attester cloud_radiative_effect_check --band net \
     --data-root $ASDC/references/retrieval/cloud-radiative-effect-root \
     --out cre_net.png

   uv run skills/receipt-figures/scripts/receipt_figure.py contrast RECEIPT.json \
     --attester cloud_radiative_effect_check --out contrast.png
   ```

4. **Check the arrays.** The renderer hashes every array it draws, over
   the array's canonical JSON bytes, prints each digest and writes them
   into the caption. Restate a digest with `--expect NAME=SHA256` to
   redraw a published figure and prove it is of the same array; a
   mismatch is a refusal and not a figure. The renderer also hashes the
   receipt file on either side of the attestation, so what is drawn is
   the bytes the attester read, and checks every series against the
   month count the receipt's own bookkeeping states.
5. **Hand over the figure with its caption line** (the renderer prints
   it): the receipt's run id, the code digest, the receipt digest, the
   data record and manifest digest or the fixture seed and digest, each
   drawn array's digest, and the attester's verdict. Never crop it.
6. **Report the figure with the concept's caveats beside it**, not
   after it. For a budget figure: the anchor, the count of months the
   window shares with the anchor decade, what the combined uncertainty
   is made of, and the Argo domain. For a cloud radiative effect
   figure: the bound convention by name, that a cloud radiative effect
   is not a cloud feedback, and that the contrast is the size of the
   incomparability and not a conversion. A fixture figure proves the
   chain and not the Earth, and says so.

## Reading these figures

- **The budget figure's two levels are not two measurements of one
  thing over the whole window.** Over the months the window shares with
  the anchor decade the radiation level is the in situ heat uptake the
  product was set to, which the title states as a count; the ocean side
  is the Argo receipt's rate over the product's mapped open-ocean
  domain, which understates the global ocean by construction.
- **The series in a `cre-series` figure is the region's monthly mean,
  not a map.** The seasonal swing in the panel is the annual cycle of
  the region's fluxes, and the window mean line is the term the receipt
  states.
- **The contrast figure's two bars are two definitions of the
  subtrahend.** Their difference does not keep its sign from one region
  to another, so a contrast drawn for one region licenses nothing about
  another, and no single number moves a result between the two
  conventions.

## Must NOT

- Never draw from a receipt the attester did not pass, and never draw
  an array the receipt does not carry. The renderer refuses both; do
  not work around it with a hand-loaded file.
- Never draw a refusal receipt. It carries a reason code and no series;
  report the refusal in the executor's own words.
- Never draw a map or a per-cell field from these receipts, and never
  present a regional mean as though it were a spatial pattern.
- Never put a number in a title, a legend or a caption that the receipt
  does not carry: no fitted trend, no mean of the two conventions, no
  difference of two receipts, and above all no single global cloud
  radiative effect standing for both conventions at once.
- Never crop or drop the caption line, and never draw two receipts on
  one pair of axes as though their difference were a measured quantity.
- Never commit a receipt, an attestation or a generated figure to the
  provider bundle or to this repository.
