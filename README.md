# Blood Bank Management System

A mini-project (Django + SQLite) that organizes blood-bank information: donors, donations, blood inventory, blood requests, notifications, reports and administration.

## Project status: Sprint 1 + Sprint 2 implemented

All 34 user stories (US-01 to US-34) are implemented, connected and tested. See **[docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)**
for the story-by-story and FR-by-FR status (use it to show how much is done).

## Run it (3 minutes)

```
cd code
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo         # demo users, blood banks, donors, stock, a request
python manage.py runserver         # open http://127.0.0.1:8000/
python manage.py test              # 11 automated tests
```

Demo logins (created by `seed_demo`):

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin@12345` |
| Blood bank staff | `staff1` | `Staff@12345` |
| Donor (has a donor record) | `donor1` | `Donor@12345` |
| Requester / hospital | `hospital1` | `Hosp@12345` |

You can log in with either the username or the e-mail address.

## Project structure

```
Blood-Bank-Management-System/
├── README.md, FR and NFR.pdf, SRS Table *.pdf, Test cases.pdf, ...   (project documentation)
├── docs/IMPLEMENTATION_STATUS.md                                       (what is done, mapped to stories and FRs)
└── code/
    ├── manage.py, settings.py, requirements.txt
    ├── core/                    one file per user story: usNN_name.py = form + view + GUI page + URL
    │   ├── models.py            ALL shared tables (single source of truth for every story)
    │   ├── common.py            page layout, menu, form rendering, home page
    │   ├── urls.py              registers every story's URLs
    │   ├── us01 ... us34        Sprint 1 and Sprint 2 stories
    │   └── management/commands/seed_demo.py
    └── _original_submissions/   the team's earlier standalone files, kept untouched for reference (not used by the app)
```

Why the earlier files did not connect: every contributor used different model and field names (for example `date` vs `donation_date`, a text `blood_bank` vs a `BloodBank` table, quantity in ml vs units),
and there was no settings file, root URL file or `manage.py`. Now there is one shared `models.py`, one layout, and one URL registry. Inventory quantity is stored in **units** everywhere.

## Documentation

| Document | Description |
|---|---|
| [FR and NFR](FR%20and%20NFR.pdf) | Combined functional and non-functional requirements |
| [Functional Requirements - SRS Table](SRS%20Table%20-%20Functional%20Req%20-%20SRS.pdf) | Functional requirements in SRS table format |
| [Non-Functional Requirements - SRS Table](SRS%20Table%20-%20Non-Functional%20Req%20-%20SRS.pdf) | Non-functional requirements in SRS table format |
| [Security Requirements](Blood_Bank_Security_Requirements.docx) | Authentication, authorization, privacy and data protection requirements |
| [Test Cases](Test%20cases.pdf) | 160 planned test cases (16 FRs x 10) |
| [Implementation status](docs/IMPLEMENTATION_STATUS.md) | Implemented stories, FR coverage, known gaps |

## Contributors

Add the names of all project team members and their responsibilities here.
