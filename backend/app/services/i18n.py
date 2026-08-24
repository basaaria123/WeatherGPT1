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
    },
    "hi": {
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
    },
    "te": {
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
    },
    "bn": {
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
    },
    "mr": {
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
    },
    "as": {
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

# Profiles the templates cover; aviation/urban alias onto the closest match.
PROFILE_ALIASES: dict[str, str] = {
    "aviation": "traveler",
    "urban": "commuter",
}

PROFILE_ACTIONS: dict[str, dict[str, dict[str, str]]] = {
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
    "fisherman": {
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
    "traveler": {
        "water": {
            "en": "Expect waterlogging and delays; check road and rail status before you start.",
            "hi": "जलभराव और देरी हो सकती है; निकलने से पहले सड़क और रेल की स्थिति देख लें।",
            "te": "నీరు నిలిచి ఆలస్యం కావచ్చు; బయలుదేరే ముందు రోడ్డు, రైలు పరిస్థితి చూసుకోండి.",
            "bn": "জল জমা ও দেরি হতে পারে; রওনা হওয়ার আগে রাস্তা ও ট্রেনের অবস্থা দেখে নিন।",
            "mr": "पाणी साचणे आणि विलंब होऊ शकतो; निघण्यापूर्वी रस्ता व रेल्वेची स्थिती तपासा.",
            "as": "পানী জমা হৈ পলম হ'ব পাৰে; ওলোৱাৰ আগতে ৰাস্তা আৰু ৰেলৰ অৱস্থা চাই লওক।",
        },
        "wind": {
            "en": "High-sided vehicles and two-wheelers are unsafe; postpone hill and coastal routes.",
            "hi": "ऊँचे वाहन और दोपहिया असुरक्षित हैं; पहाड़ी और तटीय रास्ते टालें।",
            "te": "ఎత్తైన వాహనాలు, ద్విచక్ర వాహనాలు సురక్షితం కాదు; కొండ, తీర ప్రాంత మార్గాలు వాయిదా వేయండి.",
            "bn": "উঁচু গাড়ি ও দুই চাকার যান নিরাপদ নয়; পাহাড়ি ও উপকূলীয় পথ পিছিয়ে দিন।",
            "mr": "उंच वाहने आणि दुचाकी असुरक्षित आहेत; डोंगरी व किनारी मार्ग टाळा.",
            "as": "ওখ গাড়ী আৰু দুচকীয়া বাহন নিৰাপদ নহয়; পাহাৰীয়া আৰু উপকূলীয় বাট পিছুৱাই দিয়ক।",
        },
        "heat": {
            "en": "Travel in the early morning or late evening, and carry water for the whole journey.",
            "hi": "सुबह जल्दी या देर शाम यात्रा करें, पूरी यात्रा के लिए पानी साथ रखें।",
            "te": "ఉదయం పెందలాడే లేదా సాయంత్రం ఆలస్యంగా ప్రయాణించండి, ప్రయాణమంతటికీ నీరు తీసుకెళ్లండి.",
            "bn": "ভোরে বা সন্ধ্যার পরে যাত্রা করুন, পুরো পথের জন্য জল সঙ্গে নিন।",
            "mr": "पहाटे किंवा उशिरा संध्याकाळी प्रवास करा, संपूर्ण प्रवासासाठी पाणी सोबत ठेवा.",
            "as": "ৰাতিপুৱা সোনকালে বা সন্ধিয়া পলমকৈ যাত্ৰা কৰক, গোটেই বাটৰ বাবে পানী লগত লওক।",
        },
        "storm": {
            "en": "Do not shelter under trees at bus stops; wait indoors until the lightning stops.",
            "hi": "बस स्टॉप पर पेड़ों के नीचे न रुकें; बिजली बंद होने तक अंदर रहें।",
            "te": "బస్ స్టాప్‌లో చెట్ల కింద ఆగవద్దు; పిడుగులు ఆగే వరకు లోపల ఉండండి.",
            "bn": "বাস স্টপে গাছের নিচে দাঁড়াবেন না; বজ্রপাত না থামা পর্যন্ত ঘরের ভিতরে থাকুন।",
            "mr": "बस स्टॉपवर झाडाखाली थांबू नका; वीज थांबेपर्यंत आतच थांबा.",
            "as": "বাছ ষ্টপত গছৰ তলত নাথাকিব; বজ্ৰপাত নাথমালৈকে ভিতৰত থাকক।",
        },
    },
    "commuter": {
        "water": {
            "en": "Leave earlier than usual and avoid underpasses that flood quickly.",
            "hi": "सामान्य से जल्दी निकलें और जल्दी भरने वाले अंडरपास से बचें।",
            "te": "మామూలు కంటే ముందే బయలుదేరండి, త్వరగా నీరు నిలిచే అండర్‌పాస్‌లు తప్పించుకోండి.",
            "bn": "রোজকার চেয়ে আগে বেরোন এবং দ্রুত জল জমে এমন আন্ডারপাস এড়ান।",
            "mr": "नेहमीपेक्षा लवकर निघा आणि पटकन पाणी साचणारे भुयारी मार्ग टाळा.",
            "as": "সদায়তকৈ সোনকালে ওলাওক আৰু সোনকালে পানী জমা হোৱা আণ্ডাৰপাছ এৰাই চলক।",
        },
        "wind": {
            "en": "Riding a two-wheeler is risky; use public transport if you can.",
            "hi": "दोपहिया चलाना जोखिम भरा है; हो सके तो सार्वजनिक परिवहन लें।",
            "te": "ద్విచక్ర వాహనం నడపడం ప్రమాదకరం; వీలైతే ప్రజా రవాణా వాడండి.",
            "bn": "দুই চাকার যান চালানো ঝুঁকিপূর্ণ; পারলে গণপরিবহন ব্যবহার করুন।",
            "mr": "दुचाकी चालवणे धोक्याचे आहे; शक्य असल्यास सार्वजनिक वाहतूक वापरा.",
            "as": "দুচকীয়া বাহন চলোৱা বিপজ্জনক; পাৰিলে ৰাজহুৱা পৰিবহন ব্যৱহাৰ কৰক।",
        },
        "heat": {
            "en": "Avoid waiting in direct sun; carry water and use shaded stops.",
            "hi": "धूप में खड़े रहने से बचें; पानी साथ रखें और छायादार स्टॉप चुनें।",
            "te": "ఎండలో నిలబడవద్దు; నీరు తీసుకెళ్లండి, నీడ ఉన్న స్టాప్‌లు ఎంచుకోండి.",
            "bn": "রোদে দাঁড়িয়ে থাকা এড়ান; জল সঙ্গে রাখুন ও ছায়াযুক্ত স্টপ ব্যবহার করুন।",
            "mr": "उन्हात उभे राहणे टाळा; पाणी सोबत ठेवा आणि सावलीतील थांबे वापरा.",
            "as": "ৰ'দত থিয় হৈ নাথাকিব; পানী লগত ৰাখক আৰু ছাঁ থকা ষ্টপ ব্যৱহাৰ কৰক।",
        },
        "storm": {
            "en": "Wait the storm out at the station or office rather than riding through it.",
            "hi": "तूफ़ान के दौरान स्टेशन या दफ़्तर में ही रुकें, बीच में सफ़र न करें।",
            "te": "తుఫాను సమయంలో స్టేషన్ లేదా ఆఫీసులోనే ఉండండి, ప్రయాణం చేయవద్దు.",
            "bn": "ঝড়ের সময় স্টেশন বা অফিসে অপেক্ষা করুন, পথে বেরোবেন না।",
            "mr": "वादळादरम्यान स्टेशन किंवा कार्यालयातच थांबा, प्रवास करू नका.",
            "as": "ধুমুহাৰ সময়ত ষ্টেচন বা কাৰ্যালয়তে অপেক্ষা কৰক, বাটত নোলাব।",
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
    "en": {"farming": "Farming", "fishing": "Fishing", "travel": "Travel",
           "household": "Household", "outdoor": "Outdoor activity"},
    "hi": {"farming": "खेती", "fishing": "मछली पकड़ना", "travel": "यात्रा",
           "household": "घर-गृहस्थी", "outdoor": "बाहरी गतिविधि"},
    "te": {"farming": "వ్యవసాయం", "fishing": "చేపల వేట", "travel": "ప్రయాణం",
           "household": "ఇంటి పనులు", "outdoor": "బయటి కార్యకలాపాలు"},
    "bn": {"farming": "কৃষিকাজ", "fishing": "মাছ ধরা", "travel": "যাত্রা",
           "household": "ঘরের কাজ", "outdoor": "বাইরের কাজকর্ম"},
    "mr": {"farming": "शेती", "fishing": "मासेमारी", "travel": "प्रवास",
           "household": "घरकाम", "outdoor": "बाहेरील हालचाल"},
    "as": {"farming": "কৃষি", "fishing": "মাছ ধৰা", "travel": "যাত্ৰা",
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
    profile = (user_type or "general").strip().lower()
    profile = PROFILE_ALIASES.get(profile, profile)
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
