/**
 * Client-side checks for the Profile Details form, for instant feedback while typing. The
 * server re-validates everything (backend/profile_validation.py) and is authoritative - it also
 * does the profanity screening, which isn't duplicated here. Keep these rules in step with it.
 *
 * Every validator returns an error message string, or null when the value is valid.
 */

export const INTERESTS_MAX_ITEMS = 10;
export const INTERESTS_MAX_TOTAL_LENGTH = 200;
export const ITEM_MIN_LENGTH = 2;
export const ITEM_MAX_LENGTH = 40;
export const OTHER_FIELD_MAX_LENGTH = 60;

const VOWELS = 'aeiouy';
const KEYBOARD_MASHES = ['qwer', 'asdf', 'zxcv', 'hjkl', 'uiop', 'wasd', 'qaz', 'wsx'];
const SQL_PATTERN =
  /\b(select|insert|update|delete|drop|alter|truncate|exec|execute|union)\b.*\b(from|into|table|set|where|select|all|database)\b/i;

const isLetter = (c) => c.toLowerCase() !== c.toUpperCase();
const isAlnum = (c) => isLetter(c) || /[0-9]/.test(c);

export function looksLikeGibberish(word) {
  const letters = [...word].filter(isLetter).join('');
  if (!letters) return false;
  if (word.length > 30) return true;
  const isAcronym =
    letters.length <= 6 && (letters === letters.toUpperCase() || letters.slice(1) === letters.slice(1).toUpperCase());
  const lower = letters.toLowerCase();
  if (!isAcronym && lower.length >= 3 && ![...lower].some((c) => VOWELS.includes(c))) return true;
  if (/(.)\1{3,}/.test(lower)) return true;
  if (/(.{2,3})\1{2,}/.test(lower)) return true;
  if (!isAcronym && /[^aeiouy]{6,}/.test(lower)) return true;
  return KEYBOARD_MASHES.some((m) => lower.includes(m));
}

function textQualityError(text, label) {
  if (SQL_PATTERN.test(text)) return `${label} contains text that isn't allowed.`;
  const bad = text.split(/[\s,]+/).find((w) => w && looksLikeGibberish(w));
  return bad ? `"${bad}" doesn't look like a real word.` : null;
}

export function validateInterests(value) {
  const text = (value || '').trim();
  if (!text) return null;
  if (text.length > INTERESTS_MAX_TOTAL_LENGTH) return `Keep interests under ${INTERESTS_MAX_TOTAL_LENGTH} characters.`;
  if (![...text].every((c) => isAlnum(c) || c === ' ' || c === ',')) {
    return 'Use letters, numbers, spaces and commas only.';
  }
  const items = [];
  for (const raw of text.split(',')) {
    const item = raw.replace(/\s+/g, ' ').trim();
    if (!item || items.includes(item.toLowerCase())) continue;
    if (item.length < ITEM_MIN_LENGTH || item.length > ITEM_MAX_LENGTH) {
      return `Each interest should be ${ITEM_MIN_LENGTH}-${ITEM_MAX_LENGTH} characters.`;
    }
    items.push(item.toLowerCase());
  }
  if (items.length > INTERESTS_MAX_ITEMS) return `List at most ${INTERESTS_MAX_ITEMS} interests.`;
  return textQualityError(items.join(', '), 'Interests');
}

export function validateOtherField(value, emptyMessage = 'Tell us your field of study.') {
  const text = (value || '').replace(/\s+/g, ' ').trim();
  if (!text) return emptyMessage;
  if (text.length < ITEM_MIN_LENGTH || text.length > OTHER_FIELD_MAX_LENGTH) {
    return `Use ${ITEM_MIN_LENGTH}-${OTHER_FIELD_MAX_LENGTH} characters.`;
  }
  if (![...text].every((c) => isLetter(c) || c === ' ')) return 'Use letters and spaces only.';
  return textQualityError(text, 'Field of study');
}

/** The free-text description for "Other" in the disability checklist: letters, spaces, hyphens and apostrophes. */
export function validateDisabilityOther(value) {
  const text = (value || '').replace(/\s+/g, ' ').trim();
  if (!text) return 'Describe your disability or condition.';
  if (text.length < ITEM_MIN_LENGTH || text.length > OTHER_FIELD_MAX_LENGTH) {
    return `Use ${ITEM_MIN_LENGTH}-${OTHER_FIELD_MAX_LENGTH} characters.`;
  }
  if (![...text].every((c) => isLetter(c) || ' -\''.includes(c))) {
    return 'Use letters, spaces, hyphens and apostrophes only.';
  }
  return textQualityError(text, 'This answer');
}

/** Letters (any script), spaces, and the punctuation real place names use. */
export function isAlphabeticPlace(text) {
  return !!text && [...text].every((c) => isLetter(c) || ' .,\'’-'.includes(c));
}

export function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate(); // month is 1-12; day 0 of next month = last day
}

/** parts: {year, month, day} as numbers/strings, any may be empty. All empty is valid (optional). */
export function validateBirthDate({ year, month, day }, minYear) {
  const filled = [year, month, day].filter((v) => v !== '' && v != null);
  if (filled.length === 0) return null;
  if (filled.length < 3) return 'Choose a year, month and day.';
  const y = Number(year);
  const m = Number(month);
  const d = Number(day);
  if (y < minYear) return `Birth year must be ${minYear} or later.`;
  if (d > daysInMonth(y, m)) return "That date doesn't exist.";
  if (new Date(y, m - 1, d) > new Date()) return "Birth date can't be in the future.";
  return null;
}

export function toIsoDate({ year, month, day }) {
  if (!year || !month || !day) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${year}-${pad(month)}-${pad(day)}`;
}

export function fromIsoDate(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
  return match
    ? { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) }
    : { year: '', month: '', day: '' };
}
