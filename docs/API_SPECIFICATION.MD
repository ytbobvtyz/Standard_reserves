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
            "department": "Отдел продаж"
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
        "department": "Отдел продаж",
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
        "expiry_date": "2026-12-31",
        "items": [
            {
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "product_code": 10001,
                "warehouse_code": 2001,
                "quantity_requested": 1000,
                "quantity_approved": null,
                "unit": "шт"
            }
        ],
        "created_at": "2026-08-18T09:00:00Z"
    }
}
Errors:

400 — Невалидные данные

400 INVALID_EXPIRY_DATE — `expiry_date` позже 6 месяцев от даты создания

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
                "full_name": "Иванов Иван"
            },
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
            "full_name": "Иванов Иван"
        },
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
                    "name": "Склад Ростов"
                },
                "quantity_requested": 1000,
                "quantity_approved": 800,
                "unit": "шт",
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
        "updated_at": "2026-08-18T09:30:00Z"
    }
}
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
При редактировании черновика `expiry_date` можно изменять без ограничений, кроме базового: максимум 6 месяцев от даты создания (`created_at`). Правило «только уменьшать» на черновик **не** распространяется.

Errors:

400 INVALID_EXPIRY_DATE — `expiry_date` позже created_at + 6 месяцев

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
                    "unit": "шт"
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

1. Подтвердить:

json
{
    "action": "approve",
    "comment": "Объем подтвержден"
}
2. Редактировать объем:

json
{
    "action": "edit",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_approved": 800
        }
    ],
    "comment": "Снижаем объем на 20% из-за ограничений по заводу"
}

`expiry_date` можно передать в `approve` и `edit`. Срок не может превышать 6 месяцев от `created_at`, иначе 400 INVALID_EXPIRY_DATE. Изменение срока пишется в комментарий истории согласования.

3. Отказать:

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

1. Подтвердить (нормативный):

json
{
    "action": "approve",
    "comment": "Экономика приемлема"
}
1. Подтвердить (разовый):

json
{
    "action": "approve",
    "comment": "Доставка экономически обоснована"
}
2. Редактировать/отправить на доработку:

json
{
    "action": "edit",
    "items": [
        {
            "product_code": 10001,
            "warehouse_code": 2001,
            "quantity_approved": 600
        }
    ],
    "comment": "Снижаем объем",
    "expiry_date": "2026-12-31"
}

`expiry_date` можно передать в `approve` и `edit`. Для `approve` действует проверка 6 месяцев от `created_at` (400 INVALID_EXPIRY_DATE).

При `action = 'edit'` для **нормативного** запроса в статусе `economy_check`:
- Можно изменить `expiry_date`
- **Новое значение**:
  - ✅ Должно быть **≤** текущей `expiry_date` (только уменьшать)
  - ✅ Должно быть **≥** текущей даты (`CURRENT_DATE`)
  - ❌ Не может быть больше текущей `expiry_date`
- 400 BAD_REQUEST «Дата окончания не может быть позже текущей» — если новое значение > текущей `expiry_date`
- 400 BAD_REQUEST «Дата окончания не может быть раньше сегодняшнего дня» — если новое значение < `CURRENT_DATE`

3. Отказать:

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
            "deficit_items": [
                {
                    "product_code": 10001,
                    "product_name": "Подшипник 6204ZZ",
                    "category": "A",
                    "normative_quantity": 1000,
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

`available` — доступно (факт − заказы клиентов). `plan` — запланировано (`available` + разнарядки). `deficit` = норматив − `plan`.

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
3	erp_plant_code	Завод ERP → objects.erp_plant_code → objects.code
5	erp_warehouse_code	Склад ERP → objects.erp_warehouse_code → objects.code
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
    "product_codes": [10001, 10002]  // Опционально, если не указаны — все с дефицитом
}
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
            "created_at": "2026-08-18T09:00:00Z"
        }
    ],
    "meta": {
        "page": 1,
        "limit": 50,
        "total": 3
    }
}
6.6. Отметить разовое перемещение как исполненное
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
                    "expiry_date": "2026-12-31"
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
| GET | `/references/products/template` | Скачать Excel-шаблон | pp, economist, logistics |
| POST | `/references/products/upload` | Загрузить продукты из Excel | pp, economist, logistics |
| GET | `/references/products/{code}/edit` | Получить продукт для редактирования | pp, economist, logistics |
| PUT | `/references/products/{code}` | Обновить продукт | pp, economist, logistics |
| DELETE | `/references/products/{code}` | Удалить продукт | pp, economist, logistics |

