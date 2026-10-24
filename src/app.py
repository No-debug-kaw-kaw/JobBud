import html
import base64
import re
import hashlib
import json
import time
import unicodedata
from background_data import get_background_value, any_completed
from ai_trend_sources import add_backup_signals, HN_SOURCE
from datetime import datetime
from io import BytesIO

from i18n import (
    LANGUAGES,
    USER_TYPES,
    BACKGROUNDS,
    EXPERIENCE_LEVELS,
    INTERESTS,
    t,
    tf,
    option_label,
    role_label,
    signal_label,
    group_label,
    industry_label,
    tech_label,
    term_label,
    role_description,
    sdg_title_label,
    sdg_rationale_label,
    resource_cost_label,
    cv_term_aliases,
)

import streamlit as st
import pandas as pd
from pypdf import PdfReader
from docx import Document

from gdelt_engine import (
    get_ai_skill_signals,
    get_role_ai_signal,
    load_gdelt_cache,
    normalize_signals,
    TECH_QUERIES,
    RETRY_COOLDOWN,
)

from salary_engine import get_salary_benchmark

from ai_explainer import explain_recommendation, fallback_explanation
from career_engine import (
    QUESTIONNAIRE_KNOWLEDGE,
    QUESTIONNAIRE_SKILLS,
    get_available_technologies,
    get_role_technology_requirements,
    get_data_health,
    get_onet_source_date,
    get_top_matches,
)
from reskill_engine import build_learning_path
from scenario_engine import build_scenario_comparison
from sdg_engine import get_match_sdg_impact
from trend_engine import (
    analyse_role_trends,
    analyse_skill_radar,
    apply_trends_to_matches,
    fetch_job_data,
    cached_job_data,
)


@st.cache_data(ttl=21600, max_entries=128, show_spinner=False)
def load_matches(profile):
    return get_top_matches(profile, top_n=11)


