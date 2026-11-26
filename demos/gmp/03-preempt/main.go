// Demo 3：异步抢占（Go 1.14+）能不能救一个死循环
//
// 场景：GOMAXPROCS=1，起一个「真正空转」的 goroutine（for {} 里没有任何函数调用，
//      也就没有协作式抢占点），再起一个每 100ms 打印的 goroutine。
//
// 默认行为：主 goroutine 能跑 → 异步抢占（SIGURG）生效。
// 关闭异步抢占：GODEBUG=asyncpreemptoff=1 → 空转的 G 永远不让出 P，主 goroutine 饿死。
package main

import (
	"fmt"
	"runtime"
	"time"
)

func main() {
	runtime.GOMAXPROCS(1)
	fmt.Println("GOMAXPROCS=1，启动一个空转 goroutine（for {}，无函数调用）")

	go func() {
		for {
			// 故意什么都不做：没有函数调用 = 没有协作式抢占点
		}
	}()

	start := time.Now()
	done := make(chan struct{})
	go func() {
		defer close(done)
		for i := 1; i <= 5; i++ {
			time.Sleep(100 * time.Millisecond)
			fmt.Printf("  tick %d  经过 %.0fms\n", i, float64(time.Since(start).Milliseconds()))
		}
	}()

	select {
	case <-done:
		fmt.Println("\n结论：空转的 G 被异步抢占，其他 goroutine 仍能推进。")
	case <-time.After(3 * time.Second):
		fmt.Println("\n超时：其他 goroutine 拿不到 P —— 异步抢占没生效（或被关闭）。")
	}
}
