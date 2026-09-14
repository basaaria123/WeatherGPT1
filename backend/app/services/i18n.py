# -*- coding: utf-8 -*-
"""Localised response templates for the six supported languages.

Why templates and not only machine translation: when the LLM or a translation
service is unavailable, WeatherGPT must still answer in the user's language
rather than dropping to English. Because every sentence here is a fixed
template with numeric slots filled from real Open-Meteo values, the offline
path is both multilingual *and* incapable of fabricating a number.

The LLM path still generates free prose and translates it; this module is the
floor under that, not a replacement for it.
"""

from __future__ import annotations

from typing import Any

LANGUAGES: tuple[str, ...] = ("en", "hi", "te", "bn", "mr", "as")
DEFAULT_LANG = "en"

# --- WMO code -> condition bucket ------------------------------------------
_BUCKETS: dict[int, str] = {
    0: "clear", 1: "mainly_clear", 2: "partly_cloudy", 3: "overcast",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle", 56: "drizzle", 57: "drizzle",
    61: "light_rain", 63: "moderate_rain", 65: "heavy_rain", 66: "light_rain", 67: "heavy_rain",
    71: "snow", 73: "snow", 75: "snow", 77: "snow", 85: "snow", 86: "snow",
    80: "showers", 81: "showers", 82: "violent_showers",
    95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm",
}

CONDITIONS: dict[str, dict[str, str]] = {
    "en": {
        "clear": "clear sky", "mainly_clear": "mainly clear skies", "partly_cloudy": "partly cloudy skies",
        "overcast": "overcast skies", "fog": "fog", "drizzle": "light drizzle", "light_rain": "light rain",
        "moderate_rain": "moderate rain", "heavy_rain": "heavy rain", "showers": "rain showers",
        "violent_showers": "very heavy rain showers", "thunderstorm": "a thunderstorm",
        "snow": "snowfall", "unknown": "mixed conditions",
    },
    "hi": {
        "clear": "साफ़ आसमान", "mainly_clear": "अधिकतर साफ़ आसमान", "partly_cloudy": "आंशिक बादल",
        "overcast": "घने बादल", "fog": "कोहरा", "drizzle": "हल्की बूंदाबांदी", "light_rain": "हल्की बारिश",
        "moderate_rain": "मध्यम बारिश", "heavy_rain": "भारी बारिश", "showers": "बौछारें",
        "violent_showers": "बहुत तेज़ बौछारें", "thunderstorm": "गरज के साथ तूफ़ान",
        "snow": "बर्फ़बारी", "unknown": "मिश्रित मौसम",
    },
    "te": {
        "clear": "నిర్మలమైన ఆకాశం", "mainly_clear": "ఎక్కువగా నిర్మలమైన ఆకాశం", "partly_cloudy": "పాక్షికంగా మేఘావృతం",
        "overcast": "పూర్తిగా మేఘావృతం", "fog": "పొగమంచు", "drizzle": "తుంపర వర్షం", "light_rain": "తేలికపాటి వర్షం",
        "moderate_rain": "మధ్యస్థ వర్షం", "heavy_rain": "భారీ వర్షం", "showers": "వర్షపు జల్లులు",
        "violent_showers": "అత్యంత భారీ జల్లులు", "thunderstorm": "ఉరుములతో కూడిన తుఫాను",
        "snow": "మంచు కురుస్తోంది", "unknown": "మిశ్రమ వాతావరణం",
    },
    "bn": {
        "clear": "পরিষ্কার আকাশ", "mainly_clear": "বেশিরভাগ পরিষ্কার আকাশ", "partly_cloudy": "আংশিক মেঘলা",
        "overcast": "সম্পূর্ণ মেঘলা", "fog": "কুয়াশা", "drizzle": "গুঁড়ি গুঁড়ি বৃষ্টি", "light_rain": "হালকা বৃষ্টি",
        "moderate_rain": "মাঝারি বৃষ্টি", "heavy_rain": "ভারী বৃষ্টি", "showers": "বৃষ্টির ছাঁট",
        "violent_showers": "প্রবল বৃষ্টির ছাঁট", "thunderstorm": "বজ্রঝড়",
        "snow": "তুষারপাত", "unknown": "মিশ্র আবহাওয়া",
    },
    "mr": {
        "clear": "स्वच्छ आकाश", "mainly_clear": "बहुतांशी स्वच्छ आकाश", "partly_cloudy": "अंशतः ढगाळ",
        "overcast": "पूर्ण ढगाळ", "fog": "धुके", "drizzle": "रिमझिम पाऊस", "light_rain": "हलका पाऊस",
        "moderate_rain": "मध्यम पाऊस", "heavy_rain": "जोरदार पाऊस", "showers": "सरी",
        "violent_showers": "अत्यंत जोरदार सरी", "thunderstorm": "गडगडाटी वादळ",
        "snow": "बर्फवृष्टी", "unknown": "मिश्र हवामान",
    },
    "as": {
        "clear": "পৰিষ্কাৰ আকাশ", "mainly_clear": "বেছিভাগ পৰিষ্কাৰ আকাশ", "partly_cloudy": "আংশিক ডাৱৰীয়া",
        "overcast": "সম্পূৰ্ণ ডাৱৰীয়া", "fog": "কুঁৱলী", "drizzle": "গুড়ি গুড়ি বৰষুণ", "light_rain": "পাতল বৰষুণ",
        "moderate_rain": "মজলীয়া বৰষুণ", "heavy_rain": "প্ৰবল বৰষুণ", "showers": "বৰষুণৰ ছাঁট",
        "violent_showers": "অতি প্ৰবল বৰষুণৰ ছাঁট", "thunderstorm": "বজ্ৰ-ধুমুহা",
        "snow": "বৰফপাত", "unknown": "মিশ্ৰিত বতৰ",
    },
}

HAZARD_NAMES: dict[str, dict[str, str]] = {
    "en": {"Heavy Rainfall": "Heavy Rainfall", "Flood Risk": "Flood Risk", "Strong Wind": "Strong Wind",
           "Extreme Heat": "Extreme Heat", "Lightning/Storm": "Lightning and Storm", "None": "No active hazard"},
    "hi": {"Heavy Rainfall": "भारी बारिश", "Flood Risk": "बाढ़ का ख़तरा", "Strong Wind": "तेज़ हवा",
           "Extreme Heat": "भीषण गर्मी", "Lightning/Storm": "बिजली और तूफ़ान", "None": "कोई ख़तरा नहीं"},
    "te": {"Heavy Rainfall": "భారీ వర్షం", "Flood Risk": "వరద ముప్పు", "Strong Wind": "బలమైన గాలి",
           "Extreme Heat": "తీవ్రమైన వేడి", "Lightning/Storm": "పిడుగులు మరియు తుఫాను", "None": "ముప్పు లేదు"},
    "bn": {"Heavy Rainfall": "ভারী বৃষ্টি", "Flood Risk": "বন্যার ঝুঁকি", "Strong Wind": "জোরালো বাতাস",
           "Extreme Heat": "তীব্র গরম", "Lightning/Storm": "বজ্রপাত ও ঝড়", "None": "কোনো ঝুঁকি নেই"},
    "mr": {"Heavy Rainfall": "जोरदार पाऊस", "Flood Risk": "पुराचा धोका", "Strong Wind": "जोरदार वारा",
           "Extreme Heat": "तीव्र उष्णता", "Lightning/Storm": "वीज आणि वादळ", "None": "धोका नाही"},
    "as": {"Heavy Rainfall": "প্ৰবল বৰষুণ", "Flood Risk": "বানপানীৰ আশংকা", "Strong Wind": "প্ৰবল বতাহ",
           "Extreme Heat": "প্ৰচণ্ড গৰম", "Lightning/Storm": "বজ্ৰপাত আৰু ধুমুহা", "None": "কোনো আশংকা নাই"},
}

RISK_LEVELS: dict[str, dict[str, str]] = {
    "en": {"Low": "Low", "Moderate": "Moderate", "High": "High", "Severe": "Severe"},
    "hi": {"Low": "कम", "Moderate": "मध्यम", "High": "अधिक", "Severe": "गंभीर"},
    "te": {"Low": "తక్కువ", "Moderate": "మధ్యస్థం", "High": "అధికం", "Severe": "తీవ్రం"},
    "bn": {"Low": "কম", "Moderate": "মাঝারি", "High": "বেশি", "Severe": "তীব্র"},
    "mr": {"Low": "कमी", "Moderate": "मध्यम", "High": "जास्त", "Severe": "गंभीर"},
    "as": {"Low": "কম", "Moderate": "মজলীয়া", "High": "বেছি", "Severe": "গুৰুতৰ"},
}

