def alternating_grid(func, ranges, niter=100, accept_test=None, minimum_steps=None):
    init_values = map(lambda x: (x[0] + x[1]) / 2.0, ranges)
    steps = map(lambda x: (x[1] - x[0]) / 2.0, ranges)
    minimum = func(init_values), init_values
    count = 0
    tried = [[init_values[i]] for i in range(len(ranges))]
    while count < 100:
        i = count % len(ranges)
        minimum_updated = False
        for arg_update in [- steps[i], + steps[i]]:
            args = list(init_values)
            args[i] = args[i] + arg_update
            if args[i] < ranges[i][0] or args[i] > ranges[i][1] or args[i] in tried[i]:
                continue
            res = func(args)
            tried[i].append(args[i])
            if res < minimum[0]:
                if accept_test is not None and accept_test(res, args, minimum[0], minimum[1]):
                    return res, args
                minimum = res, args
                minimum_updated = True
        if minimum_updated:
            init_values = minimum[1]
        else:
            steps[i] = steps[i] / 2.0
            if minimum_steps is not None and minimum_steps[i] > steps[i]:
                steps[i] = minimum_steps[i]
        count += 1
    return minimum
