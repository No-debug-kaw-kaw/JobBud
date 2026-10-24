# SDC_Hackathon_Submission
# JobBud

> Your job buddy for fresh graduates and career switchers, helping them discover suitable career paths and personalised reskilling steps for an AI-driven job market.
> 
> Every career starts somewhere.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | No debug kaw kaw |
| **Team Domain**        | Domain 1 |
| **SDG Track (1–17)**   | SDG 4 - Quality Education |
| **Team Leader**        | Po Rou Jing |
| **University**         | Universiti Malaya |
| **Number of Members**  | 5 |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/ngyy111000-beep/JobBud      |
| Live Demo         | https://sdc-army0709.replit.app                |
| Slide Deck        | https://example.com/slides                     |
| Demo Video        | https://example.com/demo-video                 |

---

## Overview

### Problem

Fresh graduates and career switchers navigating analytical, financial, and technical fields face a critical challenge: aligning their existing capabilities with rapidly changing industry requirements without clear, data-driven guidance. As automation, artificial intelligence, and data-intensive roles reshape career pathways, job seekers may struggle to assess their current skill readiness, identify transferable strengths, and understand specific competency gaps in areas such as quantitative analysis, complex problem-solving, systems thinking, and digital tools.
This challenge has broader economic and social implications. Limited access to transparent career guidance can contribute to career mismatch, underemployment, and inefficient workforce transitions, affecting productive employment under Sustainable Development Goal (SDG) 8 and lifelong skills development under SDG 4. TalentCorp’s workforce impact study further highlights the scale of workforce transformation in Malaysia, showing that technological and economic shifts are expected to significantly affect a substantial number of workers.
JobBud addresses this information gap by comparing user-provided skills and knowledge with structured occupational evidence, identifying development priorities, and presenting personalised reskilling pathways. The solution aims to support more informed career decisions while contributing to skills development, decent work, and innovation under SDGs 4, 8, and 9.

### Solution

JobBud is an intelligent web-based career guidance solution designed to help fresh graduates and career switchers navigate rapidly evolving job markets through transparent, evidence-based recommendations.
The application uses deterministic computational methods to compare user-provided skills, knowledge, and self-reported technology experience with structured occupational data from O*NET. It produces explainable career-alignment scores, identifies strengths and development priorities, and generates personalised reskilling pathways using verified or team-curated learning resources.
JobBud also incorporates updatable labour-market and technology signals from public sources, including current job postings and AI-related news attention, to provide additional market context. These signals are presented as indicators rather than guaranteed forecasts. Moderate and fast AI-disruption scenarios allow users to explore how career comparisons may change under different assumptions.
The prototype is developed in Python using Streamlit and deployed through Replit. An optional RunPod AI layer is designed to convert already-computed structured results into concise natural-language explanations without determining or modifying career scores.
Career recommendations remain informational guidance, with human judgement kept at the centre of career decisions.

### Key Features

- **Automated CV-Assisted Profiling** — Parses uploaded PDF or DOCX CVs to suggest relevant skills, knowledge areas and tools, reducing repetitive data entry while allowing users to confirm suggestions and rate their own proficiency.
- **Explainable Career Matching & AI-Era Insights** — Matches users against 11 O*NET occupations using skills, knowledge and technology data, supplemented by available job-market signals and moderate-versus-fast AI disruption scenarios. Recommendations include matching scores, assessment confidence, strengths and skill gaps.
- **Personalised Reskilling Pathways & SDG Mapping** — Prioritises skill gaps for a selected career and recommends structured learning steps with estimated learning times and verified resources where available. Career roles are also mapped to relevant UN Sustainable Development Goals, with explanations and links to official references.
- - **Multilingual Interface** — Supports English, Bahasa Melayu, and Chinese to make career guidance more accessible.
- **Privacy-Conscious Session Processing** — User assessment information is processed within the active session and is not intentionally stored in a persistent user database.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | Streamlit |
| Backend       | Python |
| Database      | Local CSV / JSON files |
| AI/Compute    | Rule-based matching and reskilling logic; O*NET occupational data |
| Hosting / Dev | Replit                       |

---

## Project Structure

```
JobBud/
├── src/
│   ├── app.py                 
│   ├── ai_explainer.py         
│   ├── ai_trend_sources.py     
│   ├── background_data.py      
│   ├── career_engine.py        
│   ├── gdelt_engine.py         
│   ├── i18n.py                 
│   ├── reskill_engine.py       
│   ├── salary_engine.py       
│   ├── scenario_engine.py     
│   ├── sdg_engine.py           
│   └── trend_engine.py        
│
├── data/
│   ├── occupation_data.csv
│   ├── essential_skills.csv
│   ├── transferable_skills.csv
│   ├── knowledge.csv
│   ├── software_skills.csv
│   └── related_occupations.csv
│
├── tests/
│   ├── test_ai_trend_recovery.py
│   ├── test_app_scenarios.py
│   ├── test_background_data.py
│   ├── test_cv_matching.py
│   ├── test_engines.py
│   ├── test_gdelt_engine.py
│   └── test_i18n.py
│
├── .env.example               
├── .gitignore                 
├── .replit                   
├── LICENSE
├── README.md
├── pyproject.toml         
└── uv.lock

```                

