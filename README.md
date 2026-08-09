# fft-battle-sprite

An agent skill for generating Final Fantasy Tactics style low-resolution pixel
battle sprites — idle, walk and attack — for a game character, from a reference
portrait.

Works with **Claude Code** and **Codex CLI**.

## The problem it solves

Image generation models cannot draw at 64x64. They render something large and
you downscale it. Done naively that yields mush: the model produces a
high-resolution painting with a pixel-art *look*, and a normal resize averages
several source colours into every output pixel, so edges soften, the 1px outline
disappears and the face becomes a smudge.

This skill carries the prompt clauses and the postprocessing step that make the
output survive the trip down, plus a catalogue of the failure modes that each
cost a full generation cycle to discover.

## Install

Drop the directory into wherever your agent looks for skills:

| Agent | Location |
|---|---|
| Claude Code | `.claude/skills/fft-battle-sprite` |
| Codex CLI | `.codex/skills/fft-battle-sprite` |

If you use both, keep one copy and symlink it:

```sh
mkdir -p .agents/skills .claude/skills .codex/skills
git clone https://github.com/jhihweijhan/fft-battle-sprite .agents/skills/fft-battle-sprite
ln -s ../../.agents/skills/fft-battle-sprite .claude/skills/fft-battle-sprite
ln -s ../../.agents/skills/fft-battle-sprite .codex/skills/fft-battle-sprite
```

Image generation itself requires an agent with a built-in image tool. Codex CLI
has `image_gen`; Claude Code does not, and can run the postprocessing half only.

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | The workflow, the three prompt rules, and the prompt template |
| `references/failure-modes.md` | Each failure, its cause, its fix, and how to catch it early |
| `scripts/pixelize_sprite.py` | Modal-sampling downscaler with outline rebuild, feet anchoring and a shared palette |

## The downscaler

```sh
python3 scripts/pixelize_sprite.py \
  --sheet idle-clean.png:2:2:idle_0,_a,_b,_c \
  --sheet walk-clean.png:2:2:walk_0,walk_1,walk_2,walk_3 \
  --sheet attack-clean.png:2:2:attack_0,attack_1,attack_2,attack_3 \
  --cell 64 --colors 32 --out out/
```

Each `--sheet` is `PATH:ROWS:COLS:NAME[,NAME...]`, naming cells in reading
order; names starting with `_` are discarded. Input sheets must already be
transparent (chroma-key first).

It samples the **modal** colour of each source block rather than the mean, which
keeps hard edges; rebuilds the 1px dark outline that downscaling erodes; anchors
frames on the feet so a reaching pose does not shove the body sideways; and puts
every frame on one shared palette so colours do not shimmer between frames.

Pass every action in a single invocation — that is what makes the scale factor
and the palette shared. Separate runs give each action its own, and the
character will change size when it attacks.

Requires Python 3.10+ and the packages in `requirements.txt` (`pillow`, `numpy`).

## Not for

Portraits, map props, UI, or anything meant to stay at illustration resolution.
This is specifically for small sprites that must stay legible after a large
reduction.

## Licence

MIT. See `LICENSE`.
