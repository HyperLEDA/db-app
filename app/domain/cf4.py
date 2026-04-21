import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np

clight = 299792.458  # км/с


def to_grid_index(coord, delta=1000 / 128, N=128, L=1000):
    """Преобразует координату в индекс сетки"""
    coord = (coord + L / 2)
    index = np.floor(coord / delta).astype(int)
    index = np.clip(index, 0, N - 1)
    return index


def get_data_from_skycoord_redshift(skycoord, redshift):
    """
    Извлекает данные для координат SkyCoord и красного смещения

    Parameters:
    -----------
    skycoord : SkyCoord
        Объект координат Astropy
    redshift : float
        Красное смещение

    Returns:
    --------
    tuple: (density, density_err, vxyz, vxyz_err, vr, vr_err)
    """
    # Преобразуем красное смещение в расстояние (в Мпк)
    distance_mpc = (redshift * clight) / 100  # H0 = 100 км/с/Мпк

    # Получаем супергалактические координаты
    sgl = skycoord.supergalactic.sgl
    sgb = skycoord.supergalactic.sgb

    # Вычисляем картезианские координаты в супергалактической системе
    sgc = SkyCoord(sgl=sgl, sgb=sgb, distance=distance_mpc * u.Mpc,
                   frame='supergalactic')

    sgx = sgc.cartesian.x.value
    sgy = sgc.cartesian.y.value
    sgz = sgc.cartesian.z.value

    # Находим индексы в сетке
    ix = to_grid_index(sgx)
    iy = to_grid_index(sgy)
    iz = to_grid_index(sgz)

    # Загружаем и возвращаем данные
    return _load_grid_data(ix, iy, iz)


def get_data_from_skycoord_velocity(skycoord, velocity_km_s):
    """
    Извлекает данные для координат SkyCoord и скорости

    Parameters:
    -----------
    skycoord : SkyCoord
        Объект координат Astropy
    velocity_km_s : float
        Скорость в км/с

    Returns:
    --------
    tuple: (density, density_err, vxyz, vxyz_err, vr, vr_err)
    """
    # Преобразуем скорость в расстояние (в Мпк)
    distance_mpc = velocity_km_s / 100  # H0 = 100 км/с/Мпк

    # Получаем супергалактические координаты
    sgl = skycoord.supergalactic.sgl
    sgb = skycoord.supergalactic.sgb

    # Вычисляем картезианские координаты в супергалактической системе
    sgc = SkyCoord(sgl=sgl, sgb=sgb, distance=distance_mpc * u.Mpc,
                   frame='supergalactic')

    sgx = sgc.cartesian.x.value
    sgy = sgc.cartesian.y.value
    sgz = sgc.cartesian.z.value

    # Находим индексы в сетке
    ix = to_grid_index(sgx)
    iy = to_grid_index(sgy)
    iz = to_grid_index(sgz)

    # Загружаем и возвращаем данные
    return _load_grid_data(ix, iy, iz)


def _load_grid_data(ix, iy, iz):
    """Внутренняя функция для загрузки данных из сетки"""
    data = np.load('CF4pp_mean_std_grids.npz')

    d_data = data['d_mean_CF4pp']
    derr_data = data['d_std_CF4pp']
    vxyz_data = data['v_mean_CF4pp']
    vxyz_err_data = data['v_std_CF4pp']
    vr_data = data['vr_mean_CF4pp']
    verr_data = data['vr_std_CF4pp']

    return (d_data[ix, iy, iz],
            derr_data[ix, iy, iz],
            vxyz_data[:, ix, iy, iz],
            vxyz_err_data[:, ix, iy, iz],
            vr_data[ix, iy, iz],
            verr_data[ix, iy, iz])


# Примеры использования:
if __name__ == "__main__":
    # Пример 1: Галактические координаты + красное смещение
    gc = SkyCoord(l=120.5 * u.deg, b=45.2 * u.deg, frame='galactic')
    redshift = 0.025
    result1 = get_data_from_skycoord_redshift(gc, redshift)

    # Пример 2: Экваториальные координаты + скорость
    eq = SkyCoord(ra=185.3 * u.deg, dec=-12.7 * u.deg, frame='icrs')
    velocity = 7500  # км/с
    result2 = get_data_from_skycoord_velocity(eq, velocity)

    print("Результат для красного смещения:", result1[:2])
    print("Результат для скорости:", result2[:2])