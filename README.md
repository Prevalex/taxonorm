# Библиотека taxonorm

Пакет/библиотека taxonorm предоставляет методы загрузки любого из
предусмотренных и описанных ниже форматов таксономии из csv или xlsx и
сохранения в любой из предусмотренный ниже форматов таксономии. Публичный
API возвращает и принимает объект `Taxonomy`. Табличное представление ветвей
`[id1, ..., idN, {leaf_key: value}]` используется на границах импорта,
парсинга и сериализации.

## Публичный API

### Основная модель

`Taxonomy` — каноническое представление таксономии в памяти. Объект может
содержать один корень или несколько независимых корней (лес). Узел однозначно
определяется полным путём ID от корня; поэтому один и тот же ID разрешено
использовать в разных ветвях.

Пустую изменяемую модель можно создать обычным конструктором `Taxonomy()`.
`from_branches()` удобнее, когда исходные ветви уже находятся в памяти.

```python
from taxonorm import Taxonomy

taxonomy = Taxonomy.from_branches([
    ["catalog", {"name": "Каталог"}],
    ["catalog", "phones", {"name": "Телефоны"}],
    ["catalog", "phones", "accessories", {"name": "Аксессуары"}],
    ["catalog", "tablets", {"name": "Планшеты"}],
    ["catalog", "tablets", "accessories", {"name": "Аксессуары"}],
])
```

В примере ID `"accessories"` встречается дважды, но пути
`("catalog", "phones", "accessories")` и
`("catalog", "tablets", "accessories")` обозначают разные узлы.

Основные инварианты:

- ID узла — любой непустой хэшируемый объект;
- ключ листа — любой непустой хэшируемый объект;
- значение листа — любой объект, включая `None` и нехэшируемые объекты;
- точный ID-путь не может встречаться дважды;
- порядок корней и соседних узлов стабилен и соответствует порядку добавления.

Пустыми считаются `None`, пустые и состоящие из пробелов строки, пустые
кортежи и другие пустые контейнеры. Числа `0` и `False` допустимы, однако
следует помнить, что стандартные словари Python считают `0` и `False` равными
ключами.

### Создание из таблицы ветвей

`Taxonomy.from_branches()` принимает итерируемый объект, где каждая ветвь
содержит ID-путь и завершается отображением листьев:

```python
taxonomy = Taxonomy.from_branches([
    [1, {"en": "Electronics", "uk": "Електроніка"}],
    [1, 2, {"en": "Audio", "uk": "Аудіо"}],
])
```

Если присутствует дочерняя ветвь, но отдельная строка предка отсутствует,
модель создаст недостающего предка с пустыми листьями:

```python
taxonomy = Taxonomy.from_branches([
    ["root", "child", {"name": "Child"}],
])

assert taxonomy.get_node(("root",)).leaves == {}
```

`to_branches()` выполняет обратное преобразование и возвращает все узлы в
стабильном preorder-порядке:

```python
rows = taxonomy.to_branches()
# [["root", {}], ["root", "child", {"name": "Child"}]]
```

Списки ветвей и словари листьев копируются. Сами значения листьев копируются
поверхностно: вложенный изменяемый объект остаётся тем же объектом.

### Чтение файла

`import_taxonomy()` читает CSV, XLS или XLSX и всегда возвращает `Taxonomy`:

```python
from taxonorm import LpStyle, import_taxonomy

taxonomy = import_taxonomy(
    "categories.csv",
    styler=LpStyle(header=False, ids=True, sparse=False),
    leaf_keys=["name"],
)
```

Если `styler` не указан, библиотека попытается определить стиль автоматически:

```python
taxonomy = import_taxonomy("categories.xlsx", leaf_keys=["name"])
```

Автоопределение является эвристикой. Для неоднозначных или внешних данных
рекомендуется явно передавать `IpStyle` либо `LpStyle`.

```python
from taxonorm import IpStyle

style = IpStyle(
    header=True,  # первая строка является заголовком
    keys=True,    # ключи листьев находятся в файле
    tabbed=True,  # ID и листья выровнены по столбцам
)
```

Для `LpStyle` используются свойства `header`, `ids` и `sparse`.
Для `IpStyle` — `header`, `keys` и `tabbed`. Подробное описание всех сочетаний
стилей находится ниже в этом документе.

