import re


def _is_roman_number(num):
    """
    Checks if a string is a Roman numeral
    """
    num = num.upper()
    pattern = re.compile(
        r"""   
                                ^M{0,3}
                                (CM|CD|D?C{0,3})?
                                (XC|XL|L?X{0,3})?
                                (IX|IV|V?I{0,3})?$
            """,
        re.VERBOSE,
    )
    if re.match(pattern, num):
        return True
    return False


_integers = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _roman_to_arabic(roman):
    """
    Converts Roman numerals to Arabic numerals
    """
    roman = roman.upper()
    result = 0
    for i in range(len(roman)):
        if i + 1 < len(roman) and _integers[roman[i]] < _integers[roman[i + 1]]:
            result -= _integers[roman[i]]
        else:
            result += _integers[roman[i]]
    return str(result)


def _removing_extra_zeros(second_part):
    end = len(second_part)
    rez = ""
    if second_part[0].isdigit():
        prefix = ""
    elif second_part[0] in ("+", "-"):
        prefix = second_part[0]
    else:
        prefix = second_part

    for i in range(len(prefix), end):
        if second_part[i] != "0" or ((i + 1 < end) and (second_part[i + 1] == "." or second_part[i + 1] == ",")):
            rez = second_part[i:]
            break
    rez = prefix + rez
    end = len(rez)
    for i in range(1, end):
        if rez[i] in ("+", "-"):
            for j in range(i + 1, end):
                if rez[j] != "0" or ((j + 1 < end) and (rez[j + 1] == "." or rez[j + 1] == ",")):
                    rez = rez[: i + 1] + rez[j:]
                    break
            break
    return rez


