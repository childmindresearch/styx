"""Test the codegen scope module."""

import pytest

from styx.pycodegen.scope import Scope


def test_scope_add_or_die() -> None:
    """Test adding a symbol to a scope."""
    scope = Scope()
    scope.add_or_die("foo")
    assert "foo" in scope
    assert "bar" not in scope

    with pytest.raises(ValueError):
        scope.add_or_die("foo")


def test_scope_add_or_dodge() -> None:
    """Test adding a symbol to a scope with dodging."""
    scope = Scope()
    scope.add_or_die("foo")
    assert "foo" in scope
    assert "foo_" not in scope
    assert "foo_2" not in scope
    assert "foo_3" not in scope
    assert "bar" not in scope
    assert scope.add_or_dodge("foo") == "foo_"
    assert scope.add_or_dodge("foo") == "foo_2"
    assert scope.add_or_dodge("foo") == "foo_3"
    assert scope.add_or_dodge("bar") == "bar"
    assert scope.add_or_dodge("bar") == "bar_"
    assert scope.add_or_dodge("bar") == "bar_2"
    assert scope.add_or_dodge("bar") == "bar_3"
    assert scope.add_or_dodge("bar") == "bar_4"

    with pytest.raises(ValueError):
        scope.add_or_die("foo")


def test_scope_python() -> None:
    """Test the Python scope."""
    scope = Scope.python()
    assert "def" in scope
    assert "int" in scope
    assert "typing" in scope

    assert "foo" not in scope
    scope.add_or_die("foo")
    assert "foo" in scope


def test_scope_parent() -> None:
    """Test the parent scope."""
    parent = Scope()
    parent.add_or_die("foo")
    assert "foo" in parent
    assert "bar" not in parent

    child = Scope(parent)
    assert "foo" in child
    assert "bar" not in child
    child.add_or_die("bar")
    assert "foo" in child
    assert "bar" in child
    assert "foo" in parent
    assert "bar" not in parent

    with pytest.raises(ValueError):
        child.add_or_die("foo")
    with pytest.raises(ValueError):
        parent.add_or_die("bar")
