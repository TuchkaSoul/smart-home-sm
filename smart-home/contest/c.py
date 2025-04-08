def main():
    n, m = map(int, input().split())
    s = list(map(int, input().split()))

    first_occurrence = {}
    last_occurrence = {}
    for idx, color in enumerate(s):
        if color not in first_occurrence:
            first_occurrence[color] = idx
        last_occurrence[color] = idx

    colors = sorted(last_occurrence.keys(), key=lambda c: (first_occurrence[c], last_occurrence[c]))

    operations = []
    used_colors = set()

    for c in colors:
        if c not in first_occurrence:
            continue
        l = first_occurrence[c] + 1  # 1-based
        r = last_occurrence[c] + 1   # 1-based
        operations.append((c, l, r))
        used_colors.add(c)

    for color in s:
        if color not in used_colors:
            print(-1)
            return

    print(len(operations))
    for op in operations:
        print(op[0], op[1], op[2])

if __name__ == "__main__":
    main()
