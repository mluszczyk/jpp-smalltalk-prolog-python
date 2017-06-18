from unittest import TestCase

from prolog import L, V, C, global_store, Prolog


class TestOne(TestCase):
    def test_const_none(self):
        self.assertIsNone(L.value())

    def test_const(self):
        self.assertEqual(C.make_const(123).value(), 123)

    def test_pair(self):
        assert L.pair(L).car().value() is None
        assert L.pair(L).cdr().value() is None

    def test_const_pair(self):
        assert L.make_const(3).cdr().value() == 3
        assert L.make_const(3).car().value() is None

    def test_var_pair(self):
        assert L.make_variable("blah").car().value() is None

    def test(self):
        t = L.make_const(1).pair(V.make_variable(2).make_const(3))
        assert t.car().car().value() is None
        assert t.car().cdr().value() == 1
        self.assertIsNone(t.car().value()[0])
        self.assertEqual(t.car().value()[1], 1)
        self.assertEqual(t.cdr().cdr().value(), 3)

        a = V.make_variable(1)
        b = V.make_variable(2)
        c = V.make_variable(1)
        self.assertNotEqual(a, b)
        self.assertEqual(a, c)

        t = C.make_const(1).make_variable("z")
        self.assertEqual(t.car().value(), 1)
        with self.assertRaises(Exception):
            t.value()

        C.make_const(1).go(C.make_const(2), lambda: self.assertFalse(True))

        w = []
        C.make_const(1).go(C.make_const(1), lambda: w.append(1))
        self.assertEqual(w, [1])

    def test_unify_two_vars(self):
        w = 0
        x = V.make_variable("x")
        y = V.make_variable("y")

        def check():
            nonlocal w
            w += 1
            assert x.value() == 2
            assert y.value() == 1

        x.make_const(1).go(C.make_const(2).pair(y), check)
        self.assertEqual(w, 1)

    def test_unify_with_pair(self):
        w = 0
        x = V.make_variable('x')

        def check():
            nonlocal w
            w += 1
            self.assertEqual(x.value()[0], 1)
            self.assertEqual(x.cdr().value(), 2)
        C.make_const(1).make_const(2).go(x, check)
        self.assertEqual(w, 1)

    def test_unify_nested(self):
        w = 0
        x = V.make_variable('x')

        def check1():
            nonlocal w
            w = w + 1
            x.go(C.make_const('b'), lambda: self.assertFalse(True))
        x.go(C.make_const('a'), check1)

        def check2():
            nonlocal w
            w = w + 1
        x.go(C.make_const('b'), check2)
        self.assertEqual(w, 2)

    def test_unify_repeated(self):
        w = 0
        x = V.make_variable('x')
        y = V.make_variable('y')

        def check():
            nonlocal w
            w += 1
            self.assertEqual(x.value(), 1)
            self.assertEqual(y.value(), 1)

        x.make_const(1).go(y.pair(y), check)
        self.assertEqual(w, 1)

    def test_occur_check(self):
        x = V.make_variable('x')
        x.go(L.pair(x), lambda: self.assertTrue(False))


class TestProlog(TestCase):
    def test(self):
        x = V.make_variable('x')
        t = [1, 2, 3]
        p = Prolog()
        for e in t:
            p.fact(C.make_const(e))
        w = []
        p.go(x, lambda: w.append(x.value()))
        self.assertEqual(w, t)

    def test_and(self):
        w = 0
        p = Prolog()
        for e in [1, 2, 3]:
            p.fact(C.make_const(e))

        def go():
            nonlocal w
            w += 1

        p.go(C.make_const(1) & C.make_const(2) & C.make_const(3), go)
        self.assertEqual(w, 1)

    def test_and_nested(self):
        w = 0
        p = Prolog()
        for e in [1, 2, 3]:
            p.fact(C.make_const(e))

        def go():
            nonlocal w
            w += 1

        p.go(C.make_const(1) & (C.make_const(2) & C.make_const(3)), go)
        self.assertEqual(w, 1)

    def test_head_body(self):
        x = V.make_variable("x")
        y = V.make_variable("y")
        p = Prolog()
        p.fact(C.make_const(1).make_const('a'))
        p.fact(C.make_const(2).make_const('b'))
        p.head_body(x.pair(y.make_const('c')), x.make_const('a') & y.make_const('b'))
        w = 0

        def check():
            nonlocal w
            w += 1
            self.assertEqual(x.value(), 1)
            self.assertEqual(y.value(), 2)

        p.go(x.pair(y.make_const('c')), check)
        self.assertEqual(w, 1)

    def test_member(self):
        x = V.make_variable("x")
        y = V.make_variable("y")
        z = V.make_variable("z")

        p = Prolog()
        p.fact(x.pair(y.pair(x)).make_const("member"))
        p.head_body(x.pair(y.pair(z)).make_const("member"),
                    x.pair(y).make_const("member"))

        w = []
        p.go(x.pair(L.make_const(1).make_const(2).make_const(3)),
             lambda: w.append(x.value()))
        self.assertEqual(w, [3, 2, 1])
