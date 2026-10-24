# SDC_Hackathon_Submission
# Project Name

JobBud
> Your job buddy for fresh graduates and career switchers, helping them discover suitable career paths and personalised reskilling steps for an AI-driven job market.
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

Fresh graduates and career switchers often struggle to identify suitable career paths, understand how AI is changing job-market demands and determine which skills they should develop next. With career information, industry trends and learning resources scattered across different platforms, users risk spending time on irrelevant upskilling while employers continue to face skills gaps. Without clearer career guidance and actionable learning plans, it becomes difficult for individuals to prepare for an evolving, AI-driven job market.

### Solution

JobBud is a future-ready career and reskilling platform that transforms users' existing skills into personalised career directions and actionable learning pathways. By allowing users to complete a skills questionnaire or upload their CV, JobBud extracts potential skills, knowledge areas and tools to build a structured profile, which users can review and rate themselves. It combines explainable career matching based on O*NET occupational data with job-market signals, AI disruption scenarios and prioritised skill-gap analysis to help users explore career opportunities and identify what to learn next. JobBud also incorporates Malaysian salary context and maps relevant career roles to the UN Sustainable Development Goals (SDGs) to encourage informed and purpose-driven career planning.

### Key Features

- **Automated CV-Assisted Profiling** — Parses uploaded PDF or DOCX CVs to suggest relevant skills, knowledge areas and tools, reducing repetitive data entry while allowing users to confirm suggestions and rate their own proficiency.
- **Explainable Career Matching & AI-Era Insights** — Matches users against 11 O*NET occupations using skills, knowledge and technology data, supplemented by available job-market signals and moderate-versus-fast AI disruption scenarios. Recommendations include matching scores, assessment confidence, strengths and skill gaps.
- **Personalised Reskilling Pathways & SDG Mapping** — Prioritises skill gaps for a selected career and recommends structured learning steps with estimated learning times and verified resources where available. Career roles are also mapped to relevant UN Sustainable Development Goals, with explanations and links to official references.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | HTML, CSS |
| Backend       | e.g. Python, Flask / FastAPI |
| Database      | O*NET |
| Hosting / Dev | Replit                       |

---

## Project Structure

```
.
├── docs/                    # Screenshots, diagrams
├── src/
│   ├── main.py              # Application entry point
│   └── utils.py             # Helper functions
├── submission/              # Required submission documents
│   ├── SDC2026_TeamName_Preliminary.pdf      # Preliminary submission
│   ├── SDC2026_TeamName_TechDeclaration.pdf  # Technology declaration
│   └── SDC2026_TeamName_Replit_POU.pdf       # Replit proof of use
├── tests/
│   └── test_utils.py        # Unit tests
├── .env.example             # Example environment variables
├── .gitignore
├── .replit                  # Replit run configuration
├── LICENSE
├── requirements.txt         # Python dependencies
└── README.md
```

### Architecture

```
User ──► Replit (App / API) ──► RunPod Endpoint (GPU model)
                │
                └──► Response returned to user
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@your-username/your-project), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab (🔒) and add the variables listed in `.env.example`:
   - `RUNPOD_API_KEY`
   - `RUNPOD_ENDPOINT_ID`
3. Click **Run**. Replit uses the `.replit` file to start `python src/main.py`.

### Option 2 — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/your-username/your-project.git
cd your-project

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env            # then fill in your values

# 5. Run the app
python src/main.py
```

### Run Tests

```bash
python -m unittest discover tests
```

---

## How We Use Replit *(Required)*

Describe how your team used Replit. For example:

- **Development:** Collaborative coding in a shared Repl using Multiplayer.
- **Hosting:** The app is deployed with Replit Deployments at the Live Demo link above.
- **Secrets:** API keys are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/SDC2026_TeamName_Replit_POU.pdf`](submission/SDC2026_TeamName_Replit_POU.pdf)

---

## Challenges & Learnings

Our biggest hurdle was handling compilation and integration errors where code failed or functioned only partially. As first-time hackathon participants, troubleshooting these technical roadblocks under tight time constraints was intense. We overcome this by leveraging AI-driven debugging tools and modern AI prompting to rapidly pinpoint bugs, refactor broken logic, and turn our non-functional components into a smooth, running website.

We learned that clear communication and proactive team structure are essential to executing an ambitious idea. Starting without prior hackathon experience, we navigated the initial uncertainty by establishing strong task division, supporting one another and holding frequent syncs to align our vision. Through this cooperation, we went from feeling overwhelmed to seamlessly co-creating JobBud.

Technically, we gained valuable experience in prompt engineering and utilizing Replit to build and scale big software concepts efficiently. Watching JobBud evolve from an abstract idea from scratch into a blooming, functional website capable of helping real people was an empowering experience that taught us the true value of team synergy and modern developer tools.

## Future Improvements

- [ ] Improvement 1
- [ ] Improvement 2

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
