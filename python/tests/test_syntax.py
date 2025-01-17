"""Tests for the syntax of promplate."""

from pytest import raises

from promplate import Node, Template


def render_assert(text: str, context: dict | None = None, expected: str | None = None):
    """
    Render inputted text, then compare with the expected result.

    If an exception is expected, the `expected` argument can be left out (which defaults to None).
    """
    result = Template(text).render(context or {})

    # If no exception is raised, then an `expected` value must be given.
    assert expected is not None

    assert result == expected


def test_variables():
    """Variables use {{var}} syntax."""
    render_assert(
        "Hello, {{name}}!",
        {"name": "Ned"},
        "Hello, Ned!",
    )


def test_undefined_variables():
    """Using undefined names is an error."""
    with raises(NameError):
        render_assert("Hi, {{name}}!")


def test_reusability():
    """A single Template can be used more than once with different data."""
    globs = {"upper": str.upper, "punct": "!"}

    node = Node("This is {{upper(name)}}{{punct}}", globs)

    assert node.render({"name": "Ned"}) == "This is NED!"
    assert node.render({"name": "Ben"}) == "This is BEN!"


class DummyObject:
    """Dummy object for testing purposes."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_attribute():
    """Variables' attributes can be accessed with dots."""
    obj = DummyObject(a="Ay")
    render_assert(
        "{{obj.a}}",
        locals(),
        "Ay",
    )

    obj2 = DummyObject(obj=obj, b="Bee")
    render_assert(
        "{{obj2.obj.a}} {{obj2.b}}",
        locals(),
        "Ay Bee",
    )


def test_member_function():
    """Variables' member functions can be used, as long as they are nullary."""

    class WithMemberFns(DummyObject):
        """A class to try out member function access."""

        @property
        def ditto(self):
            """Return twice the .txt attribute."""
            return self.txt + self.txt  # type: ignore

    obj = WithMemberFns(txt="Once")

    render_assert(
        "{{obj.ditto}}",
        locals(),
        "OnceOnce",
    )


def test_item_access():
    """Variables' items can be used."""
    d = {"a": 17, "b": 23}
    render_assert(
        "{{d['a']}} < {{d['b']}}",
        locals(),
        "17 < 23",
    )


def test_loops():
    """Loops work like in Django."""
    nums = [1, 2, 3, 4]
    render_assert(
        "Look: {% for n in nums %}{{n}}, {% endfor %}done.",
        locals(),
        "Look: 1, 2, 3, 4, done.",
    )


def test_empty_loops():
    render_assert(
        "Empty: {% for n in nums %}{{n}}, {% endfor %}done.",
        {"nums": []},
        "Empty: done.",
    )


def test_multiline_loops():
    render_assert(
        "Look: \n{% for n in nums %}\n{{n}}, \n{% endfor %}done.",
        {"nums": [1, 2, 3]},
        "Look: \n\n1, \n\n2, \n\n3, \ndone.",
    )


def test_multiple_loops():
    render_assert(
        "{% for n in nums %}{{n}}{% endfor %} and "
        "{% for n in nums %}{{n}}{% endfor %}",
        {"nums": [1, 2, 3]},
        "123 and 123",
    )


def test_comments():
    render_assert(
        "Hello, {## Name goes here: ##}{{name}}!",
        {"name": "Ned"},
        "Hello, Ned!",
    )


def test_if():
    render_assert(
        "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
        {"ned": 1, "ben": 0},
        "Hi, NED!",
    )
    render_assert(
        "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
        {"ned": 0, "ben": 1},
        "Hi, BEN!",
    )
    render_assert(
        "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
        {"ned": 0, "ben": 0},
        "Hi, !",
    )
    render_assert(
        "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
        {"ned": 1, "ben": 0},
        "Hi, NED!",
    )
    render_assert(
        "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
        {"ned": 1, "ben": 1},
        "Hi, NEDBEN!",
    )


