Метод API, позволяющий создать схему таблицы - `POST /api/v1/admin/table`, полное описание [см. тут](../openapi.md#post-apiv1admintable).

**Важно: этот метод не загружает никаких данных в таблицу, а только создаёт для неё схему в базе данных HyperLeda. Загрузить данные в таблицу можно, создав её схему при помощи этого метода и далее загрузив в неё данные при помощи [отдельного метода](upload_data.ru.md).**

### Принимаемые параметры

- `table_name` - машиночитаемое имя таблицы. Имя должно быть уникальным.
- `bibcode` - ADS bibcode статьи-источника данных.
- `datatype` - тип загружаемой таблицы, по умолчанию `regular`. Может быть использован для обозначения, что таблица является компиляцией уже существующих данных, переобработкой и прочим.
- `columns` - список с описанием колонок таблицы. См. секцию ниже.
- `description` - человекочитаемое описание данных в таблице.

### Описание колонок

- `name`: машиночитаемое имя колонки. Должно быть уникальным внутри одной таблицы.
- `data_type`: тип принимаемых данных, т.е. целое число, число с плавающей точкой, строка и прочее.
- `unit`: единицы измерения данных в столбце. Скорее всего сработает любое общепринятое написание. Если единиц измерения нет (например, в столбце содержатся названия объектов), это поле не должно быть указано.
- `description` - человекочитаемое описание данных в столбце.

### Возвращаемое значение

Возвращает ID таблицы во внутреннем реестре таблиц HyperLeda. Используется для дальнейшей загрузки данных, модификации и обработки данных в таблице.

Важно: если таблица с таким именем уже существует, то будет возвращён ID старой таблицы - новая создана не будет.