SENTENCES: dict[str, dict[str, str]] = {
    "en": {
        "impact_everyday_clear": "An ordinary day — nothing in the readings needs working around.",
        "impact_everyday_rain": "Rain is likely to shape the day.",
        "impact_everyday_risk": "Conditions are risky enough to change ordinary plans.",
        "now": "Right now in {loc} it is {temp}°C with {cond}.",
        "feels": "It feels like {feels}°C.",
        "humid": "The air is very humid at {hum}%.",
        "rain_high": "There is a high chance of rain — about {prob}% in the coming hour.",
        "rain_low": "Rain is unlikely for now.",
        "rain_24": "About {mm} mm of rain is expected over the next 24 hours.",
        "wind_calm": "Wind is light at about {wind} km/h.",
        "wind_strong": "Strong wind of about {wind} km/h may make outdoor activity difficult.",
        "heat_note": "It will feel very hot, around {feels}°C.",
        "calm_tail": "Conditions look normal, and there is no weather warning for your area right now.",
        "emg_headline": "Warning for {loc}: {hazard}.",
        "emg_what": "What is happening",
        "emg_why": "Why it matters",
        "emg_do": "What to do",
        "emg_why_text": "Risk level is {level} at {score} out of 100, so conditions can turn dangerous quickly.",
        "no_data": "I could not get weather data for that location just now. Please try again in a moment.",
        "no_location": "I could not work out which place you mean. Could you tell me the city or district?",
        "out_of_scope": "I can only help with weather, forecasts, alerts and climate trends. Ask me about the weather in any place in India and I will help.",
        "forecast_lead": "Forecast for {loc}: {day} — {cond}, between {tmin}°C and {tmax}°C.",
        "alert_none": "There are no active weather alerts for {loc} right now.",
        "alert_some": "There {verb} {count} active weather {noun} for {loc}.",
        "disclaimer": "This is general guidance, not professional agricultural, medical or disaster-management advice.",
        "advisory_watch_official": "Follow official alerts for this area and act on any warning that is issued.",
        "vb_lead_calm": "{hazard} in {loc} right now. Here is what to do.",
        "nwp_answer": "WeatherGPT is designed to support numerical weather prediction datasets such as GFS and WRF. These integrations are planned for the next stage of the platform — the forecast you see now comes from real-time meteorological data, not from a numerical model run here.",
        "clim_param_temperature": "temperature",
        "clim_param_rainfall": "rainfall",
        "clim_param_humidity": "humidity",
        "clim_says_rising": "In {loc}, average {param} rose by {change} between {start} and {end}, against a period average of {average}.",
        "clim_says_falling": "In {loc}, average {param} fell by {change} between {start} and {end}, against a period average of {average}.",
        "clim_says_steady": "In {loc}, average {param} stayed broadly level between {start} and {end}, around {average}. The change across that window is smaller than the year-to-year variation.",
        "clim_says_unknown": "There is not enough measured history for {loc} to describe a direction for {param}.",
        "clim_no_archive": "Historical climate analysis for {loc} is not available right now — the historical archive could not be reached. This capability is being prepared for the next data integration phase.",
        "clim_too_few": "The historical archive does not hold enough complete years for {loc} to describe a {param} trend.",
        "clim_no_series": "The daily historical archive carries temperature and rainfall but not {param}, so no long-term {param} series can be shown for {loc} yet.",
        "vb_lead_clear": "Conditions in {loc} are normal right now.",
        "vb_lead_high": "{hazard} in {loc}. Risk is {level}. Act on this now.",
        "vb_lead_severe": "{hazard} in {loc}. Do this now.",
        "vb_wind_now": 'Wind is about {wind} kilometres per hour.',
        "vb_rain_chance": 'The chance of rain is about {prob} percent.',
        "vb_window": "Expected around {time}.",
    },
    "hi": {
        "impact_everyday_clear": "आम दिन — आँकड़ों में ऐसा कुछ नहीं जिससे बचना पड़े।",
        "impact_everyday_rain": "दिन पर बारिश का असर रहेगा।",
        "impact_everyday_risk": "हालात ऐसे हैं कि रोज़ के काम बदलने पड़ सकते हैं।",
        "now": "{loc} में अभी {temp}°C है और {cond} है।",
        "feels": "महसूस {feels}°C जैसा हो रहा है।",
        "humid": "हवा में नमी काफ़ी ज़्यादा है, लगभग {hum}%।",
        "rain_high": "बारिश की संभावना ज़्यादा है — अगले एक घंटे में लगभग {prob}%।",
        "rain_low": "अभी बारिश की संभावना कम है।",
        "rain_24": "अगले 24 घंटों में लगभग {mm} मिमी बारिश का अनुमान है।",
        "wind_calm": "हवा हल्की है, लगभग {wind} किमी/घंटा।",
        "wind_strong": "लगभग {wind} किमी/घंटा की तेज़ हवा से बाहर का काम मुश्किल हो सकता है।",
        "heat_note": "बहुत गर्मी महसूस होगी, लगभग {feels}°C।",
        "calm_tail": "स्थिति सामान्य है, अभी आपके क्षेत्र के लिए कोई चेतावनी नहीं है।",
        "emg_headline": "{loc} के लिए चेतावनी: {hazard}।",
        "emg_what": "क्या हो रहा है",
        "emg_why": "यह क्यों ज़रूरी है",
        "emg_do": "क्या करें",
        "emg_why_text": "ख़तरे का स्तर {level} है, 100 में से {score}, इसलिए हालात जल्दी बिगड़ सकते हैं।",
        "no_data": "अभी उस जगह का मौसम डेटा नहीं मिल पाया। कृपया थोड़ी देर बाद फिर कोशिश करें।",
        "no_location": "मैं समझ नहीं पाया कि आप किस जगह की बात कर रहे हैं। शहर या ज़िले का नाम बताइए।",
        "out_of_scope": "मैं केवल मौसम, पूर्वानुमान, चेतावनी और जलवायु रुझान में मदद कर सकता हूँ। भारत की किसी भी जगह का मौसम पूछिए।",
        "forecast_lead": "{loc} का पूर्वानुमान: {day} — {cond}, {tmin}°C से {tmax}°C के बीच।",
        "alert_none": "{loc} के लिए अभी कोई सक्रिय मौसम चेतावनी नहीं है।",
        "alert_some": "{loc} के लिए {count} सक्रिय मौसम चेतावनी है।",
        "disclaimer": "यह सामान्य जानकारी है, पेशेवर कृषि, चिकित्सा या आपदा प्रबंधन सलाह नहीं।",
        "advisory_watch_official": "इस क्षेत्र की आधिकारिक चेतावनियों पर नज़र रखें और कोई चेतावनी जारी हो तो उस पर अमल करें।",
        "vb_lead_calm": "{loc} में अभी {hazard}। क्या करना है, सुनिए।",
        "nwp_answer": "WeatherGPT को GFS और WRF जैसे संख्यात्मक मौसम पूर्वानुमान डेटासेट के लिए बनाया गया है। ये एकीकरण अगले चरण के लिए नियोजित हैं — अभी दिखने वाला पूर्वानुमान रीयल-टाइम मौसम डेटा से आता है, यहाँ चलाए गए किसी संख्यात्मक मॉडल से नहीं।",
        "clim_param_temperature": "तापमान",
        "clim_param_rainfall": "वर्षा",
        "clim_param_humidity": "नमी",
        "clim_says_rising": "{loc} में {start} से {end} के बीच औसत {param} {change} बढ़ा, अवधि औसत {average} की तुलना में।",
        "clim_says_falling": "{loc} में {start} से {end} के बीच औसत {param} {change} घटा, अवधि औसत {average} की तुलना में।",
        "clim_says_steady": "{loc} में {start} से {end} के बीच औसत {param} लगभग {average} पर स्थिर रहा। इस अवधि का बदलाव वार्षिक उतार-चढ़ाव से कम है।",
        "clim_says_unknown": "{loc} के लिए {param} की दिशा बताने लायक पर्याप्त मापा इतिहास नहीं है।",
        "clim_no_archive": "{loc} के लिए ऐतिहासिक जलवायु विश्लेषण अभी उपलब्ध नहीं है — ऐतिहासिक संग्रह तक पहुँच नहीं हो सकी। यह क्षमता अगले डेटा एकीकरण चरण के लिए तैयार की जा रही है।",
        "clim_too_few": "{loc} के लिए {param} का रुझान बताने लायक पूरे वर्ष ऐतिहासिक संग्रह में नहीं हैं।",
        "clim_no_series": "दैनिक ऐतिहासिक संग्रह में तापमान और वर्षा है, {param} नहीं — इसलिए {loc} के लिए {param} की दीर्घकालिक श्रृंखला अभी नहीं दिखाई जा सकती।",
        "vb_lead_clear": "{loc} में स्थिति अभी सामान्य है।",
        "vb_lead_high": "{loc} में {hazard}। ख़तरा {level} है। अभी क़दम उठाइए।",
        "vb_lead_severe": "{loc} में {hazard}। यह अभी कीजिए।",
        "vb_wind_now": 'हवा लगभग {wind} किलोमीटर प्रति घंटा है।',
        "vb_rain_chance": 'बारिश की संभावना लगभग {prob} प्रतिशत है।',
        "vb_window": "लगभग {time} बजे का अनुमान है।",
    },
    "te": {
        "impact_everyday_clear": "సాధారణ రోజు — కొలతల్లో తప్పించుకోవలసినది ఏమీ లేదు.",
        "impact_everyday_rain": "రోజును వర్షం ప్రభావితం చేస్తుంది.",
        "impact_everyday_risk": "సాధారణ పనులు మార్చుకోవలసిన స్థాయిలో పరిస్థితులు ఉన్నాయి.",
        "now": "{loc}లో ప్రస్తుతం {temp}°C ఉంది, {cond}.",
        "feels": "{feels}°C లా అనిపిస్తుంది.",
        "humid": "గాలిలో తేమ చాలా ఎక్కువగా, సుమారు {hum}% ఉంది.",
        "rain_high": "వర్షం పడే అవకాశం ఎక్కువగా ఉంది — వచ్చే గంటలో సుమారు {prob}%.",
        "rain_low": "ప్రస్తుతానికి వర్షం పడే అవకాశం తక్కువ.",
        "rain_24": "వచ్చే 24 గంటల్లో సుమారు {mm} మి.మీ. వర్షం పడే అవకాశం ఉంది.",
        "wind_calm": "గాలి తేలికగా ఉంది, సుమారు {wind} కి.మీ./గంట.",
        "wind_strong": "సుమారు {wind} కి.మీ./గంట వేగంతో బలమైన గాలి వీస్తోంది, బయట పనిచేయడం కష్టం కావచ్చు.",
        "heat_note": "చాలా వేడిగా అనిపిస్తుంది, సుమారు {feels}°C.",
        "calm_tail": "పరిస్థితి సాధారణంగా ఉంది, ప్రస్తుతం మీ ప్రాంతానికి ఎలాంటి హెచ్చరిక లేదు.",
        "emg_headline": "{loc}కు హెచ్చరిక: {hazard}.",
        "emg_what": "ఏమి జరుగుతోంది",
        "emg_why": "ఇది ఎందుకు ముఖ్యం",
        "emg_do": "ఏం చేయాలి",
        "emg_why_text": "ముప్పు స్థాయి {level}, 100కి {score}, కాబట్టి పరిస్థితి త్వరగా ప్రమాదకరంగా మారవచ్చు.",
        "no_data": "ఆ ప్రాంతానికి వాతావరణ సమాచారం ప్రస్తుతం అందలేదు. కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి.",
        "no_location": "మీరు ఏ ప్రాంతం గురించి అడుగుతున్నారో అర్థం కాలేదు. ఊరు లేదా జిల్లా పేరు చెప్పగలరా?",
        "out_of_scope": "నేను వాతావరణం, సూచనలు, హెచ్చరికలు, వాతావరణ ధోరణుల గురించి మాత్రమే సహాయం చేయగలను. భారతదేశంలోని ఏ ప్రాంతం వాతావరణం గురించైనా అడగండి.",
        "forecast_lead": "{loc} సూచన: {day} — {cond}, {tmin}°C నుండి {tmax}°C మధ్య.",
        "alert_none": "{loc}కు ప్రస్తుతం ఎలాంటి క్రియాశీల వాతావరణ హెచ్చరికలు లేవు.",
        "alert_some": "{loc}కు {count} క్రియాశీల వాతావరణ హెచ్చరికలు ఉన్నాయి.",
        "disclaimer": "ఇది సాధారణ సమాచారం మాత్రమే, వృత్తిపరమైన వ్యవసాయ, వైద్య లేదా విపత్తు నిర్వహణ సలహా కాదు.",
        "advisory_watch_official": "ఈ ప్రాంతానికి సంబంధించిన అధికారిక హెచ్చరికలను గమనిస్తూ ఉండండి, ఏదైనా హెచ్చరిక వస్తే దానిని పాటించండి.",
        "vb_lead_calm": "{loc}లో ప్రస్తుతం {hazard}. ఏం చేయాలో వినండి.",
        "nwp_answer": "WeatherGPT GFS, WRF వంటి సంఖ్యాత్మక వాతావరణ సూచన డేటాసెట్లకు మద్దతు ఇచ్చేలా రూపొందించబడింది. ఈ అనుసంధానాలు తదుపరి దశకు ప్రణాళిక చేయబడ్డాయి — ఇప్పుడు కనిపిస్తున్న సూచన నిజ-సమయ వాతావరణ డేటా నుండి వస్తుంది, ఇక్కడ నడిపిన సంఖ్యాత్మక మోడల్ నుండి కాదు.",
        "clim_param_temperature": "temperature",
        "clim_param_rainfall": "rainfall",
        "clim_param_humidity": "humidity",
        "clim_says_rising": "{loc}లో {start} నుండి {end} మధ్య సగటు {param} {change} పెరిగింది, కాల సగటు {average}తో పోలిస్తే.",
        "clim_says_falling": "{loc}లో {start} నుండి {end} మధ్య సగటు {param} {change} తగ్గింది, కాల సగటు {average}తో పోలిస్తే.",
        "clim_says_steady": "{loc}లో {start} నుండి {end} మధ్య సగటు {param} సుమారు {average} వద్ద స్థిరంగా ఉంది. ఈ కాలంలోని మార్పు సంవత్సరాల మధ్య హెచ్చుతగ్గుల కంటే తక్కువ.",
        "clim_says_unknown": "{loc} కోసం {param} దిశను చెప్పడానికి తగినంత కొలిచిన చరిత్ర లేదు.",
        "clim_no_archive": "{loc} కోసం చారిత్రక వాతావరణ విశ్లేషణ ప్రస్తుతం అందుబాటులో లేదు — చారిత్రక సంగ్రహాన్ని చేరుకోలేకపోయాం. ఈ సామర్థ్యం తదుపరి డేటా అనుసంధాన దశ కోసం సిద్ధం చేయబడుతోంది.",
        "clim_too_few": "{loc} కోసం {param} ధోరణిని చెప్పడానికి సరిపడా పూర్తి సంవత్సరాలు చారిత్రక సంగ్రహంలో లేవు.",
        "clim_no_series": "రోజువారీ చారిత్రక సంగ్రహంలో ఉష్ణోగ్రత, వర్షపాతం ఉన్నాయి కానీ {param} లేదు, కాబట్టి {loc} కోసం దీర్ఘకాలిక {param} శ్రేణిని ఇంకా చూపలేము.",
        "vb_lead_clear": "{loc}లో పరిస్థితి ప్రస్తుతం సాధారణంగా ఉంది.",
        "vb_lead_high": "{loc}లో {hazard}. ముప్పు {level}. ఇప్పుడే చర్య తీసుకోండి.",
        "vb_lead_severe": "{loc}లో {hazard}. ఇది ఇప్పుడే చేయండి.",
        "vb_wind_now": 'గాలి గంటకు సుమారు {wind} కిలోమీటర్ల వేగంతో ఉంది.',
        "vb_rain_chance": 'వర్షం పడే అవకాశం సుమారు {prob} శాతం.',
        "vb_window": "సుమారు {time} గంటలకు అంచనా.",
    },
    "bn": {
        "impact_everyday_clear": "সাধারণ দিন — মাপে এমন কিছু নেই যা এড়াতে হয়।",
        "impact_everyday_rain": "দিনটা বৃষ্টিই ঠিক করবে।",
        "impact_everyday_risk": "সাধারণ পরিকল্পনা বদলানোর মতো অবস্থা।",
        "now": "{loc}-এ এখন {temp}°C, {cond}।",
        "feels": "অনুভূত হচ্ছে {feels}°C-এর মতো।",
        "humid": "বাতাসে আর্দ্রতা অনেক বেশি, প্রায় {hum}%।",
        "rain_high": "বৃষ্টির সম্ভাবনা বেশি — পরের এক ঘণ্টায় প্রায় {prob}%।",
        "rain_low": "এখন বৃষ্টির সম্ভাবনা কম।",
        "rain_24": "আগামী 24 ঘণ্টায় প্রায় {mm} মিমি বৃষ্টি হতে পারে।",
        "wind_calm": "বাতাস হালকা, প্রায় {wind} কিমি/ঘণ্টা।",
        "wind_strong": "প্রায় {wind} কিমি/ঘণ্টা বেগে জোরালো বাতাস — বাইরের কাজ কঠিন হতে পারে।",
        "heat_note": "খুব গরম লাগবে, প্রায় {feels}°C।",
        "calm_tail": "পরিস্থিতি স্বাভাবিক, এখন আপনার এলাকার জন্য কোনো সতর্কতা নেই।",
        "emg_headline": "{loc}-এর জন্য সতর্কতা: {hazard}।",
        "emg_what": "কী হচ্ছে",
        "emg_why": "কেন এটি গুরুত্বপূর্ণ",
        "emg_do": "কী করবেন",
        "emg_why_text": "ঝুঁকির মাত্রা {level}, 100-এর মধ্যে {score}, তাই পরিস্থিতি দ্রুত বিপজ্জনক হতে পারে।",
        "no_data": "ওই জায়গার আবহাওয়ার তথ্য এখন পাওয়া যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।",
        "no_location": "আপনি কোন জায়গার কথা বলছেন বুঝতে পারিনি। শহর বা জেলার নাম বলবেন?",
        "out_of_scope": "আমি কেবল আবহাওয়া, পূর্বাভাস, সতর্কতা ও জলবায়ুর প্রবণতা নিয়ে সাহায্য করতে পারি। ভারতের যেকোনো জায়গার আবহাওয়া জিজ্ঞাসা করুন।",
        "forecast_lead": "{loc}-এর পূর্বাভাস: {day} — {cond}, {tmin}°C থেকে {tmax}°C-এর মধ্যে।",
        "alert_none": "{loc}-এর জন্য এখন কোনো সক্রিয় আবহাওয়া সতর্কতা নেই।",
        "alert_some": "{loc}-এর জন্য {count}টি সক্রিয় আবহাওয়া সতর্কতা রয়েছে।",
        "disclaimer": "এটি সাধারণ পরামর্শ, পেশাদার কৃষি, চিকিৎসা বা দুর্যোগ ব্যবস্থাপনা পরামর্শ নয়।",
        "advisory_watch_official": "এই এলাকার সরকারি সতর্কবার্তা অনুসরণ করুন এবং কোনো সতর্কতা জারি হলে সেই অনুযায়ী কাজ করুন।",
        "vb_lead_calm": "{loc}-এ এখন {hazard}। কী করতে হবে শুনুন।",
        "nwp_answer": "WeatherGPT GFS ও WRF-এর মতো সংখ্যাসূচক আবহাওয়া পূর্বাভাস ডেটাসেট সমর্থনের জন্য তৈরি। এই সংযোজনগুলি পরবর্তী পর্যায়ের জন্য পরিকল্পিত — এখন যে পূর্বাভাস দেখছেন তা রিয়েল-টাইম আবহাওয়া ডেটা থেকে আসে, এখানে চালানো কোনো সংখ্যাসূচক মডেল থেকে নয়।",
        "clim_param_temperature": "temperature",
        "clim_param_rainfall": "rainfall",
        "clim_param_humidity": "humidity",
        "clim_says_rising": "{loc}-এ {start} থেকে {end} সময়ে গড় {param} {change} বেড়েছে, সময়কালের গড় {average}-এর তুলনায়।",
        "clim_says_falling": "{loc}-এ {start} থেকে {end} সময়ে গড় {param} {change} কমেছে, সময়কালের গড় {average}-এর তুলনায়।",
        "clim_says_steady": "{loc}-এ {start} থেকে {end} সময়ে গড় {param} প্রায় {average}-এ স্থিতিশীল ছিল। এই সময়ের পরিবর্তন বছরে-বছরে ওঠানামার চেয়ে কম।",
        "clim_says_unknown": "{loc}-এর জন্য {param}-এর দিক বলার মতো যথেষ্ট পরিমাপ করা ইতিহাস নেই।",
        "clim_no_archive": "{loc}-এর জন্য ঐতিহাসিক জলবায়ু বিশ্লেষণ এখন পাওয়া যাচ্ছে না — ঐতিহাসিক সংরক্ষণাগারে পৌঁছানো যায়নি। এই ক্ষমতা পরবর্তী ডেটা সংযোজন পর্যায়ের জন্য প্রস্তুত করা হচ্ছে।",
        "clim_too_few": "{loc}-এর জন্য {param} প্রবণতা বলার মতো যথেষ্ট সম্পূর্ণ বছর ঐতিহাসিক সংরক্ষণাগারে নেই।",
        "clim_no_series": "দৈনিক ঐতিহাসিক সংরক্ষণাগারে তাপমাত্রা ও বৃষ্টিপাত আছে কিন্তু {param} নেই, তাই {loc}-এর জন্য দীর্ঘমেয়াদী {param} সিরিজ এখনও দেখানো যাচ্ছে না।",
        "vb_lead_clear": "{loc}-এ পরিস্থিতি এখন স্বাভাবিক।",
        "vb_lead_high": "{loc}-এ {hazard}। ঝুঁকি {level}। এখনই ব্যবস্থা নিন।",
        "vb_lead_severe": "{loc}-এ {hazard}। এটি এখনই করুন।",
        "vb_wind_now": 'বাতাস ঘণ্টায় প্রায় {wind} কিলোমিটার।',
        "vb_rain_chance": 'বৃষ্টির সম্ভাবনা প্রায় {prob} শতাংশ।',
        "vb_window": "আনুমানিক {time}-এ।",
    },
    "mr": {
        "impact_everyday_clear": "सामान्य दिवस — मोजमापांत टाळावे असे काही नाही.",
        "impact_everyday_rain": "दिवसावर पावसाचा परिणाम राहील.",
        "impact_everyday_risk": "नेहमीचे बेत बदलावे लागतील अशी स्थिती आहे.",
        "now": "{loc} मध्ये सध्या {temp}°C आहे, {cond}.",
        "feels": "जाणवते {feels}°C सारखे.",
        "humid": "हवेतील आर्द्रता खूप जास्त आहे, सुमारे {hum}%.",
        "rain_high": "पावसाची शक्यता जास्त आहे — पुढच्या तासात सुमारे {prob}%.",
        "rain_low": "सध्या पावसाची शक्यता कमी आहे.",
        "rain_24": "पुढच्या 24 तासांत सुमारे {mm} मिमी पाऊस अपेक्षित आहे.",
        "wind_calm": "वारा हलका आहे, सुमारे {wind} किमी/तास.",
        "wind_strong": "सुमारे {wind} किमी/तास वेगाचा जोरदार वारा — बाहेरचे काम कठीण होऊ शकते.",
        "heat_note": "खूप उकाडा जाणवेल, सुमारे {feels}°C.",
        "calm_tail": "परिस्थिती सामान्य आहे, सध्या तुमच्या भागासाठी कोणताही इशारा नाही.",
        "emg_headline": "{loc} साठी इशारा: {hazard}.",
        "emg_what": "काय घडत आहे",
        "emg_why": "हे का महत्त्वाचे आहे",
        "emg_do": "काय करावे",
        "emg_why_text": "धोक्याची पातळी {level} आहे, 100 पैकी {score}, त्यामुळे परिस्थिती लवकर धोकादायक होऊ शकते.",
        "no_data": "त्या ठिकाणची हवामान माहिती सध्या मिळाली नाही. थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "no_location": "तुम्ही कोणत्या ठिकाणाबद्दल विचारत आहात हे समजले नाही. शहर किंवा जिल्ह्याचे नाव सांगाल का?",
        "out_of_scope": "मी फक्त हवामान, अंदाज, इशारे आणि हवामान बदलाच्या कलांबाबत मदत करू शकतो. भारतातील कोणत्याही ठिकाणचे हवामान विचारा.",
        "forecast_lead": "{loc} चा अंदाज: {day} — {cond}, {tmin}°C ते {tmax}°C दरम्यान.",
        "alert_none": "{loc} साठी सध्या कोणताही सक्रिय हवामान इशारा नाही.",
        "alert_some": "{loc} साठी {count} सक्रिय हवामान इशारे आहेत.",
        "disclaimer": "हे सर्वसाधारण मार्गदर्शन आहे, व्यावसायिक कृषी, वैद्यकीय किंवा आपत्ती व्यवस्थापन सल्ला नाही.",
        "advisory_watch_official": "या भागातील अधिकृत इशाऱ्यांवर लक्ष ठेवा आणि इशारा दिल्यास त्यानुसार कृती करा.",
        "vb_lead_calm": "{loc} मध्ये सध्या {hazard}. काय करायचे ते ऐका.",
        "nwp_answer": "WeatherGPT ला GFS आणि WRF सारख्या संख्यात्मक हवामान अंदाज डेटासेटसाठी तयार केले आहे. हे समाकलन पुढील टप्प्यासाठी नियोजित आहे — आता दिसणारा अंदाज रिअल-टाइम हवामान डेटावरून येतो, येथे चालवलेल्या कोणत्याही संख्यात्मक मॉडेलवरून नाही.",
        "clim_param_temperature": "temperature",
        "clim_param_rainfall": "rainfall",
        "clim_param_humidity": "humidity",
        "clim_says_rising": "{loc} मध्ये {start} ते {end} दरम्यान सरासरी {param} {change} वाढले, कालावधी सरासरी {average} च्या तुलनेत.",
        "clim_says_falling": "{loc} मध्ये {start} ते {end} दरम्यान सरासरी {param} {change} घटले, कालावधी सरासरी {average} च्या तुलनेत.",
        "clim_says_steady": "{loc} मध्ये {start} ते {end} दरम्यान सरासरी {param} सुमारे {average} वर स्थिर राहिले. या कालावधीतील बदल वार्षिक चढउतारापेक्षा कमी आहे.",
        "clim_says_unknown": "{loc} साठी {param} ची दिशा सांगण्याइतका पुरेसा मोजलेला इतिहास नाही.",
        "clim_no_archive": "{loc} साठी ऐतिहासिक हवामान विश्लेषण सध्या उपलब्ध नाही — ऐतिहासिक संग्रहापर्यंत पोहोचता आले नाही. ही क्षमता पुढील डेटा समाकलन टप्प्यासाठी तयार केली जात आहे.",
        "clim_too_few": "{loc} साठी {param} कल सांगण्याइतकी पूर्ण वर्षे ऐतिहासिक संग्रहात नाहीत.",
        "clim_no_series": "दैनिक ऐतिहासिक संग्रहात तापमान आणि पर्जन्य आहे पण {param} नाही, त्यामुळे {loc} साठी दीर्घकालीन {param} मालिका अद्याप दाखवता येत नाही.",
        "vb_lead_clear": "{loc} मध्ये परिस्थिती सध्या सामान्य आहे.",
        "vb_lead_high": "{loc} मध्ये {hazard}. धोका {level} आहे. आत्ताच पावले उचला.",
        "vb_lead_severe": "{loc} मध्ये {hazard}. हे आत्ताच करा.",
        "vb_wind_now": 'वारा ताशी सुमारे {wind} किलोमीटर आहे.',
        "vb_rain_chance": 'पावसाची शक्यता सुमारे {prob} टक्के आहे.',
        "vb_window": "अंदाजे {time} वाजता अपेक्षित.",
    },
    "as": {
        "impact_everyday_clear": "সাধাৰণ দিন — জোখত এনেকুৱা একো নাই যিটো এৰাব লাগে।",
        "impact_everyday_rain": "দিনটোত বৰষুণৰ প্ৰভাৱ থাকিব।",
        "impact_everyday_risk": "সাধাৰণ পৰিকল্পনা সলনি কৰিব লগা অৱস্থা।",
        "now": "{loc}ত এতিয়া {temp}°C, {cond}।",
        "feels": "অনুভৱ হৈছে {feels}°C ৰ দৰে।",
        "humid": "বতাহত আৰ্দ্ৰতা বহুত বেছি, প্ৰায় {hum}%।",
        "rain_high": "বৰষুণৰ সম্ভাৱনা বেছি — পিছৰ এঘণ্টাত প্ৰায় {prob}%।",
        "rain_low": "এতিয়া বৰষুণৰ সম্ভাৱনা কম।",
        "rain_24": "অহা 24 ঘণ্টাত প্ৰায় {mm} মি.মি. বৰষুণ হ'ব পাৰে।",
        "wind_calm": "বতাহ পাতল, প্ৰায় {wind} কি.মি./ঘণ্টা।",
        "wind_strong": "প্ৰায় {wind} কি.মি./ঘণ্টা বেগৰ প্ৰবল বতাহ — বাহিৰৰ কাম কঠিন হ'ব পাৰে।",
        "heat_note": "বহুত গৰম অনুভৱ হ'ব, প্ৰায় {feels}°C।",
        "calm_tail": "পৰিস্থিতি স্বাভাৱিক, এতিয়া আপোনাৰ এলেকাৰ বাবে কোনো সতৰ্কবাণী নাই।",
        "emg_headline": "{loc}ৰ বাবে সতৰ্কবাণী: {hazard}।",
        "emg_what": "কি হৈ আছে",
        "emg_why": "ই কিয় গুৰুত্বপূৰ্ণ",
        "emg_do": "কি কৰিব",
        "emg_why_text": "বিপদৰ স্তৰ {level}, 100ৰ ভিতৰত {score}, গতিকে পৰিস্থিতি সোনকালে বিপজ্জনক হ'ব পাৰে।",
        "no_data": "সেই ঠাইৰ বতৰৰ তথ্য এতিয়া পোৱা নগ'ল। অলপ পিছত পুনৰ চেষ্টা কৰক।",
        "no_location": "আপুনি কোনখন ঠাইৰ কথা কৈছে বুজিব পৰা নগ'ল। চহৰ বা জিলাৰ নাম ক'ব নেকি?",
        "out_of_scope": "মই কেৱল বতৰ, পূৰ্বাভাস, সতৰ্কবাণী আৰু জলবায়ুৰ ধাৰাৰ বিষয়ে সহায় কৰিব পাৰোঁ। ভাৰতৰ যিকোনো ঠাইৰ বতৰ সুধিব পাৰে।",
        "forecast_lead": "{loc}ৰ পূৰ্বাভাস: {day} — {cond}, {tmin}°C ৰ পৰা {tmax}°C ৰ মাজত।",
        "alert_none": "{loc}ৰ বাবে এতিয়া কোনো সক্ৰিয় বতৰৰ সতৰ্কবাণী নাই।",
        "alert_some": "{loc}ৰ বাবে {count}টা সক্ৰিয় বতৰৰ সতৰ্কবাণী আছে।",
        "disclaimer": "এয়া সাধাৰণ পৰামৰ্শ, বৃত্তিগত কৃষি, চিকিৎসা বা দুৰ্যোগ ব্যৱস্থাপনাৰ পৰামৰ্শ নহয়।",
        "advisory_watch_official": "এই অঞ্চলৰ চৰকাৰী সতৰ্কবাণী চাই থাকক আৰু কোনো সতৰ্কবাণী জাৰি হ’লে সেই অনুসৰি ব্যৱস্থা লওক।",
        "vb_lead_calm": "{loc}ত এতিয়া {hazard}। কি কৰিব লাগে শুনক।",
        "nwp_answer": "WeatherGPT ক GFS আৰু WRF-ৰ দৰে সংখ্যাগত বতৰ পূৰ্বাভাস ডেটাছেটৰ বাবে সজোৱা হৈছে। এই সংযোজনসমূহ পৰৱৰ্তী পৰ্যায়ৰ বাবে পৰিকল্পিত — এতিয়া দেখা পূৰ্বাভাস ৰিয়েল-টাইম বতৰ তথ্যৰ পৰা আহে, ইয়াত চলোৱা কোনো সংখ্যাগত মডেলৰ পৰা নহয়।",
        "clim_param_temperature": "temperature",
        "clim_param_rainfall": "rainfall",
        "clim_param_humidity": "humidity",
        "clim_says_rising": "{loc}ত {start}ৰ পৰা {end}লৈ গড় {param} {change} বাঢ়িছে, সময়ছোৱাৰ গড় {average}ৰ তুলনাত।",
        "clim_says_falling": "{loc}ত {start}ৰ পৰা {end}লৈ গড় {param} {change} কমিছে, সময়ছোৱাৰ গড় {average}ৰ তুলনাত।",
        "clim_says_steady": "{loc}ত {start}ৰ পৰা {end}লৈ গড় {param} প্ৰায় {average}ত স্থিৰ আছিল। এই সময়ছোৱাৰ সালসলনি বছৰৰ পৰা বছৰলৈ ওঠা-নমাতকৈ কম।",
        "clim_says_unknown": "{loc}ৰ বাবে {param}ৰ দিশ ক'বলৈ যথেষ্ট জোখা ইতিহাস নাই।",
        "clim_no_archive": "{loc}ৰ বাবে ঐতিহাসিক জলবায়ু বিশ্লেষণ এতিয়া উপলব্ধ নহয় — ঐতিহাসিক সংগ্ৰহলৈ যাব পৰা নগ'ল। এই সক্ষমতা পৰৱৰ্তী তথ্য সংযোজন পৰ্যায়ৰ বাবে প্ৰস্তুত কৰা হৈ আছে।",
        "clim_too_few": "{loc}ৰ বাবে {param} ধাৰা ক'বলৈ যথেষ্ট সম্পূৰ্ণ বছৰ ঐতিহাসিক সংগ্ৰহত নাই।",
        "clim_no_series": "দৈনিক ঐতিহাসিক সংগ্ৰহত উষ্ণতা আৰু বৰষুণ আছে কিন্তু {param} নাই, সেয়েহে {loc}ৰ বাবে দীৰ্ঘম্যাদী {param} শৃংখলা এতিয়াও দেখুৱাব নোৱাৰি।",
        "vb_lead_clear": "{loc}ত পৰিস্থিতি এতিয়া স্বাভাৱিক।",
        "vb_lead_high": "{loc}ত {hazard}। বিপদ {level}। এতিয়াই ব্যৱস্থা লওক।",
        "vb_lead_severe": "{loc}ত {hazard}। এইটো এতিয়াই কৰক।",
        "vb_wind_now": 'বতাহ ঘণ্টাত প্ৰায় {wind} কিলোমিটাৰ।',
        "vb_rain_chance": 'বৰষুণৰ সম্ভাৱনা প্ৰায় {prob} শতাংশ।',
        "vb_window": "প্ৰায় {time} বজাত।",
    },
}

