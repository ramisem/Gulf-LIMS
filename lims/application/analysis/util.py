import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Tuple

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
from django.shortcuts import get_object_or_404
from matplotlib import transforms
from matplotlib.lines import Line2D

from analysis.models import MergeReportingDtl
from controllerapp.settings import REPORT_IMAGE_OUTPUT_PATH
from masterdata.models import BodySite, ReportImgPropInfo, BodySubSiteMap
from logutil.log import log

matplotlib.use("Agg")


def load_user_data_from_db(merge_reporting_id):
    log.info(f"merge_reporting_id ---> {merge_reporting_id}")
    # 0) Validate the merge ID exists
    get_object_or_404(
        MergeReportingDtl._meta.get_field('merge_reporting_id').related_model,
        merge_reporting_id=merge_reporting_id
    )

    # 1) Fetch all detail records for this merge
    all_dtls = (
        MergeReportingDtl.objects
        .filter(
            merge_reporting_id__merge_reporting_id=merge_reporting_id
        )
        .select_related(
            'report_option_id__root_sample_id',
            'analyte_id'
        )
    )

    # 2) Group them by the root_sample object
    dtls_by_sample = defaultdict(list)
    for d in all_dtls:
        sample = d.report_option_id.root_sample_id
        dtls_by_sample[sample].append(d)

    # 3) For each sample, pick out the Category analyte value (if any)
    data = []
    for sample, dtl_list in dtls_by_sample.items():
        part_no = sample.part_no or ""
        keyword = (
            f"{sample.body_site}, {sample.sub_site}"
            if sample.sub_site else sample.body_site or ""
        )

        # find the first analyte=='Category', if present
        category = ""
        for d in dtl_list:
            if d.analyte_id.analyte == "Category":
                category = d.analyte_value or ""
                break

        # only include if we at least have a part_no & keyword
        if part_no and keyword:
            data.append({
                "letter": part_no,
                "keyword": keyword,
                "category": category,
            })

    log.info(f"Sample Data --->{data}")
    return data


def get_coordinates_map_for_sites(keywords):
    # Extract unique body_site strings
    body_sites = {
        kw.split(",", 1)[0].strip()
        for kw in set(keywords) if kw
    }

    body_site_qs = BodySite.objects.filter(body_site__in=body_sites).exclude(base_image__isnull=True)
    subsites_qs = BodySubSiteMap.objects.filter(body_site__in=body_site_qs)

    ds_map = defaultdict(lambda: defaultdict(dict))

    for subsite in subsites_qs:
        if subsite.x_axis is None or subsite.y_axis is None:
            continue

        bs = subsite.body_site
        cat = bs.image_render_category or "default"
        base_img = bs.base_image.strip()
        label = f"{bs.body_site}, {subsite.sub_site}" if subsite.sub_site else bs.body_site

        ds_map[cat][base_img][label] = (subsite.x_axis, subsite.y_axis)

    log.info(f"Map coordinate details --->{ds_map}")
    return ds_map


def get_image_map_props():
    style_map = {}
    for e in ReportImgPropInfo.objects.all():
        if not (e.category and e.shape and e.color):
            continue
        style_map[e.category] = {
            "marker": e.shape,
            "color": e.color,
            "label": e.category
        }
    log.info(f"Image map properties --->{style_map}")
    return style_map


def plot_one_map(ax, img_path, coords_map, style_map, data,
                 spread=30, offset_px=6):
    """
    Draw the base image and scatter any sample points whose category
    has a defined style; skips any records with missing style or data.
    """
    # if there's nothing to plot, just show the image
    if not data or not style_map:
        with Image.open(img_path) as pil:
            ax.imshow(np.array(pil))
        ax.axis("off")
        return

    # load & display background
    with Image.open(img_path) as pil:
        img = np.array(pil)
    ax.imshow(img)
    ax.axis("off")

    pix_off = transforms.ScaledTranslation(
        offset_px / ax.figure.dpi, -offset_px / ax.figure.dpi,
        ax.figure.dpi_scale_trans
    )

    # group records by site keyword
    by_site = defaultdict(list)
    for record in data:
        key = record["keyword"]
        if key in coords_map:
            by_site[key].append(record)

    # plot each group
    for site, entries in by_site.items():
        x0, y0 = coords_map[site]
        offsets = (np.linspace(-spread / 2, spread / 2, len(entries))
                   if len(entries) > 1 else [0])
        for rec, dx in zip(entries, offsets):
            st = style_map.get(rec.get("category", ""))
            if not st:
                # no style defined for this category → skip
                continue

            x, y = x0 + dx, y0
            ax.scatter(x, y,
                       marker=st["marker"], s=200,
                       c=st["color"],
                       edgecolors="black",
                       linewidths=1)
            ax.text(x, y, rec["letter"],
                    transform=ax.transData + pix_off,
                    fontsize=10, fontweight="bold",
                    ha="left", va="top", color="black")


