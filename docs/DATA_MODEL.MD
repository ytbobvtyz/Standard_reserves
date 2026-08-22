# DATA_MODEL.md
## Standart Reserve — Модель данных

---

## 1. ОБЩИЕ ПРИНЦИПЫ

### 1.1. Соглашения

| Правило | Описание |
|---------|----------|
| **Первичные ключи** | `INTEGER` для справочников (артикулы, коды объектов), `UUID` для транзакционных таблиц |
| **Временные метки** | `TIMESTAMP WITH TIME ZONE` (храним в UTC) |
| **Мягкое удаление** | Используем `deleted_at TIMESTAMP` вместо физического удаления |
| **Аудит** | История позиций — в `request_item_history`; изменения номенклатуры — в `audit_log` |
| **Индексы** | По всем foreign key и часто фильтруемым полям |
| **Наименования** | snake_case, английские названия |

### 1.2. Обозначения

| Обозначение | Значение |
|-------------|----------|
| `PK` | Первичный ключ |
| `FK` | Внешний ключ |
| `NOT NULL` | Поле обязательно для заполнения |
| `DEFAULT` | Значение по умолчанию |

---

## 2. ER-ДИАГРАММА (MERMAID)
erDiagram
    %% ============================================
    %% СПРАВОЧНИКИ
    %% ============================================

    products {
        int code PK "артикул (целочисленный)"
        text name "наименование"
        text description "описание"
        char category "A/B/C"
        int plant_id FK "основной завод"
        int second_plant_id FK "второй завод (опционально)"
        int third_plant_id FK "третий завод (опционально)"
        decimal weight_kg "вес 1 шт в кг нетто"
        decimal monthly_consumption "потребление в месяц"
        boolean is_active "активный"
        int parent_code "ссылка на старый артикул (без FK)"
        int children_code "ссылка на новый артикул (без FK)"
        varchar gtin "GTIN-13 (может повторяться)"
        boolean mark_control "Честный знак"
        uuid last_modified_by FK "кто изменил"
        timestamp last_modified_at "когда изменили"
        timestamp created_at "дата создания"
        timestamp updated_at "дата обновления"
        timestamp deleted_at "дата удаления (soft delete)"
    }

    audit_log {
        uuid id PK
        text entity_type "product / ..."
        text entity_id "код сущности"
        text action "create/update/delete/upload"
        uuid changed_by FK
        jsonb payload
        timestamp created_at
    }

    objects {
        int code PK "код объекта"
        text name "наименование"
        text city "город"
        text region "регион"
        text address "адрес"
        varchar type "plant / warehouse"
        int erp_plant_code "ERP завод, 4 цифры"
        varchar erp_warehouse_code "ERP склад, 4 символа"
        varchar loading_point "пункт отгрузки, уникальный"
        boolean is_active "активный"
        uuid last_modified_by FK "кто изменил"
        timestamp last_modified_at "когда изменили"
        timestamp created_at "дата создания"
        timestamp updated_at "дата обновления"
        timestamp deleted_at "дата удаления (soft delete)"
    }

    users {
        uuid id PK "идентификатор"
        varchar username "логин (уникальный)"
        varchar email "email (уникальный)"
        text password_hash "хэш пароля"
        text full_name "ФИО"
        varchar role "commercial/pp/economist/logistics/guest"
        text department "отдел"
        boolean is_active "активный"
        timestamp last_login_at "последний вход"
        timestamp created_at "дата создания"
        timestamp updated_at "дата обновления"
        timestamp deleted_at "дата удаления (soft delete)"
    }

    sessions {
        uuid id PK "идентификатор"
        uuid user_id FK "пользователь"
        text token "токен сессии (уникальный)"
        inet ip_address "IP-адрес"
        text user_agent "User-Agent"
        timestamp expires_at "срок действия"
        timestamp created_at "дата создания"
        timestamp revoked_at "дата отзыва"
    }

    password_reset_tokens {
        uuid id PK "идентификатор"
        uuid user_id FK "пользователь"
        text token "токен сброса (уникальный)"
        timestamp expires_at "срок действия"
        boolean used "использован"
        timestamp created_at "дата создания"
    }

    %% ============================================
    %% ЗАПРОСЫ И СОГЛАСОВАНИЯ
    %% ============================================

    requests {
        uuid id PK "идентификатор"
        varchar request_type "normative / one_time"
        varchar status "draft/pp_approved/economy_check/active/approved/rejected/expired/executed"
        text client_name "метка авторства"
        uuid initiator_id FK "инициатор"
        text initiator_comment "комментарий инициатора"
        text comment_pp "комментарий ПП"
        text comment_economy "комментарий экономиста"
        date expiry_date "срок действия (только нормативные)"
        timestamp approved_at "дата утверждения"
        timestamp executed_at "дата исполнения"
        timestamp pp_approved_at "дата согласования ПП"
        uuid pp_approved_by FK "кто согласовал от ПП"
        varchar pp_action "approve/reject/edit"
        timestamp economy_approved_at "дата согласования экономиста"
        uuid economy_approved_by FK "кто согласовал от экономистов"
        varchar economy_action "approve/reject/edit"
        timestamp created_at "дата создания"
        timestamp updated_at "дата обновления"
        timestamp deleted_at "дата удаления (soft delete)"
    }

    request_items {
        uuid id PK "идентификатор"
        uuid request_id FK "запрос"
        int product_code FK "артикул"
        int warehouse_code FK "склад"
        decimal quantity_requested "запрошенный объем"
        decimal quantity_approved "утвержденный объем"
        varchar unit "шт / т"
        text comment "комментарий по позиции"
        timestamp created_at "дата создания"
        timestamp updated_at "дата обновления"
    }

    request_item_history {
        uuid id PK "идентификатор"
        uuid request_item_id FK "позиция запроса"
        varchar field_name "quantity_requested / quantity_approved"
        decimal old_value "старое значение"
        decimal new_value "новое значение"
        uuid changed_by FK "кто изменил"
        timestamp changed_at "дата изменения"
        text comment "комментарий"
    }

    %% ============================================
    %% НОРМАТИВЫ И ОСТАТКИ
    %% ============================================

    normatives {
        uuid id PK "идентификатор"
        uuid request_id FK "запрос-основание"
        int product_code FK "артикул"
        int warehouse_code FK "склад"
        decimal quantity "утвержденный объем"
        varchar unit "шт / т"
        text client_name "метка авторства"
        date expiry_date "срок действия"
        char category "A/B/C"
        timestamp created_at "дата создания"
        timestamp updated_at "дата обновления"
        timestamp deleted_at "дата удаления (soft delete)"
    }

    available_balances {
        int warehouse_code PK "склад"
        int product_code PK "артикул"
        decimal available "доступно (факт - заказы клиентов)"
        decimal plan "запланировано (available + разнарядки)"
        varchar unit "шт / т"
        timestamp last_sync_at "дата последней синхронизации"
        varchar source "manual / csv / excel / erp_api"
    }

    sync_metadata {
        int id PK "всегда 1 (singleton)"
        timestamp last_balances_sync_at "дата последней загрузки остатков"
        uuid last_balances_sync_by FK "кто загрузил"
        timestamp updated_at "дата обновления записи"
    }

    %% ============================================
    %% БУДУЩИЙ АГЕНТ
    %% ============================================

    events {
        uuid id PK "идентификатор"
        varchar event_type "request_created/approved/rejected/normative_active/expired/deficit_detected"
        uuid request_id FK "запрос"
        jsonb payload "данные события"
        boolean processed "обработано"
        timestamp processed_at "дата обработки"
        timestamp created_at "дата создания"
    }

    %% ============================================
    %% СВЯЗИ
    %% ============================================

    %% Логическая самосвязь products (без FK: коды могут появиться позже)
    products ||--o{ products : "parent_code / children_code"

    %% Products → Objects (заводы)
    products }o--|| objects : "plant_id"
    products }o--|| objects : "second_plant_id"
    products }o--|| objects : "third_plant_id"
    products }o--o| users : "last_modified_by"
    objects }o--o| users : "last_modified_by"
    users ||--o{ audit_log : "changed_by"

    %% Users → Sessions
    users ||--o{ sessions : "имеет"
    users ||--o{ password_reset_tokens : "имеет"

    %% Requests → Users
    requests }o--|| users : "initiator_id"
    requests }o--|| users : "pp_approved_by"
    requests }o--|| users : "economy_approved_by"

    %% Requests → Request Items
    requests ||--o{ request_items : "содержит"

    %% Request Items → Products / Objects
    request_items }o--|| products : "product_code"
    request_items }o--|| objects : "warehouse_code"

    %% Request Items → History
    request_items ||--o{ request_item_history : "имеет"

    %% History → Users
    request_item_history }o--|| users : "changed_by"

    %% Normatives → Requests / Products / Objects
    normatives }o--|| requests : "request_id"
    normatives }o--|| products : "product_code"
    normatives }o--|| objects : "warehouse_code"

    %% Available Balances → Products / Objects
    available_balances }o--|| products : "product_code"
    available_balances }o--|| objects : "warehouse_code"

    %% Sync metadata → Users
    users ||--o| sync_metadata : "last_balances_sync_by"

    %% Events → Requests
    events }o--|| requests : "request_id"
    
