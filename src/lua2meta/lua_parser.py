from typing import override

import luaparser.ast as last
from luaparser import astnodes

from lua2meta.args import args
from lua2meta.logger import logger
from lua2meta.types import DepotKeys

__all__ = ["parse"]


class CallVisitor(last.ASTVisitor):
    appid: int | None
    depots: DepotKeys
    first_depot: int | None

    @override
    def __init__(self):
        super().__init__()
        self.appid = None
        self.depots = {}
        self.first_depot = None

    def visit_Call(self, node: astnodes.Call):
        if not (isinstance(node.func, astnodes.Name) and node.func.id == "addappid"):
            return
        match len(node.args):
            case 1:
                if not isinstance(node.args[0], astnodes.Number):
                    return
                appid: int = node.args[0].n
                if self.appid is not None:
                    logger.warning(f"Duplicate appid found in lua file, skipping {appid}")
                    return
                self.appid = appid
            case 3:
                if not isinstance(node.args[0], astnodes.Number):
                    return
                if not isinstance(node.args[2], astnodes.String):
                    return
                appid: int = node.args[0].n
                key: str = node.args[2].s.decode("utf-8")
                if self.first_depot is None:
                    self.first_depot = appid
                self.depots[appid] = key
                logger.info(f"Parsed depot {appid}:{key}")


def parse(src: str) -> tuple[int, DepotKeys]:
    tree = last.parse(src)  # raises ast.SyntaxException
    call_visitor = CallVisitor()
    call_visitor.visit(tree)
    if call_visitor.appid is None and call_visitor.first_depot is not None:
        depot = call_visitor.first_depot
        call_visitor.appid = depot
        call_visitor.depots.pop(depot)
        logger.warning(f"Guessed appid {depot} from first addappid()")

    if args.appid is not None:
        if call_visitor.appid is not None and call_visitor.appid != args.appid:
            logger.warning(f"Appid {call_visitor.appid} in .lua file does not match provided {args.appid}")
        call_visitor.appid = args.appid
    elif call_visitor.appid is None:
        raise last.SyntaxException(".lua file does not specify an appid")

    return (call_visitor.appid, call_visitor.depots)
