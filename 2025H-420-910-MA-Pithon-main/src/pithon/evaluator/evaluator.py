from pithon.evaluator.envframe import EnvFrame
from pithon.evaluator.primitive import check_type, get_primitive_dict
from pithon.syntax import (
    PiAssignment, PiBinaryOperation, PiNumber, PiBool, PiStatement, PiProgram, PiSubscript, PiVariable,
    PiIfThenElse, PiNot, PiAnd, PiOr, PiWhile, PiNone, PiList, PiTuple, PiString,
    PiFunctionDef, PiFunctionCall, PiFor, PiBreak, PiContinue, PiIn, PiReturn,PiClassDef, PiAttribute, PiAttributeAssignment
)
from pithon.evaluator.envvalue import EnvValue, VFunctionClosure, VList, VNone, VTuple, VNumber, VBool, VString, VClassDef ,VObject,VMethodClosure


def initial_env() -> EnvFrame:
    """Crée et retourne l'environnement initial avec les primitives."""
    env = EnvFrame()
    env.vars.update(get_primitive_dict())
    return env

def lookup(env: EnvFrame, name: str) -> EnvValue:
    """Recherche une variable dans l'environnement."""
    return env.lookup(name)

def insert(env: EnvFrame, name: str, value: EnvValue) -> None:
    """Insère une variable dans l'environnement."""
    env.insert(name, value)

def evaluate(node: PiProgram, env: EnvFrame) -> EnvValue:
    """Évalue un programme ou une liste d'instructions."""
    if isinstance(node, list):
        last_value = VNone(value=None)
        for stmt in node:
            last_value = evaluate_stmt(stmt, env)
        return last_value
    elif isinstance(node, PiStatement):
        return evaluate_stmt(node, env)
    else:
        raise TypeError(f"Type de nœud non supporté : {type(node)}")

def evaluate_stmt(node: PiStatement, env: EnvFrame) -> EnvValue:
    """Évalue une instruction ou expression Pithon."""

    if isinstance(node, PiNumber):
        return VNumber(node.value)

    elif isinstance(node, PiBool):
        return VBool(node.value)

    elif isinstance(node, PiNone):
        return VNone(node.value)

    elif isinstance(node, PiString):
        return VString(node.value)

    elif isinstance(node, PiList):
        elements = [evaluate_stmt(e, env) for e in node.elements]
        return VList(elements)

    elif isinstance(node, PiTuple):
        elements = tuple(evaluate_stmt(e, env) for e in node.elements)
        return VTuple(elements)

    elif isinstance(node, PiVariable):
        return lookup(env, node.name)

    elif isinstance(node, PiBinaryOperation):
        # Traite l'opération binaire comme un appel de fonction
        fct_call = PiFunctionCall(
            function=PiVariable(name=node.operator),
            args=[node.left, node.right]
        )
        return evaluate_stmt(fct_call, env)

    elif isinstance(node, PiAssignment):
        value = evaluate_stmt(node.value, env)
        insert(env, node.name, value)
        return value
    elif isinstance(node, PiAttribute):
        target_obj = evaluate_stmt(node.object, env)
        if not isinstance(target_obj, VObject):
            raise TypeError(f"Attribut ne peut être accédé sur un objet de type {type(target_obj).__name__}.")
        if node.attr in target_obj.attributes:
            return target_obj.attributes[node.attr]
        elif node.attr in target_obj.class_def.methods:
            # Si c'est une méthode, retourne une closure de méthode
            method_closure = target_obj.class_def.methods[node.attr]
            return VMethodClosure(function=method_closure, instance=target_obj)
        else:
            raise AttributeError(f"L'attribut '{node.attr}' n'existe pas sur l'objet de type {target_obj.class_def.name}.")

    
    elif isinstance(node, PiAttributeAssignment):
        target_obj = evaluate_stmt(node.object, env)
        value = evaluate_stmt(node.value, env)
        if not isinstance(target_obj, VObject):
            raise TypeError(f"Attribut ne peut être assigné à un objet de type {type(target_obj).__name__}.")
        target_obj.attributes[node.attr] = value
        return value

    elif isinstance(node, PiIfThenElse):
        cond = evaluate_stmt(node.condition, env)
        cond = check_type(cond, VBool)
        branch = node.then_branch if cond.value else node.else_branch
        last_value = evaluate(branch, env)
        return last_value

    elif isinstance(node, PiNot):
        operand = evaluate_stmt(node.operand, env)
        # Vérifie le type pour l'opérateur 'not'
        _check_valid_piandor_type(operand)
        return VBool(not operand.value) # type: ignore

    elif isinstance(node, PiAnd):
        left = evaluate_stmt(node.left, env)
        _check_valid_piandor_type(left)
        if not left.value: # type: ignore
            return left
        right = evaluate_stmt(node.right, env)
        _check_valid_piandor_type(right)
        return right

    elif isinstance(node, PiOr):
        left = evaluate_stmt(node.left, env)
        _check_valid_piandor_type(left)
        if left.value: # type: ignore
            return left
        right = evaluate_stmt(node.right, env)
        _check_valid_piandor_type(right)
        return right

    elif isinstance(node, PiWhile):
        return _evaluate_while(node, env)

    elif isinstance(node, PiFunctionDef):
        closure = VFunctionClosure(node, env)
        insert(env, node.name, closure)
        return VNone(value=None)

    elif isinstance(node, PiReturn):
        value = evaluate_stmt(node.value, env)
        raise ReturnException(value)

    elif isinstance(node, PiFunctionCall):
        return _evaluate_function_call(node, env)

    elif isinstance(node, PiFor):
        return _evaluate_for(node, env)

    elif isinstance(node, PiBreak):
        raise BreakException()

    elif isinstance(node, PiContinue):
        raise ContinueException()

    elif isinstance(node, PiIn):
        return _evaluate_in(node, env)

    elif isinstance(node, PiSubscript):
        return _evaluate_subscript(node, env)

    elif isinstance(node, PiClassDef):
     methods = {}

     for method in node.methods:
        if isinstance(method, PiFunctionDef):
            methods[method.name] = VFunctionClosure(method, env)

     class_val = VClassDef(
        name=node.name,
        methods=methods
    )
     insert(env, node.name, class_val)
     return class_val



    else:
        raise TypeError(f"Type de nœud non supporté : {type(node)}")

