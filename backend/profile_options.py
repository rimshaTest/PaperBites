"""
Fixed answer sets for the Profile Details form. Served to the client by GET /api/profile/options
(see api_server.py) rather than duplicated in the app, so the form and the server-side
validation in profile_validation.py can never drift apart. The one dynamic list - field of
study - comes from categories.current_categories() instead of being listed here.

Gender / sex / disability options follow the voluntary self-identification wording used on US
job applications (EEO-1 style gender, and the OFCCP Form CC-305 disability question), each with
a "prefer not to say" choice, since every field in this form is optional.
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

# Form CC-305's three answers to "do you have a disability?"
DISABILITY_STATUSES = [
    "Yes, I have a disability, or have had one in the past",
    "No, I do not have a disability and have not had one in the past",
    "I do not want to answer",
]
DISABILITY_YES = DISABILITY_STATUSES[0]

# The condition checklist from Form CC-305, shown only when the answer above is "Yes". Mental,
# physical and chronic conditions are one combined list, as on the form.
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
    "Another disability or condition not listed",
]

MIN_BIRTH_YEAR = 1920
