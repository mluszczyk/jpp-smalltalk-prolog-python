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

    def __and__(self, other) -> 'HandleConjunction':
        return HandleConjunction.from_handle(self) & other

    def to_conjunction(self) -> 'HandleConjunction':
        return HandleConjunction.from_handle(self)

    def __repr__(self):
        return "Handle({} => {})".format(self.ref_, global_store.get_item_or_ref(self.ref_))

    def get_free_variables(self):
        return global_store.get_free_vars(self.ref_)

    def substitute(self, subst):
        return Handle(global_store.substitute_ref(self.ref_, subst))


class HandleConjunction:
    def __init__(self, handles: typing.List[Handle]):
        self.handles: typing.List[Handle] = handles

    @staticmethod
    def from_handle(handle) -> 'HandleConjunction':
        return HandleConjunction([handle])

    def __and__(self, other: typing.Union[Handle, 'HandleConjunction']) ->\
            'HandleConjunction':
        con = other.to_conjunction()
        return HandleConjunction(self.handles + con.handles)

    def to_conjunction(self) -> 'HandleConjunction':
        return self

    def empty(self) -> bool:
        return not self.handles

    def head(self) -> Handle:
        return self.handles[0]

    def tail(self) -> 'HandleConjunction':
        return HandleConjunction(self.handles[1:])

    def __repr__(self):
        return "HandleConjunction([{}])".format(
            ", ".join(str(handle) for handle in self.handles))

    def get_free_variables(self):
        return [item
                for handle in self.handles
                for item in handle.get_free_variables()]

    def substitute(self, subst):
        return HandleConjunction([handle.substitute(subst) for handle in self.handles])


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
        new_items = {}
        for left, right in self.items.items():
            new_items[left] = right.substitute(name, value)
        new_items[name] = value

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
        self.fix_subst_list(subst_list)

        for (name, value) in subst_list:
            self.substitute(name, value)

    def unify(self, ref1, ref2, do):
        print("unify \n{} with \n{}".format(self.get_item_or_ref(ref1), self.get_item_or_ref(ref2)))
        subst = self.get_item_or_ref(ref1).unify(self.get_item_or_ref(ref2))
        print("subst", subst)

        if subst is None:
            pass
        else:
            new_global_store = self.clone()
            new_global_store.substitute_list(subst)

            if not subst:
                self.push_store(new_global_store, do)
            else:
                def new_do():
                    global_store.unify(ref1, ref2, do)

                self.push_store(new_global_store, new_do)

    def push_store(self, new_store, do):
        global global_store
        global_store = new_store

        exc = None
        try:
            do()
        except Exception as e:
            exc = e

        global_store = self

        if exc is not None:
            raise exc

    def __repr__(self):
        return "items: {}; vars: {}".format(
            {k: str(v) for k, v in self.items.items()},
            self.variables
        )

    def get_free_vars(self, ref):
        return self.get_item_or_ref(ref).get_free_vars()

    def clone_variables(self, vars_list):
        vars_list = list(set(vars_list))
        return [(var, self.get_next_ref()) for var in vars_list]

    def substitute_ref(self, ref, subst_list):
        value = self.items.get(ref)

        if value is not None:
            new_ref = self.get_next_ref()

            new_value = value.clone()
            self.items[new_ref] = new_value.substitute_ref_list(subst_list)
            return new_ref
        else:
            for (sub_ref, sub_val) in subst_list:
                if sub_ref == ref:
                    return sub_val
            return ref


global_store = Store()


class Value:
    def car(self):
        raise NotImplementedError()

    def cdr(self):
        raise NotImplementedError()

    def value(self):
        raise NotImplementedError()

    def clone(self) -> 'Value':
        raise NotImplementedError()

    def substitute(self, ref, value: 'Value') -> 'Value':
        raise NotImplementedError()

    def unify(self, other):
        raise NotImplementedError()

    def unify_with_const(self, const_value):
        raise NotImplementedError()

    def unify_with_var(self, ref):
        raise NotImplementedError()

    def unify_with_pair(self, a: 'Value', b: 'Value'):
        raise NotImplementedError()

    def get_ref(self):
        raise Exception("not a ref")

    def has_occurrence(self, ref):
        raise NotImplementedError()

    def get_free_vars(self):
        raise NotImplementedError()

    def substitute_ref(self, old_ref, new_ref) -> 'Value':
        raise NotImplementedError()

    def substitute_ref_list(self, subst_list):
        new_val = self
        for ref, new_ref in subst_list:
            new_val = new_val.substitute_ref(ref, new_ref)
        return new_val


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

    def __repr__(self):
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

    def unify_with_var(self, ref):
        return RefValue(ref).unify_with_const(self.val)

    def has_occurrence(self, ref):
        return False

    def get_free_vars(self):
        return []

    def substitute_ref(self, old_ref, new_ref):
        return self