def _check_valid_piandor_type(obj):
    """Vérifie que le type est valide pour 'and'/'or'."""
    if not isinstance(obj, VBool | VNumber | VString | VNone | VList | VTuple):
        raise TypeError(f"Type non supporté pour l'opérateur 'and': {type(obj).__name__}")

def _evaluate_while(node: PiWhile, env: EnvFrame) -> EnvValue:
    """Évalue une boucle while."""
    last_value = VNone(value=None)
    while True:
        cond = evaluate_stmt(node.condition, env)
        cond = check_type(cond, VBool)
        if not cond.value:
            break
        try:
            last_value = evaluate(node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return last_value

def _evaluate_for(node: PiFor, env: EnvFrame) -> EnvValue:
    """Évalue une boucle for."""
    iterable_val = evaluate_stmt(node.iterable, env)
    if not isinstance(iterable_val, (VList, VTuple)):
        raise TypeError("La boucle for attend une liste ou un tuple.")
    last_value = VNone(value=None)
    iterable = iterable_val.value
    for item in iterable:
        env.insert(node.var, item)  # Pas de nouvel environnement pour la variable de boucle
        try:
            last_value = evaluate(node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return last_value

def _evaluate_subscript(node: PiSubscript, env: EnvFrame) -> EnvValue:
    """Évalue une opération d'indexation (subscript)."""
    collection = evaluate_stmt(node.collection, env)
    index = evaluate_stmt(node.index, env)
    # Indexation pour liste, tuple ou chaîne
    if isinstance(collection, VList):
        idx = check_type(index, VNumber)
        return collection.value[int(idx.value)]
    elif isinstance(collection, VTuple):
        idx = check_type(index, VNumber)
        return collection.value[int(idx.value)]
    elif isinstance(collection, VString):
        idx = check_type(index, VNumber)
        return VString(collection.value[int(idx.value)])
    else:
        raise TypeError("L'indexation n'est supportée que pour les listes, tuples et chaînes.")

def _evaluate_in(node: PiIn, env: EnvFrame) -> EnvValue:
    """Évalue l'opérateur 'in'."""
    container = evaluate_stmt(node.container, env)
    element = evaluate_stmt(node.element, env)
    if isinstance(container, (VList, VTuple)):
        return VBool(element in container.value)
    elif isinstance(container, VString):
        if isinstance(element, VString):
            return VBool(element.value in container.value)
        else:
            return VBool(False)
    else:
        raise TypeError("'in' n'est supporté que pour les listes et chaînes.")

def _evaluate_function_call(node: PiFunctionCall, env: EnvFrame) -> EnvValue:
    """Évalue un appel de fonction (primitive ou définie par l'utilisateur)."""
    func_val = evaluate_stmt(node.function, env)
    args = [evaluate_stmt(arg, env) for arg in node.args]
    # Fonction primitive
    if isinstance(func_val, VClassDef):
        obj = VObject(class_def=func_val, attributes={})
        constructor = func_val.methods.get("__init__")
        if constructor:
           call_env = EnvFrame(parent=constructor.closure_env)
           call_env.insert('self', obj)
           for i, arg_name in enumerate(constructor.funcdef.arg_names[1:]): # Ignore 'self'
               if i < len(args):
                   call_env.insert(arg_name, args[i])
               else:
                   raise TypeError("Argument manquant pour le constructeur.")
           if constructor.funcdef.vararg:
               varargs = VList(args[len(constructor.funcdef.arg_names)-1:])
               call_env.insert(constructor.funcdef.vararg, varargs)
           elif len(args) > len(constructor.funcdef.arg_names) - 1:  # -1 pour 'self'
               raise TypeError("Trop d'arguments pour le constructeur.")

        try:
            for stmt in constructor.funcdef.body:
                evaluate_stmt(stmt, call_env)
        except ReturnException:
            pass

        return obj
    elif callable(func_val):
        return func_val(args)
    # Fonction utilisateur
    elif isinstance(func_val, VMethodClosure):
        # Appel d'une méthode liée à un objet
       method_closure = func_val.function
       instance = func_val.instance
       call_env = EnvFrame(parent=method_closure.closure_env)
       call_env.insert('self', instance)  # 'self' pour la méthode
       for i, arg_name in enumerate(method_closure.funcdef.arg_names[1:]):  # Ignore 'self'
           if i < len(args):
               call_env.insert(arg_name, args[i])
           else:
               raise TypeError("Argument manquant pour la méthode.")
       if method_closure.funcdef.vararg:
           varargs = VList(args[len(method_closure.funcdef.arg_names)-1:])
           call_env.insert(method_closure.funcdef.vararg, varargs)
       elif len(args) > len(method_closure.funcdef.arg_names) - 1:
           raise TypeError("Trop d'arguments pour la méthode.")
       try:
           for stmt in method_closure.funcdef.body:
               result = evaluate_stmt(stmt, call_env)
       except ReturnException as ret:
           return ret.value
       return VNone(value=None)
    if not isinstance(func_val, VFunctionClosure):
        raise TypeError("Tentative d'appel d'un objet non-fonction.")
    funcdef = func_val.funcdef
    closure_env = func_val.closure_env
    call_env = EnvFrame(parent=closure_env)
    for i, arg_name in enumerate(funcdef.arg_names):
        if i < len(args):
            call_env.insert(arg_name, args[i])
        else:
            raise TypeError("Argument manquant pour la fonction.")
    if funcdef.vararg:
        varargs = VList(args[len(funcdef.arg_names):])
        call_env.insert(funcdef.vararg, varargs)
    elif len(args) > len(funcdef.arg_names):
        raise TypeError("Trop d'arguments pour la fonction.")
    result = VNone(value=None)
    try:
        for stmt in funcdef.body:
            result = evaluate_stmt(stmt, call_env)
    except ReturnException as ret:
        return ret.value
    except Exception as e:
        print(f"Erreur lors de l'évaluation de la fonction : {e}")
    return result
     

class ReturnException(Exception):
    """Exception pour retourner une valeur depuis une fonction."""
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    """Exception pour sortir d'une boucle (break)."""
    pass

class ContinueException(Exception):
    """Exception pour passer à l'itération suivante (continue)."""
    pass
