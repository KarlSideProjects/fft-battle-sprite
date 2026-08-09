---
name: fft-battle-sprite
description: "Produce a Final Fantasy Tactics style low-resolution pixel battle sprite set (idle, walk, attack) for a game character from a reference portrait, using built-in image_gen plus a deterministic mode-sampling downscaler. Use when a character needs new in-game combat frames, when generated pixel art comes out blurry at the delivery size, or when a second action sheet must match an already-accepted one. Not for portraits, map props, or UI."
---

# FFT Battle Sprite

Generate a coherent battle-sprite set for one character: **idle 1 frame, walk 4, attack 4**, delivered as square transparent PNGs at a low pixel resolution (default 64x64).

`image_gen` cannot draw at 64x64. It renders a large image; you downscale it. Everything below exists because the obvious way to do that produces mush.

## The three rules that decide whether this works

Every failure in this workflow traces to one of these. Put all three in the prompt before generating anything.

**1. Say the head is one third of the figure's height.** "3 heads tall" alone reliably yields 4-5 heads. At the delivery size a 4.5-head figure leaves the face 2-3 pixels and it reads as a smudge. Spell out the ratio.

**2. Say the art is authored at the delivery pixel budget and shown upscaled with nearest-neighbour, every art pixel a large flat square.** "Pixel art" alone yields a high-resolution painting with a pixel filter. It looks convincing at full size and dissolves when downscaled, because its colour-block edges do not land on the target grid.

**3. Say the character acts toward the right.** Engines mirror a sprite with `flip_h` and fire weapons along the facing axis, so authored art must strike in the +X direction. A left-handed swing plays backwards against its own weapon effect in half the game. Weapons, whips and striking poses stay in the right half of the cell.

## Never downscale with a normal resize

A plain resize averages several source colours into every output pixel: soft edges, no outline, no face. Use `scripts/pixelize_sprite.py`, which takes the **modal** colour of each source block instead, then rebuilds the 1px outline.

Process **every action in one invocation**. One call derives a single scale factor and a single shared palette across all frames. Separate calls give each action its own scale and palette, so the character changes size when attacking and its colours shimmer as the animation cycles.

```
python3 scripts/pixelize_sprite.py \
  --sheet <idle-clean>.png:2:2:idle_0,_a,_b,_c \
  --sheet <walk-clean>.png:2:2:walk_0,walk_1,walk_2,walk_3 \
  --sheet <attack-clean>.png:2:2:attack_0,attack_1,attack_2,attack_3 \
  --cell 64 --colors 32 --out <outdir>
```

`PATH:ROWS:COLS:NAME[,NAME...]` names each cell in reading order; names starting with `_` are throwaway extras. It anchors frames on the **feet**, not the bounding box, so a reaching pose does not shove the body sideways. It exits non-zero if a pose cannot fit the cell.

## Workflow

1. **Read the character's reference art** (`view_image` on the portrait or an accepted sheet). Identity comes from the picture, not from a text description.
2. **Generate idle first** as a 2x2 grid on solid `#FF00FF`. One action per sheet; never pack several actions into one grid.
3. **Look at the raw sheet before processing.** Is the figure ~3 heads with a large head? Are the pixel blocks big and flat? Is the outline unbroken? If not, regenerate — do not process a bad sheet, and do not try to rescue it in postprocessing.
4. **Generate the remaining actions**, passing the accepted sheet as a visual reference and demanding the same figure height and feet line. Measure: bounding-box heights across sheets should sit within a few percent. A crouched attack pose is legitimately shorter; a standing wind-up that is 10% shorter is generation drift.
5. **Chroma-key** each sheet to transparency, keeping the full-resolution `raw-sheet-clean.png`.
6. **Run the pixelizer once** over all sheets.
7. **Look at the result at 6x** and confirm the face and outline survive. Confirm the strike travels right.
8. **Snapshot each approved clean sheet into your own master directory the moment it passes review, and process from the snapshot.** A generation agent may keep working after you inspect its output and overwrite it; then the frames you ship cannot be reproduced. The downscaler is deterministic, so masters plus the command line reproduce the delivered art exactly — which is also what lets you change the delivery size or palette later without paying for a new generation. Keep masters out of version control if they are large.

## Prompt template

Fill the bracketed slots. Keep the rest — each clause is load-bearing.

```
Final Fantasy Tactics style pixel-art battle sprite animation sheet, [identity],
about 3 heads tall with the head roughly one third of the figure's height as the
primary recognition element, three-quarter front view standing on the ground,
the sprite is a [N]x[N] pixel image authored at that pixel budget and shown
upscaled with nearest-neighbour so every art pixel is a large flat square, eyes
are 1-2 dark pixels each with no rendered nose or mouth, 1px solid dark outline
enclosing the whole silhouette, hard-edged colour blocks with 2-3 value steps per
material and no gradients or anti-aliasing, limited palette of roughly 16-24
colours, light source fixed at the upper left, small flat elliptical ground
shadow under the feet in a dark neutral grey-brown not tinted by the background, [action description with the strike travelling right],
exact 2x2 grid, same subject in each cell, centered, consistent scale, feet on
one shared ground line, subject fills about 70% of cell height, solid #FF00FF
background, no text, no borders, no detached FX
```

Negative prompt:

```
downscaled illustration, painterly, soft shading, gradients, anti-aliased edges,
no outline, broken or partial outline, super-deformed 2-head chibi, realistic
5-head proportions, isometric 8-direction set, floating with no ground shadow,
blurry, pillow shading, drop shadow behind the sprite, multiple subjects per cell,
text, watermark, border, striking action directed to the left
```

## Attack sheets

Four frames: wind-up, strike, follow-through, recover.

Keep the weapon **close to the body**. A long lash or wide slash arc inflates the frame's bounding box, which costs the body its pixel budget under bbox-fit scaling and can push the pose out of the cell. Generate large weapon FX as a separate layer the game composites; the body sheet carries posture and a short accent near the hand.

## Delivery

- Square RGBA PNGs with real alpha. No baked magenta, checkerboard, or white box.
- One shared palette; per-frame colour count within budget (32 at `--cell 64`).
- Consistent feet line across every frame of every action.
- Attack clips are one-shot, not looping.

## Choosing the delivery size

Decide from a rendered comparison, not from arithmetic. Export the same processed source at two candidate sizes and look at them.

Pixel-budget estimates are optimistic: 48x48 was picked for this workflow by calculating head size, and the resulting faces were unreadable. 64x64 was adopted after seeing both. Whatever size you land on, the on-screen height matters more than the source size — scale the sprite so the player reads as the protagonist without dwarfing the enemies (roughly 2x their height works).