Управление объектами (Этап 7.2) — роль `logistics`:

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
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
8.2. Получить список объектов (склады/заводы)
text
GET /references/objects
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание
type	string	plant / warehouse
city	string	Город
is_active	boolean	Только активные
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
            "last_modified_at": "2026-08-18T09:00:00Z"
        }
    ]
}
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
            "department": "Отдел продаж",
            "is_active": true
        }
    ]
}
8.4. Скачать Excel-шаблон продуктов
text
GET /references/products/template
Headers:

text
Authorization: Bearer <token>
Права: pp, economist, logistics

Response (200): файл application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

Колонки шаблона: code, name, status, children_code, parent_code, category, mark_control, gtin, plant_id, weight_kg

8.5. Загрузить продукты из Excel
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
8.6. Получить продукт для редактирования
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
8.7. Обновить продукт
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

8.8. Удалить продукт
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
8.9. Создать объект
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
    "is_active": true
}
Правила:
- `code` — целое число > 0, уникален (иначе 409 ALREADY_EXISTS)
- `name`, `city` — не пустые
- `type` — `plant` или `warehouse`
- для `plant`: `erp_plant_code` обязателен, 4 цифры (1000-9999); `erp_warehouse_code` = null
- для `warehouse`: `erp_warehouse_code` обязателен, 4 символа (буквы/цифры); `erp_plant_code` = null
- `loading_point` — опционально, если заполнен: 4 символа (буквы/цифры)
- `erp_plant_code` и `erp_warehouse_code` уникальны в таблице (иначе 409 CONFLICT)
- `is_active` по умолчанию true
- невалидные ERP-поля → 400 VALIDATION_ERROR
- `last_modified_by` / `last_modified_at` заполняются автоматически

Response (200): тот же объект, что GET .../edit.

8.10. Получить объект для редактирования
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
        "last_modified_by": {
            "id": "44444444-4444-4444-4444-444444444444",
            "full_name": "Кузнецов Кузьма"
        },
        "last_modified_at": "2026-08-20T12:00:00Z"
    }
}
8.11. Обновить объект
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
    "is_active": true
}
Валидация: name/city не пустые, type = plant|warehouse, те же правила ERP что при создании. ERP-коды можно менять.

Response (200): тот же объект, что GET .../edit. last_modified_by/at обновляются.

8.12. Удалить объект
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
9. УПРАВЛЕНИЕ ОСТАТКАМИ
На MVP загрузка остатков выполняется через `POST /logistics/normative/upload` (Excel ERP, поля `available` и `plan`). Исторический CSV-эндпоинт `/inventory/upload` не используется.

9.1. Получить остаток по складу
text
GET /inventory/balances
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Обязательный	Описание
warehouse_code	integer	✅	Склад
product_code	integer	❌	Артикул
Response (200):

json
{
    "status": "success",
    "data": {
        "warehouse_code": 2001,
        "warehouse_name": "Склад Ростов",
        "items": [
            {
                "product_code": 10001,
                "product_name": "Подшипник 6204ZZ",
                "available": 600,
                "plan": 600,
                "unit": "шт",
                "last_sync_at": "2026-08-18T08:00:00Z"
            }
        ]
    }
}
10. ИНТЕГРАЦИЯ С ТАРИФАМИ (ЗАДЕЛ)
10.1. Получить тариф доставки
text
GET /tariffs/delivery
Headers:

text
Authorization: Bearer <token>
Права: Экономисты, логисты

Query параметры:

Параметр	Тип	Обязательный	Описание
plant_code	integer	✅	Завод
warehouse_code	integer	✅	Склад
product_code	integer	✅	Артикул
Response (200):

