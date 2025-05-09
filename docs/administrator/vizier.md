В этой документации описана последовательность действий для загрузки новой таблицы из Vizier.

## Установка окружения

Если не сделано, установить базовое окружение можно при помощи [этой инструкции](../dev/environment.ru.md).

## Скачивание и загрузка таблицы из Vizier

1. Загрузить набор скриптов для leda:
    ```bash
    git clone https://github.com/HyperLEDA/scripts.git
    cd scripts
    ```

2. Установить зависимости скриптов:
    ```bash
    uv sync
    ```

3. Запустить загрузку:
    ```bash
    uv run hyperleda_scripts/cli.py vizier download -c <catalog_name> -t <table_name>
    ```

    `catalog_name` и `table_name` - имена каталога и таблицы из Vizier, которые хочется загрузить. Например, для каталога [Siena Galaxy Atlas](https://vizier.cds.unistra.fr/viz-bin/VizieR-3?-source=J/ApJS/269/3/sga2020&-out.max=50&-out.form=HTML%20Table&-out.add=_r&-out.add=_RAJ,_DEJ&-sort=_r&-oc.form=sexa) команда будет выглядеть вот так:

    ```bash
    uv run hyperleda_scripts/cli.py vizier download -c J/ApJS/269/3 -t J/ApJS/269/3/sga2020
    ```

    Во время загрузки будет выведена строка с `table_name` - сгенерированным названием загружаемой таблицы. Его стоит записать, так как оно понадобится для дальнейшей обработки.

4. Ждать, пока загрузка кончится. Она состоит из двух шагов: скачивание таблицы из Vizier и загрузка этой таблицы в HyperLeda. Если на моменте загрузки в HyperLeda загрузка оборвётся, файл из Vizier останется и скачивать его заново не придётся.

    По итогам этого шага таблица будет загружена на уровень 0 БД.

5. При необходимости можно изменить метаданне таблицы. Для этого есть метод `PATCH /admin/api/v1/table`. Один из принимаемых параметров - `table_name` - имя таблицы, указанное при загрузке. Метод позволяет сделать несколько действий:
    1. Поменять или проставить UCD у столбца таблицы.
        ```json
        {
            "table_name": "my_table_name",
            "actions": [
                {
                    "type": "change_ucd",
                    "column": "column_name",
                    "ucd": "pos.eq.ra"
                }
            ]
        }
        ```

        Для справки список UCD и их значений можно найти в [спецификации IVOA](https://cdsweb.u-strasbg.fr/UCD/).

    2. Поменять или проставить единицы измерения у столбца таблицы. 
        ```json
        {
            "table_name": "my_table_name",
            "actions": [
                {
                    "type": "change_unit",
                    "column": "column_name",
                    "unit": "km/s"
                }
            ]
        }
        ```

        Единицы измерения могут быть произвольной сложности. Для их парсинга используется [astropy](https://docs.astropy.org/en/stable/units/format.html#converting-from-strings), так что список допустимых форм совпадает с тем, что принимает парсер этого модуля, но он очень широкий - в большинстве случаев об этом можно не думать.

6. Правильно разметить таблицу можно при помощи [инструкции](./marking.md).
