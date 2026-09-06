# Learner storage and compression demonstration

Measured 6 September 2026. Shared course files and learner files have different
scaling behavior: one shared source corpus per course; a separate evolving
workspace per learner. This is a storage demonstration, not a user-capacity test.

## What was measured

The configured local workspace root is `.lecturepilot/workspaces`. Its `users/`
tree contained one learner sample. Thirteen non-lock regular files were read;
eleven were text and two PDFs. Seven transient lock files were excluded.
No source content, account identifier or file names appear in the aggregate report.
This small sample is not a completed semester or a representative population.

Each group was placed in an in-memory tar archive, retaining relative paths and
file contents. gzip level 6 and Zstandard levels 3/9 compressed that same archive.
Every result was decompressed and matched byte-for-byte; original files were
hashed again and remained unchanged. No archive was retained or production
storage changed. Zstandard CLI version: 1.5.6.

| Payload      | Original logical bytes | Current allocated bytes | tar + gzip 6 | tar + zstd 3 | tar + zstd 9 |
| ------------ | ---------------------: | ----------------------: | -----------: | -----------: | -----------: |
| Text files   |                 38,331 |                  65,536 |        7,245 |        7,407 |        6,958 |
| Two PDFs     |                 79,787 |                  86,016 |       76,409 |       74,429 |       74,308 |
| Whole sample |                118,118 |                 151,552 |       84,605 |       83,181 |       82,586 |

Text compression with zstd 3 saved **80.7%** versus original logical bytes
(5.18 times smaller). For the whole sample it saved **29.6%** (1.42 times smaller).
Archive headers are included in compressed sizes; directory/inode metadata and
compressed-file allocation are not. Allocated bytes are host-specific and do not
predict another filesystem's physical consumption or account for shared blocks.

Do not conclude zstd 9 is faster from these runs. Compression was measured once;
zstd timing includes process launch and initial cache effects, while gzip runs
inside Python. This is a size comparison with round-trip validation, not a fair
codec throughput benchmark. The zstd 9 text saving over level 3 is only 449 bytes.

Aggregate evidence: `output/learner-storage-2026-09-06/results.json`.

## What can 10 GB hold?

Use **10 decimal GB dedicated to learner data**, with an illustrative 30% reserve:
7,000,000,000 bytes available. This excludes shared courses, database, OS, container
images and separately stored backups. The reserve is not a measured overhead model.

| Explicit per-student budget | Students by arithmetic |
| --------------------------- | ---------------------: |
| 1 MB                        |                  7,000 |
| 10 MB                       |                    700 |
| 100 MB                      |                     70 |

These are budget scenarios. Establish a semester-sized distribution before
choosing which row describes typical usage. For illustration only, dividing by
this tiny sample gives 59,262 copies by logical size or 84,153 archived copies
using zstd 3. Those are copies of a sparse snapshot, not validated student spaces.
Using its current allocated size instead gives 46,188 copies before directory
metadata. Do not headline a million students by counting only the text slice.

Useful presentation sentence: **“The course is shared. Personal learning state
is compact text, with media budgeted separately.”**
Then show 38.3 KB → 7.4 KB as the measured compression demonstration and the
1/10/100 MB table as the explicitly conditional capacity illustration.

Learner storage is not all text: generated images, practice-exam PDFs and retained
PPI source archives also live below learner roots. Even text grows with courses,
attempts, notes, provenance and retained history. Small files consume allocation
units and metadata; a small logical file does not use zero physical space.

## Engineering recommendation

Keep active Markdown/JSON files directly readable for now. The current filesystem
tools and memory store open plain UTF-8 files, with locking and atomic writes.
Transparent application-level compression would need coordinated reads, writes,
locking, recovery and migration. Saving a few KB in this sample does not justify
that change or a new configuration surface.

For a future backup/archive path, benchmark one archive per learner with gzip
and zstd at a moderate level. Bundling avoids separately storing thousands of
tiny compressed files. Per-learner archives preserve useful restore/deletion
granularity; a single archive across all users would complicate those operations.
Measure restore time and growth on mature workspaces before choosing a format.
This pass does not implement archiving or retention changes.

Zstandard is a reasonable candidate for fast lossless compression; dictionaries
can improve small-record compression but add a dependency that must be retained
for decoding. There is no need to add dictionary management for this sample.
[Official Zstandard documentation](https://facebook.github.io/zstd/index.html).

The production Caddy configuration already enables `encode zstd gzip`, reducing
eligible HTTP transfer size when negotiated. That does not compress files on disk.
Postgres TOAST concerns eligible large database values, not the Markdown files
stored in the application volume.
[PostgreSQL storage documentation](https://www.postgresql.org/docs/current/storage-toast.html).

## Architecture-slide speaker notes

The companion one-slide PPTX compares the runtime services. The backend owns
auth, course policy and model calls; model inference is external. The converter
and LaTeX compiler are isolated helpers. Postgres and course/learner files have
separate persistent volumes. A container is not created per student.

The LaTeX service compiles TeX documents to PDF; it is distinct from inline math
rendering in the learner's browser. API/compiler/converter limits are configured
ceilings, not measured usage or the size of their Docker images. Their ceilings
sum to 6 GiB before Postgres, gateway, web and the OS. Startup preflight and
migration jobs are described in speaker notes rather than drawn as runtime nodes.
