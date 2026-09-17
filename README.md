# Optic Processor

**Automated grading of standardized-test bubble sheets from a phone photo — built with classical computer vision, no ML model required.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.11-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![NumPy](https://img.shields.io/badge/NumPy-2.2-013243?logo=numpy&logoColor=white)](https://numpy.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

Marking a class set of exam papers by hand is slow, repetitive, and error-prone. Commercial OMR (Optical Mark Recognition) scanners solve this, but they cost thousands and require the sheets to be fed through dedicated hardware.

Optic Processor does the same job with a photograph. Upload a stack of images taken with an ordinary phone camera, and it deskews each sheet, locates every filled bubble, decodes the student's answers, grades them against a stored answer key, and returns a per-question breakdown — in roughly a second per sheet.

It currently targets the Turkish **TYT/AYT** university entrance exam sheet format (Türkçe, Sosyal Bilimler, Matematik, Fen Bilimleri, plus student number, booklet type, and session type), but the layout engine is data-driven and adding a new sheet format is a configuration change rather than a code change.

<!-- Add a screenshot or GIF here — it is the single highest-impact thing you can put in this README.
     Suggestion: a side-by-side of the uploaded photo and the results page.
![Optic Processor in action](docs/demo.gif)
-->

---

## Table of contents

- [How it works](#how-it-works)
- [Why template matching instead of a neural network](#why-template-matching-instead-of-a-neural-network)
- [Adding a new sheet layout](#adding-a-new-sheet-layout)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [Known limitations and roadmap](#known-limitations-and-roadmap)
- [License](#license)

---

## How it works

The recognition pipeline lives in `main/image_processing.py`. It runs in five stages.

### 1. Find the paper and flatten it

A photo taken by hand is never square to the page. The sheet is found as the largest external contour after Canny edge detection, then reduced to a quadrilateral with `approxPolyDP`. Its four corners are sorted into a canonical top-left / top-right / bottom-right / bottom-left order using a coordinate-sum and coordinate-difference trick, and a perspective transform maps that quadrilateral onto a flat rectangle.

```
Canny(50, 200)  →  findContours  →  largest contour  →  approxPolyDP
                →  order_points  →  getPerspectiveTransform  →  warpPerspective
```

The result is then resized to a fixed **600 × 800** canvas using `INTER_AREA` and lightly blurred. This normalization step is what makes everything downstream possible: after it, a bubble is always 12 × 12 pixels and the geometry of the sheet is known in advance, regardless of how far away the photo was taken.

### 2. Find every filled bubble on the page in one pass

Rather than examining each question individually, a single 12 × 12 sprite of a filled bubble is matched against the whole page with `TM_CCOEFF_NORMED` at a **0.85** correlation threshold. One call returns the coordinates of every mark the student made anywhere on the sheet.

### 3. Carve the page into sections using anchor templates

Each section of the sheet is bounded by two visual landmarks stored as small template images — typically the printed section header (e.g. the `TÜRKÇE` caption) and the black registration square printed beneath the column. Matching both gives a rectangle in image coordinates:

- `x_bounds` comes from the header template's left edge and width
- `y_bounds` runs from the bottom of the header down to the registration mark

Every filled-bubble coordinate from stage 2 is then bucketed into whichever section rectangle contains it. Because the anchors are found in the image itself rather than hardcoded as pixel offsets, the system tolerates small variations in print alignment and warp residue.

### 4. Decode coordinates into answers

This is where the arithmetic happens. Within a section, the distance from a bubble to the bounding-box edge — divided by the known 12-pixel bubble pitch — *is* the answer.

- **Horizontal sections** (answer columns, where options A–E run left to right): the vertical position gives the question number, and the horizontal offset from the right edge gives the letter.
- **Vertical sections** (the student number grid, where digits 0–9 run top to bottom): the axes swap.
- **Special sections** (booklet type, session type): a single mark is resolved against a small table of divide points.

Three edge cases are handled explicitly, and they are most of what separates a demo from something usable:

| Case | Handling |
|---|---|
| Template matching returns near-duplicate hits a few pixels apart for the same bubble | Deduplicated with a ±5 px proximity filter before decoding |
| A student marks two options on one question | Detected as multiple hits sharing a row, and skipped rather than silently mis-scored |
| A question is left blank, so it produces no hit at all | Inferred from the *gap*: the distance between consecutive marks divided by the pitch yields the number of skipped questions, which are emitted as `EMPTY` |

Leading blanks (before the first mark) and trailing blanks (after the last) are reconstructed the same way, and the result is padded to the section's declared question count so the output is always a complete, correctly-indexed answer list.

### 5. Grade

Decoded answers are compared against an `Answer` record looked up by book name, booklet type, and session type — so the same uploaded sheet is automatically scored against the right key when a class writes multiple booklet variants. The view returns correct / wrong / empty totals plus a per-question status list, rendered as a collapsible detail panel.

---

## Why template matching instead of a neural network

This was a deliberate design choice, and the trade-offs are worth stating plainly.

**In favour of the classical approach here:**

- **No training data.** A CNN-based bubble classifier needs thousands of labelled marks per sheet format. This system needs one 12 × 12 sprite and two anchor crops.
- **Deterministic and debuggable.** When a sheet decodes wrongly, the failure is a coordinate you can print and a threshold you can tune — not an opaque activation.
- **Fast on commodity hardware.** The whole pipeline is a handful of NumPy and OpenCV calls. No GPU, no model weights, no inference server.
- **The problem is genuinely rigid.** Printed answer sheets have fixed geometry. Once perspective is corrected, the position of a mark carries essentially all the information — learning a representation of it would be solving an easier problem with a harder tool.

**What it gives up:** robustness to poor lighting, heavy shadow, faint pencil marks, and partially erased answers, all of which a learned model handles more gracefully. Improving this is on the roadmap via adaptive thresholding before the matching stage.

---

## Adding a new sheet layout

Sheet formats are declared as data, not code. Each section is one dictionary entry:

```python
optic_2000 = {
    #  name              top anchor        bottom anchor      anchor-1   anchor-2    offset  orientation   option type   questions
    'turkish':        ('turkish_1.jpg', 'turkish_2.jpg',     'lower', 'not lower', False,  'horizontal', 'alphabetic', 40),
    'maths':          ('maths_1.jpg',   'maths_2.jpg',       'lower', 'lower',     False,  'horizontal', 'alphabetic', 40),
    'student_number': ('student_num_1.jpg', 'student_num_2.jpg', 'lower', 'not lower', True, 'vertical', 'numeric',    5),
    'book_type':      ('book_type_1.jpg', 'book_type_2.jpg', 'lower', 'lower',     False,  'special',    'alphabetic', 2),
}
```

To support a new sheet, crop the anchor landmarks and the filled-bubble sprite from a reference scan into `media/templates/<sheet_name>/`, add a dictionary describing the sections, and register the name in the upload dropdown. No changes to the decoding logic are required.

---

## Features

- **Batch upload** — process an entire stack of sheets in one submission
- **Perspective correction** — accepts handheld photographs, not just flatbed scans
- **Multi-section decoding** — four subject areas plus student number, booklet type, and session type from a single image
- **Blank and double-mark detection** — distinguishes unanswered from unrecognized, and flags ambiguous rows
- **Answer keys per booklet variant** — automatic key selection by booklet and session type
- **Per-question result breakdown** — correct / wrong / empty totals with an expandable question-by-question view
- **User accounts** — registration, login, and session handling via Django's auth framework
- **Layout-agnostic engine** — new sheet formats added by configuration

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Django 5.1 |
| Computer vision | OpenCV 4.11, NumPy 2.2 |
| Database | MySQL 8.0 |
| Frontend | Django templates, Bootstrap 5.3, vanilla JavaScript |
| Auth | Django `contrib.auth` with a customized `UserCreationForm` |

---

## Getting started

### Prerequisites

- Python 3.11 or newer
- MySQL 8.0 running locally
- `pip` and `venv`

### Installation

```bash
git clone https://github.com/<your-username>/optic-processor.git
cd optic-processor

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Copy the example environment file and fill in your own values:

```bash
cp .env.example .env
```

```ini
SECRET_KEY=your-django-secret-key
DEBUG=True
DB_NAME=optic_processor
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
```

Create the database:

```sql
CREATE DATABASE optic_processor CHARACTER SET utf8mb4;
```

### Running

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

### First use

1. Sign in, then go to `/admin` and create an `Answer` record — the answer key. Set `name` to the exam book identifier, `book_type` to `A` or `B`, `exam_type` to `TYT` or `AYT`, and each subject field to the correct answers as a single string (e.g. `ABCDE ACEBD...`).
2. On the home page, select that book and the `Optic 2000` sheet format.
3. Upload one or more photographs of completed sheets and submit.

A reference sheet is included at `media/sample_images/optic_2000.jpg`.

---

## Project structure

```
optic_processor/
├── main/
│   ├── image_processing.py     # CV pipeline: deskew, template match, decode
│   ├── views.py                # Upload handling, grading, auth views
│   ├── models.py               # Answer key model
│   ├── forms.py                # Registration form
│   └── templates/              # Bootstrap UI
├── media/
│   ├── templates/optic_2000/   # Anchor + bubble sprites for the sheet format
│   └── sample_images/          # Reference sheet
├── optic_processor/            # Django project settings
└── manage.py
```

---

## Known limitations and roadmap

Stated openly, because knowing where a system breaks is part of having built it.

**Current limitations**

- The bubble pitch is assumed to be 12 px after normalization; a sheet with materially different bubble spacing needs its sprite and constants revisited.
- Uploads are written to a single shared temporary filename, so concurrent submissions from different users can collide.
- Recognition degrades under strong shadow or with very faint pencil marks — the 0.85 correlation threshold is fixed rather than adaptive.
- Batch uploads are processed serially in the request cycle, so a large stack blocks the response.
- The horizontal and vertical decoders share substantial structure and would benefit from unification.

**Planned**

- [ ] Adaptive thresholding and illumination normalization before template matching
- [ ] Per-request temporary file isolation via `tempfile`
- [ ] Move batch processing to a Celery worker with progress reporting
- [ ] Unify the horizontal/vertical decoders behind a single axis-parameterized function
- [ ] Unit tests over a fixture set of sheets, including deliberately degraded scans
- [ ] Annotated output image showing detected marks overlaid on the original
- [ ] CSV / XLSX export of class results
- [ ] Docker Compose setup for one-command local deployment

---