3. СПРАВОЧНИКИ
3.1. products — Номенклатура
Хранит информацию о продукции. Артикул (code) является первичным ключом.

sql
CREATE TABLE products (
    code INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category CHAR(1) NOT NULL CHECK (category IN ('A', 'B', 'C')),
    plant_id INTEGER NOT NULL REFERENCES objects(code),
    second_plant_id INTEGER REFERENCES objects(code),
    third_plant_id INTEGER REFERENCES objects(code),
    weight_kg DECIMAL(12,4) NOT NULL,
    monthly_consumption DECIMAL(12,2),
    is_active BOOLEAN DEFAULT true,
    parent_code INTEGER,
    children_code INTEGER,
    gtin VARCHAR(13),
    mark_control BOOLEAN DEFAULT false,
    last_modified_by UUID REFERENCES users(id),
    last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_plant_id ON products(plant_id);
CREATE INDEX idx_products_is_active ON products(is_active) WHERE is_active = true;
CREATE INDEX idx_products_parent_code ON products(parent_code) WHERE parent_code IS NOT NULL;
CREATE INDEX idx_products_children_code ON products(children_code) WHERE children_code IS NOT NULL;
CREATE INDEX idx_products_gtin ON products(gtin) WHERE gtin IS NOT NULL;
CREATE INDEX idx_products_last_modified_at ON products(last_modified_at);
CREATE INDEX idx_products_last_modified_by ON products(last_modified_by);
Поля:

Поле	Тип	Обязательное	Описание
code	INTEGER	✅	Артикул (PK)
name	TEXT	✅	Наименование
description	TEXT	❌	Описание
category	CHAR(1)	✅	A/B/C
plant_id	INTEGER	✅	Основной завод → objects.code
second_plant_id	INTEGER	❌	Второй завод → objects.code
third_plant_id	INTEGER	❌	Третий завод → objects.code
weight_kg	DECIMAL(12,4)	✅	Вес 1 шт в кг нетто
monthly_consumption	DECIMAL(12,2)	❌	Потребление в месяц
is_active	BOOLEAN	✅	Активный (по умолчанию true)
parent_code	INTEGER	❌	Ссылка на старый артикул (логическая, без FK; код может ещё не существовать)
children_code	INTEGER	❌	Ссылка на новый артикул (логическая, без FK; код может ещё не существовать)
gtin	VARCHAR(13)	❌	GTIN-13, 13 цифр если заполнен; может повторяться у родителя и потомка
mark_control	BOOLEAN	✅	Честный знак (по умолчанию false)
last_modified_by	UUID	❌	Кто изменил → users.id
last_modified_at	TIMESTAMP	✅	Когда изменили
created_at	TIMESTAMP	✅	Дата создания
updated_at	TIMESTAMP	✅	Дата обновления
deleted_at	TIMESTAMP	❌	Дата удаления (soft delete)
3.1.1. audit_log — Журнал изменений справочников
sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'upload')),
    changed_by UUID REFERENCES users(id),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_changed_by ON audit_log(changed_by);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
