import pytest
from custom_components.health_link.composer.engine import ComposerError, SafeFormula

def test_formula_arithmetic():assert SafeFormula("clamp(50 + a * 10 - b * 5, 0, 100)").evaluate({"a":2,"b":1})==65
def test_formula_coalesce():assert SafeFormula("coalesce(a, b)").evaluate({"a":None,"b":4})==4
def test_formula_blocks_attribute_access():
    with pytest.raises(ComposerError):SafeFormula("a.__class__")
def test_formula_blocks_unknown_function():
    with pytest.raises(ComposerError):SafeFormula("__import__('os')").evaluate({})
