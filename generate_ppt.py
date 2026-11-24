import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Design System Palette (Professional Engineering/AI Theme)
    COLOR_PRIMARY = RGBColor(15, 43, 62)      # Deep Navy/Teal
    COLOR_ACCENT = RGBColor(8, 125, 113)      # Orqentra Teal
    COLOR_BG = RGBColor(245, 248, 247)        # Light Slate/Mint Tint
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_DARK = RGBColor(30, 41, 59)         # Slate Dark Text
    COLOR_MUTED = RGBColor(100, 116, 139)     # Slate Muted Text
    COLOR_BORDER = RGBColor(226, 232, 240)    # Soft Gray Border
    COLOR_CARD_BG = RGBColor(255, 255, 255)
    COLOR_LIGHT_TEAL = RGBColor(238, 247, 244)
    COLOR_LIGHT_BLUE = RGBColor(239, 246, 255)

    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide, color=COLOR_BG):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="ORQENTRA · PHASE I REVIEW"):
        # Category label
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_right = tf_cat.margin_top = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_ACCENT
        p_cat.font.name = "Arial"

        # Main Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.6))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_right = tf_title.margin_top = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_PRIMARY
        p_title.font.name = "Arial"

        # Accent underline
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(1.5), Inches(0.04))
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_ACCENT
        line.line.fill.background()

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    # ==========================================
    # SLIDE 1: TITLE SLIDE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, RGBColor(15, 35, 48))

    # Decorative header element
    dec = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.9), Inches(0.6), Inches(0.06))
    dec.fill.solid()
    dec.fill.fore_color.rgb = COLOR_ACCENT
    dec.line.fill.background()

    # Title box
    tbox = s1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(2.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "ORQENTRA — MULTI-AGENT FRAMEWORK FOR AUTONOMOUS DIGITAL SERVICE AUTOMATION"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Arial"

    p2 = tf1.add_paragraph()
    p2.text = "Project Phase I Review"
    p2.font.size = Pt(18)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(56, 189, 168)
    p2.font.name = "Arial"
    p2.space_before = Pt(12)

    # Info cards container
    # Left Card: Students
    c_left = add_card(s1, Inches(0.8), Inches(3.8), Inches(5.6), Inches(2.7), RGBColor(24, 48, 64), None)
    tb_std = s1.shapes.add_textbox(Inches(1.1), Inches(4.0), Inches(5.0), Inches(2.3))
    tf_std = tb_std.text_frame
    tf_std.word_wrap = True

    p_s_hdr = tf_std.paragraphs[0]
    p_s_hdr.text = "SUBMITTED BY:"
    p_s_hdr.font.size = Pt(11)
    p_s_hdr.font.bold = True
    p_s_hdr.font.color.rgb = RGBColor(148, 163, 184)

    p_s1 = tf_std.add_paragraph()
    p_s1.text = "NIHILESH R  (Reg No: 922523243067)"
    p_s1.font.size = Pt(14)
    p_s1.font.bold = True
    p_s1.font.color.rgb = COLOR_WHITE
    p_s1.space_before = Pt(8)

    p_s2 = tf_std.add_paragraph()
    p_s2.text = "NAVEEN P  (Reg No: 922523243064)"
    p_s2.font.size = Pt(14)
    p_s2.font.bold = True
    p_s2.font.color.rgb = COLOR_WHITE
    p_s2.space_before = Pt(6)

    p_deg = tf_std.add_paragraph()
    p_deg.text = "Bachelor of Technology in Artificial Intelligence & Data Science"
    p_deg.font.size = Pt(11)
    p_deg.font.color.rgb = RGBColor(203, 213, 225)
    p_deg.space_before = Pt(10)

    # Right Card: Guide & Institution
    c_right = add_card(s1, Inches(6.8), Inches(3.8), Inches(5.7), Inches(2.7), RGBColor(24, 48, 64), None)
    tb_guide = s1.shapes.add_textbox(Inches(7.1), Inches(4.0), Inches(5.1), Inches(2.3))
    tf_guide = tb_guide.text_frame
    tf_guide.word_wrap = True

    p_g_hdr = tf_guide.paragraphs[0]
    p_g_hdr.text = "PROJECT SUPERVISOR / GUIDE:"
    p_g_hdr.font.size = Pt(11)
    p_g_hdr.font.bold = True
    p_g_hdr.font.color.rgb = RGBColor(148, 163, 184)

    p_g_name = tf_guide.add_paragraph()
    p_g_name.text = "Mr. V. VELUSAMY, M.E."
    p_g_name.font.size = Pt(14)
    p_g_name.font.bold = True
    p_g_name.font.color.rgb = COLOR_WHITE
    p_g_name.space_before = Pt(8)

    p_g_desig = tf_guide.add_paragraph()
    p_g_desig.text = "Assistant Professor, Dept. of AI & Data Science"
    p_g_desig.font.size = Pt(11)
    p_g_desig.font.color.rgb = RGBColor(203, 213, 225)

    p_inst = tf_guide.add_paragraph()
    p_inst.text = "V.S.B. Engineering College, Karur - 639111\n(An Autonomous Institution · Affiliated to Anna University, Chennai)\nAcademic Year 2026–2027"
    p_inst.font.size = Pt(10)
    p_inst.font.color.rgb = RGBColor(148, 163, 184)
    p_inst.space_before = Pt(8)

    # ==========================================
    # SLIDE 2: AGENDA
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "Presentation Agenda", "TABLE OF CONTENTS")

    agenda_items = [
        ("01", "Abstract & Keywords"),
        ("02", "Problem Statement & Motivation"),
        ("03", "Project Objectives"),
        ("04", "Literature Survey & Research Gap"),
        ("05", "Existing vs Proposed System"),
        ("06", "System Architecture & Modules"),
        ("07", "Technology Stack & Requirements"),
        ("08", "Methodology & Implementation"),
        ("09", "Work Completed in Phase I"),
        ("10", "Project Timeline & Schedule"),
        ("11", "Expected Outcomes & Phase II Plan"),
        ("12", "References"),
    ]

    for idx, (num, text) in enumerate(agenda_items):
        col = idx // 6
        row = idx % 6
        left = Inches(1.0 + col * 5.8)
        top = Inches(1.7 + row * 0.9)
        w = Inches(5.3)
        h = Inches(0.75)

        card = add_card(s2, left, top, w, h, COLOR_WHITE, COLOR_BORDER)
        tb = s2.shapes.add_textbox(left + Inches(0.15), top + Inches(0.12), w - Inches(0.3), h - Inches(0.24))
        tf = tb.text_frame
        p = tf.paragraphs[0]
        p.text = f"{num}   {text}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = COLOR_DARK
        p.font.name = "Arial"

    # ==========================================
    # SLIDE 3: ABSTRACT
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Abstract", "EXECUTIVE SUMMARY")

    # Main Abstract card
    add_card(s3, Inches(0.8), Inches(1.6), Inches(11.7), Inches(3.6), COLOR_WHITE, COLOR_BORDER)
    tb_abs = s3.shapes.add_textbox(Inches(1.2), Inches(1.9), Inches(10.9), Inches(3.0))
    tf_abs = tb_abs.text_frame
    tf_abs.word_wrap = True

    p_a1 = tf_abs.paragraphs[0]
    p_a1.text = (
        "Orqentra is a multi-agent framework designed to automate routine, repetitive steps in digital public service "
        "applications—such as passport issuance and national scholarship portals—through an inspectable, chat-driven interface. "
        "An applicant describes an application goal in natural language; the system classifies intent, checks eligibility requirements, "
        "and extracts applicant facts from local encrypted documents. A browser automation component inspects portal controls and safely "
        "populates approved form fields using alias matching."
    )
    p_a1.font.size = Pt(13.5)
    p_a1.font.color.rgb = COLOR_DARK
    p_a1.font.name = "Arial"
    p_a1.space_after = Pt(10)

    p_a2 = tf_abs.add_paragraph()
    p_a2.text = (
        "Crucially, Orqentra enforces strict human-in-the-loop security boundaries: AI agents pause at verifiable checkpoints "
        "whenever sensitive actions (OTP, CAPTCHA, biometrics, fee payment, legal declarations) are reached, delegating execution directly "
        "to the human applicant. All applicant facts and extracted texts are encrypted at rest using per-user Fernet keys. "
        "In Phase 1, a fully functional prototype combining React 18, FastAPI, SQLite, and Playwright was implemented, with all 18 automated "
        "verification test suites passing successfully."
    )
    p_a2.font.size = Pt(13.5)
    p_a2.font.color.rgb = COLOR_DARK
    p_a2.font.name = "Arial"

    # Keywords card
    add_card(s3, Inches(0.8), Inches(5.5), Inches(11.7), Inches(1.4), COLOR_LIGHT_TEAL, COLOR_ACCENT)
    tb_kw = s3.shapes.add_textbox(Inches(1.2), Inches(5.7), Inches(10.9), Inches(1.0))
    tf_kw = tb_kw.text_frame
    tf_kw.word_wrap = True

    p_kw_title = tf_kw.paragraphs[0]
    p_kw_title.text = "KEYWORDS"
    p_kw_title.font.size = Pt(11)
    p_kw_title.font.bold = True
    p_kw_title.font.color.rgb = COLOR_ACCENT

    p_kw_list = tf_kw.add_paragraph()
    p_kw_list.text = "Multi-Agent System  ·  Digital Service Automation  ·  Human-in-the-Loop  ·  Document Intelligence  ·  Browser Automation  ·  Data Privacy"
    p_kw_list.font.size = Pt(13)
    p_kw_list.font.bold = True
    p_kw_list.font.color.rgb = COLOR_PRIMARY
    p_kw_list.space_before = Pt(6)

    # ==========================================
    # SLIDE 4: PROBLEM STATEMENT & MOTIVATION
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "Problem Statement & Motivation", "CONTEXT & NEED")

    # Card 1: Problem Statement
    add_card(s4, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.2), COLOR_WHITE, COLOR_BORDER)
    tb_p = s4.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.1), Inches(4.7))
    tf_p = tb_p.text_frame
    tf_p.word_wrap = True

    p_p_title = tf_p.paragraphs[0]
    p_p_title.text = "1. PROBLEM STATEMENT"
    p_p_title.font.size = Pt(13)
    p_p_title.font.bold = True
    p_p_title.font.color.rgb = COLOR_PRIMARY

    bullets_p = [
        ("The Core Issue", "Applying for government and public institutional services (passports, scholarships, certificates) requires tedious, redundant manual entry across complex, fragmented online portals."),
        ("Who is Affected", "Millions of citizens, students, and job applicants who regularly complete high-stakes online forms with varying terminology and strict documentation requirements."),
        ("Shortcomings of Current Solutions", "Traditional RPA scripts are brittle—breaking on minor HTML changes—and lack transparency. Conversely, fully autonomous LLM web agents pose severe risks by attempting to bypass CAPTCHA, leaking credentials, or fabricating submission confirmations without verified proof.")
    ]
    for b_title, b_desc in bullets_p:
        p_b = tf_p.add_paragraph()
        p_b.text = f"• {b_title}: {b_desc}"
        p_b.font.size = Pt(11.5)
        p_b.font.color.rgb = COLOR_DARK
        p_b.space_before = Pt(10)

    # Card 2: Motivation & Need
    add_card(s4, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2), COLOR_WHITE, COLOR_BORDER)
    tb_m = s4.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.7))
    tf_m = tb_m.text_frame
    tf_m.word_wrap = True

    p_m_title = tf_m.paragraphs[0]
    p_m_title.text = "2. MOTIVATION & NEED"
    p_m_title.font.size = Pt(13)
    p_m_title.font.bold = True
    p_m_title.font.color.rgb = COLOR_PRIMARY

    bullets_m = [
        ("Human-Centric Assistance", "Citizens need AI assistance for repetitive, mechanical form filling while retaining exclusive personal sovereignty over legal, financial, and identity verifications."),
        ("Real-World Demand", "Digital India and global e-governance initiatives process billions of citizen applications annually, demanding verifiable automation frameworks that reduce cognitive burden and submission errors."),
        ("Opportunity Addressed", "Orqentra introduces a localized, secure, observable multi-agent paradigm: combining document OCR intelligence with guarded browser execution and verifiable checkpoints.")
    ]
    for b_title, b_desc in bullets_m:
        p_b = tf_m.add_paragraph()
        p_b.text = f"• {b_title}: {b_desc}"
        p_b.font.size = Pt(11.5)
        p_b.font.color.rgb = COLOR_DARK
        p_b.space_before = Pt(10)

    # ==========================================
    # SLIDE 5: PROJECT OBJECTIVES
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Project Objectives", "CORE GOALS")

    objectives = [
        ("01", "Conversational Goal Intake & Planning", "Capture applicant goals in natural language through an accessible chat interface, dynamically classifying intent and synthesizing inspectable 7-stage execution plans based on service templates."),
        ("02", "Document Intelligence & Encrypted Memory", "Parse uploaded supporting documents (PDF, Word, PNG, JPEG) using OCR, auto-extracting key identity and academic attributes into a permanent local vault protected by per-user Fernet encryption."),
        ("03", "Guarded Browser Form Automation", "Inspect dynamic portal pages via Playwright, score and map visible form controls against verified profile facts using fuzzy alias matching, and fill approved ordinary fields with high precision."),
        ("04", "Human-in-the-Loop Security & Verification", "Enforce strict security boundaries: pause at verifiable checkpoints for OTP, CAPTCHA, biometrics, and fee payments, and validate final submission solely through official status evidence and receipts.")
    ]

    for idx, (num, title, desc) in enumerate(objectives):
        top = Inches(1.6 + idx * 1.35)
        add_card(s5, Inches(0.8), top, Inches(11.7), Inches(1.2), COLOR_WHITE, COLOR_BORDER)

        # Number circle / accent box
        num_card = add_card(s5, Inches(1.1), top + Inches(0.18), Inches(0.85), Inches(0.85), COLOR_LIGHT_TEAL, COLOR_ACCENT)
        tb_num = s5.shapes.add_textbox(Inches(1.1), top + Inches(0.32), Inches(0.85), Inches(0.5))
        p_n = tb_num.text_frame.paragraphs[0]
        p_n.text = num
        p_n.alignment = PP_ALIGN.CENTER
        p_n.font.size = Pt(15)
        p_n.font.bold = True
        p_n.font.color.rgb = COLOR_ACCENT

        # Text Content
        tb_c = s5.shapes.add_textbox(Inches(2.2), top + Inches(0.15), Inches(10.0), Inches(0.9))
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        p_t = tf_c.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY

        p_d = tf_c.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = COLOR_DARK
        p_d.space_before = Pt(3)

    # ==========================================
    # SLIDE 6: LITERATURE SURVEY
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Literature Survey", "RELATED WORK & RESEARCH GAP")

    # Table of Surveyed Literature
    table_shape = s6.shapes.add_table(5, 4, Inches(0.8), Inches(1.6), Inches(11.7), Inches(3.6))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(2.2)
    tbl.columns[1].width = Inches(2.5)
    tbl.columns[2].width = Inches(3.5)
    tbl.columns[3].width = Inches(3.5)

    headers = ["Author & Year", "Technique", "Findings", "Limitations"]
    for col_idx, h in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_PRIMARY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

    lit_data = [
        ("Wu et al. [1]\n(2024)", "AutoGen: Multi-Agent Conversation Framework", "Demonstrated that configurable conversational agent roles cooperate effectively on complex tasks.", "Lacks deterministic browser execution sync, state checkpoints, and human intervention boundaries."),
        ("Lewis et al. [2]\n(2020)", "Retrieval-Augmented Generation (RAG)", "Grounding language models with task-relevant external evidence substantially reduces hallucination.", "Designed for open-ended text retrieval rather than structured form attribute matching and validation."),
        ("Zhou et al. [3]\n(2024)", "WebArena: Autonomous Web Agent Benchmark", "Highlighted the critical distinction between clicking a web button and completing an authentic service.", "Focuses on benchmark evaluation rather than secure human-in-the-loop pause protocols and data privacy."),
        ("Smith [4]\n(2007)", "Tesseract OCR Engine Pipeline", "Multi-stage character recognition pipeline for extracting text directly from document images.", "Accuracy degrades sharply on low-resolution mobile photo captures, complex tables, and noisy layouts.")
    ]

    for row_idx, row in enumerate(lit_data, start=1):
        for col_idx, text in enumerate(row):
            cell = tbl.cell(row_idx, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_WHITE if row_idx % 2 == 1 else RGBColor(248, 250, 252)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = text
            p.font.size = Pt(9.5)
            p.font.color.rgb = COLOR_DARK

    # Research gap card
    add_card(s6, Inches(0.8), Inches(5.4), Inches(11.7), Inches(1.5), COLOR_LIGHT_BLUE, RGBColor(191, 219, 254))
    tb_gap = s6.shapes.add_textbox(Inches(1.1), Inches(5.55), Inches(11.1), Inches(1.2))
    tf_gap = tb_gap.text_frame
    tf_gap.word_wrap = True

    p_gap_hdr = tf_gap.paragraphs[0]
    p_gap_hdr.text = "RESEARCH GAP IDENTIFIED"
    p_gap_hdr.font.size = Pt(11)
    p_gap_hdr.font.bold = True
    p_gap_hdr.font.color.rgb = RGBColor(29, 78, 216)

    p_gap_desc = tf_gap.add_paragraph()
    p_gap_desc.text = (
        "Existing systems either rely on brittle, static scripts without intent understanding or utilize unconstrained LLM web agents "
        "that lack data privacy safeguards, reproducible state recovery, and verifiable human checkpoints. No unified architecture exists "
        "that bridges local encrypted applicant memory, dynamic DOM inspection, and mandatory human-in-the-loop security protocols."
    )
    p_gap_desc.font.size = Pt(11)
    p_gap_desc.font.color.rgb = COLOR_DARK
    p_gap_desc.space_before = Pt(4)

    # ==========================================
    # SLIDE 7: EXISTING VS PROPOSED SYSTEM
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Existing vs Proposed System", "SYSTEM COMPARISON")

    # Existing System Column
    add_card(s7, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3), COLOR_WHITE, COLOR_BORDER)
    tb_ex = s7.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.1), Inches(4.8))
    tf_ex = tb_ex.text_frame
    tf_ex.word_wrap = True

    p_ex_hdr = tf_ex.paragraphs[0]
    p_ex_hdr.text = "EXISTING SYSTEM (Current Approaches)"
    p_ex_hdr.font.size = Pt(13)
    p_ex_hdr.font.bold = True
    p_ex_hdr.font.color.rgb = RGBColor(185, 28, 28)

    ex_points = [
        ("Repetitive Data Entry", "Applicants must manually re-type identical personal, contact, and educational data across every single government portal."),
        ("Brittle Automation", "Fixed RPA macros rely on hardcoded DOM element IDs or coordinates, breaking completely upon minor portal UI redesigns."),
        ("Lack of Observability", "Absence of real-time progress logging makes it impossible to distinguish between network timeouts, portal crashes, or missing input."),
        ("Privacy & Security Hazards", "Uncontrolled scripts risk exposing confidential passwords, storing OTPs in insecure logs, or attempting to bypass legal verification gates."),
        ("Unconfirmed Submissions", "Existing tools often assume a form is finished simply because a button was clicked, without verifying official acknowledgement receipts.")
    ]
    for title, desc in ex_points:
        p = tf_ex.add_paragraph()
        p.text = f"• {title}: {desc}"
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        p.space_before = Pt(8)

    # Proposed System Column
    add_card(s7, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3), COLOR_WHITE, COLOR_ACCENT)
    tb_pr = s7.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.8))
    tf_pr = tb_pr.text_frame
    tf_pr.word_wrap = True

    p_pr_hdr = tf_pr.paragraphs[0]
    p_pr_hdr.text = "PROPOSED SYSTEM (Orqentra)"
    p_pr_hdr.font.size = Pt(13)
    p_pr_hdr.font.bold = True
    p_pr_hdr.font.color.rgb = COLOR_ACCENT

    pr_points = [
        ("Permanent Encrypted Vault", "Reusable applicant profile and document vault with Fernet AES encryption allows zero-retyping across all supported portals."),
        ("Adaptive Semantic Matcher", "Playwright-based DOM crawler utilizes normalized alias matching and sequence scoring to adapt to layout and label variations."),
        ("Observable 7-Stage State", "Transparent workflow monitor displays live step-by-step progress, time-stamped activity events, and portal screenshots."),
        ("Strict Human-in-the-Loop", "AI never solves CAPTCHAs, stores OTPs, or bypasses authorization; explicit checkpoints pause execution for personal verification."),
        ("Evidence-Based Verification", "Submissions are verified exclusively through official receipts (ARN/Application ID) captured directly from the portal.")
    ]
    for title, desc in pr_points:
        p = tf_pr.add_paragraph()
        p.text = f"• {title}: {desc}"
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        p.space_before = Pt(8)

    # ==========================================
    # SLIDE 8: SYSTEM ARCHITECTURE
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "System Architecture", "ARCHITECTURAL PIPELINE")

    # 5 Architectural Layers
    layers = [
        ("1. Presentation Layer", "React 18 & Vite Client", "Single-Page Chat UI, Document Vault, Profile Editor, History Dashboard, Metrics Telemetry"),
        ("2. API & Routing Layer", "FastAPI & Uvicorn", "RESTful typed endpoints, JWT session auth, CORS handling, asynchronous background task dispatch"),
        ("3. Agent Orchestration", "Multi-Agent Runtime", "Intent, Planner, Eligibility, Document, Browser, Human, Monitoring, and Memory Agents"),
        ("4. Browser Execution", "Playwright & Chromium", "Headless/Headed DOM crawler, fuzzy field matcher, popup handling, screenshot stream"),
        ("5. Persistence & Vault", "SQLite 3 & Cryptography", "Fernet encrypted profile tables, provenance tracking, audit logs, run history analytics")
    ]

    for idx, (layer_num, tech, desc) in enumerate(layers):
        top = Inches(1.6 + idx * 0.95)
        card = add_card(s8, Inches(0.8), top, Inches(11.7), Inches(0.85), COLOR_WHITE, COLOR_BORDER)

        tb = s8.shapes.add_textbox(Inches(1.0), top + Inches(0.1), Inches(11.3), Inches(0.65))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = f"{layer_num}  [{tech}]"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_PRIMARY

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = COLOR_MUTED
        p2.space_before = Pt(2)

    # Data Flow Description Card
    add_card(s8, Inches(0.8), Inches(6.45), Inches(11.7), Inches(0.8), COLOR_LIGHT_TEAL, COLOR_ACCENT)
    tb_df = s8.shapes.add_textbox(Inches(1.0), Inches(6.52), Inches(11.3), Inches(0.65))
    tf_df = tb_df.text_frame
    tf_df.word_wrap = True
    p_df = tf_df.paragraphs[0]
    p_df.text = "DATA FLOW: User Prompt → Intent/Planner Agent decomposes request → Memory Agent retrieves encrypted facts → Browser Agent navigates portal & fills matched fields → Human Agent handles OTP/Payment pause → Submission verified & archived."
    p_df.font.size = Pt(10.5)
    p_df.font.bold = True
    p_df.font.color.rgb = COLOR_PRIMARY

    # ==========================================
    # SLIDE 9: MODULES DESCRIPTION
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Modules Description", "FUNCTIONAL MODULES")

    modules = [
        ("Module 1: Request Intake & Planning", "Intent Agent & Planner Agent", "Interprets natural language application goals from chat, classifies the service category (passport, scholarship, license), and compiles an inspectable 7-stage execution workflow from reusable service templates."),
        ("Module 2: Document Intelligence & Vault", "Document Agent & Eligibility Agent", "Performs file validation and text extraction across PDFs, DOCX, and images (OCR), classifies document types, verifies applicant eligibility criteria, and encrypts profile facts into persistent local memory."),
        ("Module 3: Guarded Browser Execution", "Browser Automation Agent (Playwright)", "Inspects live portal DOM elements, normalizes form labels, computes fuzzy alias similarity scores, rejects sensitive password/payment fields, and populates non-sensitive form inputs automatically."),
        ("Module 4: Verification Checkpoints & Monitor", "Human Agent & Monitoring Agent", "Enforces non-bypassable human-in-the-loop pauses for OTPs, CAPTCHAs, and payments, detects workflow timeouts or stalls, enables checkpoint resumption, and archives verified submission receipts.")
    ]

    for idx, (m_title, m_agents, m_desc) in enumerate(modules):
        col = idx % 2
        row = idx // 2
        left = Inches(0.8 + col * 5.95)
        top = Inches(1.6 + row * 2.7)
        w = Inches(5.75)
        h = Inches(2.5)

        add_card(s9, left, top, w, h, COLOR_WHITE, COLOR_BORDER)

        tb = s9.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), w - Inches(0.5), h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p_t = tf.paragraphs[0]
        p_t.text = m_title
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY

        p_ag = tf.add_paragraph()
        p_ag.text = f"Sub-Agents: {m_agents}"
        p_ag.font.size = Pt(10.5)
        p_ag.font.bold = True
        p_ag.font.color.rgb = COLOR_ACCENT
        p_ag.space_before = Pt(3)

        p_d = tf.add_paragraph()
        p_d.text = m_desc
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = COLOR_DARK
        p_d.space_before = Pt(8)

    # ==========================================
    # SLIDE 10: TECHNOLOGY STACK & REQUIREMENTS
    # ==========================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "Technology Stack & Requirements", "SPECIFICATIONS")

    tech_sections = [
        ("1. HARDWARE REQUIREMENTS", [
            "Processor: Multi-core Intel Core i5 / AMD Ryzen 5 or higher",
            "RAM: Minimum 8 GB (16 GB recommended for concurrent browser instances)",
            "Storage: 20 GB available SSD space (Chromium binaries, SQLite, and vaults)",
            "Display: 1280 × 720 minimum screen resolution for dashboard review",
            "Network: Active broadband connection for live portal navigation"
        ]),
        ("2. SOFTWARE REQUIREMENTS", [
            "Operating System: Windows 10/11, Ubuntu 22.04 LTS, or macOS",
            "API Runtime: Python 3.11+ with FastAPI, Uvicorn ASGI, and Pydantic v2",
            "Web Client: Node.js 18+, React 18, Vite 5, Modern Vanilla CSS3",
            "Database: SQLite 3 relational store with WAL journal mode",
            "Encryption: Fernet symmetric encryption (PBKDF2-HMAC-SHA256)"
        ]),
        ("3. TOOLS & TECHNOLOGIES", [
            "Browser Automation: Microsoft Playwright for Python (Chromium engine)",
            "Document Parsers: pypdf (PDF parsing), python-docx (Word documents)",
            "OCR Processing: Tesseract OCR Engine & Pillow (PIL) image pipeline",
            "Testing & CI: Pytest test runner (18 automated tests passing)",
            "Authentication: Bcrypt (password hashing) & python-jose (JWT tokens)"
        ])
    ]

    for idx, (sec_title, items) in enumerate(tech_sections):
        left = Inches(0.8 + idx * 3.95)
        top = Inches(1.6)
        w = Inches(3.8)
        h = Inches(5.3)

        add_card(s10, left, top, w, h, COLOR_WHITE, COLOR_BORDER)

        tb = s10.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), w - Inches(0.4), h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p_t = tf.paragraphs[0]
        p_t.text = sec_title
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY

        for itm in items:
            p = tf.add_paragraph()
            p.text = f"• {itm}"
            p.font.size = Pt(10.5)
            p.font.color.rgb = COLOR_DARK
            p.space_before = Pt(8)

    # ==========================================
    # SLIDE 11: METHODOLOGY & WORKFLOW
    # ==========================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "Methodology & Workflow", "DEVELOPMENT PROCESS")

    stages = [
        ("Analysis", "Studied citizen application journeys across Passport Seva & National Scholarship portals. Identified friction points, repetitive fields, and security-critical verification checkpoints."),
        ("Design", "Architected a decoupled multi-agent pipeline separating presentation, orchestration, browser automation, and local encrypted memory. Established strict human-in-the-loop security protocols."),
        ("Develop", "Implemented FastAPI asynchronous endpoints, Playwright DOM crawler with fuzzy label matching, document OCR pipeline, and responsive React chat & dashboard interface."),
        ("Test", "Executed rigorous Pytest unit test suites (18 tests passing), covering host allowlisting, field scoring, credential protection, mock portal flows, and checkpoint recovery."),
        ("Deploy", "Configured local ASGI server deployment with live client-server communication, production Vite bundling, and local SQLite data persistence.")
    ]

    for idx, (st_name, st_desc) in enumerate(stages):
        top = Inches(1.6 + idx * 0.95)
        add_card(s11, Inches(0.8), top, Inches(11.7), Inches(0.85), COLOR_WHITE, COLOR_BORDER)

        tb = s11.shapes.add_textbox(Inches(1.0), top + Inches(0.1), Inches(11.3), Inches(0.65))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = f"Step {idx+1}: {st_name}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_PRIMARY

        p2 = tf.add_paragraph()
        p2.text = st_desc
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = COLOR_DARK
        p2.space_before = Pt(2)

    # Process Model Banner
    add_card(s11, Inches(0.8), Inches(6.45), Inches(11.7), Inches(0.8), COLOR_LIGHT_BLUE, RGBColor(191, 219, 254))
    tb_pm = s11.shapes.add_textbox(Inches(1.0), Inches(6.52), Inches(11.3), Inches(0.65))
    tf_pm = tb_pm.text_frame
    tf_pm.word_wrap = True
    p_pm = tf_pm.paragraphs[0]
    p_pm.text = "PROCESS MODEL: Iterative & Incremental Engineering Model — selected to permit continuous refinement of agent coordination, gradual expansion of portal adapters, and controlled validation against mock test environments."
    p_pm.font.size = Pt(10)
    p_pm.font.bold = True
    p_pm.font.color.rgb = COLOR_PRIMARY

    # ==========================================
    # SLIDE 12: WORK COMPLETED IN PHASE I
    # ==========================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12)
    add_header(s12, "Work Completed in Phase I", "MILESTONES ACHIEVED")

    tasks = [
        ("Literature Survey & Domain Requirement Analysis", 100),
        ("React 18 Frontend UI (Chat, Vault, Profile, History, Metrics)", 100),
        ("FastAPI Backend & Multi-Agent Orchestration Layer", 100),
        ("Local Document Intelligence, OCR & Fernet Encrypted Vault", 100),
        ("Playwright Form Inspection & Controlled Mock Test Portals", 100),
        ("Checkpoint State Recovery & Audit Verification Test Suite", 100),
        ("Expanded Live Multi-Portal Connectors (Phase II Target)", 40)
    ]

    for idx, (t_name, pct) in enumerate(tasks):
        top = Inches(1.6 + idx * 0.75)
        # Background bar container
        add_card(s12, Inches(0.8), top, Inches(11.7), Inches(0.68), COLOR_WHITE, COLOR_BORDER)

        # Text label
        tb_lbl = s12.shapes.add_textbox(Inches(1.0), top + Inches(0.08), Inches(7.5), Inches(0.5))
        tf_lbl = tb_lbl.text_frame
        p_l = tf_lbl.paragraphs[0]
        p_l.text = t_name
        p_l.font.size = Pt(11)
        p_l.font.bold = True
        p_l.font.color.rgb = COLOR_DARK

        # Percentage text
        tb_pct = s12.shapes.add_textbox(Inches(8.5), top + Inches(0.08), Inches(1.0), Inches(0.5))
        p_p = tb_pct.text_frame.paragraphs[0]
        p_p.text = f"{pct}%"
        p_p.alignment = PP_ALIGN.RIGHT
        p_p.font.size = Pt(11)
        p_p.font.bold = True
        p_p.font.color.rgb = COLOR_ACCENT if pct == 100 else COLOR_PRIMARY

        # Progress bar background
        bar_bg = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.7), top + Inches(0.22), Inches(2.5), Inches(0.22))
        bar_bg.fill.solid()
        bar_bg.fill.fore_color.rgb = RGBColor(226, 232, 240)
        bar_bg.line.fill.background()

        # Progress bar fill
        fill_w = Inches(2.5 * (pct / 100.0))
        if fill_w > 0:
            bar_fill = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.7), top + Inches(0.22), fill_w, Inches(0.22))
            bar_fill.fill.solid()
            bar_fill.fill.fore_color.rgb = COLOR_ACCENT if pct == 100 else RGBColor(59, 130, 246)
            bar_fill.line.fill.background()

    # Note
    tb_nt = s12.shapes.add_textbox(Inches(0.8), Inches(6.85), Inches(11.7), Inches(0.5))
    p_nt = tb_nt.text_frame.paragraphs[0]
    p_nt.text = "Summary: All core Phase-1 deliverables completed, 18 automated backend tests passed, and frontend production bundle successfully verified."
    p_nt.font.size = Pt(10.5)
    p_nt.font.bold = True
    p_nt.font.color.rgb = COLOR_PRIMARY

    # ==========================================
    # SLIDE 13: PROJECT TIMELINE
    # ==========================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13)
    add_header(s13, "Project Timeline", "SCHEDULE & MILESTONES")

    # Table for Gantt Schedule
    t_timeline = s13.shapes.add_table(7, 9, Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.1))
    tbl_t = t_timeline.table

    tbl_t.columns[0].width = Inches(3.7)
    for c in range(1, 9):
        tbl_t.columns[c].width = Inches(1.0)

    t_headers = ["Project Activity", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
    for c_idx, h in enumerate(t_headers):
        cell = tbl_t.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_PRIMARY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

    activities = [
        ("Literature Survey & Problem Formulation", [1, 2], "Phase I"),
        ("Requirement Analysis & Architecture Design", [2, 3], "Phase I"),
        ("Core Module Implementation (Agents, Vault, UI)", [3, 4], "Phase I"),
        ("Phase I Testing, Mock Portals & Documentation", [4], "Phase I"),
        ("Durable Task Queue & Live Portal Adapters", [5, 6], "Phase II"),
        ("Vector Memory Embedding & Comprehensive Evaluation", [6, 7, 8], "Phase II"),
    ]

    for r_idx, (act_name, months, phase) in enumerate(activities, start=1):
        cell_lbl = tbl_t.cell(r_idx, 0)
        cell_lbl.fill.solid()
        cell_lbl.fill.fore_color.rgb = COLOR_WHITE if r_idx % 2 == 1 else RGBColor(248, 250, 252)
        cell_lbl.vertical_anchor = MSO_ANCHOR.MIDDLE
        p_l = cell_lbl.text_frame.paragraphs[0]
        p_l.text = f"{act_name} ({phase})"
        p_l.font.size = Pt(9.5)
        p_l.font.bold = True
        p_l.font.color.rgb = COLOR_DARK

        for m_idx in range(1, 9):
            cell_m = tbl_t.cell(r_idx, m_idx)
            cell_m.fill.solid()
            cell_m.vertical_anchor = MSO_ANCHOR.MIDDLE
            p_m = cell_m.text_frame.paragraphs[0]
            if m_idx in months:
                cell_m.fill.fore_color.rgb = COLOR_ACCENT if phase == "Phase I" else RGBColor(59, 130, 246)
                p_m.text = "✓" if phase == "Phase I" else "Plan"
                p_m.alignment = PP_ALIGN.CENTER
                p_m.font.size = Pt(10)
                p_m.font.bold = True
                p_m.font.color.rgb = COLOR_WHITE
            else:
                cell_m.fill.fore_color.rgb = COLOR_WHITE if r_idx % 2 == 1 else RGBColor(248, 250, 252)
                p_m.text = ""

    # ==========================================
    # SLIDE 14: EXPECTED OUTCOMES & PHASE II PLAN
    # ==========================================
    s14 = prs.slides.add_slide(blank_layout)
    set_slide_background(s14)
    add_header(s14, "Expected Outcomes & Phase II Plan", "FUTURE SCOPE")

    # Card 1: Expected Outcomes
    add_card(s14, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3), COLOR_WHITE, COLOR_BORDER)
    tb_eo = s14.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.1), Inches(4.8))
    tf_eo = tb_eo.text_frame
    tf_eo.word_wrap = True

    p_eo_hdr = tf_eo.paragraphs[0]
    p_eo_hdr.text = "1. EXPECTED OUTCOMES"
    p_eo_hdr.font.size = Pt(13)
    p_eo_hdr.font.bold = True
    p_eo_hdr.font.color.rgb = COLOR_PRIMARY

    outcomes = [
        ("Substantial Time Reduction", "Reduces average citizen application completion time by 60%–75% by automating repetitive form navigation and field mapping."),
        ("Zero Sensitive Data Leakage", "Guarantees zero storage or leakage of passwords, OTPs, or biometric templates into persistent chat logs or third-party LLMs."),
        ("Adaptive Layout Resilience", "Maintains high form-filling accuracy across changing portal versions through normalized semantic alias scoring."),
        ("Verifiable Proof of Submission", "Ensures that every recorded completion is backed by an authentic portal application reference number (ARN/Receipt).")
    ]
    for title, desc in outcomes:
        p = tf_eo.add_paragraph()
        p.text = f"• {title}: {desc}"
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        p.space_before = Pt(8)

    # Card 2: Phase II Plan
    add_card(s14, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3), COLOR_WHITE, COLOR_BORDER)
    tb_p2 = s14.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.8))
    tf_p2 = tb_p2.text_frame
    tf_p2.word_wrap = True

    p_p2_hdr = tf_p2.paragraphs[0]
    p_p2_hdr.text = "2. PHASE II DEVELOPMENT PLAN"
    p_p2_hdr.font.size = Pt(13)
    p_p2_hdr.font.bold = True
    p_p2_hdr.font.color.rgb = COLOR_PRIMARY

    phase2_tasks = [
        ("Durable Shared Task Queue", "Migrate from in-process asynchronous scheduling to a Celery/Redis queue for fault-tolerant background execution and auto-retry."),
        ("Local Vector Memory & Embedding RAG", "Upgrade lexical keyword ranking to dense local embedding retrievers (e.g., ChromaDB / SentenceTransformers) for richer semantic understanding."),
        ("Expanded Live Portal Adapters", "Build and validate connectors for additional e-governance services including state driving licenses, PAN card issuance, and voter IDs."),
        ("Controlled Experimental Benchmark", "Conduct rigorous empirical evaluations measuring precision, recall, execution time, and user intervention frequency across diverse test cohorts.")
    ]
    for title, desc in phase2_tasks:
        p = tf_p2.add_paragraph()
        p.text = f"• {title}: {desc}"
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        p.space_before = Pt(8)

    # ==========================================
    # SLIDE 15: REFERENCES
    # ==========================================
    s15 = prs.slides.add_slide(blank_layout)
    set_slide_background(s15)
    add_header(s15, "References", "BIBLIOGRAPHY & CITATIONS")

    add_card(s15, Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.3), COLOR_WHITE, COLOR_BORDER)
    tb_ref = s15.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(11.1), Inches(4.8))
    tf_ref = tb_ref.text_frame
    tf_ref.word_wrap = True

    refs = [
        ("[1]", "Q. Wu, G. Bansal, J. Zhang, Y. Wu, B. Li, N. Wang, and H. Wang, “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,” in Conference on Language Modeling (COLM), 2024. arXiv:2308.08155."),
        ("[2]", "P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-t. Yih, T. Rocktäschel, et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” in Advances in Neural Information Processing Systems (NeurIPS), vol. 33, pp. 9459–9474, 2020."),
        ("[3]", "S. Zhou, F. F. Xu, H. Zhu, X. Zhou, R. Lo, A. Sridhar, X. Yuan, D. Bisk, D. Fried, and G. Neubig, “WebArena: A Realistic Web Environment for Building Autonomous Agents,” in International Conference on Learning Representations (ICLR), 2024. arXiv:2307.13854."),
        ("[4]", "R. Smith, “An Overview of the Tesseract OCR Engine,” in Ninth International Conference on Document Analysis and Recognition (ICDAR), pp. 629–633, IEEE, 2007."),
        ("[5]", "N. R, N. P, and V. Velusamy, “Orqentra — Multi-Agent Framework for Autonomous Digital Service Automation,” Phase-1 Project Report, Department of Artificial Intelligence and Data Science, V.S.B. Engineering College, Anna University: Chennai, November 2026.")
    ]

    for idx, (tag, cit) in enumerate(refs):
        p = tf_ref.paragraphs[0] if idx == 0 else tf_ref.add_paragraph()
        p.text = f"{tag} {cit}"
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        p.font.name = "Arial"
        p.space_after = Pt(12)

    # ==========================================
    # SLIDE 16: THANK YOU
    # ==========================================
    s16 = prs.slides.add_slide(blank_layout)
    set_slide_background(s16, RGBColor(15, 35, 48))

    # Center card
    card_ty = add_card(s16, Inches(2.2), Inches(1.5), Inches(8.93), Inches(4.5), RGBColor(24, 48, 64), None)

    tb_ty = s16.shapes.add_textbox(Inches(2.5), Inches(1.9), Inches(8.33), Inches(3.7))
    tf_ty = tb_ty.text_frame
    tf_ty.word_wrap = True

    p_ty = tf_ty.paragraphs[0]
    p_ty.text = "THANK YOU!"
    p_ty.alignment = PP_ALIGN.CENTER
    p_ty.font.size = Pt(36)
    p_ty.font.bold = True
    p_ty.font.color.rgb = COLOR_WHITE
    p_ty.font.name = "Arial"

    p_qd = tf_ty.add_paragraph()
    p_qd.text = "Questions & Discussion"
    p_qd.alignment = PP_ALIGN.CENTER
    p_qd.font.size = Pt(20)
    p_qd.font.bold = True
    p_qd.font.color.rgb = RGBColor(56, 189, 168)
    p_qd.font.name = "Arial"
    p_qd.space_before = Pt(8)

    p_proj = tf_ty.add_paragraph()
    p_proj.text = "Project: ORQENTRA — Multi-Agent Framework for Autonomous Digital Service Automation"
    p_proj.alignment = PP_ALIGN.CENTER
    p_proj.font.size = Pt(13)
    p_proj.font.bold = True
    p_proj.font.color.rgb = RGBColor(226, 232, 240)
    p_proj.space_before = Pt(20)

    p_team = tf_ty.add_paragraph()
    p_team.text = "Team Members: NIHILESH R (922523243067)  ·  NAVEEN P (922523243064)\nProject Supervisor: Mr. V. VELUSAMY, M.E., Assistant Professor"
    p_team.alignment = PP_ALIGN.CENTER
    p_team.font.size = Pt(12)
    p_team.font.color.rgb = RGBColor(148, 163, 184)
    p_team.space_before = Pt(10)

    p_col = tf_ty.add_paragraph()
    p_col.text = "Department of Artificial Intelligence and Data Science\nV.S.B. Engineering College, Karur"
    p_col.alignment = PP_ALIGN.CENTER
    p_col.font.size = Pt(11)
    p_col.font.color.rgb = RGBColor(148, 163, 184)
    p_col.space_before = Pt(8)

    # Save presentation
    output_path = r"c:\Users\Niki\orqentra\Orqentra_Phase_1_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    create_deck()
