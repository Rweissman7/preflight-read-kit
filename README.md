# Preflight + Read Kit

Free Reader V3 ink maps on Kaggle, with a check first that the surface actually sits on the papyrus.

Before you spend GPU time reading a surface, the kit checks whether it sits on the papyrus, shows where on the page it doesn't, and only then reads it with Reader V3 in a direction fixed before reading. It writes a one-page report and a short list of surfaces that need a human look.

**It's a filter, not a text detector.** PASS means "the surface is placed right, worth reading", not "there is text here".

**Nothing here is built from scratch.** Every measurement comes from existing work (credits below). What the kit adds is putting those steps in order as one free run, with a verdict, a map of where the surface goes wrong, and reading only when it's worth it.

## Quick start (about an hour, no setup on your computer)
1. Open the [Kaggle notebook](https://www.kaggle.com/code/theancientdataset/preflight) and click **Copy & Edit**
2. In the right panel: Accelerator **GPU T4**, **Internet on** (Kaggle may ask you to verify your phone once), Persistence "Files only"
3. Run Cells 1, 2 and 3, then the "Your surface" cell as it is. It reads PHerc0841 w00, which has known letters: you should see PASS and letters in the forward map
4. To check your own surfaces, edit only the "Your surface" cell (`add_segment`, `add_volume` or `add_mesh`)

If Cell 1 shows "Could not resolve host", Internet is off.

## What you get for each surface
- **Verdict:** PASS (worth reading), BORDERLINE (worth reading, check by eye), FAIL (skip)
- **Red map:** where the surface sits outside the readable layers, the share of the page inside, and the biggest unbroken good area in cm2
- **Reader V3 maps**, forward and reverse, raw `.tif` files plus a report picture (pictures are contrast-stretched; the raw files are kept)
- **`to_check()`:** the surfaces that need a look by eye, and why

## Which surfaces pay to try
1. `run(name, check_only=True)` on many surfaces: verdict and map in seconds to minutes each, no reading
2. `table()` puts PASS first, then the biggest good area (the best guide to readable maps in our tests, preliminary)
3. `run()` only the top 3 to 5 (Kaggle gives about 30 free GPU hours a week)

## How it works
1. Data check (type, shape)
2. Papyrus check per 64-pixel tile: contrast, how often the brightest layer is near the middle, and how often it falls inside Reader V3's readable window
3. Verdict: the average of those three, each compared with the weakest known-readable segment of the same scan type, plus two floors (any one number below 60% of its line, or less than half the page inside the window, fails)
4. Direction fixed before reading (team-published volumes read forward). After reading, the forward/reverse ink ratio can only add a warning
5. Read with Reader V3 only on PASS or BORDERLINE
6. Report: JSON plus a four-panel picture

`kit/render_mesh.py` renders tifxyz meshes into surface volumes, so mesh-only patches work too.

## Preliminary results (October 2026)
Full table: `results/results_oct2026.csv` (scores only, no maps).
- All 16 test segments with known letters were kept (PHerc0841, 0139, 0814, 0500P2, 0009B)
- A PHerc0009B segment with only 23% of the page inside the window failed
- PHerc0800 (6 published segments): agrees with LynnHenry's pass rule on 4 of 6
- 9 clean-sheet patches: agrees with LynnHenry's verdict on 7 of 9
- Papyrus scores filter but don't rank: rank correlation with blind ratings of 23 maps by two raters was about 0. The biggest good area reached 0.73, but scroll differences may explain part of that
- No letters were seen on any First Letters surface

## Findings
- The readable window is flipped for team-published volumes (rendered with flip-normals): Domenico's -2 to +6 becomes -6 to +2 in their layer order
- The forward/reverse ink ratio can be fooled by bright cracks (PHerc0139 w039), so the direction is fixed before reading
- A "weakest of three" rule rejected two readable segments; the average with floors keeps them
- 8.64 um scans need their own contrast line
- Sheets sit about 9 layers apart: a 4-layer shift still reads, 9 layers reads the neighbor sheet (consistent with LynnHenry's offset-sweep)

## Limits
- PASS means worth reading, not that text is there
- It can't detect a jump to the neighbor sheet
- Pass lines come from a few known segments (the 8.64 um contrast line from one), and thresholds were set on some of the tested surfaces: a pilot, not a validated score
- The check-by-eye list flags too much on hard surfaces
- Flattened surface volumes (OME-Zarr layer stacks) and tifxyz meshes only, not native 3D ink detection
- Maps from First Letters scrolls are not shared here, per the prize rules

## Related work
- LynnHenry's [offset-sweep](https://github.com/LynnHenry/offset-sweep) measures how much a surface offset costs each model; this kit shows where on the page the offset is
- Diego's Ink Recoverability Protocol explains why a map came out blank; the report points to it

## Credits
Reader V3 by Domenico Russo (KLAVIS), and the readable window from his notes. Sheet-contrast check and direction rule by LynnHenry; the original sheet measure by rodriguescarson. Forward/reverse read-out by FreekCool. Clean-sheet patches by Jack and Andrew Gilman (CC BY-NC). Ink Recoverability Protocol by Diego. villa code and scroll data by the Vesuvius Challenge team (data CC BY-NC 4.0). Claude helped write the code and this text.

## Licence
Code: MIT (see LICENSE). Scroll data and model weights keep their own licences.