def test_complex_if():
    class ComplexObject(DummyObject):
        """A class to try out complex data access."""

        @property
        def getit(self):
            """Return it."""
            return self.it  # type: ignore

    obj = ComplexObject(it={"x": "Hello", "y": 0})
    render_assert(
        "@"
        "{% if obj.getit['x'] %}X{% endif %}"
        "{% if obj.getit['y'] %}Y{% endif %}"
        "!",
        {"obj": obj},
        "@X!",
    )


def test_loop_if():
    render_assert(
        "@{% for n in nums %}{% if n %}Z{% endif %}{{n}}{% endfor %}!",
        {"nums": [0, 1, 2]},
        "@0Z1Z2!",
    )
    render_assert(
        "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
        {"nums": [0, 1, 2]},
        "X@012!",
    )
    render_assert(
        "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
        {"nums": []},
        "X!",
    )


def test_nested_loops():
    render_assert(
        "@"
        "{% for n in nums %}"
        "{% for a in abc %}{{a}}{{n}}{% endfor %}"
        "{% endfor %}"
        "!",
        {"nums": [0, 1, 2], "abc": ["a", "b", "c"]},
        "@a0b0c0a1b1c1a2b2c2!",
    )


def test_whitespace_handling():
    render_assert(
        "@{% for n in nums %}\n"
        " {% for a in abc %}{{a}}{{n}}{% endfor %}\n"
        "{% endfor %}!\n",
        {"nums": [0, 1, 2], "abc": ["a", "b", "c"]},
        "@\n a0b0c0\n\n a1b1c1\n\n a2b2c2\n!\n",
    )
    render_assert(
        "@{% for n in nums -%}"
        "{% for a in abc -%}"
        "{## this disappears completely -##}"
        "{{a -}}"
        "{{n -}}"
        "{% endfor %}\n"
        "{% endfor %}!\n",
        {"nums": [0, 1, 2], "abc": ["a", "b", "c"]},
        "@a0b0c0\na1b1c1\na2b2c2\n!\n",
    )


def test_non_ascii():
    render_assert("{{where}} ollǝɥ", {"where": "ǝɹǝɥʇ"}, "ǝɹǝɥʇ ollǝɥ")


def test_exception_during_evaluation():
    with raises(AttributeError):
        render_assert("Hey {{foo.bar.baz}} there", {"foo": None}, "Hey ??? there")


def test_bad_names():
    with raises(SyntaxError):
        render_assert("Wat: {{ var%&!@ }}")
    with raises(SyntaxError):
        render_assert("Wat: {{ foo|filter%&!@ }}")
    with raises(SyntaxError):
        render_assert("Wat: {% for @ in x %}{% endfor %}")


def test_bogus_tag_syntax():
    with raises(IndexError):
        render_assert("Huh: {% bogus %}!!{% endbogus %}??")


def test_malformed_if():
    with raises(SyntaxError):
        render_assert("Buh? {% if %}hi!{% endif %}")
    with raises(NameError):
        render_assert("Buh? {% if this or that %}hi!{% endif %}")


def test_malformed_for():
    with raises(SyntaxError):
        render_assert("Weird: {% for %}loop{% endfor %}")
    with raises(SyntaxError):
        render_assert("Weird: {% for x from y %}loop{% endfor %}")
    with raises(NameError):
        render_assert("Weird: {% for x, y in z %}loop{% endfor %}")


def test_bad_nesting():
    with raises(SyntaxError):
        with raises(AssertionError):
            render_assert("{% if x %}X")
    with raises(AssertionError):
        render_assert("{% if x %}X{% endfor %}")
    with raises(IndexError):
        with raises(AssertionError):
            render_assert("{% if x %}{% endif %}{% endif %}")


def test_malformed_end():
    with raises(AssertionError):
        render_assert("{% if x %}X{% end if %}")
    with raises(AssertionError):
        render_assert("{% if x %}X{% endif now %}")


def test_pipe_iteration():
    from operator import itemgetter

    render_assert(
        "@" "{% for f in functions %}" "{{ f(nums) }}" "{% endfor %}" "!",
        {"functions": map(itemgetter, range(3)), "nums": [1, 2, 3]},
        "@123!",
    )
