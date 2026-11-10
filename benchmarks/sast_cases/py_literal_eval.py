import ast


def parse(text: str) -> object:
    return ast.literal_eval(text)
