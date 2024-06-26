Авторизация в веб-сервисе Hyperleda происходит стандартным способом при помощи механизма Bearer token.
Более подробное описание можно посмотреть, например, [тут](https://www.devopsschool.com/blog/what-is-bearer-token-and-how-it-works/), но базово принцип следующий:

1. Имея на руках логин и пароль, вызвать метод API `/api/v1/login`. В случае корректного пароля метод вернёт токен авторизации - строку случайных символов (например, `1bb7ed073572d0f3057ade25d7a50b04`), подтверждающую, что вы - это вы. Пример:
    ```bash
    > curl -X 'POST' 'http://localhost:8000/api/v1/login' \
    -d '{"username": "myusername", "password": "mypassword"}'
    {"data": {"token": "bc5a996b69f7489f9218c02b2ed3b441"}}%   
    ```

2. Эта строка далее передаётся в защищённые авторизацией методы API (все те, что начинаются с `/api/v1/admin`) в виде HTTP заголовка `Authorization` с префиксом `Bearer `.

    ```bash
    curl -X 'POST' 'http://localhost:8000/api/v1/admin/task' \
    -H 'Authorization: Bearer bc5a996b69f7489f9218c02b2ed3b441' \
    -d '{"task_name": "echo", "payload": {"sleep_time_seconds": 2}}'
    ```

Токен авторизации не вечен, а живёт 14 дней с момента создания (в дальнейшем это время может быть уменьшено для большей безопасности). В случае сгорания токена можно заново сделать пункт 1, в таком случае будет создан новый токен, который можно далее использовать так же. При создании нового токена все старые перестают быть активными и более не могут быть использованы.

Для авторизации при работе через Swagger UI можно использовать кнопку авторизации в правом верхнем углу. Переданный туда токен будет автоматически проставляться в заголовок `Authorization` во всех запросах, требующих авторизации.