3.2. objects — Объекты (заводы и склады)
Объединенная таблица для заводов и складов. Тип определяется полем type.

sql
CREATE TABLE objects (
    code INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT,
    address TEXT,
    type VARCHAR(20) NOT NULL CHECK (type IN ('plant', 'warehouse')),
    erp_plant_code INTEGER,
    erp_warehouse_code VARCHAR(4),
    loading_point VARCHAR(4),
    is_active BOOLEAN DEFAULT true,
    last_modified_by UUID REFERENCES users(id),
    last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_objects_type ON objects(type);
CREATE INDEX idx_objects_city ON objects(city);
CREATE INDEX idx_objects_last_modified_at ON objects(last_modified_at);
CREATE INDEX idx_objects_last_modified_by ON objects(last_modified_by);
CREATE INDEX idx_objects_erp_plant_code ON objects(erp_plant_code) WHERE erp_plant_code IS NOT NULL;
CREATE INDEX idx_objects_erp_warehouse_code ON objects(erp_warehouse_code) WHERE erp_warehouse_code IS NOT NULL;
CREATE UNIQUE INDEX uq_objects_loading_point ON objects(loading_point)
    WHERE loading_point IS NOT NULL AND deleted_at IS NULL;
Поля:

Поле	Тип	Обязательное	Описание
code	INTEGER	✅	Код объекта (PK)
name	TEXT	✅	Наименование
city	TEXT	✅	Город
region	TEXT	❌	Регион
address	TEXT	❌	Адрес
type	VARCHAR(20)	✅	plant или warehouse
erp_plant_code	INTEGER	❌	Номер завода в ERP (4 цифры; обязателен для plant; не уникален)
erp_warehouse_code	VARCHAR(4)	❌	Номер склада в ERP (4 символа; обязателен для warehouse; не уникален)
loading_point	VARCHAR(4)	❌	Пункт отгрузки ERP (4 символа; уникален среди неудалённых, если заполнен)
is_active	BOOLEAN	✅	Активный (по умолчанию true)
last_modified_by	UUID	❌	Кто изменил → users.id
last_modified_at	TIMESTAMP	❌	Когда изменили
created_at	TIMESTAMP	✅	Дата создания
updated_at	TIMESTAMP	✅	Дата обновления
deleted_at	TIMESTAMP	❌	Дата удаления (soft delete)
3.3. users — Пользователи
sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN (
        'commercial', 'pp', 'economist', 'logistics', 'guest'
    )),
    department TEXT,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;


Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
username	VARCHAR(100)	✅	Логин (уникальный)
email	VARCHAR(255)	✅	Email (уникальный)
password_hash	TEXT	✅	Хэш пароля (bcrypt/argon2)
full_name	TEXT	✅	ФИО
role	VARCHAR(30)	✅	commercial / pp / economist / logistics / guest
department	TEXT	❌	Отдел
is_active	BOOLEAN	✅	Активный (по умолчанию true)
last_login_at	TIMESTAMP	❌	Последний вход
created_at	TIMESTAMP	✅	Дата создания
updated_at	TIMESTAMP	✅	Дата обновления
deleted_at	TIMESTAMP	❌	Дата удаления (soft delete)

3.4. sessions — сессии пользователей
sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_revoked_at ON sessions(revoked_at) WHERE revoked_at IS NULL;


Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
user_id	UUID	✅	Пользователь → users.id (ON DELETE CASCADE)
token	TEXT	✅	Токен сессии (уникальный)
ip_address	INET	❌	IP-адрес
user_agent	TEXT	❌	User-Agent
expires_at	TIMESTAMP	✅	Срок действия
created_at	TIMESTAMP	✅	Дата создания
revoked_at	TIMESTAMP	❌	Дата отзыва (logout)