Аргумент `cvt_dict` позволяет преобразовать прочитанные значения. Например,
чтобы восстанавливать числовые ID из строк CSV:

```python
def as_int_when_possible(value):
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value

taxonomy = import_taxonomy(
    "categories.csv",
    leaf_keys=["name"],
    cvt_dict={"*": as_int_when_possible},
)
```

### Низкоуровневый парсинг и определение стиля

Если таблица уже прочитана другим кодом, `parse_taxonomy()` преобразует её в
`Taxonomy` без файлового ввода-вывода:

```python
from taxonorm import LpStyle, parse_taxonomy

rows = [
    [1, "Catalog"],
    [2, "Catalog", "Phones"],
]
taxonomy = parse_taxonomy(
    rows,
    styler=LpStyle(header=False, ids=True, sparse=False),
    leaf_keys=["name"],
)
```

`guess_style(rows, leaf_keys=[...])` возвращает предполагаемый `IpStyle` или
`LpStyle`, но не выполняет парсинг. Результат сниффера следует считать
подсказкой, а не доказательством корректности входных данных.

### Восстановление IP-обрезков

Некоторые IP-таблицы задают не полные пути, а обрезки путей. Крайний случай —
TP-таблица вида `parent_id, node_id, leaf`, но обрезок может содержать и больше
двух ID. Такие данные можно восстановить только если каждый ID узла имеет не
более одного родителя во всей таксономии:

```python
from taxonorm import IpStyle, import_taxonomy

taxonomy = import_taxonomy(
    "vendor-groups.csv",
    styler=IpStyle(header=False, keys=False, tabbed=False),
    leaf_keys=["name"],
    restore_ip_chunks=True,
)
```

Если таблица уже разобрана в обменный вид `[id1, ..., idN, {key: value}]`,
можно использовать низкоуровневую функцию:

```python
from taxonorm import restore_unique_ip_chunks

branches = restore_unique_ip_chunks(chunks)
```

При неоднозначном родителе, цикле или конфликтующих листьях для одного ID
возникает `TxParsingError`. По умолчанию `restore_ip_chunks=False`, поэтому
обычный IP-импорт остаётся без изменений. Для IP-обрезков без собственных
ключей последние ячейки строки сопоставляются с `leaf_keys` по обычному правилу
`IP_NK`: их число должно совпадать с числом ключей. Для TP-строк с одним
значением листа передавайте один ключ.

### Валидация входных данных

`validate_input()` проверяет внешнюю таблицу без парсинга и никогда не
прерывает работу из-за найденных ошибок. Метод возвращает `ValidationReport`,
содержащий все обнаруженные проблемы (до заданного ограничения):

```python
from taxonorm import LpStyle, validate_input

style = LpStyle(header=False, ids=True, sparse=False)
report = validate_input(
    rows,
    styler=style,
    leaf_keys=["name"],
)

if not report.valid:
    print(report.format_text())
```

Отчёт различает ошибки и предупреждения:

```python
report.valid       # False, если есть хотя бы одна ошибка
report.errors      # tuple[ValidationIssue, ...]
report.warnings    # tuple[ValidationIssue, ...]
report.issues      # все диагностики в порядке обнаружения
report.to_dict()   # структура для JSON, API или журнала
```

Каждый `ValidationIssue` содержит:

| Поле | Значение |
| --- | --- |
| `code` | Машиночитаемый код, например `id.invalid` или `lp.sparse.unresolved` |
| `message` | Объяснение проблемы для пользователя |
| `row` | Номер строки, начиная с 1 |
| `column` | Номер столбца, начиная с 1, если он применим |
| `value` | Проблемное входное значение |
| `expected` | Описание ожидаемого формата |
| `severity` | `"error"` либо `"warning"` |

При чтении файла номера относятся к таблице после удаления полностью пустых
строк файловым reader. Поле `ValidationReport.source` содержит путь исходного
файла, поэтому отчёты удобно собирать при пакетной проверке каталога.

`format_text()` создаёт предназначенное для человека сообщение:

```text
LP_NH_I_S; источник: categories.csv: обнаружено ошибок: 2; предупреждений: 0.
[id.invalid] строка 18, столбец 1: ID должен быть непустым хэшируемым объектом.
[lp.sparse.unresolved] строка 27, столбец 3: Значение sparse-пути невозможно восстановить из предыдущих строк.
```

