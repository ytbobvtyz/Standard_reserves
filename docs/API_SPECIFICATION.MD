# API_SPECIFICATION.md
## Standart Reserve — Спецификация API

---

## 1. ОБЩИЕ ПРИНЦИПЫ

### 1.1. Базовый URL
https://api.standart-reserve.ru/api/v1

text

### 1.2. Аутентификация

**JWT (JSON Web Token)**
- Header: `Authorization: Bearer <token>`
- Токен выдается при входе (`/auth/login`)
- Срок жизни токена: 24 часа
- Refresh токен: 7 дней (хранится в `sessions`)

### 1.3. Форматы

| Формат | Описание |
|--------|----------|
| **Запрос** | `application/json` |
| **Ответ** | `application/json` |
| **Дата** | `YYYY-MM-DD` |
| **Дата-время** | `YYYY-MM-DDTHH:MM:SSZ` (ISO 8601 UTC) |
| **Количество** | `DECIMAL(12,2)` → строка или число (в JSON) |

### 1.4. Коды ответов

| Код | Описание |
|-----|----------|
| `200` | Успешно |
| `201` | Создано |
| `400` | Неверный запрос |
| `401` | Не авторизован |
| `403` | Доступ запрещен (недостаточно прав) |
| `404` | Не найдено |
| `409` | Конфликт (дублирование) |
| `422` | Ошибка валидации |
| `500` | Внутренняя ошибка сервера |

### 1.5. Общая структура ответа

