# Библиотека taxonorm

Пакет/библиотека taxonorm предоставляет методы загрузки любого из
предусмотренных и описанных ниже форматов таксономии из csv или xlsx и
сохранения в любой из предусмотренный ниже форматов таксономии. Публичный
API возвращает и принимает объект `Taxonomy`. Табличное представление ветвей
`[id1, ..., idN, {leaf_key: value}]` используется на границах импорта,
парсинга и сериализации.

## Публичный API

### Рабочие примеры

В примерах ниже используется одна и та же небольшая таксономия из
`Samples/Variants/Shorts`: бытовая техника, электроника и серверные решения.
В этой папке лежит одна структура, сохранённая в разных стилях и форматах.

Небольшие запускаемые примеры находятся в `Examples/`:

- [sample_import.py](Examples/sample_import.py) — импорт CSV в стиле
  `IpStyle(header=True, keys=True, tabbed=True)` и базовый просмотр модели;
- [sample_parse_rows.py](Examples/sample_parse_rows.py) — парсинг таблицы,
  уже прочитанной в память;
- [sample_api_tour.py](Examples/sample_api_tour.py) — компактный сквозной
  пример: `from_branches()`, `guess_style()`, `validate_taxonomy()`,
  `serialize_taxonomy()`, равенство, перенумерация и обработка исключений;
- [sample_model_ops.py](Examples/sample_model_ops.py) — поиск, `leaf_path()`,
  изменение листьев, переименование и перенос поддерева;
- [sample_iter_paths.py](Examples/sample_iter_paths.py) — разница между
  `iter_branches()` и `iter_paths()` при массовом просмотре путей;
- [sample_chunks.py](Examples/sample_chunks.py) — восстановление и обратное
  дробление IP-обрезков с уникальными ID;
- [sample_export.py](Examples/sample_export.py) — экспорт той же таксономии в
  другой стиль;
- [sample_validate.py](Examples/sample_validate.py) — пользовательский отчёт
  валидации;
- [view_taxonomy.py](Examples/view_taxonomy.py) — утилита просмотра дерева в
  режимах `text`, `interactive` и `pyvis`.

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
    [1, {"en_US": "Household appliances", "uk_UA": "Побутова техніка"}],
    [1, 11, {"en_US": "Climate technology", "uk_UA": "Кліматична техніка"}],
    [1, 11, 21, {"en_US": "Household fans", "uk_UA": "Вентилятори побутові"}],
    [2, {"en_US": "Electronics", "uk_UA": "Електроніка"}],
    [2, 14, {"en_US": "Audio and multimedia", "uk_UA": "Аудіо та мультимедіа"}],
])
```

В варианте `Samples/Variants/Shorts/SHORT_2L_NU.json` та же таксономия
сохранена с неуникальными ID. Например, ID `1` может встречаться под разными
корнями, но пути `(101, 1)` и `(102, 1)` обозначают разные узлы.

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
    [1, {"en_US": "Household appliances", "uk_UA": "Побутова техніка"}],
    [1, 11, {"en_US": "Climate technology", "uk_UA": "Кліматична техніка"}],
])
```

Если присутствует дочерняя ветвь, но отдельная строка предка отсутствует,
модель создаст недостающего предка с пустыми листьями:

```python
taxonomy = Taxonomy.from_branches([
    [1, 12, 22, 31, {"en_US": "Freezers"}],
])

assert taxonomy.get_node((1,)).leaves == {}
```

`to_branches()` выполняет обратное преобразование и возвращает все узлы в
стабильном preorder-порядке:

```python
rows = taxonomy.to_branches()
# [[1, {}], [1, 12, {}], [1, 12, 22, {}], [1, 12, 22, 31, {"en_US": "Freezers"}]]
```

Списки ветвей и словари листьев копируются. Сами значения листьев копируются
поверхностно: вложенный изменяемый объект остаётся тем же объектом.

### Чтение файла

`import_taxonomy()` читает CSV, XLS или XLSX и всегда возвращает `Taxonomy`:

```python
from taxonorm import IpStyle, import_taxonomy

taxonomy = import_taxonomy(
    "Samples/Variants/Shorts/U_IP_H_K_T.csv",
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=["en_US", "uk_UA"],
)
```

Если `styler` не указан, библиотека попытается определить стиль автоматически:

```python
taxonomy = import_taxonomy(
    "Samples/Variants/Shorts/U_IP_H_K_T.xlsx",
    leaf_keys=["en_US", "uk_UA"],
)
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
    "Samples/Variants/Shorts/U_IP_H_K_T.csv",
    leaf_keys=["en_US", "uk_UA"],
    cvt_dict={"*": as_int_when_possible},
)
```