# --- Base safety actions per hazard ----------------------------------------
HAZARD_ACTIONS: dict[str, dict[str, list[str]]] = {
    "Heavy Rainfall": {
        "en": ["Avoid low-lying roads and underpasses.",
               "Keep the drains near your home clear.",
               "Delay non-essential travel until the rain eases."],
        "hi": ["निचली सड़कों और अंडरपास से बचें।",
               "घर के पास नालियाँ साफ़ रखें।",
               "बारिश कम होने तक ग़ैर-ज़रूरी यात्रा टालें।"],
        "te": ["లోతట్టు రోడ్లు, అండర్‌పాస్‌లకు దూరంగా ఉండండి.",
               "ఇంటి దగ్గర కాలువలు శుభ్రంగా ఉంచండి.",
               "వర్షం తగ్గే వరకు అనవసర ప్రయాణాలు వాయిదా వేయండి."],
        "bn": ["নিচু রাস্তা ও আন্ডারপাস এড়িয়ে চলুন।",
               "বাড়ির কাছের নর্দমা পরিষ্কার রাখুন।",
               "বৃষ্টি না কমা পর্যন্ত অপ্রয়োজনীয় যাত্রা স্থগিত রাখুন।"],
        "mr": ["सखल रस्ते आणि भुयारी मार्ग टाळा.",
               "घराजवळील नाले स्वच्छ ठेवा.",
               "पाऊस कमी होईपर्यंत अनावश्यक प्रवास टाळा."],
        "as": ["নিম্ন অঞ্চলৰ ৰাস্তা আৰু আণ্ডাৰপাছ এৰাই চলক।",
               "ঘৰৰ ওচৰৰ নলা পৰিষ্কাৰ ৰাখক।",
               "বৰষুণ নকমালৈকে অপ্ৰয়োজনীয় যাত্ৰা পিছুৱাই দিয়ক।"],
    },
    "Flood Risk": {
        "en": ["Move to higher ground if water starts entering your area.",
               "Keep documents, medicines and a torch in a waterproof bag.",
               "Do not walk or drive through moving flood water."],
        "hi": ["अगर पानी आपके इलाक़े में आने लगे तो ऊँची जगह पर जाएँ।",
               "दस्तावेज़, दवाइयाँ और टॉर्च वाटरप्रूफ़ बैग में रखें।",
               "बहते बाढ़ के पानी में पैदल या गाड़ी से न जाएँ।"],
        "te": ["నీరు మీ ప్రాంతంలోకి రావడం మొదలైతే ఎత్తైన ప్రదేశానికి వెళ్లండి.",
               "పత్రాలు, మందులు, టార్చ్ నీరు తగలని సంచిలో ఉంచండి.",
               "ప్రవహిస్తున్న వరద నీటిలో నడవడం, వాహనం నడపడం చేయవద్దు."],
        "bn": ["এলাকায় জল ঢুকতে শুরু করলে উঁচু জায়গায় সরে যান।",
               "কাগজপত্র, ওষুধ ও টর্চ জলরোধী ব্যাগে রাখুন।",
               "বয়ে যাওয়া বন্যার জলে হাঁটবেন না বা গাড়ি চালাবেন না।"],
        "mr": ["पाणी तुमच्या भागात शिरू लागल्यास उंच जागी जा.",
               "कागदपत्रे, औषधे आणि बॅटरी जलरोधक पिशवीत ठेवा.",
               "वाहत्या पुराच्या पाण्यातून चालू नका किंवा वाहन नेऊ नका."],
        "as": ["পানী আপোনাৰ এলেকাত সোমাবলৈ ধৰিলে ওখ ঠাইলৈ যাওক।",
               "নথি-পত্ৰ, ঔষধ আৰু টৰ্চ পানী নোসোমোৱা বেগত ৰাখক।",
               "বৈ থকা বানপানীৰ মাজেৰে খোজ কাঢ়ি বা গাড়ী চলাই নাযাব।"],
    },
    "Strong Wind": {
        "en": ["Secure loose roofing sheets, boards and outdoor items.",
               "Stay away from old trees, hoardings and electric poles.",
               "Park vehicles away from trees and weak walls."],
        "hi": ["छत की चादरें, बोर्ड और बाहर रखी चीज़ें बाँध दें।",
               "पुराने पेड़ों, होर्डिंग और बिजली के खंभों से दूर रहें।",
               "गाड़ी पेड़ों और कमज़ोर दीवारों से दूर खड़ी करें।"],
        "te": ["పైకప్పు రేకులు, బోర్డులు, బయట ఉన్న వస్తువులను గట్టిగా కట్టండి.",
               "పాత చెట్లు, హోర్డింగ్‌లు, విద్యుత్ స్తంభాలకు దూరంగా ఉండండి.",
               "వాహనాలను చెట్లు, బలహీన గోడల నుండి దూరంగా నిలపండి."],
        "bn": ["ছাদের টিন, বোর্ড ও বাইরের জিনিস শক্ত করে বেঁধে রাখুন।",
               "পুরনো গাছ, হোর্ডিং ও বিদ্যুতের খুঁটি থেকে দূরে থাকুন।",
               "গাছ ও দুর্বল দেয়াল থেকে দূরে গাড়ি রাখুন।"],
        "mr": ["छताचे पत्रे, फलक आणि बाहेरील वस्तू घट्ट बांधा.",
               "जुनी झाडे, होर्डिंग आणि विजेच्या खांबांपासून दूर राहा.",
               "झाडे आणि कमकुवत भिंतींपासून दूर वाहन उभे करा."],
        "as": ["চালৰ টিন, বৰ্ড আৰু বাহিৰৰ বস্তুবোৰ শকতকৈ বান্ধি ৰাখক।",
               "পুৰণি গছ, হৰ্ডিং আৰু বিজুলীৰ খুঁটাৰ পৰা আঁতৰি থাকক।",
               "গছ আৰু দুৰ্বল দেৱালৰ পৰা আঁতৰত গাড়ী ৰাখক।"],
    },
    "Extreme Heat": {
        "en": ["Drink water often, even if you do not feel thirsty.",
               "Avoid being outdoors between 12 noon and 4 pm.",
               "Watch for dizziness, headache or cramps and rest in the shade."],
        "hi": ["प्यास न लगे तब भी बार-बार पानी पिएँ।",
               "दोपहर 12 से शाम 4 बजे तक बाहर निकलने से बचें।",
               "चक्कर, सिरदर्द या ऐंठन हो तो छाँव में आराम करें।"],
        "te": ["దాహం వేయకపోయినా తరచూ నీరు తాగండి.",
               "మధ్యాహ్నం 12 నుంచి సాయంత్రం 4 గంటల మధ్య బయటకు వెళ్లవద్దు.",
               "కళ్లు తిరగడం, తలనొప్పి, కండరాల నొప్పి వస్తే నీడలో విశ్రాంతి తీసుకోండి."],
        "bn": ["তেষ্টা না পেলেও ঘন ঘন জল খান।",
               "দুপুর 12টা থেকে বিকেল 4টা পর্যন্ত বাইরে বেরোনো এড়িয়ে চলুন।",
               "মাথা ঘোরা, মাথাব্যথা বা খিঁচুনি হলে ছায়ায় বিশ্রাম নিন।"],
        "mr": ["तहान लागली नसली तरी वारंवार पाणी प्या.",
               "दुपारी 12 ते संध्याकाळी 4 दरम्यान बाहेर जाणे टाळा.",
               "चक्कर, डोकेदुखी किंवा पेटके आल्यास सावलीत विश्रांती घ्या."],
        "as": ["পিয়াহ নালাগিলেও বাৰে বাৰে পানী খাওক।",
               "দুপৰীয়া 12 বজাৰ পৰা আবেলি 4 বজালৈ বাহিৰলৈ নাযাব।",
               "মূৰ ঘূৰোৱা, মূৰৰ বিষ বা পেশীৰ বিষ হ'লে ছাঁত জিৰণি লওক।"],
    },
    "Lightning/Storm": {
        "en": ["Go indoors immediately and stay away from windows.",
               "Do not shelter under trees or near metal structures.",
               "Unplug electrical appliances until the storm passes."],
        "hi": ["तुरंत घर के अंदर जाएँ और खिड़कियों से दूर रहें।",
               "पेड़ों के नीचे या धातु की चीज़ों के पास न रुकें।",
               "तूफ़ान गुज़रने तक बिजली के उपकरण बंद कर दें।"],
        "te": ["వెంటనే ఇంట్లోకి వెళ్లి కిటికీలకు దూరంగా ఉండండి.",
               "చెట్ల కింద లేదా లోహపు నిర్మాణాల దగ్గర ఆగవద్దు.",
               "తుఫాను వెళ్లే వరకు విద్యుత్ ఉపకరణాలను తీసివేయండి."],
        "bn": ["সঙ্গে সঙ্গে ঘরে ঢুকুন এবং জানালা থেকে দূরে থাকুন।",
               "গাছের নিচে বা ধাতব কাঠামোর কাছে আশ্রয় নেবেন না।",
               "ঝড় না থামা পর্যন্ত বৈদ্যুতিক যন্ত্র বন্ধ রাখুন।"],
        "mr": ["ताबडतोब घरात जा आणि खिडक्यांपासून दूर राहा.",
               "झाडाखाली किंवा धातूच्या रचनांजवळ थांबू नका.",
               "वादळ जाईपर्यंत विजेची उपकरणे बंद ठेवा."],
        "as": ["লগে লগে ঘৰৰ ভিতৰলৈ যাওক আৰু খিৰিকীৰ পৰা আঁতৰি থাকক।",
               "গছৰ তলত বা ধাতুৰ গাঁথনিৰ ওচৰত আশ্ৰয় নল'ব।",
               "ধুমুহা নোযোৱালৈকে বিদ্যুৎ সঁজুলি বন্ধ কৰি ৰাখক।"],
    },
}

# Hazard -> advice family, so profile guidance stays maintainable.
HAZARD_FAMILY: dict[str, str] = {
    "Heavy Rainfall": "water",
    "Flood Risk": "water",
    "Strong Wind": "wind",
    "Extreme Heat": "heat",
    "Lightning/Storm": "storm",
}

