def bounded_evaluate(expression: str, variables: dict[str, int], max_nodes: int = 32) -> int:
    tree = ast.parse(expression, mode="eval")
    return _walk(tree.body, variables)


def _walk(node, variables):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        return variables[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_walk(node.operand, variables)
    if isinstance(node, ast.BinOp):
        left = _walk(node.left, variables)
        right = _walk(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Pow):
            return left ** right
    raise ValueError("unsupported")
