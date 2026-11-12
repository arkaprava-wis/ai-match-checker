#!/usr/bin/env python3
"""
Detect handwritten ticks in pre-printed A/B/C option boxes on worksheet images/PDFs.

Designed for worksheets like the supplied test1-test14 sheets. Detects printed
A/B/C cells individually, allowing uneven row spacing and section headings.
Also checks for pencil ticks written over the printed answer.

Output:
- Annotated images showing detected cells and ticks
- Console summary of processed rows and review counts

Important:
This is image-based detection, so review the annotated image and rows marked
"REVIEW" when handwriting is faint, overlaps a border, or the scan is skewed.
"""
from __future__ import annotations

import argparse
import copy
import csv
from pathlib import Path

import cv2
import numpy as np

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    fitz = None

# Layout values are fractions of the page width/height, based on the sample sheet.
# If your worksheets use the same template, these defaults should be a good start.
DEFAULT_LAYOUT = {
    "first_row_center_y": 0.0835,
    "last_row_center_y": 0.9410,
    "row_count": 34,
    # x ranges for the narrow tick cells (fractions of page width)
    "A": [0.657, 0.695],
    "B": [0.791, 0.830],
    "C": [0.925, 0.962],
    # fraction of row height used around each row center
    "row_half_height": 0.0105,
    # pixels of padding inside the checkbox to avoid printed borders
    "inner_x_padding": 3,
    "inner_y_padding": 2,
}


