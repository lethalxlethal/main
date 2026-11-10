# Подключение Django

Фронтенд не знает, откуда берутся данные. Всё общение с данными идёт через три сервиса
(`src/services/index.js`): `authService`, `catalogService`, `paymentService`.
У каждого две реализации с одинаковым набором функций:

| Режим | Папка | Когда используется |
|-------|-------|--------------------|
| mock  | `src/services/mock/` | `VITE_USE_MOCK=true` (по умолчанию), Django не нужен |
| Django | `src/services/api/` | `VITE_USE_MOCK=false` |

Чтобы перейти на Django: реализуйте эндпоинты ниже и пересоберите фронтенд с `VITE_USE_MOCK=false`.
Компоненты и страницы менять не нужно. Демо-данные из `src/static/data/` после этого перестают использоваться.

## Общие правила

- Базовый адрес: `/api` (`VITE_API_URL`). В Docker nginx проксирует `/api/` на `backend:8000`, в `npm run dev` Vite проксирует на `http://localhost:8000`.
- Авторизация: сессия Django в cookie (`credentials: 'include'`). Для POST/PATCH фронтенд отправляет заголовок `X-CSRFToken` из cookie `csrftoken`. Cookie `csrftoken` выдайте, например, в ответе `GET /api/auth/me/` через `ensure_csrf_cookie`.
- Поля в JSON — `camelCase` (в DRF помогает `djangorestframework-camel-case` или явные `source` в сериализаторах).
- Ошибки: статус 4xx и тело `{ "detail": "Текст для пользователя", "code": "машинный_код" }`. Текст из `detail` показывается в интерфейсе как есть.
- Списки: можно отдавать массив или постраничный ответ DRF `{ "results": [...] }`, фронтенд понимает оба варианта.
- В `settings.py` понадобятся `CSRF_TRUSTED_ORIGINS` и `ALLOWED_HOSTS` под адрес, с которого открыт сайт.

## Вход по телефону

Отдельной регистрации нет: если номер новый, аккаунт создаётся при первом входе.

| Метод и путь | Тело | Ответ |
|--------------|------|-------|
| `POST /api/auth/phone/request-code/` | `{ phone }` (формат `+79001234567`) | `204`. Код уходит по SMS. В ответе кода быть не должно |
| `POST /api/auth/phone/verify/` | `{ phone, code }` | `User`, сессия создаётся. Если номера нет в базе, пользователь создаётся с именем «Пользователь» |
| `GET /api/auth/me/` | — | `User` или `401` |
| `PATCH /api/auth/me/` | `{ name }` | `User` |
| `POST /api/auth/logout/` | — | `204` |

Код ошибки, на который реагирует интерфейс: `invalid_code` (400).
Код подтверждения храните в хэше с коротким сроком жизни и лимитом попыток.

`User`: `{ id, phone, name, createdAt }`

## Каталог

| Метод и путь | Параметры | Ответ |
|--------------|-----------|-------|
| `GET /api/categories/` | — | `["Дизайн", ...]` |
| `GET /api/posts/` | `search`, `category`, `limit` | `PostSummary[]`, новые первыми |
| `GET /api/posts/:id/` | — | `PostDetail` |
| `GET /api/creators/` | `search`, `category`, `limit` | `Creator[]` |
| `GET /api/creators/:id/` | — | `CreatorDetail` |

Доступ к тексту определяет сервер для текущего пользователя:

- `access: "free"` — открыт всем;
- `access: "paid"` — открыт после покупки.

Если доступа нет, `body` должен быть `null`, и текст закрытой публикации не должен попадать в ответ вообще.

```
PostSummary   { id, title, excerpt, category, access, price, publishedAt, hasAccess,
                creator: { id, name } }
PostDetail    PostSummary + { preview: string, body: string[] | null }
Creator       { id, name, bio, category, postsCount }
CreatorDetail Creator + { posts: PostSummary[] }
```

## Платежи

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

Сейчас поддерживается один тип платежа, `post` (разовая покупка публикации). Поле `type` оставлено в контракте, чтобы позже добавить другие типы без смены API.
Сумму всегда считает сервер, фронтенд её только показывает.

### Как подключить реального платёжного провайдера

1. `POST /api/payments/` создаёт платёж в Django и в провайдере. Если нужна страница оплаты провайдера, добавьте в ответ `confirmationUrl`: фронтенд сам перенаправит пользователя (`CheckoutPage.jsx`).
2. Провайдер возвращает пользователя на `/payments/<id>/result`. Страница запросит `GET /api/payments/:id/` и покажет статус.
3. Статус `paid` и открытие доступа должны выставляться по вебхуку провайдера, а не по действию пользователя в браузере.
4. Данные банковских карт в интерфейсе не вводятся и в Django не попадают: оплата идёт на стороне провайдера.

Чекбокс «Имитировать отказ банка» и демо-код в форме входа показываются только в mock-режиме.