_reduction = {
    "2df": "2dF",
    "2dfgrs": "2dFGRS",
    "2masx1": "2MASXI",
    "6df": "6dF",
    "6dfgs": "6dFGS",
    "aguero": "Aguero",
    "akn": "Ark",
    "andromeda": "Andromeda",
    "and": "Andromeda",
    "anon": "Anon",
    "ant": "Antlia",
    "antlia": "Antlia",
    "aps": "Apus",
    "apus": "Apus",
    "aqr": "Aquarius",
    "aquarius": "Aquarius",
    "aql": "Aquila",
    "aquila": "Aquila",
    "ara": "Ara",
    "ari": "Aries",
    "aries": "Aries",
    "ark": "Ark",
    "arm": "Arm",
    "aur": "Auriga",
    "auriga": "Auriga",
    "aztec": "AzTEC",
    "b-hizeles": "B-HiZELES",
    "boka": "BoKa",
    "boo": "Bootes",
    "bootes": "Bootes",
    "borg": "BoRG",
    "bss": "SBSG",
    "cae": "Caelum",
    "caelum": "Caelum",
    "cam": "Camelopardalis",
    "cambridge": "Cambridge",
    "camelopardalis": "Camelopardalis",
    "cancer": "Cancer",
    "cap": "Capricornus",
    "capricornus": "Capricornus",
    "car": "Carina",
    "carina": "Carina",
    "cas": "Cassiopeia",
    "cassiopeia": "Cassiopeia",
    "caseg": "CasG",
    "casg": "CasG",
    "cen": "Centaurus",
    "centaurus": "Centaurus",
    "cep": "Cepheus",
    "cepheus": "Cepheus",
    "cet": "Cetus",
    "cetus": "Cetus",
    "cgcg": "Z",
    "cgrabs": "CGRaBS",
    "cha": "Chamaleon",
    "chamaleon": "Chamaleon",
    "cir": "Circinus",
    "circinus": "Circinus",
    "cma": "Canis Major",
    "cmi": "Canis Minor",
    "cnc": "Cancer",
    "col": "Columba",
    "coldz": "COLDz",
    "columba": "Columba",
    "com": "Coma Berenices",
    "comacc": "ComaCC",
    "comafc": "ComaFC",
    "corvus": "Corvus",
    "cowie": "Cowie",
    "cpga": "AM",
    "cra": "Corona Australis",
    "crater": "Crater",
    "crb": "Corona Borealis",
    "crgc": "RGC",
    "crt": "Crater",
    "cru": "Crux",
    "crux": "Crux",
    "crv": "Corvus",
    "cvn": "Canes Venatici",
    "cyg": "Cygnus",
    "cygnus": "Cygnus",
    "dcaz94": "dCAZ94",
    "del": "Delphinus",
    "delphinus": "Delphinus",
    "dickinson": "HNM",
    "dor": "Dorado",
    "dorado": "Dorado",
    "dr5egal": "dr5EGal",
    "dr5ngal": "dr5NGal",
    "dra": "Draco",
    "draco": "Draco",
    "dragons": "DRaGONS",
    "dukst": "DUGRS",
    "dwingeloo": "Dwingeloo",
    "egnog": "EGNoG",
    "equ": "Equuleus",
    "equuleus": "Equuleus",
    "eri": "Eridanus",
    "eridanus": "Eridanus",
    "for": "Fornax",
    "fornax": "Fornax",
    "frl": "Frl",
    "gabods": "GaBoDS",
    "gem": "Gemini",
    "gemini": "Gemini",
    "gru": "Grus",
    "grus": "Grus",
    "gwyn": "Gwyn",
    "her": "Hercules",
    "herbs": "HerBS",
    "hercules": "Hercules",
    "hhic": "PGC",
    "hic": "PGC",
    "hizels": "HiZELS",
    "holmberg": "Holmberg",
    "ho": "Holmberg",
    "holm": "Holmberg",
    "hor": "Horologium",
    "horologium": "Horologium",
    "hsdf": "hSDF",
    "hya": "Hydra",
    "hydra": "Hydra",
    "hydrus": "Hydrus",
    "hyi": "Hydrus",
    "hz": "Hz",
    "ind": "Indus",
    "indus": "Indus",
    "k72": "KPG",
    "ka": "Ka",
    "kaz": "Ka",
    "kaza": "Ka",
    "kdg": "K68",
    "kissbx": "KISSBx",
    "kissrx": "KISSRx",
    "klem": "Klem",
    "lac": "Lacerta",
    "lacerta": "Lacerta",
    "leda": "PGC",
    "leo": "Leo",
    "lep": "Lepus",
    "lepus": "Lepus",
    "lib": "Libra",
    "libra": "Libra",
    "lmi": "Leo Minor",
    "lu yc": "Lu YC",
    "lup": "Lupus",
    "lupus": "Lupus",
    "lyn": "Lynx",
    "lynx": "Lynx",
    "lyr": "Lyra",
    "lyra": "Lyra",
    "macsg": "MACSg",
    "mailyan": "Mailyan",
    "malin": "Malin",
    "mark": "Mrk",
    "markarian": "Mrk",
    "men": "Mensa",
    "mensa": "Mensa",
    "mic": "Microscopium",
    "microscopium": "Microscopium",
    "mkn": "Mrk",
    "mon": "Monoceros",
    "monoceros": "Monoceros",
    "mrk": "Mrk",
    "mus": "Musca",
    "musca": "Musca",
    "n": "NGC",
    "nhzg": "NHzG",
    "nor": "Norma",
    "norma": "Norma",
    "oct": "Octans",
    "octans": "Octans",
    "oph": "Ophiucus",
    "ophiucus": "Ophiucus",
    "ori": "Orion",
    "orion": "Orion",
    "p": "PGC",
    "pav": "Pavo",
    "pavo": "Pavo",
    "peg": "Pegasus",
    "pegasus": "Pegasus",
    "per": "Perseus",
    "perseus": "Perseus",
    "phe": "Phoenix",
    "phoenix": "Phoenix",
    "pic": "Pictor",
    "pictor": "Pictor",
    "pisces": "Pisces",
    "psa": "Pisces Austrinus",
    "pup": "Puppis",
    "puppis": "Puppis",
    "psc": "Pisces",
    "pyx": "Pyxis",
    "pyxis": "Pyxis",
    "reiz": "Reiz",
    "ret": "Reticulum",
    "reticulum": "Reticulum",
    "sagitta": "Sagitta",
    "sagittarius": "Sagittarius",
    "sawicki": "Sawicki",
    "sborg": "sBoRG",
    "sbs": "SBSG",
    "sbsss": "SBSG",
    "scl": "Sculptor",
    "sco": "Scorpius",
    "scorpius": "Scorpius",
    "sct": "Scutum",
    "sculptor": "Sculptor",
    "scutum": "Scutum",
    "ser": "Serpens",
    "serpens": "Serpens",
    "sex": "Sextans",
    "sextans": "Sextans",
    "sge": "Sagitta",
    "sgr": "Sagittarius",
    "shizels": "SHiZELS",
    "shk": "Shk",
    "skk97": "SKK98",
    "ssrs2": "GSC",
    "super8": "Super8",
    "tau": "Taurus",
    "taurus": "Taurus",
    "tel": "Telescopium",
    "telescopium": "Telescopium",
    "thg": "ThG",
    "tol": "Tol",
    "tra": "Triangulum Australe",
    "tri": "Triangulum",
    "triangulum": "Triangulum",
    "tuc": "Tucana",
    "tucanac": "Tucana",
    "u": "UGC",
    "ua": "UGCA",
    "ugcg": "UGC",
    "uma": "Ursa Major",
    "umi": "Ursa Minor",
    "vel": "Vela",
    "vela": "Vela",
    "vir": "Virgo",
    "virgo": "Virgo",
    "vol": "Volans",
    "volans": "Volans",
    "vul": "Vulpecula",
    "vulpecula": "Vulpecula",
    "was": "Was",
    "wein": "Weinberger",
    "weinberger": "Weinberger",
    "westphal": "Westphal",
    "wigglez": "WiggleZ",
    "wkk97": "WKK98",
    "zcosmos": "zCOSMOS",
    "zw": "Zw",
}


