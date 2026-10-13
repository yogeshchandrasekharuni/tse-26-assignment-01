"""Versioned provider introspection compatibility; never alter inference requests or outputs."""


def frozen_parameter_order(actual: str, frozen: str) -> str:
    """Restore line order only after exact parameter names and value strings agree."""

    def pairs(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            fields = line.split(None, 1)
            if len(fields) != 2 or fields[0] in result:
                raise ValueError("Malformed or duplicate provider parameter")
            result[fields[0]] = fields[1]
        if not result:
            raise ValueError("Provider parameters are empty")
        return result

    if pairs(actual) != pairs(frozen):
        raise ValueError("Provider parameter names or values differ from the frozen profile")
    return frozen