class PairValue(Value):
    def __init__(self, value1: Value, value2: Value):
        self.value1: Value = value1
        self.value2: Value = value2

    def value(self):
        return self.car().value(), self.cdr().value()

    def car(self):
        return self.value1

    def cdr(self):
        return self.value2

    def clone(self):
        return PairValue(self.value1.clone(), self.value2.clone())

    def substitute(self, ref, value: Value):
        self.value1 = self.value1.substitute(ref, value)
        self.value2 = self.value2.substitute(ref, value)
        return self

    def __repr__(self):
        return "pair ({}), ({})".format(self.value1, self.value2)

    def unify_with_const(self, const):
        return None

    def unify_with_pair(self, a: Value, b: Value):
        subst1 = self.value1.unify(a)
        if subst1 is None:
            return None
        subst2 = self.value2.unify(b)
        if subst2 is None:
            return None
        return subst1 + subst2

    def unify_with_var(self, ref):
        return RefValue(ref).unify_with_pair(self.value1, self.value2)

    def unify(self, other):
        return other.unify_with_pair(self.value1, self.value2)

    def has_occurrence(self, ref):
        return self.value1.has_occurrence(ref) or self.value2.has_occurrence(ref)

    def get_free_vars(self):
        return self.value1.get_free_vars() + self.value2.get_free_vars()

    def substitute_ref(self, old_ref, new_ref):
        return PairValue(self.value1.substitute_ref(old_ref, new_ref),
                         self.value2.substitute_ref(old_ref, new_ref))


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

    def substitute(self, ref, value: Value) -> Value:
        if self.ref == ref:
            return value
        else:
            return self

    def __repr__(self):
        return "ref ({})".format(self.ref)

    def unify(self, other: Value):
        return other.unify_with_var(self.ref)

    def unify_with_const(self, value):
        return [(self.ref, ConstValue(value))]

    def unify_with_pair(self, a: Value, b: Value):
        if a.has_occurrence(self.ref) or b.has_occurrence(self.ref):
            return None
        return [(self.ref, PairValue(a, b))]

    def unify_with_var(self, ref):
        if ref == self.ref:
            return []
        else:
            return [(self.ref, RefValue(ref))]

    def get_ref(self):
        return self.ref

    def has_occurrence(self, ref):
        return self.ref == ref

    def get_free_vars(self):
        return [self.ref]

    def substitute_ref(self, old_ref, new_ref):
        if self.ref == old_ref:
            return RefValue(new_ref)
        else:
            return self


L = C.make_const(None)


class Predicate:
    def go(self, query: typing.Union['Handle', 'HandleConjunction'], do: typing.Callable):
        raise NotImplementedError()

    def with_new_free_variables(self):
        raise NotImplementedError()


class Fact(Predicate):
    def __init__(self, a: Handle):
        self.a: Handle = a

    def go(self, a: Handle, do: typing.Callable):
        print(">> {} go {}".format(self, a))
        copy = self.with_new_free_variables()
        print("cloned: ", copy)

        def do_debug(arg_do):

            def x():
                print("went")
                arg_do()
                print("unwent")
            return x

        copy.a.go(a, do_debug(do))

    def __repr__(self):
        return "Fact({})".format(self.a)

    def with_new_free_variables(self):
        free_vars = self.a.get_free_variables()
        subst = global_store.clone_variables(free_vars)
        new_a = self.a.substitute(subst)
        return Fact(new_a)


class HeadBody(Predicate):
    def __init__(self, prolog: 'Prolog', head: Handle, body: HandleConjunction):
        self.head: Handle = head
        self.body: HandleConjunction = body
        self.prolog: Prolog = prolog

    def go(self, query: Handle, do: typing.Callable):
        print(">> {} go {}".format(self, query))
        copy = self.with_new_free_variables()
        print("cloned", copy)

        def inner_do():
            self.prolog.go(copy.body, do)

        copy.head.go(query, inner_do)

    def __repr__(self):
        return "HeadBody({}, {})".format(self.head, self.body)

    def with_new_free_variables(self):
        vars_head = self.head.get_free_variables()
        vars_tail = self.body.get_free_variables()
        subst = global_store.clone_variables(vars_head + vars_tail)
        new_head = self.head.substitute(subst)
        new_body = self.body.substitute(subst)
        return HeadBody(self.prolog, new_head, new_body)


class Prolog:
    def __init__(self):
        self.predicates: typing.List[Predicate] = []

    def fact(self, a):
        self.predicates.append(Fact(a).with_new_free_variables())

    def head_body(self, head, body):
        self.predicates.append(HeadBody(self, head, body).with_new_free_variables())

    def go(self, handle: typing.Union[Handle, HandleConjunction], do: typing.Callable):
        full_con = handle.to_conjunction()

        def do_builder(handle_con, copy_do):
            def inner_do():
                print("inner_do", handle_con)

                if handle_con.empty():
                    print("*** call do")
                    copy_do()
                else:
                    for item in self.predicates:
                        item.go(handle_con.head(), do_builder(handle_con.tail(), copy_do))

            return inner_do

        do_builder(full_con, do)()

    def __repr__(self):
        return "Prolog([{}])".format(", ".join(str(pred) for pred in self.predicates))
