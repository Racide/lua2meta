from typing import override

from luaparser import ast

from lua2meta.types import DepotKeys

__all__ = ["parse"]


class CallVisitor(ast.ASTVisitor):
    appid: int | None
    depots: DepotKeys

    @override
    def __init__(self):
        self.appid = None
        self.depots = {}

    def visit_Call(self, node: ast.Call):
        if not (isinstance(node.func, ast.Name) and node.func.id == "addappid"):
            return
        match len(node.args):
            case 1:
                if not isinstance(node.args[0], ast.Number):
                    return
                t: int = node.args[0].n
                if self.appid is not None:
                    print(f"Duplicate appid found in lua file, skipping {t}")
                    return
                self.appid = t
            case 3:
                if not isinstance(node.args[0], ast.Number):
                    return
                if not isinstance(node.args[2], ast.String):
                    return
                self.depots[node.args[0].n] = node.args[2].s
                print(f"Parsed depot {node.args[0].n}:{node.args[2].s}")


def parse(src: str) -> tuple[int, DepotKeys]:
    tree = ast.parse(src)  # raises ast.SyntaxException
    call_visitor = CallVisitor()
    call_visitor.visit(tree)
    if call_visitor.appid is None:
        raise ast.SyntaxException(".lua file does not specify an appid")
    return (call_visitor.appid, call_visitor.depots)
