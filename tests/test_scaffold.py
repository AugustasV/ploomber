from pathlib import Path
import ast

import pytest

from ploomber import tasks
from ploomber import scaffold


@pytest.mark.parametrize('name', ['task.py', 'task.ipynb'])
@pytest.mark.parametrize('extract_upstream', [False, True])
@pytest.mark.parametrize('extract_product', [False, True])
def test_renders_valid_script(name, extract_product, extract_upstream):
    loader = scaffold.ScaffoldLoader('ploomber_add')
    out = loader.render(name,
                        params=dict(extract_product=extract_product,
                                    extract_upstream=extract_upstream))

    # make sure it generates valid python code, except for the sql template
    if not name.endswith('.sql'):
        ast.parse(out)


@pytest.mark.parametrize('extract_upstream', [False, True])
@pytest.mark.parametrize('extract_product', [False, True])
def test_renders_valid_function(extract_product, extract_upstream):
    loader = scaffold.ScaffoldLoader('ploomber_add')
    out = loader.render('function.py',
                        params=dict(function_name='some_function',
                                    extract_product=extract_product,
                                    extract_upstream=extract_upstream))
    module = ast.parse(out)

    assert module.body[0].name == 'some_function'


def test_create_function(backup_test_pkg, tmp_directory):
    loader = scaffold.ScaffoldLoader('ploomber_add')

    loader.create('test_pkg.functions.new_function',
                  dict(extract_product=False, extract_upstream=True),
                  tasks.PythonCallable)

    code = Path(backup_test_pkg, 'functions.py').read_text()
    module = ast.parse(code)

    function_names = {
        element.name
        for element in module.body if hasattr(element, 'name')
    }

    assert 'new_function' in function_names


def test_add_task_from_scaffold(backup_test_pkg, tmp_directory):
    yaml = """
    meta:
        source_loader:
            module: test_pkg
        extract_product: True
    tasks:
        - source: notebook.ipynb
        - source: notebook.py
        - source: test_pkg.functions.my_new_function
    """

    Path('pipeline.yaml').write_text(yaml)

    # FIXME: this will fail because TaskSpec validates that the
    # dotted path actually exists. I think the cleanest solution
    # is to add a special class method for DAGSpec that allows the lazy
    # load to skip validating the last attribute...
    spec, path_to_spec = scaffold.load_dag()
    scaffold.add(spec, path_to_spec)

    code = Path(backup_test_pkg, 'functions.py').read_text()
    module = ast.parse(code)

    function_names = {
        element.name
        for element in module.body if hasattr(element, 'name')
    }

    assert 'my_new_function' in function_names
    assert Path(backup_test_pkg, 'notebook.ipynb').exists()
    assert Path(backup_test_pkg, 'notebook.py').exists()


def test_add_task_when_using_import_tasks_from(tmp_directory):
    spec = """
    meta:
        import_tasks_from: subdir/tasks.yaml
        extract_product: True

    tasks: []
    """

    tasks = """
    - source: notebook.py
    """

    Path('pipeline.yaml').write_text(spec)
    subdir = Path('subdir')
    subdir.mkdir()

    (subdir / 'tasks.yaml').write_text(tasks)

    spec, path_to_spec = scaffold.load_dag()
    scaffold.add(spec, path_to_spec)

    assert (subdir / 'notebook.py').exists()
