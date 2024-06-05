import re

def is_roman_number(num):  # checks if a string is a Roman numeral
    num = num.upper()
    pattern = re.compile(r"""   
                                ^M{0,3}
                                (CM|CD|D?C{0,3})?
                                (XC|XL|L?X{0,3})?
                                (IX|IV|V?I{0,3})?$
            """, re.VERBOSE)
    if re.match(pattern, num):
        return True
    return False


integers = dict(I=1, V=5, X=10, L=50, C=100, D=500, M=1000)


def roman_to_arabic(roman):  # converts Roman numerals to Arabic numerals
    roman = roman.upper()
    result = 0
    for i, c in enumerate(roman):
        if i + 1 < len(roman) and integers[roman[i]] < integers[roman[i + 1]]:
            result -= integers[roman[i]]
        else:
            result += integers[roman[i]]
    return str(result)

class GeneralizeNameUseCase:
    """
    Given arbitrary name, transforms it to standard representation (removing abbreviation, trailing zeros, etc)
    """
    def invoke(self, source: str) -> str:
        request = source.split()
        name = ''
        index = ''
        end_name = 0
        reduction = \
            {'acg': 'ACG', 'acsrg': 'ACSRG', 'acsvcs': 'ACSVCS', 'adbs': 'ADBS', 'agc': 'AGC', 'akn': 'Arakelian',
             'aless': 'ALESS', 'alfa zoa': 'ALFA ZOA', 'and': 'Andromeda', 'anon': 'Anonymous', 'antl': 'ANTL', 'apg':
                 'APG', 'ark': 'Arakelian', 'asp03': 'ASP03', 'asxdf': 'ASXDF', 'atcdfs': 'ATCDFS', 'auds': 'AUDS',
             'awm': 'AWM', 'b-hizeles': 'B-HiZELES', 'bbh': 'BBH', 'bee': 'BEE', 'bes': 'BES', 'bfw78': 'BFW78', 'bgem':
                 'BGEM', 'bglo': 'BGLO', 'bgp': 'BGP', 'bhi': 'BHI', 'big': 'BIG', 'bk': 'BK', 'bk85': 'BK85', 'bkk':
                 'BKK', 'boi': 'BOI', 'boka': 'BoKa', 'borg': 'Borg', 'bow': 'BOW', 'bss': 'BSS', 'bta91': 'BTA91',
             'bts': 'BTS', 'bwsh': 'BWSH', 'cairns': 'CAIRNS', 'cap': 'CAP', 'cas': 'Cassiopeia', 'caseg': 'CasG',
             'casg': 'CasG', 'ccc': 'CCC', 'ccos': 'CCOS', 'cemm': 'CEMM', 'cfdf': 'CFDF', 'cg': 'CG', 'cgcg': 'CGCG',
             'cgf': 'CGF', 'cgmw': 'CGMW', 'cgpg': 'CGPG', 'cgrabs': 'CGRaBS', 'clash': 'CLASH', 'clashvlt': 'CLASHVLT',
             'cn': 'CN', 'cnoc': 'CNOC', 'cnoc2': 'CNOC2', 'coldz': 'COLDz', 'comacc': 'ComaCC', 'comafc': 'ComaFC',
             'cop': 'COP', 'cosmos': 'COSMOS', 'cpga': 'CPGA', 'crgc': 'RGC', 'csrg': 'CSRG', 'cuys': 'CUYS', 'cwat':
                 'CWAT', 'd0k': 'D0K', 'dc': 'DC', 'dcaz94': 'dCAZ94', 'ddo': 'DDO', 'deep-gss': 'DEEP-GSS', 'deep2':
                 'DEEP2', 'deep2-grs': 'DEEP2-GRS', 'denisp': 'DENISP', '2dfgrs': '2dFGRS', '6dfgs': '6dFGS', 'dls':
                 'DLS', 'dr5egal': 'dr5EGal', 'dr5ngal': 'dr5NGal', 'dragons': 'DRaGONS', 'dugrs': 'DUGRS', 'dukst':
                 'DUKST', 'dzoa': 'DZOA', 'ead': 'EAD', 'eco': 'ECO', 'edcs': 'EDCS', 'edsgc': 'EDSGC', 'ees': 'EES',
             'egips': 'EGIPS', 'egnog': 'EGNoG', 'egsd2': 'EGSD2', 'eirs': 'EIRS', 'elars': 'ELARS', 'enacs': 'ENACS',
             'eon': 'EON', 'esdo': 'ESDO', 'esis': 'ESIS', 'eso-lv': 'ESO-LV', 'esp': 'ESP', 'euc2020': 'EUC2020',
             'evcc': 'EVCC', 'ey': 'EY', 'ezoa': 'EZOA', 'f03g': 'F03G', 'fcc': 'FCC', 'fcg': 'FCG', 'ff': 'FF', 'fgc':
                 'FGC', 'fgca': 'FGCA', 'fgce': 'FGCE', 'fh': 'FH', 'fi': 'FI', 'figs': 'FIGS', 'flash': 'FLASH',
             'flsbg': 'FLSBG', 'fm': 'FM', 'fri': 'Fairall', 'fsa': 'FSA', 'fsao': 'FSAO', 'fsg': 'FSG', 'fsw': 'FSW',
             'gabods': 'GaBoDs', 'gal': 'GAL', 'gama': 'GAMA', 'gass': 'GASS', 'gb': 'GB', 'gdds': 'GDDS', 'gems':
                 'GEMS', 'gh': 'GH', 'gin': 'GIN', 'glare': 'GLARE', 'glxy': 'GLXY', 'gmass': 'GMASS', 'gmp': 'GMP',
             'gna': 'GNA', 'gnb': 'GNB', 'gnh': 'GNH', 'gns': 'GNS', 'gnx': 'GNX', 'gny': 'GNY', 'gnz': 'GNZ', 'goods':
                 'GOODS', 'goods-music': 'GOODS-MUSIC', 'gp': 'GP', 'grdg': 'GRDG', 'gsa': 'GSA', 'gsan': 'GSAN', 'gsd':
                 'GSD', 'gsf': 'GSF', 'gsg': 'GSG', 'gsi': 'GSI', 'gsm': 'GSM', 'gsn': 'GSN', 'gsp': 'GSP', 'gsw': 'GSW'
                , 'hag': 'HAG', 'hcc': 'HCC', 'hcg': 'HCG', 'hcw': 'HCW', 'hdfff': 'HDFFF', 'herbs': 'HerBS', 'hermes':
                 'HERMES', 'hhic': 'LEDA', 'hic': 'LEDA', 'hijass': 'HIJASS', 'hipeq': 'HIPEQ', 'hippies': 'HIPPIES',
             'hizela': 'HiZELS', 'hizoa': 'HIZOA', 'hizss': 'HIZSS', 'hkk': 'HKK', 'hls': 'HLS', 'hnm': 'HNM', 'ho':
                 'Holmberg', 'holm': 'Holmberg', 'hps': 'HPS', 'hpw': 'HPW', 'hq': 'HQ', 'hrg': 'HRG', 'hrs': 'HRS',
             'hsdf': 'hSDF', 'hvs': 'HVS', 'hz': 'Herzog', 'iero': 'IERO', 'iggc': 'IGGC', 'ikpm': 'IKPM', 'iok': 'IOK',
             'isg': 'ISG', 'isi96': 'ISI96', 'jb': 'JB', 'jingle': 'JINGLE', 'jj': 'JJ', 'jkb': 'JKB', 'k20s': 'K20S',
             'k68': 'K68', 'k72': 'K72', 'k73': 'K73', 'k79': 'K79', 'ka': 'Kazarian', 'kaz': 'Kazarian', 'kaza':
                 'Kazarian', 'kdg': 'K68', 'kesr': 'KESR', 'kges': 'KGES', 'khbg': 'KHBG', 'khg': 'KHG', 'kiss': 'KISS',
              'kissb': 'KISSB', 'kissbx': 'KISSBx', 'kissr': 'KISSR', 'kissrx': 'KISSRx', 'klem': 'Klemola', 'kos':
                 'KOS', 'koss': 'KOSS', 'kpg': 'KPG', 'kross': 'KROSS', 'n': 'NGC', 'ngc': 'NGC', 'u': 'UGC', 'ugc':
                 'UGC', 'ua': 'UGCA', 'ugca': 'UGCA', 'leda': 'PGC', 'p': 'PGC', 'pgc': 'PGC', 'eso': 'ESO', 'vir':
                 'Virgo'}

        if len(request) == 1:  # if there are no spaces in the request
            for i in range(len(request[0])):
                if not request[0][i].isalpha():  # define the end of the nominal part
                    name = request[0][:i]  # write all the letters on the left into the nominal part
                    end_name = i - 1
                    break
            for i in range(end_name + 1, len(request[0])):
                if request[0][i] != '0':
                    index = request[0][i:]  # the rest in the second
                    break
                elif request[0][i + 1] == '.' or request[0][i + 1] == ',':
                    index = request[0][i:]
                    break
            if index[0] == '+':
                for i in range(1, len(index)):
                    if index[i] != '0':
                        index = '+' + index[i:]
                        break
                    elif index[i + 1] == '.' or index[i + 1] == ',':
                        index = '+' + index[i:]
                        break
            if index[0] == '-':
                for i in range(1, len(index)):
                    if index[i] != '0':
                        index = '-' + index[i:]
                        break
                    elif index[i + 1] == '.' or index[i + 1] == ',':
                        index = '-' + index[i:]
                        break

        elif len(request) == 2:  # if the request consists of two parts
            if request[0].isalpha():
                if is_roman_number(request[0]):
                    name = request[1]
                    second = request[0]
                else:
                    name = request[0]
                    second = request[1]
            else:
                name = request[1]
                second = request[0]

            if is_roman_number(second):
                index = roman_to_arabic(second)
            elif second[0].isdigit():
                for i in range(len(second)):
                    if second[i] != '0':
                        index = second[i:]
                        break
                    elif second[i + 1] == '.' or second[i + 1] == ',':
                        index = second[i:]
                        break
            elif second[0] == '+':
                for i in range(1, len(second)):
                    if second[i] != '0':
                        index = '+' + second[i:]
                        break
                    elif second[i + 1] == '.' or second[i + 1] == ',':
                        index = '+' + second[i:]
                        break
            elif second[0] == '-':
                for i in range(1, len(second)):
                    if second[i] != '0':
                        index = '-' + second[i:]
                        break
                    elif second[i + 1] == '.' or second[i + 1] == ',':
                        index = '-' + second[i:]
                        break
            else:
                index = second

        if name.lower() in reduction:
            name = reduction[name.lower()]
        else:
            name = name.capitalize()

        request_convert = name + ' ' + index

        return request_convert

