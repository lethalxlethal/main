# Подключение Django

Фронтенд не знает, откуда берутся данные. Всё общение с данными идёт через три сервиса
(`src/services/index.js`): `authService`, `catalogService`, `paymentService`.
У каждого две реализации с одинаковым набором функций. Источник данных включается отдельно для каждого сервиса:

| Сервис | Переменная | Значение для текущего этапа |
|--------|------------|-----------------------------|
| Авторизация | `VITE_USE_API_AUTH` | `true` — Django, `false` — mock |
| Каталог | `VITE_USE_API_CATALOG` | `true` — Django, `false` — mock |
| Оплата | `VITE_USE_API_PAYMENT` | Оставить `false`, API оплаты ещё нет |

Для локальной разработки скопируйте `.env.example` в `.env.local` и перезапустите Vite.
Файл включает API авторизации и каталога, оставляя mock-оплату. При выключенных API
фронтенд использует mock-данные.

## Общие правила

- Базовый адрес: `/api` (`VITE_API_URL`). В `npm run dev` Vite проксирует `/api/` и `/media/` на Django `http://localhost:8000`.
- Полные адреса складываются из двух уровней: `config/urls.py` подключает `users.urls` по `api/auth/`, поэтому локальный `phone/request-code/` становится `/api/auth/phone/request-code/`. `publish.urls` подключён по `api/`, поэтому локальный `courses/` становится `/api/courses/`.
- Авторизация: JWT. После подтверждения кода сохраняйте `access` и `refresh`; защищённые запросы отправляют `Authorization: Bearer <access>`. При 401 обновляйте access через endpoint refresh. Cookie-сессия и CSRF для этих API не используются.
- Поля в JSON — `camelCase` (в DRF помогает `djangorestframework-camel-case` или явные `source` в сериализаторах).
- Ошибки: статус 4xx и тело `{ "detail": "Текст для пользователя", "code": "машинный_код" }`. Текст из `detail` показывается в интерфейсе как есть.
- Списки: можно отдавать массив или постраничный ответ DRF `{ "results": [...] }`, фронтенд понимает оба варианта.
- Для локального Vite используется proxy, поэтому отдельный CORS/CSRF для JWT API не нужен. На production `ALLOWED_HOSTS`, HTTPS и настройки reverse proxy нужно задать под домен сайта.

## Вход по телефону

Отдельной регистрации нет: если номер новый, аккаунт создаётся при первом входе.

| Метод и путь | Тело | Ответ |
|--------------|------|-------|
| `POST /api/auth/phone/request-code/` | `{ name, phone }` (телефон `+79001234567`) | `200`, код отправляется SMS; только при `DEBUG=True` ответ содержит `debug_code` |
| `POST /api/auth/phone/verify/` | `{ phone, code }` | `{ access, refresh, user }` |
| `GET /api/auth/me/` | — | `User`, требуется Bearer access token |
| `PATCH /api/auth/me/` | `{ name }` | Обновлённый `User`, требуется Bearer access token |
| `POST /api/auth/token/refresh/` | `{ refresh }` | Новый access и refresh |
| `POST /api/auth/logout/` | `{ refresh }` | `204`, refresh token отзывается |

Код ошибки, на который реагирует интерфейс: `invalid_code` (400).
Код подтверждения хранится в Django cache 5 минут; настроены лимиты запросов кода и проверки.

`User`: `{ id, phone, name, createdAt, course }`

## Каталог

| Метод и путь | Параметры | Ответ |
|--------------|-----------|-------|
| `GET /api/categories/` | — | `["Дизайн", ...]` |
| `GET /api/posts/` | `search`, `category`, `limit` | `PostSummary[]`, новые первыми |
| `GET /api/posts/:id/` | — | `PostDetail` |
| `GET /api/creators/` | `search`, `category`, `limit` | `Creator[]` |
| `GET /api/creators/:id/` | — | `CreatorDetail` |
| `GET /api/authors/` и `/api/authors/:id/` | — | Автор и его курсы |
| `GET /api/courses/` и `/api/courses/:id/` | — | Курс; те же данные доступны через совместимые `/api/posts/` |
| `GET /api/courses/:id/lessons/` и `/api/lessons/:id/` | — | Уроки курса; тело платного урока скрыто без доступа |

Доступ к тексту определяет сервер для текущего пользователя:

- `access: "free"` — открыт всем;
- `access: "paid"` — открыт после покупки.

Каждая запись `Course` также представляется фронтенду как публикация `Post`. Длинное содержимое хранится в связанных `Lesson`. Если доступа нет, `body` урока и курса равен `null`; текст закрытого материала в ответ не попадает.

