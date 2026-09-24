"""Native-language audition text; voice selection never falls back to another voice."""
SAMPLES = {
    'en': 'Take a slow breath. Let your heart be still. May peace and strength be with you today.',
    'gu': 'નમસ્તે. ધીમે ધીમે શ્વાસ લો. તમારું મન શાંત રાખો. આજનો દિવસ તમારા જીવનમાં શાંતિ અને આનંદ લાવે.',
    'hi': 'नमस्ते। धीरे से साँस लें। अपने मन को शांत होने दें। आज का दिन आपके जीवन में शांति और खुशियाँ लाए।',
    'es': 'Hola. Respira despacio y deja que tu corazón encuentre la calma. Que tengas un día lleno de paz.',
    'fr': 'Bonjour. Prenez une profonde inspiration. Que cette journée vous apporte la paix et la sérénité.',
    'pt': 'Olá. Respire devagar e deixe seu coração ficar tranquilo. Que o seu dia seja cheio de paz.',
    'it': 'Ciao. Respira lentamente e lascia che il tuo cuore trovi la calma. Ti auguro una giornata serena.',
    'ja': 'こんにちは。ゆっくりと息を吸って、心を落ち着かせましょう。今日が穏やかな一日になりますように。',
    'zh': '你好。请慢慢呼吸，让心情平静下来。愿今天带给你平安、温暖和力量。',
    'de': 'Hallo. Atme langsam und lass dein Herz zur Ruhe kommen. Ich wünsche dir einen friedlichen Tag.',
    'ar': 'مرحباً. خذ نفساً عميقاً ودع قلبك يهدأ. أتمنى لك يوماً مليئاً بالسلام والطمأنينة.',
    'bn': 'নমস্কার। ধীরে ধীরে শ্বাস নিন। মন শান্ত রাখুন। আজকের দিনটি আপনার জীবনে শান্তি ও আনন্দ নিয়ে আসুক।',
    'mr': 'नमस्कार. हळू हळू श्वास घ्या. मन शांत ठेवा. आजचा दिवस तुमच्या आयुष्यात शांती आणि आनंद घेऊन येवो.',
    'ta': 'வணக்கம். மெதுவாக மூச்சை இழுங்கள். மனதை அமைதியாக வைத்திருங்கள். இன்று உங்களுக்கு இனிய நாளாக அமையட்டும்.',
    'te': 'నమస్కారం. నెమ్మదిగా శ్వాస తీసుకోండి. మీ మనసును ప్రశాంతంగా ఉంచండి. ఈ రోజు మీకు ఆనందాన్ని అందించాలి.',
    'kn': 'ನಮಸ್ಕಾರ. ನಿಧಾನವಾಗಿ ಉಸಿರಾಡಿ. ನಿಮ್ಮ ಮನಸ್ಸನ್ನು ಶಾಂತವಾಗಿರಿಸಿ. ಈ ದಿನ ನಿಮಗೆ ಸಂತೋಷ ತರಲಿ.',
    'ml': 'നമസ്കാരം. പതുക്കെ ശ്വാസമെടുക്കൂ. മനസ്സ് ശാന്തമാക്കൂ. ഇന്നത്തെ ദിവസം സന്തോഷം നിറഞ്ഞതാകട്ടെ.',
    'ur': 'السلام علیکم۔ آہستہ سانس لیں اور اپنے دل کو سکون دیں۔ آج کا دن آپ کے لیے خوشیاں لے کر آئے۔',
    'ne': 'नमस्कार। बिस्तारै सास लिनुहोस्। मन शान्त राख्नुहोस्। आजको दिन खुसीले भरिएको होस्।',
    'ko': '안녕하세요. 천천히 숨을 쉬고 마음을 편안하게 해 보세요. 오늘도 평온한 하루 보내세요.',
    'ru': 'Здравствуйте. Сделайте медленный вдох и позвольте себе успокоиться. Желаю вам хорошего дня.',
    'uk': 'Вітаю. Зробіть повільний вдих і заспокойте своє серце. Бажаю вам мирного дня.',
    'nl': 'Hallo. Adem rustig in en laat je hart tot rust komen. Ik wens je een fijne dag.',
    'pl': 'Witaj. Weź spokojny oddech i pozwól sobie odpocząć. Życzę ci spokojnego dnia.',
    'tr': 'Merhaba. Yavaşça nefes alın ve kalbinizin sakinleşmesine izin verin. Huzurlu bir gün dilerim.',
    'vi': 'Xin chào. Hãy hít thở chậm và để tâm hồn bình yên. Chúc bạn một ngày tốt lành.',
    'th': 'สวัสดีค่ะ ค่อย ๆ หายใจและทำใจให้สงบ ขอให้วันนี้เป็นวันที่ดีของคุณ',
    'id': 'Halo. Tarik napas perlahan dan tenangkan hati Anda. Semoga hari ini penuh kedamaian.',
    'ms': 'Selamat sejahtera. Tarik nafas perlahan dan tenangkan hati anda. Semoga hari anda penuh kedamaian.',
    'sv': 'Hej. Andas långsamt och låt ditt hjärta komma till ro. Jag önskar dig en fin dag.',
    'da': 'Hej. Træk vejret langsomt og lad dit hjerte finde ro. Jeg ønsker dig en god dag.',
    'nb': 'Hei. Pust rolig og la hjertet ditt finne fred. Jeg ønsker deg en god dag.',
    'fi': 'Hei. Hengitä rauhallisesti ja anna mielesi levätä. Toivotan sinulle hyvää päivää.',
    'el': 'Γεια σας. Πάρτε μια αργή ανάσα και αφήστε την καρδιά σας να ηρεμήσει. Καλή σας μέρα.',
    'ro': 'Bună. Respiră încet și lasă inima să se liniștească. Îți doresc o zi frumoasă.',
    'hu': 'Üdvözlöm. Vegyen lassan levegőt és engedje megnyugodni a szívét. Szép napot kívánok.',
    'cs': 'Dobrý den. Pomalu se nadechněte a nechte své srdce uklidnit. Přeji vám krásný den.',
    'fil': 'Kumusta. Huminga nang dahan-dahan at hayaang maging payapa ang iyong puso. Magandang araw sa iyo.',
    'sw': 'Habari. Pumua polepole na uache moyo wako utulie. Nakutakia siku yenye amani.',
}


def sample_for(voice, catalog):
    locale = next((v.get('Locale', 'en-US') for v in catalog if v['ShortName'] == voice), 'en-US')
    language = locale.split('-')[0]
    return SAMPLES.get(language, SAMPLES['en']), language if language in SAMPLES else 'en'