PROFILE_ACTIONS: dict[str, dict[str, dict[str, str]]] = {
    "aviation": {
        "water": {
            "en": "Expect reduced visibility and standing water on surfaces; review official aviation weather information before operations.",
            "hi": "दृश्यता घटने और सतहों पर पानी जमा होने की आशंका रखें; संचालन से पहले आधिकारिक विमानन मौसम जानकारी देखें।",
            "te": "దృశ్యత తగ్గడం, ఉపరితలాలపై నీరు నిలవడం ఆశించండి; కార్యకలాపాల ముందు అధికారిక విమానయాన వాతావరణ సమాచారం చూడండి.",
            "bn": "দৃশ্যমানতা কমা ও পৃষ্ঠে জল জমার আশা রাখুন; পরিচালনার আগে সরকারি বিমান আবহাওয়া তথ্য দেখুন।",
            "mr": "दृश्यमानता घटणे व पृष्ठभागावर पाणी साचणे अपेक्षित धरा; कार्यवाहीपूर्वी अधिकृत विमान हवामान माहिती पहा.",
            "as": "দৃশ্যমানতা কমা আৰু পৃষ্ঠত পানী জমাৰ আশা ৰাখক; পৰিচালনাৰ আগতে চৰকাৰী বিমান বতৰ তথ্য চাওক।",
        },
        "wind": {
            "en": "Review crosswind and gust limits for the aircraft and runway in use, against official aviation weather information.",
            "hi": "विमान और रनवे की क्रॉसविंड व झोंके सीमाएँ आधिकारिक विमानन मौसम जानकारी के साथ जाँचें।",
            "te": "ఉపయోగించే విమానం, రన్‌వే క్రాస్‌విండ్, ఈదురుగాలి పరిమితులను అధికారిక విమానయాన సమాచారంతో సరిచూడండి.",
            "bn": "ব্যবহৃত বিমান ও রানওয়ের ক্রসউইন্ড ও দমকার সীমা সরকারি বিমান আবহাওয়া তথ্যের সঙ্গে দেখুন।",
            "mr": "वापरातील विमान व धावपट्टीच्या क्रॉसविंड आणि झोत मर्यादा अधिकृत विमान हवामान माहितीसह तपासा.",
            "as": "ব্যৱহৃত বিমান আৰু ৰাণৱেৰ ক্ৰছৱিণ্ড আৰু দমকাৰ সীমা চৰকাৰী বিমান বতৰ তথ্যৰ সৈতে চাওক।",
        },
        "heat": {
            "en": "Account for reduced performance in high density altitude and review the official aviation weather information.",
            "hi": "अधिक घनत्व-ऊँचाई पर घटे प्रदर्शन का हिसाब रखें और आधिकारिक विमानन मौसम जानकारी देखें।",
            "te": "అధిక సాంద్రత ఎత్తులో పనితీరు తగ్గడాన్ని లెక్కించండి, అధికారిక విమానయాన వాతావరణ సమాచారం చూడండి.",
            "bn": "উচ্চ ঘনত্ব-উচ্চতায় কমে যাওয়া কর্মক্ষমতা হিসাবে রাখুন ও সরকারি বিমান আবহাওয়া তথ্য দেখুন।",
            "mr": "जास्त घनता-उंचीवर घटलेली कामगिरी लक्षात घ्या व अधिकृत विमान हवामान माहिती पहा.",
            "as": "উচ্চ ঘনত্ব-উচ্চতাত কমা কাৰ্যক্ষমতা হিচাপত ৰাখক আৰু চৰকাৰী বিমান বতৰ তথ্য চাওক।",
        },
        "storm": {
            "en": "Monitor convective activity and review official aviation weather information before operations.",
            "hi": "गरज-तूफ़ान की गतिविधि पर नज़र रखें और संचालन से पहले आधिकारिक विमानन मौसम जानकारी देखें।",
            "te": "ఉరుములు-తుఫాను కార్యకలాపాలను గమనిస్తూ, కార్యకలాపాల ముందు అధికారిక విమానయాన వాతావరణ సమాచారం చూడండి.",
            "bn": "বজ্র-ঝড়ের গতিবিধি নজরে রাখুন এবং পরিচালনার আগে সরকারি বিমান আবহাওয়া তথ্য দেখুন।",
            "mr": "गडगडाटी हालचालींवर लक्ष ठेवा आणि कार्यवाहीपूर्वी अधिकृत विमान हवामान माहिती पहा.",
            "as": "ধুমুহাৰ কাৰ্যকলাপ নজৰত ৰাখক আৰু পৰিচালনাৰ আগতে চৰকাৰী বিমান বতৰ তথ্য চাওক।",
        },
    },
    "disaster": {
        "water": {
            "en": "Track rainfall accumulation and low-lying exposure, and confirm against the official warning before committing resources.",
            "hi": "बारिश के जमाव और निचले इलाक़ों पर नज़र रखें, संसाधन लगाने से पहले आधिकारिक चेतावनी से मिलान करें।",
            "te": "వర్షపాతం పోగు, పల్లపు ప్రాంతాలను గమనించండి; వనరులు కేటాయించే ముందు అధికారిక హెచ్చరికతో సరిచూడండి.",
            "bn": "বৃষ্টির জমা ও নিচু এলাকার ঝুঁকি দেখুন, সম্পদ নিয়োগের আগে সরকারি সতর্কতার সঙ্গে মিলিয়ে নিন।",
            "mr": "पावसाची साठवण व सखल भागांचा धोका पहा, साधने वापरण्यापूर्वी अधिकृत इशाऱ्याशी ताळमेळ घ्या.",
            "as": "বৰষুণৰ জমা আৰু নিম্ন অঞ্চলৰ বিপদ চাওক, সম্পদ নিয়োগৰ আগতে চৰকাৰী সতৰ্কবাণীৰ সৈতে মিলাই লওক।",
        },
        "wind": {
            "en": "Review exposure of temporary shelters, hoardings and overhead lines, and keep crews on standby.",
            "hi": "अस्थायी आश्रयों, होर्डिंग और ऊपरी तारों का जोखिम देखें, दल तैयार रखें।",
            "te": "తాత్కాలిక ఆశ్రయాలు, హోర్డింగ్‌లు, పైతీగల ప్రమాదాన్ని చూడండి; బృందాలను సిద్ధంగా ఉంచండి.",
            "bn": "অস্থায়ী আশ্রয়, হোর্ডিং ও উপরের তারের ঝুঁকি দেখুন, দল প্রস্তুত রাখুন।",
            "mr": "तात्पुरते निवारे, होर्डिंग व वरच्या तारांचा धोका पहा, पथके सज्ज ठेवा.",
            "as": "অস্থায়ী আশ্ৰয়, হৰ্ডিং আৰু ওপৰৰ তাঁৰৰ বিপদ চাওক, দল সাজু ৰাখক।",
        },
        "heat": {
            "en": "Prioritise water points, shade and outreach to people without cooling.",
            "hi": "पानी की जगहें, छाँव और बिना ठंडक वाले लोगों तक पहुँच को प्राथमिकता दें।",
            "te": "నీటి కేంద్రాలు, నీడ, చల్లదనం లేని వారికి చేరువను ప్రాధాన్యం ఇవ్వండి.",
            "bn": "জলের জায়গা, ছায়া ও শীতল ব্যবস্থাহীন মানুষের কাছে পৌঁছানোকে অগ্রাধিকার দিন।",
            "mr": "पाणी केंद्रे, सावली व थंडावा नसलेल्या लोकांपर्यंत पोहोच यांना प्राधान्य द्या.",
            "as": "পানীৰ ঠাই, ছাঁ আৰু চেঁচা ব্যৱস্থা নথকা মানুহৰ ওচৰ পোৱাক অগ্ৰাধিকাৰ দিয়ক।",
        },
        "storm": {
            "en": "Monitor escalation indicators and official warnings before activating response resources.",
            "hi": "बढ़ोतरी के संकेतों और सरकारी चेतावनियों पर नज़र रखें, फिर संसाधन सक्रिय करें।",
            "te": "పెరుగుదల సూచికలు, అధికారిక హెచ్చరికలు గమనించాకే స్పందన వనరులను సక్రియం చేయండి.",
            "bn": "বৃদ্ধির সূচক ও সরকারি সতর্কতা দেখে তবেই সাড়া-সম্পদ সক্রিয় করুন।",
            "mr": "वाढीचे निर्देशक व अधिकृत इशारे पाहूनच प्रतिसाद साधने सक्रिय करा.",
            "as": "বৃদ্ধিৰ সূচক আৰু চৰকাৰী সতৰ্কবাণী চাইহে সঁহাৰি সম্পদ সক্ৰিয় কৰক।",
        },
    },
    "smart_city": {
        "water": {
            "en": "Monitor rainfall accumulation and vulnerable drainage zones if precipitation intensifies.",
            "hi": "बारिश के जमाव और कमज़ोर जलनिकासी क्षेत्रों पर नज़र रखें, अगर बारिश तेज़ हो।",
            "te": "వర్షం పెరిగితే వర్షపాతం పోగు, బలహీన డ్రైనేజీ ప్రాంతాలను గమనించండి.",
            "bn": "বৃষ্টি বাড়লে জমা ও দুর্বল নিকাশি এলাকাগুলি নজরে রাখুন।",
            "mr": "पाऊस वाढल्यास साठवण व कमकुवत निचरा भागांवर लक्ष ठेवा.",
            "as": "বৰষুণ বাঢ়িলে জমা আৰু দুৰ্বল নিষ্কাশন অঞ্চল নজৰত ৰাখক।",
        },
        "wind": {
            "en": "Inspect hoardings, scaffolding and street furniture on the main corridors.",
            "hi": "मुख्य मार्गों पर होर्डिंग, मचान और सड़क के ढाँचे जाँचें।",
            "te": "ప్రధాన మార్గాల్లో హోర్డింగ్‌లు, పరంజా, వీధి నిర్మాణాలను తనిఖీ చేయండి.",
            "bn": "প্রধান পথে হোর্ডিং, ভারা ও রাস্তার কাঠামো পরীক্ষা করুন।",
            "mr": "मुख्य मार्गांवरील होर्डिंग, मचाण व रस्त्यावरील रचना तपासा.",
            "as": "মুখ্য পথত হৰ্ডিং, মচান আৰু বাটৰ গাঁথনি পৰীক্ষা কৰক।",
        },
        "heat": {
            "en": "Watch peak demand on water and power, and keep public cooling points open longer.",
            "hi": "पानी और बिजली की चरम माँग देखें, और सार्वजनिक ठंडक केंद्र ज़्यादा देर खुले रखें।",
            "te": "నీరు, విద్యుత్ గరిష్ఠ డిమాండ్ చూడండి; ప్రజా చల్లదన కేంద్రాలను ఎక్కువసేపు తెరిచి ఉంచండి.",
            "bn": "জল ও বিদ্যুতের সর্বোচ্চ চাহিদা দেখুন, আর সরকারি শীতল কেন্দ্র বেশি সময় খোলা রাখুন।",
            "mr": "पाणी व वीजेची सर्वोच्च मागणी पहा, आणि सार्वजनिक थंडावा केंद्रे जास्त वेळ उघडी ठेवा.",
            "as": "পানী আৰু বিজুলীৰ সৰ্বোচ্চ চাহিদা চাওক, আৰু ৰাজহুৱা চেঁচা কেন্দ্ৰ বেছি সময় খোলা ৰাখক।",
        },
        "storm": {
            "en": "Monitor infrastructure and urban impacts, and keep drainage and traffic crews reachable.",
            "hi": "बुनियादी ढाँचे और शहरी असर पर नज़र रखें, जलनिकासी और यातायात दल संपर्क में रखें।",
            "te": "మౌలిక సదుపాయాలు, పట్టణ ప్రభావాలను గమనించండి; డ్రైనేజీ, ట్రాఫిక్ సిబ్బందిని అందుబాటులో ఉంచండి.",
            "bn": "পরিকাঠামো ও নগর প্রভাব নজরে রাখুন, নিকাশি ও ট্রাফিক দলকে নাগালে রাখুন।",
            "mr": "पायाभूत सुविधा व शहरी परिणामांवर लक्ष ठेवा, निचरा व वाहतूक पथके संपर्कात ठेवा.",
            "as": "আন্তঃগাঁথনি আৰু নগৰীয়া প্ৰভাৱ নজৰত ৰাখক, নিষ্কাশন আৰু ট্ৰেফিক দল যোগাযোগত ৰাখক।",
        },
    },
    "researcher": {
        "water": {
            "en": "Monitor the precipitation trend and compare the current observation with available historical data.",
            "hi": "बारिश के रुझान पर नज़र रखें और मौजूदा अवलोकन की तुलना उपलब्ध ऐतिहासिक आँकड़ों से करें।",
            "te": "వర్షపాత ధోరణిని గమనించి, ప్రస్తుత పరిశీలనను అందుబాటులో ఉన్న చారిత్రక డేటాతో పోల్చండి.",
            "bn": "বৃষ্টির প্রবণতা দেখুন এবং চলতি পর্যবেক্ষণ উপলব্ধ ঐতিহাসিক তথ্যের সঙ্গে তুলনা করুন।",
            "mr": "पावसाचा कल पहा आणि सध्याचे निरीक्षण उपलब्ध ऐतिहासिक माहितीशी ताडून पहा.",
            "as": "বৰষুণৰ প্ৰৱণতা চাওক আৰু বৰ্তমানৰ পৰ্যবেক্ষণ উপলব্ধ ঐতিহাসিক তথ্যৰ সৈতে তুলনা কৰক।",
        },
        "wind": {
            "en": "Record the gust and sustained values separately, and note the reporting interval.",
            "hi": "झोंके और लगातार हवा के मान अलग-अलग दर्ज करें, और रिपोर्टिंग अंतराल नोट करें।",
            "te": "ఈదురుగాలి, నిలకడ గాలి విలువలను వేరుగా నమోదు చేసి, రిపోర్టింగ్ వ్యవధిని గమనించండి.",
            "bn": "দমকা ও স্থির বাতাসের মান আলাদা লিখুন, আর রিপোর্টিং ব্যবধান লক্ষ করুন।",
            "mr": "झोत व सलग वाऱ्याची मूल्ये वेगळी नोंदवा, आणि नोंदणीचा अंतराल लक्षात घ्या.",
            "as": "দমকা আৰু নিৰন্তৰ বতাহৰ মান পৃথককৈ লিখক, আৰু ৰিপৰ্টিং ব্যৱধান মন কৰক।",
        },
        "heat": {
            "en": "Track the temperature anomaly against the archive rather than against today's comfort.",
            "hi": "तापमान का विचलन आज के आराम से नहीं, अभिलेख से आँकें।",
            "te": "ఉష్ణోగ్రత వ్యత్యాసాన్ని నేటి సౌకర్యంతో కాక ఆర్కైవ్‌తో పోల్చి చూడండి.",
            "bn": "তাপমাত্রার বিচ্যুতি আজকের আরামের সঙ্গে নয়, আর্কাইভের সঙ্গে মিলিয়ে দেখুন।",
            "mr": "तापमान विचलन आजच्या आरामाशी नव्हे, संग्रहाशी ताडून पहा.",
            "as": "উষ্ণতাৰ ব্যতিক্ৰম আজিৰ আৰামৰ সৈতে নহয়, আৰ্কাইভৰ সৈতে চাওক।",
        },
        "storm": {
            "en": "Log the convective signal and its timing while the hourly series still holds it.",
            "hi": "गरज-तूफ़ान का संकेत और उसका समय तब दर्ज करें जब घंटेवार शृंखला में मौजूद है।",
            "te": "గంటవారీ శ్రేణిలో ఉన్నప్పుడే ఉరుముల సంకేతాన్ని, దాని సమయాన్ని నమోదు చేయండి.",
            "bn": "ঘণ্টাভিত্তিক সিরিজে থাকতেই বজ্র-সংকেত ও তার সময় লিখে রাখুন।",
            "mr": "तासवार मालिकेत असतानाच गडगडाटाचा संकेत व त्याची वेळ नोंदवा.",
            "as": "ঘণ্টাভিত্তিক শৃংখলাত থাকোঁতেই ধুমুহাৰ সংকেত আৰু তাৰ সময় লিখি থওক।",
        },
    },
    "household": {
        "water": {
            "en": "Prepare the household for the expected rain and keep weather-sensitive items indoors.",
            "hi": "घर को बारिश के लिए तैयार करें और मौसम से ख़राब होने वाली चीज़ें अंदर रखें।",
            "te": "వర్షానికి ఇంటిని సిద్ధం చేసి, వాతావరణానికి పాడయ్యే వస్తువులను లోపల ఉంచండి.",
            "bn": "বৃষ্টির জন্য ঘর তৈরি রাখুন এবং আবহাওয়ায় নষ্ট হওয়া জিনিস ভিতরে রাখুন।",
            "mr": "पावसासाठी घर तयार ठेवा आणि हवामानाने खराब होणाऱ्या वस्तू आत ठेवा.",
            "as": "বৰষুণৰ বাবে ঘৰ সাজু ৰাখক আৰু বতৰত নষ্ট হোৱা বস্তু ভিতৰত ৰাখক।",
        },
        "wind": {
            "en": "Secure balcony items, close shutters and check anything loose on the roof.",
            "hi": "बालकनी का सामान बाँधें, खिड़कियाँ बंद करें और छत पर ढीली चीज़ें जाँचें।",
            "te": "బాల్కనీ వస్తువులను కట్టండి, కిటికీలు మూసి, పైకప్పుపై వదులుగా ఉన్నవి చూడండి.",
            "bn": "বারান্দার জিনিস বেঁধে রাখুন, জানালা বন্ধ করুন ও ছাদে আলগা কিছু আছে কিনা দেখুন।",
            "mr": "बाल्कनीतील वस्तू बांधा, खिडक्या बंद करा व छतावर सैल काही आहे का पहा.",
            "as": "বাৰাণ্ডাৰ বস্তু বান্ধক, খিৰিকী বন্ধ কৰক আৰু ছাদত ঢিলা কিবা আছে নেকি চাওক।",
        },
        "heat": {
            "en": "Keep the house shaded and ventilated, and move cooking and chores away from the hottest hours.",
            "hi": "घर में छाँव और हवा बनाए रखें, और खाना बनाना व काम सबसे गर्म घंटों से हटाएँ।",
            "te": "ఇంట్లో నీడ, గాలి ఉండేలా చూసి, వంట, పనులను అత్యంత వేడి గంటల నుంచి మార్చండి.",
            "bn": "ঘরে ছায়া ও হাওয়া রাখুন, আর রান্না ও কাজ সবচেয়ে গরম সময় থেকে সরান।",
            "mr": "घरात सावली व हवा ठेवा, आणि स्वयंपाक व कामे सर्वात उष्ण तासांतून हलवा.",
            "as": "ঘৰত ছাঁ আৰু বতাহ ৰাখক, আৰু ৰন্ধা-বঢ়া আৰু কাম আটাইতকৈ গৰম সময়ৰ পৰা আঁতৰাওক।",
        },
        "storm": {
            "en": "Keep everyone indoors and away from windows, and charge phones while the power is on.",
            "hi": "सबको अंदर और खिड़कियों से दूर रखें, और बिजली रहते फ़ोन चार्ज कर लें।",
            "te": "అందరినీ లోపల, కిటికీలకు దూరంగా ఉంచండి; కరెంటు ఉన్నప్పుడే ఫోన్లు చార్జ్ చేయండి.",
            "bn": "সবাইকে ভিতরে ও জানালা থেকে দূরে রাখুন, আর বিদ্যুৎ থাকতেই ফোন চার্জ করুন।",
            "mr": "सर्वांना आत व खिडक्यांपासून दूर ठेवा, आणि वीज असतानाच फोन चार्ज करा.",
            "as": "সকলোকে ভিতৰত আৰু খিৰিকীৰ পৰা আঁতৰত ৰাখক, আৰু বিজুলী থাকোঁতেই ফোন চাৰ্জ কৰক।",
        },
    },
    "traveler": {
        "water": {
            "en": "Allow extra time, expect slower roads, and check conditions again before departure.",
            "hi": "अतिरिक्त समय रखें, सड़कें धीमी मानें, और निकलने से पहले हालात दोबारा देखें।",
            "te": "అదనపు సమయం తీసుకోండి, రోడ్లు నెమ్మదిగా ఉంటాయని ఆశించండి; బయలుదేరే ముందు మళ్లీ చూడండి.",
            "bn": "বাড়তি সময় রাখুন, রাস্তা ধীর ধরে নিন, আর রওনার আগে আবার দেখে নিন।",
            "mr": "जास्त वेळ ठेवा, रस्ते संथ गृहीत धरा, आणि निघण्यापूर्वी पुन्हा पहा.",
            "as": "অতিৰিক্ত সময় ৰাখক, পথ লেহেমীয়া ধৰি লওক, আৰু ৰাওনা হোৱাৰ আগতে পুনৰ চাওক।",
        },
        "wind": {
            "en": "Expect a rougher ride on open stretches and bridges, and secure luggage on the roof.",
            "hi": "खुले रास्तों और पुलों पर झटके की उम्मीद रखें, और छत का सामान कसकर बाँधें।",
            "te": "బహిరంగ మార్గాలు, వంతెనలపై కుదుపులు ఆశించండి; పైన సామాను గట్టిగా కట్టండి.",
            "bn": "খোলা রাস্তা ও সেতুতে ঝাঁকুনির আশা রাখুন, আর ছাদের মালপত্র শক্ত করে বাঁধুন।",
            "mr": "मोकळे रस्ते व पुलांवर हादरे अपेक्षित धरा, आणि छतावरील सामान घट्ट बांधा.",
            "as": "খোলা পথ আৰু দলঙত জোকাৰণিৰ আশা ৰাখক, আৰু ছাদৰ মাল ভালদৰে বান্ধক।",
        },
        "heat": {
            "en": "Travel early or late, carry water, and plan stops in shade rather than in the open.",
            "hi": "जल्दी या देर से चलें, पानी साथ रखें, और रुकने की जगह छाँव में चुनें।",
            "te": "ఉదయమో సాయంత్రమో ప్రయాణించండి, నీరు తీసుకెళ్లండి, ఆగే చోట్లు నీడలో ఎంచుకోండి.",
            "bn": "ভোরে বা দেরিতে যান, জল সঙ্গে নিন, আর থামার জায়গা ছায়ায় বেছে নিন।",
            "mr": "लवकर किंवा उशिरा प्रवास करा, पाणी सोबत ठेवा, आणि थांबे सावलीत निवडा.",
            "as": "ৰাতিপুৱা বা পলমকৈ যাওক, পানী লগত লওক, আৰু ৰ'বলৈ ঠাই ছাঁত বাছি লওক।",
        },
        "storm": {
            "en": "Keep outdoor plans flexible around the storm window and check conditions before departure.",
            "hi": "तूफ़ान की अवधि के आसपास बाहरी योजनाएँ लचीली रखें और निकलने से पहले हालात देखें।",
            "te": "తుఫాను సమయం చుట్టూ బయటి ప్రణాళికలను సడలింపుగా ఉంచి, బయలుదేరే ముందు పరిస్థితి చూడండి.",
            "bn": "ঝড়ের সময়ের আশেপাশে বাইরের পরিকল্পনা নমনীয় রাখুন ও রওনার আগে অবস্থা দেখুন।",
            "mr": "वादळाच्या वेळेभोवती बाहेरचे बेत लवचिक ठेवा आणि निघण्यापूर्वी स्थिती पहा.",
            "as": "ধুমুহাৰ সময়ৰ চাৰিওফালে বাহিৰৰ পৰিকল্পনা নমনীয় ৰাখক আৰু ৰাওনা হোৱাৰ আগতে অৱস্থা চাওক।",
        },
    },
    "farmer": {
        "water": {
            "en": "Drain standing water from fields and move harvested grain and fertiliser to a dry, raised place.",
            "hi": "खेतों से भरा पानी निकालें और कटी हुई फ़सल व खाद को सूखी, ऊँची जगह पर रखें।",
            "te": "పొలాల్లో నిలిచిన నీటిని తీసేయండి, కోసిన ధాన్యం, ఎరువులను పొడి, ఎత్తైన చోట ఉంచండి.",
            "bn": "খেত থেকে জমা জল বের করুন এবং কাটা ফসল ও সার শুকনো, উঁচু জায়গায় সরান।",
            "mr": "शेतातील साचलेले पाणी काढून टाका आणि कापणी केलेले धान्य व खत कोरड्या, उंच जागी ठेवा.",
            "as": "পথাৰৰ জমা পানী উলিয়াই দিয়ক আৰু দাব লোৱা শস্য আৰু সাৰ শুকান, ওখ ঠাইত ৰাখক।",
        },
        "wind": {
            "en": "Stake tall crops, secure the shed roof and move livestock into shelter.",
            "hi": "लंबी फ़सलों को सहारा दें, शेड की छत बाँधें और पशुओं को अंदर ले जाएँ।",
            "te": "ఎత్తైన పంటలకు ఊతం ఇవ్వండి, షెడ్ కప్పును కట్టండి, పశువులను లోపలికి తరలించండి.",
            "bn": "লম্বা ফসলে খুঁটি দিন, গোয়ালঘরের চাল বাঁধুন এবং গবাদি পশু ভিতরে নিন।",
            "mr": "उंच पिकांना आधार द्या, गोठ्याचे छप्पर बांधा आणि जनावरे आत हलवा.",
            "as": "ওখ শস্যত খুঁটা দিয়ক, গোহালিৰ চাল বান্ধক আৰু পশুধন ভিতৰলৈ নিয়ক।",
        },
        "heat": {
            "en": "Irrigate in the early morning or after sunset, and give livestock shade and extra water.",
            "hi": "सुबह जल्दी या सूरज ढलने के बाद सिंचाई करें, पशुओं को छाँव और ज़्यादा पानी दें।",
            "te": "ఉదయం పెందలాడే లేదా సూర్యాస్తమయం తర్వాత నీరు పెట్టండి, పశువులకు నీడ, ఎక్కువ నీరు ఇవ్వండి.",
            "bn": "ভোরে বা সূর্যাস্তের পরে সেচ দিন, গবাদি পশুকে ছায়া ও বেশি জল দিন।",
            "mr": "पहाटे किंवा सूर्यास्तानंतर पाणी द्या, जनावरांना सावली आणि जास्त पाणी द्या.",
            "as": "ৰাতিপুৱা সোনকালে বা সূৰ্য মাৰ যোৱাৰ পিছত পানী দিয়ক, পশুধনক ছাঁ আৰু অধিক পানী দিয়ক।",
        },
        "storm": {
            "en": "Postpone spraying and field work, and keep away from irrigation pumps while there is lightning.",
            "hi": "छिड़काव और खेत का काम टालें, बिजली चमकते समय पंप से दूर रहें।",
            "te": "పిచికారీ, పొలం పనులు వాయిదా వేయండి, పిడుగుల సమయంలో మోటార్ల దగ్గరకు వెళ్లవద్దు.",
            "bn": "স্প্রে ও খেতের কাজ পিছিয়ে দিন, বজ্রপাতের সময় সেচ পাম্প থেকে দূরে থাকুন।",
            "mr": "फवारणी आणि शेतीची कामे पुढे ढकला, वीज चमकत असताना पंपापासून दूर राहा.",
            "as": "স্প্ৰে আৰু পথাৰৰ কাম পিছুৱাই দিয়ক, বজ্ৰপাতৰ সময়ত পাম্পৰ পৰা আঁতৰত থাকক।",
        },
    },
    "marine": {
        "water": {
            "en": "Do not venture out to sea; secure your boat and nets on high ground.",
            "hi": "समुद्र में न जाएँ; नाव और जाल ऊँची जगह पर सुरक्षित बाँधें।",
            "te": "సముద్రంలోకి వెళ్లవద్దు; పడవను, వలలను ఎత్తైన చోట భద్రంగా కట్టండి.",
            "bn": "সমুদ্রে যাবেন না; নৌকা ও জাল উঁচু জায়গায় বেঁধে রাখুন।",
            "mr": "समुद्रात जाऊ नका; होडी आणि जाळी उंच जागी सुरक्षित बांधा.",
            "as": "সাগৰলৈ নাযাব; নাও আৰু জাল ওখ ঠাইত সুৰক্ষিতভাৱে বান্ধি ৰাখক।",
        },
        "wind": {
            "en": "Rough seas are likely — stay ashore and move boats to a sheltered mooring.",
            "hi": "समुद्र में ऊँची लहरें रहेंगी — किनारे पर रहें और नावें सुरक्षित जगह लगाएँ।",
            "te": "సముద్రం అల్లకల్లోలంగా ఉంటుంది — ఒడ్డునే ఉండండి, పడవలను సురక్షిత చోటికి తరలించండి.",
            "bn": "সমুদ্র উত্তাল থাকবে — তীরে থাকুন এবং নৌকা নিরাপদ জায়গায় নোঙর করুন।",
            "mr": "समुद्र खवळलेला राहील — किनाऱ्यावर राहा आणि होड्या सुरक्षित ठिकाणी लावा.",
            "as": "সাগৰ উত্তাল হৈ থাকিব — পাৰত থাকক আৰু নাওবোৰ সুৰক্ষিত ঠাইত ৰাখক।",
        },
        "heat": {
            "en": "Carry extra drinking water and ice, and avoid long midday trips.",
            "hi": "अतिरिक्त पीने का पानी और बर्फ़ साथ रखें, दोपहर की लंबी यात्रा से बचें।",
            "te": "అదనపు తాగునీరు, మంచు తీసుకెళ్లండి, మధ్యాహ్నం సుదీర్ఘ ప్రయాణాలు మానుకోండి.",
            "bn": "বাড়তি খাবার জল ও বরফ সঙ্গে নিন, দুপুরে দীর্ঘ যাত্রা এড়িয়ে চলুন।",
            "mr": "जास्त पिण्याचे पाणी आणि बर्फ सोबत ठेवा, दुपारच्या लांब फेऱ्या टाळा.",
            "as": "অতিৰিক্ত খোৱাপানী আৰু বৰফ লগত লওক, দুপৰীয়া দীঘলীয়া যাত্ৰা এৰাই চলক।",
        },
        "storm": {
            "en": "Return to harbour now and do not put out again until the storm warning is lifted.",
            "hi": "अभी बंदरगाह लौट आएँ और चेतावनी हटने तक दोबारा न निकलें।",
            "te": "వెంటనే రేవుకు తిరిగి రండి, హెచ్చరిక తొలగే వరకు మళ్లీ బయలుదేరవద్దు.",
            "bn": "এখনই বন্দরে ফিরে আসুন এবং সতর্কতা না ওঠা পর্যন্ত আবার বেরোবেন না।",
            "mr": "आत्ताच बंदरात परत या आणि इशारा मागे घेईपर्यंत पुन्हा जाऊ नका.",
            "as": "এতিয়াই বন্দৰলৈ ঘূৰি আহক আৰু সতৰ্কবাণী নুগুচালৈকে পুনৰ নাযাব।",
        },
    },
    "general": {
        "water": {
            "en": "Keep your phone charged and stay updated on local advisories.",
            "hi": "फ़ोन चार्ज रखें और स्थानीय चेतावनियों पर नज़र रखें।",
            "te": "ఫోన్ ఛార్జ్‌లో ఉంచండి, స్థానిక హెచ్చరికలను గమనిస్తూ ఉండండి.",
            "bn": "ফোন চার্জ রাখুন এবং স্থানীয় সতর্কবার্তার খোঁজ রাখুন।",
            "mr": "फोन चार्ज ठेवा आणि स्थानिक सूचनांवर लक्ष ठेवा.",
            "as": "ফোন চাৰ্জ কৰি ৰাখক আৰু স্থানীয় সতৰ্কবাৰ্তাৰ খবৰ ৰাখক।",
        },
        "wind": {
            "en": "Keep windows shut and stay indoors while the wind is strong.",
            "hi": "खिड़कियाँ बंद रखें और तेज़ हवा के दौरान अंदर रहें।",
            "te": "కిటికీలు మూసి ఉంచండి, గాలి బలంగా ఉన్నప్పుడు లోపలే ఉండండి.",
            "bn": "জানালা বন্ধ রাখুন এবং জোরালো বাতাসের সময় ঘরে থাকুন।",
            "mr": "खिडक्या बंद ठेवा आणि जोरदार वाऱ्याच्या वेळी घरात राहा.",
            "as": "খিৰিকী বন্ধ কৰি ৰাখক আৰু প্ৰবল বতাহৰ সময়ত ঘৰতে থাকক।",
        },
        "heat": {
            "en": "Check on children, elderly neighbours and people working outdoors.",
            "hi": "बच्चों, बुज़ुर्ग पड़ोसियों और बाहर काम करने वालों का ध्यान रखें।",
            "te": "పిల్లలు, వృద్ధులు, బయట పనిచేసేవారి క్షేమం చూసుకోండి.",
            "bn": "শিশু, বয়স্ক প্রতিবেশী ও বাইরে কাজ করা মানুষের খোঁজ নিন।",
            "mr": "मुले, वृद्ध शेजारी आणि बाहेर काम करणाऱ्यांची काळजी घ्या.",
            "as": "শিশু, বৃদ্ধ চুবুৰীয়া আৰু বাহিৰত কাম কৰা লোকৰ খবৰ লওক।",
        },
        "storm": {
            "en": "Stay indoors and away from windows until the thunderstorm passes.",
            "hi": "तूफ़ान गुज़रने तक अंदर और खिड़कियों से दूर रहें।",
            "te": "తుఫాను వెళ్లే వరకు లోపల, కిటికీలకు దూరంగా ఉండండి.",
            "bn": "বজ্রঝড় না থামা পর্যন্ত ঘরে ও জানালা থেকে দূরে থাকুন।",
            "mr": "वादळ जाईपर्यंत घरात आणि खिडक्यांपासून दूर राहा.",
            "as": "বজ্ৰ-ধুমুহা নোযোৱালৈকে ঘৰত আৰু খিৰিকীৰ পৰা আঁতৰত থাকক।",
        },
    },
    # --- The five profiles added for the nine-role selector ----------------
    # Written, not aliased: a household reader and a driver do not take the
    # same action in the same storm, and pointing both at the commuter text
    # would put a role label on advice that was not about them.
    "driver": {
        "water": {
            "en": "Slow down, use low beams and do not drive into flooded stretches — the depth is impossible to judge.",
            "hi": "गति कम करें, लो-बीम जलाएँ और पानी भरे हिस्सों में गाड़ी न उतारें — गहराई का अंदाज़ा नहीं लगता।",
            "te": "వేగం తగ్గించండి, లో-బీమ్ లైట్లు వాడండి, నీరు నిలిచిన చోట వాహనం దించవద్దు — లోతు అంచనా వేయలేరు.",
            "bn": "গতি কমান, লো-বিম ব্যবহার করুন এবং জল জমা অংশে গাড়ি নামাবেন না — গভীরতা বোঝা যায় না।",
            "mr": "वेग कमी करा, लो-बीम वापरा आणि पाणी साचलेल्या भागात गाडी घालू नका — खोलीचा अंदाज येत नाही.",
            "as": "গতি কমাওক, ল'-বীম ব্যৱহাৰ কৰক আৰু পানী জমা অংশত গাড়ী নমাব নালাগে — গভীৰতা বুজিব নোৱাৰি।",
        },
        "wind": {
            "en": "Hold the wheel firmly on open bridges and flyovers, and give high-sided vehicles extra room.",
            "hi": "खुले पुलों और फ़्लाईओवर पर स्टीयरिंग मज़बूती से पकड़ें और ऊँचे वाहनों से दूरी रखें।",
            "te": "బహిరంగ వంతెనలు, ఫ్లైఓవర్లపై స్టీరింగ్ గట్టిగా పట్టుకోండి, ఎత్తైన వాహనాలకు దూరం ఉంచండి.",
            "bn": "খোলা সেতু ও উড়ালপুলে স্টিয়ারিং শক্ত করে ধরুন এবং উঁচু গাড়ি থেকে দূরত্ব রাখুন।",
            "mr": "मोकळ्या पुलांवर व उड्डाणपुलांवर स्टिअरिंग घट्ट धरा आणि उंच वाहनांपासून अंतर ठेवा.",
            "as": "মুকলি দলং আৰু উৰাসেতুত ষ্টিয়েৰিং টানকৈ ধৰক আৰু ওখ বাহনৰ পৰা দূৰত্ব ৰাখক।",
        },
        "heat": {
            "en": "Check tyre pressure and coolant before a long run, and keep drinking water in the cabin.",
            "hi": "लंबी यात्रा से पहले टायर प्रेशर और कूलेंट जाँचें, और केबिन में पीने का पानी रखें।",
            "te": "దూర ప్రయాణానికి ముందు టైర్ ప్రెషర్, కూలెంట్ చూసుకోండి, క్యాబిన్‌లో తాగునీరు ఉంచండి.",
            "bn": "দূরপাল্লার আগে টায়ারের চাপ ও কুল্যান্ট দেখে নিন, কেবিনে পানীয় জল রাখুন।",
            "mr": "लांबच्या प्रवासाआधी टायर प्रेशर व कूलंट तपासा आणि केबिनमध्ये पिण्याचे पाणी ठेवा.",
            "as": "দূৰৈৰ যাত্ৰাৰ আগতে টায়াৰ প্ৰেচাৰ আৰু কুলেণ্ট চাই লওক, কেবিনত খোৱাপানী ৰাখক।",
        },
        "storm": {
            "en": "Pull over somewhere safe and wait the lightning out rather than driving through it.",
            "hi": "किसी सुरक्षित जगह गाड़ी रोकें और बिजली थमने तक रुकें, बीच में चलाते न रहें।",
            "te": "సురక్షితమైన చోట వాహనం ఆపి పిడుగులు ఆగే వరకు వేచి ఉండండి, నడుపుతూ వెళ్లవద్దు.",
            "bn": "নিরাপদ জায়গায় গাড়ি থামিয়ে বজ্রপাত না থামা পর্যন্ত অপেক্ষা করুন, চালিয়ে যাবেন না।",
            "mr": "सुरक्षित ठिकाणी गाडी थांबवा आणि वीज थांबेपर्यंत थांबा, चालवत राहू नका.",
            "as": "নিৰাপদ ঠাইত গাড়ী ৰখাই বজ্ৰপাত নাথমালৈকে অপেক্ষা কৰক, চলাই নাথাকিব।",
        },
    },
    "outdoor_worker": {
        "water": {
            "en": "Move tools and materials to higher ground and stay out of trenches that can fill quickly.",
            "hi": "औज़ार और सामान ऊँची जगह पर रखें और जल्दी भरने वाली खाइयों में न उतरें।",
            "te": "పనిముట్లు, సామగ్రిని ఎత్తైన చోటికి తరలించండి, త్వరగా నీరు నిండే గుంతల్లోకి దిగవద్దు.",
            "bn": "যন্ত্রপাতি ও মালপত্র উঁচু জায়গায় সরান এবং দ্রুত জল ভরে এমন খাদে নামবেন না।",
            "mr": "अवजारे व साहित्य उंच जागी हलवा आणि पटकन भरणाऱ्या चरांमध्ये उतरू नका.",
            "as": "সঁজুলি আৰু সামগ্ৰী ওখ ঠাইলৈ নিয়ক আৰু সোনকালে পানী ভৰা গাঁতত নামিব নালাগে।",
        },
        "wind": {
            "en": "Stop work on scaffolding and ladders, and tie down loose sheets and boards.",
            "hi": "मचान और सीढ़ी पर काम रोकें, और खुली चादरें व तख़्ते बाँध दें।",
            "te": "పరంజా, నిచ్చెనలపై పని ఆపండి, వదులుగా ఉన్న షీట్లు, పలకలు కట్టేయండి.",
            "bn": "ভারা ও মইয়ের উপর কাজ বন্ধ করুন, আলগা টিন ও তক্তা বেঁধে রাখুন।",
            "mr": "मचाण व शिडीवरील काम थांबवा आणि सुटे पत्रे व फळ्या बांधून ठेवा.",
            "as": "মাচ আৰু জখলাৰ ওপৰৰ কাম বন্ধ কৰক, আৰু ঢিলা টিন আৰু তক্তা বান্ধি থওক।",
        },
        "heat": {
            "en": "Shift heavy work to the early morning, rest in shade and drink water every twenty minutes.",
            "hi": "भारी काम सुबह जल्दी करें, छाया में आराम लें और हर बीस मिनट में पानी पिएँ।",
            "te": "బరువైన పని ఉదయాన్నే చేయండి, నీడలో విశ్రాంతి తీసుకోండి, ప్రతి ఇరవై నిమిషాలకు నీరు తాగండి.",
            "bn": "ভারী কাজ ভোরে সেরে নিন, ছায়ায় বিশ্রাম নিন এবং প্রতি কুড়ি মিনিটে জল খান।",
            "mr": "जड काम पहाटे उरका, सावलीत विश्रांती घ्या आणि दर वीस मिनिटांनी पाणी प्या.",
            "as": "গধুৰ কাম ৰাতিপুৱাই সাৰক, ছাঁত জিৰণি লওক আৰু প্ৰতি বিশ মিনিটত পানী খাওক।",
        },
        "storm": {
            "en": "Stop work and move away from cranes, scaffolding and open ground until the lightning passes.",
            "hi": "काम रोकें और बिजली थमने तक क्रेन, मचान और खुले मैदान से दूर हट जाएँ।",
            "te": "పని ఆపి, పిడుగులు ఆగే వరకు క్రేన్లు, పరంజా, ఖాళీ మైదానం నుండి దూరంగా వెళ్లండి.",
            "bn": "কাজ থামান এবং বজ্রপাত না থামা পর্যন্ত ক্রেন, ভারা ও খোলা মাঠ থেকে সরে যান।",
            "mr": "काम थांबवा आणि वीज थांबेपर्यंत क्रेन, मचाण व मोकळ्या मैदानापासून दूर जा.",
            "as": "কাম বন্ধ কৰক আৰু বজ্ৰপাত নাথমালৈকে ক্ৰেইন, মাচ আৰু মুকলি পথাৰৰ পৰা আঁতৰি যাওক।",
        },
    },
    "student": {
        "water": {
            "en": "Leave earlier than usual and do not wade through flooded roads on the way.",
            "hi": "सामान्य से जल्दी निकलें और रास्ते में भरी हुई सड़कों से होकर न गुज़रें।",
            "te": "మామూలు కంటే ముందే బయలుదేరండి, దారిలో నీరు నిలిచిన రోడ్లలో నడవవద్దు.",
            "bn": "রোজকার চেয়ে আগে বেরোন এবং পথে জল জমা রাস্তায় নামবেন না।",
            "mr": "नेहमीपेक्षा लवकर निघा आणि वाटेत पाणी साचलेल्या रस्त्यांतून जाऊ नका.",
            "as": "সদায়তকৈ সোনকালে ওলাওক আৰু বাটত পানী জমা ৰাস্তাৰে নাযাব।",
        },
        "wind": {
            "en": "A cycle or two-wheeler is unsteady in gusts today; take the bus if you can.",
            "hi": "आज झोंकों में साइकिल या दोपहिया डगमगाएगा; हो सके तो बस लें।",
            "te": "ఈరోజు గాలుల్లో సైకిల్, ద్విచక్ర వాహనం నిలకడగా ఉండదు; వీలైతే బస్సు వాడండి.",
            "bn": "আজ দমকা বাতাসে সাইকেল বা দুই চাকার যান টলমল করবে; পারলে বাসে যান।",
            "mr": "आज झोतांमध्ये सायकल किंवा दुचाकी डगमगेल; शक्य असल्यास बसने जा.",
            "as": "আজি দমকা বতাহত চাইকেল বা দুচকীয়া বাহন লৰচৰ কৰিব; পাৰিলে বাছত যাওক।",
        },
        "heat": {
            "en": "Carry water, keep out of the midday sun and leave outdoor games for the evening.",
            "hi": "पानी साथ रखें, दोपहर की धूप से बचें और बाहरी खेल शाम के लिए रखें।",
            "te": "నీరు తీసుకెళ్లండి, మధ్యాహ్న ఎండ తప్పించుకోండి, బయటి ఆటలు సాయంత్రానికి వాయిదా వేయండి.",
            "bn": "জল সঙ্গে নিন, দুপুরের রোদ এড়ান এবং বাইরের খেলা সন্ধ্যার জন্য রাখুন।",
            "mr": "पाणी सोबत ठेवा, दुपारचे ऊन टाळा आणि बाहेरचे खेळ संध्याकाळसाठी ठेवा.",
            "as": "পানী লগত লওক, দুপৰীয়াৰ ৰ'দ এৰাওক আৰু বাহিৰৰ খেল সন্ধিয়াৰ বাবে ৰাখক।",
        },
        "storm": {
            "en": "Wait indoors at school or campus until the lightning stops rather than starting out.",
            "hi": "स्कूल या कैंपस के अंदर ही रुकें और बिजली थमने तक निकलें नहीं।",
            "te": "పాఠశాల లేదా క్యాంపస్ లోపలే ఉండి, పిడుగులు ఆగే వరకు బయలుదేరవద్దు.",
            "bn": "স্কুল বা ক্যাম্পাসের ভিতরেই থাকুন, বজ্রপাত না থামা পর্যন্ত রওনা দেবেন না।",
            "mr": "शाळेत किंवा कॅम्पसमध्येच थांबा, वीज थांबेपर्यंत निघू नका.",
            "as": "স্কুল বা কেম্পাছৰ ভিতৰতে থাকক, বজ্ৰপাত নাথমালৈকে ওলাব নালাগে।",
        },
    },
    "caregiver": {
        "water": {
            "en": "Check on anyone who cannot move quickly, and keep medicines dry and within reach.",
            "hi": "जो जल्दी हिल-डुल नहीं सकते उनका हाल लें, और दवाइयाँ सूखी और पास रखें।",
            "te": "త్వరగా కదల్లేని వారిని చూసుకోండి, మందులు తడవకుండా చేతికి అందేలా ఉంచండి.",
            "bn": "যাঁরা দ্রুত নড়াচড়া করতে পারেন না তাঁদের খোঁজ নিন, ওষুধ শুকনো ও হাতের কাছে রাখুন।",
            "mr": "पटकन हालचाल न करू शकणाऱ्यांची विचारपूस करा आणि औषधे कोरडी व जवळ ठेवा.",
            "as": "সোনকালে লৰচৰ কৰিব নোৱাৰাসকলৰ খবৰ লওক, আৰু ঔষধ শুকান আৰু ওচৰত ৰাখক।",
        },
        "wind": {
            "en": "Keep children and older people away from windows, loose roofing and trees.",
            "hi": "बच्चों और बुज़ुर्गों को खिड़कियों, ढीली छत और पेड़ों से दूर रखें।",
            "te": "పిల్లలను, వృద్ధులను కిటికీలు, వదులుగా ఉన్న పైకప్పు, చెట్ల నుండి దూరంగా ఉంచండి.",
            "bn": "শিশু ও বয়স্কদের জানালা, আলগা ছাদ ও গাছ থেকে দূরে রাখুন।",
            "mr": "मुलांना व वृद्धांना खिडक्या, सुटलेले छप्पर व झाडांपासून दूर ठेवा.",
            "as": "শিশু আৰু বৃদ্ধসকলক খিৰিকী, ঢিলা চাল আৰু গছৰ পৰা আঁতৰত ৰাখক।",
        },
        "heat": {
            "en": "Check on elderly neighbours through the afternoon and keep fluids going for the children.",
            "hi": "दोपहर भर बुज़ुर्ग पड़ोसियों का हाल लेते रहें और बच्चों को पानी पिलाते रहें।",
            "te": "మధ్యాహ్నమంతా వృద్ధ పొరుగువారిని చూస్తూ ఉండండి, పిల్లలకు నీరు ఇస్తూ ఉండండి.",
            "bn": "দুপুরভর বয়স্ক প্রতিবেশীদের খোঁজ নিন এবং শিশুদের জল খাওয়াতে থাকুন।",
            "mr": "दुपारभर वृद्ध शेजाऱ्यांची विचारपूस करत राहा आणि मुलांना पाणी पाजत राहा.",
            "as": "দুপৰীয়া ভৰি বৃদ্ধ চুবুৰীয়াসকলৰ খবৰ লৈ থাকক আৰু শিশুসকলক পানী খুৱাই থাকক।",
        },
        "storm": {
            "en": "Move everyone indoors early — the people you look after need more time than you do.",
            "hi": "सबको पहले ही अंदर ले आएँ — जिनकी आप देखभाल करते हैं उन्हें आपसे ज़्यादा समय लगता है।",
            "te": "అందరినీ ముందుగానే లోపలికి తీసుకురండి — మీరు చూసుకునేవారికి మీకంటే ఎక్కువ సమయం పడుతుంది.",
            "bn": "সবাইকে আগেভাগে ঘরে আনুন — যাঁদের দেখাশোনা করেন তাঁদের আপনার চেয়ে বেশি সময় লাগে।",
            "mr": "सर्वांना आधीच आत घ्या — तुम्ही ज्यांची काळजी घेता त्यांना तुमच्यापेक्षा जास्त वेळ लागतो.",
            "as": "সকলোকে আগতীয়াকৈ ভিতৰলৈ আনক — আপুনি চোৱা-চিতা কৰাসকলৰ আপোনাতকৈ বেছি সময় লাগে।",
        },
    },
}

