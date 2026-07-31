class Common:
    PGC = "pgc"


class Designation:
    PGC = Common.PGC
    DESIGN = "design"


class ICRS:
    PGC = Common.PGC
    RA = "ra"
    E_RA = "e_ra"
    DEC = "dec"
    E_DEC = "e_dec"


class Redshift:
    PGC = Common.PGC
    CZ = "cz"
    E_CZ = "e_cz"


class Nature:
    PGC = Common.PGC
    TYPE_NAME = "type_name"