Число диагностик ограничивается аргументом `max_issues`:

```python
report = validate_input(
    rows,
    styler=style,
    leaf_keys=["name"],
    max_issues=25,
    source="categories.csv",
)
```

Если проблем больше, `report.truncated` будет равен `True`.

Валидаторы проверяют несколько уровней правил:

- общую структуру таблицы, строки, настройки стиля и `leaf_keys`;
- наличие и корректность ID;
- размещение ключей и пар key/value в IP;
- число значений листьев в IP без собственных ключей;
- плотные и sparse leaf-пути LP;
- возможность восстановить пропущенные значения sparse-пути;
- уникальность ID, ID-путей и конечных значений LP с собственными ID;
- соответствие заголовка заявленному keyed IP-стилю.

Предупреждение не запрещает парсинг. Например, LP использует только первый
ключ из `leaf_keys`; остальные ключи будут отражены предупреждением.

### Автоматическая валидация при парсинге

`parse_taxonomy()` и `import_taxonomy()` выполняют валидацию автоматически.
Если отчёт содержит ошибки, поднимается одно `TxInputValidationError`:

```python
from taxonorm import TxInputValidationError, import_taxonomy

try:
    taxonomy = import_taxonomy(
        "categories.csv",
        styler=style,
        leaf_keys=["name"],
    )
except TxInputValidationError as error:
    print(error)                 # удобный текст для пользователя
    send_to_api(error.report.to_dict())
```

Исключение содержит исходный `ValidationReport` в атрибуте `report`. Его
`context["validation"]` также попадает в стандартный `TaxonormError.to_dict()`.
Если внутренний парсер обнаружил редкую ошибку, пропущенную предварительной
проверкой, пользователь всё равно получает `TxInputValidationError`, а
исходное исключение сохраняется в `__cause__` для журнала разработчика.

Параметр `max_validation_issues` ограничивает размер отчёта автоматической
проверки. Отключение предусмотрено только для отладки внутренних парсеров:

```python
taxonomy = parse_taxonomy(
    rows,
    styler=style,
    leaf_keys=["name"],
    validate=False,
)
```

При `validate=False` могут возникать низкоуровневые `TxParsingError`,
`KeyError` и другие исключения. При обработке пользовательских файлов этот
режим применять не рекомендуется.

### Проверка готовой модели

`validate_taxonomy()` выполняет аудит уже созданного объекта:

```python
from taxonorm import validate_taxonomy

report = validate_taxonomy(taxonomy)
report.raise_for_errors()
```

Обычные операции `Taxonomy` уже поддерживают инварианты модели, поэтому эта
проверка полезна главным образом на границах интеграции и в диагностических
инструментах. Пустая `Taxonomy` допустима, но создаёт предупреждение
`taxonomy.empty`.

### Просмотр и поиск узлов

```python
len(taxonomy)                         # число узлов
("catalog", "phones") in taxonomy  # проверка полного пути

node = taxonomy.get_node(("catalog", "phones"))
print(node.leaves["name"])
print(node.children)
```

`get_node()` принимает полный ID-путь. Если путь отсутствует, возникает
`KeyError`. Передавать одиночную строку вместо пути нельзя: используйте
`("root",)`, а не `"root"`.

`TaxonomyNode.leaves`, `TaxonomyNode.children` и `Taxonomy.roots` — доступные
только для чтения отображения. Это не позволяет обойти проверку ID и ключей:

```python
node.leaves["name"] = "Новое имя"  # TypeError
```

Изменять модель следует методами `Taxonomy`, описанными ниже.

У `TaxonomyNode` намеренно нет отдельного поля `id`: ID хранится ключом на
входящем ребре и не дублируется в памяти. Получить ID и расположение узла можно
из полного `TaxonomyBranch.path` либо из пути, переданного в `get_node()`.

`leaf_keys()` возвращает ключи листьев в порядке первого появления:

```python
assert taxonomy.leaf_keys() == ("name",)
```

`leaf_path()` возвращает значения выбранного листа от корня до узла:

```python
names = taxonomy.leaf_path(
    ("catalog", "phones", "accessories"),
    "name",
)
# ("Каталог", "Телефоны", "Аксессуары")
```

Если требуемого ключа нет хотя бы у одного узла пути, возникает `KeyError`.

### Обход дерева и выборки

