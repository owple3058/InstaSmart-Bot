import re

class ProfileAnalyzer:
    def __init__(self):
        # Genişletilebilir isim listeleri
        self.female_names = {
            # Türk Kadın İsimleri (Genişletilmiş)
            "ayse", "fatma", "hayriye", "hatice", "zeynep", "elif", "merve", "gamze", "buse", "esra", 
            "kubra", "betul", "busra", "ozge", "yagmur", "beyza", "irem", "simge", "gizem", "sude",
            "dilara", "seyma", "aleyna", "ebru", "tugba", "yasemin", "songul", "hulya", "derya", "sevgi",
            "pinar", "burcu", "selin", "ece", "nazli", "asli", "didem", "sinem", "hande", "duygu",
            "sedef", "ilayda", "melis", "melisa", "sena", "ceren", "ezgi", "hilal", "rabia", "sultan",
            "emine", "havva", "ozlem", "esma", "asiye", "sevim", "azra", "hiranur", "defne", "eylul",
            "sumeyye", "seyhan", "nur", "nuray", "nuran", "aylin", "aysel", "ayten", "aynur", "belgin",
            "berna", "bilge", "birsen", "candan", "cansu", "cemre", "cigdem", "damla", "deniz", "dilek",
            "elvan", "emel", "feride", "filiz", "funda", "gonca", "gulsah", "gulsen", "gulay", "guler",
            "gulsum", "hacer", "hale", "hazal", "iclal", "ipek", "kader", "kadriye", "kamile", "kezban",
            "leyla", "medine", "melek", "meltem", "mine", "mualla", "munevver", "nagihan", "nalan", "nazan",
            "necla", "nefes", "neriman", "neslihan", "nesrin", "nida", "nihal", "nilay", "nilgun", "nurcan",
            "nurgul", "nursel", "oya", "ozden", "oznur", "pelin", "perihan", "reyhan", "rukiye", "saadet",
            "sabahat", "sabiha", "safiye", "saniye", "seher", "selda", "sema", "semiha", "serap", "serpil",
            "sevda", "sevil", "sevinc", "sibel", "su", "suna", "suzanne", "suzan", "tansu", "tuba", "tulay",
            "tulin", "turkan", "ulku", "ummu", "vildan", "yesim", "yildiz", "yonca", "zahide", "zehra", "zeliha",
            "zuhal", "sukran", "sengul", "senay", "serif", "serife", "saziye", "sukriye", "sumeyra", "seyda",
            "ada", "almila", "alya", "arya", "asya", "aybuke", "ayca", "aydan", "ayfer", "ayla", "aysegul",
            "aysun", "bahar", "basak", "begum", "bengi", "bengisu", "beril", "berivan", "berna", "berrak",
            "beste", "betigul", "birgul", "buket", "burcin", "canan", "cagla", "ceylan", "damla", "defne",
            "demet", "dila", "dilan", "dilber", "dilem", "doganur", "dudu", "eda", "ege", "ela", "elcin",
            "elfida", "elmas", "emine", "esila", "eslem", "eylul", "fadime", "fahriye", "feyza", "figen",
            "fikriye", "fulya", "fureya", "gamze", "gaye", "giz", "gokce", "gokcen", "goksu", "gozde",
            "gul", "gulbahar", "gulben", "gulbin", "gulcan", "gulcin", "gulden", "guldeste", "gulfem",
            "gulhan", "gulistan", "gulizar", "gullu", "gulnar", "gulnihal", "gulnur", "gulperi", "gulsah",
            "gulseren", "gulsum", "gunay", "gunes", "guzin", "habibe", "hadiye", "hafize", "halide", "halime",
            "hamiyet", "handan", "hanife", "hasibe", "hayal", "hazal", "hediye", "hicran", "hilal", "huriye",
            "ikbal", "ilgin", "ilknur", "imren", "inci", "ipek", "irem", "isil", "islay", "itir", "jale",
            "julide", "kader", "kadriye", "kamile", "kardelen", "kayra", "kerime", "kevser", "keziban",
            "kiraz", "kiymet", "kumru", "lale", "lamia", "latife", "leman", "lemis", "lerzan", "leyla",
            "lutfiye", "macide", "makbule", "manolya", "mavi", "maya", "mediha", "mehpare", "mehtap",
            "melahat", "melda", "melek", "meliha", "melike", "melis", "melisa", "meltem", "memnune",
            "menekse", "meral", "mercran", "meric", "merih", "merve", "meryem", "mevhibe", "mevlude",
            "munevver", "munire", "murvet", "musherref", "mujde", "mujgan", "mukadder", "mukaddes",
            "mukerrem", "mumine", "munise", "muruvvet", "naciye", "nadide", "nadire", "nady", "nafize",
            "nagehan", "nahide", "naile", "naime", "nalan", "name", "narin", "naz", "nazan", "nazife",
            "nazli", "nazmiye", "nebahat", "nebihe", "necla", "necm", "necmiye", "nedret", "nefes",
            "nehir", "nela", "neriman", "nermin", "neslihan", "nesrin", "nese", "neset", "neval",
            "nevin", "nevra", "neyran", "nezahet", "nezahat", "nezaket", "nida", "nigar", "nihal",
            "nihan", "nil", "nilay", "nilgun", "nilufer", "nimet", "nisa", "nisan", "nur", "nuran",
            "nuray", "nurcan", "nurdan", "nurdane", "nurgul", "nurhan", "nuriye", "nursel", "nursen",
            "nurten", "nurtin", "oya", "oyku", "ozden", "ozge", "ozgul", "ozlem", "ozlen", "oznur",
            "pakize", "papatya", "parla", "pelin", "pelinsu", "pembe", "peri", "perihan", "pervin",
            "petek", "pinar", "piraye", "rabia", "rahime", "rahsan", "rana", "rasime", "ravza",
            "remziye", "rengin", "reyhan", "rozerin", "ruhan", "ruken", "rukiye", "ruya", "saadet",
            "sabahat", "sabiha", "sabriye", "sacide", "sadiye", "safiye", "sahika", "sahra", "saime",
            "sakine", "saliha", "salime", "samime", "sanal", "sanem", "saniye", "sare", "sari",
            "sati", "secil", "seda", "sedef", "seher", "selda", "selen", "selin", "selma", "selvi",
            "sema", "semhat", "semiha", "semra", "sena", "senem", "seniha", "serap", "seray", "serpil",
            "serra", "sevda", "sevgi", "sevil", "sevilay", "sevim", "sevinc", "sevtap", "seyhan",
            "seyma", "seymen", "seyrantepe", "sezin", "siddika", "sidika", "silan", "sima", "simay",
            "simge", "sinem", "siren", "sirin", "sitare", "sibel", "solmaz", "songul", "su", "suat",
            "sude", "sudiye", "suheyla", "sultan", "sumru", "suna", "sunay", "sureyya", "susan",
            "suzan", "sahinde", "saziye", "sebnem", "sefik", "sefika", "sehrazat", "sehriban",
            "selale", "senay", "sengul", "sennur", "serife", "sermin", "seyda", "seyma", "sevval",
            "seyma", "sifa", "siir", "simal", "sirin", "sule", "sukran", "sukriye", "sukufe",
            "tacinur", "tahire", "taliha", "tamay", "tanem", "tansu", "tanyeli", "tayyibe",
            "tenzile", "teslime", "tevhide", "tijen", "tugba", "tugce", "tuhana", "tulin", "tulay",
            "tulın", "turkan", "tutku", "ufuk", "ulku", "ulviye", "ummu", "ummuhan", "umran",
            "vacide", "vahide", "varide", "vasfiye", "veda", "vedia", "vefa", "vesile", "vicdan",
            "vildan", "vuslat", "yagmur", "yakut", "yaprak", "yasemin", "yagmur", "yelda", "yeliz",
            "yesim", "yeter", "yildiz", "yonca", "yosun", "yurdagul", "yurdanur", "yusra", "zahide",
            "zehra", "zeki", "zekiye", "zeliha", "zerrin", "zeynep", "zisan", "ziynet", "zubeyde",
            "zuhal", "zuhre", "zulal", "zuleyha", "zumrut",
            
            # Yabancı Kadın İsimleri (Popüler - Genişletilmiş)
            "maria", "jessica", "sarah", "emily", "anna", "lisa", "julia", "laura", "emma", "hannah",
            "olivia", "ava", "sophia", "isabella", "mia", "charlotte", "amelia", "harper", "evelyn", "abigail",
            "elizabeth", "sofia", "avery", "ella", "madison", "scarlett", "victoria", "aria", "grace", "chloe",
            "camila", "penelope", "riley", "layla", "lillian", "nora", "zoey", "mila", "aubrey", "lily",
            "addison", "eleanor", "natalie", "luna", "savannah", "brooklyn", "leah", "zoe", "stella", "hazel",
            "ellie", "paisley", "audrey", "skylar", "violet", "claire", "bella", "aurora", "lucy", "anna",
            "samantha", "caroline", "genesis", "aaliyah", "kennedy", "kinsley", "allison", "maya", "sarah",
            "madelyn", "adeline", "alexa", "ariana", "elena", "gabriella", "naomi", "alice", "sadie", "hailey",
            "eva", "emilia", "autumn", "quinn", "nevah", "piper", "ruby", "serenity", "willow", "everly",
            "cora", "kaylee", "lydia", "aubree", "arianna", "eliana", "peyton", "melanie", "gianna", "isabelle",
            "kate", "catherine", "christina", "rachel", "rebecca", "jennifer", "stephanie", "vanessa", "courtney", "nicole",
            "amanda", "megan", "kaitlyn", "ashley", "brittany", "danielle", "melissa", "tiffany", "amber", "kayla",
            "kimberly", "crystal", "amy", "michelle", "angela", "heather", "kelly", "erin", "sara", "mary",
            "patricia", "linda", "barbara", "susan", "margaret", "betty", "dorothy", "nancy", "karen", "helen",
            "sandra", "donna", "carol", "ruth", "sharon", "brenda", "pamela", "deborah", "virginia", "kathleen",
            "martha", "debra", "janet", "joyce", "diane", "julie", "joan"
        }
        
        self.male_names = {
            # Türk Erkek İsimleri (Genişletilmiş)
            "ahmet", "mehmet", "mustafa", "ali", "veli", "can", "cem", "emre", "murat", "burak",
            "yusuf", "omer", "furkan", "enes", "fatih", "ibrahim", "huseyin", "hasan", "ismail", "osman",
            "hakan", "gokhan", "serkan", "volkan", "tolga", "arda", "mert", "berk", "kerem", "kaan",
            "abdullah", "adem", "adnan", "akif", "alp", "alper", "anil", "arif", "aydin", "ayhan",
            "baris", "batu", "batuhan", "bayram", "bedirhan", "bekir", "berat", "berkay", "besim", "bilal",
            "birol", "bora", "bulent", "caglar", "cagri", "cahit", "celal", "cemal", "cengiz", "cihan",
            "coskun", "cuma", "davut", "demir", "dogan", "dogukan", "dursun", "ekrem", "emin", "engin",
            "ercan", "erdal", "erdem", "erhan", "erkan", "erol", "ersin", "ertugrul", "evren", "faruk",
            "ferhat", "ferit", "fikret", "gokmen", "gorkem", "guven", "halil", "halit", "haluk", "hamza",
            "harun", "haydar", "hidayet", "hikmet", "ilhan", "ilker", "ilyas", "isa", "ishak", "iskender",
            "izzet", "kadara", "kadir", "kemal", "kenan", "koray", "korkmaz", "kubilay", "kursat", "levent",
            "mahmut", "mecit", "melih", "mesut", "metin", "mete", "mikail", "mirac", "muhammed", "muharrem",
            "muhsin", "musa", "nacim", "nazim", "necat", "necip", "nedim", "nehat", "nihat", "nurettin",
            "oguz", "oguzhan", "okan", "oktay", "onur", "orhan", "ozan", "ozcan", "ozgur", "ozkan",
            "recep", "remzi", "ridvan", "riza", "salih", "samet", "savas", "selami", "selcuk", "selim",
            "semih", "serdar", "serhat", "servet", "sinan", "soner", "suleyman", "taha", "tahsin", "tamer",
            "taner", "tarik", "tayfun", "taylan", "tayyib", "tekim", "temel", "tevfik", "timur", "tuncay",
            "turan", "ugur", "umit", "unal", "veysel", "yasar", "yasin", "yavuz", "yigit", "yilmaz",
            "yunus", "zafer", "zekeriya", "zeki", "ziya", "acan", "acar", "acun", "adige", "adil",
            "affan", "afsin", "agah", "ahsen", "akin", "akmet", "aksel", "aktug", "aladdin", "alcan",
            "algin", "alic", "alican", "alim", "alis", "alkin", "altan", "altay", "altug", "ammar",
            "araz", "arcan", "arel", "argun", "arkan", "armagan", "arman", "aras", "asaf", "asker",
            "askin", "aslan", "ata", "ataberk", "atacan", "atag", "atahan", "atakan", "atalay", "atilla",
            "atlas", "avci", "avni", "ayaz", "aybars", "ayberk", "aykut", "aytac", "aytekin", "azad",
            "azer", "aziz", "azmi", "baha", "bahadir", "bahattin", "bahri", "baki", "bala", "baran",
            "barbaros", "barin", "baris", "barkan", "barkin", "barlas", "basar", "basri", "battal", "baturalp",
            "bayar", "baybars", "bayezit", "baykal", "bayraktar", "bedi", "bedrettin", "bedri", "behlul", "behcet",
            "bekdas", "bekir", "bektas", "benan", "bender", "bener", "bengu", "benhur", "bera", "berdan",
            "berge", "berk", "berkan", "berkant", "berke", "berker", "besir", "beyazit", "beytullah", "bilgehan",
            "bilgin", "bircan", "birkan", "birol", "bozkurt", "bugra", "bulut", "bunyamin", "burak", "burhan",
            "cabbar", "cafer", "cagdas", "cagkan", "caglayan", "cahfer", "canberk", "candege", "candel", "candemir",
            "caner", "canip", "cankat", "cankut", "cansin", "cavif", "cavit", "celaleddin", "celil", "cemil",
            "cenap", "cenk", "cesur", "cetin", "cevahir", "cevat", "cevdet", "cevher", "ceyhun", "cezmi",
            "cihad", "cihat", "civan", "comert", "cumali", "cuneyt", "dervis", "devran", "devrim", "dilaver",
            "dincer", "dinc", "diren", "doruk", "dorukhan", "duran", "durmus", "duygu", "edip", "ediz",
            "efe", "efecan", "efekan", "efgan", "ege", "egemen", "ekber", "ekin", "elvan", "emcet",
            "emir", "emirhan", "emrah", "emrullah", "ender", "enes", "engin", "enis", "enver", "eralp",
            "eray", "ercument", "erdinc", "erdi", "eren", "ergin", "ergul", "ergum", "ergus", "erkin",
            "erman", "erol", "ersan", "ersen", "ersoy", "ertan", "ertekin", "erturk", "esad", "esat",
            "esref", "ethem", "evren", "eymen", "eyup", "ezel", "fadli", "fahrettin", "fahri", "faik",
            "faysal", "fazil", "fehmi", "ferda", "ferdi", "feridun", "ferman", "ferruh", "fethi", "fevzi",
            "feyyaz", "feyzullah", "firat", "fuat", "gaffar", "gaffur", "galip", "gani", "garip", "gazi",
            "gediz", "genco", "genc", "gercek", "giray", "gokay", "gokben", "gokberk", "gokcan", "gokce",
            "gokdeniz", "gokhan", "goksel", "goktug", "gokturk", "gorgun", "guclu", "gultekin", "gunay", "gunce",
            "gunduz", "guney", "gungor", "gunhan", "guniz", "gunsel", "gural", "guray", "gurbuz", "gurcan",
            "gurel", "gurhan", "gurkan", "gursel", "guven", "guvenc", "habib", "haci", "hafi", "hakki",
            "haldun", "halim", "halis", "hami", "hamit", "hamdi", "hanefi", "harun", "hasan", "hasbi",
            "hasim", "hasip", "hatay", "hatem", "hayat", "hayati", "hayrettin", "hayri", "hazar", "heper",
            "hifzi", "hilmi", "himmet", "hincal", "hizir", "hulki", "hulusi", "hurriyet", "hursit", "husnu",
            "husrev", "idris", "ihsan", "ikbal", "ilhami", "ilkay", "ilter", "imam", "imran", "inan",
            "inanc", "inci", "irfan", "islam", "ismail", "ismet", "israfil", "izzet", "izzettin", "kagan",
            "kahraman", "kalender", "kamer", "kamil", "karaca", "karan", "kartal", "kasim", "kaya", "kayhan",
            "kayra", "kazim", "kemalettin", "kerim", "keskin", "kilic", "kirac", "kivanc", "koksal", "koray",
            "korcan", "korkut", "koyun", "kudret", "kunter", "kurtulus", "kutay", "kutlu", "kuzey", "lacin",
            "latif", "lemi", "lokman", "lutfi", "lutfu", "macit", "mahir", "maksut", "malik", "mansur",
            "mazhar", "mazlum", "mecnun", "medet", "mehdi", "mekin", "melik", "memduh", "memet", "menderes",
            "mengu", "mertcan", "mervan", "mesih", "metehan", "metin", "mevlut", "midhat", "miran", "mirkelam",
            "mirza", "mithat", "muammer", "mucahit", "mucip", "muderris", "mufit", "muhammet", "muhiddin", "muhlis",
            "muhtesem", "mukted", "mumin", "mumtaz", "munir", "murathan", "mursel", "mursit", "murtaza", "muslum",
            "mustafa", "mutlu", "muzaffer", "naci", "nadi", "nadir", "nafiz", "nail", "naim", "namik",
            "nasir", "nasuh", "nasuh", "navi", "nayil", "nazif", "nazmi", "nebi", "necati", "necdet",
            "necdet", "necip", "nedim", "nefes", "nefis", "nejat", "neset", "nesim", "nevzat", "nezih",
            "nida", "nihat", "niihat", "nizam", "nizami", "noyan", "numan", "nuri", "nursel", "nusret",
            "ogunc", "oguz", "okan", "okyanus", "olcay", "olgun", "omer", "omur", "onal", "onay",
            "oner", "ongun", "onur", "oral", "oray", "orcun", "orkun", "orkut", "oruc", "osman",
            "ozan", "ozay", "ozbek", "ozcan", "ozdemir", "ozer", "ozgen", "ozgur", "ozkan", "ozmen",
            "oztekin", "ozturk", "pamir", "pasa", "peker", "peyami", "polat", "poyraz", "rafet", "ragip",
            "rahim", "rahmi", "raif", "ramazan", "rami", "ramiz", "rasim", "rasit", "rauf", "recai",
            "refik", "reha", "remzi", "resat", "resul", "ridvan", "rifat", "rifki", "riza", "robin",
            "ruhi", "rusen", "rustu", "ruzgar", "saadettin", "sabahattin", "sabri", "sadettin", "sadi", "sadik",
            "sadri", "sadullah", "saffet", "said", "sait", "sakin", "salim", "salman", "sami", "samih",
            "samim", "saner", "sanli", "sarp", "sarper", "satilmis", "savni", "saygin", "sayit", "sebahattin",
            "seckin", "seda", "sedat", "sefa", "sefer", "sefik", "sehmus", "selahattin", "selcuk", "selim",
            "selman", "semih", "senih", "senol", "seracettin", "serdar", "seren", "sergenc", "serhan", "serhat",
            "serkan", "sermet", "sertac", "sertan", "server", "servet", "settar", "seyfettin", "seyfi", "seyfullah",
            "seyit", "seymen", "seyyid", "sezai", "sezgin", "sidki", "sinasi", "sirri", "soner", "soydan",
            "soyer", "suat", "suavi", "suayip", "suha", "suphi", "tacettin", "tahir", "taif", "talat",
            "talha", "talip", "tamer", "tan", "tanju", "tankut", "tarkan", "taskin", "tayfur", "tayyar",
            "tayyip", "tekalp", "tekin", "temucin", "teoman", "tercan", "tevfik", "tevhit", "tezcan", "tijen",
            "timucin", "timur", "togan", "tolga", "tolgahan", "tolunay", "toprak", "toros", "toygar", "toygun",
            "tufan", "tugay", "tugberk", "tugrul", "tugtekin", "tuna", "tunahan", "tunay", "tunc", "tuncay",
            "tuncer", "turan", "turgay", "turgut", "turhan", "turkay", "turker", "tutku", "ufuk", "ugur",
            "ulas", "uluc", "ulvi", "umit", "ummet", "umran", "unal", "unay", "unsal", "ural",
            "uras", "usame", "utku", "uvey", "uygar", "uzeyir", "vahap", "vahdet", "vahit", "varol",
            "vedat", "vefa", "vehbi", "veli", "veysi", "volkan", "vural", "yahya", "yakup", "yalcin",
            "yalin", "yaman", "yank", "yanki", "yasar", "yasin", "yavuz", "yekta", "yener", "yigit",
            "yildirim", "yilmaz", "yucel", "yuksel", "yusuf", "zafer", "zahit", "zekai", "zekeriya", "zeki",
            "zeynel", "zihni", "ziya", "ziyattin", "zulkuf",
            
            # Yabancı Erkek İsimleri (Popüler - Genişletilmiş)
            "john", "michael", "david", "james", "robert", "william", "daniel", "joseph", "mark", "paul",
            "liam", "noah", "oliver", "elijah", "lucas", "mason", "logan", "ethan", "jacob", "jackson",
            "aiden", "matthew", "samuel", "sebastian", "alexander", "owen", "carter", "jayden", "wyatt", "gabriel",
            "julian", "mateo", "anthony", "joshua", "christopher", "andrew", "theodore", "caleb", "ryan", "asher",
            "nathan", "thomas", "leo", "isaiah", "charles", "josiah", "hudson", "christian", "hunter", "connor",
            "eli", "ezra", "aaron", "landon", "adrian", "jonathan", "nolan", "jeremiah", "easton", "elias",
            "colton", "cameron", "carson", "robert", "angel", "maverick", "nicholas", "dominic", "jaxson", "greyson",
            "adam", "ian", "austin", "santiago", "jordan", "cooper", "brayden", "roman", "evan", "zekiel",
            "richard", "charles", "thomas", "steven", "patrick", "brian", "kevin", "ronald", "george", "edward",
            "stephen", "kenneth", "jeffrey", "jason", "frank", "gary", "timothy", "jose", "larry", "scott",
            "eric", "jerry", "dennis", "walter", "peter", "douglas", "henry", "carl", "arthur", "raymond",
            "gregory", "roger", "albert", "terry", "lawrence", "sean", "ralph", "jack", "billy", "bruce",
            "bryan", "eugene", "louis", "wayne", "alan", "juan", "philip", "russell", "vincent", "roy",
            "bobby", "johnny", "bradley"
        }
        
        self.female_keywords = [
            "anne", "mom", "mother", "wife", "girl", "kız", "bayan", "lady", "woman", "queen", "prenses",
            "makeup", "beauty", "moda", "fashion", "gelin", "bride", "sister", "abla", "teyze", "hala",
            "model", "actress", "aktris", "oyuncu", "blogger", "influencer", "stil", "style", "love",
            "estetik", "güzellik", "butik", "eşarp", "tesettür", "hijab", "nurse", "hemşire", "teacher",
            "öğretmen", "student", "öğrenci", "designer", "tasarımcı", "make-up", "kuaför", "hair",
            "nail", "tırnak", "bakım", "cilt", "skin", "diet", "diyet", "yoga", "pilates", "dance", "dans",
            "art", "sanat", "coffee", "kahve", "cat", "kedi", "book", "kitap", "travel", "gezi", "blog",
            "eczacı", "pharmacist", "dr", "dyt", "psk", "av", "lawyer", "mimar", "architect", "engineer",
            "mühendis", "vet", "veteriner", "bio", "biyolog", "kimyager", "chemist", "artist", "ressam",
            "singer", "şarkıcı", "musician", "müzisyen", "writer", "yazar", "poet", "şair", "cook", "aşçı",
            "chef", "şef", "mother of", "annesi", "wife of", "eşi", "mom of", "aunt", "grandma", "babaanne",
            "anneanne", "kızım", "oğlum", "canım", "aşkım", "huzurum", "mutluluğum", "my world", "my life"
        ]
        
        self.male_keywords = [
            "baba", "dad", "father", "husband", "boy", "erkek", "man", "king", "prens", "bey", "adam",
            "brother", "abi", "dayı", "amca", "fitness", "gym", "bodybuilding", "spor", "sport", "football",
            "futbol", "basketball", "basketbol", "gamer", "oyuncu", "engineer", "mühendis", "car", "araba",
            "motor", "motorcycle", "business", "iş", "boss", "patron", "ceo", "founder", "kurucu",
            "barber", "berber", "sakal", "beard", "fenerbahçe", "galatasaray", "beşiktaş", "trabzonspor",
            "boxing", "boks", "kickboxing", "mma", "fighter", "dövüşçü", "soldier", "asker", "polis",
            "police", "pilot", "captain", "kaptan", "driver", "şoför", "mechanic", "tamirci", "technician",
            "teknisyen", "electrician", "elektrikçi", "plumber", "tesisatçı", "carpenter", "marangoz",
            "father of", "babası", "husband of", "kocası", "dad of", "uncle", "grandpa", "dede",
            "fitness coach", "antrenör", "coach", "manager", "menajer", "director", "yönetmen", "producer",
            "yapımcı", "developer", "yazılımcı", "coder", "kodlama", "hacker", "security", "güvenlik",
            "bodyguard", "koruma", "hunter", "avcı", "fisherman", "balıkçı", "sailor", "denizci"
        ]
        
        self.turkish_chars = "çğıöşüÇĞİÖŞÜ"
        self.turkish_keywords = [
            "ve", "ile", "ben", "sen", "biz", "için", "çok", "ama", "fakat", "lakin", "istanbul", "ankara", "izmir",
            "türkiye", "turkey", "dm", "iletişim", "sipariş", "gezgin", "mimar", "doktor", "avukat", "mühendis"
        ]

    def normalize_turkish_chars(self, text):
        """Türkçe karakterleri İngilizce karşılıklarına dönüştürür."""
        if not text:
            return ""
        replacements = {
            'ç': 'c', 'Ç': 'c',
            'ğ': 'g', 'Ğ': 'g',
            'ı': 'i', 'I': 'i', 'İ': 'i',
            'ö': 'o', 'Ö': 'o',
            'ş': 's', 'Ş': 's',
            'ü': 'u', 'Ü': 'u'
        }
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        return text

    def clean_text(self, text):
        if not text:
            return ""
        return text.lower().strip()

    def predict_gender(self, fullname, bio, username=""):
        """
        Geri dönüş: 'female', 'male', veya 'unknown'
        """
        score = 0 # Pozitif: Kadın, Negatif: Erkek
        
        fullname_lower = self.clean_text(fullname)
        bio_lower = self.clean_text(bio)
        username_lower = self.clean_text(username)
        
        # 1. İsim Analizi (Fullname)
        # İsimdeki Türkçe karakterleri normalize et (örn: Büşra -> busra)
        normalized_name = self.normalize_turkish_chars(fullname_lower)
        
        names = normalized_name.split()
        for name in names:
            # Sadece harflerden oluşan kısımları al
            name_clean = re.sub(r'[^a-z]', '', name)
            if len(name_clean) < 2: continue
            
            if name_clean in self.female_names:
                score += 3
            elif name_clean in self.male_names:
                score -= 3
        
        # 2. İsim Analizi (Username - Eğer Fullname'den sonuç çıkmazsa veya desteklemek için)
        # Username içindeki isimleri yakalamaya çalış (örn: ayse_yilmaz -> ayse)
        # Genelde username'de _ veya . ile ayrılır
        username_parts = re.split(r'[._0-9]', username_lower)
        for part in username_parts:
            part_clean = self.normalize_turkish_chars(part)
            part_clean = re.sub(r'[^a-z]', '', part_clean)
            if len(part_clean) < 2: continue
            
            if part_clean in self.female_names:
                score += 2 # Username daha az güvenilir olabilir, puanı düşük tut
            elif part_clean in self.male_names:
                score -= 2

        # 3. Bio Anahtar Kelime Analizi
        for kw in self.female_keywords:
            if kw in bio_lower:
                score += 2
                
        for kw in self.male_keywords:
            if kw in bio_lower:
                score -= 2
        
        if score > 0:
            return "female"
        elif score < 0:
            return "male"
        else:
            return "unknown"

    def predict_nationality(self, fullname, bio):
        """
        Geri dönüş: 'turkish', 'foreign', veya 'unknown'
        """
        # Türkçe karakter kontrolü (En güçlü kanıt)
        full_text = (fullname + " " + bio)
        for char in self.turkish_chars:
            if char in full_text:
                return "turkish"
                
        text_lower = self.clean_text(full_text)
        
        # Türkçe kelime kontrolü
        tk_score = 0
        for kw in self.turkish_keywords:
            if f" {kw} " in f" {text_lower} ": # Tam kelime eşleşmesi
                tk_score += 1
                
        if tk_score > 0:
            return "turkish"
            
        # Varsayılan olarak emin değilsek unknown, 
        # ama genelde Türkçe karakter/kelime yoksa foreign kabul edilebilir (riskli)
        return "foreign" if tk_score == 0 else "unknown"

    def analyze(self, user_info):
        """
        user_info sözlüğü: {'username': '...', 'fullname': '...', 'bio': '...'}
        """
        fullname = user_info.get('fullname', '')
        bio = user_info.get('bio', '')
        username = user_info.get('username', '')
        
        return {
            "gender": self.predict_gender(fullname, bio, username),
            "nationality": self.predict_nationality(fullname, bio)
        }