Полный запускаемый вариант этого сценария находится в
[Examples/sample_import.py](Examples/sample_import.py).

### Низкоуровневый парсинг и определение стиля

Если таблица уже прочитана другим кодом, `parse_taxonomy()` преобразует её в
`Taxonomy` без файлового ввода-вывода:

```python
from taxonorm import LpStyle, parse_taxonomy

rows = [
    [1, "Household appliances"],
    [11, "Household appliances", "Climate technology"],
    [21, "Household appliances", "Climate technology", "Household fans"],
]
taxonomy = parse_taxonomy(
    rows,
    styler=LpStyle(header=False, ids=True, sparse=False),
    leaf_keys=["en_US"],
)
```

Полный запускаемый вариант находится в
[Examples/sample_parse_rows.py](Examples/sample_parse_rows.py).

`guess_style(rows, leaf_keys=[...])` возвращает предполагаемый `IpStyle` или
`LpStyle`, но не выполняет парсинг. Результат сниффера следует считать
подсказкой, а не доказательством корректности входных данных.
См. [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Восстановление IP-обрезков

Некоторые IP-таблицы задают не полные пути, а обрезки путей. Крайний случай —
TP-таблица вида `parent_id, node_id, leaf`, но обрезок может содержать и больше
двух ID. Такие данные можно восстановить только если каждый ID узла имеет не
более одного родителя во всей таксономии:

```python
from taxonorm import IpStyle, import_taxonomy

taxonomy = import_taxonomy(
    "Samples/Variants/Chunks/mti_grp_swap.csv",
    styler=IpStyle(header=False, keys=False, tabbed=False),
    leaf_keys=["en_US"],
    restore_ip_chunks=True,
)
```

Если таблица уже разобрана в обменный вид `[id1, ..., idN, {key: value}]`,
можно использовать низкоуровневую функцию:

```python
from taxonorm import restore_unique_ip_chunks, split_to_unique_ip_chunks

branches = restore_unique_ip_chunks(chunks)
chunks = split_to_unique_ip_chunks(taxonomy, max_chunk_len=2)
```

См. [Examples/sample_chunks.py](Examples/sample_chunks.py).

При неоднозначном родителе, цикле или конфликтующих листьях для одного ID
возникает `TxParsingError`. По умолчанию `restore_ip_chunks=False`, поэтому
обычный IP-импорт остаётся без изменений. Для IP-обрезков без собственных
ключей последние ячейки строки сопоставляются с `leaf_keys` по обычному правилу
`IP_NK`: их число должно совпадать с числом ключей. Для TP-строк с одним
значением листа передавайте один ключ. При экспорте и сериализации IP-стилей
можно передать `max_chunk_len=2` или больше: тогда таксономия с уникальными ID
будет сохранена как IP-обрезки указанной максимальной длины.

### Валидация входных данных

`validate_input()` проверяет внешнюю таблицу без парсинга и никогда не
прерывает работу из-за найденных ошибок. Метод возвращает `ValidationReport`,
содержащий все обнаруженные проблемы (до заданного ограничения):

```python
from taxonorm import IpStyle, validate_input

style = IpStyle(header=True, keys=True, tabbed=True)
report = validate_input(
    rows,
    styler=style,
    leaf_keys=["en_US", "uk_UA"],
)

if not report.valid:
    print(report.format_text())
```

См. [Examples/sample_validate.py](Examples/sample_validate.py): там строка,
похожая на sample-файл, намеренно повреждена, чтобы показать формат отчёта.

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
IP_H_K_T; источник: damaged-short-sample.csv: обнаружено ошибок: 1; предупреждений: 0.
[id.missing] строка 2: В строке отсутствует ID-путь Ожидалось: хотя бы один непустой ID.
```

Число диагностик ограничивается аргументом `max_issues`:

```python
report = validate_input(
    rows,
    styler=style,
    leaf_keys=["en_US", "uk_UA"],
    max_issues=25,
    source="short-sample.csv",
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
        "Samples/Variants/Shorts/U_IP_H_K_T.csv",
        styler=style,
        leaf_keys=["en_US", "uk_UA"],
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
См. [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

Параметр `max_validation_issues` ограничивает размер отчёта автоматической
проверки. Отключение предусмотрено только для отладки внутренних парсеров:

```python
taxonomy = parse_taxonomy(
    rows,
    styler=style,
    leaf_keys=["en_US", "uk_UA"],
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
См. [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Обход дерева и выборки

`iter_branches()` возвращает объекты `TaxonomyBranch`. Каждый из них содержит
полный `path` и доступное только для чтения отображение `leaves`.

```python
for branch in taxonomy.iter_branches():
    print(branch.path, branch.leaves)
```

`leaf_path(path, key)` возвращает значения выбранного листа от корня до узла:

```python
names = taxonomy.leaf_path(
    (1, 12, 22, 31),
    "en_US",
)
# ("Household appliances", "Large household appliances", "Refrigeration equipment", "Freezers")
```

Если требуемого ключа нет у одного из узлов пути, значение задаётся параметром
`missed_leaf`. По умолчанию используется `"auto"`:

```python
names = taxonomy.leaf_path((1, 12), "de_DE")
# ("<de_DE:1>", "<de_DE:1.12>")
```

Для массового просмотра таксономии как пар ID-путь/leaf-путь удобен
`iter_paths(key=None)`. Он возвращает пары `(id_path, leaf_path)` и накапливает
leaf-путь во время обхода. Если ключ не указан, используется первый ключ из
`taxonomy.leaf_keys()`.

```python
for branch in taxonomy.iter_branches():
    id_path = branch.path
    leaf_path = taxonomy.leaf_path(branch.path, "en_US")
    print(id_path, leaf_path)

for id_path, leaf_path in taxonomy.iter_paths():
    print(id_path, leaf_path)
```

Первый вариант полезен, когда нужен весь `TaxonomyBranch`: листья текущего
узла, фильтрация по нескольким полям, редактирование или отладочный просмотр
внутренней модели. Второй вариант лучше для печати, экспорта и массового
просмотра путей: leaf-путь накапливается за один обход, без повторного прохода
от корня для каждого узла.

Запускаемый пример сравнения находится в
[Examples/sample_iter_paths.py](Examples/sample_iter_paths.py).

Поддерживаются три стабильных порядка обхода:

```python
taxonomy.iter_branches("preorder")   # узел, затем его потомки; по умолчанию
taxonomy.iter_branches("postorder")  # потомки, затем узел
taxonomy.iter_branches("breadth")    # по уровням, начиная с корней
taxonomy.iter_paths("en_US", order="breadth")
```

Неизвестное имя порядка вызывает `ValueError`.

Для выборки используется `find_branches()`:

```python
groups = taxonomy.find_branches(
    lambda branch: branch.leaves.get("en_US", "").endswith("systems"),
    order="breadth",
)

for branch in groups:
    print(branch.path)
```

Метод возвращает ленивый итератор и не создаёт отдельную копию таксономии.

### Просмотр и поиск узлов

```python
len(taxonomy)                         # число узлов
(2, 14, 24, 34) in taxonomy           # проверка полного пути

node = taxonomy.get_node((2, 14, 24, 34))
print(node.leaves["en_US"])           # Microphones
print(node.children)
```

`get_node()` принимает полный ID-путь. Если путь отсутствует, возникает
`KeyError`. Передавать одиночную строку вместо пути нельзя: используйте
`(1,)`, а не `1`.

`leaf_keys()` возвращает ключи листьев в порядке первого появления:

```python
assert taxonomy.leaf_keys() == ("en_US", "uk_UA")
```

`TaxonomyNode.leaves`, `TaxonomyNode.children` и `Taxonomy.roots` — доступные
только для чтения отображения. Это не позволяет обойти проверку ID и ключей:

```python
node.leaves["en_US"] = "New name"  # TypeError
```

Изменять модель следует методами `Taxonomy`, описанными ниже.

У `TaxonomyNode` намеренно нет отдельного поля `id`: ID хранится ключом на
входящем ребре и не дублируется в памяти. Получить ID и расположение узла можно
из полного `TaxonomyBranch.path` либо из пути, переданного в `get_node()`.

### Изменение листьев

`update_leaves()` по умолчанию объединяет переданные листья с существующими:

```python
taxonomy.update_leaves(
    (3, 15, 25),
    {"note": "Duplicated label, distinct path"},
)
```

Одинаковые ключи получают новые значения, остальные сохраняются. Для полной
замены словаря используйте `replace=True`:

```python
taxonomy.update_leaves(
    (3, 15, 25),
    {"en_US": "Servers", "uk_UA": "Сервери"},
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
    (3, 15, 25, 35),
    350,
)
```

Все пути потомков автоматически изменяются. Если у того же родителя уже есть
узел с новым ID, возникает `TxValidationError`; существующий узел не
перезаписывается.

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

Пример нескольких операций модели на sample-таксономии см.
[Examples/sample_model_ops.py](Examples/sample_model_ops.py).
Перенумерация также показана в
[Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Добавление узлов

`add_branch()` создаёт узел и отсутствующих предков:

```python
taxonomy.add_branch(
    (2, 14, 24, 39),
    {"en_US": "Studio monitors", "uk_UA": "Студійні монітори"},
)
```

Если точный путь уже объявлен, возникает `TxValidationError`. Для полной
замены словаря листьев существующего узла требуется явный `replace=True`:

```python
taxonomy.add_branch(
    (2, 14, 24, 39),
    {"en_US": "Studio monitors", "uk_UA": "Студійні монітори"},
    replace=True,
)
```

Замена листьев не удаляет дочерние узлы.

### Удаление узлов

По умолчанию `remove_branch()` удаляет только узел без потомков:

```python
taxonomy.remove_branch((2, 14, 24, 34))
```

Попытка удалить узел с дочерними узлами вызывает `TxValidationError`. Это
защищает от случайной потери целого раздела. Для намеренного удаления всего
поддерева необходимо явно указать `recursive=True`:

```python
taxonomy.remove_branch(
    (2, 14, 24),
    recursive=True,
)
```

Метод возвращает отсоединённый `TaxonomyNode`. Число узлов `len(taxonomy)`
уменьшается на размер удалённого поддерева. Повторное удаление того же пути
вызывает `KeyError`.

### Перемещение поддерева

`move_subtree()` переносит узел вместе со всеми потомками:

```python
taxonomy.move_subtree(
    (3, 15, 26, 37),
    (3, 15, 25),
)
```

Одновременно можно изменить ID корня переносимого поддерева:

```python
taxonomy.move_subtree(
    (3, 15, 26, 37),
    (3, 15, 25),
    new_id=370,
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

### Визуализация дерева

Модуль `taxonorm.viewer` содержит три способа просмотра дерева. Эти функции
работают напрямую с `Taxonomy`, без преобразования в `networkx` или другой
промежуточный граф:

```python
from taxonorm import (
    view_live_html_tree,
    view_live_text_tree,
    view_text_tree,
)

view_text_tree(taxonomy)                   # статическое дерево в терминале
view_text_tree(taxonomy, leaf_key="en_US") # показывать названия вместо ID

view_live_text_tree(taxonomy, leaf_key="en_US")  # интерактивный TUI

html_path = view_live_html_tree(
    taxonomy,
    leaf_key="en_US",
    filename="taxonomy.html",
)
```

По умолчанию подписи узлов — это ID. Если передать `leaf_key`, подписью станет
значение выбранного листа на соответствующем узле. При этом структура остаётся
родной структурой `Taxonomy`, поэтому одноимённые узлы не схлопываются.

Дополнительно доступны `render_text_tree()` для получения объекта Rich без
печати и `save_text_tree()` для сохранения текстового дерева в файл.

### Сериализация и запись

`serialize_taxonomy()` преобразует модель в таблицу выбранного стиля, не
создавая файл:

```python
from taxonorm import IpStyle, serialize_taxonomy

rows = serialize_taxonomy(
    taxonomy,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    headers=["Taxonomy", "1.0"],
    key_order=["en_US", "uk_UA"],
)
```

`export_taxonomy()` сериализует и записывает CSV, XLS или XLSX; формат файла
определяется расширением:

```python
from taxonorm import LpStyle, export_taxonomy

export_taxonomy(
    taxonomy,
    "short-taxonomy.xlsx",
    styler=LpStyle(header=True, ids=True, sparse=False),
    leaf_key="en_US",
    headers=["id", "category"],
)
```

Запускаемый пример экспорта без записи в рабочую папку проекта находится в
[Examples/sample_export.py](Examples/sample_export.py).
`serialize_taxonomy()` без записи файла показан в
[Examples/sample_api_tour.py](Examples/sample_api_tour.py).

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
См. [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

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
См. [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

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
| `leaf_path(path, key, missed_leaf="auto")` | Получить значения листа от корня до узла | `KeyError`, `TxValidationError` |
| `iter_paths(key=None, order="preorder", missed_leaf="auto")` | Обойти пары `(id_path, leaf_path)` | `ValueError`, `TxValidationError` |
| `iter_leaf_paths(key, order="preorder", missed_leaf="auto")` | Совместимый алиас `iter_paths(key, ...)` | `ValueError`, `TxValidationError` |

Связанные функции верхнеуровневого API: `renumber_taxonomy_ids(taxonomy)`,
`restore_unique_ip_chunks(chunks)`.

