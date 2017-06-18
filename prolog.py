import typing


class Pair:
    def __init__(self, item1, item2):
        self.item1 = item1
        self.item2 = item2

    def car(self):
        return self.item1

    def cdr(self):
        return self.item2


class Handle:
    def __init__(self, ref):
        self.ref_ = ref

    def value(self):
        return global_store.value(self.ref_)

    def car(self):
        return global_store.car(self. ref_)

    def cdr(self):
        return global_store.cdr(self.ref_)

    def pair(self, other):
        """should be #,"""
        return Handle(global_store.make_pair(self.ref_, other.ref_))

    def make_const(self, value):
        return self.pair(C.make_const(value))

    def make_variable(self, name):
        return self.pair(V.make_variable(name))

    def go(self, handle2: 'Handle', do):
        global_store.unify(self.ref_, handle2.ref_, do)

    def __eq__(self, other):
        return self.ref_ == other.ref_


class C:
    @staticmethod
    def make_const(value):
        return Handle(global_store.make_const(value))


class V:
    @staticmethod
    def make_variable(name):
        return Handle(global_store.make_variable(name))


class Store:
    def __init__(self):
        self.items: typing.Dict[typing.Any, Value] = {}
        self.variables = {}
        self.next_ref = 0

    def get_next_ref(self):  # factor it out into a separate class
        ref = self.next_ref
        self.next_ref += 1
        return ref

    def make_const(self, val):
        ref = self.next_ref
        self.next_ref += 1
        self.items[ref] = ConstValue(val)
        return ref

    def make_variable(self, name):
        if name not in self.variables:
            self.variables[name] = self.get_next_ref()
        return self.variables[name]

    def make_pair(self, ref1, ref2):
        ref = self.get_next_ref()
        self.items[ref] = PairValue(self.get_item_or_ref(ref1),
                                    self.get_item_or_ref(ref2))
        return ref

    def get_item_or_ref(self, ref):
        try:
            return self.items[ref]
        except KeyError:
            return RefValue(ref)

    def get_item(self, ref):
        try:
            return self.items[ref]
        except KeyError:
            raise Exception("Value not set")

    def value(self, ref):
        return self.get_item(ref).value()

    def car(self, ref):
        return self.get_item(ref).car()

    def cdr(self, ref):
        return self.get_item(ref).cdr()

    def clone(self) -> 'Store':
        new_store = Store()
        new_store.items = {k: v.clone() for k, v in self.items.items()}
        new_store.variables = self.variables.copy()
        new_store.next_ref = self.next_ref
        return new_store

    def substitute(self, name, value: 'Value'):
        print("substitute({}, {})".format(name, value))
        new_items = {name: value}
        for left, right in self.items.items():
            new_items[left] = right.substitute(name, value)

        self.items = new_items

    @staticmethod
    def fix_subst_list(subst_list):
        num = len(subst_list)
        for num in range(num):
            name, val = subst_list[num]
            for inum, (iname, ival) in enumerate(subst_list):
                subst_list[inum] = (iname, ival.substitute(name, val))
        return subst_list

    def substitute_list(self, subst_list):
        print("substitute list", [(a, str(b)) for a, b in subst_list])
        self.fix_subst_list(subst_list)
        print("fixed list", [(a, str(b)) for a, b in subst_list])

        for (name, value) in subst_list:
            self.substitute(name, value)

    def unify(self, ref1, ref2, do):
        print('items before sub', {s: str(v) for s, v in self.items.items()})
        print('vars before sub', {s: v for s, v in self.variables.items()})
        subst = self.get_item_or_ref(ref1).unify(self.get_item_or_ref(ref2))
        if subst is not None:
            new_global_store = self.clone()
            new_global_store.substitute_list(subst)

            global global_store
            global_store = new_global_store

            print('items after sub', {s: str(v) for s, v in new_global_store.items.items()})
            print('vars after sub', {s: v for s, v in new_global_store.variables.items()})

            exc = None
            try:
                do()
            except Exception as e:
                exc = e

            global_store = self

            if exc is not None:
                raise exc


global_store = Store()


class Value:
    def car(self):
        raise NotImplementedError()

    def cdr(self):
        raise NotImplementedError()

    def value(self):
        raise NotImplementedError()

    def clone(self):
        raise NotImplementedError()

    def substitute(self, ref, value: 'Value'):
        raise NotImplementedError()

    def unify(self, other):
        raise NotImplementedError()

    def unify_with_const(self, const_value):
        raise NotImplementedError()

    def unify_with_var(self, var: 'Value'):
        raise NotImplementedError()

    def unify_with_pair(self, a: 'Value', b: 'Value'):
        raise NotImplementedError()

    def get_ref(self):
        raise Exception("not a ref")


class ConstValue(Value):
    def __init__(self, val):
        self.val = val

    def car(self):
        raise Exception("not a pair")

    def cdr(self):
        raise Exception("not a pair")

    def value(self):
        return self.val

    def clone(self):
        return self

    def substitute(self, ref, value: Value):
        return self

    def __str__(self):
        return "const ({})".format(self.val)

    def unify(self, other) ->\
            typing.Union[typing.List[typing.Tuple[typing.Any, Value]], None]:
        return other.unify_with_const(self.val)

    def unify_with_const(self, val):
        if self.val == val:
            return []
        else:
            return None

    def unify_with_pair(self, a, b):
        return None

    def unify_with_var(self, value: Value):
        return value.unify_with_const(self.val)


class PairValue(Value):
    def __init__(self, key1: Value, key2: Value):
        self.key1: Value = key1
        self.key2: Value = key2

    def value(self):
        return self.car().value(), self.cdr().value()

    def car(self):
        return self.key1

    def cdr(self):
        return self.key2

    def clone(self):
        return PairValue(self.key1, self.key2)

    def substitute(self, ref, value: Value):
        self.key1 = self.key1.substitute(ref, value)
        self.key2 = self.key2.substitute(ref, value)
        return self

    def __str__(self):
        return "pair ({}), ({})".format(self.key1, self.key2)

    def unify_with_const(self, const):
        return None

    def unify_with_pair(self, a: Value, b: Value):
        subst1 = self.key1.unify(a)
        if subst1 is None:
            return None
        subst2 = self.key2.unify(b)
        if subst2 is None:
            return None
        return subst1 + subst2

    def unify_with_var(self, var: Value):
        return var.unify_with_pair(self.key1, self.key2)

    def unify(self, other):
        return other.unify_with_pair(self.key1, self.key2)


class RefValue(Value):
    def __init__(self, ref):
        self.ref = ref

    def value(self):
        raise Exception("value not assigned")

    def car(self):
        raise Exception("value not assigned")

    def cdr(self):
        raise Exception("value not assigned")

    def clone(self):
        return RefValue(self.ref)

    def substitute(self, ref, value: Value):
        if self.ref == ref:
            return value
        else:
            return value

    def __str__(self):
        return "ref ({})".format(self.ref)

    def unify(self, other: Value):
        return other.unify_with_var(self)

    def unify_with_const(self, value):
        return [(self.ref, ConstValue(value))]

    def unify_with_pair(self, a: Value, b: Value):
        return [(self.ref, PairValue(a, b))]

    def unify_with_var(self, other: Value):
        return [(self.ref, other)]

    def get_ref(self):
        return self.ref


L = C.make_const(None)
