import re


def is_roman_number(num):  # checks if a string is a Roman numeral
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


integers = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_arabic(roman):  # converts Roman numerals to Arabic numerals
    roman = roman.upper()
    result = 0
    for i, _c in enumerate(roman):
        if i + 1 < len(roman) and integers[roman[i]] < integers[roman[i + 1]]:
            result -= integers[roman[i]]
        else:
            result += integers[roman[i]]
    return str(result)


def removing_extra_zeros(second_part):
    end = len(second_part)
    rez = ""
    if second_part[0].isdigit():
        for i in range(end):
            if (second_part[i] != "0") or ((i + 1 < end) and (second_part[i + 1] == "." or second_part[i + 1] == ",")):
                rez = second_part[i:]
                break
    elif second_part[0] in ("+", "-"):
        sign_symbol = second_part[0]

        for i in range(len(sign_symbol), end):
            if second_part[i] != "0" or ((i + 1 < end) and (second_part[i + 1] == "." or second_part[i + 1] == ",")):
                rez = second_part[i:]
                break

        rez = sign_symbol + rez
    else:
        rez = second_part
    end = len(rez)
    for i in range(1, end):
        if rez[i] == "+":
            for j in range(i + 1, end):
                if rez[j] != "0" or ((j + 1 < end) and (rez[j + 1] == "." or rez[j + 1] == ",")):
                    rez = rez[:i] + "+" + rez[j:]
                    break
            break
        if rez[i] == "-":
            for j in range(i + 1, end):
                if rez[j] != "0" or ((j + 1 < end) and (rez[j + 1] == "." or rez[j + 1] == ",")):
                    rez = rez[:i] + "-" + rez[j:]
                    break
            break
    return rez


reduction = {
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


class GeneralizeNameUseCase:
    """
    Given arbitrary name, transforms it to standard representation (removing abbreviation, trailing zeros, etc)
    """

    def invoke(self, source: str) -> str:
        request = source.split()
        name = ""
        index = ""
        end_name = 0

        if len(request) == 1:  # if there are no spaces in the request
            if request[0][:3].lower() in ("2df", "6df"):
                name = request[0][:3]
                end_name = 3
            else:
                for i in range(len(request[0])):
                    if not request[0][i].isalpha():  # define the end of the nominal part
                        if i > 0 and request[0][i - 1].lower() == "j":
                            name = request[0][: i - 1]  # write all the letters on the left into the nominal part
                            end_name = i - 1
                            break
                        if i == 0:
                            continue
                        name = request[0][:i]  # write all the letters on the left into the nominal part
                        end_name = i
                        break
                if name == "":
                    for i in range(len(request[0])):
                        if request[0][:i].lower() in reduction and is_roman_number(request[0][i:]):
                            name = request[0][:i]  # write all the letters on the left into the nominal part
                            end_name = i
                            break
            second = request[0][end_name:]
            index = removing_extra_zeros(second)

        elif len(request) == 2:  # if the request consists of two parts
            if request[0][0].isalpha():
                if is_roman_number(request[0]):
                    name = request[1]
                    second = request[0]
                else:
                    name = request[0]
                    second = request[1]
            elif request[0].lower() == "6df" or request[0].lower() == "2df":
                name = request[0]
                second = request[1]
            else:
                name = request[1]
                second = request[0]

            if is_roman_number(second):
                index = roman_to_arabic(second)
            elif name.upper() == "ESO-LV":
                second = second.replace("-", "").replace("+", "")
                index = removing_extra_zeros(second)
            else:
                index = removing_extra_zeros(second)

        elif len(request) == 3:
            if request[0][0].isalpha():
                if is_roman_number(request[0]):
                    if request[1].isalpha():
                        name = roman_to_arabic(request[0]) + request[1]
                        second = request[2]
                    else:
                        name = request[0] + request[2]
                        second = request[1]
                elif request[0].lower() == "lu" and request[1].lower() == "yc":
                    name = request[0] + " " + request[1]
                    second = request[2]
                elif is_roman_number(request[1]):
                    name = roman_to_arabic(request[1]) + request[0]
                    second = request[2]
                else:
                    name = request[0]
                    second = request[1] + request[2]
            else:
                name = request[0]
                second = request[1] + request[2]
            index = removing_extra_zeros(second)

        elif len(request) == 4:
            if request[0][0].isalpha():
                if is_roman_number(request[0]):
                    if request[1][0].isalpha():
                        name = roman_to_arabic(request[0]) + request[1]
                        second = request[2]
                    else:
                        name = request[0] + request[2]
                        second = request[1]
                elif is_roman_number(request[1]):
                    name = roman_to_arabic(request[1]) + request[0]
                    second = request[2]
                else:
                    name = request[0]
                    second = request[1] + request[3]
            else:
                name = request[0]
                second = request[1] + request[2] + request[3]
            index = removing_extra_zeros(second)

        if name.lower() in reduction:
            name = reduction[name.lower()]
        else:
            name = name.upper()

        if is_roman_number(index):
            index = roman_to_arabic(index)

        return name + " " + index.upper().replace(",", ".")
