# -*- coding: utf-8 -*-
"""
MathLens — решение школьных примеров и пошаговый разбор.

Здесь нет нейросетей: считает SymPy, поэтому дроби, степени, корни и логарифмы
получаются точными. Нейросеть отвечает только за распознавание символов.
"""
from __future__ import annotations

import re
from typing import List, Tuple

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

Step = Tuple[str, str]


# --------------------------------------------------------------------------- #
# Подготовка строки
# --------------------------------------------------------------------------- #
def _fix_roots(s: str) -> str:
    """Корень: sqrt(9) вместо sqrt9."""
    s = re.sub(r"\u221a\s*\(([^()]*)\)", r"sqrt(\1)", s)
    s = re.sub(r"\u221a\s*(\d+(?:[.,]\d+)?)", r"sqrt(\1)", s)
    s = re.sub(r"\u221a\s*([a-zA-Z])", r"sqrt(\1)", s)
    return s


def normalize(raw: str) -> str:
    """Приводим распознанный текст к машинной записи."""
    s = raw.strip()
    s = _fix_roots(s)
    for old, new in (
        ("\u2212", "-"), ("\u2013", "-"), ("\u2014", "-"),
        ("\u00d7", "*"), ("\u00b7", "*"), ("\u00f7", "/"),
        ("\u03c0", "pi"), ("^", "**"),
    ):
        s = s.replace(old, new)
    s = s.replace(",", ".")
    s = s.replace("ln(", "log(")
    s = re.sub(r"\s+", "", s)
    return s


def _parse(text: str) -> sp.Expr:
    return parse_expr(text, transformations=TRANSFORMS, evaluate=True)


def _plain(expr) -> str:
    """Читаемая запись выражения для экрана."""
    return sp.sstr(expr)


def _exact(expr) -> str:
    """Точное значение: дробь как 3/4, целое как 5."""
    if expr.is_Rational:
        return str(expr.p) if expr.q == 1 else f"{expr.p}/{expr.q}"
    return _plain(expr)


def _decimal(expr, digits: int = 10) -> str:
    try:
        val = sp.N(expr, digits)
    except Exception:
        return ""
    text = sp.sstr(val)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _answer_value(expr) -> str:
    """Как показать ответ: дробь и, если нужно, десятичная запись."""
    exact = _exact(expr)
    dec = _decimal(expr)
    if dec and dec != exact and not expr.is_Integer:
        return f"{exact}  (примерно {dec})"
    return exact


# --------------------------------------------------------------------------- #
# Пример без переменных
# --------------------------------------------------------------------------- #
def _solve_expression(text: str, steps: List[Step]) -> dict:
    expr = _parse(text)
    steps.append(("Выражение", _plain(expr)))

    simplified = sp.simplify(expr)
    if _plain(simplified) != _plain(expr):
        steps.append(("Упростили", _plain(simplified)))

    factored = None
    try:
        if expr.is_Integer:
            factored = sp.factorint(expr)
    except Exception:
        factored = None
    if factored:
        parts = " * ".join(f"{p}^{k}" if k > 1 else str(p) for p, k in factored.items())
        steps.append(("Разложение на множители", parts))

    result = sp.nsimplify(simplified, rational=True)
    steps.append(("Точное значение", _exact(result)))

    dec = _decimal(result)
    if dec and dec != _exact(result):
        steps.append(("Десятичная запись", dec))

    return {
        "ok": True,
        "kind": "expression",
        "input": text,
        "answer": _answer_value(result),
        "steps": steps,
    }


# --------------------------------------------------------------------------- #
# Уравнение
# --------------------------------------------------------------------------- #
def _solve_equation(text: str, steps: List[Step]) -> dict:
    left_text, right_text = text.split("=", 1)
    left, right = _parse(left_text), _parse(right_text)
    steps.append(("Уравнение", f"{_plain(left)} = {_plain(right)}"))

    diff = sp.expand(left - right)
    steps.append(("Переносим всё в левую часть", f"{_plain(diff)} = 0"))

    variables = sorted(diff.free_symbols, key=lambda v: v.name)
    if not variables:
        same = sp.simplify(diff) == 0
        steps.append(
            ("Проверка", "Числа слева и справа совпадают" if same else "Равенство неверное")
        )
        return {
            "ok": True,
            "kind": "equation",
            "input": text,
            "answer": "верно" if same else "неверно",
            "steps": steps,
        }

    var = variables[0]
    poly = None
    if diff.is_polynomial(var):
        try:
            poly = sp.Poly(diff, var)
        except Exception:
            poly = None

    if poly is not None and poly.degree() == 1:
        a = poly.coeff_monomial(var)
        b = poly.coeff_monomial(1)
        steps.append(("Это линейное уравнение", f"{_plain(a)}*{var} = {_plain(-b)}"))
        if a != 0:
            steps.append(
                ("Делим обе части на коэффициент", f"{var} = {_plain(-b)} / {_plain(a)}")
            )
    elif poly is not None:
        steps.append(("Приводим к произведению", f"{_plain(sp.factor(diff))} = 0"))
    else:
        steps.append(("Уравнение не линейное", f"{_plain(diff)} = 0"))

    roots = sp.solve(sp.Eq(left, right), var, dict=False)
    if isinstance(roots, dict):
        roots = list(roots.values())
    if not roots:
        steps.append(("Решение", "Решений нет"))
        return {
            "ok": True,
            "kind": "equation",
            "input": text,
            "answer": "решений нет",
            "steps": steps,
        }

    answers = []
    for root in roots:
        check_left = sp.simplify(left.subs(var, root))
        check_right = sp.simplify(right.subs(var, root))
        ok = sp.simplify(check_left - check_right) == 0
        steps.append(
            (
                "Проверка подстановкой",
                f"{var} = {_plain(root)}:  {_plain(check_left)} = {_plain(check_right)}"
                f" — {'верно' if ok else 'неверно'}",
            )
        )
        answers.append(f"{var} = {_answer_value(sp.nsimplify(root, rational=True))}")

    return {
        "ok": True,
        "kind": "equation",
        "input": text,
        "answer": "; ".join(answers),
        "steps": steps,
    }


# --------------------------------------------------------------------------- #
# Точка входа
# --------------------------------------------------------------------------- #
def solve(raw: str) -> dict:
    """Решить распознанный пример и вернуть ответ вместе с шагами."""
    steps: List[Step] = [("Распознано", raw.strip())]

    machine = normalize(raw)
    if not machine:
        return {"ok": False, "error": "пустой пример", "steps": steps}
    steps.append(("Машинная запись", machine))

    try:
        if "=" in machine:
            return _solve_equation(machine, steps)
        return _solve_expression(machine, steps)
    except ZeroDivisionError:
        return {
            "ok": False,
            "error": "деление на ноль — проверь пример",
            "steps": steps,
        }
    except Exception as exc:  # noqa: BLE001 — показываем причину пользователю
        return {
            "ok": False,
            "error": f"не смог разобрать пример: {exc}",
            "steps": steps,
        }


if __name__ == "__main__":  # быстрая проверка на компьютере
    for sample in ("2+2*2", "3/4+1/6", "sqrt(144)", "2^10", "log(1000)", "2x+6=0", "x^2-5x+6=0"):
        result = solve(sample)
        print(f"{sample:>14} -> {result.get('answer') or result.get('error')}")