## Architecture

```text
User
  │
  ▼
Replit-hosted Streamlit Application
  │
  ├── Career Matching Engine
  │     └── O*NET Occupational Datasets
  │
  ├── Skill Gap Analysis
  │
  ├── Reskilling Pathway Engine
  │
  ├── Labour Market Trend Engine
  │     ├── Himalayas
  │     ├── Remotive
  │     ├── GDELT
  │     └── DOSM / OpenDOSM
  │
  ├── AI Disruption Scenario Engine
  │
  └── SDG Mapping Engine
  │
  ▼
Career Recommendations
Skill Gaps
Learning Pathways
Market Insights
```
JobBud uses a deterministic and explainable scoring approach for career matching. O*NET occupational data is combined with user-provided assessment information, while public labour-market sources provide additional market context.


## How to Run

### Option 1 — Access the Live Demo (Recommended)

1. Open the [JobBud Live Demo](https://sdc-army0709.replit.app ) project in Replit.
2. Once the application loads, complete the questionnaire or upload your CV to create your skills profile.
3. Explore your career matches, skill gaps, personalised reskilling pathways, salary benchmarks, AI disruption scenarios and SDG mapping.

Note: JobBud is a Python and Streamlit web application hosted on Replit. The live demo allows users to try the application directly without setting up the source code.

### Option 2 — Run Locally

Prerequisites
- Python 3.11 or newer
- uv
- Git

```bash
# 1. Clone the repository
git clone https://github.com/ngyy111000-beep/JobBud.git
cd JobBud

# 2. Install project dependencies
uv sync

# 3. Run the application
uv run streamlit run src/app.py
```

### Run Tests

```bash
python -m unittest discover tests
``` 
---

## How We Use Replit *(Required)*

Replit is used as the primary cloud-based development, testing, and deployment environment for JobBud.

- **Development:** Our team used Replit to develop, debug, and test the Streamlit application in a shared cloud-based workspace.
- **Integration:** Replit was used to integrate the career-matching engine, skill-gap analysis, reskilling pathway, labour-market signals, AI disruption scenarios, and SDG mapping into one application.
- **Testing:** Core application functions and supporting engines were tested within the Replit environment.
- **Hosting:** The JobBud Streamlit prototype is hosted through Replit, allowing the application to be accessed through a browser.
- **Dependency Management:** Project dependencies are managed using `pyproject.toml` and `uv.lock`.

📄 **Proof of Use:** submission/SDC_No debug kaw kaw_POU.pdf 

## Challenges & Learnings

One of our biggest challenges was integrating multiple components into a single working application within a limited hackathon timeframe. JobBud combines career matching, skill-gap analysis, reskilling pathways, labour-market signals, AI-disruption scenarios, SDG mapping, multilingual support, and external data sources. Some components worked independently but required additional debugging and testing when integrated into the complete Streamlit application.

As first-time hackathon participants, we learned the importance of clear task division, frequent communication, and continuous testing. Our team used Replit Agent to assist with code generation, debugging, troubleshooting, technical explanations, and documentation. However, AI-generated suggestions were reviewed, modified, and tested by the team before being integrated into the final prototype.

Technically, we gained practical experience in working with O*NET occupational datasets, integrating public APIs, developing transparent weighted scoring methods, structuring a modular Python application, and deploying a Streamlit application through Replit.

We also learned that different data sources must be interpreted carefully. O*NET is used as an occupational skills framework, current job-posting APIs provide market-presence signals, GDELT provides technology-attention signals, and AI-disruption scenarios are estimates based on predefined assumptions rather than guaranteed predictions.

Most importantly, we learned that career guidance should not simply provide a job recommendation. It should explain why a role may be suitable, identify skill gaps, and provide users with practical next steps for development.

## Future Improvements

- [ ] Expand career coverage beyond the current 11 occupations.
- [ ] Improve skill assessment to reduce reliance on self-reported ratings.
- [ ] Integrate more Malaysia-specific labour-market and salary data.
- [ ] Improve external API reliability, caching, and fallback mechanisms.
- [ ] Refine and validate AI-disruption scenarios using additional research and evidence.
- [ ] Conduct user testing with fresh graduates and career switchers.

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Po Rou Jing | Team Lead / Frontend | [@roujing0708](https://github.com/roujing0708) |
| Soo Yong Xin | Frontend / Backend | [@yongxinsoo-bit](https://github.com/yongxinsoo-bit) |
| Ng Yen Yi | Backend / Writer | [@ngyy111000-beep](https://github.com/ngyy111000-beep) |
| Joey Ng Chu Yee | Frontend / Backend | [@joeyng050321-ux](https://github.com/joeyng050321-ux) |
| Tan Joshuen | Ideation / Writer / Presenter | [@joshuen527](https://github.com/joshuen527) |

---

## Submission Checklist

- [/] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [ ] Replit used, with proof of use in `submission/`
- [ ] RunPod used, with proof of use in `submission/`
- [ ] Preliminary submission completed (`SDC2026_TeamName_Preliminary.pdf`)
- [ ] Technology declaration completed (`SDC2026_TeamName_TechDeclaration.pdf`)
- [ ] Submission files renamed with your team name (replace `TeamName`)
- [ ] "How to Run" steps verified
- [ ] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
