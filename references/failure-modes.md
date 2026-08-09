# Failure modes

Every entry here was hit for real while building this workflow. Each cost a full
generation cycle. Check against this list before spending another one.

## The face is a smudge at delivery size

**Cause:** the figure is 4-5 heads tall. Asking for "3 heads tall" is not enough —
models read it as a style adjective, not a measurement.

**Fix:** state the ratio. "the head is roughly one third of the figure's height."

**How to catch it early:** measure the head in the raw sheet. At 4.5 heads a
64px delivery leaves roughly 9px of head and 2px of eye. At 3 heads it is 14px
and the eyes survive.

## The whole sprite is soft, outlines have dissolved

**Cause:** `image_gen` produced a high-resolution painting with a pixel-art
*look*. Its colour blocks are not aligned to any grid, so any downscale averages
across block boundaries.

**Fix:** two parts, both required.

1. Prompt: "authored at that pixel budget and shown upscaled with
   nearest-neighbour so every art pixel is a large flat square."
2. Downscale with modal sampling (`pixelize_sprite.py`), never a plain resize.

**How to catch it early:** view the raw sheet. Real coarse pixel art has visibly
uniform square blocks. A painting with a filter does not.

## The character swings away from its own weapon effect

**Cause:** the sprite strikes toward the left, but the engine mirrors with
`flip_h` and fires weapons along the facing axis, so authored art must act
toward +X.

**Fix:** "the strike travels toward the right, the weapon and striking arm stay
in the right half of the cell" — in the positive prompt, and
"striking action directed to the left" in the negative prompt.

**How to catch it early:** look at the strike frame. This is invisible in a
static frame gallery and obvious the moment it plays in-game, so check it
deliberately.

## The character changes size when it attacks

**Cause:** either the action sheets were generated at different figure scales,
or they were downscaled in separate passes so each got its own scale factor.

**Fix:** pass the accepted sheet as a visual reference when generating later
actions, demand the same figure height and feet line, and run every action
through **one** invocation of the downscaler.

**How to tell drift from a pose:** compare head sizes, not total height. A
crouched attack stance is genuinely shorter while the head stays the same size.
If the head shrank too, it is drift and the sheet needs regenerating — do not
correct it with per-frame scaling, which hides the problem and desynchronises
the feet line.

## Colours shimmer as the animation cycles

**Cause:** each frame was quantised independently, so every frame landed on a
slightly different palette.

**Fix:** one shared palette across all frames of all actions — what
`--colors` does when every sheet is passed to a single invocation.

## The body slides sideways during the attack

**Cause:** frames were centred on their bounding box. A reaching pose drags the
box toward the extended limb, so centring the box shoves the body the other way.

**Fix:** anchor on the feet. `pixelize_sprite.py` does this; if you write your
own placement, do the same.

## A weapon blows out the frame

**Cause:** a long lash, slash arc, or trail included in the body sheet inflates
the bounding box. Under bbox-fit scaling the body then shrinks to make room.

**Fix:** keep the weapon close to the body. Generate large FX as a separate
sheet the runtime composites.

## The delivered frames cannot be reproduced from the sheet you generated

**Cause:** you processed the generator's working file in place. A generation
agent may keep running after producing the sheet you inspected — re-exporting,
re-running QC, overwriting. The file you read and the file still sitting on disk
are then different, and re-running the downscaler yields art nobody reviewed.

This happened here: the clean sheet was rewritten roughly three minutes after it
was copied out, and only the copy reproduced the shipped frames.

**Fix:** the moment a sheet passes review, snapshot it into your own master
directory and process from the snapshot. Never point the downscaler at the
generator's scratch directory.

**Why it matters:** the downscaler is deterministic, so masters plus the command
line fully reproduce the delivered art. That property is what lets you change
the delivery size or palette later without paying for a new generation — and it
evaporates the moment the input can move underneath you.

## Palette rules that gate nothing

Before enforcing "all art must use these N colours", measure existing art
against it. A rule that current assets violate at 80-100% is not a rule; a
per-frame colour ceiling is enforceable and actually distinguishes pixel art
from a resized illustration.