# --- Risk drivers: rendered from the engine's structured output ------------
DRIVERS: dict[str, dict[str, str]] = {
    "en": {
        "rain_24h": "{value} mm of rain expected over the next 24 hours",
        "rain_rate": "rain falling at {value} mm per hour",
        "precip_72h": "{value} mm of rain accumulating over three days",
        "sustained_hours": "{value} hours of continuous rain in the next 24 hours",
        "gusts": "wind gusts up to {value} km/h",
        "sustained_wind": "sustained wind of {value} km/h",
        "feels_like": "it feels like {value}°C",
        "thunderstorm": "thunderstorm conditions reported",
        "cape": "an unstable atmosphere",
    },
    "hi": {
        "rain_24h": "अगले 24 घंटों में {value} मिमी बारिश का अनुमान",
        "rain_rate": "{value} मिमी प्रति घंटा की दर से बारिश",
        "precip_72h": "तीन दिनों में {value} मिमी बारिश जमा हो रही है",
        "sustained_hours": "अगले 24 घंटों में {value} घंटे लगातार बारिश",
        "gusts": "{value} किमी/घंटा तक के हवा के झोंके",
        "sustained_wind": "{value} किमी/घंटा की लगातार हवा",
        "feels_like": "{value}°C जैसा महसूस हो रहा है",
        "thunderstorm": "गरज के साथ तूफ़ान की स्थिति",
        "cape": "वातावरण अस्थिर है",
    },
    "te": {
        "rain_24h": "వచ్చే 24 గంటల్లో {value} మి.మీ. వర్షం అంచనా",
        "rain_rate": "గంటకు {value} మి.మీ. వేగంతో వర్షం",
        "precip_72h": "మూడు రోజుల్లో {value} మి.మీ. వర్షం పోగవుతోంది",
        "sustained_hours": "వచ్చే 24 గంటల్లో {value} గంటలు ఎడతెరిపి లేని వర్షం",
        "gusts": "{value} కి.మీ./గంట వరకు గాలి తాకిడి",
        "sustained_wind": "{value} కి.మీ./గంట నిరంతర గాలి",
        "feels_like": "{value}°C లా అనిపిస్తోంది",
        "thunderstorm": "ఉరుములతో కూడిన తుఫాను పరిస్థితి",
        "cape": "వాతావరణం అస్థిరంగా ఉంది",
    },
    "bn": {
        "rain_24h": "আগামী 24 ঘণ্টায় {value} মিমি বৃষ্টির পূর্বাভাস",
        "rain_rate": "ঘণ্টায় {value} মিমি হারে বৃষ্টি",
        "precip_72h": "তিন দিনে {value} মিমি বৃষ্টি জমছে",
        "sustained_hours": "আগামী 24 ঘণ্টায় {value} ঘণ্টা টানা বৃষ্টি",
        "gusts": "{value} কিমি/ঘণ্টা পর্যন্ত দমকা হাওয়া",
        "sustained_wind": "{value} কিমি/ঘণ্টা একটানা বাতাস",
        "feels_like": "{value}°C-এর মতো অনুভূত হচ্ছে",
        "thunderstorm": "বজ্রঝড়ের পরিস্থিতি",
        "cape": "বায়ুমণ্ডল অস্থির",
    },
    "mr": {
        "rain_24h": "पुढच्या 24 तासांत {value} मिमी पावसाचा अंदाज",
        "rain_rate": "ताशी {value} मिमी वेगाने पाऊस",
        "precip_72h": "तीन दिवसांत {value} मिमी पाऊस साचत आहे",
        "sustained_hours": "पुढच्या 24 तासांत {value} तास सलग पाऊस",
        "gusts": "{value} किमी/तास पर्यंतचे वाऱ्याचे झोत",
        "sustained_wind": "{value} किमी/तास सततचा वारा",
        "feels_like": "{value}°C सारखे जाणवत आहे",
        "thunderstorm": "गडगडाटी वादळाची स्थिती",
        "cape": "वातावरण अस्थिर आहे",
    },
    "as": {
        "rain_24h": "অহা 24 ঘণ্টাত {value} মি.মি. বৰষুণৰ পূৰ্বাভাস",
        "rain_rate": "ঘণ্টাত {value} মি.মি. হাৰত বৰষুণ",
        "precip_72h": "তিনি দিনত {value} মি.মি. বৰষুণ জমা হৈ আছে",
        "sustained_hours": "অহা 24 ঘণ্টাত {value} ঘণ্টা একেৰাহে বৰষুণ",
        "gusts": "{value} কি.মি./ঘণ্টালৈকে বতাহৰ ধপ",
        "sustained_wind": "{value} কি.মি./ঘণ্টা একেৰাহে বতাহ",
        "feels_like": "{value}°C ৰ দৰে অনুভৱ হৈছে",
        "thunderstorm": "বজ্ৰ-ধুমুহাৰ পৰিস্থিতি",
        "cape": "বায়ুমণ্ডল অস্থিৰ",
    },
}

# --- Relative day names, so forecasts never fall back to English weekdays ---
DAYS: dict[str, dict[str, str]] = {
    "en": {"d0": "today", "d1": "tomorrow", "d2": "the day after tomorrow", "dn": "in {value} days"},
    "hi": {"d0": "आज", "d1": "कल", "d2": "परसों", "dn": "{value} दिन बाद"},
    "te": {"d0": "ఈరోజు", "d1": "రేపు", "d2": "ఎల్లుండి", "dn": "{value} రోజుల తర్వాత"},
    "bn": {"d0": "আজ", "d1": "আগামীকাল", "d2": "পরশু", "dn": "{value} দিন পরে"},
    "mr": {"d0": "आज", "d1": "उद्या", "d2": "परवा", "dn": "{value} दिवसांनी"},
    "as": {"d0": "আজি", "d1": "কাইলৈ", "d2": "পৰহিলৈ", "dn": "{value} দিনৰ পিছত"},
}


# Sentence terminator: Devanagari/Bengali/Assamese use the danda, not a period.
TERMINATORS: dict[str, str] = {"en": ".", "te": ".", "mr": ".", "hi": "।", "bn": "।", "as": "।"}


IMPACT_CATEGORIES: dict[str, dict[str, str]] = {
    "en": {"everyday": "Everyday weather", "farming": "Farming", "fishing": "Fishing", "travel": "Travel",
           "household": "Household", "outdoor": "Outdoor activity"},
    "hi": {"everyday": "रोज़ का मौसम", "farming": "खेती", "fishing": "मछली पकड़ना", "travel": "यात्रा",
           "household": "घर-गृहस्थी", "outdoor": "बाहरी गतिविधि"},
    "te": {"everyday": "రోజువారీ వాతావరణం", "farming": "వ్యవసాయం", "fishing": "చేపల వేట", "travel": "ప్రయాణం",
           "household": "ఇంటి పనులు", "outdoor": "బయటి కార్యకలాపాలు"},
    "bn": {"everyday": "দৈনন্দিন আবহাওয়া", "farming": "কৃষিকাজ", "fishing": "মাছ ধরা", "travel": "যাত্রা",
           "household": "ঘরের কাজ", "outdoor": "বাইরের কাজকর্ম"},
    "mr": {"everyday": "रोजचे हवामान", "farming": "शेती", "fishing": "मासेमारी", "travel": "प्रवास",
           "household": "घरकाम", "outdoor": "बाहेरील हालचाल"},
    "as": {"everyday": "দৈনন্দিন বতৰ", "farming": "কৃষি", "fishing": "মাছ ধৰা", "travel": "যাত্ৰা",
           "household": "ঘৰুৱা কাম", "outdoor": "বাহিৰৰ কাম"},
}

IMPACT_STATUS: dict[str, dict[str, str]] = {
    "en": {"Safe": "Safe", "Caution": "Caution", "Avoid": "Avoid"},
    "hi": {"Safe": "सुरक्षित", "Caution": "सावधानी", "Avoid": "टालें"},
    "te": {"Safe": "సురక్షితం", "Caution": "జాగ్రత్త", "Avoid": "వద్దు"},
    "bn": {"Safe": "নিরাপদ", "Caution": "সতর্কতা", "Avoid": "এড়ান"},
    "mr": {"Safe": "सुरक्षित", "Caution": "सावधगिरी", "Avoid": "टाळा"},
    "as": {"Safe": "নিৰাপদ", "Caution": "সাৱধান", "Avoid": "এৰাওক"},
}


# ---------------------------------------------------------------------------
# Accessors — every lookup falls back to English rather than raising.
# ---------------------------------------------------------------------------
def normalise_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    code = lang.strip().lower().replace("_", "-").split("-")[0]
    return code if code in LANGUAGES else DEFAULT_LANG


def sentence(key: str, lang: str, **kwargs: Any) -> str:
    lang = normalise_lang(lang)
    template = SENTENCES.get(lang, {}).get(key) or SENTENCES[DEFAULT_LANG].get(key, "")
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def condition_label(weather_code: int | None, lang: str) -> str:
    lang = normalise_lang(lang)
    bucket = _BUCKETS.get(int(weather_code), "unknown") if weather_code is not None else "unknown"
    table = CONDITIONS.get(lang, CONDITIONS[DEFAULT_LANG])
    return table.get(bucket) or CONDITIONS[DEFAULT_LANG].get(bucket, "mixed conditions")


def hazard_label(hazard: str, lang: str) -> str:
    lang = normalise_lang(lang)
    return HAZARD_NAMES.get(lang, {}).get(hazard) or HAZARD_NAMES[DEFAULT_LANG].get(hazard, hazard)


def level_label(level: str, lang: str) -> str:
    lang = normalise_lang(lang)
    return RISK_LEVELS.get(lang, {}).get(level) or level


def status_label(status: str, lang: str) -> str:
    lang = normalise_lang(lang)
    return IMPACT_STATUS.get(lang, {}).get(status) or status


def category_label(category: str, lang: str) -> str:
    lang = normalise_lang(lang)
    return IMPACT_CATEGORIES.get(lang, {}).get(category) or category


def canonical_profile(user_type: str | None) -> str:
    """Whose hazard-action line to use.

    Resolved through the role registry, which is the single place a retired
    profile's substitute is written down — so the line a reader is given here
    comes from the same reading their cards and their metric order came from.
    The membership check is belt and braces: every role the registry knows has
    an entry in the tables below, and a role added without one would fall back
    to the general line rather than raise.
    """
    from . import roles

    profile = roles.get(user_type).key
    return profile if profile in PROFILE_ACTIONS else "general"


