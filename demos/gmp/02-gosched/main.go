// Demo 2：Gosched 会把 G 降级到「全局队列」，代价很大
//
// 结论一：主动让出（Gosched）不是放回本地 runq，而是塞进全局 sched.runq，
//        下次被调度要等本地队列先清空、或轮到 61 次批量取。
// 结论二：因此 Gosched 的代价远高于「什么都不做」，生产代码里基本不该出现。
package main

import (
	"fmt"
	"runtime"
	"sync"
	"time"
)

func orderDemo() {
	var mu sync.Mutex
	log := make([]string, 0, 6)
	rec := func(s string) { mu.Lock(); log = append(log, s); mu.Unlock() }

	var wg sync.WaitGroup
	wg.Add(3)

	// A 跑起来后主动让出 → 进入全局队列
	go func() { defer wg.Done(); rec("A-start"); runtime.Gosched(); rec("A-resume") }()
	go func() { defer wg.Done(); rec("B") }()
	go func() { defer wg.Done(); rec("C") }()

	wg.Wait()
	fmt.Printf("执行日志：%v\n", log)
	fmt.Println("预期：C 先跑（runnext），A 让出后进全局队列，B 插上，A 最后回来。")
}

// sink 防止编译器把循环优化掉（死代码消除）
var sink int

func costDemo(iter int) (time.Duration, time.Duration, int, int) {
	// 不让出
	t0 := time.Now()
	x := 0
	for i := 0; i < iter; i++ {
		x += i * 3
	}
	plain := time.Since(t0)
	sink = x

	// 每 1000 次让出一次
	t1 := time.Now()
	y := 0
	for i := 0; i < iter; i++ {
		y += i * 3
		if i%1000 == 0 {
			runtime.Gosched()
		}
	}
	withYield := time.Since(t1)
	sink = y
	return plain, withYield, x, y
}

func main() {
	runtime.GOMAXPROCS(1)
	fmt.Println("== 场景一：Gosched 会改变执行顺序 ==")
	orderDemo()

	fmt.Println("\n== 场景二：Gosched 的代价 ==")
	plain, withYield, x, y := costDemo(300000)
	fmt.Printf("不让出       ：%v   (checksum %d)\n", plain, x)
	fmt.Printf("每 1000 次让出：%v   (checksum %d)\n", withYield, y)
	if plain > 0 {
		fmt.Printf("倍率         ：约 %.0fx\n", float64(withYield)/float64(plain))
	}
	fmt.Println("\n注意：倍率随机器与负载波动，但「让出显著更慢」是稳定结论。")
}
