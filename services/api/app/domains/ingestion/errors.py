"""Classificação de falha — transitória vs. permanente (seção 7 do plano). Decide se o
reaper pode reenfileirar (transitória) ou se vai direto a failed sem consumir tentativa
(permanente)."""


class TransientFailure(Exception):
    """Elegível a retry automático via reaper."""


class PermanentFailure(Exception):
    """Vai direto a failed, nunca consome tentativa, nunca é reenfileirada automaticamente."""


class ScopeLockHeld(TransientFailure):
    """Outro job detém o lock do mesmo scope+period — não é erro do dado, é concorrência."""


class FencingTokenMismatch(PermanentFailure):
    """O worker usava um fencing token que já não é o vigente — outro worker assumiu o
    lease enquanto este estava parado/lento. Este worker nunca deveria ter continuado;
    abortar sem retry é o comportamento correto (seção 7-ter)."""


class SchemaNotRecognized(PermanentFailure):
    pass


class NoValidRows(PermanentFailure):
    pass