def hazard_actions(hazard: str, lang: str) -> list[str]:
    lang = normalise_lang(lang)
    table = HAZARD_ACTIONS.get(hazard)
    if not table:
        return []
    return list(table.get(lang) or table[DEFAULT_LANG])


def profile_action(user_type: str | None, hazard: str, lang: str) -> str | None:
    lang = normalise_lang(lang)
    family = HAZARD_FAMILY.get(hazard)
    if not family:
        return None
    profile = canonical_profile(user_type)
    entry = PROFILE_ACTIONS.get(profile, {}).get(family)
    if not entry:
        return None
    return entry.get(lang) or entry.get(DEFAULT_LANG)


def driver_label(detail: dict[str, Any], lang: str) -> str:
    """Render one structured risk driver in the requested language."""
    lang = normalise_lang(lang)
    code = str(detail.get("code", ""))
    table = DRIVERS.get(lang, DRIVERS[DEFAULT_LANG])
    template = table.get(code) or DRIVERS[DEFAULT_LANG].get(code)
    if not template:
        return ""
    value = detail.get("value")
    if isinstance(value, float):
        value = round(value, 1)
        if value == int(value):
            value = int(value)
    try:
        return template.format(value=value)
    except (KeyError, IndexError):
        return template


def driver_labels(details: list[dict[str, Any]], lang: str) -> list[str]:
    return [text for text in (driver_label(d, lang) for d in details or []) if text]


def day_label(offset: int, lang: str) -> str:
    """Relative day name ('day after tomorrow'), localised."""
    lang = normalise_lang(lang)
    table = DAYS.get(lang, DAYS[DEFAULT_LANG])
    key = f"d{offset}" if offset in (0, 1, 2) else "dn"
    template = table.get(key) or DAYS[DEFAULT_LANG][key]
    try:
        return template.format(value=offset)
    except (KeyError, IndexError):
        return template


def terminator(lang: str) -> str:
    return TERMINATORS.get(normalise_lang(lang), ".")


# ---------------------------------------------------------------------------
# Insight and per-sector sentences.
#
# Added as a separate block and merged in, so the six-language tables above stay
# readable. Same rule as everything else here: fixed templates with numeric
# slots, so the offline path can be multilingual without being able to invent a
# value.
# ---------------------------------------------------------------------------
_EXTRA_SENTENCES: dict[str, dict[str, str]] = {
    "en": {
        "insight_factor_rain": "rain",
        "insight_factor_wind": "wind",
        "insight_factor_visibility": "visibility",
        "insight_factor_heat": "heat",
        "insight_factor_hazard": "hazard indicators",
        "advisory_generic": "Stay indoors where you can, keep your phone charged, and follow local advisories.",
        "insight_rain_from": "Rain becomes likely from around {time}, at about {prob}%.",
        "insight_rain_clear": "Rain is unlikely over the next {hours} hours.",
        "insight_window_until": "Outdoor work is best finished before about {time}.",
        "insight_wind_later": "Wind strengthens to about {wind} km/h later.",
        "insight_visibility_low": "Visibility is low, around {vis} km.",
        "insight_safe_now": "Outdoor activity is generally safe right now.",
        "insight_hazard_active": "{hazard} is the main hazard here, currently {level}.",
        "insight_small_boat": "Wind of about {wind} km/h makes small-boat conditions difficult.",
        "impact_farming_clear": "No significant rain expected — a usable window for field work.",
        "impact_farming_rain": "Finish field work early and keep harvested grain covered.",
        "impact_fishing_calm": "Wind is light at about {wind} km/h.",
        "impact_travel_clear": "Visibility is good and no major rain is expected.",
        "impact_travel_rain": "Rain may slow traffic and reduce visibility.",
        "impact_household_calm": "Nothing indoors needs attention right now.",
        "impact_household_risk": "Secure loose outdoor items and keep drains clear.",
        "impact_outdoor_clear": "Conditions suit outdoor activity for the next few hours.",
        "impact_outdoor_risk": "Outdoor plans are better postponed for now.",
    },
    "hi": {
        "insight_factor_rain": "बारिश",
        "insight_factor_wind": "हवा",
        "insight_factor_visibility": "दृश्यता",
        "insight_factor_heat": "गर्मी",
        "insight_factor_hazard": "ख़तरे के संकेत",
        "advisory_generic": "जहाँ तक हो सके घर के अंदर रहें, फ़ोन चार्ज रखें और स्थानीय चेतावनियों का पालन करें।",
        "insight_rain_from": "लगभग {time} से बारिश की संभावना बढ़ती है, करीब {prob}%।",
        "insight_rain_clear": "अगले {hours} घंटों में बारिश की संभावना कम है।",
        "insight_window_until": "बाहर का काम लगभग {time} से पहले पूरा कर लें।",
        "insight_wind_later": "आगे हवा बढ़कर लगभग {wind} किमी/घंटा हो जाएगी।",
        "insight_visibility_low": "दृश्यता कम है, लगभग {vis} किमी।",
        "insight_safe_now": "अभी बाहर की गतिविधि आम तौर पर सुरक्षित है।",
        "insight_hazard_active": "यहाँ मुख्य ख़तरा {hazard} है, फ़िलहाल {level}।",
        "insight_small_boat": "लगभग {wind} किमी/घंटा की हवा में छोटी नावों के लिए हालात मुश्किल हैं।",
        "impact_farming_clear": "बड़ी बारिश का अनुमान नहीं — खेत के काम के लिए ठीक समय है।",
        "impact_farming_rain": "खेत का काम जल्दी निपटाएँ और कटी फ़सल ढककर रखें।",
        "impact_fishing_calm": "हवा हल्की है, लगभग {wind} किमी/घंटा।",
        "impact_travel_clear": "दृश्यता अच्छी है और बड़ी बारिश का अनुमान नहीं है।",
        "impact_travel_rain": "बारिश से यातायात धीमा और दृश्यता कम हो सकती है।",
        "impact_household_calm": "अभी घर के अंदर कुछ करने की ज़रूरत नहीं है।",
        "impact_household_risk": "बाहर रखी चीज़ें बाँधें और नालियाँ साफ़ रखें।",
        "impact_outdoor_clear": "अगले कुछ घंटे बाहरी गतिविधि के लिए ठीक हैं।",
        "impact_outdoor_risk": "बाहर की योजनाएँ अभी टाल देना बेहतर है।",
    },
    "te": {
        "insight_factor_rain": "వర్షం",
        "insight_factor_wind": "గాలి",
        "insight_factor_visibility": "దృశ్యమానత",
        "insight_factor_heat": "వేడి",
        "insight_factor_hazard": "ముప్పు సూచనలు",
        "advisory_generic": "వీలైనంత వరకు ఇంట్లోనే ఉండండి, ఫోన్ ఛార్జ్‌లో ఉంచండి, స్థానిక హెచ్చరికలు పాటించండి.",
        "insight_rain_from": "సుమారు {time} నుండి వర్షం పడే అవకాశం పెరుగుతుంది, దాదాపు {prob}%.",
        "insight_rain_clear": "వచ్చే {hours} గంటల్లో వర్షం పడే అవకాశం తక్కువ.",
        "insight_window_until": "బయటి పనులు సుమారు {time} లోపు పూర్తి చేసుకోవడం మంచిది.",
        "insight_wind_later": "తర్వాత గాలి సుమారు {wind} కి.మీ./గంటకు పెరుగుతుంది.",
        "insight_visibility_low": "దృశ్యమానత తక్కువగా ఉంది, సుమారు {vis} కి.మీ.",
        "insight_safe_now": "ప్రస్తుతం బయటి కార్యకలాపాలు సాధారణంగా సురక్షితం.",
        "insight_hazard_active": "ఇక్కడ ప్రధాన ముప్పు {hazard}, ప్రస్తుతం {level}.",
        "insight_small_boat": "సుమారు {wind} కి.మీ./గంట గాలిలో చిన్న పడవలకు పరిస్థితి కష్టం.",
        "impact_farming_clear": "పెద్ద వర్షం అంచనా లేదు — పొలం పనులకు అనుకూల సమయం.",
        "impact_farming_rain": "పొలం పనులు త్వరగా ముగించి, కోసిన ధాన్యాన్ని కప్పి ఉంచండి.",
        "impact_fishing_calm": "గాలి తేలికగా ఉంది, సుమారు {wind} కి.మీ./గంట.",
        "impact_travel_clear": "దృశ్యమానత బాగుంది, పెద్ద వర్షం అంచనా లేదు.",
        "impact_travel_rain": "వర్షం వల్ల ట్రాఫిక్ నెమ్మదించి, దృశ్యమానత తగ్గవచ్చు.",
        "impact_household_calm": "ప్రస్తుతం ఇంట్లో ప్రత్యేకంగా చేయాల్సింది ఏమీ లేదు.",
        "impact_household_risk": "బయట ఉన్న వస్తువులను కట్టి, కాలువలు శుభ్రంగా ఉంచండి.",
        "impact_outdoor_clear": "వచ్చే కొన్ని గంటలు బయటి కార్యకలాపాలకు అనుకూలం.",
        "impact_outdoor_risk": "బయటి ప్రణాళికలు ప్రస్తుతానికి వాయిదా వేయడం మేలు.",
    },
    "bn": {
        "insight_factor_rain": "বৃষ্টি",
        "insight_factor_wind": "বাতাস",
        "insight_factor_visibility": "দৃশ্যমানতা",
        "insight_factor_heat": "গরম",
        "insight_factor_hazard": "ঝুঁকির লক্ষণ",
        "advisory_generic": "যতটা সম্ভব ঘরে থাকুন, ফোন চার্জ রাখুন এবং স্থানীয় সতর্কবার্তা মেনে চলুন।",
        "insight_rain_from": "প্রায় {time} থেকে বৃষ্টির সম্ভাবনা বাড়ে, প্রায় {prob}%।",
        "insight_rain_clear": "আগামী {hours} ঘণ্টায় বৃষ্টির সম্ভাবনা কম।",
        "insight_window_until": "বাইরের কাজ প্রায় {time}-এর আগে সেরে ফেলা ভালো।",
        "insight_wind_later": "পরে বাতাস বেড়ে প্রায় {wind} কিমি/ঘণ্টা হবে।",
        "insight_visibility_low": "দৃশ্যমানতা কম, প্রায় {vis} কিমি।",
        "insight_safe_now": "এখন বাইরের কাজকর্ম সাধারণভাবে নিরাপদ।",
        "insight_hazard_active": "এখানে প্রধান ঝুঁকি {hazard}, বর্তমানে {level}।",
        "insight_small_boat": "প্রায় {wind} কিমি/ঘণ্টা বাতাসে ছোট নৌকার পক্ষে অবস্থা কঠিন।",
        "impact_farming_clear": "বড় বৃষ্টির পূর্বাভাস নেই — খেতের কাজের জন্য ভালো সময়।",
        "impact_farming_rain": "খেতের কাজ তাড়াতাড়ি সেরে কাটা ফসল ঢেকে রাখুন।",
        "impact_fishing_calm": "বাতাস হালকা, প্রায় {wind} কিমি/ঘণ্টা।",
        "impact_travel_clear": "দৃশ্যমানতা ভালো এবং বড় বৃষ্টির পূর্বাভাস নেই।",
        "impact_travel_rain": "বৃষ্টিতে যান চলাচল ধীর ও দৃশ্যমানতা কম হতে পারে।",
        "impact_household_calm": "এখন ঘরের ভিতরে বিশেষ কিছু করার নেই।",
        "impact_household_risk": "বাইরের জিনিস বেঁধে রাখুন ও নর্দমা পরিষ্কার রাখুন।",
        "impact_outdoor_clear": "আগামী কয়েক ঘণ্টা বাইরের কাজকর্মের জন্য উপযুক্ত।",
        "impact_outdoor_risk": "বাইরের পরিকল্পনা আপাতত স্থগিত রাখাই ভালো।",
    },
    "mr": {
        "insight_factor_rain": "पाऊस",
        "insight_factor_wind": "वारा",
        "insight_factor_visibility": "दृश्यमानता",
        "insight_factor_heat": "उष्णता",
        "insight_factor_hazard": "धोक्याचे संकेत",
        "advisory_generic": "शक्य तितके घरात राहा, फोन चार्ज ठेवा आणि स्थानिक सूचनांचे पालन करा.",
        "insight_rain_from": "सुमारे {time} पासून पावसाची शक्यता वाढते, अंदाजे {prob}%.",
        "insight_rain_clear": "पुढच्या {hours} तासांत पावसाची शक्यता कमी आहे.",
        "insight_window_until": "बाहेरचे काम सुमारे {time} च्या आधी पूर्ण करणे चांगले.",
        "insight_wind_later": "नंतर वारा वाढून सुमारे {wind} किमी/तास होईल.",
        "insight_visibility_low": "दृश्यमानता कमी आहे, सुमारे {vis} किमी.",
        "insight_safe_now": "सध्या बाहेरील हालचाल सर्वसाधारणपणे सुरक्षित आहे.",
        "insight_hazard_active": "इथे मुख्य धोका {hazard} आहे, सध्या {level}.",
        "insight_small_boat": "सुमारे {wind} किमी/तास वाऱ्यात लहान होड्यांसाठी परिस्थिती कठीण आहे.",
        "impact_farming_clear": "मोठ्या पावसाचा अंदाज नाही — शेतीच्या कामासाठी योग्य वेळ.",
        "impact_farming_rain": "शेतीचे काम लवकर आटपा आणि कापणी केलेले धान्य झाकून ठेवा.",
        "impact_fishing_calm": "वारा हलका आहे, सुमारे {wind} किमी/तास.",
        "impact_travel_clear": "दृश्यमानता चांगली आहे आणि मोठ्या पावसाचा अंदाज नाही.",
        "impact_travel_rain": "पावसामुळे वाहतूक मंदावू शकते व दृश्यमानता कमी होऊ शकते.",
        "impact_household_calm": "सध्या घरात विशेष काही करण्याची गरज नाही.",
        "impact_household_risk": "बाहेरील वस्तू बांधा आणि नाले स्वच्छ ठेवा.",
        "impact_outdoor_clear": "पुढचे काही तास बाहेरील हालचालीसाठी योग्य आहेत.",
        "impact_outdoor_risk": "बाहेरील बेत सध्या पुढे ढकलणे बरे.",
    },
    "as": {
        "insight_factor_rain": "বৰষুণ",
        "insight_factor_wind": "বতাহ",
        "insight_factor_visibility": "দৃশ্যমানতা",
        "insight_factor_heat": "গৰম",
        "insight_factor_hazard": "বিপদৰ লক্ষণ",
        "advisory_generic": "যিমান পাৰি ঘৰত থাকক, ফোন চাৰ্জ কৰি ৰাখক আৰু স্থানীয় সতৰ্কবাৰ্তা মানি চলক।",
        "insight_rain_from": "প্ৰায় {time} ৰ পৰা বৰষুণৰ সম্ভাৱনা বাঢ়ে, প্ৰায় {prob}%।",
        "insight_rain_clear": "অহা {hours} ঘণ্টাত বৰষুণৰ সম্ভাৱনা কম।",
        "insight_window_until": "বাহিৰৰ কাম প্ৰায় {time} ৰ আগতে শেষ কৰাই ভাল।",
        "insight_wind_later": "পিছত বতাহ বাঢ়ি প্ৰায় {wind} কি.মি./ঘণ্টা হ'ব।",
        "insight_visibility_low": "দৃশ্যমানতা কম, প্ৰায় {vis} কি.মি.।",
        "insight_safe_now": "এতিয়া বাহিৰৰ কাম সাধাৰণতে নিৰাপদ।",
        "insight_hazard_active": "ইয়াত মুখ্য বিপদ {hazard}, বৰ্তমানে {level}।",
        "insight_small_boat": "প্ৰায় {wind} কি.মি./ঘণ্টা বতাহত সৰু নাওৰ বাবে পৰিস্থিতি কঠিন।",
        "impact_farming_clear": "ডাঙৰ বৰষুণৰ পূৰ্বাভাস নাই — পথাৰৰ কামৰ বাবে ভাল সময়।",
        "impact_farming_rain": "পথাৰৰ কাম সোনকালে শেষ কৰক আৰু দাব লোৱা শস্য ঢাকি ৰাখক।",
        "impact_fishing_calm": "বতাহ পাতল, প্ৰায় {wind} কি.মি./ঘণ্টা।",
        "impact_travel_clear": "দৃশ্যমানতা ভাল আৰু ডাঙৰ বৰষুণৰ পূৰ্বাভাস নাই।",
        "impact_travel_rain": "বৰষুণৰ বাবে যান চলাচল লেহেম আৰু দৃশ্যমানতা কম হ'ব পাৰে।",
        "impact_household_calm": "এতিয়া ঘৰৰ ভিতৰত বিশেষ একো কৰিবলগীয়া নাই।",
        "impact_household_risk": "বাহিৰৰ বস্তু বান্ধি ৰাখক আৰু নলা পৰিষ্কাৰ ৰাখক।",
        "impact_outdoor_clear": "অহা কেইঘণ্টামান বাহিৰৰ কামৰ বাবে উপযুক্ত।",
        "impact_outdoor_risk": "বাহিৰৰ পৰিকল্পনা আপাততঃ পিছুৱাই দিয়াই ভাল।",
    },
}

for _lang, _table in _EXTRA_SENTENCES.items():
    SENTENCES.setdefault(_lang, {}).update(_table)

# Role-intelligence wording lives in its own module purely for readability —
# it merges into the same table and is read through the same `sentence()`.
from ._role_sentences import ROLE_SENTENCES as _ROLE_SENTENCES  # noqa: E402

for _lang, _table in _ROLE_SENTENCES.items():
    SENTENCES.setdefault(_lang, {}).update(_table)