`iter_branches()` возвращает объекты `TaxonomyBranch`. Каждый из них содержит
полный `path` и доступное только для чтения отображение `leaves`.

```python
for branch in taxonomy.iter_branches():
    print(branch.path, branch.leaves)
```

Поддерживаются три стабильных порядка обхода:

```python
taxonomy.iter_branches("preorder")   # узел, затем его потомки; по умолчанию
taxonomy.iter_branches("postorder")  # потомки, затем узел
taxonomy.iter_branches("breadth")    # по уровням, начиная с корней
```

Неизвестное имя порядка вызывает `ValueError`.

Для выборки используется `find_branches()`:

```python
groups = taxonomy.find_branches(
    lambda branch: branch.leaves.get("kind") == "group",
    order="breadth",
)

for branch in groups:
    print(branch.path)
```

Метод возвращает ленивый итератор и не создаёт отдельную копию таксономии.

### Добавление узлов

`add_branch()` создаёт узел и отсутствующих предков:

```python
taxonomy.add_branch(
    ("catalog", "wearables"),
    {"name": "Носимая электроника"},
)
```

Если точный путь уже объявлен, возникает `TxValidationError`. Для полной
замены словаря листьев существующего узла требуется явный `replace=True`:

```python
taxonomy.add_branch(
    ("catalog", "wearables"),
    {"name": "Wearables"},
    replace=True,
)
```

Замена листьев не удаляет дочерние узлы.

### Изменение листьев

`update_leaves()` по умолчанию объединяет переданные листья с существующими:

```python
taxonomy.update_leaves(
    ("catalog", "phones"),
    {"description": "Mobile and landline phones"},
)
```

Одинаковые ключи получают новые значения, остальные сохраняются. Для полной
замены словаря используйте `replace=True`:

```python
taxonomy.update_leaves(
    ("catalog", "phones"),
    {"name": "Phones"},
    replace=True,
)
```

Если путь отсутствует, `update_leaves()` вызывает `KeyError`. Некорректный
ключ листа вызывает `TxValidationError`; модель при этом не изменяется.

### Переименование ID

`rename_node()` изменяет последний ID пути, сохраняя поддерево и позицию среди
соседей:

```python
taxonomy.rename_node(
    ("catalog", "phones"),
    "telephones",
)
```

Все пути потомков автоматически изменяются. Если у того же родителя уже есть
узел с новым ID, возникает `TxValidationError`; существующий узел не
перезаписывается.

### Перемещение поддерева

`move_subtree()` переносит узел вместе со всеми потомками:

```python
taxonomy.move_subtree(
    ("catalog", "telephones", "accessories"),
    ("catalog", "wearables"),
)
```

Одновременно можно изменить ID корня переносимого поддерева:

```python
taxonomy.move_subtree(
    ("catalog", "telephones", "accessories"),
    ("catalog", "wearables"),
    new_id="phone-accessories",
)
```

Чтобы сделать узел новым корнем, передайте `new_parent=None`.

Операция проверяет ограничения до изменения дерева:

- нельзя переместить узел внутрь собственного поддерева;
- у нового родителя не должно быть дочернего узла с целевым ID;
- новый родитель должен существовать;
- новый ID должен быть непустым и хэшируемым.

При нарушении первых двух правил возникает `TxValidationError`, при отсутствии
исходного пути или нового родителя — `KeyError`. Если источник и назначение
совпадают, операция ничего не меняет и возвращает существующий узел.

### Перенумерация ID

`renumber_taxonomy_ids()` создаёт новую `Taxonomy` с теми же листьями,
структурой и порядком соседних узлов, но с заново назначенными числовыми ID:

```python
from taxonorm import renumber_taxonomy_ids

renumbered = renumber_taxonomy_ids(
    taxonomy,
    slack=0.10,
    round_to=10,
    start_from=1,
)
```

Функция полезна, когда исходные ID отсутствуют, неудобны или не являются
глобально уникальными. Новые ID назначаются по уровням дерева с округлёнными
диапазонами, как при импорте LP-таксономии без собственных ID. Исходная модель
не изменяется.

### Удаление узлов

По умолчанию `remove_branch()` удаляет только узел без потомков:

```python
taxonomy.remove_branch(("catalog", "obsolete"))
```

