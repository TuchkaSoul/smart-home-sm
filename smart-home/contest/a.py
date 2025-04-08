from itertools import product

suits = set("CDHS")
ranks = set("23456789TJQKA")
full_deck = set(product(ranks, suits))

def parse_subset(subset_str):
    rank_part = set()
    suit_part = set()
    
    for c in subset_str:
        if c in ranks:
            rank_part.add(c)
        elif c in suits:
            suit_part.add(c)
    
    if not rank_part and not suit_part:
        return full_deck
    if not rank_part:
        return {(r, s) for r in ranks for s in suit_part}
    if not suit_part:
        return {(r, s) for r in rank_part for s in suits}
    
    return {(r, s) for r in rank_part for s in suit_part}

def compute_probability(r, s, subsets):
    removed = set()
    for i in range(r):
        removed.update(subsets[i])
    
    remaining = full_deck - removed
    if not remaining:
        return 0.0  

    # вероятность — это сколько из оставшихся попадает хотя бы в одно winning-множество
    winning_cards = set()
    for i in range(r, r + s):
        winning_cards.update(subsets[i] & remaining)
    
    return len(winning_cards) / len(remaining)

def read_input():
    r1, s1, r2, s2 = map(int, input().split())
    subsets = [input().strip() for _ in range(r1 + s1 + r2 + s2)]
    
    goose1_subsets = [parse_subset(x) for x in subsets[:r1 + s1]]
    goose2_subsets = [parse_subset(x) for x in subsets[r1 + s1:]]
    
    return r1, s1, goose1_subsets, r2, s2, goose2_subsets

def main():
    r1, s1, g1, r2, s2, g2 = read_input()
    prob1 = compute_probability(r1, s1, g1)
    prob2 = compute_probability(r2, s2, g2)
    print(f"{max(prob1, prob2):.6f}")

if __name__ == "__main__":
    main()