st.set_page_config(
    page_title="JobBud",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "language" not in st.session_state:
    requested_language = st.query_params.get("lang", "en")
    st.session_state.language = requested_language if requested_language in LANGUAGES else "en"

language = st.selectbox(
    "Language / Bahasa / 语言",
    options=list(LANGUAGES.keys()),
    format_func=lambda code: LANGUAGES[code],
    key="language",
)

lang = language
if st.query_params.get("lang") != lang:
    st.query_params["lang"] = lang


VISUAL_COPY = {
    "en": {
        "career_match": "Career Match",
        "career_match_copy": "Compare your profile with occupational evidence.",
        "market_insight": "Market Insight",
        "market_insight_copy": "See current job-posting and AI attention signals.",
        "learning_path": "Learning Path",
        "learning_path_copy": "Turn skill gaps into clear next learning steps.",
        "intake": "Intake",
        "context": "Context",
        "tools": "Tools",
        "skills": "Skills",
        "knowledge": "Knowledge",
    },
    "ms": {
        "career_match": "Padanan Kerjaya",
        "career_match_copy": "Bandingkan profil anda dengan bukti pekerjaan.",
        "market_insight": "Wawasan Pasaran",
        "market_insight_copy": "Lihat isyarat pekerjaan semasa dan perhatian AI.",
        "learning_path": "Laluan Pembelajaran",
        "learning_path_copy": "Tukar jurang kemahiran kepada langkah pembelajaran seterusnya.",
        "intake": "Kaedah Input",
        "context": "Konteks",
        "tools": "Alat",
        "skills": "Kemahiran",
        "knowledge": "Pengetahuan",
    },
    "zh": {
        "career_match": "职业匹配",
        "career_match_copy": "将你的个人资料与职业证据进行比较。",
        "market_insight": "市场洞察",
        "market_insight_copy": "查看当前招聘与 AI 关注度信号。",
        "learning_path": "学习路径",
        "learning_path_copy": "把技能差距转化为清晰的下一步学习计划。",
        "intake": "输入方式",
        "context": "个人背景",
        "tools": "工具",
        "skills": "技能",
        "knowledge": "知识",
    },
}

def vcopy(key: str) -> str:
    return VISUAL_COPY.get(lang, VISUAL_COPY["en"]).get(key, key)


PART2_COPY = {
    "en": {
        "top_fit": "Top fit",
        "market_signal": "Market signal",
        "details": "Explore details",
        "role_overview": "Role overview",
        "why_recommended": "Why this role was recommended",
        "score_breakdown": "Score breakdown",
        "priority_gaps": "Priority gaps",
        "no_priority_gaps": "No major assessed gaps",
        "current": "You",
        "target": "Role",
        "not_yet_used": "Not yet used",
        "technology_fit": "Technology fit",
        "already_used": "Already used",
        "role_relevance": "Role relevance",
        "high_relevance": "High relevance",
        "relevant": "Relevant",
        "no_tech_fit": "No matching self-reported technology for this role yet",
        "explore_option": "Explore option",
        "hot_technology": "Hot Technology",
        "in_demand": "In Demand",
        "role_relevant": "Role relevant",
    },
    "ms": {
        "top_fit": "Padanan utama",
        "market_signal": "Isyarat pasaran",
        "details": "Lihat butiran",
        "role_overview": "Gambaran peranan",
        "why_recommended": "Mengapa peranan ini dicadangkan",
        "score_breakdown": "Pecahan skor",
        "priority_gaps": "Jurang keutamaan",
        "no_priority_gaps": "Tiada jurang besar yang dinilai",
        "current": "Anda",
        "target": "Peranan",
        "not_yet_used": "Belum digunakan",
        "technology_fit": "Padanan teknologi",
        "already_used": "Sudah digunakan",
        "role_relevance": "Kerelevanan peranan",
        "high_relevance": "Sangat relevan",
        "relevant": "Relevan",
        "no_tech_fit": "Belum ada teknologi yang dilaporkan sendiri dan sepadan dengan peranan ini",
        "explore_option": "Teroka pilihan",
        "hot_technology": "Teknologi popular",
        "in_demand": "Dalam permintaan",
        "role_relevant": "Relevan dengan peranan",
    },
    "zh": {
        "top_fit": "主要匹配点",
        "market_signal": "市场信号",
        "details": "查看详情",
        "role_overview": "职业概览",
        "why_recommended": "为什么推荐这个职业",
        "score_breakdown": "分数构成",
        "priority_gaps": "主要技能差距",
        "no_priority_gaps": "目前没有明显的已评估差距",
        "current": "你的水平",
        "target": "职业参考",
        "not_yet_used": "尚未使用",
        "technology_fit": "技术匹配",
        "already_used": "已使用",
        "role_relevance": "职业相关度",
        "high_relevance": "高度相关",
        "relevant": "相关",
        "no_tech_fit": "目前没有与你自报工具相匹配的职业技术要求",
        "explore_option": "查看选项",
        "hot_technology": "热门技术",
        "in_demand": "市场需求",
        "role_relevant": "职业相关",
    },
}


def p2copy(key: str) -> str:
    return PART2_COPY.get(lang, PART2_COPY["en"]).get(key, key)


PART3_COPY = {
    "en": {
        "salary_snapshot": "Salary snapshot",
        "industry_context": "Industry context",
        "benchmark_year": "Benchmark year",
        "salary_note": "Industry-level benchmark · not an exact offer",
        "learning_summary": "Your next steps",
        "gap_label": "Gap",
        "weeks_label": "Estimated time",
        "weeks_short": "weeks",
        "resource_label": "Learning resource",
        "resource_pending": "Verified resource not yet mapped",
        "ai_snapshot": "AI & technology snapshot",
        "attention_label": "Attention score",
        "topics_label": "Signals considered",
        "trend_chart": "AI attention change",
        "trend_chart_help": "Change compares the recent 14-day period with the previous 14 days.",
        "market_snapshot": "Current market snapshot",
        "demand_chart": "Relative demand in current job-posting sample",
        "market_details": "View market evidence table",
        "ai_details": "View AI trend evidence table",
        "source_method": "Sources & method",
        "not_prediction": "Signals are evidence, not hiring predictions.",
        "backup_short": "Backup source active: Hacker News Algolia.",
        "learning_mix_note": "Priorities are ordered to surface different gap types when available.",
        "learning_focus_note": "Current highest-priority gaps are concentrated in",
    },
    "ms": {
        "salary_snapshot": "Ringkasan gaji",
        "industry_context": "Konteks industri",
        "benchmark_year": "Tahun penanda aras",
        "salary_note": "Penanda aras peringkat industri · bukan tawaran gaji tepat",
        "learning_summary": "Langkah seterusnya anda",
        "gap_label": "Jurang",
        "weeks_label": "Anggaran masa",
        "weeks_short": "minggu",
        "resource_label": "Sumber pembelajaran",
        "resource_pending": "Sumber disahkan belum dipetakan",
        "ai_snapshot": "Ringkasan AI & teknologi",
        "attention_label": "Skor perhatian",
        "topics_label": "Isyarat dipertimbangkan",
        "trend_chart": "Perubahan perhatian AI",
        "trend_chart_help": "Perubahan membandingkan 14 hari terkini dengan 14 hari sebelumnya.",
        "market_snapshot": "Ringkasan pasaran semasa",
        "demand_chart": "Permintaan relatif dalam sampel iklan kerja semasa",
        "market_details": "Lihat jadual bukti pasaran",
        "ai_details": "Lihat jadual bukti trend AI",
        "source_method": "Sumber & kaedah",
        "not_prediction": "Isyarat ialah bukti, bukan ramalan pengambilan.",
        "backup_short": "Sumber sandaran aktif: Hacker News Algolia.",
        "learning_mix_note": "Keutamaan disusun untuk memaparkan jenis jurang yang berbeza apabila tersedia.",
        "learning_focus_note": "Jurang keutamaan tertinggi semasa tertumpu pada",
    },
    "zh": {
        "salary_snapshot": "薪资概览",
        "industry_context": "行业背景",
        "benchmark_year": "基准年份",
        "salary_note": "行业层级基准 · 不是具体职位的薪资报价",
        "learning_summary": "你的下一步",
        "gap_label": "差距",
        "weeks_label": "预计时间",
        "weeks_short": "周",
        "resource_label": "学习资源",
        "resource_pending": "尚未匹配已验证资源",
        "ai_snapshot": "AI 与技术概览",
        "attention_label": "关注度分数",
        "topics_label": "参考信号",
        "trend_chart": "AI 关注度变化",
        "trend_chart_help": "变化比较最近 14 天与之前 14 天。",
        "market_snapshot": "当前市场概览",
        "demand_chart": "当前招聘样本中的相对需求",
        "market_details": "查看市场证据表",
        "ai_details": "查看 AI 趋势证据表",
        "source_method": "来源与方法",
        "not_prediction": "这些是证据信号，不是招聘预测。",
        "backup_short": "备用来源已启用：Hacker News Algolia。",
        "learning_mix_note": "如有不同类型的差距，学习优先级会交错展示，方便快速理解。",
        "learning_focus_note": "目前最高优先级的差距主要集中在",
    },
}


def p3copy(key: str) -> str:
    return PART3_COPY.get(lang, PART3_COPY["en"]).get(key, key)


def _diversify_learning_path(items: list[dict]) -> list[dict]:
    """Interleave gap groups for display only; underlying priorities are unchanged."""
    if len(items) < 2:
        return list(items)

    buckets: dict[str, list[dict]] = {}
    group_order: list[str] = []
    for item in items:
        group = str(item.get("group", "Skill"))
        if group not in buckets:
            buckets[group] = []
            group_order.append(group)
        buckets[group].append(item)

    if len(group_order) < 2:
        return list(items)

    mixed: list[dict] = []
    cursor = 0
    while len(mixed) < len(items):
        added = False
        for group in group_order:
            bucket = buckets[group]
            if cursor < len(bucket):
                mixed.append(bucket[cursor])
                added = True
        if not added:
            break
        cursor += 1
    return mixed


def _visual_term(item: dict) -> str:
    return term_label(item.get("skill", ""), lang)


def _chip_html(items: list[dict], limit: int = 3, tone: str = "fit") -> str:
    labels = []
    for item in items[:limit]:
        label = safe_text(_visual_term(item))
        if label:
            labels.append(f'<span class="insight-chip {tone}">{label}</span>')
    return "".join(labels)


def _technology_badges(role: str, skill: str) -> str:
    """Return display-only O*NET technology flags for one role/software pair."""
    try:
        requirements = get_role_technology_requirements(role)
    except Exception:
        requirements = []
    row = next((item for item in requirements if item.get("skill") == skill), None)
    labels = []
    if row:
        if row.get("hot_technology"):
            labels.append(p2copy("hot_technology"))
        if row.get("in_demand"):
            labels.append(p2copy("in_demand"))
    if not labels:
        labels.append(p2copy("role_relevant"))
    return " · ".join(labels)


def render_gap_visual(items: list[dict], role: str) -> None:
    """Compact visual gaps. Display only; scoring is unchanged."""
    visible = items[:5]
    if not visible:
        st.markdown(
            f'<div class="empty-visual">✓ {safe_text(p2copy("no_priority_gaps"))}</div>',
            unsafe_allow_html=True,
        )
        return

    for item in visible:
        label = safe_text(_visual_term(item))
        category = item.get("group", "")
        if category == "Technology":
            badge_text = _technology_badges(role, item.get("skill", ""))
            st.markdown(
                f'<div class="tech-gap-card">'
                f'<div class="tech-gap-head"><strong>{label}</strong>'
                f'<span class="tech-gap-badge">{safe_text(p2copy("not_yet_used"))}</span></div>'
                f'<div class="tech-gap-note">{safe_text(badge_text)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            continue

        user = item.get("user")
        target = item.get("target")
        gap = item.get("gap")
        if gap is None and user is not None and target is not None:
            gap = max(float(target) - float(user), 0)
        gap_value = max(float(gap or 0), 0)
        width = min(max(gap_value / 5 * 100, 8), 100)
        user_text = f"{float(user):.1f}/5" if user is not None else "—"
        target_text = f"{float(target):.1f}/5" if target is not None else "—"
        category_text = safe_text(group_label(category, lang))
        st.markdown(
            f'<div class="gap-row"><div class="gap-row-head"><strong>{label} · {category_text}</strong>'
            f'<span>{safe_text(p2copy("current"))} {user_text} · {safe_text(p2copy("target"))} {target_text}</span></div>'
            f'<div class="gap-track"><div class="gap-fill" style="width:{width:.0f}%"></div></div></div>',
            unsafe_allow_html=True,
        )


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap');

    :root {
        --ink: #193a36;
        --muted-ink: #536a63;
        --paper: #f5f4ec;
        --paper-deep: #e9ede3;
        --forest: #1d6559;
        --forest-dark: #154a42;
        --lime: #c6d88c;
        --ochre: #b87637;
        --line: #d5ddd1;
        --soft-blue: #dce8e5;
    }
    html, body, [data-testid="stAppViewContainer"] {
        background: var(--paper);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMain"] > div { padding-top: 1.2rem; }
    .block-container { max-width: 1220px; padding: 1rem 2.5rem 4rem; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.035em; }
    h1, h2 { font-family: 'Newsreader', Georgia, serif; }
    h1 { font-size: clamp(2.5rem, 5vw, 4.1rem) !important; line-height: 1.02 !important; }
    h2 { font-size: clamp(1.65rem, 3vw, 2.35rem) !important; }
    h3 { font-size: 1.18rem !important; font-weight: 700 !important; }
    p, li, label, [data-testid="stMarkdownContainer"] { color: var(--ink); }
    [data-testid="stCaptionContainer"] { color: var(--muted-ink); }
    [data-testid="stMetric"] {
        background: #eef0e8;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
    }
    [data-testid="stMetricLabel"] { color: var(--muted-ink); }
    [data-testid="stMetricValue"] { color: var(--forest-dark); }
    [data-testid="stProgressBar"] > div > div {
        background: var(--forest);
    }
    [data-testid="stProgressBar"] { background: #d7dfd4; }
    div[data-testid="stForm"] {
        background: #eeefe7;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1.1rem 1.3rem 0.8rem;
    }
    div[data-testid="stFormSubmitButton"] button,
    [data-testid="stButton"] button[kind="primary"] {
        background: var(--forest);
        color: #fbfbf5;
        border: 1px solid var(--forest);
        border-radius: 9px;
        min-height: 2.8rem;
        font-weight: 700;
        transition: transform 160ms ease, opacity 160ms ease;
    }
    div[data-testid="stFormSubmitButton"] button:hover,
    [data-testid="stButton"] button[kind="primary"]:hover {
        background: var(--forest-dark);
        border-color: var(--forest-dark);
        transform: translateY(-1px);
    }
    button[kind="secondary"], [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
        border-color: #b8c8bd !important;
        border-radius: 8px !important;
    }
    [data-testid="stSlider"] [role="slider"] { border-color: var(--forest) !important; }
    [data-testid="stExpander"] {
        background: rgba(238, 240, 232, 0.72);
        border: 1px solid var(--line);
        border-radius: 12px;
    }
    [data-testid="stAlert"] { border-radius: 10px; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 10px; }
    .masthead {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid var(--line); padding: 0.15rem 0 1.1rem;
        margin-bottom: 2rem;
    }
    .brand { font-size: 0.83rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: var(--forest-dark); }
    .brand-mark { display: inline-block; width: 11px; height: 11px; margin-right: 9px; background: var(--ochre); border-radius: 2px 7px 2px 7px; transform: rotate(-12deg); }
    .masthead-note { font-size: 0.76rem; color: var(--muted-ink); letter-spacing: 0.05em; text-transform: uppercase; }
    .hero-kicker, .section-kicker {
        color: var(--forest); font-size: 0.74rem; font-weight: 700;
        letter-spacing: 0.15em; text-transform: uppercase;
    }
    .hero-copy { color: var(--muted-ink); font-size: 1.1rem; max-width: 690px; line-height: 1.65; }
    .hero-aside {
        border-left: 3px solid var(--ochre); padding: 0.65rem 0 0.65rem 1rem;
        color: var(--muted-ink); font-size: 0.91rem; line-height: 1.55;
        margin-top: 1.5rem;
    }
    .section-rule { border: 0; border-top: 1px solid var(--line); margin: 2rem 0 1.5rem; }
    .result-card {
        background: #eef0e8; border: 1px solid var(--line); border-radius: 15px;
        padding: 1rem 1.05rem; margin: 0.3rem 0 0.75rem;
    }
    .role-rank { color: var(--ochre); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }
    .role-title { font-family: 'Newsreader', Georgia, serif; color: var(--ink); font-size: 1.45rem; line-height: 1.15; margin: 0.3rem 0 0.55rem; }
    .signal-pill {
        display: inline-block; border-radius: 999px; padding: 0.2rem 0.6rem;
        background: var(--soft-blue); color: var(--forest-dark);
        font-size: 0.74rem; font-weight: 700;
    }
    .signal-muted { background: #e7e8e1; color: #4d5d56; }
    .career-summary-card {
        height: 100%; background: #eef0e8; border: 1px solid var(--line);
        border-radius: 18px; padding: 1.15rem 1.15rem 1rem;
        box-shadow: 0 8px 24px rgba(25, 58, 54, 0.045);
    }
    .career-summary-card.top-card {
        border-color: #afc5b8; box-shadow: 0 10px 28px rgba(25, 58, 54, 0.08);
    }
    .career-card-rank {
        color: var(--ochre); font-size: 0.68rem; font-weight: 700;
        letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.35rem;
    }
    .career-card-title {
        font-family: 'Newsreader', Georgia, serif; color: var(--ink);
        font-size: 1.32rem; font-weight: 600; line-height: 1.12;
        min-height: 3rem; margin-bottom: 0.55rem;
    }
    .career-big-score {
        color: var(--forest-dark); font-size: 2.35rem; font-weight: 700;
        letter-spacing: -0.06em; line-height: 1;
    }
    .career-score-label {
        color: var(--muted-ink); font-size: 0.72rem; margin: 0.22rem 0 0.7rem;
    }
    .career-score-track {
        height: 8px; background: #d9e1d8; border-radius: 999px; overflow: hidden;
        margin-bottom: 0.8rem;
    }
    .career-score-fill {
        height: 100%; background: var(--forest); border-radius: 999px;
    }
    .career-meta {
        display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center;
        margin-bottom: 0.8rem;
    }
    .summary-badge {
        display: inline-block; padding: 0.24rem 0.55rem; border-radius: 999px;
        background: var(--soft-blue); color: var(--forest-dark);
        font-size: 0.7rem; font-weight: 700;
    }
    .confidence-badge { background: #f0eadf; color: #7b552d; }
    .career-mini-label {
        color: var(--muted-ink); font-size: 0.69rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.38rem;
    }
    .insight-chip {
        display: inline-block; margin: 0 0.3rem 0.32rem 0; padding: 0.28rem 0.55rem;
        border-radius: 999px; font-size: 0.72rem; font-weight: 600;
        border: 1px solid #c7d5ca; background: #f7f7f1; color: var(--forest-dark);
    }
    .insight-chip.gap { background: #f3e9de; border-color: #e3c7ac; color: #724b2a; }
    .visual-panel {
        background: rgba(238, 240, 232, 0.72); border: 1px solid var(--line);
        border-radius: 14px; padding: 0.9rem 1rem; margin-top: 0.4rem;
    }
    .gap-row { margin: 0.6rem 0 0.8rem; }
    .gap-row-head {
        display: flex; justify-content: space-between; gap: 1rem; align-items: baseline;
        font-size: 0.82rem; margin-bottom: 0.3rem;
    }
    .gap-row-head span { color: var(--muted-ink); font-size: 0.72rem; text-align: right; }
    .gap-track { height: 8px; background: #dde3da; border-radius: 999px; overflow: hidden; }
    .gap-fill { height: 100%; background: var(--ochre); border-radius: 999px; }
    .tech-gap-card {
        background: rgba(255,255,255,0.28); border: 1px solid var(--line);
        border-radius: 10px; padding: 0.6rem 0.7rem; margin: 0.55rem 0;
    }
    .tech-gap-head {
        display: flex; justify-content: space-between; gap: 0.8rem; align-items: center;
        font-size: 0.82rem;
    }
    .tech-gap-badge {
        display: inline-block; padding: 0.2rem 0.5rem; border-radius: 999px;
        background: #e4ece7; color: var(--forest-dark); font-size: 0.68rem; font-weight: 700;
        white-space: nowrap;
    }
    .tech-fit-card {
        border-color: rgba(29,101,89,.22);
        background: rgba(223,238,232,.36);
    }
    .tech-fit-badge {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: .3rem .58rem;
        background: #dfeee8;
        color: #15564c;
        font-size: .78rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .tech-gap-note {
        color: var(--muted-ink); font-size: 0.7rem; margin-top: 0.25rem;
    }
    .empty-visual {
        background: #edf3e9; border: 1px solid #cfddc9; color: var(--forest-dark);
        border-radius: 10px; padding: 0.7rem 0.85rem; font-size: 0.82rem;
    }
    .note-panel {
        background: #e9ede3; border-left: 3px solid var(--forest);
        border-radius: 0 10px 10px 0; padding: 0.95rem 1.1rem;
    }
    .source-small { font-size: 0.82rem; color: var(--muted-ink); }
    .footer-note { border-top: 1px solid var(--line); margin-top: 2.7rem; padding-top: 1.2rem; color: var(--muted-ink); font-size: 0.83rem; line-height: 1.6; }

    /* Part 1 visual refresh: presentation only */
    .feature-card {
        min-height: 112px; background: rgba(238, 240, 232, 0.86);
        border: 1px solid var(--line); border-radius: 16px; padding: 1rem 1.05rem;
        box-shadow: 0 6px 18px rgba(25, 58, 54, 0.04);
    }
    .feature-icon { font-size: 1.35rem; margin-bottom: 0.35rem; }
    .feature-title { color: var(--forest-dark); font-weight: 800; font-size: 0.95rem; }
    .feature-copy { color: var(--muted-ink); font-size: 0.82rem; line-height: 1.45; margin-top: 0.25rem; }
    .mini-section-card {
        background: rgba(255,255,255,0.22); border: 1px solid var(--line);
        border-radius: 14px; padding: 0.7rem 0.9rem; margin: 0.35rem 0 0.8rem;
    }
    .chip-wrap { display: flex; flex-wrap: wrap; gap: 0.42rem; margin: 0.35rem 0 0.75rem; }
    .chip {
        display: inline-block; padding: 0.28rem 0.62rem; border-radius: 999px;
        border: 1px solid #c7d5cc; background: #edf2ec; color: var(--forest-dark);
        font-size: 0.78rem; font-weight: 650; line-height: 1.25;
    }
    .chip.tool { background: #e5eeeb; }
    .chip.knowledge { background: #f2eee2; border-color: #ded4ba; }
    .visual-label {
        color: var(--ochre); font-size: 0.7rem; font-weight: 800;
        letter-spacing: 0.12em; text-transform: uppercase; margin-top: 0.25rem;
    }

    /* Part 3 visual refresh */
    .salary-hero-card {
        background: linear-gradient(145deg, rgba(229,238,235,.92), rgba(238,240,232,.92));
        border: 1px solid var(--line); border-radius: 16px; padding: 1rem 1.1rem; height: 100%;
    }
    .salary-amount {
        font-family: 'Newsreader', Georgia, serif; color: var(--forest-dark);
        font-size: 2rem; line-height: 1; margin: .35rem 0 .25rem;
    }
    .salary-label { color: var(--muted-ink); font-size: .78rem; }
    .context-card {
        background: rgba(255,255,255,.22); border: 1px solid var(--line);
        border-radius: 16px; padding: 1rem 1.05rem; height: 100%;
    }
    .context-value { color: var(--forest-dark); font-weight: 750; font-size: .96rem; margin-top: .35rem; line-height: 1.35; }
    .learning-step-card {
        background: rgba(238,240,232,.82); border: 1px solid var(--line);
        border-radius: 14px; padding: .9rem 1rem; margin: .55rem 0;
    }
    .learning-step-head { display:flex; justify-content:space-between; gap:.8rem; align-items:flex-start; }
    .learning-step-no {
        display:inline-flex; width:2rem; height:2rem; align-items:center; justify-content:center;
        border-radius:999px; background:var(--forest); color:white; font-weight:800; font-size:.78rem; flex:0 0 auto;
    }
    .learning-step-title { font-weight:800; color:var(--forest-dark); font-size:.98rem; line-height:1.3; }
    .learning-step-meta { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.55rem; }
    .learning-meta-pill {
        display:inline-block; padding:.22rem .5rem; border-radius:999px; background:#e6ece5;
        color:var(--muted-ink); font-size:.7rem; font-weight:700;
    }
    .learning-resource { margin-top:.65rem; padding-top:.6rem; border-top:1px solid var(--line); font-size:.8rem; }
    .signal-summary-card {
        background:rgba(238,240,232,.82); border:1px solid var(--line); border-radius:15px;
        padding:.9rem 1rem; height:100%;
    }
    .signal-number { color:var(--forest-dark); font-size:1.9rem; font-weight:800; letter-spacing:-.04em; margin-top:.3rem; }
    .signal-small { color:var(--muted-ink); font-size:.73rem; line-height:1.45; margin-top:.25rem; }
    .chart-caption { color:var(--muted-ink); font-size:.75rem; margin:.15rem 0 .55rem; }
    @media (max-width: 760px) {
        .block-container { padding: 0.75rem 1rem 3rem; }
        .masthead-note { display: none; }
        div[data-testid="stForm"] { padding: 0.8rem; }
        .hero-copy { font-size: 1rem; }
    }

    .sdg-visual-card {
        border: 1px solid var(--line);
        border-radius: 15px;
        padding: .75rem .85rem;
        background: rgba(255,255,255,0.24);
        display: flex;
        align-items: center;
        gap: .85rem;
        max-width: 620px;
        min-height: 116px;
    }
    .sdg-visual-card img {
        display: block;
        width: 88px;
        height: 88px;
        object-fit: cover;
        border-radius: 12px;
        flex: 0 0 88px;
        margin: 0;
    }
    .sdg-visual-body { padding: 0; min-width: 0; }
    .sdg-visual-kicker {
        font-size: 0.67rem;
        font-weight: 800;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        color: var(--ochre);
        margin-bottom: 0.18rem;
    }
    .sdg-visual-title {
        font-family: 'Newsreader', Georgia, serif;
        font-size: 1.02rem;
        line-height: 1.15;
        font-weight: 600;
        color: var(--ink);
        margin-bottom: 0.28rem;
    }
    .sdg-visual-copy {
        font-size: 0.78rem;
        color: var(--muted-ink);
        line-height: 1.35;
        margin-bottom: 0.28rem;
    }
    .sdg-visual-link {
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--forest);
        text-decoration: none;
    }
    @media (max-width: 760px) {
        .sdg-visual-card { max-width: 100%; gap: .7rem; }
        .sdg-visual-card img { width: 74px; height: 74px; flex-basis: 74px; }
    }

    </style>
    """,
    unsafe_allow_html=True,
)

def extract_cv_text(uploaded_file) -> str:
    """Extract text from PDF, DOCX or TXT without saving the file."""

    if uploaded_file is None:
        return ""

    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    try:
        if file_name.endswith(".pdf"):
            reader = PdfReader(BytesIO(file_bytes))

            pages = []

            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)

            return "\n".join(pages)

        if file_name.endswith(".docx"):
            document = Document(BytesIO(file_bytes))

            return "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            )

        if file_name.endswith(".txt"):
            return file_bytes.decode(
                "utf-8",
                errors="ignore",
            )

    except Exception:
        return ""

    return ""


def _normalise_cv_text(text: str) -> str:
    """Normalise CV text for deterministic phrase matching."""
    return " ".join(
        unicodedata.normalize(
            "NFKC",
            str(text or ""),
        ).casefold().split()
    )


def _contains_cv_phrase(
    normalized_text: str,
    phrase: str,
) -> bool:
    """Match a phrase as a standalone word/phrase rather than a substring."""
    normalized_phrase = _normalise_cv_text(phrase)

    if not normalized_phrase:
        return False

    # Chinese phrases may appear without spaces.
    if (
        len(normalized_phrase) >= 4
        and all(
            "\u4e00" <= char <= "\u9fff"
            for char in normalized_phrase
        )
    ):
        boundary = r"[^\W\u4e00-\u9fff]"
    else:
        boundary = r"\w"

    pattern = (
        rf"(?<!{boundary})"
        rf"{re.escape(normalized_phrase)}"
        rf"(?!{boundary})"
    )

    return re.search(
        pattern,
        normalized_text,
    ) is not None


def cv_contains_term(
    text: str,
    term: str,
) -> bool:
    """
    Strict direct matching for canonical questionnaire terms and i18n aliases.

    This is intentionally conservative. Broader CV evidence phrases are handled
    separately in detect_cv_items().
    """
    if not text or not term:
        return False

    normalized_text = _normalise_cv_text(
        text
    )

    for candidate in (
        term,
        *cv_term_aliases(term),
    ):
        if _contains_cv_phrase(
            normalized_text,
            candidate,
        ):
            return True

    return False


# These mappings convert common CV wording into the SMALL set of
# questionnaire concepts supported by the O*NET matching engine.
# They are suggestion rules only; they do not assign a 1-5 proficiency level.
CV_SKILL_EVIDENCE: dict[str, tuple[str, ...]] = {
    "Reading Comprehension": (
        "literature review",
        "reviewed literature",
        "reviewed research",
        "research review",
    ),
    "Active Listening": (
        "active listening",
        "client interviews",
        "stakeholder interviews",
        "user interviews",
    ),
    "Speaking": (
        "presentation",
        "presented",
        "public speaking",
        "pitching",
        "pitched",
        "oral presentation",
    ),
    "Critical Thinking": (
        "critical thinking",
        "analytical thinking",
        "analytical skills",
        "root cause analysis",
        "evaluated alternatives",
        "evaluated options",
    ),
    "Active Learning": (
        "active learning",
        "self learning",
        "self-learning",
        "self taught",
        "self-taught",
        "continuous learning",
    ),
    "Writing": (
        "report writing",
        "written report",
        "written reports",
        "documentation",
        "documented",
        "meeting minutes",
        "technical writing",
    ),
    "Mathematics": (
        "mathematics",
        "mathematical",
        "quantitative methods",
        "quantitative analysis",
        "calculus",
        "linear algebra",
    ),
    "Monitoring": (
        "monitoring",
        "monitored",
        "tracked kpi",
        "tracked kpis",
        "performance tracking",
        "progress tracking",
    ),
    "Learning Strategies": (
        "learning strategies",
        "training plan",
        "learning plan",
        "study plan",
    ),
    # IMPORTANT: do not map generic "data science", "computer science",
    # or "actuarial science" to the O*NET skill named "Science".
    "Science": (
        "scientific method",
        "scientific research",
        "laboratory research",
        "laboratory experiment",
        "lab experiment",
        "experimental design",
    ),
    "Complex Problem Solving": (
        "complex problem solving",
        "problem solving",
        "problem-solving",
        "troubleshooting",
        "troubleshot",
        "debugging",
        "resolved issues",
        "resolved problems",
    ),
    "Judgment and Decision Making": (
        "decision making",
        "decision-making",
        "risk assessment",
        "risk analysis",
        "recommended actions",
        "made recommendations",
        "decision support",
    ),
    "Systems Analysis": (
        "systems analysis",
        "system analysis",
        "requirements analysis",
        "business requirements",
        "process analysis",
        "workflow analysis",
    ),
    "Systems Evaluation": (
        "systems evaluation",
        "system evaluation",
        "evaluated system",
        "evaluated systems",
        "performance evaluation",
    ),
    "Time Management": (
        "time management",
        "managed deadlines",
        "met deadlines",
        "project timeline",
        "project timelines",
        "schedule management",
    ),
    "Coordination": (
        "coordination",
        "coordinated",
        "co-ordinated",
        "cross-functional",
        "cross functional",
        "stakeholder coordination",
        "team coordination",
    ),
    "Social Perceptiveness": (
        "social perceptiveness",
        "customer needs",
        "client needs",
        "user needs",
        "stakeholder needs",
    ),
    "Instructing": (
        "tutor",
        "tutoring",
        "teacher",
        "teaching",
        "instructor",
        "instructed",
        "trained staff",
        "trained students",
        "mentored",
        "mentoring",
    ),
}


CV_KNOWLEDGE_EVIDENCE: dict[str, tuple[str, ...]] = {
    "Mathematics": (
        "mathematics",
        "statistics",
        "statistical",
        "calculus",
        "linear algebra",
        "probability",
        "actuarial",
        "quantitative methods",
        "quantitative analysis",
    ),
    "Computers and Electronics": (
        "computer science",
        "information technology",
        "software development",
        "software engineering",
        "programming",
        "coding",
        "database",
        "databases",
        "data engineering",
        "machine learning",
        "artificial intelligence",
    ),
    "Economics and Accounting": (
        "economics",
        "economic analysis",
        "accounting",
        "financial accounting",
        "management accounting",
        "finance",
        "financial analysis",
        "financial modelling",
        "financial modeling",
        "actuarial",
    ),
    "Administration and Management": (
        "business administration",
        "management",
        "project management",
        "operations management",
        "strategic management",
        "team management",
    ),
    "Sales and Marketing": (
        "marketing",
        "digital marketing",
        "market research",
        "sales",
        "sales analysis",
        "consumer behaviour",
        "consumer behavior",
        "branding",
    ),
    "English Language": (
        "english proficiency",
        "fluent in english",
        "proficient in english",
        "ielts",
        "toefl",
        "muet",
    ),
    "Customer and Personal Service": (
        "customer service",
        "customer support",
        "client service",
        "client support",
        "customer experience",
        "customer relations",
        "client relations",
    ),
}


# Common CV wording for O*NET workplace-software labels.
# Keys are compared case-insensitively with the actual available O*NET options.
CV_TECHNOLOGY_ALIASES: dict[str, tuple[str, ...]] = {
    "Microsoft Excel": (
        "excel",
        "ms excel",
        "microsoft excel",
    ),
    "Microsoft Power BI": (
        "power bi",
        "powerbi",
        "microsoft power bi",
    ),
    "Microsoft SQL Server": (
        "sql",
        "sql server",
        "mssql",
        "microsoft sql server",
    ),
    "Microsoft PowerPoint": (
        "powerpoint",
        "microsoft powerpoint",
        "ms powerpoint",
    ),
    "Microsoft Word": (
        "microsoft word",
        "ms word",
    ),
    "IBM SPSS Statistics": (
        "spss",
        "ibm spss",
    ),
    "Amazon Web Services AWS software": (
        "aws",
        "amazon web services",
    ),
    "Apache Hadoop": (
        "hadoop",
        "apache hadoop",
    ),
    "Apache Spark": (
        "spark",
        "apache spark",
        "pyspark",
    ),
    "Git": (
        "git",
        "github",
        "gitlab",
    ),
    "Tableau": (
        "tableau",
    ),
    "SAS": (
        "sas",
    ),
    "R": (
        "r programming",
        "r language",
        "rstudio",
        "r studio",
    ),
    "C": (
        "c programming",
        "c language",
    ),
    "Python": (
        "python",
    ),
    "C++": (
        "c++",
        "cpp",
    ),
    "C#": (
        "c#",
        "c sharp",
    ),
    "JavaScript": (
        "javascript",
        "java script",
        "js",
    ),
}


def _has_evidence(
    normalized_text: str,
    phrases: tuple[str, ...],
) -> bool:
    return any(
        _contains_cv_phrase(
            normalized_text,
            phrase,
        )
        for phrase in phrases
    )


def _contains_single_letter_tool(
    raw_text: str,
    technology: str,
) -> bool:
    """
    Recognise single-letter tools only when they appear as a standalone item
    in a comma/semicolon/pipe/newline-separated tool list.

    This prevents generic prose from falsely triggering C or R.
    """
    raw = unicodedata.normalize(
        "NFKC",
        str(raw_text or ""),
    )

    token = str(
        technology or ""
    ).strip()

    if token not in {"C", "R"}:
        return False

    pattern = (
        rf"(?:^|[,;|•\n])\s*"
        rf"{re.escape(token)}"
        rf"\s*(?=$|[,;|•\n])"
    )

    return re.search(
        pattern,
        raw,
        flags=re.MULTILINE,
    ) is not None


def _technology_cv_match(
    raw_text: str,
    normalized_text: str,
    technology: str,
) -> bool:
    """
    Match an O*NET technology label plus practical CV aliases.

    Single-letter labels such as C and R use stricter list-item matching so
    they cannot be triggered by unrelated words. Short labels are never used
    in substring-based canonical matching.
    """
    technology_label = str(
        technology or ""
    ).strip()

    technology_key = technology_label.casefold()

    if technology_label in {"C", "R"}:
        if _contains_single_letter_tool(
            raw_text,
            technology_label,
        ):
            return True
    else:
        if cv_contains_term(
            normalized_text,
            technology_label,
        ):
            return True

    aliases: tuple[str, ...] = ()

    for canonical, candidates in (
        CV_TECHNOLOGY_ALIASES.items()
    ):
        canonical_key = canonical.casefold()

        if technology_key == canonical_key:
            aliases = candidates
            break

        if (
            len(technology_key) >= 4
            and len(canonical_key) >= 4
            and (
                canonical_key in technology_key
                or technology_key in canonical_key
            )
        ):
            aliases = candidates
            break

    return _has_evidence(
        normalized_text,
        aliases,
    )


def detect_cv_items(
    cv_text: str,
    available_technologies: list[str],
) -> dict:
    """
    Suggest questionnaire items from CV evidence.

    The function is deliberately evidence-based:
    - direct canonical/translated terms are recognised;
    - common CV phrases can suggest supported O*NET questionnaire concepts;
    - generic compound phrases such as "Data Science" do NOT automatically
      imply the separate O*NET skill "Science";
    - proficiency is never inferred. Users still rate selected skills/knowledge.
    """
    normalized_text = _normalise_cv_text(
        cv_text
    )

    detected_skills: list[str] = []

    for skill in QUESTIONNAIRE_SKILLS:
        direct_match = (
            cv_contains_term(
                normalized_text,
                skill,
            )
            if skill != "Science"
            else False
        )

        evidence_match = _has_evidence(
            normalized_text,
            CV_SKILL_EVIDENCE.get(
                skill,
                (),
            ),
        )

        if (
            direct_match
            or evidence_match
        ):
            detected_skills.append(
                skill
            )

    detected_knowledge: list[str] = []

    for subject in QUESTIONNAIRE_KNOWLEDGE:
        if (
            cv_contains_term(
                normalized_text,
                subject,
            )
            or _has_evidence(
                normalized_text,
                CV_KNOWLEDGE_EVIDENCE.get(
                    subject,
                    (),
                ),
            )
        ):
            detected_knowledge.append(
                subject
            )

    detected_technologies = [
        technology
        for technology in available_technologies
        if _technology_cv_match(
            cv_text,
            normalized_text,
            technology,
        )
    ]

    # Keep UI output deterministic and duplicate-free.
    return {
        "skills": sorted(
            set(detected_skills),
            key=str.casefold,
        ),
        "knowledge": sorted(
            set(detected_knowledge),
            key=str.casefold,
        ),
        "technologies": sorted(
            set(detected_technologies),
            key=str.casefold,
        ),
    }


def _score_copy(
    key: str,
    language: str,
) -> str:
    """UI copy kept aligned with the current scoring implementation."""
    copy = {
        "en": {
            "transition": (
                "For new graduates and career switchers. Skills, knowledge and tools "
                "drive the match; background and interests add only a small context adjustment."
            ),
            "background_help": (
                "Adds a small context bonus to related roles; it does not override "
                "your assessed skills, knowledge or tools."
            ),
            "interests_help": (
                "Optional. Your strongest selected interest can add up to 1 context point "
                "to related roles."
            ),
            "future_formula": (
                "Future Career Match starts from the Base Match. When sufficient current "
                "job-posting evidence is available, a small market bonus of up to 3 points "
                "is added. This is an estimate, not a hiring forecast."
            ),
            "future_help": (
                "Starts from Base Match and may add up to 3 points when enough current "
                "job-posting evidence is available."
            ),
        },
        "ms": {
            "transition": (
                "Untuk graduan baharu dan penukar kerjaya. Kemahiran, pengetahuan dan alat "
                "memacu padanan; latar belakang dan minat hanya menambah pelarasan konteks kecil."
            ),
            "background_help": (
                "Menambah bonus konteks kecil kepada peranan berkaitan; ia tidak mengatasi "
                "kemahiran, pengetahuan atau alat yang telah dinilai."
            ),
            "interests_help": (
                "Pilihan. Minat terkuat yang dipilih boleh menambah sehingga 1 mata konteks "
                "kepada peranan berkaitan."
            ),
            "future_formula": (
                "Future Career Match bermula daripada Base Match. Apabila bukti iklan kerja "
                "semasa mencukupi, bonus pasaran kecil sehingga 3 mata ditambah. Ini ialah "
                "anggaran, bukan ramalan pengambilan pekerja."
            ),
            "future_help": (
                "Bermula daripada Base Match dan boleh menambah sehingga 3 mata apabila "
                "bukti iklan kerja semasa mencukupi."
            ),
        },
        "zh": {
            "transition": (
                "面向应届毕业生和转职者。技能、知识和工具是主要匹配依据；"
                "背景与兴趣只提供小幅情境调整。"
            ),
            "background_help": (
                "会为相关职业加入小幅情境加分，但不会取代你已评估的技能、知识和工具。"
            ),
            "interests_help": (
                "可选。你所选兴趣中最相关的一项，最多可为相关职业增加 1 个情境分。"
            ),
            "future_formula": (
                "Future Career Match 以 Base Match 为起点；当当前职位发布证据足够时，"
                "最多加入 3 分的小幅市场加分。这是估计值，不是招聘预测。"
            ),
            "future_help": (
                "以 Base Match 为起点；当当前职位发布证据足够时，最多加入 3 分。"
            ),
        },
    }

    language_copy = copy.get(
        language,
        copy["en"],
    )

    return language_copy.get(
        key,
        copy["en"].get(key, ""),
    )



SDG_VISUAL_COLORS = {
    "1": "#E5243B", "2": "#DDA63A", "3": "#4C9F38", "4": "#C5192D",
    "5": "#FF3A21", "6": "#26BDE2", "7": "#FCC30B", "8": "#A21942",
    "9": "#FD6925", "10": "#DD1367", "11": "#FD9D24", "12": "#BF8B2E",
    "13": "#3F7E44", "14": "#0A97D9", "15": "#56C02B", "16": "#00689D",
    "17": "#19486A",
}


def sdg_visual_data_uri(number: object, title: str) -> str:
    """Create a compact self-contained SDG-themed SVG icon."""
    num = str(number or "").strip()
    color = SDG_VISUAL_COLORS.get(num, "#1d6559")
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='180' height='180' viewBox='0 0 180 180'>
      <rect width='180' height='180' rx='24' fill='{color}'/>
      <circle cx='142' cy='38' r='24' fill='white' fill-opacity='0.12'/>
      <text x='20' y='42' font-family='Arial, sans-serif' font-size='18' font-weight='700' fill='white'>SDG</text>
      <text x='18' y='135' font-family='Arial, sans-serif' font-size='92' font-weight='800' fill='white'>{html.escape(num)}</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_sdg_visual_cards(career_mappings: list[dict], lang: str) -> None:
    if not career_mappings:
        return
    shown = career_mappings[:3]
    columns = st.columns(len(shown), gap="medium")
    for column, mapping in zip(columns, shown):
        number = mapping.get("number", "")
        raw_title = sdg_title_label(number, mapping.get("title", ""), lang)
        raw_rationale = sdg_rationale_label(mapping.get("rationale", ""), lang)
        image_uri = sdg_visual_data_uri(number, raw_title)
        source_url = html.escape(str(mapping.get("source_url", "") or ""), quote=True)
        title = safe_text(raw_title)
        rationale = safe_text(raw_rationale)
        number_text = safe_text(number)
        with column:
            st.markdown(
                f"""
                <div class="sdg-visual-card">
                  <img src="{image_uri}" alt="SDG {number_text} {title}">
                  <div class="sdg-visual-body">
                    <div class="sdg-visual-kicker">SDG {number_text}</div>
                    <div class="sdg-visual-title">{title}</div>
                    <div class="sdg-visual-copy">{rationale}</div>
                    <a class="sdg-visual-link" href="{source_url}" target="_blank">{safe_text(t('official_goal_reference', lang))} →</a>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def safe_text(value: object) -> str:
    return html.escape(str(value or ""))


def render_chips(values: list[str], kind: str = "skill") -> None:
    """Render compact visual chips without changing any assessment data."""
    if not values:
        return
    css_class = "chip"
    if kind == "tool":
        css_class += " tool"
    elif kind == "knowledge":
        css_class += " knowledge"
    chips = "".join(
        f'<span class="{css_class}">{safe_text(value)}</span>'
        for value in values
    )
    st.markdown(
        f'<div class="chip-wrap">{chips}</div>',
        unsafe_allow_html=True,
    )


def display_score(value: object) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return t("unavailable", lang)


def display_timestamp(value: object) -> str:
    if not value:
        return t("unavailable", lang)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y, %H:%M UTC")
    except (TypeError, ValueError):
        return str(value)


def render_signal_badge(direction: str) -> None:
    tone = "" if direction != "Insufficient signal" else " signal-muted"
    label = signal_label(direction, lang)
    st.markdown(
        f'<span class="signal-pill{tone}">{safe_text(label)}</span>',
        unsafe_allow_html=True,
    )


def render_list_items(
    items: list[dict],
    empty_message: str,
    group: str
) -> None:

    if not items:
        st.caption(empty_message)
        return

    for item in items[:5]:

        skill = safe_text(
            term_label(item.get("skill", ""), lang)
        )

        user = item.get("user")
        target = item.get("target")
        category = safe_text(
            item.get("group", group)
        )

        if user is not None:
            user_text = f"{float(user):.1f}"
        else:
            user_text = "—"

        if target is not None:
            target_text = f"{float(target):.1f}"
        else:
            target_text = "—"

        if category == "Technology":

            if group == "gap":

                st.markdown(
                    f"**{skill}** · {group_label('Technology', lang)}  \n"
                    f"{t('not_self_reported', lang)} · {t('onet_software_note', lang)}"
                )

            else:

                st.markdown(
                    f"**{skill}** · {group_label('Technology', lang)}  \n"
                    f"{t('self_reported_use', lang)} · {t('onet_software_note', lang)}"
                )

            continue

        if group == "gap":

            gap = item.get("gap")

            if gap is not None:
                gap_text = f"{float(gap):.1f}"
            else:
                gap_text = "—"

            st.markdown(
                f"**{skill}** · {group_label(category, lang)}  \n"
                f"{t('current_level', lang)} {user_text}/5 · "
                f"{t('role_benchmark', lang)} {target_text}/5 · "
                f"{t('gap', lang)} {gap_text}"
            )

        else:

            st.markdown(
                f"**{skill}** · {group_label(category, lang)}  \n"
                f"{t('self_rated', lang)} {user_text}/5 · "
                f"{t('role_benchmark', lang)} {target_text}/5"
            )



def render_technology_fit(items: list[dict], role: str) -> None:
    """Show self-reported tools that also appear in this role's O*NET software data."""
    tech_items = [item for item in items if item.get("group") == "Technology"][:5]
    if not tech_items:
        st.caption(p2copy("no_tech_fit"))
        return

    for item in tech_items:
        label = safe_text(_visual_term(item))
        badge_text = _technology_badges(role, item.get("skill", ""))
        st.markdown(
            f'<div class="tech-gap-card tech-fit-card">'
            f'<div class="tech-gap-head"><strong>{label}</strong>'
            f'<span class="tech-fit-badge">✓ {safe_text(p2copy("already_used"))}</span></div>'
            f'<div class="tech-gap-note">{safe_text(badge_text)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def apply_gdelt_to_scenarios(
    scenarios: list[dict],
    gdelt_signals: dict,
) -> list[dict]:
    updated_scenarios = []

    for scenario in scenarios:
        row = dict(scenario)

        role = row.get("role", "")

        ai_signal = get_role_ai_signal(role, gdelt_signals)

        attention_score = ai_signal.get("score")

        row["gdelt_attention_score"] = attention_score
        row["gdelt_direction"] = ai_signal.get("direction", "Insufficient signal")
        row["gdelt_topics"] = ai_signal.get("topics", [])

        if attention_score is not None:
            # 50 = neutral attention.
            # Convert GDELT score into a centred -1 to +1 signal.
            centred_signal = (attention_score - 50) / 50

            # Team-defined scenario sensitivity.
            moderate_adjustment = centred_signal * 5

            fast_adjustment = centred_signal * 10

            moderate_original = row.get("moderate_ai_disruption")

            fast_original = row.get("fast_ai_disruption")

            if moderate_original is not None:
                row["moderate_ai_disruption"] = round(
                    max(0, min(100, moderate_original + moderate_adjustment)), 1
                )

            if fast_original is not None:
                row["fast_ai_disruption"] = round(
                    max(0, min(100, fast_original + fast_adjustment)), 1
                )

            row["gdelt_moderate_adjustment"] = round(moderate_adjustment, 1)

            row["gdelt_fast_adjustment"] = round(fast_adjustment, 1)

        else:
            row["gdelt_moderate_adjustment"] = None

            row["gdelt_fast_adjustment"] = None

        updated_scenarios.append(row)

    return updated_scenarios


def run_assessment(profile: dict, assessment_language=None) -> dict:
    language_code = assessment_language or lang
    base_matches = load_matches(profile)
    scored_matches = [
        match for match in base_matches if match.get("overall") is not None
    ]

    pending_keys = []
    gdelt_signals, pending = get_background_value(
        "gdelt", lambda: add_backup_signals(get_ai_skill_signals()), load_gdelt_cache() or {}, ttl=300,
    )
    gdelt_signals = normalize_signals(gdelt_signals)
    if pending:
        pending_keys.append("gdelt")

    market: dict = {
        "jobs": [],
        "source": "Himalayas + Remotive job-market APIs",
        "fetched_at": None,
        "from_cache": False,
        "stale": True,
        "error": None,
        "listings_analysed": 0,
        "next_refresh_at": None,
    }
    market_error = None
    try:
        market, pending = get_background_value(
            "market", fetch_job_data, cached_job_data(),
        )
        if pending:
            pending_keys.append("market")
    except Exception as error:
        market_error = (
            "The market-data service could not be reached. Career matching is "
            f"still available. ({type(error).__name__})"
        )
    jobs = market.get("jobs") or []
    try:
        role_trends = analyse_role_trends(jobs)
        radar = analyse_skill_radar(jobs)
    except Exception:
        role_trends = {}
        radar = []
        market_error = market_error or (
            "Market signals could not be analysed for this assessment."
        )

    future_matches = apply_trends_to_matches(scored_matches, role_trends)
    top_matches = future_matches[:3]
    scenarios = build_scenario_comparison(top_matches)

    scenarios = apply_gdelt_to_scenarios(scenarios, gdelt_signals)
    paths: dict[str, list[dict]] = {}
    impacts: dict[str, dict] = {}
    explanations: dict[str, dict] = {}
    for index, match in enumerate(top_matches):
        role = match.get("role", "")
        path = build_learning_path(match)
        impact = get_match_sdg_impact(match)
        paths[role] = path
        impacts[role] = impact
        if index == 0 and not pending_keys:
            try:
                explanation_key = "explanation:" + hashlib.sha256(
                    json.dumps([profile, match, language_code], sort_keys=True, default=str).encode()
                ).hexdigest()
                explanations[role], pending = get_background_value(
                    explanation_key,
                    lambda p=profile, m=match, lp=path, si=impact, lc=language_code:
                        explain_recommendation(p, m, learning_path=lp, sdg_impact=si, language=lc),
                    {"text": fallback_explanation(match, language_code), "source": "Rule-based fallback"},
                )
                if pending:
                    pending_keys.append(explanation_key)
            except Exception:
                explanations[role] = {
                    "text": fallback_explanation(match, language_code),
                    "source": "Rule-based fallback",
                }
        else:
            explanations[role] = {
                "text": fallback_explanation(match, language_code),
                "source": "Rule-based fallback for additional matches",
            }
    return {
        "profile": profile,
        "base_matches": base_matches,
        "matches": top_matches,
        "role_trends": role_trends,
        "radar": radar,
        # GDELT AI / technology signals
        "gdelt_signals": gdelt_signals,
        "market": market,
        "market_error": market_error or market.get("error"),
        "scenarios": scenarios,
        "paths": paths,
        "impacts": impacts,
        "explanations": explanations,
        "language": language_code,
        "pending_keys": pending_keys,
        "ai_retry_at": (
            time.monotonic() + RETRY_COOLDOWN + 5
            if "gdelt" not in pending_keys and any(
                gdelt_signals.get(topic, {}).get("direction", "Unavailable") == "Unavailable"
                for topic in TECH_QUERIES
            ) else None
        ),
        "created_at": datetime.now().strftime("%d/%m/%Y, %H:%M"),
    }


if "assessment" not in st.session_state:
    st.session_state.assessment = None
if "assessment_error" not in st.session_state:
    st.session_state.assessment_error = None


st.markdown(
    f"""
    <div class="masthead">
      <div class="brand">
        <span class="brand-mark"></span>
        {safe_text(t("brand", lang))}
      </div>
      <div class="masthead-note">
        {safe_text(t("masthead_note", lang))}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Your Job Buddy. Every career starts somewhere")

st.markdown(
    f'<div class="hero-kicker">{safe_text(t("hero_kicker", lang))}</div>',
    unsafe_allow_html=True,
)
st.title(t("hero_title", lang))
st.markdown(
    f'<div class="hero-copy">{safe_text(t("hero_copy", lang))}</div>',
    unsafe_allow_html=True,
)

feature_col1, feature_col2, feature_col3 = st.columns(3, gap="medium")
with feature_col1:
    st.markdown(
        f'<div class="feature-card"><div class="feature-icon">🎯</div>'
        f'<div class="feature-title">{safe_text(vcopy("career_match"))}</div>'
        f'<div class="feature-copy">{safe_text(vcopy("career_match_copy"))}</div></div>',
        unsafe_allow_html=True,
    )
with feature_col2:
    st.markdown(
        f'<div class="feature-card"><div class="feature-icon">📊</div>'
        f'<div class="feature-title">{safe_text(vcopy("market_insight"))}</div>'
        f'<div class="feature-copy">{safe_text(vcopy("market_insight_copy"))}</div></div>',
        unsafe_allow_html=True,
    )
with feature_col3:
    st.markdown(
        f'<div class="feature-card"><div class="feature-icon">🧭</div>'
        f'<div class="feature-title">{safe_text(vcopy("learning_path"))}</div>'
        f'<div class="feature-copy">{safe_text(vcopy("learning_path_copy"))}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown(
    f'<div class="section-kicker">{safe_text(t("starting_point", lang))}</div>',
    unsafe_allow_html=True,
)
st.header(t("build_profile", lang))
st.caption(t("profile_instruction", lang))

try:
    available_technologies = sorted(
        {
            str(item).strip()
            for item in get_available_technologies()
            if str(item).strip()
        },
        key=str.casefold,
    )
except Exception:
    available_technologies = []

try:
    unavailable_datasets = [
        item["name"] for item in get_data_health() if not item["available"]
    ]
except Exception:
    unavailable_datasets = []
if unavailable_datasets:
    st.warning(
        tf("onet_unavailable", lang, datasets=", ".join(unavailable_datasets))
    )

st.markdown(f'<div class="visual-label">01 · {safe_text(vcopy("intake"))}</div>', unsafe_allow_html=True)
intake_method = st.radio(
    t("choose_intake", lang),
    options=[
        "No-CV Questionnaire",
        "Upload CV",
    ],
    format_func=lambda value: (
        t("no_cv", lang)
        if value == "No-CV Questionnaire"
        else t("upload_cv", lang)
    ),
    horizontal=True,
    key="intake_method",
)
cv_text = ""

cv_suggestions = {
    "skills": [],
    "knowledge": [],
    "technologies": [],
}


if intake_method == "Upload CV":

    st.caption(t("privacy_note", lang))

    uploaded_cv = st.file_uploader(
        t("upload_your_cv", lang),
        type=[
            "pdf",
            "docx",
            "txt",
        ],
        help=t("cv_help", lang),
        key="uploaded_cv",
    )

    if uploaded_cv is not None:

        cv_text = extract_cv_text(
            uploaded_cv
        )

        if cv_text.strip():

            cv_suggestions = detect_cv_items(
                cv_text,
                available_technologies,
            )
            cv_fingerprint = hashlib.md5(
                uploaded_cv.getvalue()
            ).hexdigest()

            if st.session_state.get(
                "loaded_cv_fingerprint"
            ) != cv_fingerprint:

                st.session_state[
                    "technologies"
                ] = cv_suggestions[
                    "technologies"
                ]

                st.session_state[
                    "selected_skills"
                ] = cv_suggestions[
                    "skills"
                ]

                st.session_state[
                    "selected_knowledge"
                ] = cv_suggestions[
                    "knowledge"
                ]

                st.session_state[
                    "loaded_cv_fingerprint"
                ] = cv_fingerprint

            st.success(t("cv_success", lang))

            st.caption(
                tf(
                    "detected_summary",
                    lang,
                    skills=len(cv_suggestions["skills"]),
                    knowledge=len(cv_suggestions["knowledge"]),
                    tools=len(cv_suggestions["technologies"]),
                )
            )

            with st.expander(
                t("see_detected", lang),
                expanded=True,
            ):
                if cv_suggestions["skills"]:
                    st.markdown(f"**{t('skills_detected', lang)}**")
                    render_chips(
                        [term_label(value, lang) for value in cv_suggestions["skills"]],
                        "skill",
                    )
                else:
                    st.caption(t("no_skills_detected", lang))

                if cv_suggestions["knowledge"]:
                    st.markdown(f"**{t('knowledge_detected', lang)}**")
                    render_chips(
                        [term_label(value, lang) for value in cv_suggestions["knowledge"]],
                        "knowledge",
                    )
                else:
                    st.caption(t("no_knowledge_detected", lang))

                if cv_suggestions["technologies"]:
                    st.markdown(f"**{t('tools_detected', lang)}**")
                    render_chips(cv_suggestions["technologies"], "tool")
                else:
                    st.caption(t("no_tools_detected", lang))

                st.caption(t("cv_review_note", lang))


        else:

            st.warning(t("cv_extract_failed", lang))


st.markdown("---")
st.markdown(f'<div class="visual-label">02 · {safe_text(vcopy("context"))}</div>', unsafe_allow_html=True)
st.subheader(t("your_context", lang))

context_col1, context_col2 = st.columns(
    2,
    gap="large",
)

with context_col1:

    user_type = st.selectbox(
        t("career_stage", lang),
        options=list(USER_TYPES.keys()),
        format_func=lambda value: option_label(value, USER_TYPES, lang),
        help=t("context_help", lang),
        key="user_type",
    )

    background = st.selectbox(
        t("degree_background", lang),
        options=list(BACKGROUNDS.keys()),
        format_func=lambda value: option_label(value, BACKGROUNDS, lang),
        help=_score_copy("background_help", lang),
        key="background",
    )

with context_col2:

    experience = st.selectbox(
        t("experience_level", lang),
        options=list(EXPERIENCE_LEVELS.keys()),
        format_func=lambda value: option_label(value, EXPERIENCE_LEVELS, lang),
        help=t("experience_help", lang),
        key="experience",
    )

    interests = st.multiselect(
        t("interests", lang),
        options=list(INTERESTS.keys()),
        format_func=lambda value: option_label(value, INTERESTS, lang),
        help=_score_copy("interests_help", lang),
        key="interests",
        placeholder=t("choose_options", lang),
    )


st.markdown("---")
st.markdown(f'<div class="visual-label">03 · {safe_text(vcopy("tools"))}</div>', unsafe_allow_html=True)

st.subheader(t("tools_used", lang))

technologies = st.multiselect(
    t("search_tools", lang),
    options=available_technologies,
    default=cv_suggestions[
        "technologies"
    ],
    help=t("tools_help", lang),
    key="technologies",
    placeholder=t("choose_options", lang),
)


st.markdown("---")
st.markdown(f'<div class="visual-label">04 · {safe_text(vcopy("skills"))}</div>', unsafe_allow_html=True)
st.subheader(t("skills_profile", lang))

st.caption(t("skills_caption", lang))

selected_skills = st.multiselect(
    t("select_skills", lang),
    options=sorted(
        QUESTIONNAIRE_SKILLS,
        key=str.casefold,
    ),
    default=cv_suggestions[
        "skills"
    ],
    key="selected_skills",
    placeholder=t("choose_options", lang),
    format_func=lambda value: term_label(value, lang),
)


skills = {}

if selected_skills:

    skill_columns = st.columns(
        2,
        gap="large",
    )

    for index, skill in enumerate(
        selected_skills
    ):

        with skill_columns[
            index % 2
        ]:

            skills[skill] = st.slider(
                f"{term_label(skill, lang)} — {t('rating', lang)}",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                key=f"selected_skill_{skill}",
            )

else:

    st.caption(t("select_skill_first", lang))


st.markdown("---")
st.markdown(f'<div class="visual-label">05 · {safe_text(vcopy("knowledge"))}</div>', unsafe_allow_html=True)
st.subheader(t("knowledge", lang))

st.caption(t("knowledge_caption", lang))

selected_knowledge = st.multiselect(
    t("select_knowledge", lang),
    options=sorted(
        QUESTIONNAIRE_KNOWLEDGE,
        key=str.casefold,
    ),
    default=cv_suggestions[
        "knowledge"
    ],
    key="selected_knowledge",
    placeholder=t("choose_options", lang),
    format_func=lambda value: term_label(value, lang),
)


knowledge = {}

if selected_knowledge:

    knowledge_columns = st.columns(
        2,
        gap="large",
    )

    for index, subject in enumerate(
        selected_knowledge
    ):

        with knowledge_columns[
            index % 2
        ]:

            knowledge[subject] = st.slider(
                f"{term_label(subject, lang)} — {t('rating', lang)}",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                key=f"selected_knowledge_{subject}",
            )


submitted = st.button(
    t("explore_matches", lang),
    type="primary",
    width="stretch",
)


if submitted:
    profile = {
        "user_type": user_type,
        "background": background.strip(),
        "experience": experience,
        "interests": interests,
        "skills": skills,
        "knowledge": knowledge,
        "technologies": technologies,
    }
    try:
        with st.spinner(t("comparing_profile", lang)):
            st.session_state.assessment = run_assessment(profile)
        st.session_state.assessment_error = None
        roles_now = [
            match.get("role") for match in st.session_state.assessment["matches"]
        ]
        if roles_now:
            st.session_state.selected_role = roles_now[0]
    except Exception as error:
        st.session_state.assessment = None
        st.session_state.assessment_error = type(error).__name__

if st.session_state.assessment_error:
    st.error(tf("assessment_error", lang, error=st.session_state.assessment_error))


@st.fragment(run_every="1s")
def refresh_pending_results():
    current = st.session_state.get("assessment")
    if not current:
        return
    keys = current.get("pending_keys", [])
    retry_at = current.get("ai_retry_at")
    if any_completed(keys) or (retry_at is not None and time.monotonic() >= retry_at):
        updated = run_assessment(current["profile"], current.get("language", "en"))
        updated["created_at"] = current["created_at"]
        st.session_state.assessment = updated
        st.rerun()
    salary_key = st.session_state.get("pending_salary")
    if salary_key and any_completed([salary_key]):
        st.session_state.pending_salary = None
        st.rerun()
    if keys or salary_key:
        st.info(t("background_refresh", lang))


refresh_pending_results()

assessment = st.session_state.assessment
if assessment:
    st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-kicker">{safe_text(t("evidence_suggests", lang))}</div>',
        unsafe_allow_html=True,
    )
    st.header(t("future_matches", lang))
    st.caption(
        tf(
            "assessment_saved",
            lang,
            time=assessment.get("created_at", ""),
        )
    )

    market = assessment["market"]
    if assessment.get("market_error"):
        st.warning(
            t("market_failure", lang)
        )
    elif market.get("stale"):
        st.warning(
            t("market_stale_warning", lang)
        )

    if market.get("from_cache"):
        cache_note = t("market_cached", lang)
        if market.get("stale"):
            cache_note += " · " + t("stale", lang)
    else:
        cache_note = t("market_returned", lang)
    st.markdown(
        f'<div class="note-panel"><strong>{safe_text(cache_note)}</strong> · '
        f"{safe_text(market.get('source') or t('unavailable', lang))} · "
        f"{int(market.get('listings_analysed') or 0)} {t('listings_analysed', lang)} · "
        f"{t('sample_timestamp', lang)}: {safe_text(display_timestamp(market.get('fetched_at')))}."
        + (
            f" {t('next_refresh_after', lang)}: {safe_text(display_timestamp(market.get('next_refresh_at')))}."
            if market.get("next_refresh_at")
            else ""
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    matches = assessment["matches"]
    if not matches:
        st.info(t("no_matches", lang))
    else:
        st.subheader(t("top_three", lang))
        st.caption(_score_copy("future_formula", lang))

        role_options = [match.get("role", "") for match in matches]
        if st.session_state.get("selected_role") not in role_options:
            st.session_state.selected_role = role_options[0]

        # Visual summary cards. Clicking the button under a card selects that role
        # and immediately shows one detailed panel below.
        summary_cols = st.columns(3, gap="medium")
        for index, match in enumerate(matches, start=1):
            role = match.get("role", "Career option")
            display_role = role_label(role, lang)
            base = match.get("base_match")
            future = match.get("future_match", base)
            confidence = match.get("confidence")
            direction = match.get("trend_direction", "Insufficient signal")
            future_value = float(future) if future is not None else 0.0
            score_width = min(max(future_value, 0), 100)
            non_tech_strengths = [
                item for item in match.get("strengths", [])
                if item.get("group") != "Technology"
            ]
            strengths_html = _chip_html(non_tech_strengths, 3, "fit")
            market_label = signal_label(direction, lang)
            confidence_text = display_score(confidence)
            selected_class = " selected-card" if st.session_state.selected_role == role else ""

            with summary_cols[index - 1]:
                st.markdown(
                    f'<div class="career-summary-card {"top-card" if index == 1 else ""}{selected_class}">'
                    f'<div class="career-card-rank">{safe_text(t("option", lang))} {index:02d}</div>'
                    f'<div class="career-card-title">{safe_text(display_role)}</div>'
                    f'<div class="career-big-score">{safe_text(display_score(future))}</div>'
                    f'<div class="career-score-label">{safe_text(t("future_match", lang))}</div>'
                    f'<div class="career-score-track"><div class="career-score-fill" style="width:{score_width:.1f}%"></div></div>'
                    f'<div class="career-meta"><span class="summary-badge">{safe_text(market_label)}</span>'
                    f'<span class="summary-badge confidence-badge">{safe_text(t("confidence", lang))} {safe_text(confidence_text)}</span></div>'
                    f'<div class="career-mini-label">{safe_text(p2copy("top_fit"))}</div>'
                    f'<div>{strengths_html or "—"}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    f'{p2copy("explore_option")} {index:02d}',
                    key=f"explore_role_{index}_{role}",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_role == role else "secondary",
                ):
                    st.session_state.selected_role = role
                    st.rerun()

        selected_role = st.session_state.selected_role
        selected_match = next(
            (match for match in matches if match.get("role") == selected_role),
            matches[0],
        )
        selected_index = role_options.index(selected_role) + 1
        display_role = role_label(selected_role, lang)
        base = selected_match.get("base_match")
        future = selected_match.get("future_match", base)
        direction = selected_match.get("trend_direction", "Insufficient signal")

        st.markdown("<div style='height:0.55rem'></div>", unsafe_allow_html=True)
        st.markdown(
            f"#### {safe_text(p2copy('details'))} · {safe_text(t('option', lang))} {selected_index:02d} — {safe_text(display_role)}"
        )

        with st.container(border=True):
            score_cols = st.columns(3)
            score_cols[0].metric(t("base_match", lang), display_score(base))
            score_cols[1].metric(
                t("future_match", lang),
                display_score(future),
                help=_score_copy("future_help", lang),
            )
            score_cols[2].metric(
                t("confidence", lang), display_score(selected_match.get("confidence"))
            )

            strength_col, gap_col = st.columns(2, gap="large")
            with strength_col:
                st.markdown(f"#### {t('evidence_fit', lang)}")
                all_strengths = selected_match.get("strengths", [])
                non_tech_strengths = [
                    item for item in all_strengths if item.get("group") != "Technology"
                ]
                strength_chips = _chip_html(non_tech_strengths, 5, "fit")
                if strength_chips:
                    st.markdown(
                        f'<div class="visual-panel">{strength_chips}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(t("no_strengths", lang))

                st.markdown(f"#### {safe_text(p2copy('technology_fit'))}")
                render_technology_fit(all_strengths, selected_role)

                st.markdown(f"**{safe_text(p2copy('market_signal'))}**")
                render_signal_badge(direction)
                if selected_match.get("trend_adjusted"):
                    st.caption(
                        tf(
                            "evidence_sample",
                            lang,
                            count=selected_match.get("trend_sample_count", 0),
                            score=display_score(selected_match.get("trend_score")),
                        )
                    )
                else:
                    st.caption(t("not_enough_posting", lang))

            with gap_col:
                st.markdown(f"#### {safe_text(p2copy('priority_gaps'))}")
                render_gap_visual(selected_match.get("gaps", []), selected_role)

            description = selected_match.get("description")
            if description:
                with st.expander(p2copy("role_overview")):
                    st.write(role_description(selected_role, description, lang))

            with st.expander(p2copy("score_breakdown")):
                component_scores = selected_match.get("component_scores") or {}
                component_coverages = selected_match.get("component_coverages") or {}
                component_names = {
                    "essential": t("essential_skills", lang),
                    "transferable": t("transferable_skills", lang),
                    "knowledge": t("knowledge", lang),
                    "technology": t("workplace_software", lang),
                }
                component_rows = []
                for key, label in component_names.items():
                    component_rows.append(
                        {
                            t("assessment_component", lang): label,
                            t("alignment", lang): display_score(component_scores.get(key)),
                            t("evidence_coverage", lang): display_score(
                                component_coverages.get(key)
                            ),
                        }
                    )
                st.dataframe(component_rows, hide_index=True, width="stretch")
                st.caption(t("score_formula_note", lang))

            explanation = assessment["explanations"].get(selected_role, {})
            if assessment.get("language", "en") != lang or explanation.get("source") != "RunPod":
                explanation = {
                    "text": fallback_explanation(selected_match, lang),
                    "source": "Rule-based fallback",
                }
            with st.expander(p2copy("why_recommended")):
                st.write(
                    explanation.get("text")
                    or fallback_explanation(selected_match, lang)
                )
                st.caption(
                    f"{t('explanation_source', lang)}: "
                    f"{'RunPod' if explanation.get('source') == 'RunPod' else t('rule_based_localized', lang)}"
                )
                if explanation.get("source") == "RunPod":
                    st.caption(t("runpod_note", lang))

        salary_key = f"salary:{selected_role}"
        salary, salary_pending = get_background_value(
            salary_key, lambda role=selected_role: get_salary_benchmark(role),
            {"available": False},
        )
        st.session_state.pending_salary = salary_key if salary_pending else None

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-kicker">{safe_text(t("malaysia_context", lang))}</div>',
            unsafe_allow_html=True,
        )
        st.header(t("salary_context", lang))

        if salary.get("available"):
            salary_cols = st.columns([1, 1, 1.25], gap="medium")
            with salary_cols[0]:
                st.markdown(
                    f'<div class="salary-hero-card"><div class="career-mini-label">{safe_text(t("median_salary", lang))}</div>'
                    f'<div class="salary-amount">RM {int(salary["median"]):,}</div>'
                    f'<div class="salary-label">{safe_text(p3copy("salary_note"))}</div></div>',
                    unsafe_allow_html=True,
                )
            with salary_cols[1]:
                st.markdown(
                    f'<div class="salary-hero-card"><div class="career-mini-label">{safe_text(t("mean_salary", lang))}</div>'
                    f'<div class="salary-amount">RM {int(salary["mean"]):,}</div>'
                    f'<div class="salary-label">{safe_text(p3copy("salary_note"))}</div></div>',
                    unsafe_allow_html=True,
                )
            with salary_cols[2]:
                industry_text = industry_label(salary["industry_label"], lang)
                st.markdown(
                    f'<div class="context-card"><div class="career-mini-label">{safe_text(p3copy("industry_context"))}</div>'
                    f'<div class="context-value">{safe_text(industry_text)}</div>'
                    f'<div class="signal-small">MSIC {safe_text(salary["industry_section"])} · '
                    f'{safe_text(p3copy("benchmark_year"))}: {safe_text(salary["year"])}</div></div>',
                    unsafe_allow_html=True,
                )
            with st.expander(p3copy("source_method")):
                st.caption(t("salary_source_note", lang))
        elif salary_pending:
            st.info(t("salary_loading", lang))
        else:
            st.info(t("salary_unavailable", lang))

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-kicker">{safe_text(t("plan_forward", lang))}</div>',
            unsafe_allow_html=True,
        )
        st.header(
            tf(
                "learning_pathway_for",
                lang,
                role=role_label(selected_role, lang),
            )
        )
        selected_path = assessment["paths"].get(selected_role, [])
        if selected_path:
            st.caption(t("learning_caption", lang))
            display_path = _diversify_learning_path(selected_path)
            path_groups = list(dict.fromkeys(str(item.get("group", "Skill")) for item in display_path))
            if len(path_groups) > 1:
                st.caption(p3copy("learning_mix_note"))
            elif path_groups:
                st.caption(
                    f"{p3copy('learning_focus_note')} "
                    f"{group_label(path_groups[0], lang)}."
                )
            for display_index, item in enumerate(display_path, start=1):
                step_no = display_index
                gap_value = float(item.get("gap", 0) or 0)
                weeks = item.get("estimated_weeks", "—")
                skill_label = term_label(item.get("skill", ""), lang)
                group_text = group_label(item.get("group", "Skill"), lang)
                st.markdown(
                    f'<div class="learning-step-card">'
                    f'<div class="learning-step-head"><div style="display:flex;gap:.7rem;align-items:flex-start;">'
                    f'<span class="learning-step-no">{step_no:02d}</span>'
                    f'<div><div class="learning-step-title">{safe_text(skill_label)}</div>'
                    f'<div class="learning-step-meta">'
                    f'<span class="learning-meta-pill">{safe_text(group_text)}</span>'
                    f'<span class="learning-meta-pill">{safe_text(p3copy("gap_label"))}: {gap_value:.1f}</span>'
                    f'<span class="learning-meta-pill">{safe_text(p3copy("weeks_label"))}: {safe_text(weeks)} {safe_text(p3copy("weeks_short"))}</span>'
                    f'</div></div></div></div></div>',
                    unsafe_allow_html=True,
                )
                resource_url = item.get("source_url")
                if resource_url:
                    st.markdown(
                        f"**{safe_text(p3copy('resource_label'))}:** "
                        f"[{safe_text(item.get('resource_title', 'Verified learning resource'))}]"
                        f"({resource_url}) · {safe_text(item.get('provider', ''))} · "
                        f"{safe_text(resource_cost_label(item.get('resource_cost', ''), lang))}"
                    )
                else:
                    st.caption(p3copy("resource_pending"))
        else:
            st.info(t("no_learning_path", lang))

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-kicker">{safe_text(t("work_transition", lang))}</div>',
            unsafe_allow_html=True,
        )
        st.header(t("ai_attention", lang))

        gdelt_signals = assessment.get("gdelt_signals", {})
        if "gdelt" in assessment.get("pending_keys", []):
            st.info(t("ai_trends_loading", lang))
        elif not gdelt_signals or any(
            signal.get("direction") == "Unavailable"
            for signal in gdelt_signals.values()
        ):
            st.warning(t("ai_trends_limited", lang))

        role_ai_signal = get_role_ai_signal(selected_role, gdelt_signals)
        direction = role_ai_signal.get("direction", "Insufficient signal")
        score = role_ai_signal.get("score")
        topics = role_ai_signal.get("topics", [])

        ai_cols = st.columns([1, 1, 1.4], gap="medium")
        with ai_cols[0]:
            direction_label = signal_label(direction, lang)
            direction_icon = "↑" if direction == "Rising" else "↓" if direction == "Declining" else "→" if direction == "Stable" else "·"
            st.markdown(
                f'<div class="signal-summary-card"><div class="career-mini-label">{safe_text(p3copy("ai_snapshot"))}</div>'
                f'<div class="signal-number">{safe_text(direction_icon)} {safe_text(direction_label)}</div>'
                f'<div class="signal-small">{safe_text(role_label(selected_role, lang))}</div></div>',
                unsafe_allow_html=True,
            )
        with ai_cols[1]:
            score_text = f"{float(score):.1f}/100" if score is not None else t("unavailable", lang)
            st.markdown(
                f'<div class="signal-summary-card"><div class="career-mini-label">{safe_text(p3copy("attention_label"))}</div>'
                f'<div class="signal-number">{safe_text(score_text)}</div>'
                f'<div class="signal-small">{safe_text(p3copy("not_prediction"))}</div></div>',
                unsafe_allow_html=True,
            )
        with ai_cols[2]:
            topic_text = " · ".join(tech_label(topic, lang) for topic in topics) if topics else t("unavailable", lang)
            st.markdown(
                f'<div class="signal-summary-card"><div class="career-mini-label">{safe_text(p3copy("topics_label"))}</div>'
                f'<div class="context-value">{safe_text(topic_text)}</div>'
                f'<div class="signal-small">GDELT / backup attention evidence</div></div>',
                unsafe_allow_html=True,
            )

        if any(signal.get("source") == HN_SOURCE for signal in gdelt_signals.values()):
            st.caption(f"ℹ️ {p3copy('backup_short')}")

        gdelt_rows = []
        gdelt_chart_rows = []
        for skill, signal in gdelt_signals.items():
            change = signal.get("change")
            missing = signal.get("direction") == "Unavailable"
            label = tech_label(skill, lang)
            gdelt_rows.append(
                {
                    t("technology_signal", lang): label,
                    t("ai_trend_source", lang): signal.get("source", "GDELT"),
                    t("ai_trend_query", lang): signal.get("query", TECH_QUERIES.get(skill, "")),
                    t("ai_trend_period", lang): (
                        f"{signal['period_start']} – {signal['period_end']}"
                        if signal.get("period_start") and signal.get("period_end")
                        else t("ai_trend_provider_period", lang)
                    ),
                    t("direction", lang): signal_label(signal.get("direction", "Unavailable"), lang),
                    t("recent_14_days", lang): str(signal.get("recent", 0)) if not missing else t("unavailable", lang),
                    t("previous_14_days", lang): str(signal.get("previous", 0)) if not missing else t("unavailable", lang),
                    t("change", lang): f"{change:+.1f}%" if change is not None else t("unavailable", lang),
                }
            )
            if change is not None:
                gdelt_chart_rows.append({"Technology": label, "Change (%)": float(change)})

        if gdelt_chart_rows:
            st.markdown(f"#### {p3copy('trend_chart')}")
            st.caption(p3copy("trend_chart_help"))
            gdelt_chart_df = pd.DataFrame(gdelt_chart_rows)
            st.bar_chart(
                gdelt_chart_df,
                x="Technology",
                y="Change (%)",
                horizontal=True,
                sort=False,
                height=max(260, 48 * len(gdelt_chart_df)),
            )
        else:
            st.info(t("ai_unavailable", lang))

        with st.expander(p3copy("ai_details")):
            if gdelt_rows:
                st.dataframe(gdelt_rows, hide_index=True, width="stretch")
            else:
                st.caption(t("ai_unavailable", lang))
            st.caption(t("gdelt_source_note", lang))

        st.markdown(f"#### {p3copy('market_snapshot')}")
        radar = assessment["radar"]
        radar_rows = []
        radar_chart_rows = []
        if radar:
            for row in radar:
                demand_index = row.get("demand_index")
                label = term_label(row.get("skill", ""), lang)
                radar_rows.append(
                    {
                        t("skill_signal", lang): label,
                        t("current_market_signal", lang): signal_label(row.get("direction", "Insufficient signal"), lang),
                        t("recent_mentions", lang): row.get("recent", 0),
                        t("relative_demand", lang): f"{demand_index:.1f}/100" if demand_index is not None else t("unavailable", lang),
                        t("evidence_sample_short", lang): row.get("sample_count", 0),
                    }
                )
                if demand_index is not None:
                    radar_chart_rows.append({"Skill": label, "Demand": float(demand_index)})

            if radar_chart_rows:
                market_chart_df = (
                    pd.DataFrame(radar_chart_rows)
                    .sort_values("Demand", ascending=False)
                    .head(8)
                )
                st.markdown(f"#### {p3copy('demand_chart')}")
                st.bar_chart(
                    market_chart_df,
                    x="Skill",
                    y="Demand",
                    horizontal=True,
                    sort=False,
                    height=max(300, 44 * len(market_chart_df)),
                )

            with st.expander(p3copy("market_details")):
                st.dataframe(
                    radar_rows,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        t("recent_mentions", lang): st.column_config.NumberColumn(format="%d"),
                        t("evidence_sample_short", lang): st.column_config.NumberColumn(format="%d"),
                    },
                )
        else:
            st.info(t("job_radar_unavailable", lang))

        with st.expander(p3copy("source_method")):
            st.caption(
                tf(
                    "market_source_caption",
                    lang,
                    source=market.get("source") or t("unavailable", lang),
                    count=int(market.get("listings_analysed") or 0),
                    timestamp=display_timestamp(market.get("fetched_at")),
                )
            )
            st.markdown(
                "[Himalayas Remote Jobs API](https://himalayas.app/docs/remote-jobs-api) · "
                "[Remotive Public Jobs API](https://remotive.com/api/remote-jobs)"
            )
            st.caption(p3copy("not_prediction"))

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-kicker">{safe_text(t("possibilities", lang))}</div>',
            unsafe_allow_html=True,
        )
        st.header(t("scenarios", lang))
        st.write(t("scenario_intro", lang))
        st.caption(
            t("scenario_method", lang)
        )
        scenario_by_role = {row.get("role"): row for row in assessment["scenarios"]}
        chosen_scenario = scenario_by_role.get(selected_role)
        if chosen_scenario:
            scenario_cols = st.columns(2)
            scenario_cols[0].metric(
                t("moderate_ai", lang),
                display_score(chosen_scenario.get("moderate_ai_disruption")),
            )
            scenario_cols[1].metric(
                t("fast_ai", lang),
                display_score(chosen_scenario.get("fast_ai_disruption")),
            )
            gdelt_score = chosen_scenario.get("gdelt_attention_score")

            moderate_adjustment = chosen_scenario.get("gdelt_moderate_adjustment")

            fast_adjustment = chosen_scenario.get("gdelt_fast_adjustment")

            trend_score = chosen_scenario.get("trend_score")

            if trend_score is not None:
                trend_text = display_score(trend_score)
            else:
                trend_text = t("insufficient_signal", lang)

            scenario_summary = tf("scenario_summary", lang,
                                  base=display_score(chosen_scenario.get("base_match")),
                                  demand=trend_text)

            if gdelt_score is not None:
                scenario_summary += f" · {t('gdelt_attention_short', lang)}: {gdelt_score:.1f}/100"

                if moderate_adjustment is not None:
                    scenario_summary += (
                        f" · {t('moderate_adjustment', lang)}: {moderate_adjustment:+.1f} {t('points_short', lang)}"
                    )

                if fast_adjustment is not None:
                    scenario_summary += (
                        f" · {t('fast_adjustment', lang)}: {fast_adjustment:+.1f} {t('points_short', lang)}"
                    )

            st.caption(scenario_summary)
            with st.expander(t("scenario_weights", lang)):
                for scenario_label, weight_key in (
                    (t("moderate_change", lang), "moderate_weights"),
                    (t("fast_change", lang), "fast_weights"),
                ):
                    weights = chosen_scenario.get(weight_key) or {}
                    readable_weights = {
                        "base_match": t("base_match", lang),
                        "trend_score": t("current_posting_demand", lang),
                        "ai_technology_readiness": t("ai_technology_readiness", lang),
                    }
                    st.markdown(f"**{scenario_label}**")
                    if weights:
                        st.write(
                            " · ".join(
                                f"{readable_weights.get(key, key)} {value * 100:.0f}%"
                                for key, value in weights.items()
                            )
                        )
                    else:
                        st.caption(t("no_scenario_inputs", lang))
                st.caption(t("scenario_caption", lang))
        else:
            st.info(t("no_scenario", lang))

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-kicker">{safe_text(t("wider_contribution", lang))}</div>',
            unsafe_allow_html=True,
        )
        st.header(t("sdg_title", lang))
        impact = assessment["impacts"].get(selected_role, {})
        if impact.get("label"):
            st.caption(t("sdg_interpretive_label", lang))
        career_mappings = impact.get("career_mappings") or []
        if career_mappings:
            render_sdg_visual_cards(career_mappings, lang)
        else:
            st.info(t("sdg_mapping_unavailable", lang))
        st.caption(t("sdg_mapping_note", lang))
        st.markdown(f"#### {t('skill_contribution', lang)}")
        category_labels = {
            "essential": t("essential_skills", lang),
            "transferable": t("transferable_skills", lang),
            "knowledge": t("knowledge", lang),
            "technology": group_label("Technology", lang),
        }
        for category, label in category_labels.items():
            category_mappings = (impact.get("skill_categories") or {}).get(category, [])
            with st.expander(tf("relevant_sdgs", lang, label=label)):
                if category_mappings:
                    for mapping in category_mappings:
                        st.markdown(
                            f"**SDG {safe_text(mapping.get('number', ''))} · "
                            f"{safe_text(sdg_title_label(mapping.get('number'), mapping.get('title', ''), lang))}**  \n"
                            f"{safe_text(sdg_rationale_label(mapping.get('rationale', ''), lang))}  \n"
                            f"[{t('official_goal_reference', lang)}]({mapping.get('source_url', '')})"
                        )
                else:
                    st.caption(t("no_category_mapping", lang))

        st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-kicker">{safe_text(t("method", lang))}</div>',
            unsafe_allow_html=True,
        )
        st.header(t("sources", lang))
        st.markdown(
            f"[{tf('onet_source_line', lang, date=get_onet_source_date())}]"
            "(https://www.onetcenter.org/database.html)"
        )
        st.markdown(
            t("job_source_method", lang)
        )
        st.markdown(
            t("gdelt_source_method", lang)
        )

        st.markdown(
            t("dosm_source_method", lang)
        )

        with st.expander(t("how_to_read", lang), expanded=True):
            st.markdown(t("methodology_body", lang))
        st.markdown(f"**{t('important_disclaimers', lang)}**")
        st.markdown(t("disclaimer_body", lang))
    st.markdown(
        f'<div class="footer-note">{safe_text(t("footer", lang))}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="note-panel"><strong>{safe_text(t("results_here_title", lang))}</strong> '
        f'{safe_text(t("results_here_copy", lang))}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="footer-note"><strong>{safe_text(t("important_disclaimers", lang))}</strong><br>'
        f'{safe_text(t("disclaimer_body", lang)).replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )


