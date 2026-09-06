/**
 * The catalogue of languages WeatherGPT offers.
 *
 * This is the only place a language is declared. The selector, its search, its
 * grouping, the footer count and the speech tags are all derived from this
 * array — adding a language is one row here, not a new component.
 *
 * Two flags keep the interface honest, because claiming more than the backend
 * can do would be worse than offering less:
 *
 *   `translation` — the backend can actually answer in this language. Today
 *                   that is the six languages `i18n.LANGUAGES` carries. The
 *                   rest are selectable and searchable, and are answered in
 *                   English until the backend corpus reaches them. The live
 *                   truth arrives with `/config`, so `withServerLanguages()`
 *                   reconciles these defaults against it rather than letting
 *                   the two drift.
 *
 *   `voice`       — speech recognition and spoken answers are wired end to
 *                   end. It tracks `translation` today: reading an English
 *                   sentence aloud with a Tamil voice would be a claim we
 *                   cannot keep. When the backend gains a language, both flags
 *                   flip together and the microphone and speaker follow.
 *
 * `speechTag` is the BCP-47 tag handed to the browser's recogniser. It is
 * filled in for languages the browser knows even when `voice` is false, so
 * enabling one later needs no second lookup table.
 */

/** Where a language sits in the panel. Order here is the order on screen. */
export const REGIONS = {
  popular: { id: 'popular', icon: '⭐' },
  north: { id: 'north' },
  south: { id: 'south' },
  east: { id: 'east' },
  community: { id: 'community' },
}

/**
 * Every language, declared once.
 *
 * `native` is the name as its own speakers write it; `short` is the two- or
 * three-character form the header falls back to at 320px. `aliases` carry the
 * other names a person might type — spellings, endonyms, and the community
 * names that differ from the official one (Lambadi is Lamani is Banjara).
 */
export const LANGUAGE_CATALOG = [
  // --- Answered end to end, today -----------------------------------------
  { id: 'en', english: 'English', native: 'English', short: 'EN', region: 'popular', translation: true, voice: true, speechTag: 'en-IN', aliases: ['angrezi', 'ingles'] },
  { id: 'hi', english: 'Hindi', native: 'हिन्दी', short: 'हिं', region: 'popular', translation: true, voice: true, speechTag: 'hi-IN', aliases: ['hindustani'] },
  { id: 'te', english: 'Telugu', native: 'తెలుగు', short: 'తె', region: 'popular', translation: true, voice: true, speechTag: 'te-IN', aliases: ['telegu', 'andhra'] },
  { id: 'bn', english: 'Bengali', native: 'বাংলা', short: 'বাং', region: 'popular', translation: true, voice: true, speechTag: 'bn-IN', aliases: ['bangla'] },
  { id: 'mr', english: 'Marathi', native: 'मराठी', short: 'मरा', region: 'popular', translation: true, voice: true, speechTag: 'mr-IN', aliases: ['marathi'] },
  { id: 'as', english: 'Assamese', native: 'অসমীয়া', short: 'অস', region: 'popular', translation: true, voice: true, speechTag: 'as-IN', aliases: ['asamiya', 'axomiya'] },

  // --- North, west and central India ---------------------------------------
  { id: 'ur', english: 'Urdu', native: 'اردو', short: 'UR', region: 'north', translation: false, voice: false, speechTag: 'ur-IN', aliases: ['urdu'] },
  { id: 'pa', english: 'Punjabi', native: 'ਪੰਜਾਬੀ', short: 'ਪੰ', region: 'north', translation: false, voice: false, speechTag: 'pa-Guru-IN', aliases: ['panjabi', 'gurmukhi'] },
  { id: 'gu', english: 'Gujarati', native: 'ગુજરાતી', short: 'ગુ', region: 'north', translation: false, voice: false, speechTag: 'gu-IN', aliases: ['gujrati'] },
  { id: 'sa', english: 'Sanskrit', native: 'संस्कृतम्', short: 'सं', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['sanskrutam', 'samskrutam'] },
  { id: 'ne', english: 'Nepali', native: 'नेपाली', short: 'ने', region: 'north', translation: false, voice: false, speechTag: 'ne-NP', aliases: ['gorkhali', 'khas kura'] },
  { id: 'kok', english: 'Konkani', native: 'कोंकणी', short: 'कों', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['konknni', 'goan'] },
  { id: 'ks', english: 'Kashmiri', native: 'كٲشُر', short: 'KS', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['koshur', 'kashur'] },
  { id: 'mai', english: 'Maithili', native: 'मैथिली', short: 'मै', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['maithil', 'tirhuta'] },
  { id: 'doi', english: 'Dogri', native: 'डोगरी', short: 'डो', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['dogra'] },
  { id: 'sd', english: 'Sindhi', native: 'سنڌي', short: 'SD', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['sindi', 'sindhu'] },
  { id: 'bho', english: 'Bhojpuri', native: 'भोजपुरी', short: 'भो', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['bhojpury', 'bihari'] },
  { id: 'awa', english: 'Awadhi', native: 'अवधी', short: 'अव', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['abadhi', 'kosali'] },
  { id: 'hne', english: 'Chhattisgarhi', native: 'छत्तीसगढ़ी', short: 'छत्', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['chattisgarhi', 'khaltahi'] },
  { id: 'gbm', english: 'Garhwali', native: 'गढ़वळि', short: 'गढ़', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['gadwali', 'pahari'] },
  { id: 'kfy', english: 'Kumaoni', native: 'कुमाऊँनी', short: 'कु', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['kumauni', 'kumaon'] },
  { id: 'bgc', english: 'Haryanvi', native: 'हरियाणवी', short: 'हरि', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['hariyanvi', 'bangru', 'jatu'] },
  { id: 'raj', english: 'Rajasthani', native: 'राजस्थानी', short: 'राज', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['rajasthani'] },
  { id: 'mwr', english: 'Marwari', native: 'मारवाड़ी', short: 'मार', region: 'north', translation: false, voice: false, speechTag: null, aliases: ['marwadi', 'merwari'] },

  // --- South India ----------------------------------------------------------
  { id: 'ta', english: 'Tamil', native: 'தமிழ்', short: 'த', region: 'south', translation: false, voice: false, speechTag: 'ta-IN', aliases: ['thamizh', 'tamizh'] },
  { id: 'kn', english: 'Kannada', native: 'ಕನ್ನಡ', short: 'ಕ', region: 'south', translation: false, voice: false, speechTag: 'kn-IN', aliases: ['canarese', 'kanada'] },
  { id: 'ml', english: 'Malayalam', native: 'മലയാളം', short: 'മ', region: 'south', translation: false, voice: false, speechTag: 'ml-IN', aliases: ['malayalm', 'kerala'] },
  { id: 'tcy', english: 'Tulu', native: 'ತುಳು', short: 'ತು', region: 'south', translation: false, voice: false, speechTag: null, aliases: ['tulu bhasa', 'thulu'] },

  // --- East and northeast India --------------------------------------------
  { id: 'or', english: 'Odia', native: 'ଓଡ଼ିଆ', short: 'ଓ', region: 'east', translation: false, voice: false, speechTag: null, aliases: ['oriya', 'orissa'] },
  { id: 'mni', english: 'Manipuri', native: 'মৈতৈলোন্', short: 'মৈ', region: 'east', translation: false, voice: false, speechTag: null, aliases: ['meitei', 'meiteilon', 'manipuri'] },
  { id: 'brx', english: 'Bodo', native: 'बर’', short: 'बर', region: 'east', translation: false, voice: false, speechTag: null, aliases: ['boro', 'bodo'] },
  { id: 'sat', english: 'Santhali', native: 'संताली', short: 'सं', region: 'east', translation: false, voice: false, speechTag: null, aliases: ['santali', 'santal', 'hor'] },

  // --- Regional and community languages ------------------------------------
  { id: 'lmn', english: 'Lambadi', native: 'लंबाडी', short: 'लं', region: 'community', translation: false, voice: false, speechTag: null, aliases: ['lamani', 'lambani', 'banjara', 'gor boli', 'goar boli'] },
  { id: 'gon', english: 'Gondi', native: 'गोंडी', short: 'गों', region: 'community', translation: false, voice: false, speechTag: null, aliases: ['gondi', 'koitur'] },
  { id: 'bhb', english: 'Bhili', native: 'भीली', short: 'भी', region: 'community', translation: false, voice: false, speechTag: null, aliases: ['bhil', 'bhilodi'] },
]

/** The order groups appear in the panel. */
export const GROUP_ORDER = ['popular', 'north', 'south', 'east', 'community']

export const LANGUAGE_COUNT = LANGUAGE_CATALOG.length

/** Rounded down to the nearest five, so the footer reads "35+" not "36". */
export const LANGUAGE_COUNT_LABEL = `${Math.floor(LANGUAGE_COUNT / 5) * 5}+`

const BY_ID = new Map(LANGUAGE_CATALOG.map((entry) => [entry.id, entry]))

export function findLanguage(id) {
  return BY_ID.get(id) ?? BY_ID.get('en')
}

/** BCP-47 tag for the browser's recogniser; English India when unknown. */
export function speechTagFor(id) {
  return findLanguage(id).speechTag ?? 'en-IN'
}

/**
 * Reconcile the built-in flags against what the server reports it can do.
 *
 * `/config` lists the languages the backend has a corpus for. Trusting it over
 * the constants above means the selector can never promise a translation the
 * running backend has since dropped, or withhold one it has gained.
 */
export function withServerLanguages(catalog, serverLanguages) {
  if (!Array.isArray(serverLanguages) || serverLanguages.length === 0) return catalog
  const supported = new Set(serverLanguages.map((l) => (typeof l === 'string' ? l : l?.code)).filter(Boolean))
  return catalog.map((entry) => {
    const translation = supported.has(entry.id)
    if (translation === entry.translation) return entry
    // Voice rides with translation: we only speak what we can write.
    return { ...entry, translation, voice: translation && entry.voice !== undefined ? translation : entry.voice }
  })
}

/**
 * Case- and script-insensitive search over English name, native name and
 * aliases. Returns entries in catalogue order so the grouping stays stable
 * while the user types.
 */
export function searchLanguages(catalog, query) {
  const needle = query.trim().toLowerCase()
  if (!needle) return catalog
  return catalog.filter((entry) => {
    if (entry.english.toLowerCase().includes(needle)) return true
    if (entry.native.toLowerCase().includes(needle)) return true
    if (entry.id.toLowerCase() === needle) return true
    return entry.aliases.some((alias) => alias.toLowerCase().includes(needle))
  })
}

/**
 * Bucket entries into their groups for rendering.
 *
 * Each language belongs to exactly one group — `region` decides, and `popular`
 * is a region like any other — so the list never offers the same language
 * twice. Empty groups are dropped, which is what makes a search result read as
 * a short list rather than five headings with one row between them.
 */
export function groupLanguages(entries) {
  return GROUP_ORDER.map((id) => ({ id, items: entries.filter((entry) => entry.region === id) })).filter(
    (group) => group.items.length > 0,
  )
}

/**
 * Which of the matches the user most likely meant.
 *
 * The list stays in its regional groups while searching, because that is what
 * makes it navigable — but "kan" should offer Kannada, not Konkani, which
 * happens to contain those letters in the middle and happens to sort earlier.
 * So the highlight goes to the best match rather than the first one, and
 * pressing Enter picks what the user was typing towards.
 */
export function bestMatchIndex(entries, query) {
  const needle = query.trim().toLowerCase()
  if (!needle) return 0

  const score = (entry) => {
    if (entry.id.toLowerCase() === needle) return 0
    if (entry.english.toLowerCase().startsWith(needle)) return 1
    if (entry.native.toLowerCase().startsWith(needle)) return 1
    if (entry.aliases.some((alias) => alias.toLowerCase().startsWith(needle))) return 2
    return 3
  }

  let best = 0
  let bestScore = 4
  entries.forEach((entry, index) => {
    const value = score(entry)
    if (value < bestScore) {
      bestScore = value
      best = index
    }
  })
  return best
}
