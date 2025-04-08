from collections import defaultdict

def main():
    N, M, K = map(int, input().split())
    edges = []

    max_s = 0
    for _ in range(M):
        u, v, s = map(int, input().split())
        edges.append((u-1, v-1, s))
        max_s = max(max_s, s)

    def is_possible(limit):
        graph = defaultdict(list)
        indegree = [0] * N

        for u, v, s in edges:
            if s <= limit:
                graph[u].append(v)
                indegree[v] += 1

        
        visited = [0] * N

        def has_cycle(v):
            visited[v] = 1
            for nei in graph[v]:
                if visited[nei] == 1:
                    return True
                if visited[nei] == 0 and has_cycle(nei):
                    return True
            visited[v] = 2
            return False

        for i in range(N):
            if visited[i] == 0:
                if has_cycle(i):
                    return True  

        dp = [0] * N
        order = []
        visited = [False] * N

        def dfs(v):
            visited[v] = True
            for nei in graph[v]:
                if not visited[nei]:
                    dfs(nei)
            order.append(v)

        for i in range(N):
            if not visited[i]:
                dfs(i)
        order.reverse()

        for u in order:
            for v in graph[u]:
                if dp[v] < dp[u] + 1:
                    dp[v] = dp[u] + 1

        return max(dp) >= K

    left = 0
    right = max_s
    answer = -1

    while left <= right:
        mid = (left + right) // 2
        if is_possible(mid):
            answer = mid
            right = mid - 1
        else:
            left = mid + 1

    print(answer)

if __name__ == "__main__":
    main()