def load_user_data_with_diagnosis(merge_reporting_id):
    """
    Returns a list of dicts, one per sample:
      {
        letter: str,
        keyword: str,
        diagnosis: str,  # first Diagnosis analyte or ""
        category: str    # first Category analyte or ""
      }
    """
    log.info(f"merge_reporting_id ---> {merge_reporting_id}")
    # 0) Ensure the merge exists
    get_object_or_404(
        MergeReportingDtl._meta.get_field('merge_reporting_id').related_model,
        merge_reporting_id=merge_reporting_id
    )

    # 1) Fetch *all* analyte rows for this merge
    all_dtls = (
        MergeReportingDtl.objects
        .filter(merge_reporting_id__merge_reporting_id=merge_reporting_id)
        .select_related('report_option_id__root_sample_id', 'analyte_id')
    )

    # 2) Group by sample
    dtls_by_sample = defaultdict(list)
    for d in all_dtls:
        sample = d.report_option_id.root_sample_id
        dtls_by_sample[sample].append(d)

    # 3) Build output
    out = []
    for sample, dtl_list in dtls_by_sample.items():
        letter = sample.part_no or ""
        keyword = (
            f"{sample.body_site}, {sample.sub_site}"
            if sample.sub_site else sample.body_site or ""
        )

        if not (letter and keyword):
            # skip if either is missing
            continue

        # find Diagnosis & Category analytes (first match)
        diagnosis = ""
        category = ""
        for d in dtl_list:
            name = d.analyte_id.analyte
            if not diagnosis and name.lower() == "diagnosis":
                diagnosis = d.analyte_value or ""
            if not category and name.lower() == "category":
                category = d.analyte_value or ""
            # if both found, stop searching
            if diagnosis and category:
                break

        out.append({
            "letter": letter,
            "keyword": keyword,
            "diagnosis": diagnosis,
            "category": category,
        })

    log.info(f"Sample Data with diagnosis --->{out}")
    return out


def extract_plain_text(input_text: str) -> str:
    """
    Extract plain text from rich text HTML (e.g., Summernote input).
    Removes tags but preserves line breaks between paragraphs.
    If the input is just a plain text string, returns it stripped.
    """
    soup = BeautifulSoup(input_text, "html.parser")

    # collect text from each <p> or <div>
    blocks = [
        tag.get_text(separator=" ", strip=True)
        for tag in soup.find_all(["p", "div"])
        if tag.get_text(strip=True)
    ]

    if blocks:
        # if we found any <p> or <div>, join them with newlines
        return "\n".join(blocks)
    else:
        # no paragraphs/divs → fall back to the entire text content
        # this will handle pure text, or inline tags like <b>foo</b><i>bar</i>
        return soup.get_text(separator=" ", strip=True)


def parse_diagnosis(input_text: str) -> Tuple[str, str, str, float]:
    """
    Parses a diagnosis rich-text string and extracts:
    - disease name (before first comma)
    - Gleason score (e.g., "Gleason score 9")
    - Gleason pattern (e.g., "(4+5)")
    - Involvement percentage (e.g., 75.0)

    Example HTML:
    <p><b>Prostatic Adenocarcinoma, Gleason score 9 (4+5)</b></p>
    <p>Involving 75% of the cores</p>
    """
    log.info(f"Input for parse_diagnosis before extracting into plain text---> {input_text}")
    text = extract_plain_text(input_text)
    log.info(f"Input for parse_diagnosis after extracting into plain text---> {text}")
    # 1) disease before first comma
    disease = text.split(",", 1)[0].strip()

    # 2) gleason score
    m_score = re.search(r"Gleason score\s*(\d+)", text, re.IGNORECASE)
    gleason_score = f"Gleason score {m_score.group(1)}" if m_score else ""

    # 3) pattern in parentheses (e.g., (4+5))
    m_pat = re.search(r"\((\d+\+\d+)\)", text)
    pattern = f"({m_pat.group(1)})" if m_pat else ""

    # 4) percent after "Involving"
    m_pct = re.search(r"Involving\s*(\d+)%", text)
    pct = float(m_pct.group(1)) if m_pct else 0.0

    log.info(
        f"Output(s) for parse_diagnosis ---> disease: {disease}, gleason_score : {gleason_score}"
        f", pattern : {pattern},  pct : {pct}")
    return disease, gleason_score, pattern, pct


