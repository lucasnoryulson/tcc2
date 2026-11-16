"""Fail-closed AST contract for the two standalone automatic transformations.

restrict is a caller precondition, not a dynamic alias analysis. Bounds and finite
arithmetic remain preconditions of the original C program; gates test inputs.
"""
import hashlib


class Unsupported(ValueError):
    pass


def children(node):
    return [child for child in node.get("inner", []) if child.get("kind")]


def unwrap(node):
    while node.get("kind") in {"ImplicitCastExpr", "ParenExpr"}:
        parts = children(node)
        if len(parts) != 1:
            raise Unsupported("unexpected cast structure")
        node = parts[0]
    return node


def name(node):
    node = unwrap(node)
    if node.get("kind") != "DeclRefExpr":
        raise Unsupported("expected a direct variable reference")
    return node["referencedDecl"]["name"]


def literal(node):
    node = unwrap(node)
    if node.get("kind") not in {"IntegerLiteral", "FloatingLiteral"}:
        raise Unsupported("expected a literal initializer")
    return float(node["value"])


def certify_kernel(kernel, source):
    """Return evidence or a concrete refusal; never authorize unknown AST nodes."""
    try:
        if not source.isascii():
            raise Unsupported("standalone source must be ASCII for source-offset insertion")
        if any((ord(c) < 32 and c not in '\t\n\r\v\f') or ord(c) == 127 for c in source):
            raise Unsupported("unsupported control character in standalone source")
        if any(token in source for token in ('#', '%:', '??', '_Pragma', '\\', '__attribute', '__declspec', '[[')):
            raise Unsupported("standalone kernels exclude preprocessing tokens, splices, pragmas and attributes")
        if kernel.get("loc", {}).get("includedFrom"):
            raise Unsupported("kernel definitions from included headers are not standalone sources")
        parts = children(kernel)
        if any(part['kind'].endswith('Attr') for part in parts):
            raise Unsupported("function attributes require a separate semantic contract")
        params = {part["name"]: part["type"]["qualType"] for part in parts if part["kind"] == "ParmVarDecl"}
        bodies = [part for part in parts if part["kind"] == "CompoundStmt"]
        if len(bodies) != 1 or any("volatile" in value or "_Atomic" in value for value in params.values()):
            raise Unsupported("one nonvolatile function body is required")
        statements = children(bodies[0])
        if "#pragma" in source:
            raise Unsupported("pre-existing pragmas require a separate adaptive transformation")
        loops = [part for part in statements if part["kind"] == "ForStmt"]
        if len(loops) != 1:
            raise Unsupported("exactly one top-level for loop is supported")
        loop = loops[0]
        raw = loop.get("inner", [])
        if len(raw) != 5 or raw[1].get("kind"):
            raise Unsupported("unsupported for-loop structure")
        init, condition, increment, body = raw[0], unwrap(raw[2]), unwrap(raw[3]), raw[4]
        declarations = children(init)
        if init.get("kind") != "DeclStmt" or len(declarations) != 1:
            raise Unsupported("loop iterator must be declared locally")
        iterator = declarations[0]
        if any(part['kind'].endswith('Attr') for part in children(iterator)):
            raise Unsupported("iterator attributes are unsupported")
        it = iterator.get("name")
        if iterator.get("type", {}).get("qualType") != "int" or literal(children(iterator)[0]) not in {0, 1}:
            raise Unsupported("supported iterator: int initialized to 0 or 1")
        if condition.get("kind") != "BinaryOperator" or condition.get("opcode") != "<":
            raise Unsupported("supported bound: iterator < integer parameter")
        condition_parts = children(condition)
        bound = name(condition_parts[1])
        if name(condition_parts[0]) != it or params.get(bound) != "int" or bound == it:
            raise Unsupported("bound must be an unmodified int parameter")
        if increment.get("kind") != "UnaryOperator" or increment.get("opcode") != "++" or name(children(increment)[0]) != it:
            raise Unsupported("supported step is ++iterator")
        location = loop.get("range", {}).get("begin", {})
        if "offset" not in location or "expansionLoc" in location:
            raise Unsupported("macro-expanded loops are unsupported")
        offset = location["offset"]
        if not isinstance(offset, int) or source[offset:offset + 3] != "for":
            raise Unsupported("AST loop offset does not identify the current source token")
        line_start = source.rfind("\n", 0, offset) + 1
        if source[line_start:offset].strip():
            raise Unsupported("for loop must begin on its own source line")
        loop_body = children(body) if body.get("kind") == "CompoundStmt" else [body]
        if len(loop_body) != 1:
            raise Unsupported("exactly one assignment is supported in the loop")
        assignment = unwrap(loop_body[0])
        lhs, rhs = children(assignment) if len(children(assignment)) == 2 else ({}, {})
        pointers = {key for key, value in params.items() if "*" in value}
        scalars = {key for key, value in params.items() if value in {"int", "double"}}
        used_inputs = set()

        def index(node):
            node = unwrap(node)
            if node.get("kind") == "DeclRefExpr" and name(node) == it:
                return
            if node.get("kind") == "BinaryOperator" and node.get("opcode") in {"+", "-"}:
                left, right = children(node)
                if name(left) == it and unwrap(right).get("kind") == "IntegerLiteral" and 0 <= literal(right) <= 16:
                    return
            raise Unsupported("only iterator +/- constant input indices are supported")

        def expression(node):
            node = unwrap(node)
            kind = node.get("kind")
            if kind in {"IntegerLiteral", "FloatingLiteral"}:
                return
            if kind == "DeclRefExpr":
                if name(node) not in scalars | {it}:
                    raise Unsupported("RHS references shared state or a pointer outside a subscript")
                return
            if kind == "ArraySubscriptExpr":
                base, subscript = children(node)
                array = name(base)
                if array not in pointers or "const double *" not in params[array]:
                    raise Unsupported("array inputs must be const double pointers")
                index(subscript)
                used_inputs.add(array)
                return
            if kind == "UnaryOperator" and node.get("opcode") in {"+", "-", "!"}:
                expression(children(node)[0])
                return
            if kind == "BinaryOperator" and node.get("opcode") in {"+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!=", "&&", "||"}:
                for child in children(node):
                    expression(child)
                return
            if kind == "ConditionalOperator":
                for child in children(node):
                    expression(child)
                return
            raise Unsupported("calls, casts, nested writes, control flow and unknown expressions are unsupported")

        expression(rhs)
        if assignment.get("kind") == "BinaryOperator" and assignment.get("opcode") == "=":
            lhs = unwrap(lhs)
            if lhs.get("kind") != "ArraySubscriptExpr":
                raise Unsupported("DOALL requires a direct array assignment")
            base, subscript = children(lhs)
            output = name(base)
            if name(subscript) != it or output not in pointers:
                raise Unsupported("DOALL output must use the injective index iterator")
            if params[output] != "double *restrict" or any("restrict" not in params[key] for key in pointers):
                raise Unsupported("DOALL requires restrict on every pointer and a mutable double output")
            if output in used_inputs or statements != [loop] or not kernel["type"]["qualType"].startswith("void ("):
                raise Unsupported("DOALL forbids output reads and other function statements")
            pattern, variable = "DOALL", None
        elif assignment.get("kind") == "CompoundAssignOperator" and assignment.get("opcode") == "+=":
            variable = name(lhs)
            locals_ = [part for part in statements if part["kind"] == "DeclStmt"]
            returns = [part for part in statements if part["kind"] == "ReturnStmt"]
            if len(locals_) != 1 or len(returns) != 1 or len(statements) != 3 or statements[1] != loop:
                raise Unsupported("reduction requires initializer, one loop and return")
            local = children(locals_[0])
            if len(local) != 1 or local[0].get("name") != variable or local[0].get("type", {}).get("qualType") != "double":
                raise Unsupported("reduction must update a local double accumulator")
            if any(part['kind'].endswith('Attr') for part in children(local[0])):
                raise Unsupported("accumulator attributes may introduce hidden side effects")
            if literal(children(local[0])[0]) != 0 or name(children(returns[0])[0]) != variable:
                raise Unsupported("reduction accumulator must start at zero and be returned")
            if not kernel["type"]["qualType"].startswith("double ("):
                raise Unsupported("reduction return type must be double")
            pattern = "REDUCTION"
        else:
            raise Unsupported("only disjoint output assignments and scalar += reductions are supported")
        return {"status": "SUPPORTED", "pattern": pattern, "iterator": it, "start_line": source.count("\n", 0, offset) + 1,
                "reduction_variable": variable, "pointer_precondition": "valid input extents; DOALL restrict pointers obey the C restrict contract",
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "version": "standalone-ast-v2"}
    except (Unsupported, KeyError, IndexError, TypeError, ValueError) as error:
        return {"status": "REFUSED", "reason": str(error), "version": "standalone-ast-v2"}
