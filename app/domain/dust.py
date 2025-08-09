from typing import Callable

from astropy.coordinates import SkyCoord
from dustmaps.config import config
from dustmaps.planck import PlanckQuery
from dustmaps.sfd import SFDQuery, SFDWebQuery
from pathlib import Path

project_dir = Path(__file__).parent.resolve()
config['data_dir'] = f'{project_dir}/dust_maps'


def get_absorption(coords: SkyCoord, dust_map: Callable):
    """
    Получение поглощения
        пример веб запроса:
                создаём координаты
            l = [180., 160.]
            b = [30., 45.]
            coords = SkyCoord(l, b, unit='deg', frame='galactic')
                создаём карту
            sdf = SFDWebQuery()
                вызываем функцию
            absorption = get_absorption(coords=coords, map=sdf)

        пример локального запроса:
                в директории с этим файлом создаём папку dust_maps и в неё скачиваем локальные карты

                создаём координаты
            l = [180., 160.]
            b = [30., 45.]
            coords = SkyCoord(l, b, unit='deg', frame='galactic')
                создаём локальную карту
            sdf = SFDQuery()
                вызываем функцию
            absorption = get_absorption(coords=coords, map=sdf)
    """
    resp = dust_map(coords)
    return resp