```
PostSummary   { id, title, excerpt, category, access, price, publishedAt, hasAccess,
                creator: { id, name } }
PostDetail    PostSummary + { preview: string, body: string[] | null }
Creator       { id, name, bio, category, postsCount }
CreatorDetail Creator + { posts: PostSummary[] }
```

## Платежи

Backend API оплаты пока **не реализован**. Пока `VITE_USE_API_PAYMENT=false`, работают mock-сценарии. Django не узнаёт о mock-покупках и не открывает закрытое содержимое после такой оплаты.

Предполагаемый контракт для будущей реализации:

| Метод и путь | Тело / параметры | Ответ |
|--------------|------------------|-------|
| `GET /api/payments/quote/` | `?type=post&targetId=` | `Quote`. `409 already_owned`, если публикация уже куплена |
| `POST /api/payments/` | `{ type, targetId }` | `Payment` |
| `POST /api/payments/cancel/` | `{ type, targetId }` | `Payment` со статусом `cancelled` |
| `GET /api/payments/:id/` | — | `Payment` |
| `GET /api/me/payments/` | — | `Payment[]`, новые первыми |
| `GET /api/me/purchases/` | — | `PostSummary[]` + `paidAt` |

```
Quote   { type, targetId, title, description, amount, returnPath }
Payment { id, type, targetId, title, amount, status, createdAt, returnPath, confirmationUrl? }
status  "pending" | "paid" | "failed" | "cancelled"
```

Планируется начать с одного типа платежа, `post` (разовая покупка публикации). Поле `type` оставлено в контракте, чтобы позже добавить другие типы без смены API. Сумму должен считать сервер, фронтенд её только показывает.

### Как подключить реального платёжного провайдера

1. На будущем этапе `POST /api/payments/` будет создавать платёж в Django и провайдере. Если нужна страница оплаты провайдера, добавьте в ответ `confirmationUrl`: фронтенд сам перенаправит пользователя (`CheckoutPage.jsx`).
2. Провайдер возвращает пользователя на `/payments/<id>/result`. Страница запросит `GET /api/payments/:id/` и покажет статус.
3. Статус `paid` и открытие доступа должны выставляться по вебхуку провайдера, а не по действию пользователя в браузере.
4. Данные банковских карт в интерфейсе не вводятся и в Django не попадают: оплата идёт на стороне провайдера.

## Проверка на живом Django

Frontend-сборка и mock-тесты не проверяют соединение с настоящей базой или SMS-провайдером. Проверьте их отдельно:

1. Убедитесь, что установлены переменные PostgreSQL. Не публикуйте `.env` и не копируйте секреты в `.env.local` фронтенда.
2. Проверьте состояние миграций командой `poetry run python manage.py showmigrations`. Эта команда только показывает состояние; она ничего не применяет.
3. Когда решите применить уже созданные миграции, выполните `poetry run python manage.py migrate`, затем создайте администратора командой `poetry run python manage.py createsuperuser`.
4. В локальном режиме `DEBUG=True` backend не вызывает SMS Aero: он кладёт одноразовый код в cache и возвращает `debug_code` для формы. Для реальной отправки установите `DEBUG=False` и настройте в backend `.env` переменные `SMSAERO_EMAIL`, `SMSAERO_API_KEY`, `SMSAERO_SIGN`.
5. Запустите в отдельных терминалах `poetry run python manage.py runserver 8000` и `npm run dev`. Откройте адрес Vite, обычно `http://localhost:5173`.
6. Проверьте публичные API: `GET /api/categories/`, `/api/creators/`, `/api/posts/`. Проверьте и `GET /api/auth/me/` без токена — ожидается `401`.
7. После настройки SMS отправьте код через форму, проверьте `POST /api/auth/phone/request-code/` и `POST /api/auth/phone/verify/`. Успешная проверка должна вернуть `access`, `refresh` и `user`.
8. Проверьте профиль с `Authorization: Bearer <access>`, обновление access через refresh и выход. После этого откройте каталог и страницу курса.
9. Для проверки закрытого курса назначьте вошедшему пользователю курс через Django Admin. Без назначения `body` уроков должен быть `null`; после назначения авторизованный запрос должен получить тексты уроков.
10. Оплату пока проверяйте только на mock. Она не меняет доступ в Django.

Настоящий запуск и браузерная проверка этим чек-листом не выполняются автоматически. Команду `migrate` запускайте вручную, когда будете готовы.
