// Demo 1：验证 runnext 的「插队」行为
//
// 结论：go 语句创建的新 G 会写入当前 P 的 runnext（覆盖式，只存一个），
//      被顶掉的那个才进入本地 runq 尾部。因此最后一个创建的 G 最先执行，
//      其余按 FIFO。这不是「后进先出」，而是「最后一个插队 + 其余 FIFO」。
package main

import (
	"fmt"
	"runtime"
	"sync"
)

func scenario(name string, n int) {
	var mu sync.Mutex
	order := make([]int, 0, n)
	var wg sync.WaitGroup
	wg.Add(n)

	for i := 0; i < n; i++ {
		id := i
		go func() {
			defer wg.Done()
			mu.Lock()
			order = append(order, id)
			mu.Unlock()
		}()
	}

	wg.Wait() // 主 goroutine 阻塞，触发调度，runnext 先被取走
	fmt.Printf("%-28s 创建顺序 0..%d  →  执行顺序 %v\n", name, n-1, order)
}

func main() {
	runtime.GOMAXPROCS(1) // 单核，排除并行带来的干扰
	fmt.Printf("GOMAXPROCS=%d\n\n", runtime.GOMAXPROCS(0))

	scenario("3 个 goroutine", 3)
	scenario("5 个 goroutine", 5)
	scenario("8 个 goroutine", 8)

	fmt.Println("\n预期规律：最后一个创建的先跑，其余从 0 开始按 FIFO。")
	fmt.Println("如果看到「后进先出」的完整倒序，说明你用的不是当前调度器。")
}
