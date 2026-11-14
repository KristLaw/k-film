# 450D rolls in Darkrooms

**Darkrooms** is M-Film's desktop app. It finds film rolls on a card by
reading the roll logs an M-Film camera writes next to the photos. A 450D
can't run M-Film, so K-Film writes the same log for you.

## Use it

1. `kfilm load portra400`. Any M-Film film id is shown in Darkrooms as itself.
2. Shoot RAW on the 450D.
3. Put the card in the computer and run `kfilm status` (or `kfilm sync`).
   This adds the new frames to the log.
4. Open Darkrooms. The roll is on its shelf: develop it there.

A K-Film film (e.g. `reggieportra`) is logged as its nearest M-Film film
(`portra400`), because Darkrooms only knows M-Film's films. Choose another
with `kfilm load reggieportra --darkrooms-film gold200` or
`kfilm sync --film gold200`. To skip the log: `--no-darkrooms`.

## The file

`DCIM/100CANON/ROLL_001.TXT`, in the format of M-Film 0.2.1 (`filmroll.c`):

```
# ML film mode roll log (filmroll module)
roll = 001
film = portra400
exposures = 24
loaded = 2026-11-14 16:27:26

1  _MG_6625.CR2  2026-11-14 16:16:48  f/4.5
2  _MG_6626.CR2  2026-11-14 16:18:04  f/4.5
```

The time and f-stop come from each photo's EXIF. `kfilm rewind` adds the
`# rewound ...` line M-Film writes.

## Limits

- Not tested in Darkrooms yet. Darkrooms is a separate app with its own
  rules, so it may not accept a 450D RAW or a roll it didn't see being made.
  If it refuses, open an issue with what it says.
- Darkrooms' free tier develops 1 roll a day; see M-Film's README.
- Deleting a roll in Darkrooms can delete the photos the log lists.
  Copy your RAWs off the card first.