```json
{
    "status": "success",
    "data": { ... },
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 100
    }
}
1.6. Ошибки
json
{
    "status": "error",
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Поле 'quantity' должно быть больше 0",
        "details": [
            {
                "field": "quantity_requested",
                "message": "Значение должно быть > 0"
            }
        ]
    }
}
2. АУТЕНТИФИКАЦИЯ И ПОЛЬЗОВАТЕЛИ
2.1. Вход в систему
text
POST /auth/login
Request:

json
{
    "username": "ivanov",
    "password": "secure_password"
}
Response (200):

json
{
    "status": "success",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 86400,
        "user": {
            "id": "11111111-1111-1111-1111-111111111111",
            "username": "ivanov",
            "full_name": "Иванов Иван",
            "role": "commercial",
            "department": "Коммерческий отдел",
            "department_id": "66111111-1111-1111-1111-111111111111"
        }
    }
}
Errors:

401 — Неверный логин или пароль

403 — Учетная запись заблокирована

2.2. Выход
text
POST /auth/logout
Headers:

text
Authorization: Bearer <token>
Response (200):

json
{
    "status": "success",
    "message": "Вы вышли из системы"
}
2.3. Обновление токена
text
POST /auth/refresh
Request:

json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
Response (200):

json
{
    "status": "success",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 86400
    }
}
2.4. Получение профиля
text
GET /auth/profile
Headers:

text
Authorization: Bearer <token>
Response (200):

json
{
    "status": "success",
    "data": {
        "id": "11111111-1111-1111-1111-111111111111",
        "username": "ivanov",
        "email": "ivanov@company.ru",
        "full_name": "Иванов Иван",
        "role": "commercial",
        "department": "Коммерческий отдел",
        "department_id": "66111111-1111-1111-1111-111111111111",
        "last_login_at": "2026-08-18T09:00:00Z"
    }
}
2.5. Смена пароля
text
POST /auth/change-password
Headers:

text
Authorization: Bearer <token>
Request:

json
{
    "old_password": "old_password",
    "new_password": "new_secure_password"
}
Response (200):

json
{
    "status": "success",
    "message": "Пароль изменен"
}
3. ЗАПРОСЫ (REQUESTS)
3.1. Создать запрос
text
POST /requests
Headers:

text
Authorization: Bearer <token>
Request (нормативный запас):

json
{
    "request_type": "normative",
    "client_name": "ООО 'Ромашка'",
    "expiry_date": "2026-12-31",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_requested": 1000,
            "unit": "шт"
        },
        {
            "product_code": 10002,
            "warehouse_code": 2002,
            "quantity_requested": 500,
            "unit": "шт"
        }
    ],
    "comment": "Срочная потребность"
}
Request (разовое перемещение):

json
{
    "request_type": "one_time",
    "client_name": "ООО 'Ромашка'",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_requested": 200,
            "unit": "шт"
        }
    ],
    "comment": "Разовое перемещение для запуска"
}
Response (201):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "request_type": "normative",
        "status": "draft",
        "client_name": "ООО 'Ромашка'",
        "initiator_id": "11111111-1111-1111-1111-111111111111",
        "department_id": "66111111-1111-1111-1111-111111111111",
        "expiry_date": "2026-12-31",
        "items": [
            {
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "product_code": 10001,
                "warehouse_code": 2001,
                "quantity_requested": 1000,
                "quantity_approved": null,
                "unit": "шт",
                "category": "A",
                "category_factor": 1,
                "long_distance": false,
                "distance_factor": 1,
                "requirement": 1000
            }
        ],
        "created_at": "2026-08-18T09:00:00Z"
    }
}

`department_id` в запрос **не передаётся** клиентом: при создании копируется `users.department_id` инициатора.

`requirement` в каждой позиции = эффективное количество (`quantity_approved`, если задано, иначе `quantity_requested`) × коэффициент категории (A=1, B=1.5, C=2) × коэффициент удалённости склада (`long_distance` false=1, true=1.5). Результат округляется до 32 знаков после запятой.

Errors:

400 — Невалидные данные

400 INVALID_EXPIRY_DATE — `expiry_date` раньше 3 месяцев или позже 6 месяцев от даты создания

403 — Недостаточно прав (только commercial для нормативных; commercial/logistics для разовых)

3.2. Получить список запросов (с фильтрацией)
text
GET /requests
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание	Пример
type	string	Тип запроса	normative / one_time
status	string	Статус	draft / pp_approved / ...
client_name	string	Клиент (частичное совпадение)	Ромашка
initiator_id	uuid	Инициатор	11111111-...
warehouse_code	integer	Склад (фильтр по позициям)	2001
product_code	integer	Артикул (фильтр по позициям)	10001
department_id	uuid	Подразделение инициатора	66111111-...
from_date	date	Создан с	2026-08-01
to_date	date	Создан по	2026-08-18
page	integer	Страница	1
limit	integer	Записей на страницу	50
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "request_type": "normative",
            "status": "draft",
            "client_name": "ООО 'Ромашка'",
            "initiator": {
                "id": "11111111-1111-1111-1111-111111111111",
                "full_name": "Иванов Иван",
                "department": "Коммерческий отдел",
                "department_id": "66111111-1111-1111-1111-111111111111"
            },
            "department_id": "66111111-1111-1111-1111-111111111111",
            "department_name": "Коммерческий отдел",
            "items_count": 2,
            "total_quantity": 1500,
            "expiry_date": "2026-12-31",
            "created_at": "2026-08-18T09:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 15
    }
}
3.3. Получить запрос по ID
text
GET /requests/{request_id}
Headers:

text
Authorization: Bearer <token>
Response (200):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "request_type": "normative",
        "status": "pp_approved",
        "client_name": "ООО 'Ромашка'",
        "initiator": {
            "id": "11111111-1111-1111-1111-111111111111",
            "full_name": "Иванов Иван",
            "department": "Коммерческий отдел",
            "department_id": "66111111-1111-1111-1111-111111111111"
        },
        "department_id": "66111111-1111-1111-1111-111111111111",
        "department_name": "Коммерческий отдел",
        "initiator_comment": "Срочная потребность",
        "comment_pp": "Объем подтвержден, 20% резерв",
        "comment_economy": null,
        "expiry_date": "2026-12-31",
        "items": [
            {
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "product": {
                    "code": 10001,
                    "name": "Подшипник 6204ZZ",
                    "category": "A",
                    "weight_kg": 0.25
                },
                "warehouse": {
                    "code": 2001,
                    "name": "Склад Ростов",
                    "long_distance": false
                },
                "quantity_requested": 1000,
                "quantity_approved": 800,
                "unit": "шт",
                "category_factor": 1,
                "long_distance": false,
                "distance_factor": 1,
                "requirement": 800,
                "comment": null
            }
        ],
        "approvals": {
            "pp": {
                "approved_at": "2026-08-18T09:30:00Z",
                "approved_by": {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "full_name": "Петров Петр"
                },
                "action": "edit"
            },
            "economy": {
                "approved_at": null,
                "approved_by": null,
                "action": null
            }
        },
        "created_at": "2026-08-18T09:00:00Z",
        "updated_at": "2026-08-18T09:30:00Z",
        "order_number": null,
        "executed_at": null,
        "executed_comment": null,
        "executed_by": null
    }
}
Для разового запроса в статусе `executed` дополнительно возвращаются:

json
{
    "order_number": "РН-2026-08-18-001",
    "executed_at": "2026-08-18T11:00:00Z",
    "executed_comment": "Отгрузка произведена 18.08.2026",
    "executed_by": {
        "id": "44444444-4444-4444-4444-444444444444",
        "full_name": "Кузнецов Кузьма"
    },
    "history": [
        {
            "timestamp": "2026-08-18T11:00:00Z",
            "action": "executed",
            "user_name": "Кузнецов Кузьма",
            "comment": "Разнарядка: РН-2026-08-18-001. Отгрузка произведена 18.08.2026"
        }
    ]
}

text

3.4. Обновить черновик
text
PUT /requests/{request_id}
Headers:

text
Authorization: Bearer <token>
Request (только для статуса draft):

json
{
    "client_name": "ООО 'Тюльпан'",
    "expiry_date": "2026-12-31",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_requested": 1500,
            "unit": "шт"
        }
    ],
    "comment": "Уточненный объем"
}
При редактировании черновика `expiry_date` можно изменять без ограничений, кроме базового: от 3 до 6 месяцев от даты создания (`created_at`). Правило «только уменьшать» на черновик **не** распространяется.

Errors:

400 INVALID_EXPIRY_DATE — `expiry_date` раньше created_at + 3 месяца или позже created_at + 6 месяцев

400 INVALID_STATUS — запрос не в статусе draft

Response (200):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "status": "draft",
        "updated_at": "2026-08-18T10:00:00Z"
    }
}
3.5. Удалить запрос
text
DELETE /requests/{request_id}
Headers:

text
Authorization: Bearer <token>
Права: только инициатор запроса. Soft delete (`deleted_at`). Связанные записи `normatives` также помечаются `deleted_at`.

**Статусы, доступные для удаления:**
- `draft` ✅
- `pp_approved` ✅
- `economy_check` ✅
- `rejected` ✅ (можно удалить отклонённый запрос)
- `expired` ✅ (можно удалить просроченный запрос)

**Статусы, НЕ доступные для удаления:**
- `active` ❌ (норматив создан)
- `approved` ❌ (разовый согласован)
- `executed` ❌ (разовый исполнен)

Response (200):

json
{
    "status": "success",
    "message": "Запрос удален"
}

Errors:

403 FORBIDDEN — текущий пользователь не инициатор («Только инициатор может удалить запрос»)

400 BAD_REQUEST — статус `active` / `approved` / `executed` (и любой другой, кроме разрешённых). Сообщение: «Невозможно удалить запрос после финального согласования»
3.6. Изменить срок активного норматива
text
PATCH /requests/{request_id}/expiry-date
Headers:

text
Authorization: Bearer <token>
Условия: только нормативный запрос в статусе `active`. Гость (`guest`) не может изменять срок. Новое значение: ≥ `CURRENT_DATE` и ≤ текущей `expiry_date` (только уменьшение). Связанные записи `normatives` обновляются тем же сроком.

Request:

json
{
    "expiry_date": "2026-10-01"
}

Response (200):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "status": "active",
        "expiry_date": "2026-10-01",
        "updated_at": "2026-08-22T10:00:00Z"
    }
}

Errors:

400 INVALID_STATUS — запрос не в статусе `active` или не нормативный

400 BAD_REQUEST — «Дата окончания не может быть позже текущей» / «Дата окончания не может быть раньше сегодняшнего дня»

403 FORBIDDEN — недостаточно прав

3.7. Отправить на согласование
text
POST /requests/{request_id}/submit
Headers:

text
Authorization: Bearer <token>
Условия: Только для статуса draft, только инициатор

Response (200):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "status": "pp_approved",
        "updated_at": "2026-08-18T10:00:00Z"
    }
}
4. СОГЛАСОВАНИЕ (ПП)
4.1. Получить список запросов на согласование (ПП)
text
GET /approvals/pp/pending
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание
type	string	normative / one_time
client_name	string	Клиент (частичное совпадение, ILIKE)
page	integer	Страница
limit	integer	Записей на страницу
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "request_type": "normative",
            "client_name": "ООО 'Ромашка'",
            "initiator": {
                "id": "11111111-1111-1111-1111-111111111111",
                "full_name": "Иванов Иван"
            },
            "items": [
                {
                    "product_code": 10001,
                    "product_name": "Подшипник 6204ZZ",
                    "warehouse_code": 2001,
                    "warehouse_name": "Склад Ростов",
                    "quantity_requested": 1000,
                    "unit": "шт",
                    "category": "A",
                    "category_factor": 1,
                    "long_distance": false,
                    "distance_factor": 1,
                    "requirement": 1000
                }
            ],
            "created_at": "2026-08-18T09:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 5
    }
}
4.2. Согласовать запрос (ПП)
text
POST /approvals/pp/{request_id}/action
Headers:

text
Authorization: Bearer <token>
Действия:

API принимает только `approve` и `reject`. Отдельное действие `edit` **не поддерживается** (422). Изменение объёма и срока выполняется в теле `approve`.

1. Подтвердить (с опциональной корректировкой объёма и срока):

json
{
    "action": "approve",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_approved": 800
        }
    ],
    "comment": "Снижаем объем на 20% из-за ограничений по заводу",
    "expiry_date": "2026-12-31"
}

`expiry_date` можно передать в `approve`. Срок должен быть от 3 до 6 месяцев от `created_at`, иначе 400 INVALID_EXPIRY_DATE. Изменение срока пишется в комментарий истории согласования. Если `items` не переданы, `quantity_approved` заполняется из `quantity_requested`.

2. Отказать:

json
{
    "action": "reject",
    "comment": "Нет необходимого сырья для производства"
}
Response (200):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "status": "economy_check",
        "pp_approved_at": "2026-08-18T09:30:00Z",
        "pp_approved_by": {
            "id": "22222222-2222-2222-2222-222222222222",
            "full_name": "Петров Петр"
        },
        "pp_action": "edit",
        "comment_pp": "Снижаем объем на 20% из-за ограничений по заводу"
    }
}
5. СОГЛАСОВАНИЕ (ЭКОНОМИСТ)
5.1. Получить список запросов на согласование (Экономист)
text
GET /approvals/economy/pending
Headers:

text
Authorization: Bearer <token>
Response (200): Аналогично /approvals/pp/pending

5.2. Согласовать запрос (Экономист)
text
POST /approvals/economy/{request_id}/action
Headers:

text
Authorization: Bearer <token>
Действия:

API принимает только `approve` и `reject`. Отдельное действие `edit` **не поддерживается** (422). Изменение объёма и срока выполняется в теле `approve`.

1. Подтвердить (нормативный или разовый, с опциональной корректировкой):

json
{
    "action": "approve",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_approved": 600
        }
    ],
    "comment": "Экономика приемлема",
    "expiry_date": "2026-10-01"
}

`expiry_date` можно передать в `approve`. Для нормативного запроса действует проверка:
- минимум 3 месяца и максимум 6 месяцев от `created_at` (400 INVALID_EXPIRY_DATE);
- только уменьшение: новое значение ≥ `CURRENT_DATE` и ≤ текущей `expiry_date`.
  - 400 BAD_REQUEST «Дата окончания не может быть позже текущей»
  - 400 BAD_REQUEST «Дата окончания не может быть раньше сегодняшнего дня»

Проверка минимума 3 месяца сохраняется при согласовании экономистом.

Если `items` не переданы, `quantity_approved` заполняется из `quantity_requested`.

2. Отказать:

json
{
    "action": "reject",
    "comment": "Хранение экономически нецелесообразно"
}
Response (нормативный, утвержден):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "status": "active",
        "economy_approved_at": "2026-08-18T10:00:00Z",
        "economy_approved_by": {
            "id": "33333333-3333-3333-3333-333333333333",
            "full_name": "Сидоров Сидор"
        },
        "economy_action": "approve",
        "comment_economy": "Экономика приемлема"
    }
}
Response (разовый, утвержден):

json
{
    "status": "success",
    "data": {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "status": "approved",
        "economy_approved_at": "2026-08-18T10:00:00Z",
        "economy_approved_by": {
            "id": "33333333-3333-3333-3333-333333333333",
            "full_name": "Сидоров Сидор"
        }
    }
}
6. ЛОГИСТИКА
6.1. Дашборд логиста — нормативы
text
GET /logistics/normative/dashboard
Headers:

text
Authorization: Bearer <token>
Права: все авторизованные (просмотр). Кнопки формирования заказов, Excel и загрузки остатков — только logistics.
Query параметры:

Параметр	Тип	Описание
warehouse_code	integer	Фильтр по складу
filter_mode	string	all / with_normatives / deficit_only
unit	string	шт / т
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "warehouse_code": 2001,
            "warehouse_name": "Склад Ростов",
            "long_distance": false,
            "long_distance_message": null,
            "deficit_items": [
                {
                    "product_code": 10001,
                    "product_name": "Подшипник 6204ZZ",
                    "category": "A",
                    "normative_quantity": 1000,
                    "requirement": 1000,
                    "available": 600,
                    "plan": 600,
                    "unit": "шт",
                    "deficit": 400,
                    "client_name": "ООО 'Ромашка'",
                    "expiry_date": "2026-12-31",
                    "status": "warning"
                }
            ],
            "total_deficit": 400,
            "deficit_count": 1
        }
    ],
    "summary": {
        "total_deficit": 400,
        "deficit_warehouses": 1,
        "deficit_products": 1
    }
}

`available` — доступно (факт − заказы клиентов). `plan` — запланировано (`available` + разнарядки).

`requirement` (Потребность) = `normative_quantity` × коэффициент категории (A=1, B=1.5, C=2) × коэффициент удалённости (`long_distance` false=1, true=1.5).

`deficit` = `requirement` − `plan`.

Для склада с `long_distance = true` возвращаются `long_distance: true` и сообщение:

```json
{
    "long_distance": true,
    "long_distance_message": "Ввиду удалённого расположения склада, пополнение возможно по железной дороге — срок доставки около 1 месяца от даты готовности продукции на производственной площадке, в связи с чем нормативы увеличены"
}
```

6.2. Загрузить остатки из Excel (ERP)
text
POST /logistics/normative/upload
Headers:

text
Authorization: Bearer <token>
Content-Type: multipart/form-data
Права: только logistics. Остальные роли получают 403 FORBIDDEN.

Form-data:

Поле	Тип	Описание
file	file	Excel-файл (.xlsx / .xls)

Формат Excel (колонки по номеру, 1-based; первая строка — заголовок):

Колонка	Поле	Описание
1	product_code	Артикул (ID продукта → products.code)
3	erp_plant_code	Завод ERP → objects.erp_plant_code → objects.code (если несколько заводов с одним кодом — активный с наименьшим `code`)
5	erp_warehouse_code	Склад ERP → objects.erp_warehouse_code → objects.code (если несколько складов с одним кодом — активный с наименьшим `code`)
17	unit	Единица измерения: `ШТ` или `КГ` (пусто → `ШТ`)
19	available	Доступно (факт − заказы клиентов)
20	plan	Запланировано (available + разнарядки)

Логика загрузки (перезапись по складам из файла):
1. Разобрать строки Excel: поиск завода, склада и продукта.
2. Определить все `warehouse_code`, которые есть в валидных строках файла.
3. Удалить все записи `available_balances` для этих складов.
4. Вставить только новые записи из файла (`source` = `excel`, `last_sync_at` = NOW()). Позиция, которой больше нет в файле, исчезает из БД.
5. Обновить `sync_metadata`: `last_balances_sync_at` = NOW(), `last_balances_sync_by` = текущий пользователь.

Склады, которых нет в файле, не затрагиваются. Неизвестные коды и невалидные числа — ошибка по строке, остальные строки сохраняются.

Response (200):

json
{
    "status": "success",
    "data": {
        "uploaded": 2,
        "created": 1,
        "updated": 1,
        "errors": 1,
        "message": "Загружено 2, ошибок 1",
        "error_details": [
            {"row": 4, "message": "Склад ERP X999 не найден"}
        ]
    }
}
Errors:

400 INVALID_FILE — не Excel или пустой файл

403 FORBIDDEN — не роль logistics

6.2.1. Дата и автор последней загрузки остатков
text
GET /logistics/normative/sync-info
Headers:

text
Authorization: Bearer <token>
Права: все авторизованные (как дашборд). Данные читаются из `sync_metadata`.

Response (200):

json
{
    "status": "success",
    "data": {
        "last_balances_sync_at": "2026-08-22T14:30:00Z",
        "last_balances_sync_by": {
            "id": "44444444-4444-4444-4444-444444444444",
            "username": "ivanov",
            "full_name": "Иванов Иван",
            "role": "logistics"
        }
    }
}

Если загрузки ещё не было, `last_balances_sync_at` и `last_balances_sync_by` равны `null`.

6.3. Сформировать заказы на пополнение
text
POST /logistics/normative/{warehouse_code}/generate-orders
Headers:

text
Authorization: Bearer <token>
Права: только logistics. Остальные роли получают 403 FORBIDDEN.
Request:

json
{
    "product_codes": [10001, 10002]
}
Опционально: если `product_codes` не указаны — все позиции с дефицитом по складу.

6.3.1. Сформировать заказы по нескольким складам
text
POST /logistics/normative/generate-orders
Права: только logistics.

json
{
    "warehouse_codes": [2001, 2002],
    "product_codes": [10001]
}
`warehouse_codes` обязателен (хотя бы один склад). Ответ тот же, что у 6.3: список заказов, сгруппированных по заводам.
Response (200):

json
{
    "status": "success",
    "data": {
        "orders": [
            {
                "plant_code": 1001,
                "plant_name": "Завод Московский",
                "warehouse_code": 2001,
                "warehouse_name": "Склад Ростов",
                "items": [
                    {
                        "product_code": 10001,
                        "product_name": "Подшипник 6204ZZ",
                        "deficit": 400,
                        "unit": "шт"
                    }
                ],
                "estimated_delivery_days": 5
            }
        ],
        "total_orders": 1,
        "total_products": 1,
        "total_quantity": 400
    }
}
6.4. Выгрузить заказы в Excel
text
GET /logistics/normative/export
Headers:

text
Authorization: Bearer <token>
Права: только logistics (действие, не просмотр). Остальные роли — 403.
Query параметры:

Параметр	Тип	Описание
warehouse_code	integer	Склад
product_codes	array	Артикулы (через запятую)
Response: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

6.5. Разовые перемещения — список
text
GET /logistics/one-time/list
Headers:

text
Authorization: Bearer <token>
Права: все авторизованные (просмотр). Исполнение и Excel — только logistics.
Query параметры:

Параметр	Тип	Описание
status	string	approved / executed
client_name	string	Клиент (частичное совпадение)
page	integer	Страница
limit	integer	Записей на страницу
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "client_name": "ООО 'Ромашка'",
            "status": "approved",
            "items": [
                {
                    "product_code": 10001,
                    "product_name": "Подшипник 6204ZZ",
                    "warehouse_code": 2001,
                    "warehouse_name": "Склад Ростов",
                    "quantity": 200,
                    "unit": "шт"
                }
            ],
            "created_at": "2026-08-18T09:00:00Z",
            "order_number": "РН-2026-08-18-001",
            "executed_at": "2026-08-18T11:00:00Z",
            "executed_comment": "Отгрузка произведена 18.08.2026"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 3
    }
}
6.6. Справочники для фильтров разовых
text
GET /logistics/one-time/initiators
GET /logistics/one-time/clients
Права: все авторизованные. `initiators` — список заявителей разовых запросов. `clients` — список уникальных имён клиентов.

6.7. Выгрузить разовый запрос в Excel
text
GET /logistics/one-time/{request_id}/export
Права: только logistics. Response: Excel-файл.

6.8. Отметить разовое перемещение как исполненное
text
POST /logistics/one-time/{request_id}/execute
Headers:

text
Authorization: Bearer <token>
Права: только logistics. Остальные роли получают 403 FORBIDDEN.
Request:

json
{
    "order_number": "РН-2026-08-18-001",
    "comment": "Отгрузка произведена 18.08.2026"
}
Response (200):

json
{
    "status": "success",
    "data": {
        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "status": "executed",
        "executed_at": "2026-08-18T11:00:00Z",
        "order_number": "РН-2026-08-18-001",
        "executed_comment": "Отгрузка произведена 18.08.2026"
    }
}
7. НОРМАТИВЫ
7.1. Получить текущие нормативы
text
GET /normatives
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание
warehouse_code	integer	Склад
product_code	integer	Артикул
client_name	string	Клиент (частичное совпадение)
category	string	A/B/C
department_id	uuid	Подразделение инициатора запроса или загрузившего Excel-партию
search	string	Поиск по коду или названию продукта
page	integer	Страница
limit	integer	Записей на страницу
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "product_code": 10001,
            "product_name": "Подшипник 6204ZZ",
            "category": "A",
            "warehouse_code": 2001,
            "warehouse_name": "Склад Ростов",
            "quantity": 1000,
            "unit": "шт",
            "client_name": "ООО 'Ромашка'",
            "department_id": "66111111-1111-1111-1111-111111111111",
            "department_name": "Коммерческий отдел",
            "expiry_date": "2026-12-31",
            "created_at": "2026-08-18T10:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 10
    }
}
7.2. Получить нормативы на дату
text
GET /normatives/on-date
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Обязательный	Описание
date	date	✅	Дата среза
warehouse_code	integer	❌	Склад
product_code	integer	❌	Артикул
department_id	uuid	❌	Подразделение инициатора запроса или загрузившего Excel-партию
search	string	❌	Поиск по коду или названию продукта
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "product_code": 10001,
            "product_name": "Подшипник 6204ZZ",
            "warehouse_code": 2001,
            "warehouse_name": "Склад Ростов",
            "total_quantity": 1000,
            "unit": "шт",
            "details": [
                {
                    "client_name": "ООО 'Ромашка'",
                    "quantity": 1000,
                    "expiry_date": "2026-12-31",
                    "department_id": "66111111-1111-1111-1111-111111111111",
                    "department_name": "Коммерческий отдел"
                }
            ]
        }
    ]
}
7.3. Расчет норматива (формула)
text
GET /normatives/calculate
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Обязательный	Описание
product_code	integer	✅	Артикул
warehouse_code	integer	✅	Склад
Response (200):

json
{
    "status": "success",
    "data": {
        "product_code": 10001,
        "product_name": "Подшипник 6204ZZ",
        "category": "A",
        "warehouse_code": 2001,
        "warehouse_name": "Склад Ростов",
        "monthly_consumption": 1000,
        "distance_factor": 1,
        "category_factor": 1,
        "calculated_normative": 1000,
        "unit": "шт"
    }
}
7.4. Получить цепочку родственных артикулов
text
GET /products/{product_code}/related
Headers:

text
Authorization: Bearer <token>
Response (200):

json
{
    "status": "success",
    "data": {
        "product_code": 10001,
        "product_name": "Подшипник 6204ZZ",
        "related_products": [
            {
                "code": 10101,
                "name": "Подшипник 6204ZZ (новая этикетка)",
                "relation": "child",
                "is_active": true
            },
            {
                "code": 99001,
                "name": "Подшипник 6204ZZ (старая этикетка)",
                "relation": "parent",
                "is_active": false
            }
        ]
    }
}
8. СПРАВОЧНИКИ

Управление номенклатурой (Этап 7.1) — роли `pp`, `economist`, `logistics`:

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| GET | `/references/products` | Список продуктов | все авторизованные |
| GET | `/references/products/{code}` | Карточка продукта | все авторизованные |
| GET | `/references/products/template` | Скачать Excel-шаблон | pp, economist, logistics |
| POST | `/references/products/upload` | Загрузить продукты из Excel | pp, economist, logistics |
| GET | `/references/products/{code}/edit` | Получить продукт для редактирования | pp, economist, logistics |
| PUT | `/references/products/{code}` | Обновить продукт | pp, economist, logistics |
| DELETE | `/references/products/{code}` | Удалить продукт | pp, economist, logistics |

Управление объектами (Этап 7.2) — роль `logistics`:

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| GET | `/references/objects` | Список объектов | все авторизованные |
| GET | `/references/objects/{code}` | Карточка объекта | все авторизованные |
| POST | `/references/objects` | Создать объект | logistics |
| GET | `/references/objects/{code}/edit` | Получить объект для редактирования | logistics |
| PUT | `/references/objects/{code}` | Обновить объект | logistics |
| DELETE | `/references/objects/{code}` | Удалить объект | logistics |

Просмотр списков и карточек продуктов/объектов доступен всем авторизованным ролям, включая `commercial` и `guest`.

8.1. Получить список продуктов
text
GET /references/products
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание
search	string	Поиск по коду или названию
category	string	A/B/C
is_active	boolean	Только активные
include_analogs	boolean	Если true — к найденным продуктам добавить активные аналоги по цепочке parent_code/children_code
page	integer	Страница
limit	integer	Записей на страницу
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "code": 10001,
            "name": "Подшипник 6204ZZ",
            "category": "A",
            "plant_id": 1001,
            "plant_name": "Завод Московский",
            "weight_kg": 0.250,
            "monthly_consumption": 1000,
            "is_active": true,
            "is_analog": false,
            "gtin": "4601234567890",
            "mark_control": false,
            "last_modified_at": "2026-08-20T12:00:00Z"
        },
        {
            "code": 10101,
            "name": "Подшипник 6204ZZ (новая этикетка)",
            "category": "A",
            "plant_id": 1001,
            "plant_name": "Завод Московский",
            "weight_kg": 0.250,
            "monthly_consumption": 800,
            "is_active": true,
            "is_analog": true,
            "gtin": "4601234567890",
            "mark_control": false,
            "last_modified_at": "2026-08-20T12:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 500
    }
}

`include_analogs=true`: в `data` сначала идут продукты, совпавшие с поиском
(`is_analog: false`), затем активные аналоги по всей связанной цепочке
`parent_code`/`children_code` (`is_analog: true`). Неактивные аналоги не
возвращаются. Продукт, который сам совпал с поиском, не дублируется как аналог.
`meta.total` считает только совпадения поиска (без раздувания аналогами).

Особый случай точного поиска по числовому коду: при сочетании
`is_active=true&include_analogs=true` найденный неактивный товар сохраняется в
ответе как `is_active: false, is_analog: false` и служит начальной точкой поиска
замен. Благодаря этому запрос по выведенному из ассортимента артикулу возвращает
сам артикул и его активные аналоги. Выбирать неактивный товар клиент не должен.

8.1.1. Получить продукт по коду
text
GET /references/products/{code}
Права: все авторизованные. 404, если продукт не найден или удалён.

Response (200): тот же объект, что GET `/references/products/{code}/edit` (`ProductDetail`).
8.2. Получить список объектов (склады/заводы)
text
GET /references/objects
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание
type	string	plant / warehouse
city	string	Город (частичное совпадение, ILIKE)
is_active	boolean	Только активные
page	integer	Страница (по умолчанию 1)
limit	integer	Записей на страницу (по умолчанию 50, максимум 200)
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "code": 1001,
            "name": "Завод Московский",
            "city": "Москва",
            "region": "Московская область",
            "address": null,
            "type": "plant",
            "erp_plant_code": 2401,
            "erp_warehouse_code": null,
            "loading_point": null,
            "is_active": true,
            "long_distance": false,
            "last_modified_at": "2026-08-20T12:00:00Z"
        },
        {
            "code": 2001,
            "name": "Склад Ростов",
            "city": "Ростов-на-Дону",
            "region": "Ростовская область",
            "address": null,
            "type": "warehouse",
            "erp_plant_code": null,
            "erp_warehouse_code": "F005",
            "loading_point": "2R05",
            "is_active": true,
            "long_distance": false,
            "last_modified_at": "2026-08-18T09:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 15
    }
}

8.2.1. Получить объект по коду
text
GET /references/objects/{code}
Права: все авторизованные. 404, если объект не найден или удалён.

Response (200): объект списка (`ObjectListItem`). Для полного набора полей редактирования — GET `/references/objects/{code}/edit` (только logistics).
8.3. Получить список пользователей
text
GET /references/users
Headers:

text
Authorization: Bearer <token>
Права: Только для администраторов (в MVP — для всех с ролью выше guest)

Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "username": "ivanov",
            "email": "ivanov@company.ru",
            "full_name": "Иванов Иван",
            "role": "commercial",
            "department": "Коммерческий отдел",
            "department_id": "66111111-1111-1111-1111-111111111111",
            "is_active": true
        }
    ]
}
8.4. Получить список подразделений
text
GET /references/departments
Headers:

text
Authorization: Bearer <token>
Права: все авторизованные.

Query параметры: `is_active` (boolean, по умолчанию true).

Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "66111111-1111-1111-1111-111111111111",
            "name": "Коммерческий отдел",
            "is_active": true
        }
    ]
}
8.5. Скачать Excel-шаблон продуктов
text
GET /references/products/template
Headers:

text
Authorization: Bearer <token>
Права: pp, economist, logistics

Response (200): файл application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

Колонки шаблона: code, name, status, children_code, parent_code, category, mark_control, gtin, plant_id, weight_kg

8.6. Загрузить продукты из Excel
text
POST /references/products/upload
Headers:

text
Authorization: Bearer <token>
Content-Type: multipart/form-data
Права: pp, economist, logistics

Form-data: file — .xlsx или .xls

Правила ячеек:
- status: «Активный» → is_active=true, пустая → false
- mark_control: «да» → true, «нет» → false
- gtin: пусто или ровно 13 цифр; **не уникален** (родитель и потомок могут иметь один GTIN)
- parent_code / children_code: целые или пусто; **не проверяются** на наличие в БД (ссылка сохраняется как есть)
- обязательные при создании: `code` (уникальный PK), `name` (не пустой), `category` (A/B/C); `plant_id` и `weight_kg` нужны новым строкам из‑за NOT NULL в таблице
- по code: существующая запись обновляется, иначе создаётся

Response (200):

json
{
    "status": "success",
    "data": {
        "created": 2,
        "updated": 3,
        "errors": 1,
        "message": "Загружено 5, ошибок 1",
        "error_details": [
            {"row": 4, "message": "GTIN должен содержать 13 цифр"}
        ]
    }
}
8.7. Получить продукт для редактирования
text
GET /references/products/{code}/edit
Headers:

text
Authorization: Bearer <token>
Права: pp, economist, logistics

Response (200):

json
{
    "status": "success",
    "data": {
        "code": 10001,
        "name": "Подшипник 6204ZZ",
        "description": null,
        "category": "A",
        "plant_id": 1001,
        "plant_name": "Завод Московский",
        "second_plant_id": null,
        "third_plant_id": null,
        "weight_kg": 0.25,
        "monthly_consumption": 1000,
        "is_active": true,
        "parent_code": null,
        "children_code": 10004,
        "gtin": "4601234567890",
        "mark_control": false,
        "last_modified_by": {
            "id": "22222222-2222-2222-2222-222222222222",
            "full_name": "Петров Петр"
        },
        "last_modified_at": "2026-08-20T12:00:00Z"
    }
}
8.8. Обновить продукт
text
PUT /references/products/{code}
Headers:

text
Authorization: Bearer <token>
Права: pp, economist, logistics

Поле code не изменяется. Тело:

json
{
    "name": "Подшипник 6204ZZ",
    "description": null,
    "category": "A",
    "is_active": true,
    "weight_kg": 0.25,
    "monthly_consumption": 1000,
    "gtin": "4601234567890",
    "mark_control": false,
    "plant_id": 1001,
    "second_plant_id": null,
    "third_plant_id": null,
    "parent_code": null,
    "children_code": 10004
}
Валидация: категория A/B/C, вес > 0, GTIN пусто или ровно 13 цифр (дубликаты разрешены), parent_code/children_code не проверяются на существование.

Response (200): тот же объект, что GET .../edit. last_modified_by/at обновляются.

8.9. Удалить продукт
text
DELETE /references/products/{code}
Headers:

text
Authorization: Bearer <token>
Права: pp, economist, logistics

Soft delete (deleted_at). Если есть связанные записи в normatives, request_items или available_balances — 409:

json
{
    "status": "error",
    "error": {
        "code": "HAS_RELATIONS",
        "message": "Нельзя удалить продукт: есть связанные нормативы, позиции запросов или остатки"
    }
}
Response (200):

json
{
    "status": "success",
    "message": "Продукт удален"
}
8.10. Создать объект
text
POST /references/objects
Headers:

text
Authorization: Bearer <token>
Права: logistics

Тело:

json
{
    "code": 3001,
    "name": "Склад Тестовый",
    "city": "Москва",
    "region": null,
    "address": null,
    "type": "warehouse",
    "erp_warehouse_code": "T001",
    "loading_point": "2T01",
    "is_active": true,
    "long_distance": false
}
Правила:
- `code` — целое число > 0, уникален (иначе 409 ALREADY_EXISTS)
- `name`, `city` — не пустые
- `type` — `plant` или `warehouse`
- для `plant`: `erp_plant_code` обязателен, 4 цифры (1000-9999)
- для `warehouse`: `erp_warehouse_code` обязателен, 4 символа (буквы/цифры)
- `erp_plant_code`, `erp_warehouse_code` и `loading_point` можно заполнять для **любого** типа объекта
- `loading_point` — опционально, если заполнен: 4 символа (буквы/цифры); уникален среди неудалённых объектов (иначе 409 CONFLICT «Пункт отгрузки уже используется»). Пустые значения могут повторяться
- `erp_plant_code` и `erp_warehouse_code` **не** уникальны: одинаковые коды ERP можно задать нескольким объектам
- `is_active` по умолчанию true
- `long_distance` — признак удалённого склада (по умолчанию false). Имеет смысл только для `type = warehouse`; для `plant` всегда сохраняется false
- невалидные ERP-поля → 400 VALIDATION_ERROR
- `last_modified_by` / `last_modified_at` заполняются автоматически

Response (200): тот же объект, что GET .../edit.

8.11. Получить объект для редактирования
text
GET /references/objects/{code}/edit
Headers:

text
Authorization: Bearer <token>
Права: logistics

Response (200):

json
{
    "status": "success",
    "data": {
        "code": 3001,
        "name": "Склад Тестовый",
        "city": "Москва",
        "region": null,
        "address": null,
        "type": "warehouse",
        "erp_plant_code": null,
        "erp_warehouse_code": "T001",
        "loading_point": "2T01",
        "is_active": true,
        "long_distance": false,
        "last_modified_by": {
            "id": "44444444-4444-4444-4444-444444444444",
            "full_name": "Кузнецов Кузьма"
        },
        "last_modified_at": "2026-08-20T12:00:00Z"
    }
}
8.12. Обновить объект
text
PUT /references/objects/{code}
Headers:

text
Authorization: Bearer <token>
Права: logistics

Поле `code` не изменяется. Переданные поля обновляются; непереданные сохраняют текущие значения.

json
{
    "name": "Склад Тестовый (обновлён)",
    "city": "Санкт-Петербург",
    "region": "Санкт-Петербург",
    "address": null,
    "type": "warehouse",
    "erp_warehouse_code": "T009",
    "loading_point": "2T09",
    "is_active": true,
    "long_distance": true
}
Валидация: name/city не пустые, type = plant|warehouse, те же правила ERP что при создании. ERP-коды можно менять.

Response (200): тот же объект, что GET .../edit. last_modified_by/at обновляются.

8.13. Удалить объект
text
DELETE /references/objects/{code}
Headers:

text
Authorization: Bearer <token>
Права: logistics

Soft delete (deleted_at). Если есть связанные записи в products (plant_id / second_plant_id / third_plant_id), request_items, normatives или available_balances — 409:

json
{
    "status": "error",
    "error": {
        "code": "HAS_RELATIONS",
        "message": "Нельзя удалить объект: есть связанные продукты, позиции запросов, нормативы или остатки"
    }
}
Response (200):

json
{
    "status": "success",
    "message": "Объект удален"
}
9. АДМИНИСТРИРОВАНИЕ ПОЛЬЗОВАТЕЛЕЙ

Управление учётными записями и подразделениями — роль `logistics`. Все эндпоинты защищены `require_roles("logistics")`.

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| GET | `/admin/users` | Список пользователей (с фильтрами) | `logistics` |
| POST | `/admin/users` | Создать пользователя | `logistics` |
| GET | `/admin/users/{id}` | Получить пользователя для редактирования | `logistics` |
| PUT | `/admin/users/{id}` | Обновить пользователя | `logistics` |
| DELETE | `/admin/users/{id}` | Удалить пользователя (soft delete) | `logistics` |
| POST | `/admin/users/{id}/reset-password` | Сбросить пароль | `logistics` |
| GET | `/admin/departments` | Список подразделений | `logistics` |
| POST | `/admin/departments` | Создать подразделение | `logistics` |
| PUT | `/admin/departments/{id}` | Переименовать подразделение | `logistics` |
| DELETE | `/admin/departments/{id}` | Удалить подразделение (soft delete) | `logistics` |

9.1. Список пользователей
text
GET /admin/users
Headers:

text
Authorization: Bearer <token>
Права: только logistics. Остальные роли — 403 FORBIDDEN.

Query параметры:

Параметр	Тип	Описание
search	string	Поиск по username, email, full_name (ILIKE)
role	string	commercial / pp / economist / logistics / guest
department_id	uuid	Подразделение
is_active	boolean	Фильтр по `is_active` (среди неудалённых, если `deleted` не true)
deleted	boolean	Если true — только мягко удалённые (`deleted_at` задан). По умолчанию удалённые скрыты
page	integer	Страница (по умолчанию 1)
limit	integer	Записей на страницу (по умолчанию 50)

Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "username": "ivanov",
            "email": "ivanov@company.ru",
            "full_name": "Иванов Иван",
            "role": "commercial",
            "department_id": "66111111-1111-1111-1111-111111111111",
            "department_name": "Коммерческий отдел",
            "is_active": true,
            "created_at": "2026-08-18T09:00:00Z",
            "deleted_at": null
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 5
    }
}
9.2. Создать пользователя
text
POST /admin/users
Права: logistics.

Request:

json
{
    "username": "sidorova",
    "email": "sidorova@company.ru",
    "full_name": "Сидорова Анна",
    "role": "commercial",
    "department_id": "66111111-1111-1111-1111-111111111111",
    "password": "secure_password"
}
Правила:
- `username` и `email` уникальны (иначе 409 ALREADY_EXISTS)
- пароль хешируется bcrypt, в ответе не возвращается
- `role` ∈ commercial / pp / economist / logistics / guest
- `department_id` опционален; если задан — подразделение должно существовать
- денормализованное поле `users.department` заполняется именем подразделения

Response (201): объект пользователя (как в 9.1), без пароля.

9.3. Получить пользователя
text
GET /admin/users/{id}
Права: logistics. 404, если пользователь не найден.

Response (200): тот же объект, что в списке.

9.4. Обновить пользователя
text
PUT /admin/users/{id}
Права: logistics. Поле `username` не изменяется.

Request:

json
{
    "email": "sidorova@company.ru",
    "full_name": "Сидорова Анна Петровна",
    "role": "pp",
    "department_id": "66222222-2222-2222-2222-222222222222",
    "is_active": true
}
Правила:
- `email` уникален среди других пользователей (иначе 409)
- нельзя сменить роль последнего активного логиста на другую (400 LAST_LOGISTICS)
- нельзя деактивировать последнего активного логиста (400 LAST_LOGISTICS)
- обновление удалённого пользователя — 400

Response (200): обновлённый пользователь.

9.5. Удалить пользователя
text
DELETE /admin/users/{id}
Права: logistics. Soft delete: `deleted_at = NOW()`.

Проверки:
- нельзя удалить себя (400 CANNOT_DELETE_SELF)
- нельзя удалить последнего активного логиста (400 LAST_LOGISTICS)
- повторное удаление — 404

Response (200):

json
{
    "status": "success",
    "message": "Пользователь удален"
}
9.6. Сбросить пароль
text
POST /admin/users/{id}/reset-password
Права: logistics.

Генерирует новый пароль из 8 символов (буквы и цифры), хеширует и сохраняет. Действующие сессии пользователя отзываются. Новый пароль возвращается **один раз**.

Response (200):

json
{
    "status": "success",
    "data": {
        "new_password": "aB3kP9xQ"
    }
}
Errors: 404 — пользователь не найден; 400 — пользователь удалён.

9.7. Список подразделений
text
GET /admin/departments
Права: logistics. Используется на странице подразделений и в выпадающем списке при создании/редактировании пользователя.

Возвращаются все неудалённые подразделения (включая неактивные), с количеством назначенных неудалённых пользователей.

Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "66111111-1111-1111-1111-111111111111",
            "name": "Коммерческий отдел",
            "is_active": true,
            "users_count": 3
        }
    ]
}
9.8. Создать подразделение
text
POST /admin/departments
Права: logistics.

Request:

json
{
    "name": "Отдел логистики"
}
Правила:
- `name` обрезается по краям, не может быть пустым
- название уникально среди неудалённых подразделений (иначе 409 ALREADY_EXISTS)
- `is_active` всегда true при создании

Response (201): объект подразделения (как в 9.7).

9.9. Переименовать подразделение
text
PUT /admin/departments/{id}
Права: logistics. 404, если подразделение не найдено или удалено.

Request:

json
{
    "name": "Коммерческий блок"
}
Правила:
- название уникально среди других неудалённых (иначе 409 ALREADY_EXISTS)
- денормализованное поле `users.department` обновляется у всех пользователей с этим `department_id`

Response (200): обновлённое подразделение.

9.10. Удалить подразделение
text
DELETE /admin/departments/{id}
Права: logistics. Soft delete: `deleted_at = NOW()`.

Проверки:
- нельзя удалить, если есть неудалённые пользователи с этим `department_id` (409 HAS_RELATIONS)
- исторические запросы (`requests.department_id`) удаление не блокируют
- повторное удаление — 404

Response (200):

json
{
    "status": "success",
    "message": "Подразделение удалено"
}

10. УПРАВЛЕНИЕ ОСТАТКАМИ
На MVP загрузка остатков выполняется через `POST /logistics/normative/upload` (Excel ERP, поля `available` и `plan`). Эндпоинты `/inventory/*` **не реализованы**.

11. ИНТЕГРАЦИЯ С ТАРИФАМИ (ЗАДЕЛ, НЕ РЕАЛИЗОВАНО)
`GET /tariffs/delivery` в MVP отсутствует. Экономист принимает решение без отображения тарифов.

12. ИСТОРИЯ И АУДИТ
12.1. Получить историю изменений запроса
text
GET /requests/{request_id}/history
Headers:

text
Authorization: Bearer <token>
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "item_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "field_name": "quantity_approved",
            "old_value": 1000,
            "new_value": 800,
            "changed_by": {
                "id": "22222222-2222-2222-2222-222222222222",
                "full_name": "Петров Петр"
            },
            "changed_at": "2026-08-18T09:30:00Z",
            "comment": "Снижаем объем на 20%"
        }
    ]
}
13. ЗАДЕЛ ПОД АГЕНТА ЛОГИСТА
Таблица `events` создана, триггеры пишут события. HTTP-эндпоинты `/agent/events` и `/agent/events/{id}/process` в MVP **не реализованы**.

14. СВОДКА ЭНДПОИНТОВ
14.1. Группировка по функционалу (реализовано)
Группа	Эндпоинты	Количество
Аутентификация	/auth/login, logout, refresh, profile, change-password	5
Запросы	/requests, /requests/{id}, submit, history, expiry-date	7
Согласование (ПП)	/approvals/pp/pending, /approvals/pp/{id}/action	2
Согласование (экономист)	/approvals/economy/pending, /approvals/economy/{id}/action	2
Логистика нормативы	dashboard, upload, sync-info, export, generate-orders, /{wh}/generate-orders	6
Логистика разовые	list, initiators, clients, export, execute	5
Нормативы	/normatives, on-date, calculate	3
Продукты (related)	/products/{code}/related	1
Справочники продукты	list, template, upload, get, edit, put, delete	7
Справочники объекты	list, create, get, edit, put, delete	6
Справочники пользователи	/references/users	1
Справочники подразделения	/references/departments	1
Администрирование	/admin/users, /admin/users/{id}, reset-password, /admin/departments	10
Партии нормативов	/production-requests, template, upload, dates, delete	5
ИТОГО реализовано		~61
Не реализовано (задел)	/inventory/*, /tariffs/*, /agent/*, /auth/register	—
14.2. Ролевой доступ
Роль	Доступные эндпоинты
guest	Просмотр справочников, нормативов и дашборда логистики (только чтение)
commercial	Создание запросов (нормативные + разовые), просмотр своих запросов, просмотр логистики (только чтение)
pp	Согласование (ПП), просмотр всех запросов, CRUD продуктов, Excel-загрузка, просмотр логистики, управление партиями нормативов
economist	Согласование (экономист), просмотр всех запросов, CRUD продуктов, Excel-загрузка, просмотр логистики, управление партиями нормативов
logistics	Дашборд, формирование заказов, исполнение разовых, выгрузка Excel, загрузка остатков, CRUD продуктов и объектов, управление партиями нормативов, администрирование пользователей и подразделений (`/admin/*`)
15. ПРИМЕР ПОЛНОГО FLOW
15.1. Нормативный запас — полный цикл
text
1. Коммерция: POST /requests → создает черновик (draft)
2. Коммерция: POST /requests/{id}/submit → отправляет на ПП
3. ПП: GET /approvals/pp/pending → видит запрос
4. ПП: POST /approvals/pp/{id}/action (approve) → утверждает
5. Экономист: GET /approvals/economy/pending → видит запрос
6. Экономист: POST /approvals/economy/{id}/action (approve) → утверждает
7. Автоматически: создается запись в normatives (сервис при approve экономиста; в БД также есть триггер)
8. Логист: GET /logistics/normative/dashboard → видит дефицит
9. Логист: POST /logistics/normative/generate-orders → формирует заказы
10. Логист: GET /logistics/normative/export → выгружает Excel
15.2. Разовое перемещение — полный цикл
text
1. Коммерция/Логист: POST /requests → создает разовый запрос (draft)
2. Коммерция/Логист: POST /requests/{id}/submit → отправляет на ПП (статус pp_approved)
3. ПП: GET /approvals/pp/pending → видит запрос
4. ПП: POST /approvals/pp/{id}/action (approve) → утверждает
5. Экономист: GET /approvals/economy/pending → видит запрос
6. Экономист: POST /approvals/economy/{id}/action (approve) → утверждает → статус approved
7. Логист: GET /logistics/one-time/list → видит запрос
8. Логист: POST /logistics/one-time/{id}/execute → отмечает исполненным
15.3. Excel-партия нормативов
text
1. ПП / экономист / логист: GET /production-requests/template → скачивает шаблон
2. POST /production-requests/upload (file, valid_from, valid_to, client_name?) → партия + нормативы
3. GET /normatives и GET /logistics/normative/dashboard → новые нормативы видны с даты valid_from
4. PATCH /production-requests/{id}/dates → меняет период и expiry_date нормативов
5. DELETE /production-requests/{id} → партия и нормативы удалены каскадом
16. ПРОИЗВОДСТВЕННЫЕ ЗАПРОСЫ (ПАРТИИ EXCEL)

Доступ ко всем эндпоинтам: `logistics`, `economist`, `pp` (`require_roles`). Остальные роли — 403.

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/production-requests` | Список партий (пагинация) |
| GET | `/production-requests/template` | Excel-шаблон |
| POST | `/production-requests/upload` | Загрузить партию |
| PATCH | `/production-requests/{id}/dates` | Изменить период партии |
| DELETE | `/production-requests/{id}` | Удалить партию каскадом |

Правило дат: `valid_from <= valid_to`. Исторический `valid_from` разрешён (не обязан быть ≥ сегодня).

16.1. Список партий
text
GET /production-requests
Query: `page` (default 1), `limit` (default 50, max 200). Сортировка: `created_at` DESC. Только неудалённые (`deleted_at IS NULL`).

Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "batch_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "source": "excel_upload",
            "uploaded_by": {
                "id": "22222222-2222-2222-2222-222222222222",
                "username": "pp",
                "full_name": "Петров Петр",
                "role": "pp",
                "department": "Планирование производства",
                "department_id": "66222222-2222-2222-2222-222222222222"
            },
            "client_name": "ООО 'Ромашка'",
            "valid_from": "2026-08-01",
            "valid_to": "2026-11-01",
            "status": "active",
            "items_count": 2,
            "created_at": "2026-08-25T10:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 1
    }
}

16.2. Скачать Excel-шаблон
text
GET /production-requests/template
Response (200): `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
Файл: `production_normatives_template.xlsx`

Колонки шаблона (порядок фиксирован): `Завод ERP`, `Склад ERP`, `Артикул`, `Количество`, `Ед.`, `Клиент`.

16.3. Загрузить партию
text
POST /production-requests/upload
Content-Type: multipart/form-data
Права: logistics, economist, pp.

Form-data:

Поле	Тип	Обязательное	Описание
file	file	✅	Excel `.xlsx` / `.xls`, максимум 10 МБ
valid_from	date	✅	Начало действия
valid_to	date	✅	Окончание действия
client_name	string	❌	Общий клиент (если в строке Excel клиент пуст)

Правила файла:
- первые три колонки обязательны и идут в порядке `Завод ERP`, `Склад ERP`, `Артикул`;
- далее обязательны `Количество`, `Ед.`; колонка `Клиент` необязательна;
- склад определяется по паре `objects.erp_plant_code` + `objects.erp_warehouse_code`;
- принимаются только активные завод, склад и товар;
- клиент строки имеет приоритет над общим `client_name`;
- единицы: `шт` / `кг` / `т` (и синонимы Excel);
- строки независимы: валидные загружаются, невалидные — в `error_details` `{row, message}`.

Если `valid_to < valid_from` — 400 INVALID_DATES. Если файл не Excel / пустой / > 10 МБ — 400 INVALID_FILE. Если все содержательные строки невалидны, партия не создаётся: `production_request` = `null`, ошибки возвращаются.

Response (201):

json
{
    "status": "success",
    "data": {
        "production_request": {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "batch_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "source": "excel_upload",
            "uploaded_by": {
                "id": "22222222-2222-2222-2222-222222222222",
                "username": "pp",
                "full_name": "Петров Петр",
                "role": "pp"
            },
            "client_name": "ООО 'Ромашка'",
            "valid_from": "2026-08-01",
            "valid_to": "2026-11-01",
            "status": "active",
            "items_count": 2,
            "created_at": "2026-08-25T10:00:00Z",
            "items": [
                {
                    "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "product_code": 10001,
                    "warehouse_code": 2401005,
                    "quantity": 1000,
                    "unit": "шт",
                    "client_name": "ООО 'Ромашка'",
                    "category": "A"
                }
            ]
        },
        "total_rows": 4,
        "imported_count": 2,
        "error_count": 2,
        "message": "Загружено 2 строк из 4",
        "error_details": [
            {"row": 4, "message": "активный артикул 99999999 не найден"},
            {"row": 5, "message": "Количество: ожидается число"}
        ]
    }
}

Для каждой импортированной строки создаётся активный норматив: `request_id` = NULL, `production_request_item_id` задан, `expiry_date` = `valid_to`.

16.4. Изменить даты партии
text
PATCH /production-requests/{id}/dates
Request:

json
{
    "valid_from": "2026-08-15",
    "valid_to": "2026-12-15"
}

Обновляет `valid_from` / `valid_to` партии и `expiry_date` всех связанных нормативов (= `valid_to`). 404, если партия не найдена. 422, если `valid_to < valid_from`.

Response (200): `ProductionRequestDetail` (как объект `production_request` в 16.3).

16.5. Удалить партию
text
DELETE /production-requests/{id}
Физическое удаление (`session.delete`). Позиции и нормативы снимаются каскадом. 404, если партия не найдена.

Response (200):

json
{
    "status": "success",
    "message": "Партия загрузки удалена"
}

Версия: 1.9
Дата: 25.08.2026
Статус: Утверждена