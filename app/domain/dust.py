from astropy.coordinates import SkyCoord
from dustmaps.config import config
from dustmaps.planck import PlanckQuery
from dustmaps.sfd import SFDQuery, SFDWebQuery
from dustmaps.csfd import CSFDQuery
from dustmaps.bayestar import BayestarQuery
from dustmaps.chen2014 import Chen2014Query
from dustmaps.decaps import DECaPSQuery
from dustmaps.edenhofer2023 import Edenhofer2023Query
from dustmaps.gaia_tge import GaiaTGEQuery
from dustmaps.iphas import IPHASQuery
from dustmaps.leike2020 import Leike2020Query
from dustmaps.leike_ensslin_2019 import LeikeEnsslin2019Query
from dustmaps.lenz2017 import Lenz2017Query
from dustmaps.marshall import MarshallQuery
from dustmaps.pg2010 import PG2010Query
from pathlib import Path

project_dir = Path(__file__).parent.resolve()
"""
    Для локального запроса в директории с этим файлом создаём папку dust_maps и в неё скачиваем локальные карты
    1) карта должна быть примерно по такому пути /db-app/app/domain/dust_maps/sfd/SFD_dust_4096_ngp.fits
    скачать её можно командами в пайтон консоли 

    from dustmaps.config import config
    config['data_dir'] = '/path/to/store/maps/in'

    import dustmaps.sfd
    dustmaps.sfd.fetch()

    import dustmaps.csfd
    dustmaps.csfd.fetch()

    import dustmaps.planck
    dustmaps.planck.fetch()

    import dustmaps.planck
    dustmaps.planck.fetch(which='GNILC')

    import dustmaps.bayestar
    dustmaps.bayestar.fetch()

    import dustmaps.iphas
    dustmaps.iphas.fetch()

    import dustmaps.marshall
    dustmaps.marshall.fetch()

    import dustmaps.chen2014
    dustmaps.chen2014.fetch()

    import dustmaps.lenz2017
    dustmaps.lenz2017.fetch()

    import dustmaps.pg2010
    dustmaps.pg2010.fetch()

    import dustmaps.leike_ensslin_2019
    dustmaps.leike_ensslin_2019.fetch()

    import dustmaps.leike2020
    dustmaps.leike2020.fetch()

    import dustmaps.edenhofer2023
    dustmaps.edenhofer2023.fetch()

    import dustmaps.gaia_tge
    dustmaps.gaia_tge.fetch()

    import dustmaps.decaps
    dustmaps.decaps.fetch()
"""
config['data_dir'] = f'{project_dir}/dust_maps'

"""
    1) coords = SkyCoord('12h30m25.3s', '15d15m58.1s', frame='icrs')

    2) l = np.array([0., 90., 180.])
    b = np.array([15., 0., -15.])
    coords = SkyCoord(l, b, unit='deg', frame='galactic')

    3) coords = SkyCoord(180., 0., unit='deg', frame='galactic')
"""


def get_absorption_sdf_web(coords: SkyCoord):
    edv = SFDWebQuery()
    resp = edv(coords)
    return resp


def get_absorption_sdf(coords: SkyCoord):
    edv = SFDQuery()
    resp = edv(coords)
    return resp


def get_absorption_plank(coords: SkyCoord):
    edv = PlanckQuery()
    resp = edv(coords)
    return resp


def get_absorption_scfd(coords: SkyCoord):
    edv = CSFDQuery()
    resp = edv(coords)
    return resp


def get_absorption_bayerstar(coords: SkyCoord):
    edv = BayestarQuery()
    resp = edv(coords)
    return resp


def get_absorption_chen2014(coords: SkyCoord):
    edv = Chen2014Query()
    resp = edv(coords)
    return resp


def get_absorption_decaps(coords: SkyCoord):
    edv = DECaPSQuery()
    resp = edv(coords)
    return resp


def get_absorption_edenhofer_2023(coords: SkyCoord):
    edv = Edenhofer2023Query()
    resp = edv(coords)
    return resp


def get_absorption_gaia_tge(coords: SkyCoord):
    edv = GaiaTGEQuery()
    resp = edv(coords)
    return resp


def get_absorption_iphas(coords: SkyCoord):
    edv = IPHASQuery()
    resp = edv(coords)
    return resp


def get_absorption_leike_2020(coords: SkyCoord):
    edv = Leike2020Query()
    resp = edv(coords)
    return resp


def get_absorption_leike_ensslin_2019(coords: SkyCoord):
    edv = LeikeEnsslin2019Query()
    resp = edv(coords)
    return resp


def get_absorption_lenz2017(coords: SkyCoord):
    edv = Lenz2017Query()
    resp = edv(coords)
    return resp


def get_absorption_marshall(coords: SkyCoord):
    edv = MarshallQuery()
    resp = edv(coords)
    return resp