Попытка удалить узел с дочерними узлами вызывает `TxValidationError`. Это
защищает от случайной потери целого раздела. Для намеренного удаления всего
поддерева необходимо явно указать `recursive=True`:

```python
taxonomy.remove_branch(
    ("catalog", "old-section"),
    recursive=True,
)
```

Метод возвращает отсоединённый `TaxonomyNode`. Число узлов `len(taxonomy)`
уменьшается на размер удалённого поддерева. Повторное удаление того же пути
вызывает `KeyError`.

### Сериализация и запись

`serialize_taxonomy()` преобразует модель в таблицу выбранного стиля, не
создавая файл:

```python
from taxonorm import IpStyle, serialize_taxonomy

rows = serialize_taxonomy(
    taxonomy,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    headers=["Taxonomy", "1.0"],
    key_order=["name", "description"],
)
```

`export_taxonomy()` сериализует и записывает CSV, XLS или XLSX; формат файла
определяется расширением:

```python
from taxonorm import LpStyle, export_taxonomy

export_taxonomy(
    taxonomy,
    "categories.xlsx",
    styler=LpStyle(header=True, ids=True, sparse=False),
    leaf_key="name",
    headers=["ID", "Category path"],
)
```

Для IP-стиля `key_order` задаёт порядок столбцов листьев. Для LP-стиля
`leaf_key` выбирает единственный лист, образующий leaf-путь. Аргумент
`missed_leaf` управляет значением отсутствующего листа: `None`, функция либо
строка `"auto"`.

Значения листьев в памяти могут быть любыми Python-объектами, но конкретный
файловый формат способен сохранить только поддерживаемые табличным драйвером
типы. Для сложных объектов пользователь должен заранее определить собственное
преобразование.

### Равенство и порядок

Два объекта `Taxonomy` равны, если совпадают их ветви, листья и стабильный
порядок обхода:

```python
assert Taxonomy.from_branches(taxonomy.to_branches()) == taxonomy
```

Порядок является частью наблюдаемого результата сериализации. Если входные
данные семантически одинаковы, но добавлены в разном порядке, объекты могут
сравниваться как неравные.

### Исключения

Основные исключения определены в `taxonorm.errors`:

```python
from taxonorm.errors import (
    TaxonormError,
    TxConversionError,
    TxExportError,
    TxImportError,
    TxInputValidationError,
    TxParsingError,
    TxValidationError,
)
```

Все специализированные исключения наследуют `TaxonormError`, содержат
стабильный `code`, текст `message`, необязательный `context` и метод
`to_dict()`. Для обработки всех ошибок библиотеки можно перехватывать базовый
`TaxonormError`; для ошибок пользовательских ID, ключей и операций дерева —
`TxValidationError`, а для некорректной внешней таблицы — более точный
`TxInputValidationError`.

### Краткий справочник методов `Taxonomy`

| Метод | Назначение | Основные ошибки |
| --- | --- | --- |
| `Taxonomy()` | Создать пустую модель | — |
| `from_branches(rows)` | Создать модель из полных ID-ветвей | `TxValidationError` |
| `to_branches()` | Получить поверхностно скопированную таблицу ветвей | — |
| `get_node(path)` | Получить узел по полному пути | `KeyError` |
| `add_branch(path, leaves, replace=False)` | Добавить узел и недостающих предков | `TxValidationError` |
| `update_leaves(path, leaves, replace=False)` | Объединить или заменить листья | `KeyError`, `TxValidationError` |
| `rename_node(path, new_id)` | Переименовать ID с сохранением поддерева | `KeyError`, `TxValidationError` |
| `move_subtree(path, new_parent, new_id=None)` | Переместить и при необходимости переименовать поддерево | `KeyError`, `TxValidationError` |
| `remove_branch(path, recursive=False)` | Удалить узел либо всё поддерево | `KeyError`, `TxValidationError` |
| `iter_branches(order="preorder")` | Обойти дерево в выбранном порядке | `ValueError` |
| `find_branches(predicate, order="preorder")` | Лениво выбрать ветви по предикату | `ValueError` |
| `leaf_keys()` | Получить ключи в порядке первого появления | — |
| `leaf_path(path, key)` | Получить значения листа от корня до узла | `KeyError` |

Связанные функции верхнеуровневого API: `renumber_taxonomy_ids(taxonomy)`,
`restore_unique_ip_chunks(chunks)`.

