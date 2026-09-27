// Maps every language code langdetect can produce (backend/paper/latest.py's _detect_language)
// to a full display name - the raw ISO codes ("en", "es", "id") read as confusing abbreviations
// in the card badge, capitalized to "En"/"Es"/"Id" by the badge's textTransform.
const LANGUAGE_NAMES = {
  af: 'Afrikaans',
  ar: 'Arabic',
  bg: 'Bulgarian',
  bn: 'Bengali',
  ca: 'Catalan',
  cs: 'Czech',
  cy: 'Welsh',
  da: 'Danish',
  de: 'German',
  el: 'Greek',
  en: 'English',
  es: 'Spanish',
  et: 'Estonian',
  fa: 'Persian',
  fi: 'Finnish',
  fr: 'French',
  gu: 'Gujarati',
  he: 'Hebrew',
  hi: 'Hindi',
  hr: 'Croatian',
  hu: 'Hungarian',
  id: 'Indonesian',
  it: 'Italian',
  ja: 'Japanese',
  kn: 'Kannada',
  ko: 'Korean',
  lt: 'Lithuanian',
  lv: 'Latvian',
  mk: 'Macedonian',
  ml: 'Malayalam',
  mr: 'Marathi',
  ne: 'Nepali',
  nl: 'Dutch',
  no: 'Norwegian',
  pa: 'Punjabi',
  pl: 'Polish',
  pt: 'Portuguese',
  ro: 'Romanian',
  ru: 'Russian',
  sk: 'Slovak',
  sl: 'Slovenian',
  so: 'Somali',
  sq: 'Albanian',
  sv: 'Swedish',
  sw: 'Swahili',
  ta: 'Tamil',
  te: 'Telugu',
  th: 'Thai',
  tl: 'Tagalog',
  tr: 'Turkish',
  uk: 'Ukrainian',
  ur: 'Urdu',
  vi: 'Vietnamese',
  'zh-cn': 'Chinese',
  'zh-tw': 'Chinese',
};

/**
 * Full display name for a language code, falling back to the code itself (uppercased) for
 * anything unrecognized rather than showing nothing.
 * @param {string} code - ISO 639-1-ish code, as backend/paper/latest.py's langdetect produces
 * @returns {string}
 */
export const languageName = (code) => {
  if (!code) return '';
  return LANGUAGE_NAMES[code.toLowerCase()] || code.toUpperCase();
};
