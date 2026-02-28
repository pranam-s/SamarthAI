from __future__ import annotations

BASE_LOCALE = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app.name": "Samarth AI Resume Platform",
        "nav.home": "Home",
        "nav.dashboard": "Dashboard",
        "nav.resumes": "Resumes",
        "nav.jobs": "Jobs",
        "nav.applications": "Applications",
        "nav.analysis": "Market Analysis",
        "nav.login": "Login",
        "nav.register": "Register",
        "nav.logout": "Logout",
        "common.submit": "Submit",
        "common.cancel": "Cancel",
        "common.view": "View",
        "common.create": "Create",
        "common.update": "Update",
        "common.delete": "Delete",
        "common.language": "Language",
        "common.back": "Back",
        "home.hero.title": "AI-Powered Resume and Job Matching",
        "home.hero.subtitle": "Build better resumes, discover relevant roles, and improve your applications with AI.",
        "auth.login.title": "Login",
        "auth.register.title": "Create Account",
        "auth.email": "Email",
        "auth.password": "Password",
        "auth.full_name": "Full Name",
        "auth.recruiter": "I am a recruiter",
        "dashboard.recruiter": "Recruiter Dashboard",
        "dashboard.jobseeker": "Job Seeker Dashboard",
        "jobs.title": "Jobs",
        "jobs.create": "Post New Job",
        "resumes.title": "Resumes",
        "resumes.upload": "Upload Resume",
        "applications.title": "Applications",
        "analysis.title": "Job Market Analysis",
        "footer.copy": "AI-Powered Resume Platform",
    },
    "hi": {
        "nav.home": "होम", "nav.dashboard": "डैशबोर्ड", "nav.resumes": "रिज़्यूमे", "nav.jobs": "नौकरियाँ", "nav.applications": "आवेदन", "nav.analysis": "मार्केट विश्लेषण", "nav.login": "लॉगिन", "nav.register": "रजिस्टर", "nav.logout": "लॉगआउट", "common.language": "भाषा"
    },
    "bn": {
        "nav.home": "হোম", "nav.dashboard": "ড্যাশবোর্ড", "nav.resumes": "রেজ্যুমে", "nav.jobs": "চাকরি", "nav.applications": "আবেদন", "nav.analysis": "বাজার বিশ্লেষণ", "nav.login": "লগইন", "nav.register": "রেজিস্টার", "nav.logout": "লগআউট", "common.language": "ভাষা"
    },
    "te": {
        "nav.home": "హోమ్", "nav.dashboard": "డ్యాష్‌బోర్డ్", "nav.resumes": "రెజ్యూమేలు", "nav.jobs": "ఉద్యోగాలు", "nav.applications": "దరఖాస్తులు", "nav.analysis": "మార్కెట్ విశ్లేషణ", "nav.login": "లాగిన్", "nav.register": "నమోదు", "nav.logout": "లాగౌట్", "common.language": "భాష"
    },
    "mr": {
        "nav.home": "मुख्यपृष्ठ", "nav.dashboard": "डॅशबोर्ड", "nav.resumes": "रेझ्युमे", "nav.jobs": "नोकऱ्या", "nav.applications": "अर्ज", "nav.analysis": "बाजार विश्लेषण", "nav.login": "लॉगिन", "nav.register": "नोंदणी", "nav.logout": "लॉगआउट", "common.language": "भाषा"
    },
    "ta": {
        "nav.home": "முகப்பு", "nav.dashboard": "டாஷ்போர்டு", "nav.resumes": "சுயவிவரங்கள்", "nav.jobs": "வேலைகள்", "nav.applications": "விண்ணப்பங்கள்", "nav.analysis": "சந்தை பகுப்பாய்வு", "nav.login": "உள்நுழை", "nav.register": "பதிவு", "nav.logout": "வெளியேறு", "common.language": "மொழி"
    },
    "ur": {
        "nav.home": "ہوم", "nav.dashboard": "ڈیش بورڈ", "nav.resumes": "ریزومے", "nav.jobs": "نوکریاں", "nav.applications": "درخواستیں", "nav.analysis": "مارکیٹ تجزیہ", "nav.login": "لاگ ان", "nav.register": "رجسٹر", "nav.logout": "لاگ آؤٹ", "common.language": "زبان"
    },
    "gu": {
        "nav.home": "હોમ", "nav.dashboard": "ડૅશબોર્ડ", "nav.resumes": "રિઝ્યૂમે", "nav.jobs": "નોકરીઓ", "nav.applications": "અરજીઓ", "nav.analysis": "માર્કેટ વિશ્લેષણ", "nav.login": "લૉગિન", "nav.register": "નોંધણી", "nav.logout": "લૉગઆઉટ", "common.language": "ભાષા"
    },
    "kn": {
        "nav.home": "ಮುಖಪುಟ", "nav.dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "nav.resumes": "ರೆಸ್ಯೂಮ್‌ಗಳು", "nav.jobs": "ಉದ್ಯೋಗಗಳು", "nav.applications": "ಅರ್ಜಿಗಳು", "nav.analysis": "ಮಾರುಕಟ್ಟೆ ವಿಶ್ಲೇಷಣೆ", "nav.login": "ಲಾಗಿನ್", "nav.register": "ನೋಂದಣಿ", "nav.logout": "ಲಾಗ್‌ಔಟ್", "common.language": "ಭಾಷೆ"
    },
    "ml": {
        "nav.home": "ഹോം", "nav.dashboard": "ഡാഷ്ബോർഡ്", "nav.resumes": "റെസ്യൂമുകൾ", "nav.jobs": "ജോലികൾ", "nav.applications": "അപേക്ഷകൾ", "nav.analysis": "മാർക്കറ്റ് വിശകലനം", "nav.login": "ലോഗിൻ", "nav.register": "രജിസ്റ്റർ", "nav.logout": "ലോഗൗട്ട്", "common.language": "ഭാഷ"
    },
    "es": {"nav.home": "Inicio", "nav.dashboard": "Panel", "nav.resumes": "Currículums", "nav.jobs": "Empleos", "nav.applications": "Solicitudes", "nav.analysis": "Análisis de mercado", "nav.login": "Iniciar sesión", "nav.register": "Registrarse", "nav.logout": "Cerrar sesión", "common.language": "Idioma"},
    "fr": {"nav.home": "Accueil", "nav.dashboard": "Tableau de bord", "nav.resumes": "CV", "nav.jobs": "Emplois", "nav.applications": "Candidatures", "nav.analysis": "Analyse du marché", "nav.login": "Connexion", "nav.register": "S’inscrire", "nav.logout": "Déconnexion", "common.language": "Langue"},
    "ar": {"nav.home": "الرئيسية", "nav.dashboard": "لوحة التحكم", "nav.resumes": "السير الذاتية", "nav.jobs": "الوظائف", "nav.applications": "الطلبات", "nav.analysis": "تحليل السوق", "nav.login": "تسجيل الدخول", "nav.register": "إنشاء حساب", "nav.logout": "تسجيل الخروج", "common.language": "اللغة"},
    "zh": {"nav.home": "首页", "nav.dashboard": "仪表板", "nav.resumes": "简历", "nav.jobs": "职位", "nav.applications": "申请", "nav.analysis": "市场分析", "nav.login": "登录", "nav.register": "注册", "nav.logout": "退出", "common.language": "语言"},
    "pt": {"nav.home": "Início", "nav.dashboard": "Painel", "nav.resumes": "Currículos", "nav.jobs": "Vagas", "nav.applications": "Candidaturas", "nav.analysis": "Análise de mercado", "nav.login": "Entrar", "nav.register": "Registrar", "nav.logout": "Sair", "common.language": "Idioma"},
    "de": {"nav.home": "Startseite", "nav.dashboard": "Dashboard", "nav.resumes": "Lebensläufe", "nav.jobs": "Jobs", "nav.applications": "Bewerbungen", "nav.analysis": "Marktanalyse", "nav.login": "Anmelden", "nav.register": "Registrieren", "nav.logout": "Abmelden", "common.language": "Sprache"},
    "ru": {"nav.home": "Главная", "nav.dashboard": "Панель", "nav.resumes": "Резюме", "nav.jobs": "Вакансии", "nav.applications": "Заявки", "nav.analysis": "Анализ рынка", "nav.login": "Войти", "nav.register": "Регистрация", "nav.logout": "Выйти", "common.language": "Язык"},
    "ja": {"nav.home": "ホーム", "nav.dashboard": "ダッシュボード", "nav.resumes": "履歴書", "nav.jobs": "求人", "nav.applications": "応募", "nav.analysis": "市場分析", "nav.login": "ログイン", "nav.register": "登録", "nav.logout": "ログアウト", "common.language": "言語"},
    "ko": {"nav.home": "홈", "nav.dashboard": "대시보드", "nav.resumes": "이력서", "nav.jobs": "채용", "nav.applications": "지원서", "nav.analysis": "시장 분석", "nav.login": "로그인", "nav.register": "가입", "nav.logout": "로그아웃", "common.language": "언어"},
    "it": {"nav.home": "Home", "nav.dashboard": "Dashboard", "nav.resumes": "Curriculum", "nav.jobs": "Lavori", "nav.applications": "Candidature", "nav.analysis": "Analisi di mercato", "nav.login": "Accedi", "nav.register": "Registrati", "nav.logout": "Esci", "common.language": "Lingua"},
}


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return BASE_LOCALE

    locale_key = locale.split(",")[0].split("-")[0].strip().lower()
    return locale_key if locale_key in TRANSLATIONS else BASE_LOCALE


def translate(locale: str, key: str) -> str:
    selected = TRANSLATIONS.get(normalize_locale(locale), {})
    if key in selected:
        return selected[key]
    return TRANSLATIONS[BASE_LOCALE].get(key, key)
