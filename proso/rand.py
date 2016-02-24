import random


def roulette(weights, n):
    """
    Choose randomly the given number of items. The probability the item is
    chosen is proportionate to its weight.

    .. testsetup::

        import random
        from proso.rand import roulette

        random.seed(1)

    .. testcode::

        print(roulette({'cat': 2, 'dog': 1000}, 1))

    .. testoutput::

        ['dog']

    Args:
        weights (dict): item -> weight mapping, non-positive weights are forbidden
        n (int): number of chosen items

    Returns:
        list: randomly chosen items
    """
    if n > len(weights):
        raise Exception("Can't choose {} samples from {} items".format(n, len(weights)))
    if any(map(lambda w: w <= 0, weights.values())):
        raise Exception("The weight can't be a non-positive number.")
    items = weights.items()
    chosen = set()
    for i in range(n):
        total = sum(list(zip(*items))[1])
        dice = random.random() * total
        running_weight = 0
        chosen_item = None
        for item, weight in items:
            if dice < running_weight + weight:
                chosen_item = item
                break
            running_weight += weight
        chosen.add(chosen_item)
        items = [(i, w) for (i, w) in items if i != chosen_item]
    return list(chosen)