def annotate_core(ax, x: float, y: float,
                  part_no: str,
                  subsite_initials: str,
                  category: str,
                  diagnosis: str,
                  spread: int = 125,
                  bar_height: int = 25):
    """
    Draws, at (x,y):
      1) category (bold)
      2) gleason, pattern, bar, %
      3) part_no + subsite initials

    Special case: if subsite_initials is 'LSV' or 'RSV',
    then after plotting the pattern, reset y to the original
    y and shift x by +100 for the remainder.
    """
    disease, gleason, pattern, pct = parse_diagnosis(diagnosis)

    dy = 12
    cursor_y = y

    # Remember the originals for the special subsites
    orig_x, orig_y = x, y

    # 1) Category (if any)
    if category:
        ax.text(x, cursor_y, category,
                ha="center", va="top",
                fontsize=6, fontweight="bold",
                color="red")
        cursor_y += dy * 2.5

    # 2) Gleason score
    ax.text(x, cursor_y, gleason,
            ha="center", va="top",
            fontsize=6)
    cursor_y += dy * 1.5

    # 3) Gleason pattern
    ax.text(x, cursor_y, pattern,
            ha="center", va="top",
            fontsize=6)
    cursor_y += dy * 3

    # --- Special repositioning for LSV/RSV ---
    if subsite_initials in ("LSV", "RSV"):
        x = orig_x + 180
        cursor_y = orig_y

    # 4) Progress bar background
    bar_left = x - spread / 2
    bar_bottom = cursor_y
    ax.add_patch(mpatches.Rectangle(
        (bar_left, bar_bottom),
        spread, bar_height,
        linewidth=1, edgecolor="black", facecolor="#eee"
    ))

    # 5) Red fill
    ax.add_patch(mpatches.Rectangle(
        (bar_left, bar_bottom),
        spread * (pct / 100), bar_height,
        linewidth=0, facecolor="red"
    ))

    # 6) Percent text
    ax.text(x, bar_bottom + bar_height / 2,
            f"{int(pct)}%",
            ha="center", va="center",
            fontsize=6, fontweight="bold")
    cursor_y += bar_height + dy * 1.5

    # 7) Part No + Subsite Initials
    suffix = f". {subsite_initials}" if subsite_initials else ""
    ax.text(x, cursor_y, f"{part_no}{suffix}",
            ha="center", va="top",
            fontsize=6, fontweight="bold")


def generate_category1_map(merge_reporting_id, base_groups, output_dir):
    """
    Generate Category‑1 maps only for those base images that have
    at least one sample whose category has a style defined AND whose
    keyword maps into that image’s coords_map. Return [] if none apply.
    """
    data = load_user_data_from_db(merge_reporting_id)
    style_map = get_image_map_props()

    # 1) keep only records whose category has a style defined
    valid = [rec for rec in data if style_map.get(rec.get("category", "").strip())]
    if not valid:
        return []

    # 2) find which base_imgs actually have at least one valid point
    imgs_with_points = []
    for img_name, coords_map in base_groups.items():
        for rec in valid:
            if rec["keyword"] in coords_map:
                imgs_with_points.append(img_name)
                break

    # if none of the base images have points, bail out
    if not imgs_with_points:
        return []

    # 3) build a subplot only for those imgs
    n = len(imgs_with_points)
    fig, axes = plt.subplots(1, n, figsize=(8 * n, 6))
    if n == 1:
        axes = [axes]

    for ax, img_name in zip(axes, imgs_with_points):
        coords = base_groups[img_name]
        img_path = os.path.join("static", img_name)
        plot_one_map(ax, img_path, coords, style_map, valid)

    # shared horizontal legend
    handles = [
        Line2D([], [], marker=st["marker"], color="w",
               markerfacecolor=st["color"], markersize=12,
               label=st["label"], markeredgecolor="black")
        for st in style_map.values()
    ]
    fig.subplots_adjust(bottom=0.15)
    fig.legend(handles=handles,
               loc="lower center",
               ncol=len(handles),
               title="Map Legend",
               frameon=True)

    plt.tight_layout()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"img_{merge_reporting_id}_category1_{ts}.jpg"
    out_path = os.path.join(output_dir, fn)
    os.makedirs(output_dir, exist_ok=True)
    fig.savefig(out_path, format="jpeg", dpi=150)
    plt.close(fig)
    return [out_path]