def load_pages(path: Path, dpi: int = 250):
    """Yield (page_number, BGR image), where page_number starts at 1."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if fitz is None:
            raise RuntimeError("PDF input requires PyMuPDF. Install with: pip install pymupdf")
        doc = fitz.open(path)
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        for index, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                image = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            else:
                image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            yield index + 1, image
    else:
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f"Could not open image: {path}")
        yield 1, image


def tick_cell_crop(image, x_range, y_center, half_height, x_padding=3, y_padding=2):
    h, w = image.shape[:2]
    x1 = max(0, int(round(x_range[0] * w)) + x_padding)
    x2 = min(w, int(round(x_range[1] * w)) - x_padding)
    y1 = max(0, int(round((y_center - half_height) * h)) + y_padding)
    y2 = min(h, int(round((y_center + half_height) * h)) - y_padding)
    if x2 <= x1 or y2 <= y1:
        return None, (x1, y1, x2, y2)
    return image[y1:y2, x1:x2], (x1, y1, x2, y2)


def detect_box_rows(image):
    """Choose the most complete grid from normal and broken-border extraction."""
    grids = []
    for repair in (False, True):
        try:
            grids.append(_detect_box_rows(image, repair))
        except ValueError:
            pass
    if not grids:
        raise ValueError("Could not locate worksheet boxes; use --manual-layout for a fixed grid")
    return max(grids, key=len)


def _detect_box_rows(image, repair=False):
    """Find the actual blank cells, including skew and gaps for section headers.

    Horizontal/vertical morphology suppresses text and handwriting before looking
    for enclosed cells. Work at a bounded resolution so PDF DPI is immaterial.
    Returned quadrilaterals follow the inside edges of the printed borders.
    """
    scale = min(1.0, 2400 / image.shape[1])
    work = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image
    h, w = work.shape[:2]
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 31, 12)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                  np.ones((1, max(12, w // 70)), np.uint8))
    horizontal = cv2.morphologyEx(horizontal, cv2.MORPH_CLOSE,
                                  np.ones((1, max(3, w // 100)), np.uint8))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                np.ones((3 if repair else max(10, h // 160), 1), np.uint8))
    vertical = cv2.morphologyEx(vertical, cv2.MORPH_CLOSE,
                                np.ones((10 if repair else max(3, h // 200), 1), np.uint8))
    grid = cv2.morphologyEx(horizontal | vertical, cv2.MORPH_CLOSE,
                            np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if not (x > .48 * w and .035 * w < width < .085 * w
                and .013 * h < height < .030 * h):
            continue
        polygon = cv2.approxPolyDP(contour, .025 * cv2.arcLength(contour, True), True)
        if len(polygon) != 4:
            polygon = cv2.boxPoints(cv2.minAreaRect(contour))
        points = np.asarray(polygon, dtype=np.float32).reshape(4, 2)
        # Order clockwise: top-left, top-right, bottom-right, bottom-left.
        points = points[np.argsort(points[:, 0])]
        left = points[:2][np.argsort(points[:2, 1])]
        right = points[2:][np.argsort(points[2:, 1])]
        quad = np.array([left[0], right[0], right[1], left[1]]) / scale
        candidates.append(quad)

    # Learn all six printed columns (answer, tick, repeated A/B/C). This
    # tolerates margins and photographs where the sheet does not fill the frame.
    clusters = []
    for quad in sorted(candidates, key=lambda q: q[:, 0].mean()):
        if not clusters or quad[:, 0].mean() - np.mean(
                [q[:, 0].mean() for q in clusters[-1]]) > .023 * image.shape[1]:
            clusters.append([])
        clusters[-1].append(quad)
    clusters = [cluster for cluster in clusters if len(cluster) >= 3]
    if len(clusters) != 6:
        raise ValueError("Could not locate six worksheet columns; use --manual-layout for a fixed grid")
    tick_columns = clusters[1::2]
    candidates = [quad for column in clusters for quad in column]
    all_column_centers = np.array([np.median([q[:, 0].mean() for q in column])
                                   for column in clusters])
    grouped = []
    for quad in sorted(candidates, key=lambda q: q[:, 1].mean()):
        if not grouped or (quad[:, 1].mean() - np.mean(
                [q[:, 1].mean() for q in grouped[-1]])) > .012 * image.shape[0]:
            grouped.append([])
        grouped[-1].append(quad)
    # A row needs at least two real cells; isolated rectangles are not questions.
    grouped = [row for row in grouped if len(row) >= 2]
    if len(grouped) < 3:
        raise ValueError("Could not locate worksheet boxes; use --manual-layout for a fixed grid")
    rows = []
    for group in grouped:
        row = {}
        for quad in group:
            column = int(np.argmin(abs(all_column_centers - quad[:, 0].mean())))
            label = 'ABC'[column // 2]
            if column % 2:
                row[label] = quad
        for quad in group:
            column = int(np.argmin(abs(all_column_centers - quad[:, 0].mean())))
            label = 'ABC'[column // 2]
            if column % 2 == 0 and label not in row:
                # A broken tick-cell border need not erase the question: the
                # adjacent answer cell supplies its measured height and skew.
                reference = min(tick_columns[column // 2],
                                key=lambda q: abs(q[:, 1].mean() - quad[:, 1].mean()))
                left_top, left_bottom = quad[1], quad[2]
                top_width = reference[1] - reference[0]
                bottom_width = reference[2] - reference[3]
                inset = np.float32([3 / scale, 0])
                row[label] = np.array([left_top + inset, left_top + inset + top_width,
                                       left_bottom + inset + bottom_width,
                                       left_bottom + inset], dtype=np.float32)
        if len(row) < 2:
            continue
        rows.append(row)
    # A damaged border can merge two cells. Infer only the missing cell from
    # nearby rows, retaining the locally measured row height and page skew.
    for index, row in enumerate(rows):
        for label in 'ABC':
            if label in row:
                continue
            reference = min((j for j, other in enumerate(rows) if label in other),
                            key=lambda j: abs(j - index))
            shared = next(key for key in row if key in rows[reference])
            row[label] = rows[reference][label] + row[shared] - rows[reference][shared]
    return rows


def box_crop(image, quad, answer=False, extend=False):
    """Rectify a detected cell and inset its border, not a page-relative grid."""
    quad = np.asarray(quad, dtype=np.float32).copy()
    if answer:
        # The answer cell immediately to the left is about 1.18 tick-cell widths.
        top = quad[1] - quad[0]
        bottom = quad[2] - quad[3]
        quad = np.array([quad[0] - 1.18 * top, quad[0], quad[3],
                         quad[3] - 1.18 * bottom], dtype=np.float32)
        if extend:
            quad[2:] += .35 * np.array([quad[2] - quad[1], quad[3] - quad[0]])
    width = max(8, round(np.linalg.norm(quad[1] - quad[0])))
    height = max(8, round(np.linalg.norm(quad[3] - quad[0])))
    target = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    crop = cv2.warpPerspective(image, cv2.getPerspectiveTransform(quad, target), (width, height))
    pad = max(2, round(min(width, height) * .08))
    return crop[pad:-pad, pad:-pad]


def answer_tick_score(crop, dark_only=False, dark_height=48):
    """Look for light pencil diagonals while suppressing dark printed digits.

    This is deliberately conservative: a long rising stroke must start near the
    left edge of the answer cell. Digit edges and show-through are not ticks.
    Normalize scale so the same rules work for both scans and PDF renderings.
    """
    if crop is None or crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    target_height = dark_height if dark_only else 24
    gray = cv2.resize(gray, (max(8, round(gray.shape[1] * target_height / gray.shape[0])), target_height),
                      interpolation=cv2.INTER_AREA)
    kernel = 2 * (target_height * 7 // 24) + 1
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((kernel, kernel), np.uint8))
    contrast = cv2.subtract(background, gray)
    # Dark ticks can overlap printed answers too. Unlike a digit stroke, their
    # rising arm spans most of the answer cell, starting at its left edge.
    dark_lines = cv2.HoughLinesP(np.uint8(contrast > 65) * 255, 1, np.pi / 180,
                                  threshold=5, minLineLength=4, maxLineGap=2)
    dark_tick = 0.0
    if dark_lines is not None:
        for x1, y1, x2, y2 in np.asarray(dark_lines).reshape(-1, 4):
            if x1 > x2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            dx, dy = x2 - x1, y2 - y1
            if (dark_only and dx > .35 * gray.shape[1] and -2.5 < dy / dx < -.2
                    and x1 < .60 * gray.shape[1] and y1 > .72 * gray.shape[0]):
                for a, b, c, d in np.asarray(dark_lines).reshape(-1, 4):
                    if a > c:
                        a, b, c, d = c, d, a, b
                    if (c - a >= 2 and d - b >= 2 and a < .30 * gray.shape[1]
                            and np.hypot(c - x1, d - y1) < 6):
                        dark_tick = .45
    if dark_only:
        return dark_tick
    printed = cv2.dilate((contrast > 80).astype(np.uint8), np.ones((3, 3), np.uint8))
    pencil = np.uint8((contrast > 18) & (printed == 0)) * 255
    lines = cv2.HoughLinesP(pencil, 1, np.pi / 180, threshold=7,
                            minLineLength=9, maxLineGap=2)
    longest = 0.0
    if lines is not None:
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            if x1 > x2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            dx, dy = x2 - x1, y2 - y1
            if dx and -.9 < dy / dx < -.2 and x1 < .20 * gray.shape[1]:
                longest = max(longest, float(np.hypot(dx, dy)))
    pencil_tick = min(.8, .18 + longest / gray.shape[1] * .5) if longest >= 12.0 else 0.0
    return max(dark_tick, pencil_tick)


def tick_score(crop):
    """
    Return a rough tick-likelihood score and diagnostic values.

    Uses dark-pixel occupancy and diagonal line evidence. The narrow tick cell
    should be blank except for the handwritten tick; its printed border is
    excluded by crop padding.
    """
    if crop is None or crop.size == 0:
        return 0.0, {"dark_ratio": 0.0, "diag_ratio": 0.0}

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Adaptive threshold works better across uneven scans and shadows.
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 7
    )
    # Remove tiny isolated specks.
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    ink = binary > 0
    dark_ratio = float(np.mean(ink))

    # A tick typically has a diagonal stroke. Hough lines provide a weak signal,
    # not a hard requirement, because handwritten ticks vary.
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=max(5, min(gray.shape) // 3),
        minLineLength=max(4, min(gray.shape) // 4), maxLineGap=3
    )
    diag_ratio = 0.0
    if lines is not None:
        diagonals = 0

        # Normalize OpenCV output to rows of [x1, y1, x2, y2].
        normalized_lines = np.asarray(lines).reshape(-1, 4)

        for line in normalized_lines:
            x1, y1, x2, y2 = map(int, line)

            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            if dx > 0 and dy > 0 and 0.20 <= (dy / dx) <= 4.5:
                diagonals += 1

        diag_ratio = min(1.0, diagonals / 2.0)

    # Weighted score: dark ink is the main signal; diagonals help separate ticks
    # from faint specks. Thresholds are configurable on the command line.
    score = min(1.0, dark_ratio * 3.0 + diag_ratio * 0.18)
    return score, {"dark_ratio": dark_ratio, "diag_ratio": diag_ratio}


def process_page(image, page_number, args):
    h, w = image.shape[:2]
    layout = copy.deepcopy(DEFAULT_LAYOUT)
    if args.rows is not None:
        layout["row_count"] = args.rows
    if args.first_y is not None:
        layout["first_row_center_y"] = args.first_y
    if args.last_y is not None:
        layout["last_row_center_y"] = args.last_y
    if args.row_half_height is not None:
        layout["row_half_height"] = args.row_half_height

    # Optional x overrides: normalized fractions of page width.
    for label in ("A", "B", "C"):
        left = getattr(args, f"{label.lower()}_left")
        right = getattr(args, f"{label.lower()}_right")
        if left is not None:
            layout[label][0] = left
        if right is not None:
            layout[label][1] = right

    manual = getattr(args, "manual_layout", False) or any(
        getattr(args, name, None) is not None for name in
        ("rows", "first_y", "last_y", "row_half_height", "a_left", "a_right",
         "b_left", "b_right", "c_left", "c_right"))
    detected_rows = None if manual else detect_box_rows(image)
    count = len(detected_rows) if detected_rows is not None else int(layout["row_count"])
    if count < 1:
        raise ValueError("Row count must be at least 1")
    ys = np.linspace(layout["first_row_center_y"], layout["last_row_center_y"], count)

    results = []
    annotated = image.copy()
    for row_offset, yc in enumerate(ys):
        row_index = getattr(args, "start_question", 1) + row_offset
        scores = {}
        boxes = {}
        diagnostics = {}
        answer_marks = set()
        for option in ("A", "B", "C"):
            if detected_rows is not None:
                quad = detected_rows[row_offset][option]
                crop = box_crop(image, quad)
                rect = quad
            else:
                crop, rect = tick_cell_crop(
                    image, layout[option], float(yc), layout["row_half_height"],
                    layout["inner_x_padding"], layout["inner_y_padding"]
                )
            score, diag = tick_score(crop)
            if detected_rows is not None:
                answer_score = answer_tick_score(box_crop(image, quad, answer=True))
                if score < args.threshold:
                    extended = box_crop(image, quad, answer=True, extend=True)
                    answer_score = max(answer_score, *(answer_tick_score(
                        extended, dark_only=True, dark_height=size) for size in (24, 48)))
                if answer_score > score:
                    score = answer_score
                    answer_marks.add(option)
            scores[option] = score
            boxes[option] = rect
            diagnostics[option] = diag

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_option, best_score = ranked[0]
        second_score = ranked[1][1]
        # Mark uncertain if no clear mark, or if two options look similarly marked.
        if best_score < args.threshold:
            selected = ""
            status = "REVIEW - no clear tick"
        elif second_score >= max(.25, args.threshold):
            selected = ""
            status = "REVIEW - multiple marks"
        elif (best_score - second_score) < args.margin:
            selected = ""
            status = "REVIEW - ambiguous"
        else:
            selected = best_option
            status = "OK"

        results.append({
            "page": page_number,
            "question_number": row_index,
            "ticked_option": selected,
            "status": status,
            "score_A": round(scores["A"], 3),
            "score_B": round(scores["B"], 3),
            "score_C": round(scores["C"], 3),
        })

        # Visual diagnostic: green = detected; red = review; yellow = unselected boxes.
        for option, rect in boxes.items():
            if selected == option:
                color = (0, 180, 0)
            elif status.startswith("REVIEW"):
                color = (0, 0, 255)
            else:
                color = (0, 190, 255)
            if detected_rows is not None:
                outline = rect.copy()
                if option in answer_marks:
                    # Include the answer in the outline when the tick is there.
                    outline[0] -= 1.18 * (rect[1] - rect[0])
                    outline[3] -= 1.18 * (rect[2] - rect[3])
                cv2.polylines(annotated, [np.rint(outline).astype(np.int32)], True, color, 2)
            else:
                x1, y1, x2, y2 = rect
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        if detected_rows is not None:
            yc = np.mean([q[:, 1].mean() for q in detected_rows[row_offset].values()]) / h
        label = selected if selected else "?"
        cv2.putText(
            annotated, f"{row_index}:{label}", (int(0.04 * w), int(yc * h) + 5),
            cv2.FONT_HERSHEY_SIMPLEX, max(0.35, w / 2200), (0, 0, 255) if not selected else (0, 120, 0), 1, cv2.LINE_AA
        )

    return results, annotated


def main():
    parser = argparse.ArgumentParser(
        description="Detect handwritten ticks in A/B/C worksheet option boxes and save annotated images."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input image(s) or PDF(s), e.g. test*.jpeg")
    parser.add_argument("--out", type=Path, default=Path("detected_ticks.csv"), help="CSV results path")
    parser.add_argument("--xlsx", type=Path, default=Path("detected_ticks.xlsx"), help="Excel results path")
    parser.add_argument("--annotated-dir", type=Path, default=Path("annotated_pages"), help="Directory for diagnostic images")
    parser.add_argument("--dpi", type=int, default=250, help="PDF render DPI (default: 250)")
    parser.add_argument("--manual-layout", action="store_true", help="Use the old fixed grid instead of detecting box borders")
    parser.add_argument("--start-question", type=int, default=1, help="First printed question number (e.g. 31 for test2.jpeg)")
    parser.add_argument("--rows", type=int, default=None, help="Number of question rows per page (default: 34)")
    parser.add_argument("--first-y", type=float, default=None, help="First row center as page-height fraction, e.g. 0.0835")
    parser.add_argument("--last-y", type=float, default=None, help="Last row center as page-height fraction, e.g. 0.941")
    parser.add_argument("--row-half-height", type=float, default=None, help="Half-height around row center as page-height fraction")
    parser.add_argument("--threshold", type=float, default=0.12, help="Minimum tick score to accept (default: 0.12)")
    parser.add_argument("--margin", type=float, default=0.025, help="Required lead over second-best option (default: 0.025)")
    for label in ("a", "b", "c"):
        parser.add_argument(f"--{label}-left", type=float, default=None, help=f"{label.upper()} tick-cell left x fraction")
        parser.add_argument(f"--{label}-right", type=float, default=None, help=f"{label.upper()} tick-cell right x fraction")
    args = parser.parse_args()

    for path in args.inputs:
        if not path.is_file():
            parser.error(f"Input file does not exist: {path}")
    if not 0 <= args.threshold <= 1 or not 0 <= args.margin <= 1:
        parser.error("--threshold and --margin must be between 0 and 1")

    args.annotated_dir.mkdir(parents=True, exist_ok=True)
    all_results = []
    for file_index, path in enumerate(args.inputs, 1):
        page_args = copy.copy(args)
        for page_number, image in load_pages(path, args.dpi):
            results, annotated = process_page(image, page_number, page_args)
            for result in results:
                result["source"] = str(path)
            all_results.extend(results)
            prefix = f"{file_index:03d}_{path.stem}_" if len(args.inputs) > 1 else ""
            annotated_path = args.annotated_dir / f"{prefix}page_{page_number:03d}_annotated.png"
            if not cv2.imwrite(str(annotated_path), annotated):
                raise RuntimeError(f"Could not save annotated image: {annotated_path}")
            print(f"\n{path} — page {page_number}")
            print("Question  Option  Status")
            for result in results:
                print(f"{result['question_number']:>8}  {result['ticked_option'] or '-':^6}  {result['status']}")
            print(f"Annotated image: {annotated_path}")
            page_args.start_question += len(results)

    fields = ["source", "page", "question_number", "ticked_option", "status",
              "score_A", "score_B", "score_C"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_results)
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Detected ticks"
    sheet.append(fields)
    for result in all_results:
        sheet.append([result[field] for field in fields])
        if result["status"].startswith("REVIEW"):
            for cell in sheet[sheet.max_row]:
                cell.fill = PatternFill("solid", fgColor="FFF2CC")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(
            60, max(len(str(cell.value or "")) for cell in column) + 2)
    args.xlsx.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(args.xlsx)
    print(f"\nResults: {args.out} and {args.xlsx}")

    review_count = sum(1 for row in all_results if str(row["status"]).startswith("REVIEW"))
    print(f"Processed {len(all_results)} rows; {review_count} need manual review.")
    print("Tip: inspect the annotated images, especially rows marked with '?'.")


if __name__ == "__main__":
    main()