# ---------------------------------------------------------------------------
# Why an action matters.
#
# Carried only on the persona-specific lead action: that is the one a reader is
# most likely to act on, and attaching a reason to all 35 actions would treble
# the translated corpus without adding much. Reasons state a consequence a
# non-specialist can verify — they never assert agronomic, medical or maritime
# expertise the weather data cannot support.
# ---------------------------------------------------------------------------
PROFILE_REASONS: dict[str, dict[str, dict[str, str]]] = {
    "aviation": {
        "water": {
            "en": "Precipitation cuts visibility and changes surface conditions, and this app is not an aviation weather source.",
            "hi": "बारिश दृश्यता घटाती है और सतह की स्थिति बदलती है, और यह ऐप विमानन मौसम का स्रोत नहीं है।",
            "te": "వర్షం దృశ్యతను తగ్గించి ఉపరితల స్థితిని మారుస్తుంది, ఈ యాప్ విమానయాన వాతావరణ మూలం కాదు.",
            "bn": "বৃষ্টি দৃশ্যমানতা কমায় ও পৃষ্ঠের অবস্থা বদলায়, আর এই অ্যাপ বিমান আবহাওয়ার উৎস নয়।",
            "mr": "पाऊस दृश्यमानता घटवतो व पृष्ठस्थिती बदलतो, आणि हे ॲप विमान हवामानाचा स्रोत नाही.",
            "as": "বৰষুণে দৃশ্যমানতা কমায় আৰু পৃষ্ঠৰ অৱস্থা সলনি কৰে, আৰু এই এপ বিমান বতৰৰ উৎস নহয়।",
        },
        "wind": {
            "en": "Gusts and crosswind are what decide a runway, and the limits belong to the aircraft rather than to the forecast.",
            "hi": "रनवे झोंकों और क्रॉसविंड से तय होता है, और सीमाएँ विमान की होती हैं, पूर्वानुमान की नहीं।",
            "te": "రన్‌వేను ఈదురుగాలులు, క్రాస్‌విండ్ నిర్ణయిస్తాయి; పరిమితులు అంచనావి కాదు, విమానానివి.",
            "bn": "রানওয়ে ঠিক করে দমকা ও ক্রসউইন্ড, আর সীমা পূর্বাভাসের নয়, বিমানের।",
            "mr": "धावपट्टी झोत व क्रॉसविंडने ठरते, आणि मर्यादा अंदाजाच्या नव्हे तर विमानाच्या असतात.",
            "as": "ৰাণৱে নিৰ্ধাৰণ কৰে দমকা আৰু ক্ৰছৱিণ্ডে, আৰু সীমা পূৰ্বাভাসৰ নহয়, বিমানৰ।",
        },
        "heat": {
            "en": "Air is thinner when it is hot, and the ground crew are working in the same heat.",
            "hi": "गर्मी में हवा पतली होती है, और ज़मीनी दल उसी गर्मी में काम कर रहा है।",
            "te": "వేడిగా ఉన్నప్పుడు గాలి పలచగా ఉంటుంది, గ్రౌండ్ సిబ్బంది అదే వేడిలో పని చేస్తారు.",
            "bn": "গরমে বাতাস পাতলা হয়, আর গ্রাউন্ড ক্রু সেই গরমেই কাজ করে।",
            "mr": "उष्णतेत हवा विरळ होते, आणि भूकर्मचारी त्याच उष्णतेत काम करतात.",
            "as": "গৰমত বতাহ পাতল হয়, আৰু গ্ৰাউণ্ড ক্ৰুৱে সেই গৰমতে কাম কৰে।",
        },
        "storm": {
            "en": "Convection moves fast and this reading is a public forecast, not an aviation product.",
            "hi": "गरज-तूफ़ान तेज़ी से बदलता है और यह आकलन आम पूर्वानुमान है, विमानन उत्पाद नहीं।",
            "te": "ఉరుములు వేగంగా కదులుతాయి, ఇది సాధారణ అంచనా, విమానయాన ఉత్పత్తి కాదు.",
            "bn": "বজ্রঝড় দ্রুত সরে, আর এই পাঠ সাধারণ পূর্বাভাস, বিমান পণ্য নয়।",
            "mr": "गडगडाट झपाट्याने सरकतो आणि हे वाचन सार्वजनिक अंदाज आहे, विमान उत्पादन नाही.",
            "as": "ধুমুহা সোনকালে লৰচৰ কৰে আৰু এই পঢ়া সাধাৰণ পূৰ্বাভাস, বিমান সামগ্ৰী নহয়।",
        },
    },
    "disaster": {
        "water": {
            "en": "Flood response turns on accumulation and terrain, and this app carries no official warning feed.",
            "hi": "बाढ़ की कार्रवाई जमाव और भू-बनावट पर निर्भर है, और इस ऐप में सरकारी चेतावनी का फ़ीड नहीं है।",
            "te": "వరద స్పందన పోగు, భూస్వరూపంపై ఆధారపడుతుంది; ఈ యాప్‌లో అధికారిక హెచ్చరిక ఫీడ్ లేదు.",
            "bn": "বন্যার সাড়া নির্ভর করে জমা ও ভূ-গঠনের উপর, আর এই অ্যাপে সরকারি সতর্কতার ফিড নেই।",
            "mr": "पूर प्रतिसाद साठवण व भूरचनेवर अवलंबून असतो, आणि या ॲपमध्ये अधिकृत इशाऱ्यांचा फीड नाही.",
            "as": "বানপানীৰ সঁহাৰি জমা আৰু ভূ-গঠনৰ ওপৰত নিৰ্ভৰ কৰে, আৰু এই এপত চৰকাৰী সতৰ্কবাণীৰ ফিড নাই।",
        },
        "wind": {
            "en": "Wind damage arrives before the rain does, and it lands on the lightest structures first.",
            "hi": "हवा का नुक़सान बारिश से पहले आता है, और सबसे हल्के ढाँचों पर पहले पड़ता है।",
            "te": "గాలి నష్టం వర్షానికి ముందే వస్తుంది, తేలికపాటి నిర్మాణాలపై ముందుగా పడుతుంది.",
            "bn": "বাতাসের ক্ষতি বৃষ্টির আগে আসে, আর সবচেয়ে হালকা কাঠামোয় আগে পড়ে।",
            "mr": "वाऱ्याचे नुकसान पावसाआधी येते, आणि सर्वात हलक्या बांधकामांवर आधी होते.",
            "as": "বতাহৰ ক্ষতি বৰষুণৰ আগতে আহে, আৰু আটাইতকৈ পাতল গাঁথনিত আগতে পৰে।",
        },
        "heat": {
            "en": "Heat kills quietly, and the people at risk are the ones least likely to call for help.",
            "hi": "गर्मी चुपचाप जान लेती है, और जो सबसे ज़्यादा ख़तरे में हैं वही मदद सबसे कम माँगते हैं।",
            "te": "వేడి నిశ్శబ్దంగా ప్రాణాలు తీస్తుంది, ఎక్కువ ప్రమాదంలో ఉన్నవారే సహాయం అడగరు.",
            "bn": "গরম নীরবে প্রাণ নেয়, আর যারা সবচেয়ে ঝুঁকিতে তারাই কম সাহায্য চায়।",
            "mr": "उष्णता शांतपणे जीव घेते, आणि सर्वाधिक धोक्यात असलेलेच मदत मागत नाहीत.",
            "as": "গৰমে নিমাতে প্ৰাণ লয়, আৰু যিসকল আটাইতকৈ বিপদত তেওঁলোকেই সহায় কম বিচাৰে।",
        },
        "storm": {
            "en": "Activating early costs resources; activating late costs more, so the escalation curve is the decision.",
            "hi": "जल्दी सक्रिय करना संसाधन खर्च करता है, देर से करना उससे ज़्यादा — इसलिए बढ़ोतरी का रुझान ही निर्णय है।",
            "te": "ముందుగా సక్రియం చేస్తే వనరులు ఖర్చు, ఆలస్యమైతే మరింత — కాబట్టి పెరుగుదల వక్రరేఖే నిర్ణయం.",
            "bn": "তাড়াতাড়ি সক্রিয় করলে সম্পদ খরচ, দেরিতে করলে আরও বেশি — তাই বৃদ্ধির বাঁকই সিদ্ধান্ত।",
            "mr": "लवकर सक्रिय केल्यास साधने खर्च होतात, उशिरा केल्यास अधिक — म्हणून वाढीचा कल हाच निर्णय.",
            "as": "সোনকালে সক্ৰিয় কৰিলে সম্পদ খৰচ, পলমকৈ কৰিলে অধিক — সেয়েহে বৃদ্ধিৰ ধাৰাই সিদ্ধান্ত।",
        },
    },
    "smart_city": {
        "water": {
            "en": "A city floods where the drains are already full, not where the most rain falls.",
            "hi": "शहर वहाँ डूबता है जहाँ नालियाँ पहले से भरी हैं, वहाँ नहीं जहाँ सबसे ज़्यादा बारिश होती है।",
            "te": "నగరం ఎక్కువ వర్షం పడే చోట కాదు, కాలువలు ఇప్పటికే నిండిన చోట మునుగుతుంది.",
            "bn": "শহর ডোবে যেখানে নর্দমা আগেই ভরা, যেখানে বেশি বৃষ্টি সেখানে নয়।",
            "mr": "शहर तिथे बुडते जिथे गटारे आधीच भरलेली आहेत, जिथे सर्वाधिक पाऊस पडतो तिथे नव्हे.",
            "as": "নগৰ তাত ডুবে য'ত নলা আগতেই ভৰা, য'ত বেছি বৰষুণ তাত নহয়।",
        },
        "wind": {
            "en": "Wind finds whatever a city has bolted on, and drops it into the traffic below.",
            "hi": "हवा शहर की जोड़ी गई चीज़ों को ढूँढ़ती है, और नीचे यातायात में गिरा देती है।",
            "te": "నగరం అమర్చిన వస్తువులను గాలి పట్టుకుని కింద ట్రాఫిక్‌లో పడేస్తుంది.",
            "bn": "বাতাস শহরের লাগানো জিনিস খুঁজে নেয়, আর নিচে যানবাহনে ফেলে।",
            "mr": "वारा शहराने जोडलेल्या वस्तू शोधतो, आणि खाली वाहतुकीत टाकतो.",
            "as": "বতাহে নগৰে লগোৱা বস্তু বিচাৰি উলিয়ায়, আৰু তলৰ যান-জঁটত পেলায়।",
        },
        "heat": {
            "en": "A hot city draws its worst load at the same hour every utility is already stretched.",
            "hi": "गर्म शहर पर सबसे बड़ा भार उसी घड़ी पड़ता है जब हर सेवा पहले से तनी हुई है।",
            "te": "వేడి నగరంలో అత్యధిక భారం, ప్రతి సేవ ఇప్పటికే ఒత్తిడిలో ఉన్న అదే గంటలో వస్తుంది.",
            "bn": "গরম শহরে সবচেয়ে বড় চাপ পড়ে সেই ঘণ্টায় যখন প্রতিটি পরিষেবা এমনিতেই টানটান।",
            "mr": "उष्ण शहरावर सर्वात मोठा भार त्याच वेळी येतो जेव्हा प्रत्येक सेवा आधीच ताणलेली असते.",
            "as": "গৰম নগৰত আটাইতকৈ ডাঙৰ ভাৰ সেই ঘণ্টাতে পৰে যেতিয়া প্ৰতিটো সেৱা আগতেই টান।",
        },
        "storm": {
            "en": "A storm reaches a city as three failures at once: water, power and movement.",
            "hi": "तूफ़ान शहर तक एक साथ तीन ख़राबियों के रूप में पहुँचता है — पानी, बिजली और आवाजाही।",
            "te": "తుఫాను నగరానికి ఒకేసారి మూడు వైఫల్యాలుగా చేరుతుంది: నీరు, విద్యుత్, రాకపోకలు.",
            "bn": "ঝড় শহরে পৌঁছায় একসঙ্গে তিন বিপর্যয় হয়ে: জল, বিদ্যুৎ ও চলাচল।",
            "mr": "वादळ शहरात एकाच वेळी तीन बिघाड घेऊन येते: पाणी, वीज व वाहतूक.",
            "as": "ধুমুহাই নগৰত একেলগে তিনিটা বিফলতা হৈ পায়: পানী, বিজুলী আৰু চলাচল।",
        },
    },
    "researcher": {
        "water": {
            "en": "One observation is a point; the archive is what turns it into a signal.",
            "hi": "एक अवलोकन बिंदु भर है; अभिलेख ही उसे संकेत बनाता है।",
            "te": "ఒక పరిశీలన ఒక బిందువు; ఆర్కైవే దాన్ని సంకేతంగా మారుస్తుంది.",
            "bn": "একটি পর্যবেক্ষণ কেবল বিন্দু; আর্কাইভই তাকে সংকেত করে।",
            "mr": "एक निरीक्षण म्हणजे केवळ बिंदू; संग्रहच त्याला संकेत बनवतो.",
            "as": "এটা পৰ্যবেক্ষণ এটা বিন্দুহে; আৰ্কাইভেহে তাক সংকেত কৰে।",
        },
        "wind": {
            "en": "A gust and a mean are different measurements, and mixing them is how a series stops meaning anything.",
            "hi": "झोंका और औसत अलग माप हैं, और उन्हें मिलाने से शृंखला का अर्थ ख़त्म हो जाता है।",
            "te": "ఈదురుగాలి, సగటు వేర్వేరు కొలతలు; వాటిని కలపడం వల్ల శ్రేణికి అర్థం పోతుంది.",
            "bn": "দমকা ও গড় আলাদা মাপ, এদের মিশিয়ে দিলে সিরিজের অর্থ থাকে না।",
            "mr": "झोत व सरासरी वेगळी मापे आहेत, ती मिसळल्यास मालिकेचा अर्थ उरत नाही.",
            "as": "দমকা আৰু গড় পৃথক জোখ, সেইবোৰ মিহলালে শৃংখলাৰ অৰ্থ নাথাকে।",
        },
        "heat": {
            "en": "Hot is a feeling; anomalous is a number, and only one of them belongs in a finding.",
            "hi": "गर्म एक एहसास है; विचलन एक संख्या — निष्कर्ष में इनमें से एक ही आता है।",
            "te": "వేడి అనేది అనుభూతి; వ్యత్యాసం అనేది సంఖ్య — ఫలితంలో ఒకటే ఉంటుంది.",
            "bn": "গরম একটি অনুভূতি; ব্যতিক্রম একটি সংখ্যা — সিদ্ধান্তে একটিই থাকে।",
            "mr": "उष्ण ही जाणीव आहे; विचलन हा आकडा — निष्कर्षात यातील एकच येतो.",
            "as": "গৰম এটা অনুভৱ; ব্যতিক্ৰম এটা সংখ্যা — সিদ্ধান্তত এটাহে থাকে।",
        },
        "storm": {
            "en": "Convective detail is the first thing a forecast series loses when it is re-aggregated.",
            "hi": "पुनः-संकलन में पूर्वानुमान शृंखला सबसे पहले गरज-तूफ़ान का ब्यौरा खोती है।",
            "te": "తిరిగి సమీకరించినప్పుడు అంచనా శ్రేణి మొదట కోల్పోయేది ఉరుముల వివరమే.",
            "bn": "পুনঃসমষ্টি করলে পূর্বাভাস সিরিজ সবার আগে বজ্রঝড়ের বিবরণ হারায়।",
            "mr": "पुन्हा एकत्रित केल्यास अंदाज मालिका सर्वात आधी गडगडाटाचा तपशील गमावते.",
            "as": "পুনৰ একত্ৰিত কৰিলে পূৰ্বাভাস শৃংখলাই আটাইতকৈ আগতে ধুমুহাৰ বিৱৰণ হেৰুৱায়।",
        },
    },
    "household": {
        "water": {
            "en": "Laundry, stored grain and anything on a balcony are what a wet day actually costs a home.",
            "hi": "गीले दिन का असल नुक़सान घर में कपड़े, रखा अनाज और बालकनी की चीज़ों पर होता है।",
            "te": "తడి రోజు ఇంటికి నిజంగా ఖర్చు పెట్టేది బట్టలు, నిల్వ ధాన్యం, బాల్కనీలోని వస్తువులే.",
            "bn": "ভেজা দিনে ঘরের আসল ক্ষতি হয় কাপড়, মজুত শস্য আর বারান্দার জিনিসে।",
            "mr": "ओल्या दिवशी घराचे खरे नुकसान कपडे, साठवलेले धान्य व बाल्कनीतील वस्तूंचे होते.",
            "as": "তিতা দিনত ঘৰৰ প্ৰকৃত ক্ষতি হয় কাপোৰ, ৰখা শস্য আৰু বাৰাণ্ডাৰ বস্তুত।",
        },
        "wind": {
            "en": "Most wind damage at home starts with something that was never tied down.",
            "hi": "घर में हवा का ज़्यादातर नुक़सान उसी चीज़ से शुरू होता है जो कभी बाँधी ही नहीं गई।",
            "te": "ఇంట్లో గాలి నష్టం చాలావరకు ఎప్పుడూ కట్టని వస్తువుతోనే మొదలవుతుంది.",
            "bn": "ঘরে বাতাসের বেশিরভাগ ক্ষতি শুরু হয় এমন জিনিস দিয়ে যা কখনও বাঁধা হয়নি।",
            "mr": "घरात वाऱ्याचे बहुतांश नुकसान कधीच न बांधलेल्या वस्तूपासून सुरू होते.",
            "as": "ঘৰত বতাহৰ বেছিভাগ ক্ষতি কেতিয়াও নবন্ধা বস্তুৰ পৰাই আৰম্ভ হয়।",
        },
        "heat": {
            "en": "A kitchen adds its own heat, and indoors is only cooler if the air is moving.",
            "hi": "रसोई अपनी गर्मी जोड़ती है, और अंदर तभी ठंडा है जब हवा चल रही हो।",
            "te": "వంటిల్లు తన వేడిని కలుపుతుంది, గాలి కదిలితేనే లోపల చల్లగా ఉంటుంది.",
            "bn": "রান্নাঘর নিজের গরম যোগ করে, আর হাওয়া চললে তবেই ভিতরে ঠান্ডা।",
            "mr": "स्वयंपाकघर स्वतःची उष्णता जोडते, आणि हवा वाहत असेल तरच आत थंड असते.",
            "as": "পাকঘৰে নিজৰ গৰম যোগ কৰে, আৰু বতাহ চলিলেহে ভিতৰত চেঁচা।",
        },
        "storm": {
            "en": "Power goes first in a storm, and a charged phone is how a household stays reachable.",
            "hi": "तूफ़ान में बिजली पहले जाती है, और चार्ज फ़ोन से ही घर संपर्क में रहता है।",
            "te": "తుఫానులో ముందుగా కరెంటు పోతుంది, చార్జ్ చేసిన ఫోనే ఇంటిని అందుబాటులో ఉంచుతుంది.",
            "bn": "ঝড়ে আগে বিদ্যুৎ যায়, আর চার্জ করা ফোনেই ঘর নাগালে থাকে।",
            "mr": "वादळात वीज आधी जाते, आणि चार्ज केलेल्या फोनमुळेच घर संपर्कात राहते.",
            "as": "ধুমুহাত বিজুলী আগতে যায়, আৰু চাৰ্জ কৰা ফোনেৰেহে ঘৰ যোগাযোগত থাকে।",
        },
    },
    "traveler": {
        "water": {
            "en": "Rain rarely cancels a journey; it just makes every part of it take longer.",
            "hi": "बारिश सफ़र शायद ही रद्द करती है; बस हर हिस्से में ज़्यादा समय लगाती है।",
            "te": "వర్షం ప్రయాణాన్ని రద్దు చేయదు; ప్రతి భాగానికీ ఎక్కువ సమయం పట్టేలా చేస్తుంది.",
            "bn": "বৃষ্টি যাত্রা বাতিল করে না; শুধু প্রতিটি অংশে বেশি সময় নেয়।",
            "mr": "पाऊस प्रवास क्वचितच रद्द करतो; फक्त प्रत्येक टप्पा जास्त वेळ घेतो.",
            "as": "বৰষুণে যাত্ৰা বাতিল নকৰে; কেৱল প্ৰতিটো অংশত অধিক সময় লয়।",
        },
        "wind": {
            "en": "Crosswind is worst exactly where a road has nothing beside it to break the gust.",
            "hi": "क्रॉसविंड वहीं सबसे तेज़ है जहाँ सड़क के पास हवा रोकने को कुछ नहीं।",
            "te": "గాలిని ఆపేది ఏమీ లేని చోటే క్రాస్‌విండ్ అత్యధికం.",
            "bn": "ক্রসউইন্ড সেখানেই সবচেয়ে বেশি যেখানে রাস্তার পাশে বাতাস আটকানোর কিছু নেই।",
            "mr": "क्रॉसविंड तिथेच सर्वात तीव्र असतो जिथे रस्त्याशेजारी वारा अडवायला काही नसते.",
            "as": "ক্ৰছৱিণ্ড তাতেই আটাইতকৈ বেছি য'ত পথৰ কাষত বতাহ ৰোধ কৰিবলৈ একো নাই।",
        },
        "heat": {
            "en": "A parked vehicle in the sun gets hotter than the air, and so does anyone waiting in it.",
            "hi": "धूप में खड़ी गाड़ी हवा से ज़्यादा गर्म होती है, और उसमें बैठा व्यक्ति भी।",
            "te": "ఎండలో ఆపిన వాహనం గాలి కంటే వేడెక్కుతుంది, అందులో వేచి ఉన్నవారూ అంతే.",
            "bn": "রোদে দাঁড়ানো গাড়ি বাতাসের চেয়ে বেশি গরম হয়, আর তাতে বসে থাকা মানুষও।",
            "mr": "उन्हात उभी गाडी हवेपेक्षा जास्त तापते, आणि तिच्यात बसलेला माणूसही.",
            "as": "ৰ'দত ৰখা গাড়ী বতাহতকৈ বেছি গৰম হয়, আৰু তাত বহি থকা মানুহো।",
        },
        "storm": {
            "en": "A storm is a window rather than a day, and a trip planned around it usually still happens.",
            "hi": "तूफ़ान पूरा दिन नहीं, एक अवधि है — उसके आसपास बनाई योजना अक्सर चल जाती है।",
            "te": "తుఫాను ఒక రోజు కాదు, ఒక సమయం; దాని చుట్టూ ప్రణాళిక వేస్తే ప్రయాణం సాధారణంగా జరుగుతుంది.",
            "bn": "ঝড় একটি সময়, গোটা দিন নয় — তার আশেপাশে সাজানো যাত্রা সাধারণত হয়ে যায়।",
            "mr": "वादळ म्हणजे संपूर्ण दिवस नव्हे तर एक कालावधी — त्याभोवती आखलेला प्रवास बहुधा होतोच.",
            "as": "ধুমুহা এটা সময়, গোটেই দিন নহয় — তাৰ চাৰিওফালে সজা যাত্ৰা সাধাৰণতে হয়।",
        },
    },
    "farmer": {
        "water": {
            "en": "Rain washes chemicals off before they are absorbed, and standing water spoils stored grain.",
            "hi": "बारिश छिड़काव को सोखने से पहले बहा देती है, और भरा पानी रखी फ़सल ख़राब करता है।",
            "te": "వర్షం పిచికారీ చేసినది పీల్చుకునేలోపే కొట్టుకుపోతుంది, నిలిచిన నీరు నిల్వ ధాన్యాన్ని పాడు చేస్తుంది.",
            "bn": "বৃষ্টি শোষণের আগেই রাসায়নিক ধুয়ে দেয়, আর জমা জল মজুত শস্য নষ্ট করে।",
            "mr": "पाऊस फवारणी शोषली जाण्याआधीच वाहून नेतो, आणि साचलेले पाणी साठवलेले धान्य खराब करते.",
            "as": "বৰষুণে শোষণ হোৱাৰ আগতেই ৰাসায়নিক ধুই নিয়ে, আৰু জমা পানীয়ে ৰখা শস্য নষ্ট কৰে।",
        },
        "wind": {
            "en": "Tall crops fall over in strong wind, and loose roofing becomes dangerous.",
            "hi": "तेज़ हवा में लंबी फ़सल गिर जाती है, और खुली छत की चादरें ख़तरनाक हो जाती हैं।",
            "te": "బలమైన గాలిలో ఎత్తైన పంటలు పడిపోతాయి, వదులుగా ఉన్న రేకులు ప్రమాదకరం అవుతాయి.",
            "bn": "জোরালো বাতাসে লম্বা ফসল পড়ে যায়, আর আলগা চাল বিপজ্জনক হয়ে ওঠে।",
            "mr": "जोरदार वाऱ्यात उंच पिके कोलमडतात, आणि सैल पत्रे धोकादायक ठरतात.",
            "as": "প্ৰবল বতাহত ওখ শস্য পৰি যায়, আৰু ঢিলা চাল বিপজ্জনক হৈ পৰে।",
        },
        "heat": {
            "en": "Midday water evaporates before it reaches the roots, and livestock suffer in the heat.",
            "hi": "दोपहर का पानी जड़ों तक पहुँचने से पहले भाप बन जाता है, और गर्मी में पशु परेशान होते हैं।",
            "te": "మధ్యాహ్నం పెట్టిన నీరు వేర్లకు చేరకముందే ఆవిరైపోతుంది, వేడిలో పశువులు ఇబ్బంది పడతాయి.",
            "bn": "দুপুরের জল শিকড়ে পৌঁছানোর আগেই বাষ্প হয়ে যায়, আর গরমে গবাদি পশু কষ্ট পায়।",
            "mr": "दुपारचे पाणी मुळांपर्यंत पोहोचण्याआधीच वाफ होते, आणि उष्णतेत जनावरे त्रस्त होतात.",
            "as": "দুপৰীয়াৰ পানী শিপালৈ পোৱাৰ আগতেই বাষ্প হৈ যায়, আৰু গৰমত পশুধনে কষ্ট পায়।",
        },
        "storm": {
            "en": "Open fields and metal equipment are exposed places during lightning.",
            "hi": "बिजली गिरने के दौरान खुले खेत और धातु के उपकरण असुरक्षित जगह हैं।",
            "te": "పిడుగుల సమయంలో ఖాళీ పొలాలు, లోహపు పరికరాలు ప్రమాదకర ప్రదేశాలు.",
            "bn": "বজ্রপাতের সময় খোলা মাঠ ও ধাতব যন্ত্রপাতি অরক্ষিত জায়গা।",
            "mr": "वीज पडताना मोकळी शेते आणि धातूची अवजारे असुरक्षित ठिकाणे असतात.",
            "as": "বজ্ৰপাতৰ সময়ত খোলা পথাৰ আৰু ধাতুৰ সঁজুলি অৰক্ষিত ঠাই।",
        },
    },
    "marine": {
        "water": {
            "en": "Boats and nets left at the waterline are lost when the level rises.",
            "hi": "पानी के किनारे छोड़ी नाव और जाल जलस्तर बढ़ने पर बह जाते हैं।",
            "te": "నీటి అంచున ఉంచిన పడవలు, వలలు నీటిమట్టం పెరిగితే కొట్టుకుపోతాయి.",
            "bn": "জলের ধারে রাখা নৌকা ও জাল জলস্তর বাড়লে ভেসে যায়।",
            "mr": "पाण्याच्या काठावर ठेवलेल्या होड्या व जाळी पातळी वाढल्यास वाहून जातात.",
            "as": "পানীৰ কাষত থোৱা নাও আৰু জাল পানীৰ স্তৰ বাঢ়িলে উটি যায়।",
        },
        "wind": {
            "en": "Small boats become unstable in strong wind and rough water.",
            "hi": "तेज़ हवा और ऊँची लहरों में छोटी नावें अस्थिर हो जाती हैं।",
            "te": "బలమైన గాలి, అల్లకల్లోల నీటిలో చిన్న పడవలు అస్థిరంగా మారతాయి.",
            "bn": "জোরালো বাতাস ও উত্তাল জলে ছোট নৌকা টাল সামলাতে পারে না।",
            "mr": "जोरदार वारा व खवळलेल्या पाण्यात लहान होड्या अस्थिर होतात.",
            "as": "প্ৰবল বতাহ আৰু উত্তাল পানীত সৰু নাও অস্থিৰ হৈ পৰে।",
        },
        "heat": {
            "en": "A long trip without shade or drinking water risks heat exhaustion.",
            "hi": "छाँव और पीने के पानी के बिना लंबी यात्रा में लू लगने का ख़तरा है।",
            "te": "నీడ, తాగునీరు లేకుండా సుదీర్ఘ ప్రయాణం వడదెబ్బ ప్రమాదం తెస్తుంది.",
            "bn": "ছায়া ও খাবার জল ছাড়া দীর্ঘ যাত্রায় হিটস্ট্রোকের ঝুঁকি থাকে।",
            "mr": "सावली व पिण्याच्या पाण्याविना लांब फेरीत उष्माघाताचा धोका असतो.",
            "as": "ছাঁ আৰু খোৱাপানী নোহোৱাকৈ দীঘলীয়া যাত্ৰাত তাপাঘাতৰ আশংকা থাকে।",
        },
        "storm": {
            "en": "Open water offers no shelter from lightning.",
            "hi": "खुले पानी में बिजली से बचने की कोई जगह नहीं होती।",
            "te": "బహిరంగ నీటిపై పిడుగుల నుండి రక్షణ ఉండదు.",
            "bn": "খোলা জলে বজ্রপাত থেকে আড়াল নেওয়ার জায়গা নেই।",
            "mr": "मोकळ्या पाण्यावर विजेपासून आडोसा मिळत नाही.",
            "as": "খোলা পানীত বজ্ৰপাতৰ পৰা আঁৰ লোৱাৰ ঠাই নাথাকে।",
        },
    },
    "general": {
        "water": {
            "en": "Local advisories change quickly once heavy rain sets in.",
            "hi": "भारी बारिश शुरू होते ही स्थानीय चेतावनियाँ तेज़ी से बदलती हैं।",
            "te": "భారీ వర్షం మొదలైన తర్వాత స్థానిక హెచ్చరికలు వేగంగా మారతాయి.",
            "bn": "ভারী বৃষ্টি শুরু হলে স্থানীয় সতর্কবার্তা দ্রুত বদলায়।",
            "mr": "जोरदार पाऊस सुरू झाल्यावर स्थानिक सूचना झपाट्याने बदलतात.",
            "as": "প্ৰবল বৰষুণ আৰম্ভ হ'লে স্থানীয় সতৰ্কবাৰ্তা সোনকালে সলনি হয়।",
        },
        "wind": {
            "en": "Falling branches and loose objects cause most wind injuries.",
            "hi": "हवा से होने वाली ज़्यादातर चोटें गिरती डालियों और खुली चीज़ों से होती हैं।",
            "te": "గాలి వల్ల జరిగే గాయాలు ఎక్కువగా విరిగిపడే కొమ్మలు, వదులు వస్తువుల వల్లే.",
            "bn": "বাতাসে বেশিরভাগ আঘাত আসে ভেঙে পড়া ডাল ও আলগা জিনিস থেকে।",
            "mr": "वाऱ्यामुळे होणाऱ्या बहुतेक दुखापती तुटलेल्या फांद्या व सैल वस्तूंमुळे होतात.",
            "as": "বতাহৰ বেছিভাগ আঘাত ভাঙি পৰা ডাল আৰু ঢিলা বস্তুৰ পৰাই হয়।",
        },
        "heat": {
            "en": "Children, older people and outdoor workers are affected first.",
            "hi": "बच्चे, बुज़ुर्ग और बाहर काम करने वाले सबसे पहले प्रभावित होते हैं।",
            "te": "పిల్లలు, వృద్ధులు, బయట పనిచేసేవారే ముందుగా ప్రభావితమవుతారు.",
            "bn": "শিশু, বয়স্ক ও বাইরে কাজ করা মানুষই সবার আগে কষ্ট পান।",
            "mr": "मुले, वृद्ध व बाहेर काम करणारे सर्वात आधी बाधित होतात.",
            "as": "শিশু, বৃদ্ধ আৰু বাহিৰত কাম কৰা লোকেই আটাইতকৈ আগতে আক্ৰান্ত হয়।",
        },
        "storm": {
            "en": "Indoors and away from windows is the safest place during lightning.",
            "hi": "बिजली चमकने के दौरान घर के अंदर, खिड़कियों से दूर रहना सबसे सुरक्षित है।",
            "te": "పిడుగుల సమయంలో ఇంట్లో, కిటికీలకు దూరంగా ఉండటమే అత్యంత సురక్షితం.",
            "bn": "বজ্রপাতের সময় ঘরের ভিতরে, জানালা থেকে দূরে থাকাই সবচেয়ে নিরাপদ।",
            "mr": "वीज चमकत असताना घरात, खिडक्यांपासून दूर राहणे सर्वात सुरक्षित आहे.",
            "as": "বজ্ৰপাতৰ সময়ত ঘৰৰ ভিতৰত, খিৰিকীৰ পৰা আঁতৰত থকাটোৱেই সৰ্বাধিক নিৰাপদ।",
        },
    },
    "driver": {
        "water": {
            "en": "Standing water hides potholes and can stall an engine in seconds.",
            "hi": "भरा हुआ पानी गड्ढों को छिपा देता है और इंजन कुछ ही पलों में बंद कर सकता है।",
            "te": "నిలిచిన నీరు గుంతలను కప్పేస్తుంది, ఇంజన్ క్షణాల్లో ఆగిపోవచ్చు.",
            "bn": "জমা জল গর্ত ঢেকে রাখে এবং কয়েক সেকেন্ডে ইঞ্জিন বন্ধ করে দিতে পারে।",
            "mr": "साचलेले पाणी खड्डे झाकते आणि काही क्षणांत इंजिन बंद पाडू शकते.",
            "as": "জমা পানীয়ে গাঁত ঢাকি ৰাখে আৰু কেইছেকেণ্ডমানতে ইঞ্জিন বন্ধ কৰি দিব পাৰে।",
        },
        "wind": {
            "en": "A single gust on an open bridge is enough to move a vehicle out of its lane.",
            "hi": "खुले पुल पर एक ही झोंका गाड़ी को उसकी लेन से हटा सकता है।",
            "te": "బహిరంగ వంతెనపై ఒక్క గాలి తాకిడి చాలు, వాహనం లేన్ దాటిపోతుంది.",
            "bn": "খোলা সেতুতে একটি দমকাই গাড়িকে লেন থেকে সরিয়ে দিতে যথেষ্ট।",
            "mr": "मोकळ्या पुलावर एकच झोत गाडीला लेनबाहेर नेण्यास पुरेसा असतो.",
            "as": "মুকলি দলঙত এটা দমকাই গাড়ীখন লেইনৰ পৰা আঁতৰাই নিবলৈ যথেষ্ট।",
        },
        "heat": {
            "en": "Heat is hard on tyres and on the driver's concentration alike.",
            "hi": "गर्मी टायरों पर और चालक के ध्यान पर, दोनों पर भारी पड़ती है।",
            "te": "వేడి టైర్లపైనా, డ్రైవర్ ఏకాగ్రతపైనా సమానంగా ప్రభావం చూపుతుంది.",
            "bn": "গরম টায়ারের উপর যেমন, চালকের মনোযোগের উপরও তেমনই চাপ ফেলে।",
            "mr": "उष्णतेचा ताण टायरवर आणि चालकाच्या एकाग्रतेवर सारखाच पडतो.",
            "as": "গৰমে টায়াৰৰ ওপৰত আৰু চালকৰ মনোযোগৰ ওপৰত একেদৰেই চাপ পেলায়।",
        },
        "storm": {
            "en": "A vehicle parked safely is in far less danger than one moving through a squall.",
            "hi": "सुरक्षित जगह खड़ी गाड़ी, तूफ़ान में चलती गाड़ी से कहीं कम ख़तरे में होती है।",
            "te": "సురక్షితంగా ఆపిన వాహనం, తుఫానులో నడుస్తున్న వాహనం కంటే చాలా తక్కువ ప్రమాదంలో ఉంటుంది.",
            "bn": "নিরাপদে দাঁড় করানো গাড়ি ঝড়ের মধ্যে চলা গাড়ির চেয়ে অনেক কম ঝুঁকিতে থাকে।",
            "mr": "सुरक्षित जागी उभी केलेली गाडी वादळातून धावणाऱ्या गाडीपेक्षा खूप कमी धोक्यात असते.",
            "as": "নিৰাপদে ৰখাই থোৱা গাড়ী ধুমুহাৰ মাজেৰে চলা গাড়ীতকৈ বহু কম বিপদত থাকে।",
        },
    },
    "outdoor_worker": {
        "water": {
            "en": "Saturated ground and filled trenches give way without warning.",
            "hi": "भीगी ज़मीन और पानी भरी खाइयाँ बिना चेतावनी धँस जाती हैं।",
            "te": "తడిసిన నేల, నీరు నిండిన గుంతలు హెచ్చరిక లేకుండా కూలిపోతాయి.",
            "bn": "ভেজা মাটি ও জল ভরা খাদ কোনও পূর্বাভাস ছাড়াই ধসে পড়ে।",
            "mr": "ओलसर जमीन व पाणी भरलेले चर कोणतीही पूर्वसूचना न देता ढासळतात.",
            "as": "তিতা মাটি আৰু পানী ভৰা গাঁত কোনো সতৰ্কবাণী নোহোৱাকৈ ভাঙি পৰে।",
        },
        "wind": {
            "en": "Work at height is the first thing wind makes dangerous.",
            "hi": "ऊँचाई पर काम सबसे पहले हवा की वजह से ख़तरनाक होता है।",
            "te": "గాలి వల్ల ముందుగా ప్రమాదకరంగా మారేది ఎత్తులో చేసే పనే.",
            "bn": "বাতাস সবার আগে উঁচুতে কাজকেই বিপজ্জনক করে তোলে।",
            "mr": "वाऱ्यामुळे सर्वात आधी उंचावरचे कामच धोकादायक होते.",
            "as": "বতাহে আটাইতকৈ আগতে ওখ ঠাইৰ কামকেই বিপজ্জনক কৰি তোলে।",
        },
        "heat": {
            "en": "Heat illness builds through the working day before it is felt.",
            "hi": "गर्मी का असर काम के दौरान धीरे-धीरे बढ़ता है, महसूस बाद में होता है।",
            "te": "వేడి వల్ల వచ్చే అనారోగ్యం పని రోజంతా పేరుకుంటుంది, తెలిసేది ఆలస్యంగా.",
            "bn": "গরমজনিত অসুস্থতা সারা কর্মদিন ধরে জমতে থাকে, টের পাওয়া যায় পরে।",
            "mr": "उष्णतेचा त्रास कामाच्या दिवसभरात साचत जातो, जाणवतो मात्र उशिरा.",
            "as": "গৰমজনিত অসুস্থতা কামৰ দিনটোত জমা হৈ থাকে, গম পোৱা যায় পিছত।",
        },
        "storm": {
            "en": "On an open site, the scaffolding or the crane is the tallest thing around.",
            "hi": "खुले साइट पर मचान या क्रेन ही सबसे ऊँची चीज़ होती है।",
            "te": "ఖాళీ సైట్‌లో పరంజా లేదా క్రేనే చుట్టుపక్కల ఎత్తైన వస్తువు.",
            "bn": "খোলা সাইটে ভারা বা ক্রেনই চারপাশের সবচেয়ে উঁচু জিনিস।",
            "mr": "मोकळ्या साइटवर मचाण किंवा क्रेनच आजूबाजूची सर्वात उंच गोष्ट असते.",
            "as": "মুকলি ছাইটত মাচ বা ক্ৰেইনেই চাৰিওফালৰ আটাইতকৈ ওখ বস্তু।",
        },
    },
    "student": {
        "water": {
            "en": "A flooded stretch on the way is the most common reason a journey turns unsafe.",
            "hi": "रास्ते में भरा हुआ हिस्सा ही सबसे आम वजह है जिससे सफ़र असुरक्षित हो जाता है।",
            "te": "దారిలో నీరు నిలిచిన భాగమే ప్రయాణం ప్రమాదకరంగా మారడానికి అత్యంత సాధారణ కారణం.",
            "bn": "পথে জল জমা অংশই যাত্রা অনিরাপদ হওয়ার সবচেয়ে সাধারণ কারণ।",
            "mr": "वाटेत पाणी साचलेला भाग हेच प्रवास असुरक्षित होण्याचे सर्वात सामान्य कारण आहे.",
            "as": "বাটত পানী জমা অংশেই যাত্ৰা অসুৰক্ষিত হোৱাৰ আটাইতকৈ সাধাৰণ কাৰণ।",
        },
        "wind": {
            "en": "Cycles and two-wheelers are the hardest vehicles to hold steady in gusts.",
            "hi": "झोंकों में साइकिल और दोपहिया ही सबसे मुश्किल से सँभलते हैं।",
            "te": "గాలుల్లో నిలకడగా ఉంచడం అత్యంత కష్టమైనవి సైకిళ్లు, ద్విచక్ర వాహనాలే.",
            "bn": "দমকা বাতাসে সাইকেল ও দুই চাকার যানই সামলানো সবচেয়ে কঠিন।",
            "mr": "झोतांमध्ये सायकल व दुचाकी सांभाळणे सर्वात कठीण असते.",
            "as": "দমকা বতাহত চাইকেল আৰু দুচকীয়া বাহনেই আটাইতকৈ কঠিনকৈ নিয়ন্ত্ৰণ কৰিব লগা হয়।",
        },
        "heat": {
            "en": "Midday heat during outdoor activity is what sends students to the clinic.",
            "hi": "बाहरी गतिविधि के दौरान दोपहर की गर्मी ही छात्रों को क्लिनिक तक पहुँचाती है।",
            "te": "బయటి కార్యకలాపాల్లో మధ్యాహ్న వేడే విద్యార్థులను ఆసుపత్రికి పంపుతుంది.",
            "bn": "বাইরের কাজকর্মের সময় দুপুরের গরমেই শিক্ষার্থীরা অসুস্থ হয়ে পড়ে।",
            "mr": "बाहेरील हालचालींदरम्यानची दुपारची उष्णताच विद्यार्थ्यांना दवाखान्यापर्यंत नेते.",
            "as": "বাহিৰৰ কামৰ সময়ত দুপৰীয়াৰ গৰমেই শিক্ষাৰ্থীসকলক অসুস্থ কৰি তোলে।",
        },
        "storm": {
            "en": "Being caught in the open mid-journey is the main risk.",
            "hi": "सफ़र के बीच खुले में फँस जाना सबसे बड़ा ख़तरा है।",
            "te": "ప్రయాణం మధ్యలో ఆరుబయట చిక్కుకోవడమే ప్రధాన ప్రమాదం.",
            "bn": "যাত্রার মাঝপথে খোলা জায়গায় আটকে পড়াই প্রধান ঝুঁকি।",
            "mr": "प्रवासाच्या मध्येच मोकळ्यावर अडकणे हा मुख्य धोका आहे.",
            "as": "যাত্ৰাৰ মাজতে মুকলি ঠাইত আটক পৰাটোৱেই মুখ্য বিপদ।",
        },
    },
    "caregiver": {
        "water": {
            "en": "The people you look after cannot reach safety as fast as you can.",
            "hi": "जिनकी आप देखभाल करते हैं वे आपकी तरह जल्दी सुरक्षित जगह नहीं पहुँच सकते।",
            "te": "మీరు చూసుకునేవారు మీలా వేగంగా సురక్షిత చోటికి చేరుకోలేరు.",
            "bn": "যাঁদের দেখাশোনা করেন তাঁরা আপনার মতো দ্রুত নিরাপদ জায়গায় পৌঁছাতে পারেন না।",
            "mr": "तुम्ही ज्यांची काळजी घेता ते तुमच्याइतक्या वेगाने सुरक्षित जागी पोहोचू शकत नाहीत.",
            "as": "আপুনি চোৱা-চিতা কৰাসকলে আপোনাৰ দৰে সোনকালে নিৰাপদ ঠাই পাব নোৱাৰে।",
        },
        "wind": {
            "en": "Falling branches and loose roofing injure the slowest movers first.",
            "hi": "गिरती डालियाँ और ढीली छत सबसे पहले उन्हें चोट पहुँचाती हैं जो धीरे चलते हैं।",
            "te": "విరిగిపడే కొమ్మలు, వదులైన పైకప్పు ముందుగా నెమ్మదిగా కదిలేవారినే గాయపరుస్తాయి.",
            "bn": "ভেঙে পড়া ডাল ও আলগা ছাদ আগে তাঁদেরই আঘাত করে যাঁরা ধীরে চলেন।",
            "mr": "पडणाऱ्या फांद्या व सुटलेले छप्पर आधी हळू चालणाऱ्यांनाच इजा करतात.",
            "as": "ভাঙি পৰা ডাল আৰু ঢিলা চালে আগতে লাহে লাহে খোজ কঢ়াসকলকেই আঘাত কৰে।",
        },
        "heat": {
            "en": "Children and older people lose fluids faster and show it later.",
            "hi": "बच्चे और बुज़ुर्ग पानी जल्दी खोते हैं और असर देर से दिखता है।",
            "te": "పిల్లలు, వృద్ధులు నీటిని త్వరగా కోల్పోతారు, లక్షణాలు ఆలస్యంగా కనిపిస్తాయి.",
            "bn": "শিশু ও বয়স্করা দ্রুত জল হারান আর তা বোঝা যায় দেরিতে।",
            "mr": "मुले व वृद्ध लवकर पाणी गमावतात आणि लक्षणे उशिरा दिसतात.",
            "as": "শিশু আৰু বৃদ্ধসকলে সোনকালে পানী হেৰুৱায় আৰু লক্ষণ দেখা যায় পিছত।",
        },
        "storm": {
            "en": "Moving everyone in early costs nothing; doing it late costs time you may not have.",
            "hi": "सबको पहले अंदर लाने में कुछ नहीं जाता; देर करने पर वह समय जाता है जो शायद हो ही न।",
            "te": "అందరినీ ముందే లోపలికి తీసుకురావడం వల్ల నష్టం లేదు; ఆలస్యం చేస్తే మీ దగ్గర లేని సమయం పోతుంది.",
            "bn": "সবাইকে আগে ঘরে আনলে কিছুই হারায় না; দেরি করলে যে সময় নেই সেটাই হারায়।",
            "mr": "सर्वांना आधी आत घेतल्याने काहीच जात नाही; उशीर केल्यास नसलेला वेळ जातो.",
            "as": "সকলোকে আগতে ভিতৰলৈ আনিলে একো নাযায়; পলম কৰিলে নথকা সময়টোৱেই যায়।",
        },
    },
}