def generate_category2_map(merge_reporting_id, base_groups, output_dir):
    """
    Only plot rows where:
      1) category is non‑empty, AND
      2) diagnosis (after stripping HTML) is non‑empty.

    Otherwise, return [] and never write a file.
    """
    # 1) Fetch all diagnosis+category data
    data = load_user_data_with_diagnosis(merge_reporting_id)

    # 2) Filter: require category AND non‑empty diagnosis
    valid = []
    for rec in data:
        cat_text = (rec.get("category") or "").strip()
        if not cat_text:
            # drop immediately if no category
            continue

        # normalize HTML → plain text
        diag_text = extract_plain_text(rec.get("diagnosis", ""))
        if not diag_text.strip():
            # drop if diagnosis is empty after stripping tags
            continue

        # keep the cleaned diagnosis for annotation
        rec["diagnosis"] = diag_text
        valid.append(rec)

    # nothing to plot?
    if not valid:
        return []

    # 3) Ensure at least one of these maps to a coordinate
    all_coords = {kw for coords in base_groups.values() for kw in coords}
    matched = [rec for rec in valid if rec["keyword"] in all_coords]
    if not matched:
        return []

    # 4) Proceed to plot only the matched, valid rows
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_paths = []

    for base_img, coords_map in base_groups.items():
        if not coords_map:
            continue

        img_path = os.path.join("static", base_img)
        with Image.open(img_path) as pil:
            arr = np.array(pil)
        h, w = arr.shape[:2]

        DPI = 150
        fig = plt.figure(figsize=(w / DPI, h / DPI), dpi=DPI)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(arr)
        ax.axis("off")

        for rec in matched:
            key = rec["keyword"]
            if key not in coords_map:
                continue

            # compute subsite initials
            parts = key.split(",", 1)
            subsite = parts[1].strip() if len(parts) == 2 else ""
            initials = "".join(w[0].upper() for w in subsite.split()) if subsite else ""

            x0, y0 = coords_map[key]
            annotate_core(
                ax,
                x0, y0,
                part_no=rec["letter"],
                subsite_initials=initials,
                category=rec.get("category", ""),
                diagnosis=rec["diagnosis"]
            )

        os.makedirs(output_dir, exist_ok=True)
        fn = f"img_{merge_reporting_id}_category2_{ts}.jpg"
        out = os.path.join(output_dir, fn)
        fig.savefig(out, format="jpeg", dpi=DPI, bbox_inches=None, pad_inches=0)
        plt.close(fig)
        out_paths.append(out)

    return out_paths


def merge_category_images(paths_by_category: dict, output_path: str, bg_color=(255, 255, 255)):
    # 1) Build each row image
    row_imgs = []
    for cat, paths in paths_by_category.items():
        imgs = [Image.open(p) for p in paths]
        widths, heights = zip(*(im.size for im in imgs))
        row_w, row_h = sum(widths), max(heights)
        row = Image.new("RGB", (row_w, row_h), bg_color)
        x = 0
        for im in imgs:
            row.paste(im, (x, 0))
            x += im.width
        row_imgs.append(row)

    # 2) Compute the final canvas size
    final_w = max(r.width for r in row_imgs)
    final_h = sum(r.height for r in row_imgs)
    final = Image.new("RGB", (final_w, final_h), bg_color)

    # 3) Paste each row centered
    y = 0
    for row in row_imgs:
        x_offset = (final_w - row.width) // 2
        final.paste(row, (x_offset, y))
        y += row.height

    # 4) Save
    final.save(output_path, "JPEG", quality=90)
    log.info(f"Final output path---> {output_path}")
    return output_path


def generate_image_map(
        merge_reporting_id,
        output_dir=REPORT_IMAGE_OUTPUT_PATH,
        merge_images: bool = False
):
    log.info(
        f"Parameters for generate_image_map ---> merge_reporting_id: {merge_reporting_id}, "
        f", output_dir : {output_dir},  merge_images : {merge_images} ")
    os.makedirs(output_dir, exist_ok=True)

    # 1) Load & group
    data = load_user_data_from_db(merge_reporting_id)
    keywords = [r["keyword"] for r in data]
    grouped = get_coordinates_map_for_sites(keywords)

    # 2) Sort categories
    def cat_key(cat_name):
        m = re.search(r"(\d+)$", cat_name)
        return int(m.group(1)) if m else float("inf")

    sorted_categories = sorted(grouped.keys(), key=cat_key)

    # 3) Generate per‑category maps, but only keep non‑empty results
    paths_by_cat = {}
    for category in sorted_categories:
        base_groups = grouped[category]
        fn = globals().get(f"generate_{category}_map")
        if not callable(fn):
            continue

        result = fn(merge_reporting_id, base_groups, output_dir)
        # skip categories with no output
        if not result:
            continue

        paths = result if isinstance(result, (list, tuple)) else [result]
        if paths:
            paths_by_cat[category] = paths

    # flatten all individual paths
    all_paths = [p for paths in paths_by_cat.values() for p in paths]

    # 4a) If not merging, just return them joined by semicolons
    if not merge_images:
        return ";".join(all_paths)

    # 4b) Otherwise, merge into one image
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"img_bodysubsite_{merge_reporting_id}_{ts}.jpg"
    final_path = os.path.join(output_dir, final_name)
    merge_category_images(paths_by_cat, final_path)

    # 5) Clean up the individual files
    for p in all_paths:
        try:
            os.remove(p)
        except OSError:
            pass

    log.info(f"Final image path---> {final_path}")
    return final_path
