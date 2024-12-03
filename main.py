import os
import json
import zlib

def parse_object(object_hash, description=None):
    """
    Извлечь информацию из git-объекта по его хэшу.
    """
    object_path = os.path.join(config['repo_path'], '.git', 'objects', object_hash[:2], object_hash[2:])
    with open(object_path, 'rb') as file:
        raw_object_content = zlib.decompress(file.read())
        header, raw_object_body = raw_object_content.split(b'\x00', maxsplit=1)
        object_type, _ = header.decode().split(' ')

        object_dict = {}
        if object_type == 'commit':
            object_dict['label'] = f"commit {object_hash[:6]}"
            object_dict['children'] = parse_commit(raw_object_body)
        elif object_type == 'tree':
            object_dict['label'] = f"tree {object_hash[:6]}"
            object_dict['children'] = parse_tree(raw_object_body)
        elif object_type == 'blob':
            object_dict['label'] = f"blob {object_hash[:6]}"
            object_dict['children'] = []
        if description is not None:
            object_dict['label'] += f" ({description})"
        return object_dict

def parse_tree(raw_content):
    """
    Парсим git-объект дерева.
    """
    children = []
    rest = raw_content
    while rest:
        mode, rest = rest.split(b' ', maxsplit=1)
        name, rest = rest.split(b'\x00', maxsplit=1)
        sha1, rest = rest[:20].hex(), rest[20:]
        children.append(parse_object(sha1, description=name.decode()))
    return children

def parse_commit(raw_content):
    """
    Парсим git-объект коммита.
    """
    content = raw_content.decode()
    content_lines = content.split('\n')

    commit_data = {}
    commit_data['tree'] = content_lines[0].split()[1]
    content_lines = content_lines[1:]

    commit_data['parents'] = []
    while content_lines and content_lines[0].startswith('parent'):
        commit_data['parents'].append(content_lines[0].split()[1])
        content_lines = content_lines[1:]

    commit_data['message'] = '\n'.join(content_lines).strip()

    return [parse_object(commit_data['tree'])] + [parse_object(parent) for parent in commit_data['parents']]

def get_last_commit():
    """
    Получить хэш для последнего коммита в ветке.
    """
    head_path = os.path.join(config['repo_path'], '.git', 'refs', 'heads', config['branch'])
    with open(head_path, 'r') as file:
        return file.read().strip()

def generate_plantuml(filename):
    """
    Создать PlantUML файл для графа зависимостей.
    """
    def recursive_write(file, tree):
        label = tree['label']
        for child in tree['children']:
            file.write(f'"{label}" --> "{child["label"]}"\n')
            recursive_write(file, child)

    last_commit = get_last_commit()
    tree = parse_object(last_commit)

    with open(filename, 'w') as file:
        file.write('@startuml\n')
        file.write('digraph G {\n')
        recursive_write(file, tree)
        file.write('}\n')
        file.write('@enduml\n')

# Загрузка конфигурации
with open('config.json', 'r') as f:
    config = json.load(f)

# Генерация файла PlantUML
output_file = "graph.puml"
generate_plantuml(output_file)
print(f"Файл {output_file} создан. Загрузите его на сайт PlantUML для визуализации.")
