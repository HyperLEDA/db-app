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
    "6df": "6dF",
    "2df": "2dF",
    "aguero": "Aguero",
    "akn": "Ark",
    "andromeda": "Andromeda",
    "and": "Andromeda",
    "anon": "Anon",
    "ark": "Ark",
    "arm": "Arm",
    "aztec": "AzTEC",
    "b-hizeles": "B-HiZELES",
    "boka": "BoKa",
    "borg": "BoRG",
    "bss": "SBSG",
    "cambridge": "Cambridge",
    "cas": "Cas",
    "caseg": "CasG",
    "casg": "CasG",
    "cgcg": "Z",
    "cgrabs": "CGRaBS",
    "coldz": "COLDz",
    "comacc": "ComaCC",
    "comafc": "ComaFC",
    "cowie": "Cowie",
    "cpga": "AM",
    "crgc": "RGC",
    "dcaz94": "dCAZ94",
    "2dfgrs": "2dFGRS",
    "6dfgs": "6dFGS",
    "dickinson": "HNM",
    "dr5egal": "dr5EGal",
    "dr5ngal": "dr5NGal",
    "dragons": "DRaGONS",
    "dukst": "DUGRS",
    "dwingeloo": "Dwingeloo",
    "egnog": "EGNoG",
    "frl": "Frl",
    "gabods": "GaBoDS",
    "gwyn": "Gwyn",
    "herbs": "HerBS",
    "hhic": "PGC",
    "hic": "PGC",
    "hizels": "HiZELS",
    "holmberg": "Holmberg",
    "ho": "Holmberg",
    "holm": "Holmberg",
    "hsdf": "hSDF",
    "hz": "Hz",
    "k72": "KPG",
    "ka": "Ka",
    "kaz": "Ka",
    "kaza": "Ka",
    "kdg": "K68",
    "kissbx": "KISSBx",
    "kissrx": "KISSRx",
    "klem": "Klem",
    "leda": "PGC",
    "lu yc": "Lu YC",
    "macsg": "MACSg",
    "mailyan": "Mailyan",
    "malin": "Malin",
    "mark": "Mrk",
    "markarian": "Mrk",
    "2masx1": "2MASXI",
    "mkn": "Mrk",
    "mrk": "Mrk",
    "n": "NGC",
    "nhzg": "NHzG",
    "p": "PGC",
    "psc": "Psc",
    "reiz": "Reiz",
    "sawicki": "Sawicki",
    "sborg": "sBoRG",
    "sbs": "SBSG",
    "sbsss": "SBSG",
    "shizels": "SHiZELS",
    "shk": "Shk",
    "skk97": "SKK98",
    "ssrs2": "GSC",
    "super8": "Super8",
    "thg": "ThG",
    "tol": "Tol",
    "u": "UGC",
    "ua": "UGCA",
    "ugcg": "UGC",
    "vir": "Virgo",
    "virgo": "Virgo",
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


class GeneralizeNameUseCase:
    """
    Given arbitrary name, transforms it to standard representation (removing abbreviation, trailing zeros, etc)
    """

    def invoke(self, source: str) -> str:
        for rule, algorithm in _rules:
            if rule(source):
                return algorithm(source)

        return source