3.5. password_reset_tokens — сброс пароля
sql
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);


Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
user_id	UUID	✅	Пользователь → users.id (ON DELETE CASCADE)
token	TEXT	✅	Токен сброса (уникальный)
expires_at	TIMESTAMP	✅	Срок действия
used	BOOLEAN	✅	Использован (по умолчанию false)
created_at	TIMESTAMP	✅	Дата создания

ИТОГОВАЯ СВОДКА ПОЛЬЗОВАТЕЛЬСКИХ ТАБЛИЦ
Таблица	Назначение
users	Хранит логины, пароли, роли
sessions	Активные сессии (JWT или токены)
password_reset_tokens	Токены для восстановления пароля

4. ОСНОВНЫЕ ТАБЛИЦЫ
4.1. requests — Запросы
sql
CREATE TABLE requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type VARCHAR(20) NOT NULL CHECK (request_type IN ('normative', 'one_time')),
    status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',
        'pp_approved',
        'economy_check',
        'pp_rework',
        'economy_rework',
        'active',
        'approved',
        'rejected',
        'expired',
        'executed'
    )),
    client_name TEXT NOT NULL,
    initiator_id UUID NOT NULL REFERENCES users(id),
    initiator_comment TEXT,
    comment_pp TEXT,
    comment_economy TEXT,
    expiry_date DATE,
    approved_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    pp_approved_at TIMESTAMP WITH TIME ZONE,
    pp_approved_by UUID REFERENCES users(id),
    pp_action VARCHAR(20) CHECK (pp_action IN ('approve', 'reject', 'edit')),
    economy_approved_at TIMESTAMP WITH TIME ZONE,
    economy_approved_by UUID REFERENCES users(id),
    economy_action VARCHAR(20) CHECK (economy_action IN ('approve', 'reject', 'edit')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX idx_requests_status_type ON requests(status, request_type);
CREATE INDEX idx_requests_initiator_id ON requests(initiator_id);
CREATE INDEX idx_requests_client_name ON requests(client_name);
CREATE INDEX idx_requests_created_at ON requests(created_at);
CREATE INDEX idx_requests_expiry_date ON requests(expiry_date) WHERE expiry_date IS NOT NULL;
Поля:

Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
request_type	VARCHAR(20)	✅	normative / one_time
status	VARCHAR(30)	✅	Статус (по умолчанию draft)
client_name	TEXT	✅	Метка авторства
initiator_id	UUID	✅	Инициатор → users.id
initiator_comment	TEXT	❌	Комментарий инициатора
comment_pp	TEXT	❌	Комментарий ПП
comment_economy	TEXT	❌	Комментарий экономиста
expiry_date	DATE	❌	Срок действия (только нормативные), не позже created_at + 6 месяцев
approved_at	TIMESTAMP	❌	Дата утверждения
executed_at	TIMESTAMP	❌	Дата исполнения (разовые)
pp_approved_at	TIMESTAMP	❌	Дата согласования ПП
pp_approved_by	UUID	❌	Кто согласовал от ПП → users.id
pp_action	VARCHAR(20)	❌	approve / reject / edit
economy_approved_at	TIMESTAMP	❌	Дата согласования экономиста
economy_approved_by	UUID	❌	Кто согласовал от экономистов → users.id
economy_action	VARCHAR(20)	❌	approve / reject / edit
created_at	TIMESTAMP	✅	Дата создания
updated_at	TIMESTAMP	✅	Дата обновления
deleted_at	TIMESTAMP	❌	Дата удаления (soft delete)
4.2. request_items — Позиции запроса
sql
CREATE TABLE request_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    product_code INTEGER NOT NULL REFERENCES products(code),
    warehouse_code INTEGER NOT NULL REFERENCES objects(code),
    quantity_requested DECIMAL(12,2) NOT NULL CHECK (quantity_requested > 0),
    quantity_approved DECIMAL(12,2),
    unit VARCHAR(10) NOT NULL CHECK (unit IN ('шт', 'т')),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(request_id, product_code, warehouse_code)
);

-- Индексы
CREATE INDEX idx_request_items_request_id ON request_items(request_id);
CREATE INDEX idx_request_items_product_code ON request_items(product_code);
CREATE INDEX idx_request_items_warehouse_code ON request_items(warehouse_code);
CREATE INDEX idx_request_items_product_warehouse ON request_items(product_code, warehouse_code);
Поля:

Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
request_id	UUID	✅	Запрос → requests.id (ON DELETE CASCADE)
product_code	INTEGER	✅	Артикул → products.code
warehouse_code	INTEGER	✅	Склад → objects.code
quantity_requested	DECIMAL(12,2)	✅	Запрошенный объем (>0)
quantity_approved	DECIMAL(12,2)	❌	Утвержденный объем
unit	VARCHAR(10)	✅	шт или т
comment	TEXT	❌	Комментарий по позиции
created_at	TIMESTAMP	✅	Дата создания
updated_at	TIMESTAMP	✅	Дата обновления
4.3. request_item_history — История изменений позиций
sql
CREATE TABLE request_item_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_item_id UUID NOT NULL REFERENCES request_items(id) ON DELETE CASCADE,
    field_name VARCHAR(30) NOT NULL CHECK (field_name IN ('quantity_requested', 'quantity_approved')),
    old_value DECIMAL(12,2),
    new_value DECIMAL(12,2),
    changed_by UUID NOT NULL REFERENCES users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    comment TEXT
);