def profile_reason(user_type: str | None, hazard: str, lang: str) -> str | None:
    """Why the persona-specific lead action matters, in the reader's language."""
    lang = normalise_lang(lang)
    family = HAZARD_FAMILY.get(hazard)
    if not family:
        return None
    entry = PROFILE_REASONS.get(canonical_profile(user_type), {}).get(family)
    if not entry:
        return None
    return entry.get(lang) or entry.get(DEFAULT_LANG)


# ---------------------------------------------------------------------------
# Languages added after the original six.
#
# The six above are written inline, one column per string, which reads well at
# six and would not at thirteen. Everything since lives in `langs/`, one module
# per language, and merges into these same tables — so every accessor above
# serves them without knowing the difference.
#
# The merge is strict on purpose. Each accessor falls back to English when a key
# is missing, which means a half-finished language would ship as a language that
# quietly answers in English behind a translated name. `validate()` refuses that
# at import: an incomplete pack is an ImportError, not a silent fallback.
# ---------------------------------------------------------------------------
from . import langs as _langs  # noqa: E402

_REFERENCE: dict[str, Any] = {
    "conditions": CONDITIONS[DEFAULT_LANG],
    "hazards": HAZARD_NAMES[DEFAULT_LANG],
    "levels": RISK_LEVELS[DEFAULT_LANG],
    "sentences": {k: v for k, v in SENTENCES[DEFAULT_LANG].items() if not k.startswith(("ri_", "mi_"))},
    "role_sentences": _ROLE_SENTENCES[DEFAULT_LANG],
    "drivers": DRIVERS[DEFAULT_LANG],
    "days": DAYS[DEFAULT_LANG],
    "impact_categories": IMPACT_CATEGORIES[DEFAULT_LANG],
    "impact_status": IMPACT_STATUS[DEFAULT_LANG],
    "hazard_actions": {h: t[DEFAULT_LANG] for h, t in HAZARD_ACTIONS.items()},
    "profile_actions": {p: {f: v[DEFAULT_LANG] for f, v in fams.items()} for p, fams in PROFILE_ACTIONS.items()},
    "profile_reasons": {p: {f: v[DEFAULT_LANG] for f, v in fams.items()} for p, fams in PROFILE_REASONS.items()},
}

_PACKS: dict[str, dict[str, Any]] = _langs.load()

for _code, _pack in sorted(_PACKS.items()):
    _langs.validate(_code, _pack, _REFERENCE)

    CONDITIONS[_code] = dict(_pack["conditions"])
    HAZARD_NAMES[_code] = dict(_pack["hazards"])
    RISK_LEVELS[_code] = dict(_pack["levels"])
    DRIVERS[_code] = dict(_pack["drivers"])
    DAYS[_code] = dict(_pack["days"])
    IMPACT_CATEGORIES[_code] = dict(_pack["impact_categories"])
    IMPACT_STATUS[_code] = dict(_pack["impact_status"])
    TERMINATORS[_code] = _pack["terminator"]
    SENTENCES[_code] = {**_pack["sentences"], **_pack["role_sentences"]}

    for _hazard, _lines in _pack["hazard_actions"].items():
        HAZARD_ACTIONS[_hazard][_code] = list(_lines)
    for _profile, _families in _pack["profile_actions"].items():
        for _family, _text in _families.items():
            PROFILE_ACTIONS[_profile][_family][_code] = _text
    for _profile, _families in _pack["profile_reasons"].items():
        for _family, _text in _families.items():
            PROFILE_REASONS[_profile][_family][_code] = _text

    if _code not in LANGUAGES:
        LANGUAGES = LANGUAGES + (_code,)

