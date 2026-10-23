# SDC_Hackathon_Submission
# Project Name

> JobBud, your job buddy for university fresh graduates and career switchers. Every career starts somewhere.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | No Debug Kaw Kaw |
| **Team Domain**        | Domain 1 |
| **SDG Track (1–17)**   | SDG 4 - Quality Education |
| **Team Leader**        | Po Rou Jing |
| **University**         | Universiti Malaya |
| **Number of Members**  | 4 |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/ngyy111000-beep/JobBud      |
| Replit Project    | https://replit.com/@your-username/your-project |
| Live Demo         | https://your-project.replit.app                |
| RunPod Endpoint   | https://api.runpod.ai/v2/your-endpoint-id      |
| Slide Deck        | https://example.com/slides                     |
| Demo Video        | https://example.com/demo-video                 |

---

## Overview

### Problem

Over 60% of university fresh graduates and career switchers feel unprepared for an AI-driven job market where skills rapidly become obsolete and traditional career guidance falls behind. Without clear line-of-sight into future industry shifts, high-potential talent wastes months on outdated upskilling, while employers face widening skill gaps. Our platform solves this by using predictive AI to map emerging and declining roles, automatically generate personalized reskilling pathways and connect every skill to the 17 UN Sustainable Development Goals to guide purpose-driven careers.

### Solution

Our solution uses a focused AI stack to transform static resume data into dynamic, future-proof career pathways. By programmatically reading uploaded CVs, Natural Language Processing (NLP) extracts and categorizes the candidate’s tools used, skills profile, and knowledge areas into a structured baseline. Machine Learning models trained on labor market trends evaluate this baseline to forecast emerging roles and identify critical skill gaps. Generative AI then constructs personalized reskilling pathways, recommending targeted free online learning resources for each core area and mapping every skill directly to the 17 UN Sustainable Development Goals to guide sustainable career growth.

### Key Features

- **Automated CV Intelligence (Code Parser & NLP)** — Programmatically parses uploaded PDF resumes to identify and categorize candidate tools used, skills profiles and core knowledge areas into a standardized profile.
- **Predictive Skill-Gap Analysis (Machine Learning)** — Maps candidate tools and knowledge baselines against labor market datasets to predict emerging role demands and highlight precise skill gaps.
- **Dynamic Pathway & Resource Curation (Generative AI)** — Recommends personalized reskilling pathways with curated free learning resources while aligning every skill and role to the 17 UN Sustainable Development Goals.

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
├── runpod/
│   └── handler.py           # RunPod serverless handler (GPU workload)
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
| Po Rou Jing | Team Lead / Frontend | [@username](https://github.com/username) |
| Soo Yong Xin | Frontend / AI            | [@username](https://github.com/username) |
| Ng Yen Yi | AI / Backend        | [@username](https://github.com/username) |
| Joey Ng Chu Yee | AI / Backend        | [@username](https://github.com/username) |
| Tan Joshuen | AI / Backend         | [@username](https://github.com/username) |

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
