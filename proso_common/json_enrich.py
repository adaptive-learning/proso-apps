def enrich(request, json, fun, nested=False):
    if isinstance(json, list):
        return map(lambda x: enrich(request, x, fun), json)
    elif isinstance(json, dict):
        json = fun(request, json, nested=nested)
        return {k: enrich(request, v, fun, nested=True) for k, v in json.items()}
    else:
        return json


def enrich_by_predicate(request, json, fun, predicate):
    collected = []
    memory = {'nested': False}

    def _collect(json_inner, nested):
        if isinstance(json_inner, list):
            map(lambda x: _collect(x, nested), json_inner)
        elif isinstance(json_inner, dict):
            if predicate(json_inner):
                collected.append(json_inner)
                if nested:
                    memory['nested'] = True
            map(lambda x: _collect(x, True), json_inner.values())
    _collect(json, False)
    if len(collected) > 0:
        fun(request, collected, memory['nested'])
    return json


def enrich_by_object_type(request, json, fun, object_type):
    return enrich_by_predicate(
        request, json, fun,
        lambda x: 'object_type' in x and x['object_type'] == object_type
    )
