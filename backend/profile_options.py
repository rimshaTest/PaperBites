"""
Fixed answer sets for the Profile Details form. Served to the client by GET /api/profile/options
(see api_server.py) rather than duplicated in the app, so the form and the server-side
validation in profile_validation.py can never drift apart. The one dynamic list - field of
study - comes from categories.current_categories() instead of being listed here.

Gender / sex / disability options follow the voluntary self-identification wording used on US
job applications (EEO-1 style gender, and the OFCCP Form CC-305 disability list). Every field
in this form is optional; gender and sex also offer "prefer not to say".
"""

OTHER = "Other"

# "Professional / self-directed" covers learners outside formal enrollment (working
# professionals, self-taught readers).
EDUCATION_LEVELS = [
    "High school",
    "Undergraduate",
    "Graduate",
    "Post-doctoral",
    "Professional / self-directed",
]

PREFER_NOT_TO_SAY = "Prefer not to say"

GENDERS = ["Man", "Woman", "Non-binary", PREFER_NOT_TO_SAY]

SEXES = ["Male", "Female", "Intersex", PREFER_NOT_TO_SAY]

# One checklist, as on the voluntary self-identification form: the condition list from Form
# CC-305 (mental, physical and chronic conditions together), plus "None" and "Other" (which
# takes a free-text description). Leaving it empty means "not answered". "None" can't be
# combined with other choices.
DISABILITY_NONE = "None"
DISABILITY_OTHER = OTHER
DISABILITY_CONDITIONS = [
    "Autism",
    "Autoimmune disorder (e.g. lupus, fibromyalgia, rheumatoid arthritis, HIV/AIDS)",
    "Blind or low vision",
    "Cancer (past or present)",
    "Cardiovascular or heart disease",
    "Celiac disease",
    "Cerebral palsy",
    "Deaf or serious difficulty hearing",
    "Diabetes",
    "Disfigurement (e.g. caused by burns, wounds, accidents, or congenital disorders)",
    "Epilepsy or other seizure disorder",
    "Gastrointestinal disorders (e.g. Crohn's disease, irritable bowel syndrome)",
    "Intellectual or developmental disability",
    "Mental health conditions (e.g. depression, bipolar disorder, anxiety disorder, PTSD)",
    "Missing limbs or partially missing limbs",
    "Mobility impairment, excluding wheelchair use",
    "Nervous system condition (e.g. migraine headaches, Parkinson's disease, multiple sclerosis)",
    "Neurodivergence (e.g. ADHD, dyslexia, dyspraxia, other learning disabilities)",
    "Partial or complete paralysis (any cause)",
    "Pulmonary or respiratory conditions (e.g. tuberculosis, asthma, emphysema)",
    "Short stature (dwarfism)",
    "Traumatic brain injury",
    "Wheelchair user for mobility",
]
# What the form shows, in order
DISABILITY_OPTIONS = [DISABILITY_NONE] + DISABILITY_CONDITIONS + [DISABILITY_OTHER]

MIN_BIRTH_YEAR = 1920
