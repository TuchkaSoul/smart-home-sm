import bisect

n, m = map(int, input().split())
list_houses=list(map(int, input().split()))
list_heaters=list(map(int, input().split()))

def minimal_r(list_houses, list_heaters):
    list_houses.sort()
    list_heaters.sort()
    max_r = 0

    for house in list_houses:
        pos = bisect.bisect_left(list_heaters, house)
        min_dist = float('inf')
        if pos > 0:
            min_dist = house - list_heaters[pos - 1]
        if pos < len(list_heaters):
            min_dist = min(min_dist, list_heaters[pos] - house)
        max_r = max(max_r, min_dist)

    return max_r

print(minimal_r(list_houses,list_heaters))
