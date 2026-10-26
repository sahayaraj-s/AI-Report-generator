"""
generate_gemini_analysis_pdf.py
Generates a comprehensive, publication-quality PDF report detailing the full
Gemini API integration audit and implementation roadmap for Skill Bay Academy.
"""
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# Palette
PRIMARY = colors.HexColor("#8B1D55")      # Deep Maroon
PRIMARY_LIGHT = colors.HexColor("#FDF2F7")
SECONDARY = colors.HexColor("#72398C")    # Purple
ACCENT = colors.HexColor("#DE4F73")       # Pink
DARK = colors.HexColor("#0F172A")         # Slate Dark
MUTED = colors.HexColor("#475569")        # Slate Muted
BORDER = colors.HexColor("#E2E8F0")       # Border Grey
BG_LIGHT = colors.HexColor("#F8FAFC")     # Background Grey
SUCCESS = colors.HexColor("#16A34A")      # Green
WARNING = colors.HexColor("#D97706")      # Amber
WHITE = colors.white

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        if self._pageNumber == 1:
            return  # Skip cover page
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED)
        
        # Header
        self.drawString(54, A4[1] - 36, "Skill Bay Academy · Gemini API Full Project Integration Analysis")
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(54, A4[1] - 42, A4[0] - 54, A4[1] - 42)
        
        # Footer
        self.line(54, 45, A4[0] - 54, 45)
        self.drawString(54, 32, "Confidential · Architectural Audit & Implementation Specification")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 54, 32, page_str)
        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=PRIMARY,
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=DARK,
        spaceAfter=6,
    )
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=4,
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=DARK,
    )
    tbl_hdr = ParagraphStyle(
        "TableHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=WHITE,
    )
    tbl_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=DARK,
    )
    tbl_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
    )
    badge_green = ParagraphStyle(
        "BadgeGreen",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
        textColor=SUCCESS,
    )
    badge_amber = ParagraphStyle(
        "BadgeAmber",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
        textColor=WARNING,
    )

    story = []

    # =========================================================================
    # COVER PAGE / HEADER
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("SKILL BAY ACADEMY · KAUVERY HOSPITAL CCDP", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Google Gemini API — Full Project Integration Analysis & Master Roadmap", title_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceAfter=15))

    meta_table_data = [
        [Paragraph("<b>Target System:</b>", body_style), Paragraph("AI Placement Analytics Platform (CCDP)", body_style),
         Paragraph("<b>Date:</b>", body_style), Paragraph("October 2026", body_style)],
        [Paragraph("<b>Architecture:</b>", body_style), Paragraph("FastAPI + React 19/Vite + Google GenAI", body_style),
         Paragraph("<b>Audit Status:</b>", body_style), Paragraph("<font color='#16A34A'><b>Active & Verified</b></font>", body_style)],
        [Paragraph("<b>Current Model:</b>", body_style), Paragraph("gemini-3.6-flash (Discovered via models.list)", body_style),
         Paragraph("<b>SDK Version:</b>", body_style), Paragraph("google-genai (Official SDK)", body_style)],
    ]
    meta_table = Table(meta_table_data, colWidths=[100, 150, 90, 140])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Executive Summary Box
    exec_summary_text = (
        "<b>Executive Summary:</b> This technical audit provides an exhaustive, code-level analysis of every location "
        "where the Google Gemini API is referenced, utilized, or required across both backend and frontend repositories. "
        "The project has an active, connected Gemini integration via the official <code>google-genai</code> SDK in "
        "<code>llm_manager.py</code>. However, the codebase exhibits <b>architectural fragmentation</b>: three legacy modules "
        "(<code>ai_service.py</code>, <code>chat_service.py</code>, <code>schema_detector.py</code>) continue to use raw, "
        "deprecated <code>httpx</code> REST calls with rigid API-key prefix guards (<code>startswith('AIza')</code>) that fail on "
        "newer Google keys. Furthermore, critical features—including on-demand student re-analysis, Excel batch narrative "
        "synthesis, and live executive report summaries—currently bypass Gemini with static placeholders. This specification "
        "outlines the exact remediation path to unify the entire application around a single, resilient GenAI core."
    )
    exec_table = Table([[Paragraph(exec_summary_text, body_style)]], colWidths=[480])
    exec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(exec_table)
    story.append(Spacer(1, 15))

    # =========================================================================
    # SECTION 1: COMPLETE GEMINI API USAGE MAP (CURRENT LOCATIONS)
    # =========================================================================
    story.append(Paragraph("1. Current Gemini API Implementation Map", h1_style))
    story.append(Paragraph(
        "The following table catalogues every occurrence of Google Gemini API references, SDK invocations, and environment "
        "variable hooks in the active codebase. Each occurrence is evaluated for operational necessity.", body_style
    ))

    curr_table_data = [
        [
            Paragraph("File Path", tbl_hdr),
            Paragraph("Lines", tbl_hdr),
            Paragraph("Code / Invocation", tbl_hdr),
            Paragraph("Functional Description", tbl_hdr),
            Paragraph("Necessity", tbl_hdr),
        ],
        [
            Paragraph("backend/app/services/<br/>llm_manager.py", tbl_cell_bold),
            Paragraph("24-26<br/>63-71<br/>503-542", tbl_cell),
            Paragraph("<code>genai.Client()</code><br/><code>client.chats.create()</code><br/><code>chat.send_message_stream()</code>", code_style),
            Paragraph("Official SDK client. Orchestrates streaming SSE, function-calling analytics tools, and multi-model fallback.", tbl_cell),
            Paragraph("CRITICAL<br/>(Core Engine)", badge_green),
        ],
        [
            Paragraph("backend/app/services/<br/>llm_manager.py", tbl_cell_bold),
            Paragraph("74-121", tbl_cell),
            Paragraph("<code>client.models.list()</code>", code_style),
            Paragraph("Dynamic model discovery at runtime. Filters retired models and caches active models for frontend dropdowns.", tbl_cell),
            Paragraph("REQUIRED", badge_green),
        ],
        [
            Paragraph("backend/app/routers/<br/>ai.py", tbl_cell_bold),
            Paragraph("54-65<br/>120-168", tbl_cell),
            Paragraph("<code>/api/ai/status</code><br/><code>/api/ai/models</code><br/><code>/api/ai/chat/stream</code>", code_style),
            Paragraph("FastAPI router exposing status, active model inventory, and SSE streaming to MiniChatbot and SkillBay AI.", tbl_cell),
            Paragraph("REQUIRED<br/>(API Surface)", badge_green),
        ],
        [
            Paragraph("backend/app/services/<br/>ai_service.py", tbl_cell_bold),
            Paragraph("123-145<br/>147-156", tbl_cell),
            Paragraph("<code>httpx.post(url)</code><br/><code>generativelanguage/v1beta</code>", code_style),
            Paragraph("Generates single-student AI summaries, 30-day plans, and certifications. Contains buggy <code>startswith('AIza')</code> check.", tbl_cell),
            Paragraph("REDUNDANT<br/>(Refactor to SDK)", badge_amber),
        ],
        [
            Paragraph("backend/app/services/<br/>chat_service.py", tbl_cell_bold),
            Paragraph("338-383", tbl_cell),
            Paragraph("<code>_gemini_grounded_chat()</code><br/><code>httpx.post()</code>", code_style),
            Paragraph("Legacy RAG query responder with manual HTTPX calls. Orphaned by <code>llm_manager.py</code> tool calling.", tbl_cell),
            Paragraph("DUPLICATE<br/>(Deprecate)", badge_amber),
        ],
        [
            Paragraph("backend/<br/>schema_detector.py", tbl_cell_bold),
            Paragraph("340-389", tbl_cell),
            Paragraph("<code>_ask_llm_for_schema()</code><br/><code>httpx.post()</code>", code_style),
            Paragraph("Calls LLM to infer table schema and score columns from Excel first 15 rows. Defaults to retired <code>gemini-1.5-flash</code>.", tbl_cell),
            Paragraph("REDUNDANT<br/>(Refactor to SDK)", badge_amber),
        ],
        [
            Paragraph("backend/app/<br/>config.py", tbl_cell_bold),
            Paragraph("15-24", tbl_cell),
            Paragraph("<code>gemini_api_key</code><br/><code>gemini_model_default</code>", code_style),
            Paragraph("Pydantic BaseSettings loading API keys, default models, timeout (20s), and model fallback sequence.", tbl_cell),
            Paragraph("CRITICAL<br/>(Config)", badge_green),
        ],
        [
            Paragraph("backend/app/routers/<br/>admin.py", tbl_cell_bold),
            Paragraph("63-64", tbl_cell),
            Paragraph("<code>gemini_model</code><br/><code>gemini_api_key_configured</code>", code_style),
            Paragraph("Reports active Gemini model and configuration status to the admin settings dashboard.", tbl_cell),
            Paragraph("REQUIRED", badge_green),
        ],
        [
            Paragraph("frontend/src/hooks/<br/>useAiChat.js", tbl_cell_bold),
            Paragraph("27-39<br/>196-265", tbl_cell),
            Paragraph("<code>/api/ai/chat/stream</code><br/>SSE event parser", code_style),
            Paragraph("Frontend client hook managing chat history, model selection, attachments, and real-time token streaming.", tbl_cell),
            Paragraph("CRITICAL<br/>(Frontend)", badge_green),
        ],
        [
            Paragraph("frontend/src/pages/<br/>SkillBayAI.jsx", tbl_cell_bold),
            Paragraph("106-110<br/>172-185", tbl_cell),
            Paragraph("Model selector dropdown<br/>Session sidebar", code_style),
            Paragraph("Dedicated full-screen AI chat page supporting model selection, session memory, and attachment parsing.", tbl_cell),
            Paragraph("REQUIRED", badge_green),
        ],
        [
            Paragraph("frontend/src/pages/<br/>UploadStudentData.jsx", tbl_cell_bold),
            Paragraph("95, 117<br/>814-830", tbl_cell),
            Paragraph("<code>reportModel</code><br/><code>EFFORT_LEVELS</code>", code_style),
            Paragraph("UI controls to select model and effort for instant PDF/Image export from uploaded session preview.", tbl_cell),
            Paragraph("REQUIRED<br/>(Unconnected)", badge_amber),
        ],
        [
            Paragraph("frontend/src/pages/<br/>StudentProfile.jsx", tbl_cell_bold),
            Paragraph("175-177", tbl_cell),
            Paragraph("<code>ai_source === 'gemini'</code>", code_style),
            Paragraph("Renders AI badge indicating whether student's narrative was generated via Gemini or local heuristics.", tbl_cell),
            Paragraph("REQUIRED", badge_green),
        ],
    ]

    curr_table = Table(curr_table_data, colWidths=[95, 45, 105, 160, 75])
    curr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(curr_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 2: ARCHITECTURAL ISSUES & DUPLICATES
    # =========================================================================
    story.append(Paragraph("2. Architectural Fragmentation & Duplicate Implementations", h1_style))
    story.append(Paragraph(
        "The audit revealed three critical architectural bottlenecks that must be resolved to ensure production stability:", body_style
    ))

    issues = [
        "<b>1. Dual API Calling Paradigms:</b> The system utilizes both the modern <code>google-genai</code> SDK "
        "(in <code>llm_manager.py</code>) and legacy direct <code>httpx.post()</code> REST requests (in <code>ai_service.py</code>, "
        "<code>chat_service.py</code>, and <code>schema_detector.py</code>). This causes maintenance fragmentation, conflicting timeouts, "
        "and inconsistent model resolution.",
        "<b>2. Fragile Key Prefix Validation:</b> Three legacy modules enforce <code>api_key.startswith('AIza')</code>. "
        "Google AI Studio now provisions valid production keys beginning with <code>AQ...</code>. Consequently, valid keys cause "
        "these modules to silently fail and drop into offline fallback, while <code>llm_manager.py</code> functions properly.",
        "<b>3. Retired Model Fallbacks:</b> References to <code>gemini-1.5-flash</code> persist in <code>schema_detector.py</code>, "
        "<code>reports.py</code>, and <code>render.yaml</code>. When invoked, these trigger HTTP 404 / 400 errors. "
        "All calls must route through <code>resolve_working_model()</code> with <code>gemini-3.6-flash</code> as default.",
        "<b>4. Orphaned Chat Engine:</b> <code>chat_service.py</code> contains an older grounded RAG implementation. "
        "The active router <code>ai.py</code> routes chat through <code>llm_manager.py</code> via tool calling. "
        "<code>chat_service.py</code>'s LLM route is dead code and should be removed.",
    ]
    for issue in issues:
        story.append(Paragraph(f"• {issue}", bullet_style))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 3: MISSING INTEGRATION POINTS (REQUIRED INTEGRATIONS)
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("3. Required Gemini API Integration Locations", h1_style))
    story.append(Paragraph(
        "The following five key operational workflows currently lack Gemini integration or rely on static placeholders. "
        "Each requires immediate implementation to unlock full platform capabilities:", body_style
    ))

    int_table_data = [
        [
            Paragraph("Workflow / Target File", tbl_hdr),
            Paragraph("Insertion Line", tbl_hdr),
            Paragraph("Required Code & Logic", tbl_hdr),
            Paragraph("Business Justification", tbl_hdr),
            Paragraph("Connection Module", tbl_hdr),
        ],
        [
            Paragraph("<b>A. Student Profile On-Demand Re-Analysis</b><br/>backend/app/routers/students.py", tbl_cell),
            Paragraph("After line 150", tbl_cell),
            Paragraph("<code>@router.post('/{id}/ai-analysis')</code><br/>Calls <code>llm_manager.generate_student_narrative()</code> with model selection.", code_style),
            Paragraph("Allows placement officers to regenerate tailored 30-day plans and roadmaps directly from the student profile.", tbl_cell),
            Paragraph("<code>app.services.<br/>llm_manager</code>", tbl_cell_bold),
        ],
        [
            Paragraph("<b>B. Upload Pipeline Batch Narrative Synthesis</b><br/>backend/app/routers/upload.py", tbl_cell),
            Paragraph("Lines 107-112 in <code>persist_consolidated_student</code>", tbl_cell),
            Paragraph("Replace hardcoded strings with async batch call or background task using <code>generate_ai_report()</code>.", code_style),
            Paragraph("Prevents uploaded cohorts from storing generic boilerplate roadmaps. Ensures unique Gemini evaluations.", tbl_cell),
            Paragraph("<code>app.services.<br/>llm_manager</code>", tbl_cell_bold),
        ],
        [
            Paragraph("<b>C. Live Cohort Executive Report Summary</b><br/>backend/app/routers/reports.py", tbl_cell),
            Paragraph("Lines 794-796 in <code>_build_live_report_pdf</code>", tbl_cell),
            Paragraph("Query Gemini for a 3-sentence executive cohort diagnosis and embed it into the generated PDF story.", code_style),
            Paragraph("Delivers instant, high-value AI commentary on batch strengths and Kauvery role readiness for executive leadership.", tbl_cell),
            Paragraph("<code>app.services.<br/>llm_manager</code>", tbl_cell_bold),
        ],
        [
            Paragraph("<b>D. Intelligent Role Fit Explainer</b><br/>backend/app/routers/jobs.py", tbl_cell),
            Paragraph("After line 150", tbl_cell),
            Paragraph("<code>@router.post('/roles/{id}/ai-explain')</code><br/>Takes student scores and returns clinical fit rationale.", code_style),
            Paragraph("Explains <i>why</i> a student is a 90% fit for a Kauvery unit and details remediation steps for gaps.", tbl_cell),
            Paragraph("<code>app.services.<br/>llm_manager</code>", tbl_cell_bold),
        ],
        [
            Paragraph("<b>E. Admin Model Switching & Connection Test</b><br/>backend/app/routers/admin.py", tbl_cell),
            Paragraph("Lines 86-137", tbl_cell),
            Paragraph("Persist <code>gemini_model</code> in DB/settings and add <code>POST /settings/test-ai</code> to verify keys.", code_style),
            Paragraph("Allows administrators to switch active Gemini models dynamically from the frontend settings screen.", tbl_cell),
            Paragraph("<code>app.config.settings</code><br/><code>llm_manager</code>", tbl_cell_bold),
        ],
    ]

    int_table = Table(int_table_data, colWidths=[110, 45, 125, 130, 70])
    int_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(int_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 4: RECOMMENDED FINAL ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("4. Recommended Unified GenAI Architecture", h1_style))
    story.append(Paragraph(
        "To achieve enterprise reliability, the platform should transition to a <b>Single Gateway Pattern</b> "
        "where all features consume Gemini via <code>llm_manager.py</code>:", body_style
    ))

    arch_box_text = (
        "<b>[ FRONTEND LAYER ]</b><br/>"
        "• <b>MiniChatbot & SkillBayAI</b> ──► SSE Streaming (<code>/api/ai/chat/stream</code>)<br/>"
        "• <b>Student Profile View</b> ──► On-Demand Analysis (<code>/api/students/{id}/ai-analysis</code>)<br/>"
        "• <b>Upload Workflow</b> ──► Live Session Export (<code>/api/reports/live/pdf</code> with AI summary)<br/>"
        "• <b>Settings Panel</b> ──► Model Switching & Key Health Check (<code>/api/admin/settings</code>)<br/>"
        "<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼ (JSON REST / SSE)<br/>"
        "<b>[ BACKEND UNIFIED LLM GATEWAY (llm_manager.py) ]</b><br/>"
        "• <b>Client Management:</b> Single <code>genai.Client</code> initialized from <code>settings.gemini_api_key</code><br/>"
        "• <b>Dynamic Discovery:</b> <code>models.list()</code> caches working models every 5 minutes<br/>"
        "• <b>Auto-Fallback Chain:</b> <code>gemini-3.6-flash</code> ➔ <code>gemini-3.5-flash-lite</code> ➔ <code>local offline</code><br/>"
        "• <b>Grounding Engine:</b> First-class read-only tool calling (Analytics, Cohort, Student Profile)<br/>"
        "• <b>Task Functions:</b> <code>generate_chat_turn()</code>, <code>generate_student_narrative()</code>, <code>generate_cohort_narrative()</code><br/>"
        "<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼ (HTTPS REST)<br/>"
        "<b>[ GOOGLE GEMINI CLOUD (Developer API v1beta) ]</b><br/>"
        "• Multimodal Vision (Inbound PDF/PNG) &bull; Structured JSON &bull; Tool Calling &bull; Fast Reasoning"
    )
    arch_table = Table([[Paragraph(arch_box_text, code_style)]], colWidths=[480])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 5: ENVIRONMENT VARIABLES & DEPLOYMENT MATRIX
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("5. Environment Variable Requirements & Cloud Matrix", h1_style))
    story.append(Paragraph(
        "The following matrix outlines all environment variables required across development, Render backend, "
        "and Vercel frontend environments:", body_style
    ))

    env_table_data = [
        [
            Paragraph("Variable Name", tbl_hdr),
            Paragraph("Target Service", tbl_hdr),
            Paragraph("Production Value / Example", tbl_hdr),
            Paragraph("Purpose & Description", tbl_hdr),
        ],
        [
            Paragraph("<code>GEMINI_API_KEY</code>", code_style),
            Paragraph("Backend (Render)", tbl_cell),
            Paragraph("<code>AIzaSy...</code> or <code>AQ...</code>", tbl_cell),
            Paragraph("Google AI Studio API key. Grants access to Gemini models.", tbl_cell),
        ],
        [
            Paragraph("<code>GEMINI_MODEL_DEFAULT</code>", code_style),
            Paragraph("Backend (Render)", tbl_cell),
            Paragraph("<code>gemini-3.6-flash</code>", tbl_cell),
            Paragraph("Primary model for chat, streaming, and student narrative generation.", tbl_cell),
        ],
        [
            Paragraph("<code>GEMINI_MODEL_FAST</code>", code_style),
            Paragraph("Backend (Render)", tbl_cell),
            Paragraph("<code>gemini-3.5-flash-lite</code>", tbl_cell),
            Paragraph("High-speed model used during high traffic or automated schema classification.", tbl_cell),
        ],
        [
            Paragraph("<code>GEMINI_MODEL_DEEP</code>", code_style),
            Paragraph("Backend (Render)", tbl_cell),
            Paragraph("<code>gemini-3.8-flash</code>", tbl_cell),
            Paragraph("Deep reasoning model for executive reports and comprehensive evaluations.", tbl_cell),
        ],
        [
            Paragraph("<code>GEMINI_FALLBACKS</code>", code_style),
            Paragraph("Backend (Render)", tbl_cell),
            Paragraph("<code>gemini-3.6-flash,gemini-3.5-flash</code>", tbl_cell),
            Paragraph("Comma-separated fallback chain invoked automatically on 503 or 404.", tbl_cell),
        ],
        [
            Paragraph("<code>GEMINI_TIMEOUT_SECONDS</code>", code_style),
            Paragraph("Backend (Render)", tbl_cell),
            Paragraph("<code>20.0</code>", tbl_cell),
            Paragraph("Maximum duration before falling back to local deterministic response.", tbl_cell),
        ],
        [
            Paragraph("<code>VITE_API_URL</code>", code_style),
            Paragraph("Frontend (Vercel)", tbl_cell),
            Paragraph("<code>https://skillbay-backend.onrender.com</code>", tbl_cell),
            Paragraph("Directs frontend Axios requests and SSE streams to the Render backend.", tbl_cell),
        ],
        [
            Paragraph("<code>VITE_DEV_MODE</code>", code_style),
            Paragraph("Frontend (Vercel)", tbl_cell),
            Paragraph("<code>false</code>", tbl_cell),
            Paragraph("Enforces production authentication and real AI server endpoints.", tbl_cell),
        ],
    ]

    env_table = Table(env_table_data, colWidths=[120, 75, 125, 160])
    env_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(env_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 6: STEP-BY-STEP IMPLEMENTATION ROADMAP
    # =========================================================================
    story.append(Paragraph("6. Step-by-Step Implementation Roadmap", h1_style))
    story.append(Paragraph(
        "To achieve 100% unified Gemini integration with zero breaking changes, follow this execution sequence:", body_style
    ))

    steps = [
        "<b>Phase 1: Key Validation & Legacy Clean-up</b> — Remove <code>startswith('AIza')</code> checks from <code>ai_service.py</code>, "
        "<code>chat_service.py</code>, and <code>schema_detector.py</code>. Ensure all modules accept <code>AQ...</code> keys. Replace retired "
        "<code>gemini-1.5-flash</code> defaults with <code>gemini-3.6-flash</code>.",
        "<b>Phase 2: Unified Narrative Helpers in <code>llm_manager.py</code></b> — Add dedicated helper functions in <code>llm_manager.py</code>: "
        "<code>generate_student_narrative()</code> (returning structured summary, 30-day plan, roadmap, certs) and "
        "<code>generate_cohort_executive_summary()</code> (for live report PDFs).",
        "<b>Phase 3: Student Profile On-Demand Re-Analysis</b> — Create <code>POST /api/students/{id}/ai-analysis</code> in <code>students.py</code>. "
        "In <code>StudentProfile.jsx</code>, add a 'Regenerate AI Analysis' button with a spinner and instant badge refresh.",
        "<b>Phase 4: Live Cohort PDF AI Commentary</b> — Update <code>_build_live_report_pdf()</code> in <code>reports.py</code> to invoke "
        "<code>generate_cohort_executive_summary()</code> and inject a styled AI Narrative callout box above the student table.",
        "<b>Phase 5: Job Role AI Fit Explainer</b> — Add <code>POST /api/jobs/roles/{id}/ai-explain</code> in <code>jobs.py</code> to explain candidate "
        "strengths and specific Kauvery unit requirements.",
        "<b>Phase 6: Admin Settings Model Persistence</b> — Enable updating <code>settings.gemini_model</code> in <code>admin.py</code> and add an "
        "instant connection diagnostic test button in <code>Settings.jsx</code>.",
    ]
    for s in steps:
        story.append(Paragraph(s, bullet_style))
        story.append(Spacer(1, 2))
    story.append(Spacer(1, 12))

    # =========================================================================
    # SECTION 7: VERIFICATION CHECKLIST
    # =========================================================================
    story.append(Paragraph("7. Final Verification Checklist", h1_style))
    checklist_data = [
        [Paragraph("Check Item", tbl_hdr), Paragraph("Verification Command / Target", tbl_hdr), Paragraph("Status", tbl_hdr)],
        [Paragraph("1. Gemini SDK Initialized", tbl_cell_bold), Paragraph("<code>genai.Client(api_key=...)</code> instantiated cleanly", code_style), Paragraph("VERIFIED (Live)", badge_green)],
        [Paragraph("2. Status Endpoint Working", tbl_cell_bold), Paragraph("<code>GET /api/ai/status</code> returns mode: gemini", code_style), Paragraph("VERIFIED (200 OK)", badge_green)],
        [Paragraph("3. Dynamic Model Discovery", tbl_cell_bold), Paragraph("<code>GET /api/ai/models</code> lists available models", code_style), Paragraph("VERIFIED (200 OK)", badge_green)],
        [Paragraph("4. Real-time Streaming SSE", tbl_cell_bold), Paragraph("<code>POST /api/ai/chat/stream</code> emits tool_status & token", code_style), Paragraph("VERIFIED (Live)", badge_green)],
        [Paragraph("5. Automatic Model Fallback", tbl_cell_bold), Paragraph("Falls back to gemini-3.5-flash-lite on 503 or 404", code_style), Paragraph("VERIFIED (Unit Test)", badge_green)],
        [Paragraph("6. Student Narrative Unification", tbl_cell_bold), Paragraph("Refactor ai_service.py to consume llm_manager", code_style), Paragraph("PENDING ACTION", badge_amber)],
        [Paragraph("7. Cohort Report AI Narrative", tbl_cell_bold), Paragraph("Embed executive summary into Live PDF builder", code_style), Paragraph("PENDING ACTION", badge_amber)],
        [Paragraph("8. Zero Retired Model Refs", tbl_cell_bold), Paragraph("Purge gemini-1.5-flash from configs & doc templates", code_style), Paragraph("PENDING ACTION", badge_amber)],
    ]
    chk_table = Table(checklist_data, colWidths=[150, 230, 100])
    chk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(chk_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated: {filename}")


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "Gemini_API_Full_Project_Integration_Analysis.pdf"
    build_pdf(out_path)
