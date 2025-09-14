from astropy.coordinates import SkyCoord
from dustmaps.config import config
from dustmaps.planck import PlanckQuery
from dustmaps.sfd import SFDQuery
from dustmaps.csfd import CSFDQuery
from dustmaps.lenz2017 import Lenz2017Query
from pathlib import Path

project_dir = Path(__file__).parent.resolve()
"""
    Для локального запроса в директории с этим файлом создаём папку dust_maps и в неё скачиваем локальные карты
    1) карта должна быть примерно по такому пути /db-app/app/domain/dust_maps/sfd/SFD_dust_4096_ngp.fits
    скачать её можно командами в пайтон консоли 

    from dustmaps.config import config
    config['data_dir'] = ('/Volumes/NVME 1TB/PyProjects/LEDA/app/domain/dust_maps') # нужно прописать свой путь

    import dustmaps.sfd
    dustmaps.sfd.fetch()

    import dustmaps.csfd
    dustmaps.csfd.fetch()

    import dustmaps.planck
    dustmaps.planck.fetch()

    import dustmaps.lenz2017
    dustmaps.lenz2017.fetch()
"""
config['data_dir'] = f'{project_dir}/dust_maps'

"""
    1) coords = SkyCoord('12h30m25.3s', '15d15m58.1s', frame='icrs')

    2) l = np.array([0., 90., 180.])
    b = np.array([15., 0., -15.])
    coords = SkyCoord(l, b, unit='deg', frame='galactic')

    3) coords = SkyCoord(180., 0., unit='deg', frame='galactic')
"""


def get_absorption_sdf(coords: SkyCoord):
    edv = SFDQuery()
    resp = edv(coords)
    return resp


def get_absorption_plank(coords: SkyCoord):
    edv = PlanckQuery()
    resp = edv(coords)
    return resp


def get_absorption_csfd(coords: SkyCoord):
    edv = CSFDQuery()
    resp = edv(coords)
    return resp


def get_absorption_lenz2017(coords: SkyCoord):
    edv = Lenz2017Query()
    resp = edv(coords)
    return resp