def _rule_len_1(source: str) -> bool:
    return len(source.split()) == 1


def _rule_len_2(source: str) -> bool:
    return len(source.split()) == 2


def _rule_len_3(source: str) -> bool:
    return len(source.split()) == 3


def _rule_len_4(source: str) -> bool:
    return len(source.split()) == 4


def _algorithm_len_1(source: str) -> str:
    request = source.split()
    name = ""
    if request[0][:3].lower() in ("2df", "6df"):
        name = request[0][:3]
    else:
        for i in range(len(request[0])):
            if not request[0][i].isalpha():  # define the end of the nominal part
                if i > 0 and request[0][i - 1].lower() == "j":
                    name = request[0][: i - 1]  # write all the letters on the left into the nominal part
                    break
                if i == 0:
                    continue
                name = request[0][:i]  # write all the letters on the left into the nominal part
                break
        if name == "":
            for i in range(len(request[0])):
                if request[0][:i].lower() in _reduction and _is_roman_number(request[0][i:]):
                    name = request[0][:i]  # write all the letters on the left into the nominal part
                    break
    second = request[0][len(name) :]
    index = _removing_extra_zeros(second)

    if name.lower() in _reduction:
        name = _reduction[name.lower()]
    else:
        name = name.upper()

    if _is_roman_number(index):
        index = _roman_to_arabic(index)

    return name + " " + index.upper().replace(",", ".")


def _algorithm_len_2(source: str) -> str:
    request = source.split()
    if request[0][0].isalpha():
        if _is_roman_number(request[0]):
            name = request[1]
            second = request[0]
        else:
            name = request[0]
            second = request[1]
    elif request[0].lower() in ("2df", "6df"):
        name = request[0]
        second = request[1]
    else:
        name = request[1]
        second = request[0]

    if _is_roman_number(second):
        index = _roman_to_arabic(second)
    elif name.upper() == "ESO-LV":
        second = second.replace("-", "").replace("+", "")
        index = _removing_extra_zeros(second)
    else:
        index = _removing_extra_zeros(second)

    if name.lower() in _reduction:
        name = _reduction[name.lower()]
    else:
        name = name.upper()

    if _is_roman_number(index):
        index = _roman_to_arabic(index)

    return name + " " + index.upper().replace(",", ".")


def _algorithm_len_3(source: str) -> str:
    request = source.split()
    if request[0][0].isalpha():
        if _is_roman_number(request[0]):
            if request[1].isalpha():
                name = _roman_to_arabic(request[0]) + request[1]
                second = request[2]
            else:
                name = request[0] + request[2]
                second = request[1]
        elif request[0].lower() == "lu" and request[1].lower() == "yc":
            name = request[0] + " " + request[1]
            second = request[2]
        elif _is_roman_number(request[1]):
            name = _roman_to_arabic(request[1]) + request[0]
            second = request[2]
        else:
            name = request[0]
            second = request[1] + request[2]
    else:
        name = request[0]
        second = request[1] + request[2]
    index = _removing_extra_zeros(second)

    if name.lower() in _reduction:
        name = _reduction[name.lower()]
    else:
        name = name.upper()

    if _is_roman_number(index):
        index = _roman_to_arabic(index)

    return name + " " + index.upper().replace(",", ".")


def _algorithm_len_4(source: str) -> str:
    request = source.split()
    if request[0][0].isalpha():
        if _is_roman_number(request[0]):
            if request[1][0].isalpha():
                name = _roman_to_arabic(request[0]) + request[1]
                second = request[2]
            else:
                name = request[0] + request[2]
                second = request[1]
        elif _is_roman_number(request[1]):
            name = _roman_to_arabic(request[1]) + request[0]
            second = request[2]
        else:
            name = request[0]
            second = request[1] + request[3]
    else:
        name = request[0]
        second = request[1] + request[2] + request[3]
    index = _removing_extra_zeros(second)

    if name.lower() in _reduction:
        name = _reduction[name.lower()]
    else:
        name = name.upper()

    if _is_roman_number(index):
        index = _roman_to_arabic(index)

    return name + " " + index.upper().replace(",", ".")


_rules = [
    (_rule_len_1, _algorithm_len_1),
    (_rule_len_2, _algorithm_len_2),
    (_rule_len_3, _algorithm_len_3),
    (_rule_len_4, _algorithm_len_4),
]


def generalize_name(source: str) -> str:
    """
    Given arbitrary name, transforms it to standard representation (removing abbreviation, trailing zeros, etc)
    """
    for rule, algorithm in _rules:
        if rule(source):
            return algorithm(source)

    return source