json
{
    "status": "success",
    "data": {
        "plant_code": 1001,
        "plant_name": "Завод Московский",
        "warehouse_code": 2001,
        "warehouse_name": "Склад Ростов",
        "product_code": 10001,
        "product_name": "Подшипник 6204ZZ",
        "delivery_cost": 12.50,           // за единицу
        "delivery_cost_currency": "RUB",
        "storage_cost": 0.98,              // за единицу в месяц
        "storage_cost_currency": "RUB"
    }
}
11. ИСТОРИЯ И АУДИТ
11.1. Получить историю изменений запроса
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
12. ЗАДЕЛ ПОД АГЕНТА ЛОГИСТА
12.1. Получить события (для агента)
text
GET /agent/events
Headers:

text
Authorization: Bearer <token>
Query параметры:

Параметр	Тип	Описание
processed	boolean	Фильтр по статусу обработки
event_type	string	Тип события
limit	integer	Записей на страницу
Response (200):

json
{
    "status": "success",
    "data": [
        {
            "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "event_type": "deficit_detected",
            "request_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "payload": {
                "warehouse_code": 2001,
                "product_code": 10001,
                "deficit": 400,
                "normative_quantity": 1000,
                "available": 600,
                "plan": 600
            },
            "processed": false,
            "created_at": "2026-08-18T11:00:00Z"
        }
    ]
}
12.2. Отметить событие как обработанное
text
POST /agent/events/{event_id}/process
Headers:

text
Authorization: Bearer <token>
Response (200):

json
{
    "status": "success",
    "message": "Событие обработано"
}
13. СВОДКА ЭНДПОИНТОВ
13.1. Группировка по функционалу
Группа	Эндпоинты	Количество
Аутентификация	/auth/*	5
Запросы	/requests/*	7
Согласование (ПП)	/approvals/pp/*	2
Согласование (экономист)	/approvals/economy/*	2
Логистика	/logistics/*	7
Нормативы	/normatives/*	4
Справочники	/references/*	8
Остатки	/inventory/*	2
Тарифы (задел)	/tariffs/*	1
Агент (задел)	/agent/*	2
ИТОГО		35
13.2. Ролевой доступ
Роль	Доступные эндпоинты
guest	Просмотр справочников, нормативов и дашборда логистики (только чтение)
commercial	Создание запросов (нормативные + разовые), просмотр своих запросов, просмотр логистики (только чтение)
pp	Согласование (ПП), просмотр всех запросов, CRUD продуктов, Excel-загрузка, просмотр логистики
economist	Согласование (экономист), просмотр всех запросов, CRUD продуктов, Excel-загрузка, просмотр логистики
logistics	Дашборд, формирование заказов, исполнение разовых, выгрузка Excel, загрузка остатков, CRUD продуктов и объектов
14. ПРИМЕР ПОЛНОГО FLOW
14.1. Нормативный запас — полный цикл
text
1. Коммерция: POST /requests → создает черновик (draft)
2. Коммерция: POST /requests/{id}/submit → отправляет на ПП
3. ПП: GET /approvals/pp/pending → видит запрос
4. ПП: POST /approvals/pp/{id}/action (approve) → утверждает
5. Экономист: GET /approvals/economy/pending → видит запрос
6. Экономист: POST /approvals/economy/{id}/action (approve) → утверждает
7. Автоматически: создается запись в normatives (триггер)
8. Логист: GET /logistics/normative/dashboard → видит дефицит
9. Логист: POST /logistics/normative/{warehouse_code}/generate-orders → формирует заказы
10. Логист: GET /logistics/normative/export → выгружает Excel
14.2. Разовое перемещение — полный цикл
text
1. Коммерция/Логист: POST /requests → создает разовый запрос (draft)
2. Коммерция/Логист: POST /requests/{id}/submit → отправляет на ПП
3. ПП: GET /approvals/pp/pending → видит запрос
4. ПП: POST /approvals/pp/{id}/action (approve) → утверждает
5. Экономист: GET /approvals/economy/pending → видит запрос
6. Экономист: POST /approvals/economy/{id}/action (approve) → утверждает → статус approved
7. Логист: GET /logistics/one-time/list → видит запрос
8. Логист: POST /logistics/one-time/{id}/execute → отмечает исполненным
Версия: 1.1
Дата: 22.08.2026
Статус: На согласовании