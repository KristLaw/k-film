# Could M-Film run *inside* the 450D?

Short answer: **not today.** This page records what was checked, so anyone
who wants to try has a starting point.

## What M-Film needs

From M-Film's `PORTING.md` and README (checked November 2026):

- A working **Magic Lantern platform build** for the exact camera + firmware.
- A port layer (`fos_port_*` functions) for screen, keys, and memory.
- A **720×480 bitmap overlay with a 254-colour palette**, which works on
  DIGIC 4 and 5.
- The whole build must fit the camera's boot memory limit.
- M-Film only targets cameras "where Magic Lantern is mature": DIGIC 4 and 5.
  Its supported list starts at the 500D and 50D.

## What the 450D is

| | 450D | 500D (supported by M-Film) |
|---|---|---|
| Processor | DIGIC III | DIGIC 4 |
| Canon OS | VxWorks | DryOS |
| Last Canon firmware | 1.1.0 (2009) | 1.1.1 |
| Magic Lantern | 2016 test build only | Stable nightly |
| RAW | 14-bit CR2, 4272×2848 | 14-bit CR2 |

All Magic Lantern platforms that M-Film uses are DryOS cameras. The 450D,
40D, 1000D and original 5D run VxWorks, and the Magic Lantern wiki calls
supporting them "lots of effort".

## The existing 450D Magic Lantern work

- Forum thread: "Porting ML to XSi (450D)" on magiclantern.fm.
- Developer **Ant123** published a test build for **450D firmware 1.1.0**
  in October 2016 (`ML450D110.fir` + `magiclantern-Nightly.2016Oct26.450D110.zip`)
  from the `magic-lantern-40d` fork on Bitbucket.
- Reports from users say only basic things work (boot, menu, intervalometer).
- Bitbucket removed Mercurial repos in 2020, so those links may be dead.
  Look for mirrors on GitHub before starting.
- A related 40D port (also DIGIC III / VxWorks) lives in the `vxworks`
  branch of the old Magic Lantern tree.

## A realistic roadmap (if you want to try)

You need the camera and a spare SD card. Check whether Magic Lantern's QEMU
fork can boot a 450D ROM dump before testing on the real camera.

1. **Find the code.** Locate a mirror of Ant123's `magic-lantern-40d` fork
   and the `vxworks` branch. Build it for `450D.110`.
2. **Boot plain ML.** Confirm the camera boots and the ML menu draws. Note the
   boot image size; the memory budget decides everything after this.
3. **Display test.** Check whether the 450D overlay can show a 254-colour
   palette at 720×480. DIGIC III LCD is 320×240-class (3.0" 230k dots),
   so M-Film's screens would need a new low-res layout.
4. **Keys.** Map buttons and the half-shutter event.
5. **Minimal roll.** A frame counter + "film loaded" screen that hides the
   review image. This alone gives most of the film feeling.
6. **Darkroom last.** In-camera development is probably out of reach on
   DIGIC III memory. Keep development on the PC (this repo).

Estimated effort: months of reverse engineering, not a weekend. Step 5 is
the most useful realistic goal.

## Why this repo exists instead

The film feeling comes from three things: committing to one stock, not
seeing your photos, and getting a whole roll back at once. All three work
without touching the camera's firmware, with zero risk to the camera. That
is what XSi Darkroom does.

## Sources

- M-Film README and PORTING.md: https://github.com/HNGSeries/mfilm-canon-film-simulation
- Magic Lantern forum, "Porting ML to XSi (450D)": https://www.magiclantern.fm/forum/index.php?msg=212129
- Magic Lantern wiki (VxWorks cameras): https://magiclantern.fandom.com/wiki/Magic_Lantern_Firmware_Wiki
- DPReview 450D review (DIGIC III, 14-bit CR2): https://www.dpreview.com/reviews/canoneos450d/3
- Canon 450D firmware 1.1.0: https://www.dpreview.com/?p=316773