CREATE INDEX idx_request_item_history_item_id ON request_item_history(request_item_id);
CREATE INDEX idx_request_item_history_changed_by ON request_item_history(changed_by);
Поля:

Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
request_item_id	UUID	✅	Позиция запроса → request_items.id (ON DELETE CASCADE)
field_name	VARCHAR(30)	✅	quantity_requested / quantity_approved
old_value	DECIMAL(12,2)	❌	Старое значение
new_value	DECIMAL(12,2)	❌	Новое значение
changed_by	UUID	✅	Кто изменил → users.id
changed_at	TIMESTAMP	✅	Дата изменения (по умолчанию NOW())
comment	TEXT	❌	Комментарий
5. ТАБЛИЦЫ ДЛЯ БИЗНЕС-ЛОГИКИ
5.1. normatives — Активные нормативы
Записывается после утверждения запроса. На одном складе и артикуле может быть несколько нормативов под разных клиентов. Расчет на дату суммирует все активные в интервале created_at — expiry_date.

sql
CREATE TABLE normatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES requests(id),
    product_code INTEGER NOT NULL REFERENCES products(code),
    warehouse_code INTEGER NOT NULL REFERENCES objects(code),
    quantity DECIMAL(12,2) NOT NULL,
    unit VARCHAR(10) NOT NULL CHECK (unit IN ('шт', 'т')),
    client_name TEXT NOT NULL,
    expiry_date DATE NOT NULL,
    category CHAR(1) NOT NULL CHECK (category IN ('A', 'B', 'C')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX idx_normatives_product_warehouse ON normatives(product_code, warehouse_code);
CREATE INDEX idx_normatives_product_code ON normatives(product_code);
CREATE INDEX idx_normatives_warehouse_code ON normatives(warehouse_code);
CREATE INDEX idx_normatives_expiry_date ON normatives(expiry_date);
CREATE INDEX idx_normatives_deleted_at ON normatives(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_normatives_created_at ON normatives(created_at);
Поля:

Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
request_id	UUID	✅	Запрос-основание → requests.id
product_code	INTEGER	✅	Артикул → products.code
warehouse_code	INTEGER	✅	Склад → objects.code
quantity	DECIMAL(12,2)	✅	Утвержденный объем
unit	VARCHAR(10)	✅	шт или т
client_name	TEXT	✅	Метка авторства
expiry_date	DATE	✅	Срок действия
category	CHAR(1)	✅	A/B/C
created_at	TIMESTAMP	✅	Дата создания
updated_at	TIMESTAMP	✅	Дата обновления
deleted_at	TIMESTAMP	❌	Дата удаления (soft delete)
5.2. available_balances — Остатки ERP
Загружается из ERP вручную (Excel) на MVP. `available` — доступно к отгрузке (факт минус заказы клиентов). `plan` — запланировано (`available` плюс разнарядки). Дефицит на дашборде: норматив − plan. В будущем — автоматическая синхронизация.

sql
CREATE TABLE available_balances (
    warehouse_code INTEGER NOT NULL REFERENCES objects(code),
    product_code INTEGER NOT NULL REFERENCES products(code),
    available DECIMAL(12,2) NOT NULL DEFAULT 0,
    plan DECIMAL(12,2) NOT NULL DEFAULT 0,
    unit VARCHAR(10) NOT NULL DEFAULT 'шт' CHECK (unit IN ('шт', 'т', 'ШТ', 'КГ')),
    last_sync_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    source VARCHAR(50) DEFAULT 'manual',

    PRIMARY KEY (warehouse_code, product_code)
);

-- Индексы
CREATE INDEX idx_available_balances_warehouse ON available_balances(warehouse_code);
CREATE INDEX idx_available_balances_product ON available_balances(product_code);
CREATE INDEX idx_available_balances_available ON available_balances(available) WHERE available > 0;
Поля:

Поле	Тип	Обязательное	Описание
warehouse_code	INTEGER	✅	Склад → objects.code (PK)
product_code	INTEGER	✅	Артикул → products.code (PK)
available	DECIMAL(12,2)	✅	Доступно: факт − заказы клиентов (по умолчанию 0)
plan	DECIMAL(12,2)	✅	Запланировано: available + разнарядки (по умолчанию 0)
unit	VARCHAR(10)	✅	шт / т / ШТ / КГ (по умолчанию шт; Excel ERP: ШТ или КГ)
last_sync_at	TIMESTAMP	✅	Дата последней синхронизации
source	VARCHAR(50)	❌	manual / csv / excel / erp_api (по умолчанию manual)
5.3. sync_metadata — Метаданные синхронизации
Singleton-таблица (ровно одна строка, `id = 1`). Хранит дату и автора последней загрузки остатков Excel (`POST /logistics/normative/upload`).

sql
CREATE TABLE sync_metadata (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_balances_sync_at TIMESTAMP WITH TIME ZONE,
    last_balances_sync_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sync_metadata_last_balances_sync_by ON sync_metadata(last_balances_sync_by);

INSERT INTO sync_metadata (id) VALUES (1);
Поля:

Поле	Тип	Обязательное	Описание
id	INTEGER	✅	Всегда 1 (PK, CHECK id = 1)
last_balances_sync_at	TIMESTAMP	❌	Дата и время последней загрузки остатков
last_balances_sync_by	UUID	❌	Кто загрузил → users.id
updated_at	TIMESTAMP	✅	Дата обновления записи (по умолчанию NOW())
При загрузке Excel: для складов из файла старые строки `available_balances` удаляются, затем вставляются только строки из файла. После этого обновляются `last_balances_sync_at` и `last_balances_sync_by`.
6. ТАБЛИЦА ДЛЯ БУДУЩЕГО АГЕНТА
6.1. events — События для агента логиста
sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'request_created',
        'request_approved',
        'request_rejected',
        'normative_active',
        'normative_expired',
        'deficit_detected',
        'deficit_resolved'
    )),
    request_id UUID REFERENCES requests(id),
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_events_processed ON events(processed) WHERE processed = false;
CREATE INDEX idx_events_request_id ON events(request_id);
CREATE INDEX idx_events_created_at ON events(created_at);
Поля:

Поле	Тип	Обязательное	Описание
id	UUID	✅	Идентификатор (PK)
event_type	VARCHAR(50)	✅	Тип события
request_id	UUID	❌	Запрос → requests.id
payload	JSONB	✅	Данные события (гибкая структура)
processed	BOOLEAN	✅	Обработано (по умолчанию false)
processed_at	TIMESTAMP	❌	Дата обработки
created_at	TIMESTAMP	✅	Дата создания
7. ФУНКЦИИ
7.1. Пересчет единиц (шт ↔ т)
sql
-- Пересчет количества в тонны
CREATE OR REPLACE FUNCTION convert_to_tons(
    p_product_code INTEGER,
    p_quantity_units DECIMAL(12,2)
) RETURNS DECIMAL(12,2) AS $$
DECLARE
    v_weight DECIMAL(12,4);
BEGIN
    SELECT weight_kg INTO v_weight
    FROM products
    WHERE code = p_product_code;

    RETURN (p_quantity_units * v_weight) / 1000;
END;
$$ LANGUAGE plpgsql;

-- Пересчет количества в штуки
CREATE OR REPLACE FUNCTION convert_to_units(
    p_product_code INTEGER,
    p_quantity_tons DECIMAL(12,2)
) RETURNS DECIMAL(12,2) AS $$
DECLARE
    v_weight DECIMAL(12,4);
BEGIN
    SELECT weight_kg INTO v_weight
    FROM products
    WHERE code = p_product_code;

    RETURN (p_quantity_tons * 1000) / v_weight;
END;
$$ LANGUAGE plpgsql;
7.2. Поиск по цепочке родственных артикулов
Для расчета норматива и остатка по всем родственным артикулам:

sql
CREATE OR REPLACE FUNCTION get_related_products(
    p_product_code INTEGER
) RETURNS TABLE(product_code INTEGER) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE product_tree AS (
        -- Базовый уровень: искомый код
        SELECT code, parent_code, children_code, 1 AS level
        FROM products
        WHERE code = p_product_code
          AND deleted_at IS NULL

        UNION ALL

        -- Вверх по цепочке (parent_code)
        SELECT p.code, p.parent_code, p.children_code, pt.level + 1
        FROM products p
        JOIN product_tree pt ON p.code = pt.parent_code
        WHERE p.deleted_at IS NULL

        UNION ALL

        -- Вниз по цепочке (children_code)
        SELECT p.code, p.parent_code, p.children_code, pt.level + 1
        FROM products p
        JOIN product_tree pt ON p.code = pt.children_code
        WHERE p.deleted_at IS NULL
    )
    SELECT DISTINCT code
    FROM product_tree
    WHERE code != p_product_code;
END;
$$ LANGUAGE plpgsql;
7.3. Расчет норматива для продукта
sql
CREATE OR REPLACE FUNCTION calculate_normative(
    p_product_code INTEGER,
    p_warehouse_code INTEGER
) RETURNS DECIMAL(12,2) AS $$
DECLARE
    v_monthly_consumption DECIMAL(12,2);
    v_category CHAR(1);
    v_result DECIMAL(12,2);
BEGIN
    SELECT monthly_consumption, category
    INTO v_monthly_consumption, v_category
    FROM products
    WHERE code = p_product_code
      AND deleted_at IS NULL;

    IF v_monthly_consumption IS NULL THEN
        RETURN NULL;
    END IF;

    -- Коэффициент удаленности (MVP: всегда 1)
    -- Коэффициент категории
    v_result := v_monthly_consumption * 1 *
        CASE v_category
            WHEN 'A' THEN 1
            WHEN 'B' THEN 1.5
            WHEN 'C' THEN 2
        END;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;
7.4. Автоматическое истечение нормативов
sql
-- Функция для ежедневного обновления статуса expired
CREATE OR REPLACE FUNCTION expire_normatives()
RETURNS void AS $$
BEGIN
    -- Обновляем статус запросов
    UPDATE requests
    SET status = 'expired'
    WHERE status = 'active'
      AND expiry_date < CURRENT_DATE;

    -- Мягко удаляем нормативы
    UPDATE normatives
    SET deleted_at = NOW()
    WHERE deleted_at IS NULL
      AND expiry_date < CURRENT_DATE;

    -- Создаем события для агента
    INSERT INTO events (event_type, request_id, payload)
    SELECT 'normative_expired', id, jsonb_build_object(
        'expiry_date', expiry_date,
        'client_name', client_name
    )
    FROM requests
    WHERE status = 'expired'
      AND NOT EXISTS (
          SELECT 1 FROM events
          WHERE events.request_id = requests.id
            AND events.event_type = 'normative_expired'
            AND events.created_at > CURRENT_DATE - INTERVAL '1 day'
      );
END;
$$ LANGUAGE plpgsql;
8. ВЬЮ ДЛЯ ЛОГИСТА
8.1. Дефицит по складу
sql
CREATE OR REPLACE VIEW deficit_view AS
SELECT
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    p.category,
    n.quantity AS normative_quantity,
    n.unit AS normative_unit,
            COALESCE(ab.available, 0) AS available,
            COALESCE(ab.plan, 0) AS plan,
            COALESCE(ab.unit, 'шт') AS fact_unit,
            (n.quantity - COALESCE(ab.plan, 0)) AS deficit,
            n.expiry_date,
            n.client_name,
            CASE
                WHEN (n.quantity - COALESCE(ab.plan, 0)) > 0 THEN 'warning'
                ELSE 'ok'
            END AS status
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
LEFT JOIN available_balances ab ON n.warehouse_code = ab.warehouse_code AND n.product_code = ab.product_code
WHERE n.deleted_at IS NULL
  AND n.expiry_date >= CURRENT_DATE
  AND (n.quantity - COALESCE(ab.plan, 0)) > 0;
8.2. Нормативы на дату
sql
CREATE OR REPLACE VIEW normatives_on_date AS
SELECT
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    n.quantity,
    n.unit,
    n.client_name,
    n.expiry_date,
    n.category,
    n.created_at,
    (SELECT SUM(n2.quantity)
     FROM normatives n2
     WHERE n2.warehouse_code = n.warehouse_code
       AND n2.product_code = n.product_code
       AND n2.created_at <= :target_date
       AND n2.expiry_date >= :target_date
       AND n2.deleted_at IS NULL
    ) AS total_normative_on_date
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
WHERE n.deleted_at IS NULL;
9. ТРИГГЕРЫ
9.1. Автоматическое создание события при создании запроса
sql
CREATE OR REPLACE FUNCTION trigger_request_created_event()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO events (event_type, request_id, payload)
    VALUES (
        'request_created',
        NEW.id,
        jsonb_build_object(
            'request_type', NEW.request_type,
            'client_name', NEW.client_name,
            'initiator_id', NEW.initiator_id
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER request_created_event
AFTER INSERT ON requests
FOR EACH ROW
EXECUTE FUNCTION trigger_request_created_event();
9.2. Автоматическое создание норматива при утверждении
sql
CREATE OR REPLACE FUNCTION trigger_create_normative()
RETURNS TRIGGER AS $$
DECLARE
    item RECORD;
    v_category CHAR(1);
BEGIN
    -- Только для нормативных запросов
    IF NEW.request_type != 'normative' THEN
        RETURN NEW;
    END IF;

    -- Только при утверждении
    IF NEW.status = 'active' AND OLD.status = 'economy_check' THEN
        FOR item IN
            SELECT
                ri.product_code,
                ri.warehouse_code,
                COALESCE(ri.quantity_approved, ri.quantity_requested) AS quantity,
                ri.unit,
                NEW.client_name,
                NEW.expiry_date
            FROM request_items ri
            WHERE ri.request_id = NEW.id
        LOOP
            -- Получаем категорию продукта
            SELECT category INTO v_category
            FROM products
            WHERE code = item.product_code;

            INSERT INTO normatives (
                request_id,
                product_code,
                warehouse_code,
                quantity,
                unit,
                client_name,
                expiry_date,
                category
            ) VALUES (
                NEW.id,
                item.product_code,
                item.warehouse_code,
                item.quantity,
                item.unit,
                item.client_name,
                item.expiry_date,
                v_category
            );
        END LOOP;

        -- Создаем событие
        INSERT INTO events (event_type, request_id, payload)
        VALUES (
            'normative_active',
            NEW.id,
            jsonb_build_object(
                'expiry_date', NEW.expiry_date,
                'client_name', NEW.client_name
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_normative_on_approve
AFTER UPDATE OF status ON requests
FOR EACH ROW
WHEN (NEW.status = 'active' AND OLD.status = 'economy_check')
EXECUTE FUNCTION trigger_create_normative();
10. МИГРАЦИИ (ПОРЯДОК СОЗДАНИЯ)
№	Файл	Таблицы
1	001_objects.sql	objects
2	002_products.sql	products
3	003_users.sql	users
4	004_requests.sql	requests
5	005_request_items.sql	request_items
6	006_request_item_history.sql	request_item_history
7	007_normatives.sql	normatives
8	008_available_balances.sql	available_balances
9	009_events.sql	events
11	011_product_admin.sql	products (gtin, mark_control, audit) + audit_log
14	014_object_admin.sql	objects (last_modified_by, last_modified_at)
15	015_object_erp.sql	objects (erp_plant_code, erp_warehouse_code, loading_point)
16	016_balances_available_plan.sql	available_balances (quantity → available, +plan)
17	017_balance_unit_kg.sql	available_balances.unit: шт, т, ШТ, КГ
18	018_product_gtin_parent_relax.sql	products: снять UNIQUE с gtin, снять FK parent/children
19	019_sync_metadata.sql	sync_metadata (дата и автор последней загрузки остатков)
20	020_object_uniqueness.sql	objects: снять UNIQUE с ERP-кодов, UNIQUE на loading_point
21	021_seed_users_objects.sql	начальные users + objects (остальные таблицы пустые)
10	010_functions.sql	Все функции
11	011_views.sql	Все представления
12	012_triggers.sql	Все триггеры
13	013_indexes.sql	Дополнительные индексы
11. НАЧАЛЬНЫЕ ДАННЫЕ
После `alembic upgrade head` (миграция `0013_seed_users_objects`) в БД есть только пользователи и объекты. Продукты, запросы, нормативы, остатки и прочие таблицы пустые (`sync_metadata` — служебная строка `id=1`).

Пароль всех пользователей: `password`.

sql
-- Пользователи
INSERT INTO users (id, username, email, full_name, role, department) VALUES
('11111111-1111-1111-1111-111111111111', 'commercial', 'commercial@company.ru', 'Иванов Иван', 'commercial', 'Коммерческий отдел'),
('22222222-2222-2222-2222-222222222222', 'pp', 'pp@company.ru', 'Петров Петр', 'pp', 'Планирование производства'),
('33333333-3333-3333-3333-333333333333', 'economist', 'economist@company.ru', 'Сидоров Сидор', 'economist', 'Экономический отдел'),
('44444444-4444-4444-4444-444444444444', 'logistics', 'logistics@company.ru', 'Кузнецов Кузьма', 'logistics', 'Логистика'),
('55555555-5555-5555-5555-555555555555', 'guest', 'guest@company.ru', 'Смирнов Гость', 'guest', NULL);

-- Заводы
INSERT INTO objects (code, name, city, region, type, erp_plant_code, erp_warehouse_code, loading_point) VALUES
(2420, 'ТПП Волгоград', 'Волгоград', 'Волгоградская область', 'plant', 2420, 'F001', '2420'),
(2421, 'ТПП Пермь', 'Пермь', 'Пермский край', 'plant', 2421, 'F001', '2421'),
(2422, 'ТПП Торжок', 'Торжок', 'Тверская область', 'plant', 2422, 'F001', '2422'),
(2423, 'Тюменский филиал', 'Богандинский', 'Тюменская область', 'plant', 2423, 'F001', '2423');

-- Склады
INSERT INTO objects (code, name, city, region, type, erp_plant_code, erp_warehouse_code, loading_point) VALUES
(2401002, 'ЛогЛаб Санкт-Петербург', 'Санкт-Петербург', 'Ленинградская область', 'warehouse', 2401, 'F002', '2R02'),
(2401004, 'ЛогЛаб Нижний Новгород', 'Дзержинск', 'Нижегородская область', 'warehouse', 2401, 'F004', '2R04'),
(2401005, 'ЛогЛаб Солнечногорск', 'Солнечногорск', 'Московская область', 'warehouse', 2401, 'F005', '2R05'),
(2401006, 'ЛогЛаб Краснодар', 'Краснодар', 'Краснодарский край', 'warehouse', 2401, 'F006', '2R06'),
(2401010, 'ЛогЛаб Екатеринбург', 'Екатеринбург', 'Свердловская область', 'warehouse', 2401, 'F010', '2R10'),
(2401011, 'ЛогЛаб Новосибирск', 'Новосибирск', 'Новосибирская область', 'warehouse', 2401, 'F011', '2R11'),
(2401015, 'ЛогЛаб Калининград', 'Калининград', 'Калининградская область', 'warehouse', 2401, 'F015', '2R15'),
(2401016, 'ЛогЛаб Ростов-на-Дону', 'Ростов-на-Дону', 'Ростовская область', 'warehouse', 2401, 'F016', '2R16'),
(2401017, 'ЛогЛаб Тюмень', 'Тюмень', 'Тюменская область', 'warehouse', 2401, 'F017', '2R17'),
(2401018, 'ЛогЛаб Иркутск', 'Иркутск', 'Иркутская область', 'warehouse', 2401, 'F018', '2R18'),
(2401025, 'ЛогЛаб Хабаровск', 'Хабаровск', 'Хабаровский край', 'warehouse', 2401, 'F025', '2R25');

12. КЛЮЧЕВЫЕ ЗАПРОСЫ
12.1. Расчет норматива для продукта
sql
SELECT calculate_normative(10001, 2001);
12.2. Дефицит по складу
sql
SELECT *
FROM deficit_view
WHERE warehouse_code = 2001;
12.3. Нормативы на дату
sql
SELECT *
FROM normatives_on_date(:target_date)
WHERE warehouse_code = 2001;
12.4. Все родственные артикулы
sql
SELECT * FROM get_related_products(10001);
12.5. Суммарный норматив по складу и артикулу на дату
sql
SELECT
    warehouse_code,
    product_code,
    SUM(quantity) AS total_normative
FROM normatives
WHERE warehouse_code = 2001
  AND product_code = 10001
  AND created_at <= :target_date
  AND expiry_date >= :target_date
  AND deleted_at IS NULL
GROUP BY warehouse_code, product_code;
13. ПРИМЕЧАНИЯ ПО MVP
Элемент	Статус в MVP
Таблица tariffs	❌ Удалена. Будет замена через API (не MVP)
Таблица available_balances	✅ Заполняется вручную через Excel (ERP: available + plan)
Таблица events	✅ Создана (задел под агента)
Таблица request_item_history	✅ История изменений
Функция expire_normatives()	✅ Нужна с первого дня
Функция get_related_products()	✅ Для расчета по цепочке артикулов
Коэффициент удаленности	✅ Зафиксирован = 1 (в будущем Яндекс API)


Версия: 2.1
Дата: 22.08.2026
Статус: Утверждена